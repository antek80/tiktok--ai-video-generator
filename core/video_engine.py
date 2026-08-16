import logging
import subprocess
from pathlib import Path
from typing import List, Optional
from config.settings import settings

logger = logging.getLogger(__name__)

class VideoEngine:
    def __init__(
        self,
        width: int = None,
        height: int = None,
        fps: int = None,
        audio_bitrate: str = None
    ):
        self.width = width or settings.video_width
        self.height = height or settings.video_height
        self.fps = fps or settings.fps
        self.audio_bitrate = audio_bitrate or settings.audio_bitrate

    def create_scene_segment(
        self,
        image_path: Path,
        duration: float,
        animation: str,
        output_segment_path: Path
    ) -> Path:
        """
        Creates a dynamic video segment from a static image with smooth camera motion.
        """
        output_segment_path.parent.mkdir(parents=True, exist_ok=True)
        total_frames = max(30, int(duration * self.fps))

        if animation == "zoom_in":
            vf_anim = f"zoompan=z='min(zoom+0.0015,1.15)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={self.width}x{self.height}:fps={self.fps}"
        elif animation == "zoom_out":
            vf_anim = f"zoompan=z='if(lte(zoom,1.0),1.15,max(1.001,zoom-0.0015))':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={self.width}x{self.height}:fps={self.fps}"
        elif animation == "pan_left":
            vf_anim = f"zoompan=z=1.12:d={total_frames}:x='if(lte(on,1),iw/2-(iw/zoom/2),max(0,x-1.2))':y='ih/2-(ih/zoom/2)':s={self.width}x{self.height}:fps={self.fps}"
        elif animation == "pan_right":
            vf_anim = f"zoompan=z=1.12:d={total_frames}:x='if(lte(on,1),0,min(iw-iw/zoom,x+1.2))':y='ih/2-(ih/zoom/2)':s={self.width}x{self.height}:fps={self.fps}"
        else:
            vf_anim = f"zoompan=z='min(zoom+0.001,1.10)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={self.width}x{self.height}:fps={self.fps}"

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(image_path),
            "-c:v", "libx264",
            "-preset", "fast",
            "-tune", "stillimage",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-vf", f"scale={self.width}:{self.height}:force_original_aspect_ratio=increase,crop={self.width}:{self.height},{vf_anim}",
            "-t", f"{duration:.3f}",
            "-r", str(self.fps),
            "-an",
            str(output_segment_path)
        ]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            logger.error(f"Error creating segment: {result.stderr.decode('utf-8')}")
            raise RuntimeError(f"FFmpeg segment error: {result.stderr.decode('utf-8')}")

        return output_segment_path

    def assemble_final_video(
        self,
        segment_paths: List[Path],
        subtitles_concat_path: Path,
        voice_audio_path: Path,
        bgm_audio_path: Path,
        output_video_path: Path,
        whoosh_sfx_path: Optional[Path] = None
    ) -> Path:
        """
        Concatenates segments, overlays dynamic subtitle stream, mixes audio, applies anti-shadowban
        noise & metadata spoofing, and produces final ready-to-publish MP4.
        """
        work_dir = output_video_path.parent
        concat_txt = work_dir / "concat_list.txt"
        
        with open(concat_txt, "w") as f:
            for p in segment_paths:
                f.write(f"file '{p.resolve()}'\n")

        # Video filter: apply subtle grain on background video, then overlay dynamic subtitles
        if settings.apply_film_grain:
            vf_filter = f"[0:v]noise=alls={settings.grain_intensity}:allf=t+u[vbase];[vbase][1:v]overlay=0:0:shortest=1[vout]"
        else:
            vf_filter = "[0:v][1:v]overlay=0:0:shortest=1[vout]"

        # Audio mixing: Primary TTS Voiceover + Background Ambient Music
        af_filter = "[2:a]volume=1.0[voice];[3:a]volume=0.10[bgm];[voice][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_txt),
            "-f", "concat",
            "-safe", "0",
            "-i", str(subtitles_concat_path),
            "-i", str(voice_audio_path),
            "-i", str(bgm_audio_path),
            "-filter_complex", f"{vf_filter};{af_filter}",
            "-map", "[vout]",
            "-map", "[aout]",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "19",
            "-profile:v", "high",
            "-level", "4.2",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", self.audio_bitrate,
            "-ar", "44100",
            "-ac", "2",
            "-movflags", "+faststart",
            "-shortest",
        ]

        # Anti-Shadowban metadata spoofing (iPhone EXIF + bitexact stripping)
        if settings.spoof_device_metadata:
            cmd.extend([
                "-fflags", "+bitexact",
                "-flags:v", "+bitexact",
                "-map_metadata", "-1",
                "-metadata", f"make={settings.spoofed_make}",
                "-metadata", f"model={settings.spoofed_model}",
                "-metadata", "creation_time=now"
            ])

        cmd.append(str(output_video_path))

        logger.info(f"Rendering final anti-shadowban video to: {output_video_path}")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            logger.error(f"FFmpeg assembly failed: {result.stderr.decode('utf-8')}")
            raise RuntimeError(f"FFmpeg error: {result.stderr.decode('utf-8')}")

        if concat_txt.exists():
            concat_txt.unlink()

        return output_video_path
