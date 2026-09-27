"""
Current-news scripts: real headlines from RSS feeds, rewritten by Gemini into a
debate-provoking TikTok script that sticks to the facts in the source article.

Posting is fully automatic, so every script goes through a second Gemini pass that
checks each sentence against the article; unsupported claims mean no video.
"""
import html
import json
import logging
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional, Set

from config.settings import settings
from core.scriptwriter import NoFreshStoryError, VideoScript

logger = logging.getLogger(__name__)

NEWS_FEEDS = {
    "BBC News": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "BBC Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "NPR": "https://feeds.npr.org/1001/rss.xml",
    "The Guardian": "https://www.theguardian.com/us-news/rss",
    "The Guardian World": "https://www.theguardian.com/world/rss",
}
MAX_AGE_HOURS = 24
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) TikTokStoryBot/2.0"

GEMINI_MODELS = ["gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash", "gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-lite"]


def _http_get(url: str, timeout: int = 8) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch_headlines(max_age_hours: int = MAX_AGE_HOURS) -> List[Dict[str, str]]:
    """Fresh headlines from all feeds: title, summary, url, source."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    items: List[Dict[str, str]] = []
    for source, feed_url in NEWS_FEEDS.items():
        try:
            root = ET.fromstring(_http_get(feed_url))
        except Exception as e:
            logger.warning(f"News feed {source} unavailable: {e}")
            continue
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            summary = re.sub(r"<[^>]+>", " ", html.unescape(item.findtext("description") or "")).strip()
            try:
                published = parsedate_to_datetime(item.findtext("pubDate") or "")
            except (TypeError, ValueError):
                continue
            if not title or not link or published < cutoff:
                continue
            items.append({"title": title, "summary": summary[:300], "url": link, "source": source.replace(" World", "").replace(" Business", "")})
    logger.info(f"Fetched {len(items)} fresh headlines (last {max_age_hours}h)")
    return items


def fetch_article_text(url: str, max_chars: int = 6000) -> str:
    """Plain text of the article's paragraphs — the only facts the script may use."""
    page = _http_get(url, timeout=10)
    # Drop scripts/menus first — otherwise an unclosed <p> swallows inline JS (Guardian)
    page = re.sub(r"<(script|style|noscript|svg|nav|header|footer|aside|figure)\b[^>]*>.*?</\1>", " ", page, flags=re.S | re.I)
    start, end = page.find("<article"), page.rfind("</article>")
    if start != -1 and end > start:
        page = page[start:end]
    paragraphs = re.findall(r"<p\b[^>]*>(.*?)</p>", page, flags=re.S | re.I)
    texts = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(p))).strip() for p in paragraphs]
    return " ".join(t for t in texts if len(t) > 40)[:max_chars]


def _gemini_json(prompt: str) -> Optional[dict]:
    from google import genai
    client = genai.Client(api_key=settings.gemini_api_key)
    for model in GEMINI_MODELS:
        try:
            res = client.models.generate_content(
                model=model, contents=prompt, config={"response_mime_type": "application/json"}
            )
            if res and res.text:
                data = json.loads(res.text)
                # Models occasionally wrap the object in a one-element list
                if isinstance(data, list) and data and isinstance(data[0], dict):
                    data = data[0]
                if isinstance(data, dict):
                    return data
        except Exception as e:
            logger.debug(f"Gemini {model} failed: {e}")
    return None


PICK_PROMPT = """You pick ONE news story for a TikTok video that will spark heated debate in the comments.
Good picks: prices and cost of living, controversial laws or court rulings, absurd official decisions,
big-tech and billionaire moves, workplace and money fights, culture-war-adjacent policy that people
genuinely disagree about.
The audience is American: prefer US stories or global stories Americans care about; skip
purely local UK/European items unless they are internationally famous.
NEVER pick: stories centred on deaths, killings, disasters with victims, war casualties, terrorism,
child abuse, suicide, or anything where outrage would mock victims.
Return JSON: {{"index": <number from the list>, "reason": "why people will argue about it"}}

Headlines:
{headlines}"""

