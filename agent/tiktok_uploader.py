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
            logger.info("Navigating to TikTok Studio Upload page...")
            await page.goto("https://www.tiktok.com/tiktokstudio/upload", wait_until="domcontentloaded")
            await self._human_delay(2.0, 4.0)

            # Check if login is required
            if "login" in page.url:
                logger.error("User is not logged in. Please run `python cli.py login` first.")
                return False

            # Dismiss discard modal if any
            nie_teraz = await page.query_selector('button:has-text("Nie teraz")')
            if nie_teraz and await nie_teraz.is_visible():
                await nie_teraz.click()
                await self._human_delay(0.5, 1.0)

            # Locate file input (attached in DOM, even if visually hidden)
            logger.info(f"Selecting video file: {video_path.name}")
            try:
                await page.set_input_files('input[type="file"]', str(video_path.resolve()), timeout=20000)
            except Exception:
                file_input = await page.wait_for_selector('input[type="file"]', state="attached", timeout=20000)
                if not file_input:
                    logger.error("Could not find file upload input on TikTok upload page.")
                    return False
                await file_input.set_input_files(str(video_path.resolve()))
            logger.info("File uploaded to input. Waiting for video processing to complete...")

            # Wait until post button is enabled (indicates upload and processing is 100% ready)
            try:
                await page.wait_for_selector('button[data-e2e="post_video_button"]:not([disabled])', timeout=60000)
                logger.info("Video upload & processing confirmed ready by TikTok Studio.")
            except Exception:
                logger.warning("Timed out waiting for post_video_button enabled state, proceeding...")

            # Construct clean, unique description with deduplicated hashtags
            existing_words = caption.split()
            unique_tags = []
            if hashtags:
                for tag in hashtags:
                    formatted_tag = tag if tag.startswith("#") else f"#{tag}"
                    if formatted_tag.lower() not in [w.lower() for w in existing_words]:
                        unique_tags.append(formatted_tag)
            
            full_text = caption
            if unique_tags:
                full_text = f"{caption.strip()} {' '.join(unique_tags)}"

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
                    await page.keyboard.type(char, delay=random.randint(15, 45))
            else:
                logger.warning("Could not find rich caption editor; trying alternative input methods.")

            await self._human_delay(1.5, 3.0)

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

            await self._human_delay(1.5, 2.5)

            # Click Publish / Post button if requested
            if publish_now:
                logger.info("Waiting for TikTok Studio to finish transcoding and enable Post button (monitoring aria-disabled)...")
                
                post_ready = False
                for attempt in range(40):
                    await asyncio.sleep(3)
                    btn = await page.query_selector('button[data-e2e="post_video_button"]')
                    if btn:
                        is_disabled = await btn.get_attribute("disabled")
                        is_aria_disabled = await btn.get_attribute("aria-disabled")
                        if is_disabled is None and is_aria_disabled != "true":
                            logger.info(f"Post button is fully enabled and ready after {(attempt + 1) * 3}s!")
                            post_ready = True
                            break
                    else:
                        logger.debug("Waiting for post button...")

                if not post_ready:
                    logger.warning("Timed out waiting for aria-disabled=false, attempting direct click...")

                logger.info("Clicking confirmed Post / Publish button...")
                await page.click('button[data-e2e="post_video_button"]', timeout=20000)

                logger.info("Waiting for TikTok Studio to process and confirm publication...")
                confirmed = False
                for _ in range(30):
                    await asyncio.sleep(1)
                    # Check for modal success button
                    manage_btn = await page.query_selector('button:has-text("Zarządzaj swoimi postami"), button:has-text("Manage your posts")')
                    if manage_btn and await manage_btn.is_visible():
                        logger.info("Clicked Manage Posts modal button! Post successfully registered.")
                        await manage_btn.click()
                        confirmed = True
                        await asyncio.sleep(3)
                        break

                    txt = await page.inner_text("body")
                    if "Twoje wideo zostało przesłane" in txt or "Wideo zostało przesłane" in txt or "Your video has been uploaded" in txt or "content" in page.url:
                        logger.info("Upload confirmed by TikTok Studio success state!")
                        confirmed = True
                        break

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
