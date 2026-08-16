import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List

from config.settings import BASE_DIR, settings
from core.pipeline import Pipeline
from agent.session_manager import SessionManager
from agent.tiktok_uploader import TikTokUploader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "daily_poster.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("daily-poster")

TOPICS_FILE = BASE_DIR / "topics_queue.json"
HISTORY_FILE = BASE_DIR / "posted_history.json"

DEFAULT_TOPICS_POOL = [
    "The Bizarre Mystery of the Dyatlov Pass Incident",
    "Why No One Is Allowed Inside China's First Emperor Tomb",
    "The Terrifying Bloop Sound Recorded in the Deep Ocean",
    "The Philadelphia Experiment – Secret Teleportation or Hoax",
    "What Is Hidden Deep Under the Ice of Antarctica",
    "The Ghost Ship Mary Celeste – The Crew That Vanished Into Thin Air",
    "The 1977 Wow Signal – Our Only Contact With Aliens",
    "Why Everyone Sees the Same Entity During Sleep Paralysis",
    "Inside the Secret Underground Vaults of the Vatican",
    "What Actually Happens When You Cross a Black Hole Event Horizon"
]

def load_posted_history() -> List[dict]:
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_posted_history(history: List[dict]):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def get_next_topic() -> str:
    """Picks next unposted topic or generates a fresh high-retention English topic via Gemini."""
    history = load_posted_history()
    used_topics = {entry.get("topic") for entry in history}

    # 1. Check custom queue file
    if TOPICS_FILE.exists():
        try:
            with open(TOPICS_FILE, "r", encoding="utf-8") as f:
                custom_topics = json.load(f)
            for t in custom_topics:
                if t not in used_topics:
                    return t
        except Exception as e:
            logger.warning(f"Error reading {TOPICS_FILE}: {e}")

    # 2. Pick from default pool
    for t in DEFAULT_TOPICS_POOL:
        if t not in used_topics:
            return t

    # 3. Dynamic LLM Generation for endless fresh topics
    if settings.gemini_api_key:
        try:
            from google import genai
            client = genai.Client(api_key=settings.gemini_api_key)
            prompt = f"Generate ONE short, viral, mind-blowing storytelling topic in English for TikTok (unexplained mysteries, deep ocean, cosmos, ancient secrets, psychology). Return ONLY the title. Do not repeat these: {list(used_topics)[-10:]}"
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            new_topic = res.text.strip().strip('"').strip("'")
            if new_topic:
                return new_topic
        except Exception as e:
            logger.warning(f"Error generating topic with Gemini: {e}")

    return f"Untold Dark Mystery of History #{len(history) + 1}"

async def run_daily_job():
    """Main execution function for daily autonomous video generation and posting."""
    logger.info("=== 🤖 Starting TikTok Daily Autonomous Agent ===")
    
    # 1. Check Session
    sm = SessionManager()
    is_logged = await sm.is_logged_in()
    if not is_logged:
        logger.warning("No active TikTok session detected. Opening login browser...")
        await sm.login_interactively()
        is_logged = await sm.is_logged_in()
        if not is_logged:
            logger.error("❌ Login failed or was cancelled.")
            return False

    # 2. Pick Unique English Topic
    topic = get_next_topic()
    logger.info(f"Selected English topic for today: '{topic}'")

    # 3. Generate High-Retention Video in English
    pipeline = Pipeline()
    result = pipeline.generate_video(topic=topic, language="en", voice=settings.default_voice_en)
    logger.info(f"Video generated successfully: {result.video_path} (duration: {result.duration:.2f}s)")

    # 4. Publish to TikTok (without AI label)
    uploader = TikTokUploader(headless=False)
    success = await uploader.upload_video(
        video_path=result.video_path,
        caption=result.caption,
        hashtags=result.hashtags,
        publish_now=True,
        declare_ai=False
    )

    # 5. Record History
    if success:
        history = load_posted_history()
        history.append({
            "timestamp": datetime.now().isoformat(),
            "topic": topic,
            "language": "en",
            "video_path": str(result.video_path),
            "caption": result.caption,
            "status": "published"
        })
        save_posted_history(history)
        logger.info(f"🎉 Daily video for topic '{topic}' published to TikTok and recorded in history!")
        return True
    else:
        logger.error(f"⚠️ Failed to publish video for topic '{topic}'.")
        return False

if __name__ == "__main__":
    asyncio.run(run_daily_job())
