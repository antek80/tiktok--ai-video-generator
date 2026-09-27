import io
import json
import logging
import re
import urllib.request
import urllib.parse
from pathlib import Path
from typing import List, Optional
from PIL import Image, ImageDraw, ImageOps, ImageFilter, ImageStat, ImageFont
from config.settings import settings

logger = logging.getLogger(__name__)

_STOPWORDS = {
    "the", "in", "on", "at", "a", "an", "of", "to", "for", "and", "but", "or",
    "is", "are", "was", "were", "this", "that", "it", "its", "as", "by", "with",
    "from", "their", "his", "her", "over", "into", "after", "before", "when",
    "while", "than", "then", "some", "even", "still", "yet", "if", "so"
}

# Verified Wikipedia article titles for high-confidence viral topics.
# Resolved to a live thumbnail via the REST summary API at fetch time, since
# hardcoded Wikimedia thumbnail URLs go stale when their allowed sizes change.
KNOWN_TOPIC_PAGES = {
    "dyatlov": "Dyatlov Pass incident",
    "mary celeste": "Mary Celeste",
    "eldridge": "USS Eldridge",
    "philadelphia experiment": "Philadelphia Experiment",
    "terracotta": "Terracotta Army",
    "china": "Terracotta Army",
    "antarctica": "Lake Vostok",
    "vostok": "Lake Vostok",
    "wow": "Wow! signal"
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

    def _fetch_wikipedia_page_thumbnail(self, page_title: str) -> Optional[Image.Image]:
        """Resolves a known Wikipedia page title to its current thumbnail via the REST summary API."""
        try:
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(page_title)}"
            req = urllib.request.Request(url, headers={"User-Agent": "TikTokStoryBot/2.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                img_url = data.get("thumbnail", {}).get("source")
                if not img_url:
                    return None
                img_req = urllib.request.Request(img_url, headers={"User-Agent": "TikTokStoryBot/2.0"})
                with urllib.request.urlopen(img_req, timeout=4) as img_resp:
                    img = Image.open(io.BytesIO(img_resp.read())).convert("RGBA")
                    if self._is_image_valid_and_visual(img):
                        return img
        except Exception as e:
            logger.debug(f"Known-topic thumbnail fetch failed for '{page_title}': {e}")
        return None

    def _extract_entity_phrases(self, text: str) -> List[str]:
        """
        Pulls likely proper-noun phrases (e.g. "USS Eldridge", "Philadelphia") out of a
        single narration sentence, longest/most-specific first, so a photo search can be
        matched to what is actually said in that moment instead of the video's topic.
        """
        if not text:
            return []
        words = re.findall(r"[A-Za-z0-9'\-]+", text)
        phrases: List[str] = []
        current: List[str] = []
        for w in words:
            if w[0].isupper() and w.lower() not in _STOPWORDS:
                current.append(w)
            else:
                if current:
                    phrases.append(" ".join(current))
                    current = []
        if current:
            phrases.append(" ".join(current))
        phrases = [p for p in phrases if len(p) > 3]
        phrases.sort(key=len, reverse=True)
        return phrases

    def fetch_scene_matched_image(self, narration: str) -> Optional[Image.Image]:
        """
        Tries to find a real photo matching the SPECIFIC entity/moment mentioned in one
        scene's narration (e.g. "USS Eldridge" for a Philadelphia Experiment scene about
        the ship), rather than a generic topic-wide photo. Returns None if nothing in the
        sentence resolves to a real, verifiable photo.
        """
        for phrase in self._extract_entity_phrases(narration)[:3]:
            img = self.fetch_real_entity_image(phrase)
            if img:
                return img
        return None

    def _resolve_known_page_title(self, query: str) -> Optional[str]:
        """Maps a free-text query onto a verified Wikipedia article title, if recognized."""
        q_lower = query.lower()
        for k, page_title in KNOWN_TOPIC_PAGES.items():
            if k in q_lower:
                return page_title
        return None

    @staticmethod
    def _is_relevant_title(query: str, page_title: str) -> bool:
        """
        True when the search hit's article title shares a meaningful word with the query.
        Full-text search always returns *something* with an image — without this check a
        phrase like "This Cosmic" lands on a scanned 19th-century book cover.
        """
        def words(s: str) -> set:
            return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if len(w) > 2 and w not in _STOPWORDS}
        return bool(words(query) & words(page_title))

    def fetch_real_entity_image(self, query: str, exact_title: bool = False) -> Optional[Image.Image]:
        """
        Attempts to search and download a real authentic photo from verified links or Wikipedia.
        Returns PIL Image only if it is a genuine, high-contrast, recognizable photo.
        With exact_title, `query` is treated as a Wikipedia article title and tried directly first.
        """
        if not query or len(query.strip()) < 3:
            return None

        if exact_title:
            img = self._fetch_wikipedia_page_thumbnail(query.strip())
            if img:
                return img

        # Check known verified topics
        known_title = self._resolve_known_page_title(query)
        if known_title:
            img = self._fetch_wikipedia_page_thumbnail(known_title)
            if img:
                return img

        # Wikipedia full-text search fallback (finds the best-matching page instead of
        # requiring the query to be an exact article title).
        clean_query = query.replace("photo of ", "").replace("picture of ", "").replace("The ", "").strip()
        if not clean_query:
            return None

        try:
            url = (
                "https://en.wikipedia.org/w/api.php?action=query&generator=search"
                f"&gsrsearch={urllib.parse.quote(clean_query)}&gsrlimit=3"
                "&prop=pageimages&piprop=thumbnail&pithumbsize=800&format=json"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "TikTokStoryBot/2.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                pages = data.get("query", {}).get("pages", {})
                for page_id, page_info in pages.items():
                    if not self._is_relevant_title(clean_query, page_info.get("title", "")):
                        logger.debug(f"Skipping unrelated search hit '{page_info.get('title')}' for '{clean_query}'")
                        continue
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
            logger.debug(f"Image search failed for '{clean_query}': {e}")

        return None

    def _download_commons_candidate(self, img_url: str) -> Optional[Image.Image]:
        """Downloads and validates one Commons file URL. Rejects SVG renders (maps/diagrams)."""
        if not img_url or ".svg" in img_url.lower():
            return None
        try:
            req = urllib.request.Request(img_url, headers={"User-Agent": "TikTokStoryBot/2.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                img = Image.open(io.BytesIO(resp.read())).convert("RGBA")
                if self._is_image_valid_and_visual(img):
                    return img
        except Exception:
            pass
        return None

    def fetch_entity_image_pool(self, query: str, count: int = 4) -> List[Image.Image]:
        """
        Fetches up to `count` DISTINCT real photos related to the topic from Wikimedia
        Commons, so different scenes in the same video can each show a different image
        instead of the single Wikipedia infobox thumbnail repeated on every card.
        """
        images: List[Image.Image] = []
        if not query or len(query.strip()) < 3:
            return images

        # Prefer the verified article title when recognized — raw marketing titles
        # (e.g. "The Dyatlov Pass Mystery") often contain words absent from any real
        # Commons file/description, which silently zeroes out the search results.
        known_title = self._resolve_known_page_title(query)
        clean_query = known_title or \
            query.replace("photo of ", "").replace("picture of ", "").replace("The ", "").strip()

        candidate_urls: List[str] = []

        # 1. Full-text search across Commons file names/descriptions.
        try:
            url = (
                "https://commons.wikimedia.org/w/api.php?action=query&generator=search"
                f"&gsrsearch={urllib.parse.quote(clean_query)}&gsrnamespace=6&gsrlimit=15"
                "&prop=imageinfo&iiprop=url&iiurlwidth=800&format=json"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "TikTokStoryBot/2.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for page_info in data.get("query", {}).get("pages", {}).values():
                    infos = page_info.get("imageinfo") or []
                    if infos:
                        img_url = infos[0].get("thumburl") or infos[0].get("url")
                        if img_url:
                            candidate_urls.append(img_url)
        except Exception as e:
            logger.debug(f"Commons search failed for '{clean_query}': {e}")

        # 2. Matching Commons category listing — catches real photos that full-text
        # search misses (e.g. non-English file names), when a category of that exact
        # name exists for the topic.
        try:
            cat_title = urllib.parse.quote(f"Category:{clean_query}")
            url = (
                "https://commons.wikimedia.org/w/api.php?action=query&generator=categorymembers"
                f"&gcmtitle={cat_title}&gcmtype=file&gcmlimit=25"
                "&prop=imageinfo&iiprop=url&iiurlwidth=800&format=json"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "TikTokStoryBot/2.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for page_info in data.get("query", {}).get("pages", {}).values():
                    infos = page_info.get("imageinfo") or []
                    if infos:
                        img_url = infos[0].get("thumburl") or infos[0].get("url")
                        if img_url and img_url not in candidate_urls:
                            candidate_urls.append(img_url)
        except Exception as e:
            logger.debug(f"Commons category listing failed for '{clean_query}': {e}")

        for img_url in candidate_urls:
            if len(images) >= count:
                break
            img = self._download_commons_candidate(img_url)
            if img:
                images.append(img)

        return images

    def create_floating_card_overlay(
        self,
        query: str,
        output_path: Path,
        video_width: int = 1080,
        video_height: int = 1920,
        raw_image: Optional[Image.Image] = None
    ) -> Optional[Path]:
        """
        Creates a sleek compact 1080x1920 transparent PNG with a floating card overlay
        only when an authentic photo is found. Returns None if no quality image is available.
        Pass `raw_image` to use an already-fetched photo (e.g. from fetch_entity_image_pool)
        instead of searching again.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        raw_image = raw_image or self.fetch_real_entity_image(query)
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

    def draw_tiktok_heart(self, size: int = 280) -> Image.Image:
        """Draws a clean, official TikTok #FE2C55 vector heart with smooth edges."""
        scale = 3
        s = size * scale
        h_img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        h_draw = ImageDraw.Draw(h_img)
        
        import math
        points = []
        steps = 360
        for i in range(steps):
            t = (i / steps) * 2 * math.pi
            x = 16 * (math.sin(t) ** 3)
            y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
            cx = (s / 2.0) + (x * (s / 38.0))
            cy = (s / 2.0) + (y * (s / 38.0)) + (s * 0.03)
            points.append((cx, cy))
            
        h_draw.polygon(points, fill=(254, 44, 85, 255))
        return h_img.resize((size, size), Image.Resampling.LANCZOS)

    def create_like_outro_overlay(
        self,
        output_dir: Path,
        total_duration: float,
        video_width: int = 1080,
        video_height: int = 1920
    ) -> Path:
        """
        Generates an authentic 2-second TikTok Double-Tap Like Heart animation:
        - Expanding glowing pulse ripple ring
        - Elastic bounce pop-in of vibrant #FE2C55 heart
        - 100% clean vector aesthetics (no artifacts/grey spots)
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        outro_len = 2.0
        fps = 15
        total_frames = int(outro_len * fps)

        blank_png = output_dir / "outro_blank.png"
        Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0)).save(blank_png)

        base_heart = self.draw_tiktok_heart(size=320)
        frames = []

        import math
        for f in range(total_frames):
            progress = f / float(total_frames)
            canvas = Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(canvas)

            center_x = video_width // 2
            center_y = 760

            # 1. Expanding Ripple Ring (Classic Double-Tap effect)
            if progress < 0.55:
                ring_p = progress / 0.55
                ring_r = int(60 + 170 * ring_p)
                ring_alpha = int(240 * (1.0 - ring_p))
                if ring_alpha > 0 and ring_r > 0:
                    draw.ellipse(
                        [center_x - ring_r, center_y - ring_r, center_x + ring_r, center_y + ring_r],
                        outline=(254, 44, 85, ring_alpha),
                        width=6
                    )

            # 2. Heart Scaling with Smooth Pop-in Bounce
            if progress < 0.28:
                p = progress / 0.28
                scale = 0.15 + (1.25 * math.sin(p * math.pi / 2))
                alpha = int(255 * p)
            elif progress < 0.55:
                p = (progress - 0.28) / 0.27
                scale = 1.4 - (0.4 * p)
                alpha = 255
            else:
                p = (progress - 0.55) / 0.45
                scale = 1.0 + (0.05 * math.sin(p * 2 * math.pi))
                alpha = 255

            w = max(10, int(300 * scale))
            h = max(10, int(300 * scale))
            scaled_heart = base_heart.resize((w, h), Image.Resampling.LANCZOS)
            
            hx = center_x - (w // 2)
            hy = center_y - (h // 2)

            # 3. Soft Glowing Shadow
            glow = Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0))
            g_draw = ImageDraw.Draw(glow)
            g_draw.ellipse([hx - 25, hy - 25, hx + w + 25, hy + h + 25], fill=(254, 44, 85, int(90 * (alpha / 255.0))))
            glow = glow.filter(ImageFilter.GaussianBlur(30))
            canvas = Image.alpha_composite(canvas, glow)

            # 4. Composite Clean Heart
            canvas.paste(scaled_heart, (hx, hy), scaled_heart)

            # 5. Render Animated CTA Text on the final canvas (No missing glyph boxes!)
            final_draw = ImageDraw.Draw(canvas)
            try:
                font_path = "/System/Library/Fonts/Supplemental/Impact.ttf"
                cta_font = ImageFont.truetype(font_path, 50) if Path(font_path).exists() else ImageFont.load_default()
            except Exception:
                cta_font = ImageFont.load_default()

            text_line1 = "PLEASE LIKE THE VIDEO"
            text_line2 = "TO SUPPORT MY WORK"
            
            w1 = final_draw.textlength(text_line1, font=cta_font)
            w2 = final_draw.textlength(text_line2, font=cta_font)
            
            # Mini vector heart next to the yellow text line
            mini_heart_size = 46
            mini_heart = self.draw_tiktok_heart(size=mini_heart_size)
            
            total_w2 = w2 + mini_heart_size + 12
            tx1 = (video_width - w1) // 2
            tx2 = int((video_width - total_w2) // 2)
            ty = 960

            # Shadow for CTA
            final_draw.text((tx1 + 4, ty + 4), text_line1, font=cta_font, fill=(0, 0, 0, alpha), stroke_fill=(0, 0, 0, alpha), stroke_width=8)
            final_draw.text((tx2 + 4, ty + 64 + 4), text_line2, font=cta_font, fill=(0, 0, 0, alpha), stroke_fill=(0, 0, 0, alpha), stroke_width=8)

            # Main CTA Text
            final_draw.text((tx1, ty), text_line1, font=cta_font, fill=(255, 255, 255, alpha), stroke_fill=(0, 0, 0, alpha), stroke_width=8)
            final_draw.text((tx2, ty + 64), text_line2, font=cta_font, fill=(255, 230, 0, alpha), stroke_fill=(0, 0, 0, alpha), stroke_width=8)

            # Paste clean mini vector heart next to line 2
            canvas.paste(mini_heart, (int(tx2 + w2 + 12), int(ty + 66)), mini_heart)

            frame_path = output_dir / f"heart_{f:02d}.png"
            canvas.save(frame_path, "PNG")
            frames.append((frame_path, 1.0 / fps))

        # Concat demuxer file
        concat_path = output_dir / "outro_concat.txt"
        with open(concat_path, "w", encoding="utf-8") as f:
            lead_in_dur = max(0.1, total_duration - outro_len)
            f.write(f"file '{blank_png.resolve()}'\n")
            f.write(f"duration {lead_in_dur:.4f}\n")
            for f_path, f_dur in frames:
                f.write(f"file '{f_path.resolve()}'\n")
                f.write(f"duration {f_dur:.4f}\n")
            if frames:
                f.write(f"file '{frames[-1][0].resolve()}'\n")

        return concat_path

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
