import io
import json
import logging
import urllib.request
import urllib.parse
from pathlib import Path
from typing import List, Optional
from PIL import Image, ImageDraw, ImageOps, ImageFilter, ImageStat
from config.settings import settings

logger = logging.getLogger(__name__)

# Specific high-quality verified historical entity images for viral topics
KNOWN_TOPIC_IMAGES = {
    "dyatlov": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Dyatlov_pass_tent.jpg/800px-Dyatlov_pass_tent.jpg",
    "mary celeste": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1f/Mary_Celeste_as_Amazon_in_1861_%28cropped%29.jpg/800px-Mary_Celeste_as_Amazon_in_1861_%28cropped%29.jpg",
    "eldridge": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/USS_Eldridge_%28DE-173%29_underway%2C_circa_in_1944.jpg/800px-USS_Eldridge_%28DE-173%29_underway%2C_circa_in_1944.jpg",
    "philadelphia experiment": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/USS_Eldridge_%28DE-173%29_underway%2C_circa_in_1944.jpg/800px-USS_Eldridge_%28DE-173%29_underway%2C_circa_in_1944.jpg",
    "terracotta": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/86/Terracotta_Army%2C_View_of_Pit_1.jpg/800px-Terracotta_Army%2C_View_of_Pit_1.jpg",
    "china": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/86/Terracotta_Army%2C_View_of_Pit_1.jpg/800px-Terracotta_Army%2C_View_of_Pit_1.jpg",
    "antarctica": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Antarctica_6400px_from_Blue_Marble.jpg/800px-Antarctica_6400px_from_Blue_Marble.jpg",
    "vostok": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Antarctica_6400px_from_Blue_Marble.jpg/800px-Antarctica_6400px_from_Blue_Marble.jpg",
    "wow": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2f/Wow_signal.jpg/800px-Wow_signal.jpg"
}

class AssetManager:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.gemini_api_key

    def _is_image_valid_and_visual(self, img: Image.Image) -> bool:
        """Ensures image is not a pure black/dark spectrogram or blank chart."""
        try:
            grayscale = img.convert("L")
            stat = ImageStat.Stat(grayscale)
            mean_brightness = stat.mean[0]
            std_dev = stat.stddev[0]
            # Must have decent brightness and visual variance (not solid black or flat grey)
            if mean_brightness < 35 or std_dev < 15:
                return False
            return True
        except Exception:
            return False

    def fetch_real_entity_image(self, query: str) -> Optional[Image.Image]:
        """
        Attempts to search and download a real authentic photo from verified links or Wikipedia.
        Returns PIL Image only if it is a genuine, high-contrast, recognizable photo.
        """
        if not query or len(query.strip()) < 3:
            return None

        # Check known verified topics
        q_lower = query.lower()
        for k, url in KNOWN_TOPIC_IMAGES.items():
            if k in q_lower:
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "TikTokStoryBot/2.0"})
                    with urllib.request.urlopen(req, timeout=4) as img_resp:
                        img = Image.open(io.BytesIO(img_resp.read())).convert("RGBA")
                        if self._is_image_valid_and_visual(img):
                            return img
                except Exception:
                    pass

        # Wikipedia Search fallback
        clean_query = query.replace("photo of ", "").replace("picture of ", "").replace("The ", "").strip()
        search_terms = [clean_query]

        for term in search_terms:
            try:
                url = f"https://en.wikipedia.org/w/api.php?action=query&titles={urllib.parse.quote(term)}&prop=pageimages&format=json&pithumbsize=800"
                req = urllib.request.Request(url, headers={"User-Agent": "TikTokStoryBot/2.0"})
                with urllib.request.urlopen(req, timeout=3) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    pages = data.get("query", {}).get("pages", {})
                    for page_id, page_info in pages.items():
                        if "thumbnail" in page_info:
                            img_url = page_info["thumbnail"]["source"]
                            # Ignore audio spectrograms / SVG charts
                            if "bloop.jpg" in img_url.lower() or ".svg" in img_url.lower():
                                continue
                            img_req = urllib.request.Request(img_url, headers={"User-Agent": "TikTokStoryBot/2.0"})
                            with urllib.request.urlopen(img_req, timeout=4) as img_resp:
                                img = Image.open(io.BytesIO(img_resp.read())).convert("RGBA")
                                if self._is_image_valid_and_visual(img):
                                    return img
            except Exception as e:
                logger.debug(f"Image search failed for '{term}': {e}")

        return None

    def create_floating_card_overlay(
        self,
        query: str,
        output_path: Path,
        video_width: int = 1080,
        video_height: int = 1920
    ) -> Optional[Path]:
        """
        Creates a sleek compact 1080x1920 transparent PNG with a floating card overlay
        only when an authentic photo is found. Returns None if no quality image is available.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        raw_image = self.fetch_real_entity_image(query)
        if not raw_image:
            return None

        card_w, card_h = 620, 440
        corner_radius = 24

        # Resize and center crop
        cropped_img = ImageOps.fit(raw_image, (card_w, card_h), method=Image.Resampling.LANCZOS).convert("RGBA")

        # Create rounded mask
        mask = Image.new("L", (card_w, card_h), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.rounded_rectangle([0, 0, card_w, card_h], radius=corner_radius, fill=255)
        cropped_img.putalpha(mask)

        # Transparent canvas
        canvas = Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0))
        
        # Position card in upper center (Y: 420 to 860)
        card_x = (video_width - card_w) // 2
        card_y = 440

        # Draw smooth shadow
        shadow_canvas = Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_canvas)
        shadow_draw.rounded_rectangle(
            [card_x + 4, card_y + 8, card_x + card_w + 4, card_y + card_h + 8],
            radius=corner_radius,
            fill=(0, 0, 0, 160)
        )
        shadow_canvas = shadow_canvas.filter(ImageFilter.GaussianBlur(14))
        canvas = Image.alpha_composite(canvas, shadow_canvas)

        # Paste the image
        canvas.paste(cropped_img, (card_x, card_y), cropped_img)

        # Draw crisp white border
        border_draw = ImageDraw.Draw(canvas)
        border_draw.rounded_rectangle(
            [card_x, card_y, card_x + card_w, card_y + card_h],
            radius=corner_radius,
            outline=(255, 255, 255, 240),
            width=4
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
