"""Generate topic ideas and full video scripts with Claude."""
import json
import re

import anthropic

from . import config

_client = None


def _ask(prompt: str, max_tokens: int = 4000) -> str:
    global _client
    _client = _client or anthropic.Anthropic()
    msg = _client.messages.create(
        model=config.MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def _json(text: str):
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    return json.loads(m.group(1) if m else text)


def ideas(n: int = 10, avoid: list[str] | None = None) -> list[dict]:
    prompt = f"""You plan videos for a YouTube channel.
Niche: {config.NICHE}
Audience: {config.AUDIENCE}
Style: {config.CHANNEL_STYLE}

Give {n} video ideas that people actually search for (problem-first, e.g. "How to ..."),
each with a specific outcome. Avoid these already-made topics: {avoid or []}.
Return only JSON: [{{"topic": str, "search_phrase": str, "why_it_works": str}}]"""
    return _json(_ask(prompt))


def script(topic: str, minutes: int = 6) -> dict:
    words = minutes * 150
    prompt = f"""Write a YouTube video script (~{words} words of narration).
Channel niche: {config.NICHE}. Audience: {config.AUDIENCE}. Style: {config.CHANNEL_STYLE}.
Topic: {topic}

Rules:
- Open with the concrete payoff in the first 15 seconds. No filler intro.
- Give real, accurate, step-by-step content. Do not invent statistics, quotes or product features.
  If unsure whether a feature exists, say what to check instead.
- Split into 8-14 scenes. Each scene is one on-screen slide with a short title and 2-4 bullets
  (max 8 words each) and the narration that plays over it.
- End with one clear takeaway and a soft call to action.
Return only JSON:
{{"title": str (<=70 chars, clickable but not misleading), "description": str (with chapters placeholder-free),
 "tags": [str], "scenes": [{{"title": str, "bullets": [str], "narration": str}}]}}"""
    data = _json(_ask(prompt, max_tokens=8000))
    assert data.get("scenes"), "model returned no scenes"
    return data
