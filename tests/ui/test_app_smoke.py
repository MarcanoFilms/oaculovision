"""Headless smoke tests for multi-screen navigation."""

from __future__ import annotations

import asyncio

from oraculovision.config import AppConfig
from oraculovision.ui.app import SovereignApp


def test_sovereign_app_mounts_all_screens() -> None:
    app = SovereignApp(config=AppConfig())

    async def _exercise() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            for key in "12345678":
                await pilot.press(key)
            await pilot.pause()
            switcher = app.query_one("#screen-switcher")
            assert switcher.current in {
                "dashboard",
                "policies",
                "mempool_glass",
                "block_explorer",
                "tx_inspector",
                "spam_health",
                "mining",
                "node_control",
            }

    asyncio.run(_exercise())