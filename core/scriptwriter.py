import json
import logging
from typing import List, Optional
from pydantic import BaseModel, Field
from config.settings import settings

logger = logging.getLogger(__name__)

class Scene(BaseModel):
    scene_id: int
    visual_prompt: str = Field(description="Detailed prompt for generating a vertical 9:16 high quality realistic or stylized image for this scene")
    narration: str = Field(description="Spoken text for this scene segment (concise, 1-2 punchy sentences)")
    animation: str = Field(default="zoom_in", description="Camera motion: zoom_in, zoom_out, pan_left, pan_right")

class VideoScript(BaseModel):
    title: str
    topic: str
    target_audience: str
    hook: str
    scenes: List[Scene]
    full_narration: str
    caption: str
    hashtags: List[str]

SYSTEM_PROMPT = """You are a world-class viral short-form video creator (TikTok, YouTube Shorts, Instagram Reels).
Your mission is to generate a high-retention, anti-boring script for a 15-30 second vertical video.

RULES FOR VIRALITY & RETENTION:
1. THE 3-SECOND HOOK: The first sentence must trigger immediate curiosity, surprise, or an emotional response.
   - FORBIDDEN OPENINGS: Do NOT use "Did you know...", "In today's fast-paced world...", "Have you ever wondered...", "Hey guys...".
   - Start immediately in the middle of the action or with a bold, counter-intuitive statement.
2. PACING: Each scene must last between 1.5 and 2.5 seconds (about 5-10 words spoken). Never exceed 3 seconds per scene.
3. LANGUAGE: Natural, punchy, conversational, no academic jargon.
4. VISUAL PROMPTS: Vivid, high-contrast, cinematic, 9:16 vertical composition instructions for each scene.

Output MUST be strictly valid JSON matching this schema:
{
  "title": "Short title",
  "topic": "Topic summary",
  "target_audience": "Target demographic",
  "hook": "First 3 seconds spoken text",
  "scenes": [
    {
      "scene_id": 1,
      "visual_prompt": "Cinematic vertical 9:16 photo of...",
      "narration": "First sentence spoken here.",
      "animation": "zoom_in"
    }
  ],
  "full_narration": "Combined narration of all scenes joined by space",
  "caption": "Catchy TikTok caption",
  "hashtags": ["#fyp", "#viral", "#foryou", "#topic1", "#topic2"]
}
"""

class ScriptWriter:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.gemini_api_key

    def generate_script(self, topic: str, language: str = "pl", style: str = "curiosity") -> VideoScript:
        """Generates a viral script using Gemini AI or structured fallback."""
        if self.api_key:
            try:
                from google import genai
                client = genai.Client(api_key=self.api_key)
                
                lang_instruction = "Write the narration, caption, and hashtags in POLISH (Język polski)." if language.startswith("pl") else "Write in ENGLISH."
                prompt = f"""Topic: {topic}
Style: {style}
Language: {lang_instruction}

Create a viral 5-7 scene high-retention video script strictly following the JSON format."""

                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[SYSTEM_PROMPT, prompt],
                    config={"response_mime_type": "application/json"}
                )
                
                data = json.loads(response.text)
                return VideoScript(**data)
            except Exception as e:
                logger.warning(f"Failed to generate script with Gemini API: {e}. Using intelligent fallback.")
                
        # Smart template fallback if API key not provided or failed
        return self._generate_fallback_script(topic, language)

    def _generate_fallback_script(self, topic: str, language: str) -> VideoScript:
        if language.startswith("pl"):
            return VideoScript(
                title=f"Tajemnica: {topic}",
                topic=topic,
                target_audience="Entuzjaści ciekawostek i technologii",
                hook=f"To co zaraz usłyszysz o {topic}, zmieni Twoje myślenie.",
                scenes=[
                    Scene(
                        scene_id=1,
                        visual_prompt=f"Cinematic vertical shot, dramatic lighting, mystery, high detail, 9:16, showing {topic}",
                        narration=f"To co zaraz usłyszysz o {topic}, zmieni Twoje myślenie.",
                        animation="zoom_in"
                    ),
                    Scene(
                        scene_id=2,
                        visual_prompt=f"Detailed macro close up, intense colors, 9:16, mysterious elements of {topic}",
                        narration="Większość ludzi nie ma pojęcia, jak to naprawdę działa.",
                        animation="pan_left"
                    ),
                    Scene(
                        scene_id=3,
                        visual_prompt=f"Futuristic concept art, vibrant neon contrast, 9:16 vertical, revealing the truth about {topic}",
                        narration="Naukowcy odkryli, że kluczem jest jeden niewiarygodny szczegół.",
                        animation="zoom_out"
                    ),
                    Scene(
                        scene_id=4,
                        visual_prompt=f"Epic cinematic wide angle, breathtaking composition, 9:16 vertical, {topic} in action",
                        narration="Efekt tego zjawiska widać dosłownie na każdym kroku.",
                        animation="pan_right"
                    ),
                    Scene(
                        scene_id=5,
                        visual_prompt=f"Ultra realistic portrait looking at the camera with curiosity, cinematic lighting, 9:16",
                        narration="A Ty? Wiedziałeś o tym wcześniej? Zostaw komentarz i zaobserwuj po więcej!",
                        animation="zoom_in"
                    )
                ],
                full_narration=f"To co zaraz usłyszysz o {topic}, zmieni Twoje myślenie. Większość ludzi nie ma pojęcia, jak to naprawdę działa. Naukowcy odkryli, że kluczem jest jeden niewiarygodny szczegół. Efekt tego zjawiska widać dosłownie na każdym kroku. A Ty? Wiedziałeś o tym wcześniej? Zostaw komentarz i zaobserwuj po więcej!",
                caption=f"Niewiarygodna prawda o: {topic} 🤯 Sprawdź do końca! #ciekawostki",
                hashtags=["#ciekawostki", "#nauka", "#wiedza", "#fyp", "#dlaciebie", "#viral"]
            )
        else:
            return VideoScript(
                title=f"The Truth About {topic}",
                topic=topic,
                target_audience="Curiosity seekers",
                hook=f"What you are about to hear about {topic} will blow your mind.",
                scenes=[
                    Scene(
                        scene_id=1,
                        visual_prompt=f"Cinematic vertical shot, dramatic lighting, mystery, high detail, 9:16, showing {topic}",
                        narration=f"What you are about to hear about {topic} will blow your mind.",
                        animation="zoom_in"
                    ),
                    Scene(
                        scene_id=2,
                        visual_prompt=f"Detailed macro close up, intense colors, 9:16, mysterious elements of {topic}",
                        narration="99% of people have no idea this actually exists.",
                        animation="pan_left"
                    ),
                    Scene(
                        scene_id=3,
                        visual_prompt=f"Futuristic concept art, vibrant neon contrast, 9:16 vertical, revealing {topic}",
                        narration="Experts recently uncovered the single mechanism behind it.",
                        animation="zoom_out"
                    ),
                    Scene(
                        scene_id=4,
                        visual_prompt=f"Ultra realistic cinematic portrait with curiosity, 9:16",
                        narration="Did you know this before? Follow for more mind-blowing facts!",
                        animation="zoom_in"
                    )
                ],
                full_narration=f"What you are about to hear about {topic} will blow your mind. 99% of people have no idea this actually exists. Experts recently uncovered the single mechanism behind it. Did you know this before? Follow for more mind-blowing facts!",
                caption=f"Mind-blowing facts about {topic} 🤯 Wait for the end! #facts",
                hashtags=["#facts", "#curiosity", "#fyp", "#viral", "#foryou"]
            )
