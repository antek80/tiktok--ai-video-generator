import logging
import subprocess
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("bg-downloader")

BASE_DIR = Path("/Users/antoniborawski/repos/tiktok--ai-video-generator")
BG_DIR = BASE_DIR / "assets/backgrounds"
BG_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR = BASE_DIR / "temp/bg_downloads"
TEMP_DIR.mkdir(parents=True, exist_ok=True)
YT_DLP_BIN = BASE_DIR / ".venv/bin/yt-dlp"

TARGET_SOURCES = [
    # 1. Minecraft Parkour 60fps Vertical
    {"id": "7yl7Wc1dtWc", "category": "minecraft", "slices": 12},
    {"id": "2SWW4U4TKOA", "category": "minecraft", "slices": 12},
    
    # 2. GTA 5 Mega Ramp / Car Parkour Stunts
    {"id": "8VmCwcGw6SI", "category": "gta5", "slices": 12},
    {"id": "ZtLrNBdXT7M", "category": "gta5", "slices": 10},
    
    # 3. Subway Surfers Vertical 60fps
    {"id": "ldDJr3aggEE", "category": "subway", "slices": 10},
    
    # 4. CS:GO / CS2 Surfing Vertical 60fps
    {"id": "KYqob2oKN3I", "category": "csgosurf", "slices": 8}
]

def slice_existing_minecraft():
    """Slices existing 150MB minecraft_parkour.mp4 into 12 unique clips."""
    existing_mc = BG_DIR / "minecraft_parkour.mp4"
    if not existing_mc.exists():
        return 0
    
    logger.info(f"Slicing existing {existing_mc.name} into 12 distinct 60s clips...")
    created = 0
    for i in range(12):
        start_t = i * 45.0
        out_clip = BG_DIR / f"mc_base_clip_{i+1:02d}.mp4"
        if out_clip.exists() and out_clip.stat().st_size > 100000:
            created += 1
            continue
            
        ff_cmd = [
            "ffmpeg", "-y",
            "-ss", f"{start_t:.1f}",
            "-i", str(existing_mc),
            "-t", "65.0",
            "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=60",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "19",
            "-an",
            str(out_clip)
        ]
        subprocess.run(ff_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if out_clip.exists() and out_clip.stat().st_size > 100000:
            created += 1
            logger.info(f"  ✅ Created {out_clip.name}")
    return created

def run_download_pipeline():
    total_clips = slice_existing_minecraft()
    
    for item in TARGET_SOURCES:
        vid_id = item["id"]
        cat = item["category"]
        slices_count = item["slices"]
        url = f"https://www.youtube.com/watch?v={vid_id}"
        
        raw_file = TEMP_DIR / f"{cat}_{vid_id}.mp4"
        logger.info(f"Downloading stream for {cat} ({vid_id})...")
        
        cmd = [
            str(YT_DLP_BIN),
            "--extractor-args", "youtube:player_client=android",
            "-f", "b[height<=1080]/bv[height<=1080]+ba/b",
            "--no-playlist",
            "--no-check-certificates",
            "-o", str(raw_file),
            url
        ]
        
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if not raw_file.exists() or raw_file.stat().st_size < 50000:
            logger.warning(f"Failed to download {vid_id}: {res.stderr.decode('utf-8')[:200]}")
            continue
            
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(raw_file)
        ]
        p_res = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            duration = float(p_res.stdout.decode().strip())
        except Exception:
            duration = 180.0
            
        slice_len = 65.0
        step = max(35.0, (duration - 15.0) / max(1, slices_count))
        
        logger.info(f"Slicing {raw_file.name} (Length: {duration:.1f}s) into {slices_count} vertical clips...")
        
        for s in range(slices_count):
            start_time = s * step
            if start_time + 30.0 > duration:
                break
                
            out_path = BG_DIR / f"{cat}_{vid_id}_{s+1:02d}.mp4"
            
            ff_cmd = [
                "ffmpeg", "-y",
                "-ss", f"{start_time:.1f}",
                "-i", str(raw_file),
                "-t", f"{slice_len:.1f}",
                "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=60",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "19",
                "-an",
                str(out_path)
            ]
            
            subprocess.run(ff_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if out_path.exists() and out_path.stat().st_size > 100000:
                total_clips += 1
                logger.info(f"  ✅ [{total_clips}] Saved {out_path.name}")

        if raw_file.exists():
            raw_file.unlink()

    all_bgs = list(BG_DIR.glob("*.mp4"))
    logger.info(f"=== COMPLETED: Total {len(all_bgs)} background video clips available in {BG_DIR} ===")

if __name__ == "__main__":
    run_download_pipeline()
