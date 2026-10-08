"""Channel settings. Edit NICHE and the rest to fit your channel."""
import os

NICHE = "Practical AI tools and workflows for small-business owners and freelancers"
AUDIENCE = "busy non-technical people who want to save time with AI"
CHANNEL_STYLE = "clear, honest, concrete; no hype; every video shows a real, repeatable workflow"
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")
VOICE = os.environ.get("TTS_VOICE", "en-US-AndrewMultilingualNeural")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "output")
WIDTH, HEIGHT = 1920, 1080
# Upload as private first so you can review before publishing.
DEFAULT_PRIVACY = "private"
# Realistic AI-generated voice/visuals: YouTube asks you to disclose altered/synthetic content.
CONTAINS_SYNTHETIC_MEDIA = True
