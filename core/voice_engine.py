import asyncio
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Tuple
import edge_tts
from config.settings import settings

logger = logging.getLogger(__name__)

class WordTimestamp:
    def __init__(self, word: str, start_time: float, end_time: float):
        self.word = word
        self.start_time = start_time
        self.end_time = end_time

    def to_dict(self) -> Dict[str, Any]:
        return {
            "word": self.word,
            "start": self.start_time,
            "end": self.end_time
        }

def probe_audio_duration(audio_path: Path) -> float:
    """Uses ffprobe to obtain exact audio duration in seconds."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path)
    ]
    try:
        output = subprocess.check_output(cmd).decode("utf-8").strip()
        return float(output)
    except Exception as e:
        logger.warning(f"Failed to probe audio duration: {e}")
        return 0.0

class VoiceEngine:
    def __init__(self, voice: str = None, rate: str = "+5%", pitch: str = "+0Hz"):
        self.voice = voice or settings.default_voice_pl
        self.rate = rate
        self.pitch = pitch

    async def generate_speech_with_timestamps(
        self,
        text: str,
        output_audio_path: Path,
        voice: str = None
    ) -> Tuple[float, List[WordTimestamp]]:
        """
        Generates high quality natural TTS audio and extracts exact word-level timestamps.
        Supports both WordBoundary and SentenceBoundary interpolation.
        """
        selected_voice = voice or self.voice
        communicate = edge_tts.Communicate(
            text=text,
            voice=selected_voice,
            rate=self.rate,
            pitch=self.pitch
        )

        word_timestamps: List[WordTimestamp] = []
        sentence_boundaries = []
        audio_chunks = []

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                offset_s = chunk["offset"] / 10_000_000.0
                duration_s = chunk["duration"] / 10_000_000.0
                word = chunk["text"].strip()
                if word:
                    word_timestamps.append(
                        WordTimestamp(
                            word=word,
                            start_time=offset_s,
                            end_time=offset_s + duration_s
                        )
                    )
            elif chunk["type"] == "SentenceBoundary":
                sentence_boundaries.append(chunk)

        output_audio_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_audio_path, "wb") as f:
            for chunk in audio_chunks:
                f.write(chunk)

        # Get exact audio file duration
        total_duration = probe_audio_duration(output_audio_path)

        # If no WordBoundary events received, interpolate from SentenceBoundary
        if not word_timestamps and sentence_boundaries:
            for sb in sentence_boundaries:
                s_offset = sb["offset"] / 10_000_000.0
                s_duration = sb["duration"] / 10_000_000.0
                s_text = sb["text"].strip()
                words = s_text.split()
                if not words:
                    continue

                total_chars = sum(len(w) + 1 for w in words)
                curr_offset = s_offset
                for w in words:
                    w_weight = (len(w) + 1) / total_chars
                    w_dur = s_duration * w_weight
                    word_timestamps.append(
                        WordTimestamp(
                            word=w,
                            start_time=curr_offset,
                            end_time=curr_offset + w_dur
                        )
                    )
                    curr_offset += w_dur

        # Fallback if no boundary events at all (rare)
        if not word_timestamps and text:
            words = text.split()
            if words and total_duration > 0:
                time_per_word = total_duration / len(words)
                for i, w in enumerate(words):
                    word_timestamps.append(
                        WordTimestamp(
                            word=w,
                            start_time=i * time_per_word,
                            end_time=(i + 1) * time_per_word
                        )
                    )

        logger.info(f"Generated TTS audio: {output_audio_path} (Duration: {total_duration:.2f}s, Words: {len(word_timestamps)})")
        return total_duration, word_timestamps

    def generate_sync(self, text: str, output_audio_path: Path, voice: str = None) -> Tuple[float, List[WordTimestamp]]:
        """Synchronous wrapper for generating speech."""
        return asyncio.run(self.generate_speech_with_timestamps(text, output_audio_path, voice))
