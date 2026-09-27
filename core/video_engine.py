import logging
import random
import subprocess
from pathlib import Path
from typing import List, Optional
from config.settings import settings, ASSETS_DIR

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
        """Creates a dynamic video segment from a static image with smooth camera motion."""
        output_segment_path.parent.mkdir(parents=True, exist_ok=True)
        total_frames = max(30, int(duration * self.fps))

        if animation == "zoom_in":
            vf_anim = f"zoompan=z='min(zoom+0.0015,1.15)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={self.width}x{self.height}:fps={self.fps}"
        elif animation == "zoom_out":
            vf_anim = f"zoompan=z='if(lte(zoom,1.0),1.15,max(1.001,zoom-0.0015))':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={self.width}x{self.height}:fps={self.fps}"
        elif animation == "pan_left":
            vf_anim = f"zoompan=z=1.12:d={total_frames}:x='if(lte(on,1),iw/2-(iw/zoom/2),max(0,x-1.2))':y='ih/2-(ih/zoom/2)':s={self.width}x{self.height}:fps={self.fps}"
        else:
            vf_anim = f"zoompan=z=1.12:d={total_frames}:x='if(lte(on,1),0,min(iw-iw/zoom,x+1.2))':y='ih/2-(ih/zoom/2)':s={self.width}x{self.height}:fps={self.fps}"

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

    def get_gameplay_background(self) -> Optional[Path]:
        """Returns a background parkour gameplay video if available in assets/backgrounds."""
        bg_dir = ASSETS_DIR / "backgrounds"
        if not bg_dir.exists():
            return None
        videos = list(bg_dir.glob("*.mp4"))
        if videos:
            return random.choice(videos)
        return None

    def build_photo_track(self, photos: List[tuple], work_dir: Path, height: int) -> Optional[Path]:
        """
        Renders the top half of a split-screen video: each (PIL image, seconds) gets its own
        Ken Burns move (zoom in / zoom out / pan left / pan right, rotating) and they are cut
        together hard. Short shots with constant motion keep viewers watching.
        """
        from PIL import Image, ImageOps
        work_dir.mkdir(parents=True, exist_ok=True)
        fps = self.fps
        moves = [
            ("1+0.14*on/{d}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
            ("1.14-0.14*on/{d}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
            ("1.15", "(iw-iw/zoom)*on/{d}", "ih/2-(ih/zoom/2)"),
            ("1.15", "(iw-iw/zoom)*(1-on/{d})", "ih/2-(ih/zoom/2)"),
        ]
        clips = []
        for i, (img, seconds) in enumerate(photos):
            frames = max(2, int(round(seconds * fps)))
            # 2x oversampling keeps zoompan motion smooth instead of jittery
            src = ImageOps.fit(img.convert("RGB"), (self.width * 2, height * 2), method=Image.Resampling.LANCZOS)
            src_path = work_dir / f"photo_{i:02d}.jpg"
            src.save(src_path, "JPEG", quality=92)
            z, x, y = (e.format(d=frames) for e in moves[i % len(moves)])
            clip = work_dir / f"shot_{i:02d}.mp4"
            cmd = [
                "ffmpeg", "-y", "-loglevel", "error", "-i", str(src_path),
                "-vf", f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={self.width}x{height}:fps={fps},format=yuv420p",
                "-frames:v", str(frames), "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-r", str(fps), str(clip)
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                logger.warning(f"Ken Burns shot {i} failed: {result.stderr.decode('utf-8')[-300:]}")
                continue
            clips.append(clip)
        if not clips:
            return None
        concat_txt = work_dir / "shots.txt"
        concat_txt.write_text("".join(f"file '{c.resolve()}'\n" for c in clips), encoding="utf-8")
        track = work_dir / "photo_track.mp4"
        result = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                                 "-i", str(concat_txt), "-c", "copy", str(track)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            logger.warning(f"Photo track concat failed: {result.stderr.decode('utf-8')[-300:]}")
            return None
        return track

    def assemble_final_video(
        self,
        segment_paths: List[Path],
        subtitles_concat_path: Path,
        voice_audio_path: Path,
        bgm_audio_path: Path,
        output_video_path: Path,
        cards_concat_path: Optional[Path] = None,
        outro_concat_path: Optional[Path] = None,
        whoosh_sfx_path: Optional[Path] = None,
        duration: Optional[float] = None,
        photo_track_path: Optional[Path] = None,
        hook_concat_path: Optional[Path] = None
    ) -> Path:
        """
        Assembles full video with background gameplay, floating entity photo cards,
        TikTok double-tap like heart outro animation, and Hormozi karaoke subtitles.
        """
        gameplay_bg = self.get_gameplay_background() if settings.use_gameplay_background else None
        
        if gameplay_bg and gameplay_bg.exists():
            logger.info(f"Using viral gameplay background: {gameplay_bg.name}")
            
            # Probe background duration
            bg_dur = 60.0
            try:
                probe_cmd = [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(gameplay_bg)
                ]
                pr = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                bg_dur = float(pr.stdout.decode().strip())
            except Exception:
                bg_dur = 60.0

            needed_dur = duration or 35.0
            max_offset = max(0.0, bg_dur - needed_dur - 2.0)
            start_offset = random.uniform(0.0, max_offset) if max_offset > 0 else 0.0
            
            inputs = ["-ss", f"{start_offset:.2f}", "-stream_loop", "-1", "-i", str(gameplay_bg)]
            idx = 1
            grain = f",noise=alls={settings.grain_intensity}:allf=t+u" if settings.apply_film_grain else ""

            if photo_track_path and photo_track_path.exists():
                # Split screen: big moving photos on top, gameplay on the bottom half
                half = self.height // 2
                inputs += ["-i", str(photo_track_path)]
                filters = [
                    f"[0:v]scale={self.width}:{half}:force_original_aspect_ratio=increase,crop={self.width}:{half},setsar=1[gbot]",
                    f"[{idx}:v]scale={self.width}:{half},setsar=1,tpad=stop_mode=clone:stop_duration=60[ptop]",
                    f"[ptop][gbot]vstack=inputs=2{grain}[v0]",
                ]
                idx += 1
                overlays = [outro_concat_path, hook_concat_path, subtitles_concat_path]
            else:
                filters = [f"[0:v]scale={self.width}:{self.height}:force_original_aspect_ratio=increase,crop={self.width}:{self.height}{grain}[v0]"]
                overlays = [cards_concat_path, outro_concat_path, hook_concat_path, subtitles_concat_path]

            last = "v0"
            for n, ov in enumerate(p for p in overlays if p):
                inputs += ["-f", "concat", "-safe", "0", "-i", str(ov)]
                filters.append(f"[{last}][{idx}:v]overlay=0:0:shortest=1[v{n + 1}]")
                last = f"v{n + 1}"
                idx += 1

            inputs += ["-i", str(voice_audio_path), "-i", str(bgm_audio_path)]
            voice_i, bgm_i = idx, idx + 1
            idx += 2
            audio = f"[{voice_i}:a]volume=1.0[voice];[{bgm_i}:a]volume=0.08[bgm]"
            mix = "[voice][bgm]"
            if whoosh_sfx_path and whoosh_sfx_path.exists():
                # Impact whoosh on the opening hook
                inputs += ["-i", str(whoosh_sfx_path)]
                audio += f";[{idx}:a]volume=0.7[sfx]"
                mix += "[sfx]"
                idx += 1
            n_audio = mix.count("[")
            audio += f";{mix}amix=inputs={n_audio}:duration=first:dropout_transition=2:normalize=0[aout]"

            cmd = [
                "ffmpeg", "-y", *inputs,
                "-filter_complex", ";".join(filters) + f";[{last}]null[vout];{audio}",
                "-map", "[vout]",
                "-map", "[aout]",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "18",
                "-profile:v", "high",
                "-level", "4.2",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", self.audio_bitrate,
                "-ar", "44100",
                "-ac", "2",
                "-movflags", "+faststart",
                "-shortest"
            ]
        else:
            # Fallback
            work_dir = output_video_path.parent
            concat_txt = work_dir / "concat_list.txt"
            with open(concat_txt, "w") as f:
                for p in segment_paths:
                    f.write(f"file '{p.resolve()}'\n")

            vf_filter = "[0:v][1:v]overlay=0:0:shortest=1[vout]"
            af_filter = "[2:a]volume=1.0[voice];[3:a]volume=0.08[bgm];[voice][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"

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
                "-preset", "fast",
                "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", self.audio_bitrate,
                "-shortest"
            ]

        # Anti-Shadowban metadata spoofing (iPhone EXIF + bitexact)
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

        logger.info(f"Rendering final video with TikTok like outro to: {output_video_path}")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            logger.error(f"FFmpeg assembly failed: {result.stderr.decode('utf-8')}")
            raise RuntimeError(f"FFmpeg error: {result.stderr.decode('utf-8')}")

        return output_video_path
