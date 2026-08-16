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
    
    # TTS Settings
    default_voice_pl: str = "pl-PL-MarekNeural"  # Natural Polish male voice (or pl-PL-ZofiaNeural)
    default_voice_en: str = "en-US-ChristopherNeural"  # Natural English male voice
    
    # Video Specifications
    video_width: int = 1080
    video_height: int = 1920
    fps: int = 30
    audio_bitrate: str = "192k"
    
    # Anti-Fingerprinting (Anti-Shadowban)
    apply_film_grain: bool = True
    grain_intensity: int = 2  # subtle noise (2%)
    spoof_device_metadata: bool = True
    spoofed_make: str = "Apple"
    spoofed_model: str = "iPhone 15 Pro"
    
    # Subtitle Styles (Hormozi / TikTok Viral Style)
    sub_font_name: str = "Impact"  # or "Arial Black"
    sub_font_size: int = 26
    sub_primary_color: str = "&H00FFFFFF"  # White in ASS (&HAABBGGRR)
    sub_highlight_color: str = "&H0000FFFF"  # Vibrant Yellow in ASS
    sub_outline_color: str = "&H00000000"  # Black outline
    sub_outline_width: int = 3
    sub_shadow_width: int = 2
    sub_words_per_batch: int = 2  # 1-3 words visible on screen at once
    
    # TikTok Automation Settings
    tiktok_session_dir: Path = Path.home() / ".tiktok_automation_session"
    headless: bool = False
    simulate_human_delays: bool = True
    declare_ai_content: bool = True  # Mandatory to avoid algorithm penalties

settings = Settings()
