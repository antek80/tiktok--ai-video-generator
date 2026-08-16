import logging
import uuid
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from PIL import Image
from config.settings import settings, OUTPUT_DIR, TEMP_DIR
from core.scriptwriter import ScriptWriter, VideoScript
from core.voice_engine import VoiceEngine
from core.subtitle_engine import SubtitleEngine
from core.asset_manager import AssetManager
from core.video_engine import VideoEngine

logger = logging.getLogger(__name__)

class VideoGenerationResult:
    def __init__(
        self,
        video_path: Path,
        script: VideoScript,
        duration: float,
        caption: str,
        hashtags: list,
        project_dir: Path
    ):
        self.video_path = video_path
        self.script = script
        self.duration = duration
        self.caption = caption
        self.hashtags = hashtags
        self.project_dir = project_dir

    def to_dict(self) -> Dict[str, Any]:
        return {
            "video_path": str(self.video_path),
            "title": self.script.title,
            "topic": self.script.topic,
            "duration": self.duration,
            "caption": self.caption,
            "hashtags": self.hashtags,
            "full_caption": f"{self.caption}\n\n" + " ".join(self.hashtags)
        }

class Pipeline:
    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        voice: Optional[str] = None
    ):
        self.scriptwriter = ScriptWriter(api_key=gemini_api_key)
        self.voice_engine = VoiceEngine(voice=voice)
        self.subtitle_engine = SubtitleEngine()
        self.asset_manager = AssetManager(api_key=gemini_api_key)
        self.video_engine = VideoEngine()

    def generate_video(
        self,
        topic: str,
        language: str = "en",
        voice: Optional[str] = None,
        custom_script: Optional[VideoScript] = None
    ) -> VideoGenerationResult:
        """
        Full end-to-end automated pipeline to produce a high-retention anti-shadowban TikTok video.
        Layers: 60fps Gameplay + Authentic Photo Cards + TikTok Like Heart Outro + Hormozi Subtitles.
        """
        job_id = f"video_{uuid.uuid4().hex[:8]}"
        project_dir = TEMP_DIR / job_id
        project_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"=== Starting Video Generation Pipeline for Topic: '{topic}' [{job_id}] ===")

        # 1. Generate Script
        if custom_script:
            script = custom_script
        else:
            logger.info("Step 1: Generating high-retention viral script...")
            script = self.scriptwriter.generate_script(topic=topic, language=language)

        with open(project_dir / "script.json", "w", encoding="utf-8") as f:
            json.dump(script.model_dump(), f, ensure_ascii=False, indent=2)

        # 2. Generate Voiceover Audio & Word Timestamps
        logger.info("Step 2: Generating natural TTS voiceover with word-level timestamps...")
        audio_path = project_dir / "voice.mp3"
        total_duration, word_timestamps = self.voice_engine.generate_sync(
            text=script.full_narration,
            output_audio_path=audio_path,
            voice=voice or settings.default_voice_en
        )

        # 3. Generate Dynamic Subtitles Overlays (Hormozi style)
        logger.info("Step 3: Creating dynamic word-by-word karaoke subtitles...")
        subs_dir = project_dir / "subtitles"
        subtitles_concat_path, _ = self.subtitle_engine.generate_subtitle_overlays(
            word_timestamps=word_timestamps,
            output_dir=subs_dir,
            total_duration=total_duration
        )

        # 4. Generate Contextual Image Cards for Specific Entities Mentioned
        logger.info("Step 4: Checking for authentic entity photos & visual overlays...")
        cards_dir = project_dir / "cards"
        cards_dir.mkdir(parents=True, exist_ok=True)
        
        blank_card = cards_dir / "card_blank.png"
        Image.new("RGBA", (settings.video_width, settings.video_height), (0, 0, 0, 0)).save(blank_card)

        num_scenes = len(script.scenes)
        base_scene_duration = total_duration / max(1, num_scenes)
        
        card_entries = []
        current_time = 0.0

        for i, scene in enumerate(script.scenes):
            seg_duration = max(1.0, total_duration - current_time) if i == num_scenes - 1 else base_scene_duration
            card_path = cards_dir / f"card_{scene.scene_id}.png"
            
            entity_query = scene.visual_prompt.replace("Cinematic vertical shot", "").replace("9:16", "").strip()
            if i == 0:
                entity_query = topic
                
            generated_overlay = self.asset_manager.create_floating_card_overlay(
                query=entity_query,
                output_path=card_path,
                video_width=settings.video_width,
                video_height=settings.video_height
            )

            used_img = card_path if (generated_overlay and generated_overlay.exists()) else blank_card
            card_entries.append((used_img, seg_duration))
            current_time += seg_duration

        cards_concat_path = cards_dir / "cards_concat.txt"
        with open(cards_concat_path, "w", encoding="utf-8") as f:
            for c_path, c_dur in card_entries:
                f.write(f"file '{c_path.resolve()}'\n")
                f.write(f"duration {c_dur:.4f}\n")
            if card_entries:
                f.write(f"file '{card_entries[-1][0].resolve()}'\n")

        # 5. Generate TikTok Double-Tap Like Outro Heart Animation
        logger.info("Step 5: Generating TikTok Like Heart Outro animation...")
        outro_dir = project_dir / "outro"
        outro_concat_path = self.asset_manager.create_like_outro_overlay(
            output_dir=outro_dir,
            total_duration=total_duration,
            video_width=settings.video_width,
            video_height=settings.video_height
        )

        # 6. Generate BGM and SFX
        logger.info("Step 6: Synthesizing background ambience and SFX...")
        bgm_path = project_dir / "bgm.aac"
        self.asset_manager.create_ambient_bgm(bgm_path, duration=total_duration + 1.0)
        
        whoosh_path = project_dir / "whoosh.aac"
        self.asset_manager.create_whoosh_sfx(whoosh_path)

        # 7. Final Video Assembly with Multi-layer FFmpeg Composition
        logger.info("Step 7: Assembling final video with Heart Outro & FFmpeg...")
        final_video_path = OUTPUT_DIR / f"{job_id}.mp4"
        self.video_engine.assemble_final_video(
            segment_paths=[],
            subtitles_concat_path=subtitles_concat_path,
            voice_audio_path=audio_path,
            bgm_audio_path=bgm_path,
            output_video_path=final_video_path,
            cards_concat_path=cards_concat_path,
            outro_concat_path=outro_concat_path,
            whoosh_sfx_path=whoosh_path,
            duration=total_duration
        )

        logger.info(f"=== Video Generated Successfully: {final_video_path} ===")

        return VideoGenerationResult(
            video_path=final_video_path,
            script=script,
            duration=total_duration,
            caption=script.caption,
            hashtags=script.hashtags,
            project_dir=project_dir
        )
