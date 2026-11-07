"""共享 HTTP 客户端与头像缓存（R-13）。

签到/垂钓/日历/切磋每个面板都要拉 QQ 头像；原先每次渲染都新建
``httpx.AsyncClient``（一次 TCP+TLS 握手）并重新下载同一张头像。
这里收敛为：进程级共享客户端（on_shutdown 关闭）+ 带 TTL 的字节 LRU。
"""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Optional

import httpx
from nonebot import logger

from .state import config

_shared_http_client: Optional[httpx.AsyncClient] = None
_AVATAR_CACHE_TTL_SECONDS = 3600.0
_AVATAR_CACHE_MAX_ENTRIES = 200
_avatar_cache: OrderedDict[str, tuple[float, bytes]] = OrderedDict()


def get_shared_http_client() -> httpx.AsyncClient:
    global _shared_http_client
    if _shared_http_client is None or _shared_http_client.is_closed:
        _shared_http_client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=config.xiuxian_signin_avatar_timeout,
        )
    return _shared_http_client


async def close_shared_http_client() -> None:
    global _shared_http_client
    if _shared_http_client is not None and not _shared_http_client.is_closed:
        await _shared_http_client.aclose()
    _shared_http_client = None


def _avatar_cache_get(user_id: str) -> Optional[bytes]:
    entry = _avatar_cache.get(user_id)
    if entry is None:
        return None
    fetched_at, payload = entry
    if time.monotonic() - fetched_at > _AVATAR_CACHE_TTL_SECONDS:
        _avatar_cache.pop(user_id, None)
        return None
    _avatar_cache.move_to_end(user_id)
    return payload


def _avatar_cache_put(user_id: str, payload: bytes) -> None:
    _avatar_cache[user_id] = (time.monotonic(), payload)
    _avatar_cache.move_to_end(user_id)
    while len(_avatar_cache) > _AVATAR_CACHE_MAX_ENTRIES:
        _avatar_cache.popitem(last=False)


async def fetch_avatar(user_id: str) -> Optional[bytes]:
    cached = _avatar_cache_get(user_id)
    if cached is not None:
        return cached
    url = f"https://q1.qlogo.cn/g?b=qq&nk={user_id}&s=640"
    try:
        client = get_shared_http_client()
        response = await client.get(url)
        if response.status_code == 200 and response.content:
            _avatar_cache_put(user_id, response.content)
            return response.content
    except Exception as exc:
        logger.debug(f"获取 QQ 头像失败: {exc}")
    return None
