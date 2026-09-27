import logging
import uuid
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from PIL import Image
from config.settings import settings, BASE_DIR, OUTPUT_DIR, TEMP_DIR
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

    def _load_used_story_titles(self) -> set:
        """
        Story titles already posted, so a fresh generation can avoid picking one that was
        already told — even if it's being posted this time under a different topic label
        (e.g. a placeholder "Untold Dark Mystery of History #N" title).
        """
        history_file = BASE_DIR / "posted_history.json"
        if not history_file.exists():
            return set()
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                past_posts = json.load(f)
            return {
                p.get("story_title") or p.get("topic")
                for p in past_posts
                if p.get("published", False) and (p.get("story_title") or p.get("topic"))
            }
        except Exception as e:
            logger.debug(f"Could not load posting history for dedup: {e}")
            return set()

    @staticmethod
    def _scene_start_times(script: VideoScript, word_timestamps: list, total_duration: float) -> List[float]:
        """Scene start times taken from the TTS word timings, so photos change on the right words."""
        counts = [max(1, len(sc.narration.split())) for sc in script.scenes]
        total_words = sum(counts)
        starts, cumulative = [], 0
        for c in counts:
            if word_timestamps:
                idx = min(len(word_timestamps) - 1, int(round(cumulative / total_words * len(word_timestamps))))
                starts.append(0.0 if not starts else float(word_timestamps[idx].start_time))
            else:
                starts.append(total_duration * cumulative / total_words)
            cumulative += c
        return starts

    @staticmethod
    def _plan_photo_shots(scene_images: list, pool: list, scene_durations: List[float],
                          scene_pools: Optional[List[list]] = None, shot_len: float = 3.0) -> List[tuple]:
        """
        Splits every scene into ~3s shots: the scene's own photo first, then photos of the
        scene's subject, then the topic pool. A scene with a single photo keeps it (with a
        different camera move) rather than cutting to something unrelated.
        Returns [(image, seconds)] covering the whole video.
        """
        shots, pool_i = [], 0
        scene_pools = scene_pools or [[] for _ in scene_images]
        everything = [i for i in scene_images if i is not None] + list(pool) + [i for p in scene_pools for i in p]
        fallback = everything[0] if everything else None
        for img, dur, own in zip(scene_images, scene_durations, scene_pools):
            candidates = ([img] if img is not None else []) + list(own)
            n = max(1, int(round(dur / shot_len)))
            for k in range(n):
                if k < len(candidates):
                    pick = candidates[k]
                elif candidates:
                    pick = candidates[k % len(candidates)]
                elif pool:
                    pick = pool[pool_i % len(pool)]
                    pool_i += 1
                else:
                    pick = fallback
                shots.append((pick, dur / n))
        return shots

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
            used_story_titles = self._load_used_story_titles()
            script = self.scriptwriter.generate_script(
                topic=topic, language=language, used_story_titles=used_story_titles
            )

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

        # 4. Photos: one matched photo per scene plus a topic pool for extra shots
        logger.info("Step 4: Fetching real photos for each scene...")
        cards_dir = project_dir / "cards"
        cards_dir.mkdir(parents=True, exist_ok=True)
        blank_card = cards_dir / "card_blank.png"
        Image.new("RGBA", (settings.video_width, settings.video_height), (0, 0, 0, 0)).save(blank_card)

        num_scenes = len(script.scenes)
        scene_starts = self._scene_start_times(script, word_timestamps, total_duration)
        scene_durations = [
            (scene_starts[i + 1] if i + 1 < num_scenes else total_duration) - scene_starts[i]
            for i in range(num_scenes)
        ]

        # Gemini scripts carry exact Wikipedia titles per scene; the first one names the
        # topic far better than a clickbait title like "The Terrifying ... Hole in Space".
        pool_query = next((s.image_query for s in script.scenes if s.image_query), None) or script.title
        image_pool = self.asset_manager.fetch_entity_image_pool(pool_query, count=num_scenes * 2)
        if not image_pool:
            single = self.asset_manager.fetch_real_entity_image(pool_query, exact_title=pool_query != script.title)
            if single:
                image_pool = [single]

        scene_images = []
        for i, scene in enumerate(script.scenes):
            # Prefer a photo matched to what THIS scene says (e.g. "USS Eldridge") over a
            # generic topic-wide photo.
            raw_img = None
            if scene.image_query:
                raw_img = self.asset_manager.fetch_real_entity_image(scene.image_query, exact_title=True)
            if not raw_img:
                raw_img = self.asset_manager.fetch_scene_matched_image(scene.narration)
            scene_images.append(raw_img)

        photo_track_path = None
        cards_concat_path = None
        # Extra ~3s shots for each scene come from that scene's own subject first
        # (White House, CNN, ...) and only then from the topic-wide pool
        scene_pools = []
        for i, scene in enumerate(script.scenes):
            extra_needed = max(0, int(round(scene_durations[i] / 3.0)) - 1)
            extras = []
            if extra_needed and scene.image_query:
                extras = self.asset_manager.fetch_entity_image_pool(scene.image_query, count=extra_needed)
            scene_pools.append(extras)

        if any(scene_images) or image_pool or any(scene_pools):
            # Split screen: a new photo every ~3s, each with its own camera move
            shots = self._plan_photo_shots(scene_images, image_pool, scene_durations, scene_pools)
            photo_track_path = self.video_engine.build_photo_track(
                shots, project_dir / "photo_track", height=settings.video_height // 2
            )
        if not photo_track_path:
            # No usable photos: keep the old full-screen gameplay with (blank) cards
            cards_concat_path = cards_dir / "cards_concat.txt"
            with open(cards_concat_path, "w", encoding="utf-8") as f:
                for i, scene in enumerate(script.scenes):
                    card = blank_card
                    if scene_images[i]:
                        made = self.asset_manager.create_floating_card_overlay(
                            query=scene.image_query or script.title, output_path=cards_dir / f"card_{scene.scene_id}.png",
                            video_width=settings.video_width, video_height=settings.video_height,
                            raw_image=scene_images[i])
                        card = made or blank_card
                    f.write(f"file '{card.resolve()}'\nduration {scene_durations[i]:.4f}\n")
                f.write(f"file '{blank_card.resolve()}'\n")

        # 5. Opening hook + closing comment prompt (replaces the "please like" heart outro)
        logger.info("Step 5: Rendering opening hook and comment prompt overlays...")
        hook_text = script.hook_text or " ".join(script.title.upper().split()[:5])
        hook_concat_path = self.asset_manager.create_hook_overlay(
            output_dir=project_dir / "hook", hook_text=hook_text, total_duration=total_duration,
            video_width=settings.video_width, video_height=settings.video_height,
            center_y=settings.video_height // 4 if photo_track_path else settings.video_height // 3,
        )
        last_is_question = script.scenes and script.scenes[-1].narration.strip().endswith("?")
        cta_start = scene_starts[-1] if last_is_question else max(0.0, total_duration - 3.5)
        outro_concat_path = self.asset_manager.create_comment_cta_overlay(
            output_dir=project_dir / "cta", start=cta_start, total_duration=total_duration,
            options=script.cta_options, video_width=settings.video_width, video_height=settings.video_height,
        )

        # 6. Generate BGM and SFX
        logger.info("Step 6: Synthesizing background ambience and SFX...")
        bgm_path = project_dir / "bgm.aac"
        self.asset_manager.create_ambient_bgm(bgm_path, duration=total_duration + 1.0)
        
        whoosh_path = project_dir / "whoosh.aac"
        self.asset_manager.create_whoosh_sfx(whoosh_path)

        # 7. Final Video Assembly with Multi-layer FFmpeg Composition
        logger.info(f"Step 7: Assembling final video ({'split screen' if photo_track_path else 'full-screen gameplay'})...")
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
            duration=total_duration,
            photo_track_path=photo_track_path,
            hook_concat_path=hook_concat_path,
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
