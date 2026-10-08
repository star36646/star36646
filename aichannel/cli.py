"""Usage:
  python -m aichannel ideas [-n 10]
  python -m aichannel make "topic" [--minutes 6] [--upload] [--script script.json]
"""
import argparse
import json
import os
import re

from . import config, render, script_gen, tts


def build_video(data: dict, workdir: str) -> str:
    os.makedirs(workdir, exist_ok=True)
    scenes, clips = data["scenes"], []
    for i, sc in enumerate(scenes, 1):
        print(f"scene {i}/{len(scenes)}: {sc['title']}")
        png, mp3, mp4 = (os.path.join(workdir, f"{i:02d}.{e}") for e in ("png", "mp3", "mp4"))
        render.slide(sc, i, len(scenes), png)
        tts.synth(sc["narration"], mp3)
        render.clip(png, mp3, mp4)
        clips.append(mp4)
    out = os.path.join(workdir, "video.mp4")
    render.concat(clips, out)
    return out


def main():
    p = argparse.ArgumentParser(prog="aichannel")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("ideas"); a.add_argument("-n", type=int, default=10)
    m = sub.add_parser("make"); m.add_argument("topic")
    m.add_argument("--minutes", type=int, default=6)
    m.add_argument("--script", help="use an existing script JSON instead of calling Claude")
    m.add_argument("--upload", action="store_true")
    m.add_argument("--privacy", default=config.DEFAULT_PRIVACY, choices=["private", "unlisted", "public"])
    args = p.parse_args()

    if args.cmd == "ideas":
        for i in script_gen.ideas(args.n):
            print(f"- {i['topic']}  [{i['search_phrase']}]\n    {i['why_it_works']}")
        return

    data = json.load(open(args.script)) if args.script else script_gen.script(args.topic, args.minutes)
    slug = re.sub(r"[^a-z0-9]+", "-", args.topic.lower()).strip("-")[:50]
    workdir = os.path.join(config.OUTPUT_DIR, slug)
    os.makedirs(workdir, exist_ok=True)
    json.dump(data, open(os.path.join(workdir, "script.json"), "w"), indent=2)
    print(f"Script saved to {workdir}/script.json -- REVIEW IT for accuracy before publishing.")
    video = build_video(data, workdir)
    print("video:", video)
    if args.upload:
        from . import upload
        print("uploaded:", upload.upload(video, data["title"], data["description"], data["tags"], args.privacy))
