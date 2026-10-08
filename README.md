# AI YouTube Channel Kit

A pipeline that turns a topic into a reviewed, uploaded YouTube video:
**Claude (ideas + script) → edge-tts (voiceover) → Pillow/ffmpeg (video) → YouTube Data API (upload).**

Default niche: *practical AI tools and workflows for small-business owners* (edit `aichannel/config.py`).

## Honest expectations
- No tool can guarantee profit. Most channels earn nothing for months.
- **You must create the channel** and own the Google account; this kit can't do that for you.
- YouTube Partner Program (ads) needs **1,000 subs + 4,000 public watch hours (12 mo)** or **10M Shorts views (90 days)**;
  the lower tier (500 subs, 3 public uploads in 90 days, 3,000 hours / 3M Shorts views) unlocks fan funding and early perks.
- Since July 2025 YouTube demonetizes **"inauthentic" mass-produced / repetitive content**. Pure unreviewed AI slop
  gets rejected. To stay monetizable: fact-check every script, add your own screen recordings/examples/opinions,
  vary format, and don't upload dozens a day.
- Disclose realistic synthetic media (the uploader sets `containsSyntheticMedia`).

## Setup
```bash
pip install -r requirements.txt
sudo apt install ffmpeg           # or brew install ffmpeg
export ANTHROPIC_API_KEY=...      # for scripts
# For upload: Google Cloud Console -> enable YouTube Data API v3 -> OAuth client (Desktop) -> save as client_secret.json
```

## Use
```bash
python -m aichannel ideas -n 10
python -m aichannel make "How to summarize long PDFs with AI" --minutes 6
# review output/<slug>/script.json and video.mp4, then:
python -m aichannel make "How to summarize long PDFs with AI" --script output/<slug>/script.json --upload
```
Uploads default to **private** so you can check them before going public. Unverified API projects
may force private uploads until you pass Google's audit.

## Ways it makes money (in order of realism)
1. **Affiliate links** in descriptions for tools you actually recommend (needs no YPP).
2. **Services/leads**: use the channel to sell AI setup consulting to small businesses.
3. **Ads** after reaching YPP thresholds.
4. Sponsorships once you have a consistent audience.

## Weekly routine
Pick 2 ideas from `ideas` → generate → fact-check and add real screen recordings → publish 1–2 videos →
check YouTube Studio analytics (CTR, retention) and double down on what gets watched.
