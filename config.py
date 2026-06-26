"""
Central configuration. All environment-dependent and tunable values live here
so nothing is hardcoded deep inside handlers or services.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Telegram ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "change-this-to-a-random-string")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_BASE_URL}{WEBHOOK_PATH}" if WEBHOOK_BASE_URL else ""

# --- Server ---
PORT = int(os.getenv("PORT", "8080"))

# --- Database ---
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./ielts_bot.db")

# --- OpenRouter / AI ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

# Swappable model list. First entry is tried first; if it fails (rate limit,
# removed, error), the client falls through to the next one automatically.
# IMPORTANT: free models on OpenRouter rotate — check https://openrouter.ai/models
# periodically and update this list. This is the ONE place that needs editing
# when a free model dies or gets pulled.
VISION_MODELS = [
    "nvidia/nemotron-nano-12b-v2-vl:free",
    # NOTE: this is currently the ONLY confirmed vision-capable free model
    # from our last live check of openrouter.ai/api/v1/models (see README).
    # If this one fails/gets pulled, check the live model list again rather
    # than guessing -- an unverified "vision" model that's actually text-only
    # will fail Task 1 image reads silently or with confusing errors.
]

TEXT_MODELS = [
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "openai/gpt-oss-120b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
]

# Max characters accepted for a pasted essay (Telegram message limit headroom)
MAX_ANSWER_LENGTH = 4000

# How many days of inactivity before we no longer offer "Continue" on /start
# (purely cosmetic safeguard; pending_data is kept regardless)
RESUME_OFFER_DAYS = 14
