"""后台账号与会话认证的行为测试（R-04）。

这里测的是真实的 ``AdminAuth``：密码哈希、会签会话、失败退避、改密轮换。
其余后台测试用 ``FakeAuth`` 替身，只能验证路由接线，验证不了安全性。
"""

from __future__ import annotations

import importlib
import json
import sys
import time
import types
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pytest
from fastapi.testclient import TestClient


PACKAGE_NAME = "admin_auth_test_package"
PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "nonebot_plugin_xiuxian_signin"
if PACKAGE_NAME not in sys.modules:
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(PACKAGE_ROOT)]  # type: ignore[attr-defined]
    package.__package__ = PACKAGE_NAME
    sys.modules[PACKAGE_NAME] = package

admin_auth = importlib.import_module(f"{PACKAGE_NAME}.admin_auth")
admin = importlib.import_module(f"{PACKAGE_NAME}.admin")

AdminAuth = admin_auth.AdminAuth
AuthConfigError = admin_auth.AuthConfigError
SESSION_COOKIE_NAME = admin_auth.SESSION_COOKIE_NAME
MIN_PASSWORD_LENGTH = admin_auth.MIN_PASSWORD_LENGTH
STRONG = "Correct-Horse-Battery-9"


def _auth(tmp: str, **kwargs: Any) -> AdminAuth:
    return AdminAuth(Path(tmp), **kwargs)


def test_bootstrap_generates_password_once_and_requires_change() -> None:
    with TemporaryDirectory() as tmp:
        auth = _auth(tmp)
        generated = auth.ensure_initialized()

        assert generated is not None
        assert len(generated) >= MIN_PASSWORD_LENGTH
        assert auth.must_change_password() is True
        assert auth.authenticate(auth.username(), generated) is True
        # 二次调用不得再生成，也不得再回显明文
        assert auth.ensure_initialized() is None
        # 明文绝不落盘
        assert generated not in (Path(tmp) / admin_auth.AUTH_FILE_NAME).read_text(encoding="utf-8")


def test_env_password_overrides_generated_and_skips_forced_change() -> None:
    with TemporaryDirectory() as tmp:
        auth = _auth(tmp, env_username="keeper", env_password=STRONG)
        assert auth.ensure_initialized() is None
        assert auth.username() == "keeper"
        assert auth.must_change_password() is False
        assert auth.authenticate("keeper", STRONG) is True


def test_env_password_below_policy_is_rejected() -> None:
    with TemporaryDirectory() as tmp:
        auth = _auth(tmp, env_password="short")
        with pytest.raises(AuthConfigError):
            auth.ensure_initialized()


@pytest.mark.parametrize(
    "password,expected",
    [
        ("short", "长度"),
        ("a" * 20, "单一"),
        ("admin", "长度"),
        ("Correct-Horse-Battery-9", None),
    ],
)
def test_password_policy(password: str, expected: str | None) -> None:
    message = admin_auth.password_strength_error(password)
    if expected is None:
        assert message is None
    else:
        assert message is not None and expected in message


def test_authenticate_rejects_wrong_user_and_password() -> None:
    with TemporaryDirectory() as tmp:
        auth = _auth(tmp, env_password=STRONG)
        auth.ensure_initialized()
        assert auth.authenticate("admin", "wrong-password-000000") is False
        assert auth.authenticate("root", STRONG) is False
        assert auth.authenticate("", "") is False


def test_session_round_trip_and_tampering() -> None:
    with TemporaryDirectory() as tmp:
        auth = _auth(tmp, env_password=STRONG)
        auth.ensure_initialized()
        token = auth.issue_session()

        assert auth.verify_session(token) is True
        assert auth.verify_session("") is False
        assert auth.verify_session("garbage") is False
        # 改动签名即失效
        payload, _, signature = token.rpartition(".")
        assert auth.verify_session(f"{payload}.{signature[:-2]}AB") is False
        # 改动载荷也失效
        assert auth.verify_session(f"{signature}.{payload}") is False


def test_expired_session_is_rejected() -> None:
    with TemporaryDirectory() as tmp:
        auth = _auth(tmp, env_password=STRONG, session_ttl=-1)
        auth.ensure_initialized()
        assert auth.verify_session(auth.issue_session()) is False


def test_change_password_rotates_session_secret() -> None:
    with TemporaryDirectory() as tmp:
        auth = _auth(tmp, env_password=STRONG)
        auth.ensure_initialized()
        old_session = auth.issue_session()

        assert auth.change_password("wrong-old-password-1", STRONG) == "原密码不正确"
        assert auth.change_password(STRONG, "abc") is not None
        assert auth.change_password(STRONG, STRONG) is not None
        assert auth.change_password(STRONG, "Another-Strong-Pass-77") is None

        # 改密后旧会话立即失效，即使用同一个密钥文件
        assert auth.verify_session(old_session) is False
        assert auth.authenticate("admin", "Another-Strong-Pass-77") is True
        assert auth.authenticate("admin", STRONG) is False


