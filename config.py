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
    "meta-llama/llama-4-maverick:free",
    "qwen/qwen2.5-vl-72b-instruct:free",
    "google/gemini-2.0-flash-exp:free",
]

TEXT_MODELS = [
    "meta-llama/llama-4-maverick:free",
    "deepseek/deepseek-r1:free",
    "meta-llama/llama-3.3-70b-instruct:free",
]

# Max characters accepted for a pasted essay (Telegram message limit headroom)
MAX_ANSWER_LENGTH = 4000

# How many days of inactivity before we no longer offer "Continue" on /start
# (purely cosmetic safeguard; pending_data is kept regardless)
RESUME_OFFER_DAYS = 14
