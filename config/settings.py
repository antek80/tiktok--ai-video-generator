import os
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = BASE_DIR / "temp"

for directory in [ASSETS_DIR, OUTPUT_DIR, TEMP_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

class Settings(BaseModel):
    # Gemini API Key
    gemini_api_key: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    
    # Language & Voice Settings
    default_language: str = "en"
    default_voice: str = "en-US-BrianMultilingualNeural"  # Viral TikTok storytelling voice
    default_voice_pl: str = "pl-PL-MarekNeural"
    default_voice_en: str = "en-US-BrianMultilingualNeural"
    
    # Video Specifications
    video_width: int = 1080
    video_height: int = 1920
    fps: int = 30
    audio_bitrate: str = "192k"
    use_gameplay_background: bool = True  # High-retention Minecraft Parkour / GTA gameplay loops
    
    # Anti-Fingerprinting (Anti-Shadowban)
    apply_film_grain: bool = True
    grain_intensity: int = 2  # subtle noise (2%)
    spoof_device_metadata: bool = True
    spoofed_make: str = "Apple"
    spoofed_model: str = "iPhone 15 Pro"
    
    # Subtitle Styles (Hormozi / TikTok Viral Style)
    sub_font_name: str = "Impact"  # or "Arial Black"
    sub_font_size: int = 74
    sub_primary_color: str = "&H00FFFFFF"  # White in ASS (&HAABBGGRR)
    sub_highlight_color: str = "&H0000FFFF"  # Vibrant Yellow in ASS
    sub_outline_color: str = "&H00000000"  # Black outline
    sub_outline_width: int = 4
    sub_shadow_width: int = 3
    sub_words_per_batch: int = 2  # 1-2 words visible on screen at once (rapid-fire)
    
    # TikTok Automation Settings
    tiktok_session_dir: Path = Path.home() / ".tiktok_automation_session"
    headless: bool = True
    simulate_human_delays: bool = True
    declare_ai_content: bool = False  # Domyślnie wyłączone dla formatu storytelling / lektora

    # Daily Schedule Settings (from .env)
    posts_per_day: int = Field(default_factory=lambda: int(os.getenv("POSTS_PER_DAY", "4")))
    schedule_times: str = Field(default_factory=lambda: os.getenv("SCHEDULE_TIMES", ""))

    def get_schedule_slots(self) -> list:
        """Returns the list of HH:MM schedule slots based on .env configuration."""
        if self.schedule_times and self.schedule_times.strip():
            slots = [s.strip() for s in self.schedule_times.split(",") if ":" in s]
            if slots:
                return sorted(slots)

        count = max(1, min(self.posts_per_day, 16))
        # Standard predefined optimal schedules
        predefined = {
            1: ["18:00"],
            2: ["12:30", "19:00"],
            3: ["10:00", "15:00", "19:30"],
            4: ["09:00", "13:00", "17:00", "21:00"],
            5: ["09:00", "12:00", "15:00", "18:00", "21:00"],
            6: ["08:30", "11:00", "13:30", "16:00", "18:30", "21:00"],
            8: ["08:30", "10:30", "12:30", "14:30", "16:30", "18:30", "20:30", "22:00"],
            10: ["08:30", "10:00", "11:30", "13:00", "14:30", "16:00", "17:30", "19:00", "20:30", "22:00"]
        }
        if count in predefined:
            return predefined[count]

        # Dynamic spacing between 08:30 and 22:30
        start_min = 8 * 60 + 30
        end_min = 22 * 60 + 30
        step = (end_min - start_min) / (count - 1) if count > 1 else 0
        slots = []
        for i in range(count):
            cur = int(start_min + i * step)
            slots.append(f"{cur // 60:02d}:{cur % 60:02d}")
        return slots

settings = Settings()
