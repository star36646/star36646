"""Text-to-speech with edge-tts (free). Falls back to silence if offline so the pipeline can be tested."""
import asyncio
import subprocess

from . import config


def synth(text: str, path: str) -> str:
    try:
        import edge_tts

        asyncio.run(edge_tts.Communicate(text, config.VOICE).save(path))
        return path
    except Exception as e:  # network blocked, etc.
        print(f"  [tts] falling back to silent audio ({type(e).__name__})")
        secs = max(3, len(text.split()) / 2.5)
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
             "anullsrc=r=44100:cl=mono", "-t", f"{secs:.1f}", "-q:a", "9", path],
            check=True,
        )
        return path
