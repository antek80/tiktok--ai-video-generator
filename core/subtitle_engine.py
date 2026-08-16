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
        active_color: Tuple[int, int, int] = (255, 230, 0),   # Neon Yellow
        normal_color: Tuple[int, int, int] = (255, 255, 255), # Pure White
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
        outro_duration: float = 2.0,
        video_width: int = 1080,
        video_height: int = 1920
    ) -> Tuple[Path, Path]:
        """
        Generates sample-accurate karaoke subtitle overlays that remain 100% in sync
        and automatically blanks out during the outro so subtitles NEVER overlap with the CTA heart.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        blank_png = output_dir / "sub_blank.png"
        Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0)).save(blank_png)

        if not word_timestamps:
            concat_path = output_dir / "subtitles_concat.txt"
            with open(concat_path, "w", encoding="utf-8") as f:
                f.write(f"file '{blank_png.resolve()}'\n")
                f.write(f"duration {total_duration:.4f}\n")
                f.write(f"file '{blank_png.resolve()}'\n")
            return concat_path, blank_png

        # 1. Group into batches of 1-2 words (Hormozi rapid-fire style)
        batches: List[List[WordTimestamp]] = []
        current_batch: List[WordTimestamp] = []
        for wt in word_timestamps:
            current_batch.append(wt)
            if len(current_batch) >= self.words_per_batch or wt.word.endswith((".", "?", "!", ",")):
                batches.append(current_batch)
                current_batch = []
        if current_batch:
            batches.append(current_batch)

        # 2. Build flat list of all timeline event states: (image_path, start_time)
        timeline_events = []

        # If voice doesn't start at 0.0, prepend blank
        first_word_start = word_timestamps[0].start_time
        if first_word_start > 0.05:
            timeline_events.append((blank_png, 0.0))

        for batch_idx, batch in enumerate(batches):
            for active_idx, active_word in enumerate(batch):
                img_path = output_dir / f"sub_{batch_idx}_{active_idx}.png"
                self._render_subtitle_image(
                    batch=batch,
                    active_idx=active_idx,
                    output_path=img_path,
                    video_width=video_width,
                    video_height=video_height
                )
                timeline_events.append((img_path, active_word.start_time))

        # 3. Calculate exact delta durations, stopping before outro
        cards: List[SubtitleCard] = []
        cutoff_time = max(0.0, total_duration - outro_duration)

        for i in range(len(timeline_events)):
            img_p, t_start = timeline_events[i]
            if t_start >= cutoff_time:
                continue

            if i < len(timeline_events) - 1:
                t_next = timeline_events[i + 1][1]
                if t_next >= cutoff_time:
                    duration = max(0.03, cutoff_time - t_start)
                    cards.append(SubtitleCard(img_p, duration))
                    break
                else:
                    duration = max(0.03, t_next - t_start)
                    cards.append(SubtitleCard(img_p, duration))
            else:
                duration = max(0.1, cutoff_time - t_start)
                cards.append(SubtitleCard(img_p, duration))

        # 4. Fill the entire outro duration with transparent blank so NO text overlaps with CTA
        if outro_duration > 0:
            cards.append(SubtitleCard(blank_png, outro_duration))

        # 5. Write FFmpeg concat list
        concat_path = output_dir / "subtitles_concat.txt"
        with open(concat_path, "w", encoding="utf-8") as f:
            for card in cards:
                f.write(f"file '{card.image_path.resolve()}'\n")
                f.write(f"duration {card.duration:.4f}\n")
            if cards:
                f.write(f"file '{cards[-1].image_path.resolve()}'\n")

        logger.info(f"Generated {len(cards)} synchronized subtitle frames (outro clear enabled) in: {concat_path}")
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
        start_y = (video_height / 2.0) + 120.0

        curr_x = start_x
        for i, word in enumerate(words):
            fill_color = self.active_color if i == active_idx else self.normal_color
            
            # Shadow
            draw.text(
                (curr_x + 5, start_y + 6),
                word,
                font=self.font,
                fill=(0, 0, 0, 240),
                stroke_fill=(0, 0, 0, 240),
                stroke_width=self.stroke_width
            )

            # Main text
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
