import logging
from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont
from core.voice_engine import WordTimestamp
from config.settings import settings

logger = logging.getLogger(__name__)

CANDIDATE_FONTS = [
    Path("/System/Library/Fonts/Supplemental/Impact.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    Path("/System/Library/Fonts/Helvetica.ttc"),
    Path("/Library/Fonts/Impact.ttf"),
    Path("/System/Library/Fonts/SFNS.ttf"),
]

class SubtitleCard:
    def __init__(self, image_path: Path, duration: float):
        self.image_path = image_path
        self.duration = duration

class SubtitleEngine:
    def __init__(
        self,
        words_per_batch: int = 2,
        font_size: int = 76,
        active_color: Tuple[int, int, int] = (255, 230, 0),   # Vibrant Neon Yellow
        normal_color: Tuple[int, int, int] = (255, 255, 255), # Pure Crisp White
        stroke_color: Tuple[int, int, int] = (0, 0, 0),       # Heavy Black outline
        stroke_width: int = 10
    ):
        self.words_per_batch = words_per_batch
        self.font_size = font_size
        self.active_color = active_color
        self.normal_color = normal_color
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.font = self._load_font()

    def _load_font(self) -> ImageFont.FreeTypeFont:
        for font_path in CANDIDATE_FONTS:
            if font_path.exists():
                try:
                    return ImageFont.truetype(str(font_path), self.font_size)
                except Exception:
                    continue
        return ImageFont.load_default()

    def generate_subtitle_overlays(
        self,
        word_timestamps: List[WordTimestamp],
        output_dir: Path,
        total_duration: float,
        video_width: int = 1080,
        video_height: int = 1920
    ) -> Tuple[Path, Path]:
        """
        Generates a sequence of transparent PNG subtitle overlays with rapid-fire
        active-word highlight and returns the concat demuxer text file path.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Transparent placeholder
        blank_png = output_dir / "sub_blank.png"
        blank_img = Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0))
        blank_img.save(blank_png)

        # 2. Group into batches of 1-2 words (Hormozi rapid-fire style)
        batches: List[List[WordTimestamp]] = []
        current_batch: List[WordTimestamp] = []
        for wt in word_timestamps:
            current_batch.append(wt)
            if len(current_batch) >= self.words_per_batch or wt.word.endswith((".", "?", "!", ",")):
                batches.append(current_batch)
                current_batch = []
        if current_batch:
            batches.append(current_batch)

        # 3. Render each active word state
        cards: List[SubtitleCard] = []
        last_timestamp = 0.0

        for batch_idx, batch in enumerate(batches):
            for active_idx, active_word in enumerate(batch):
                start_time = active_word.start_time
                if active_idx < len(batch) - 1:
                    end_time = batch[active_idx + 1].start_time
                else:
                    end_time = active_word.end_time + 0.08

                # Insert gap if needed
                if start_time > last_timestamp + 0.05:
                    gap_duration = start_time - last_timestamp
                    cards.append(SubtitleCard(blank_png, gap_duration))

                # Render PNG
                img_path = output_dir / f"sub_{batch_idx}_{active_idx}.png"
                self._render_subtitle_image(
                    batch=batch,
                    active_idx=active_idx,
                    output_path=img_path,
                    video_width=video_width,
                    video_height=video_height
                )
                
                duration = max(0.04, end_time - start_time)
                cards.append(SubtitleCard(img_path, duration))
                last_timestamp = end_time

        # Fill end gap
        if total_duration > last_timestamp:
            cards.append(SubtitleCard(blank_png, total_duration - last_timestamp))

        # 4. Write concat file
        concat_path = output_dir / "subtitles_concat.txt"
        with open(concat_path, "w", encoding="utf-8") as f:
            for card in cards:
                f.write(f"file '{card.image_path.resolve()}'\n")
                f.write(f"duration {card.duration:.4f}\n")
            if cards:
                f.write(f"file '{cards[-1].image_path.resolve()}'\n")

        logger.info(f"Generated {len(cards)} dynamic subtitle frames in: {concat_path}")
        return concat_path, blank_png

    def _render_subtitle_image(
        self,
        batch: List[WordTimestamp],
        active_idx: int,
        output_path: Path,
        video_width: int,
        video_height: int
    ):
        img = Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        words = [w.word.upper().strip() for w in batch if w.word.strip()]
        if not words:
            img.save(output_path, "PNG")
            return

        space_width = draw.textlength(" ", font=self.font)
        word_widths = [draw.textlength(w, font=self.font) for w in words]

        total_text_width = sum(word_widths) + (len(words) - 1) * space_width
        start_x = (video_width - total_text_width) / 2.0
        
        # Perfect vertical positioning (eye level center-middle)
        start_y = (video_height / 2.0) + 120.0

        curr_x = start_x
        for i, word in enumerate(words):
            fill_color = self.active_color if i == active_idx else self.normal_color
            
            # 1. Heavy Black Drop Shadow for 3D POP
            draw.text(
                (curr_x + 5, start_y + 6),
                word,
                font=self.font,
                fill=(0, 0, 0, 240),
                stroke_fill=(0, 0, 0, 240),
                stroke_width=self.stroke_width
            )

            # 2. Main Text with thick outer outline
            draw.text(
                (curr_x, start_y),
                word,
                font=self.font,
                fill=fill_color,
                stroke_fill=self.stroke_color,
                stroke_width=self.stroke_width
            )
            curr_x += word_widths[i] + space_width

        img.save(output_path, "PNG")
