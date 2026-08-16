import io
import json
import logging
import urllib.request
import urllib.parse
from pathlib import Path
from typing import List, Optional
from PIL import Image, ImageDraw, ImageOps, ImageFilter
from config.settings import settings

logger = logging.getLogger(__name__)

class AssetManager:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.gemini_api_key

    def fetch_real_entity_image(self, query: str) -> Optional[Image.Image]:
        """
        Attempts to search and download a real authentic photo from Wikipedia/Wikimedia.
        Returns PIL Image if found, or None.
        """
        if not query or len(query.strip()) < 3:
            return None

        # Clean query
        clean_query = query.replace("photo of ", "").replace("picture of ", "").replace("historic ", "").strip()
        search_terms = [clean_query, clean_query.split()[0] if len(clean_query.split()) > 1 else clean_query]

        for term in search_terms:
            try:
                # 1. Search Wikipedia pageimages API
                url = f"https://en.wikipedia.org/w/api.php?action=query&titles={urllib.parse.quote(term)}&prop=pageimages&format=json&pithumbsize=1000"
                req = urllib.request.Request(url, headers={"User-Agent": "TikTokStoryBot/2.0"})
                with urllib.request.urlopen(req, timeout=3) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    pages = data.get("query", {}).get("pages", {})
                    for page_id, page_info in pages.items():
                        if "thumbnail" in page_info:
                            img_url = page_info["thumbnail"]["source"]
                            img_req = urllib.request.Request(img_url, headers={"User-Agent": "TikTokStoryBot/2.0"})
                            with urllib.request.urlopen(img_req, timeout=4) as img_resp:
                                return Image.open(io.BytesIO(img_resp.read())).convert("RGBA")
            except Exception as e:
                logger.debug(f"Wikipedia image search failed for '{term}': {e}")

            try:
                # 2. Search Wikimedia Commons Open API
                url = f"https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrnamespace=6&gsrsearch={urllib.parse.quote(term)}&gsrlimit=1&prop=imageinfo&iiprop=url&iiurlwidth=1000&format=json"
                req = urllib.request.Request(url, headers={"User-Agent": "TikTokStoryBot/2.0"})
                with urllib.request.urlopen(req, timeout=3) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    pages = data.get("query", {}).get("pages", {})
                    for page_id, page_info in pages.items():
                        image_info = page_info.get("imageinfo", [])
                        if image_info and "thumburl" in image_info[0]:
                            img_url = image_info[0]["thumburl"]
                            img_req = urllib.request.Request(img_url, headers={"User-Agent": "TikTokStoryBot/2.0"})
                            with urllib.request.urlopen(img_req, timeout=4) as img_resp:
                                return Image.open(io.BytesIO(img_resp.read())).convert("RGBA")
            except Exception:
                pass

        return None

    def create_floating_card_overlay(
        self,
        query: str,
        output_path: Path,
        video_width: int = 1080,
        video_height: int = 1920
    ) -> Optional[Path]:
        """
        If a real photo is found, creates a sleek 1080x1920 transparent PNG with a floating
        card overlay (rounded corners, drop shadow, white border) in the upper center.
        If no image is found, returns None (clean parkour background).
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        raw_image = self.fetch_real_entity_image(query)
        if not raw_image:
            return None

        card_w, card_h = 760, 560
        corner_radius = 28

        # Resize and center crop raw image into card dimensions
        cropped_img = ImageOps.fit(raw_image, (card_w, card_h), method=Image.Resampling.LANCZOS).convert("RGBA")

        # Create rounded mask
        mask = Image.new("L", (card_w, card_h), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.rounded_rectangle([0, 0, card_w, card_h], radius=corner_radius, fill=255)
        cropped_img.putalpha(mask)

        # Create canvas with drop shadow
        canvas = Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0))
        
        # Position card in upper center (Y: 380 to 940)
        card_x = (video_width - card_w) // 2
        card_y = 400

        # Draw smooth blurred shadow
        shadow_canvas = Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_canvas)
        shadow_draw.rounded_rectangle(
            [card_x + 6, card_y + 12, card_x + card_w + 6, card_y + card_h + 12],
            radius=corner_radius,
            fill=(0, 0, 0, 180)
        )
        shadow_canvas = shadow_canvas.filter(ImageFilter.GaussianBlur(18))
        canvas = Image.alpha_composite(canvas, shadow_canvas)

        # Paste the cropped image
        canvas.paste(cropped_img, (card_x, card_y), cropped_img)

        # Draw crisp card border
        border_draw = ImageDraw.Draw(canvas)
        border_draw.rounded_rectangle(
            [card_x, card_y, card_x + card_w, card_y + card_h],
            radius=corner_radius,
            outline=(255, 255, 255, 220),
            width=5
        )

        canvas.save(output_path, "PNG")
        logger.info(f"Created floating entity card overlay for '{query}': {output_path}")
        return output_path

    def create_ambient_bgm(self, output_path: Path, duration: float = 30.0) -> Path:
        """Synthesizes high quality subtle cinematic drone audio."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        import subprocess
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"anoisesrc=d={duration}:c=pink:r=44100:a=0.015,lowpass=f=220,volume=0.4",
            "-c:a", "aac",
            "-b:a", "192k",
            str(output_path)
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return output_path

    def create_whoosh_sfx(self, output_path: Path) -> Path:
        """Synthesizes subtle whoosh transition sound."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        import subprocess
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "anoisesrc=d=0.35:c=white:r=44100:a=0.03,bandpass=f=800:width_type=h:w=500,volume=0.3",
            "-c:a", "aac",
            "-b:a", "192k",
            str(output_path)
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return output_path
