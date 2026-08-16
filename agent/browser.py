import logging
from pathlib import Path
from typing import Tuple
from playwright.async_api import async_playwright, BrowserContext, Page
from playwright_stealth import Stealth
from config.settings import settings

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

class BrowserManager:
    def __init__(self, session_dir: Path = None, headless: bool = None):
        self.session_dir = session_dir or settings.tiktok_session_dir
        self.headless = headless if headless is not None else settings.headless
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = None
        self._context = None

    async def get_stealth_context(self) -> Tuple[BrowserContext, Page]:
        """
        Creates or resumes a persistent browser context with stealth modifications
        to prevent bot detection and preserve cookies / TikTok logins.
        """
        self._playwright = await async_playwright().start()
        
        args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-infobars",
            "--window-position=0,0",
            "--ignore-certifcate-errors",
            "--ignore-certifcate-errors-spki-list",
            "--disable-accelerated-2d-canvas",
            "--disable-gpu",
        ]

        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.session_dir),
            channel="chrome",
            headless=self.headless,
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 800},
            device_scale_factor=1,
            has_touch=False,
            is_mobile=False,
            args=args,
            locale="pl-PL",
            timezone_id="Europe/Warsaw",
        )

        pages = self._context.pages
        page = pages[0] if pages else await self._context.new_page()

        # Apply stealth patches
        stealth = Stealth()
        await stealth.apply_stealth_async(page)

        return self._context, page

    async def close(self):
        if self._context:
            await self._context.close()
        if self._playwright:
            await self._playwright.stop()
