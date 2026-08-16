import logging
import uuid
import json
from pathlib import Path
from typing import Optional, Dict, Any
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
        language: str = "pl",
        voice: Optional[str] = None,
        custom_script: Optional[VideoScript] = None
    ) -> VideoGenerationResult:
        """
        Full end-to-end automated pipeline to produce a high-retention anti-shadowban TikTok video.
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
            voice=voice
        )

        # 3. Generate Dynamic Subtitles Overlays
        logger.info("Step 3: Creating dynamic word-by-word karaoke subtitles...")
        subs_dir = project_dir / "subtitles"
        subtitles_concat_path, _ = self.subtitle_engine.generate_subtitle_overlays(
            word_timestamps=word_timestamps,
            output_dir=subs_dir,
            total_duration=total_duration
        )

        # 4. Generate Images & Render Scene Segments
        logger.info(f"Step 4: Generating visual assets for {len(script.scenes)} scenes...")
        num_scenes = len(script.scenes)
        base_scene_duration = total_duration / max(1, num_scenes)
        
        segment_paths = []
        current_time = 0.0

        for i, scene in enumerate(script.scenes):
            if i == num_scenes - 1:
                seg_duration = max(1.0, total_duration - current_time)
            else:
                seg_duration = base_scene_duration

            img_path = project_dir / f"scene_{scene.scene_id}.jpg"
            self.asset_manager.generate_image_for_scene(
                prompt=scene.visual_prompt,
                scene_id=scene.scene_id,
                output_path=img_path,
                topic=topic
            )

            seg_video_path = project_dir / f"segment_{scene.scene_id}.mp4"
            self.video_engine.create_scene_segment(
                image_path=img_path,
                duration=seg_duration,
                animation=scene.animation,
                output_segment_path=seg_video_path
            )
            segment_paths.append(seg_video_path)
            current_time += seg_duration

        # 5. Generate BGM and SFX
        logger.info("Step 5: Synthesizing background ambience and SFX...")
        bgm_path = project_dir / "bgm.aac"
        self.asset_manager.create_ambient_bgm(bgm_path, duration=total_duration + 1.0)
        
        whoosh_path = project_dir / "whoosh.aac"
        self.asset_manager.create_whoosh_sfx(whoosh_path)

        # 6. Final Video Assembly with Anti-Shadowban Filters
        logger.info("Step 6: Assembling final anti-shadowban video with FFmpeg...")
        final_video_path = OUTPUT_DIR / f"{job_id}.mp4"
        self.video_engine.assemble_final_video(
            segment_paths=segment_paths,
            subtitles_concat_path=subtitles_concat_path,
            voice_audio_path=audio_path,
            bgm_audio_path=bgm_path,
            output_video_path=final_video_path,
            whoosh_sfx_path=whoosh_path
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
