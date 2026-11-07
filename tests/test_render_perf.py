"""R-13：渲染线程化、字体/背景缓存与头像 LRU 的回归测试。"""

from __future__ import annotations

import asyncio
import os
import tempfile
import time
import unittest
from pathlib import Path

import httpx
from PIL import Image, ImageChops

from nonebot_plugin_xiuxian_signin.cards import (
    _PANEL_BACKGROUND_CACHE,
    load_font,
    load_panel_background,
    render_in_thread,
    set_font_paths,
)
from nonebot_plugin_xiuxian_signin.net import (
    _AVATAR_CACHE_MAX_ENTRIES,
    _avatar_cache,
    close_shared_http_client,
    fetch_avatar,
)


class FontCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        set_font_paths(None, None)

    def test_load_font_cached_identity(self) -> None:
        first = load_font(24)
        second = load_font(24)
        self.assertIs(first, second, "同参数二次 load_font 必须命中缓存")

    def test_set_font_paths_clears_cache(self) -> None:
        first = load_font(24)
        set_font_paths(None, None)
        second = load_font(24)
        self.assertIsNot(first, second, "set_font_paths 后缓存必须失效重建")

    def test_different_sizes_get_separate_fonts(self) -> None:
        small = load_font(20)
        large = load_font(36)
        self.assertIsNot(small, large)


class PanelBackgroundCacheTests(unittest.TestCase):
    def tearDown(self) -> None:
        _PANEL_BACKGROUND_CACHE.clear()

    def test_cache_returns_copies_with_identical_pixels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bg.png"
            Image.new("RGBA", (1200, 900), (200, 100, 50, 255)).save(path)

            first, used = load_panel_background(path, 450, 600, "#3589d8")
            self.assertTrue(used)
            second, _ = load_panel_background(path, 450, 600, "#3589d8")
            self.assertIsNot(first, second, "缓存必须返回副本，防止调用方互相涂改")
            self.assertIsNone(ImageChops.difference(first.convert("RGB"), second.convert("RGB")).getbbox())

    def test_mtime_change_invalidates_cache_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bg.png"
            Image.new("RGBA", (600, 600), (10, 200, 30, 255)).save(path)
            load_panel_background(path, 300, 300, "#3589d8")
            self.assertEqual(len(_PANEL_BACKGROUND_CACHE), 1)

            stat = path.stat()
            os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
            load_panel_background(path, 300, 300, "#3589d8")
            self.assertEqual(
                len(_PANEL_BACKGROUND_CACHE),
                2,
                "mtime 变化（如资源包重新下载）必须产生新缓存键",
            )

    def test_missing_file_falls_back_to_placeholder(self) -> None:
        image, used = load_panel_background(Path("Z:/definitely/missing/bg.png"), 200, 300, "#3589d8")
        self.assertFalse(used)
        self.assertEqual(image.size, (200, 300))


class RenderThreadTests(unittest.TestCase):
    def test_event_loop_stays_responsive_during_render(self) -> None:
        async def scenario() -> tuple[float, str]:
            loop = asyncio.get_running_loop()

            def slow_render() -> str:
                time.sleep(0.3)
                return "done"

            started = loop.time()
            task = asyncio.create_task(render_in_thread(slow_render))
            await asyncio.sleep(0.05)
            ticked_at = loop.time() - started
            result = await asyncio.wait_for(task, timeout=5)
            return ticked_at, result

        ticked_at, result = asyncio.run(scenario())
        self.assertLess(ticked_at, 0.2, "渲染期间事件循环必须保持可调度")
        self.assertEqual(result, "done")

    def test_render_in_thread_passes_args_and_kwargs(self) -> None:
        async def scenario() -> tuple[int, int]:
            return await asyncio.gather(
                render_in_thread(lambda a, b: a + b, 2, b=3),
                render_in_thread(lambda a, b: a * b, 4, 5),
            )

        total, product = asyncio.run(scenario())
        self.assertEqual((total, product), (5, 20))


class AvatarCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        _avatar_cache.clear()

    def tearDown(self) -> None:
        _avatar_cache.clear()

    def test_cache_hit_and_ttl_expiry(self) -> None:
        import nonebot_plugin_xiuxian_signin.net as net

        net._avatar_cache_put("10000", b"img")
        self.assertEqual(net._avatar_cache_get("10000"), b"img")

        fetched_at, payload = net._avatar_cache["10000"]
        net._avatar_cache["10000"] = (fetched_at - 7200.0, payload)
        self.assertIsNone(net._avatar_cache_get("10000"), "超过 TTL 的头像必须视为过期")

    def test_cache_eviction_respects_cap(self) -> None:
        import nonebot_plugin_xiuxian_signin.net as net

        for index in range(_AVATAR_CACHE_MAX_ENTRIES + 50):
            net._avatar_cache_put(str(index), b"x")
        self.assertEqual(len(_avatar_cache), _AVATAR_CACHE_MAX_ENTRIES)
        self.assertNotIn("0", _avatar_cache, "最旧的头像必须被淘汰")
        self.assertIn(str(_AVATAR_CACHE_MAX_ENTRIES + 49), _avatar_cache)

    def test_fetch_avatar_reuses_client_and_cache(self) -> None:
        import nonebot_plugin_xiuxian_signin.net as net

        calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            return httpx.Response(200, content=b"avatar-bytes")

        async def scenario() -> tuple[bytes, bytes]:
            net._shared_http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            return await fetch_avatar("20000"), await fetch_avatar("20000")

        first, second = asyncio.run(scenario())
        self.assertEqual(first, b"avatar-bytes")
        self.assertEqual(second, b"avatar-bytes")
        self.assertEqual(calls["n"], 1, "第二次 fetch_avatar 必须命中缓存，不再发请求")
        asyncio.run(close_shared_http_client())
        self.assertIsNone(net._shared_http_client)


if __name__ == "__main__":
    unittest.main()
