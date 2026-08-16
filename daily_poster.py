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
    "Niewyjaśniona tajemnica Przełęczy Diatłowa",
    "Dlaczego nikt nie może wejść do grobowca pierwszego cesarza Chin",
    "Najgłębsze miejsce na Ziemi i dźwięki z Rowu Mariańskiego",
    "Eksperyment Filadelfia – prawda czy wojskowa mistyfikacja",
    "Co naprawdę znajduje się pod lodami Antarktydy",
    "Zaginięcie statku Mary Celeste – załoga zniknęła bez śladu",
    "Tajemniczy sygnał 'Wow!' z głębokiego kosmosu",
    "Dlaczego ludzie widzą te same sny podczas paraliżu sennego",
    "Najbardziej strzeżone archiwum na świecie – Tajne Archiwa Watykanu",
    "Czarne dziury i co dzieje się za horyzontem zdarzeń"
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
    """Pobiera kolejny unikalny temat z kolejki lub generuje świeży przez Gemini."""
    history = load_posted_history()
    used_topics = {entry.get("topic") for entry in history}

    # 1. Sprawdź plik kolejki
    if TOPICS_FILE.exists():
        try:
            with open(TOPICS_FILE, "r", encoding="utf-8") as f:
                custom_topics = json.load(f)
            for t in custom_topics:
                if t not in used_topics:
                    return t
        except Exception as e:
            logger.warning(f"Błąd odczytu {TOPICS_FILE}: {e}")

    # 2. Wybierz z puli domyślnej
    for t in DEFAULT_TOPICS_POOL:
        if t not in used_topics:
            return t

    # 3. Jeśli wszystko wyczerpane, zapytaj Gemini o nowy temat
    if settings.gemini_api_key:
        try:
            from google import genai
            client = genai.Client(api_key=settings.gemini_api_key)
            prompt = f"Zaproponuj 1 krótki, niezwykle wciągający i intrygujący temat na film storytelling TikTok (tajemnica, niewyjaśniona historia, kosmos, archeologia). Zwróć tylko sam tytuł tematu. Nie powtarzaj tych: {list(used_topics)[-10:]}"
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            new_topic = res.text.strip().strip('"').strip("'")
            if new_topic:
                return new_topic
        except Exception as e:
            logger.warning(f"Błąd generowania tematu z Gemini: {e}")

    return f"Niezwykła tajemnica z przeszłości #{len(history) + 1}"

async def run_daily_job():
    """Główna funkcja wykonująca codzienne generowanie i publikację."""
    logger.info("=== 🤖 Uruchamianie dziennego Agenta TikTok ===")
    
    # 1. Sprawdź sesję
    sm = SessionManager()
    is_logged = await sm.is_logged_in()
    if not is_logged:
        logger.warning("Brak aktywnej sesji TikTok. Otwieram okno logowania...")
        await sm.login_interactively()
        is_logged = await sm.is_logged_in()
        if not is_logged:
            logger.error("❌ Logowanie nie powiodło się lub zostało przerwane.")
            return False

    # 2. Pobierz unikalny temat
    topic = get_next_topic()
    logger.info(f"Wybrany temat na dziś: '{topic}'")

    # 3. Generuj wideo
    pipeline = Pipeline()
    result = pipeline.generate_video(topic=topic, language="pl")
    logger.info(f"Wideo wygenerowane pomyślnie: {result.video_path} (czas: {result.duration:.2f}s)")

    # 4. Opublikuj na TikToku (bez etykiety AI)
    uploader = TikTokUploader(headless=False)
    success = await uploader.upload_video(
        video_path=result.video_path,
        caption=result.caption,
        hashtags=result.hashtags,
        publish_now=True,
        declare_ai=False
    )

    # 5. Zapisz historię
    if success:
        history = load_posted_history()
        history.append({
            "timestamp": datetime.now().isoformat(),
            "topic": topic,
            "video_path": str(result.video_path),
            "caption": result.caption,
            "status": "published"
        })
        save_posted_history(history)
        logger.info(f"🎉 Codzienne wideo dla tematu '{topic}' zostało opublikowane i zapisane w historii!")
        return True
    else:
        logger.error(f"⚠️ Nie udało się opublikować wideo dla tematu '{topic}'.")
        return False

if __name__ == "__main__":
    asyncio.run(run_daily_job())
