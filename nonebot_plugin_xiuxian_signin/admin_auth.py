"""后台账号与会话认证（对应重构计划 R-04）。

设计要点：

- 凭据持久化在数据目录的 ``admin_auth.json``，与运营配置 ``admin_config.json``
  分开存放——后者支持「配置一键回滚」，密码哈希不应进入回滚范围。
- 密码用 PBKDF2-HMAC-SHA256 加盐哈希，任何路径都不落明文。
- 会话是 HMAC 签名的无状态 token，密钥持久化，重启 bot 不掉登录；改密后轮换
  密钥，令其它会话立即失效。
- 首次启动生成随机密码并只在日志里打印一次，登录后强制改密。
- 后台路由跑在 Starlette 线程池里，因此本模块内部用线程锁保护读改写。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
from pathlib import Path
from typing import Any

from nonebot import logger

from .storage import atomic_write_json

SESSION_COOKIE_NAME = "xiuxian_admin_session"
SESSION_TTL_SECONDS = 7 * 24 * 3600
MIN_PASSWORD_LENGTH = 16
PBKDF2_ITERATIONS = 240_000
AUTH_FILE_NAME = "admin_auth.json"
_WEAK_PASSWORDS = {
    "admin",
    "admin123",
    "123456",
    "1234567890123456",
    "password",
    "xiuxian",
    "nonebot",
    "qwertyuiopasdfgh",
}


class AuthConfigError(RuntimeError):
    """Raised when the admin credential file cannot be created or parsed."""


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64d(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def hash_password(
    password: str,
    *,
    salt: bytes | None = None,
    iterations: int = PBKDF2_ITERATIONS,
) -> dict[str, Any]:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return {
        "algorithm": "pbkdf2_sha256",
        "iterations": int(iterations),
        "salt": _b64e(salt),
        "hash": _b64e(digest),
    }


def verify_password(password: str, record: Any) -> bool:
    if not isinstance(record, dict):
        return False
    try:
        salt = _b64d(str(record["salt"]))
        expected = _b64d(str(record["hash"]))
        iterations = int(record["iterations"])
    except (KeyError, TypeError, ValueError):
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(digest, expected)


def password_strength_error(password: str) -> str | None:
    """返回不可用的原因；``None`` 表示通过。

    下限 16 字符（用户拍板），并要求不是常见弱口令，避免「设了等于没设」。
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"密码长度至少 {MIN_PASSWORD_LENGTH} 位"
    if password.strip().lower() in _WEAK_PASSWORDS:
        return "密码过于常见，请更换"
    if len(set(password)) < 6:
        return "密码字符种类过于单一，请更换"
    return None