def test_login_penalty_backs_off_after_repeated_failures() -> None:
    with TemporaryDirectory() as tmp:
        auth = _auth(tmp, env_password=STRONG)
        auth.ensure_initialized()
        for _ in range(2):
            auth.record_failure("1.2.3.4")
        # 前 3 次尝试不惩罚
        assert auth.penalty_delay("1.2.3.4") == 0.0
        auth.record_failure("1.2.3.4")
        assert auth.penalty_delay("1.2.3.4") == pytest.approx(0.5)
        auth.record_failure("1.2.3.4")
        assert auth.penalty_delay("1.2.3.4") == pytest.approx(1.0)
        assert auth.penalty_delay("5.6.7.8") == 0.0
        auth.reset_failures("1.2.3.4")
        assert auth.penalty_delay("1.2.3.4") == 0.0


class _StubManager:
    """只暴露登录相关端点所需的成员，避免拉起整份领域层。"""

    def __init__(self, auth: AdminAuth) -> None:
        self.auth = auth

    def dashboard_payload(self) -> dict[str, Any]:
        return {"ok": True}


def test_login_endpoint_sets_httponly_cookie_and_gates_api() -> None:
    with TemporaryDirectory() as tmp:
        auth = AdminAuth(Path(tmp), env_password=STRONG)
        auth.ensure_initialized()
        app = admin.create_admin_app(manager=_StubManager(auth), base_path="/xiuxian-admin")

        anonymous = TestClient(app)
        assert anonymous.get("/xiuxian-admin/api/dashboard").status_code == 401
        assert anonymous.post(
            "/xiuxian-admin/api/login",
            json={"username": "admin", "password": "nope"},
        ).status_code == 401

        login = anonymous.post(
            "/xiuxian-admin/api/login",
            json={"username": "admin", "password": STRONG},
        )
        assert login.status_code == 200
        cookie_header = login.headers["set-cookie"]
        assert "HttpOnly" in cookie_header
        assert "SameSite=lax" in cookie_header.replace("samesite=lax", "SameSite=lax") or "samesite=lax" in cookie_header

        # 登录后同一客户端自动携带 Cookie
        assert anonymous.get("/xiuxian-admin/api/dashboard").status_code == 200
        session = anonymous.get("/xiuxian-admin/api/session").json()
        assert session["authenticated"] is True
        assert session["must_change_password"] is False

        assert anonymous.post("/xiuxian-admin/api/logout").status_code == 200
        assert anonymous.get("/xiuxian-admin/api/dashboard").status_code == 401


def test_forced_password_change_blocks_other_apis() -> None:
    with TemporaryDirectory() as tmp:
        auth = AdminAuth(Path(tmp))  # 随机生成 → 必须改密
        password = auth.ensure_initialized()
        assert password is not None
        app = admin.create_admin_app(manager=_StubManager(auth), base_path="/xiuxian-admin")
        client = TestClient(app)

        login = client.post(
            "/xiuxian-admin/api/login",
            json={"username": "admin", "password": password},
        )
        assert login.status_code == 200
        assert login.json()["must_change_password"] is True

        blocked = client.get("/xiuxian-admin/api/dashboard")
        assert blocked.status_code == 403
        assert blocked.json()["error"] == "must_change_password"

        changed = client.post(
            "/xiuxian-admin/api/password",
            json={"old_password": password, "new_password": "Another-Strong-Pass-77"},
        )
        assert changed.status_code == 200
        assert client.get("/xiuxian-admin/api/dashboard").status_code == 200


def test_no_plaintext_password_in_session_cookie() -> None:
    with TemporaryDirectory() as tmp:
        auth = AdminAuth(Path(tmp), env_password=STRONG)
        auth.ensure_initialized()
        token = auth.issue_session()
        assert STRONG not in token
        assert auth.username() in admin_auth._b64d(token.split(".")[0]).decode("utf-8")


def test_session_expiry_field_is_present() -> None:
    with TemporaryDirectory() as tmp:
        auth = AdminAuth(Path(tmp), env_password=STRONG, session_ttl=60)
        auth.ensure_initialized()
        payload = json.loads(admin_auth._b64d(auth.issue_session().split(".")[0]).decode("utf-8"))
        assert payload["exp"] - int(time.time()) <= 60
