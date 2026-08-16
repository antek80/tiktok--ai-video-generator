import asyncio
import logging
from pathlib import Path
from agent.browser import BrowserManager
from config.settings import settings

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self, session_dir: Path = None):
        self.session_dir = session_dir or settings.tiktok_session_dir
        self.browser_manager = BrowserManager(session_dir=self.session_dir, headless=False)

    async def login_interactively(self):
        """
        Opens a headful stealth browser window for the user to log in to TikTok (QR code / credentials).
        Waits until login is detected and cookies are stored.
        """
        logger.info("Opening browser for TikTok login...")
        context, page = await self.browser_manager.get_stealth_context()

        try:
            await page.goto("https://www.tiktok.com/login", wait_until="domcontentloaded")
            print("\n=======================================================")
            print("👉 Zaloguj się na swoje konto TikTok w otwartym oknie.")
            print("Możesz użyć kodu QR w aplikacji TikTok na telefonie.")
            print("Po zalogowaniu sesja zostanie zapisana automatycznie.")
            print("=======================================================\n")

            # Wait for user to navigate to feed or profile
            while True:
                current_url = page.url
                # If URL changed to fyp, upload or profile, user is logged in
                if "login" not in current_url and ("tiktok.com/@" in current_url or "creator-center" in current_url or "foryou" in current_url or "following" in current_url):
                    print("✅ Zalogowano pomyślnie! Zapisuję profil sesji...")
                    await page.wait_for_timeout(3000)
                    break
                await page.wait_for_timeout(1000)

        finally:
            await self.browser_manager.close()

    async def is_logged_in(self) -> bool:
        """Checks if active session is still authenticated."""
        bm = BrowserManager(session_dir=self.session_dir, headless=True)
        context, page = await bm.get_stealth_context()
        try:
            await page.goto("https://www.tiktok.com/creator-center/upload", wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            logged_in = "login" not in page.url
            return logged_in
        except Exception:
            return False
        finally:
            await bm.close()
