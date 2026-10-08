"""Render slides with Pillow and assemble the video with ffmpeg."""
import os
import subprocess
import textwrap

from PIL import Image, ImageDraw, ImageFont

from . import config

BG, FG, ACCENT = (15, 23, 42), (241, 245, 249), (56, 189, 248)
_FONTS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
          "/System/Library/Fonts/Helvetica.ttc", "C:/Windows/Fonts/arialbd.ttf"]


def _font(size):
    for f in _FONTS:
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def slide(scene: dict, idx: int, total: int, path: str):
    img = Image.new("RGB", (config.WIDTH, config.HEIGHT), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 24, config.HEIGHT], fill=ACCENT)
    y = 140
    for line in textwrap.wrap(scene["title"], 28):
        d.text((120, y), line, font=_font(88), fill=FG)
        y += 110
    y += 40
    for b in scene.get("bullets", []):
        for i, line in enumerate(textwrap.wrap(b, 50)):
            d.text((120, y), ("•  " if i == 0 else "    ") + line, font=_font(54), fill=(203, 213, 225))
            y += 75
        y += 20
    d.text((120, config.HEIGHT - 90), f"{idx}/{total}", font=_font(36), fill=ACCENT)
    img.save(path)


def clip(image: str, audio: str, out: str):
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", image, "-i", audio,
         "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p", "-r", "24",
         "-c:a", "aac", "-b:a", "160k", "-shortest", out],
        check=True,
    )


def concat(clips: list[str], out: str):
    lst = out + ".txt"
    with open(lst, "w") as f:
        f.writelines(f"file '{os.path.abspath(c)}'\n" for c in clips)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", lst, "-c", "copy", out], check=True)
