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

# Massive curated viral storytelling database (50+ non-repeating high-retention topics)
DEFAULT_TOPICS_POOL = [
    # Ocean & Deep Earth Mysteries
    "The Terrifying Bloop Sound Recorded in the Deep Ocean",
    "What Is Hidden Deep Under the Ice of Antarctica",
    "The Mariana Trench Sound – The Deepest Recording on Earth",
    "The Baltic Sea Anomaly – Ancient UFO or Natural Rock",
    "The Underwater Megaliths of Yonaguni Monument in Japan",
    "The Point Nemo Spacecraft Cemetery in the South Pacific",
    
    # Ancient Secrets & Forbidden Archeology
    "The Bizarre Mystery of the Dyatlov Pass Incident",
    "Why No One Is Allowed Inside China's First Emperor Tomb",
    "Inside the Secret Underground Vaults of the Vatican",
    "The Mysterious Lost City of Atlantis – Did It Actually Exist",
    "The Unsolved Riddle of Gobekli Tepe – Older Than History",
    "The Mystery of the Nazca Lines – Messages for the Sky",
    "The Baghdad Battery – Was Electricity Used 2,000 Years Ago",
    "The Great Sphinx Water Erosion Hypothesis – Hidden Age of Egypt",
    "The Underground City of Derinkuyu That Sheltered 20,000 People",

    # Military Secrets & Paranormal Experiments
    "The Philadelphia Experiment – Secret Teleportation or Hoax",
    "The Ghost Ship Mary Celeste – The Crew That Vanished Into Thin Air",
    "The 1977 Wow Signal – Our Only Contact With Aliens",
    "The Montauk Project – Secret Mind Control and Time Travel",
    "The Tunguska Event – The Mysterious 1908 Siberian Explosion",
    "Project MKUltra – The CIA Mind Control Experiments",
    "The Disappearance of Flight 19 in the Bermuda Triangle",
    "The Roswell Incident – What Really Crashed in New Mexico 1947",
    "The Mystery of the Oak Island Money Pit – 200-Year Treasure Hunt",

    # Cosmos, Physics & Mind-Blowing Science
    "What Actually Happens When You Cross a Black Hole Event Horizon",
    "Why Everyone Sees the Same Entity During Sleep Paralysis",
    "The Fermi Paradox – Where Are All the Alien Civilizations",
    "The Great Attractor – The Invisible Force Pulling Our Galaxy",
    "The Simulation Hypothesis – Are We Living in a Computer Code",
    "Quantum Entanglement – Einstein's Spooky Action at a Distance",
    "The Wow Signal vs Tabby's Star – The Megastructure Star",
    "The Boiling River of the Amazon – The Water That Cooks Animals Alive",
    "The Voynich Manuscript – The 600-Year-Old Unbreakable Book",
    "The Lead Masks Case – The Bizarre Brazilian Mystery",
    "The Strange Case of the Green Children of Woolpit",
    "The Disappearance of the Flannan Isles Lighthouse Keepers",
    "The Secret of the Antikythera Mechanism – World's First Computer",
    "The Lake Nyos Disaster – The Invisible Cloud That Killed a Town",
    "The Door to Hell in Turkmenistan – Burning for Over 50 Years",
    "The Siberian Hell Hole Recording – Fact vs Urban Legend",
    "The Mystery of Cicada 3301 – The Internet's Deepest Puzzle",
    "The Voynich Codex – The Book Written in an Unknown Alphabet",
    "The Great Molasses Flood of 1919 – A Deadly Tidal Wave of Sugar",
    "The Strange Disappearance of Roanoke Island's Lost Colony",
    "The Devil's Kettle Waterfall – Where Does Half the River Go",
    "The Lost Cosmonauts – Did the USSR Send Humans to Space First",
    "The Mysterious Klerksdorp Spheres – 3-Billion-Year-Old Artifacts",
    "The Silent Zone of Mapimi – The Desert Where Radio Signals Die",
    "The Mystery of the Taos Hum – The Sound Driving Residents Mad",
    "The Hessdalen Lights – Norway's Unexplained Flying Orbs"
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

    # 2. Pick from default 50+ viral pool
    for t in DEFAULT_TOPICS_POOL:
        if t not in used_topics:
            return t

    # 3. Dynamic LLM Generation for endless fresh topics
    if settings.gemini_api_key:
        try:
            from google import genai
            client = genai.Client(api_key=settings.gemini_api_key)
            prompt = f"Generate ONE short, viral, mind-blowing storytelling topic in English for TikTok (unexplained mysteries, deep ocean, cosmos, ancient secrets, psychology). Return ONLY the title. Do not repeat these: {list(used_topics)[-15:]}"
            candidate_models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
            for mod in candidate_models:
                try:
                    res = client.models.generate_content(model=mod, contents=prompt)
                    if res and res.text:
                        new_topic = res.text.strip().strip('"').strip("'")
                        if new_topic:
                            return new_topic
                except Exception:
                    continue

    return f"Untold Dark Mystery of History #{len(history) + 1}"

async def run_daily_job():
    """Main execution function for 4x daily autonomous video generation and posting."""
    logger.info("=== 🤖 Starting TikTok Autonomous 4x Daily Agent ===")
    
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
    logger.info(f"Selected English topic for today's slot: '{topic}'")

    # 3. Generate High-Retention Video in English (60fps gameplay + photo cards + TikTok like outro)
    pipeline = Pipeline()
    result = pipeline.generate_video(topic=topic, language="en", voice=settings.default_voice_en)
    logger.info(f"Video generated successfully: {result.video_path} (duration: {result.duration:.2f}s)")

    # 4. Publish to TikTok Studio
    uploader = TikTokUploader(headless=False)
    success = await uploader.upload_video(
        video_path=result.video_path,
        caption=result.caption,
        hashtags=result.hashtags,
        publish_now=True,
        declare_ai=False
    )

    # 5. Log History
    history = load_posted_history()
    history.append({
        "timestamp": datetime.now().isoformat(),
        "topic": topic,
        "video_path": str(result.video_path),
        "duration": result.duration,
        "caption": result.caption,
        "hashtags": result.hashtags,
        "published": success
    })
    save_posted_history(history)

    if success:
        logger.info(f"🎉 Successfully published video #{len(history)} to TikTok: '{topic}'")
    else:
        logger.warning(f"⚠️ Video generated and saved, but upload was not confirmed for: '{topic}'")

    return success

if __name__ == "__main__":
    asyncio.run(run_daily_job())
