"""
config.py - MovYra Bot Configuration & Constants
================================================
All settings are loaded from environment variables (.env file).
Never hard-code your bot token or admin IDs directly here.
"""

import os
from dotenv import load_dotenv

# Load variables from .env file in the same directory
load_dotenv()

# ─── TELEGRAM CREDENTIALS ─────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Comma-separated list of admin Telegram user IDs in .env
# Example: ADMIN_IDS=123456789,987654321
ADMIN_IDS = [
    int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
]

# ─── AUTO-POSTING SETTINGS ────────────────────────────────────────────────────
DEFAULT_INTERVAL_MINUTES = 30    # Post promo every N minutes
RETRY_DELAY_MINUTES      = 5     # Retry a failed send after N minutes
DUPLICATE_WINDOW_HOURS   = 24    # Skip if same promo sent to same group within N hours

# ─── DATABASE ─────────────────────────────────────────────────────────────────
DB_PATH    = os.getenv("DB_PATH", "movyra.db")
BACKUP_DIR = "backups"

# ─── WEBSITE / API ────────────────────────────────────────────────────────────
WEBSITE_BASE_URL = os.getenv("WEBSITE_URL", "https://movyra.com")
WEBSITE_API_URL  = os.getenv("WEBSITE_API_URL", "https://movyra.com/api")

# ─── COMMUNITY GROUP ──────────────────────────────────────────────────────────
MAIN_GROUP_ID   = os.getenv("MAIN_GROUP_ID", "")         # e.g. -1001234567890
MAIN_GROUP_LINK = os.getenv("MAIN_GROUP_LINK", "https://t.me/movyra")

# ─── SCHEDULED DAILY CONTENT TIMES (24-hr, IST) ──────────────────────────────
SCHEDULE_MORNING   = "09:00"   # Daily movie recommendation
SCHEDULE_AFTERNOON = "14:00"   # Trending movie update
SCHEDULE_EVENING   = "18:00"   # OTT release alert
SCHEDULE_NIGHT     = "20:00"   # Movie trivia / poll

# ─── RATE LIMITING (to avoid Telegram flood bans) ────────────────────────────
SEND_DELAY_SECONDS  = 1.5   # Wait between each group message
GROUP_BATCH_SIZE    = 10    # Groups per batch
BATCH_DELAY_SECONDS = 5     # Wait between batches

# ─── LOGGING ──────────────────────────────────────────────────────────────────
LOG_FILE  = "movyra_bot.log"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ─── MISC ─────────────────────────────────────────────────────────────────────
BOT_VERSION  = "1.0.0"
BOT_NAME     = "MovYra Bot"
BOT_ABOUT    = "Official bot for MovYra — Your Movie Universe 🎬"
