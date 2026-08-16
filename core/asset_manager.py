import logging
import math
from pathlib import Path
from typing import List, Optional
from PIL import Image, ImageDraw, ImageFont
from config.settings import settings

logger = logging.getLogger(__name__)

class AssetManager:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.gemini_api_key

    def generate_image_for_scene(
        self,
        prompt: str,
        scene_id: int,
        output_path: Path,
        topic: str = ""
    ) -> Path:
        """
        Generates or prepares a 1080x1920 9:16 image for the scene.
        Uses Gemini Imagen if API key is provided, or creates a vibrant cinematic gradient visual.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if self.api_key:
            try:
                from google import genai
                client = genai.Client(api_key=self.api_key)
                
                # Request vertical 9:16 image
                enhanced_prompt = f"{prompt}, cinematic vertical 9:16 portrait composition, 8k resolution, dramatic lighting, highly detailed, photorealistic, trending on artstation"
                
                result = client.models.generate_images(
                    model="imagen-3.0-generate-002",
                    prompt=enhanced_prompt,
                    config=dict(
                        number_of_images=1,
                        aspect_ratio="9:16",
                        output_mime_type="image/jpeg",
                    ),
                )
                
                for generated_image in result.generated_images:
                    with open(output_path, "wb") as f:
                        f.write(generated_image.image.image_bytes)
                    logger.info(f"Generated AI image for scene {scene_id}: {output_path}")
                    return output_path
            except Exception as e:
                logger.warning(f"Imagen generation failed ({e}), creating cinematic procedural fallback image.")

        # Fallback procedural generation
        self._create_cinematic_fallback_image(prompt, scene_id, output_path, topic)
        return output_path

    def _create_cinematic_fallback_image(self, prompt: str, scene_id: int, output_path: Path, topic: str):
        """Generates a rich, vibrant 1080x1920 background image with lighting effects."""
        width = settings.video_width
        height = settings.video_height
        
        # Color palettes per scene
        palettes = [
            ((15, 23, 42), (88, 28, 135), (236, 72, 153)),   # Slate to Purple to Pink
            ((10, 15, 30), (14, 116, 144), (59, 130, 246)),  # Deep Blue to Cyan
            ((24, 24, 27), (180, 83, 9), (245, 158, 11)),   # Dark Amber to Gold
            ((15, 23, 42), (5, 150, 105), (16, 185, 129)),   # Emerald Dark to Bright
            ((17, 24, 39), (225, 29, 72), (244, 63, 94)),   # Crimson to Rose
        ]
        
        c1, c2, c3 = palettes[scene_id % len(palettes)]
        image = Image.new("RGB", (width, height), c1)
        draw = ImageDraw.Draw(image)
        
        # Draw smooth vertical radial/linear gradient
        for y in range(height):
            ratio = y / height
            r = int(c1[0] * (1 - ratio) + c2[0] * ratio)
            g = int(c1[1] * (1 - ratio) + c2[1] * ratio)
            b = int(c1[2] * (1 - ratio) + c2[2] * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Add luminous glow circles
        glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        
        cx, cy = width // 2, height // 3 + (scene_id * 120) % (height // 3)
        radius = 450
        for r in range(radius, 0, -15):
            alpha = int(45 * (1 - (r / radius)))
            glow_draw.ellipse(
                [cx - r, cy - r, cx + r, cy + r],
                fill=(c3[0], c3[1], c3[2], alpha)
            )

        # Composite glow onto background
        image = Image.alpha_composite(image.convert("RGBA"), glow).convert("RGB")
        
        # Save image
        image.save(output_path, "JPEG", quality=95)
        logger.info(f"Created fallback visual for scene {scene_id}: {output_path}")

    def create_whoosh_sfx(self, output_path: Path) -> Path:
        """Generates a synthetic whoosh sound effect using FFmpeg lavfi."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists():
            return output_path
            
        import subprocess
        # Generate 0.4s filtered noise whoosh
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "anoisesrc=d=0.4:c=pink:r=44100:a=0.3",
            "-af", "bandpass=f=800:width_type=h:w=500,afade=t=in:ss=0:d=0.15,afade=t=out:st=0.15:d=0.25,volume=0.4",
            str(output_path)
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except Exception as e:
            logger.warning(f"Could not generate synthetic whoosh: {e}")
        return output_path

    def create_ambient_bgm(self, output_path: Path, duration: float) -> Path:
        """Generates a smooth, subtle lo-fi ambient background track using FFmpeg lavfi."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        import subprocess
        
        # Generate warm, gentle ambient chord drone
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"sine=frequency=220:duration={duration}",
            "-f", "lavfi",
            "-i", f"sine=frequency=277.18:duration={duration}",
            "-f", "lavfi",
            "-i", f"sine=frequency=329.63:duration={duration}",
            "-filter_complex",
            f"[0:a][1:a][2:a]amix=inputs=3:duration=first[mixed];[mixed]lowpass=f=600,volume=0.08,afade=t=in:ss=0:d=1.0,afade=t=out:st={max(0.1, duration - 1.5)}:d=1.5[out]",
            "-map", "[out]",
            "-c:a", "aac",
            "-b:a", "192k",
            str(output_path)
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except Exception as e:
            logger.warning(f"Could not generate synthetic ambient BGM: {e}")
        return output_path
