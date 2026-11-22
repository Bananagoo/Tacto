"""The Together models the voice layer uses, in one place.

Chosen on 22 Nov 2026 from the account's own model list (GET /v1/models) and Together's
docs, then checked with `scripts/together_smoke.py`. Model names go stale: rerun the
smoke script before trusting these, and change them only here.
"""

from __future__ import annotations

BASE_URL = "https://api.together.ai/v1"

# Speech to text. The only Whisper on the serverless list; it takes a prompt, which the
# other serverless transcribers ignore.
STT_MODEL = "openai/whisper-large-v3"

# Grades a spoken answer into a fixed label. Small, on the serverless list with structured
# outputs, and the one model Together's docs show with reasoning switched off.
GRADER_MODEL = "Qwen/Qwen3.5-9B"

# Text to speech for the prewritten tutor lines. The cheapest on the list; it always
# answers at 24 kHz whatever sample rate is asked for.
TTS_MODEL = "hexgrad/Kokoro-82M"
TTS_VOICE = "af_heart"