SCRIPT_PROMPT = """You write a 30-40 second TikTok news script in ENGLISH about the article below.

HARD RULES:
1. Use ONLY facts stated in the article. No invented numbers, quotes, motives or events.
   Do not attribute anything to a real person unless the article says it.
2. Strong hook: scene 1 opens with the most provocative TRUE fact from the article.
3. 4-5 scenes, 85-105 words total, short punchy sentences.
4. Present both sides fairly; the emotion comes from the facts, not from insults.
5. The last scene asks ONE polarising question that makes viewers pick a side in the comments.
6. For every scene set "image_query" to the EXACT title of an existing English Wikipedia article
   whose main photo fits the scene (the country, city, institution, company or public figure
   named in the article). Never a description.
7. "caption": one provocative line (a true fact + question) ending with "Source: {source}".
   Hashtags are single words without spaces.

Article ({source}): {title}
{article}

Return JSON matching:
{{
  "title": "Short punchy title",
  "topic": "{title_json}",
  "target_audience": "News & debate",
  "hook": "first sentence",
  "scenes": [{{"scene_id": 1, "visual_prompt": "short description", "narration": "sentence", "animation": "zoom_in", "image_query": "Wikipedia title"}}],
  "full_narration": "all narration joined",
  "caption": "caption ... Source: {source}",
  "hashtags": ["#news", "#debate", "#fyp"]
}}"""

VERIFY_PROMPT = """Fact-check a TikTok script against its source article.
For each sentence of the narration decide whether it is fully supported by the article
(paraphrase is fine; opinions phrased as a question are fine). Any invented number, quote,
name, date, motive or event is NOT supported.
Return JSON: {{"supported": true/false, "problems": ["sentence ... - why"]}}

ARTICLE:
{article}

NARRATION:
{narration}"""


def generate_news_script(used_urls: Set[str]) -> tuple:
    """
    Returns (VideoScript, source_url) for the most debate-worthy fresh headline that
    was not posted before and passes the fact check.
    Raises NoFreshStoryError when nothing qualifies.
    """
    if not settings.gemini_api_key:
        raise NoFreshStoryError("News mode needs GEMINI_API_KEY in .env.")

    candidates = [h for h in fetch_headlines() if h["url"] not in used_urls]
    if not candidates:
        raise NoFreshStoryError("No fresh, unposted headlines in the news feeds.")

    tried: Set[int] = set()
    for _ in range(3):
        remaining = [(i, h) for i, h in enumerate(candidates) if i not in tried]
        if not remaining:
            break
        listing = "\n".join(f"{i}. [{h['source']}] {h['title']} — {h['summary']}" for i, h in remaining)
        pick = _gemini_json(PICK_PROMPT.format(headlines=listing))
        idx = pick.get("index") if pick else None
        if not isinstance(idx, int) or idx in tried or not 0 <= idx < len(candidates):
            break
        tried.add(idx)
        story = candidates[idx]
        logger.info(f"Picked news story: [{story['source']}] {story['title']} — {pick.get('reason', '')}")

        try:
            article = fetch_article_text(story["url"])
        except Exception as e:
            logger.warning(f"Could not read article {story['url']}: {e}")
            continue
        if len(article) < 400:
            logger.warning(f"Article too short to fact-check ({len(article)} chars), skipping.")
            continue

        data = _gemini_json(SCRIPT_PROMPT.format(
            source=story["source"], title=story["title"], title_json=story["title"].replace('"', "'"),
            article=article,
        ))
        if not data:
            continue
        try:
            script = VideoScript(**data)
        except Exception as e:
            logger.warning(f"Gemini returned an invalid news script: {e}")
            continue

        verdict = _gemini_json(VERIFY_PROMPT.format(article=article, narration=script.full_narration))
        if not verdict or not verdict.get("supported"):
            logger.warning(f"News script failed fact check, not posting: {verdict and verdict.get('problems')}")
            continue

        return script, story["url"]

    raise NoFreshStoryError("No news story produced a script that passed the fact check.")