class AdminAuth:
    def __init__(
        self,
        data_dir: Path,
        *,
        env_username: str = "",
        env_password: str = "",
        session_ttl: int = SESSION_TTL_SECONDS,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.path = self.data_dir / AUTH_FILE_NAME
        self.env_username = str(env_username or "").strip()
        self.env_password = str(env_password or "")
        self.session_ttl = int(session_ttl)
        self._lock = threading.RLock()
        self._failures: dict[str, tuple[int, float]] = {}

    # --- 持久化 -----------------------------------------------------------
    def _read(self) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AuthConfigError(f"后台凭据文件不可读：{self.path}（{exc}）") from exc
        if not isinstance(raw, dict) or not isinstance(raw.get("password"), dict):
            raise AuthConfigError(f"后台凭据文件结构异常：{self.path}")
        return raw

    def _write(self, data: dict[str, Any]) -> None:
        data["version"] = int(data.get("version") or 1)
        data["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        atomic_write_json(self.path, data)

    def ensure_initialized(self) -> str | None:
        """确保凭据存在；返回仅需展示一次的明文密码（未生成时为 ``None``）。"""
        with self._lock:
            existing = self._read()
            if existing is not None:
                return None
            username = self.env_username or "admin"
            if self.env_password:
                error = password_strength_error(self.env_password)
                if error:
                    raise AuthConfigError(f"环境变量中的后台密码不合规：{error}")
                password = self.env_password
                must_change = False
            else:
                password = secrets.token_urlsafe(18)
                must_change = True
            data = {
                "username": username,
                "password": hash_password(password),
                "must_change_password": must_change,
                "session_secret": secrets.token_urlsafe(32),
            }
            self._write(data)
            if must_change:
                logger.warning(
                    "已生成修仙签到后台初始账号："
                    f"{username} / {password}（仅本次显示，登录后必须修改）"
                )
            else:
                logger.info(f"修仙签到后台已使用环境变量中的账号初始化：{username}")
            return password if must_change else None

    # --- 账号 -------------------------------------------------------------
    def username(self) -> str:
        with self._lock:
            data = self._read() or {}
        return str(data.get("username") or "admin")

    def must_change_password(self) -> bool:
        with self._lock:
            data = self._read() or {}
        return bool(data.get("must_change_password"))

    def authenticate(self, username: str, password: str) -> bool:
        with self._lock:
            data = self._read()
        if data is None:
            return False
        # 用户名比较也走常量时间，避免通过响应时间枚举账号。
        if not hmac.compare_digest(str(username or ""), str(data.get("username") or "")):
            return False
        return verify_password(str(password or ""), data.get("password"))

    def change_password(self, old_password: str, new_password: str) -> str | None:
        """修改密码；成功返回 ``None``，失败返回错误文案。"""
        with self._lock:
            data = self._read()
            if data is None:
                return "后台凭据未初始化"
            if not verify_password(str(old_password or ""), data.get("password")):
                return "原密码不正确"
            error = password_strength_error(str(new_password or ""))
            if error:
                return error
            if hmac.compare_digest(str(old_password), str(new_password)):
                return "新密码不能与原密码相同"
            data["password"] = hash_password(new_password)
            data["must_change_password"] = False
            # 轮换会话密钥：改密后其它设备上的登录立即失效。
            data["session_secret"] = secrets.token_urlsafe(32)
            self._write(data)
            return None

    # --- 会话 -------------------------------------------------------------
    def _secret(self) -> bytes:
        with self._lock:
            data = self._read() or {}
        secret = str(data.get("session_secret") or "")
        if not secret:
            raise AuthConfigError("后台会话密钥缺失，请删除 admin_auth.json 后重启重建")
        return secret.encode("utf-8")

    def _sign(self, payload: str, secret: bytes) -> str:
        return _b64e(hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).digest())

    def issue_session(self) -> str:
        payload = json.dumps(
            {
                "u": self.username(),
                "exp": int(time.time()) + self.session_ttl,
                "n": secrets.token_urlsafe(8),
            },
            separators=(",", ":"),
        )
        encoded = _b64e(payload.encode("utf-8"))
        return f"{encoded}.{self._sign(encoded, self._secret())}"

    def verify_session(self, token: str | None) -> bool:
        raw = str(token or "").strip()
        if not raw or "." not in raw:
            return False
        encoded, _, signature = raw.rpartition(".")
        try:
            secret = self._secret()
        except AuthConfigError:
            return False
        if not hmac.compare_digest(signature, self._sign(encoded, secret)):
            return False
        try:
            payload = json.loads(_b64d(encoded).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return False
        if not isinstance(payload, dict):
            return False
        if int(payload.get("exp") or 0) <= int(time.time()):
            return False
        return hmac.compare_digest(str(payload.get("u") or ""), self.username())

    # --- 登录失败退避 ------------------------------------------------------
    def penalty_delay(self, key: str) -> float:
        """连续失败后的强制等待秒数；前 3 次不惩罚。"""
        with self._lock:
            entry = self._failures.get(key)
        if entry is None:
            return 0.0
        count, last = entry
        if time.time() - last > 900:
            with self._lock:
                self._failures.pop(key, None)
            return 0.0
        if count < 3:
            return 0.0
        return min(0.5 * (2 ** (count - 3)), 8.0)

    def record_failure(self, key: str) -> None:
        with self._lock:
            count = self._failures.get(key, (0, 0.0))[0]
            self._failures[key] = (count + 1, time.time())

    def reset_failures(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
