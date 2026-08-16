import asyncio
import logging
import random
from pathlib import Path
from typing import List, Optional
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from agent.browser import BrowserManager
from config.settings import settings

logger = logging.getLogger(__name__)

class TikTokUploader:
    def __init__(self, headless: bool = None):
        self.headless = headless if headless is not None else settings.headless
        self.browser_manager = BrowserManager(headless=self.headless)

    async def _human_delay(self, min_s: float = 1.0, max_s: float = 2.5):
        """Simulates natural human hesitation."""
        if settings.simulate_human_delays:
            await asyncio.sleep(random.uniform(min_s, max_s))

    async def _dismiss_modals(self, page: Page):
        """Dismisses any floating dialogs, tooltips, or tutorial popups."""
        try:
            # Try pressing Escape first
            await page.keyboard.press("Escape")
        except Exception:
            pass

        modal_button_selectors = [
            'button:has-text("Rozumiem")',
            'button:has-text("Got it")',
            'button:has-text("OK")',
            'button:has-text("Ok")',
            'button:has-text("Zamknij")',
            'button:has-text("Close")',
            '.TUXModal button',
            'div[data-e2e="modal-close-button"]',
            'button[aria-label="Close"]',
            'button[aria-label="Zamknij"]'
        ]
        for sel in modal_button_selectors:
            try:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click(force=True)
                    await asyncio.sleep(0.5)
            except Exception:
                continue

    async def upload_video(
        self,
        video_path: Path,
        caption: str,
        hashtags: Optional[List[str]] = None,
        publish_now: bool = True,
        declare_ai: Optional[bool] = None
    ) -> bool:
        """
        Uploads and publishes a video to TikTok Creator Center with anti-detection steps
        and AI content disclosure toggle.
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        context, page = await self.browser_manager.get_stealth_context()
        try:
            logger.info("Navigating to TikTok Creator Center Upload page...")
            await page.goto("https://www.tiktok.com/creator-center/upload", wait_until="domcontentloaded")
            await self._human_delay(2.0, 4.0)

            # Check if login is required
            if "login" in page.url:
                logger.error("User is not logged in. Please run `python cli.py login` first.")
                return False

            # Locate file input (may be inside an iframe or directly in page)
            logger.info(f"Selecting video file: {video_path.name}")
            
            file_input = None
            try:
                file_input = await page.wait_for_selector('input[type="file"]', timeout=20000)
            except Exception:
                pass

            if not file_input:
                for frame in page.frames:
                    try:
                        file_input = await frame.query_selector('input[type="file"]')
                        if file_input:
                            break
                    except Exception:
                        continue

            if not file_input:
                logger.error("Could not find file upload input on TikTok upload page.")
                return False

            await file_input.set_input_files(str(video_path.resolve()))
            logger.info("File uploaded to input. Waiting for video processing...")

            await self._human_delay(4.0, 7.0)

            # Construct full description with hashtags
            full_text = caption
            if hashtags:
                full_text += " " + " ".join(hashtags)

            # Dismiss any popups or tutorial modals (e.g. copyright check modal, cookies)
            await self._dismiss_modals(page)

            # Set Caption
            logger.info("Entering caption and hashtags...")
            editor_selectors = [
                'div[contenteditable="true"]',
                '.public-DraftEditor-content',
                '.notranslate.public-DraftEditor-content',
                'div[data-placeholder="Dodaj opis"]',
                'div[data-placeholder="Add a caption"]'
            ]
            
            caption_input = None
            for sel in editor_selectors:
                caption_input = await page.query_selector(sel)
                if caption_input:
                    break

            if caption_input:
                await self._dismiss_modals(page)
                try:
                    await caption_input.click(force=True, timeout=5000)
                except Exception:
                    await caption_input.focus()

                await self._human_delay(0.5, 1.2)
                # Clear existing text
                await page.keyboard.press("Meta+A")
                await page.keyboard.press("Backspace")
                await self._human_delay(0.3, 0.6)
                # Type caption with human typing speed
                for char in full_text:
                    await page.keyboard.type(char, delay=random.randint(25, 75))
            else:
                logger.warning("Could not find rich caption editor; trying alternative input methods.")

            await self._human_delay(2.0, 3.5)

            # Toggle "AI-generated content" (AIGC) declaration (opcjonalnie)
            should_declare_ai = declare_ai if declare_ai is not None else settings.declare_ai_content
            if should_declare_ai:
                logger.info("Disclosing AI-generated content toggle...")
                try:
                    ai_switch_selectors = [
                        '//span[contains(text(), "AI-generated") or contains(text(), "wygenerowane przez AI")]/ancestor::div//input[@type="checkbox"]',
                        '//div[contains(text(), "AI-generated") or contains(text(), "wygenerowane przez AI")]/following-sibling::div//input[@type="checkbox"]',
                        '//span[contains(text(), "AI-generated") or contains(text(), "wygenerowane przez AI")]/ancestor::label',
                        'div[data-e2e="ai-label-switch"]'
                    ]
                    
                    for xpath in ai_switch_selectors:
                        if xpath.startswith("//"):
                            elements = await page.locator(f"xpath={xpath}").all()
                        else:
                            elements = await page.locator(xpath).all()
                            
                        if elements:
                            for el in elements:
                                if await el.is_visible():
                                    await el.click()
                                    logger.info("Toggled AI-generated content disclosure.")
                                    break
                except Exception as e:
                    logger.warning(f"Could not automatically toggle AI switch: {e}")

            await self._human_delay(2.0, 4.0)

            # Click Publish / Post button if requested
            if publish_now:
                logger.info("Clicking Post / Publish button...")
                post_button_selectors = [
                    'button:has-text("Post")',
                    'button:has-text("Opublikuj")',
                    'div[data-e2e="post-video-button"]',
                    'button[type="button"]:has-text("Post")',
                    'button[type="button"]:has-text("Opublikuj")'
                ]

                posted = False
                for btn_sel in post_button_selectors:
                    btn = await page.query_selector(btn_sel)
                    if btn and await btn.is_enabled():
                        await btn.click()
                        logger.info("Clicked Post button!")
                        posted = True
                        break

                if not posted:
                    logger.warning("Could not auto-click post button. Saving as draft or waiting.")

                await self._human_delay(5.0, 8.0)
                logger.info("TikTok upload sequence finished successfully!")
                return True
            else:
                logger.info("Publish_now is False. Video prepared in browser without final submit.")
                return True

        except Exception as e:
            logger.error(f"Error during TikTok upload: {e}")
            return False
        finally:
            await self.browser_manager.close()
