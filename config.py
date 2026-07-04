"""
Central config — loads everything from .env
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _env_str(key: str, default: str = "") -> str:
    value = os.getenv(key, default)
    if value is None:
        return ""
    return value.strip()

# Groq
GROQ_API_KEY = _env_str("GROQ_API_KEY", "")
GROQ_MODEL = _env_str("GROQ_MODEL", "llama3-70b-8192")

# Google
GOOGLE_CLIENT_ID = _env_str("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = _env_str("GOOGLE_CLIENT_SECRET", "")
GOOGLE_ACCESS_TOKEN = _env_str("GOOGLE_ACCESS_TOKEN", "")
GOOGLE_REFRESH_TOKEN = _env_str("GOOGLE_REFRESH_TOKEN", "")
TIMEZONE = _env_str("TIMEZONE", "Asia/Kolkata")

# Notion
NOTION_TOKEN = _env_str("NOTION_TOKEN", "")
NOTION_BRIEFING_PARENT_PAGE_ID = _env_str("NOTION_BRIEFING_PARENT_PAGE_ID", "")
NOTION_TASKS_DATABASE_ID = _env_str("NOTION_TASKS_DATABASE_ID", "")
NOTION_FINANCE_DATABASE_ID = _env_str("NOTION_FINANCE_DATABASE_ID", "")
NOTION_MEETINGS_PARENT_PAGE_ID = _env_str("NOTION_MEETINGS_PARENT_PAGE_ID", "")

# Email
YOUR_EMAIL = _env_str("YOUR_EMAIL", "")
YOUR_NAME = _env_str("YOUR_NAME", "there")
EMAIL_POLL_INTERVAL = int(os.getenv("EMAIL_POLL_INTERVAL", "30"))
WATCHED_DOMAINS = [d.strip() for d in _env_str("WATCHED_DOMAINS", "").split(",") if d.strip()]
WATCHED_ADDRESSES = [a.strip() for a in _env_str("WATCHED_ADDRESSES", "").split(",") if a.strip()]
TRIGGER_KEYWORDS = [k.strip().lower() for k in _env_str("TRIGGER_KEYWORDS", "invoice,meeting,schedule,deadline").split(",") if k.strip()]

# App
PORT = int(os.getenv("PORT", "8000"))
CITY = _env_str("CITY", "Chennai")
TEMP_UNIT = _env_str("TEMP_UNIT", "celsius")
EMAIL_HISTORY_DAYS = int(os.getenv("EMAIL_HISTORY_DAYS", "7"))
SECRET_KEY = _env_str("SECRET_KEY", "changeme")
SKIP_EXISTING_ON_BOOT = os.getenv("SKIP_EXISTING_ON_BOOT", "false").strip().lower() in ("1", "true", "yes", "on")

GOOGLE_CREDENTIALS = {
    "access_token": GOOGLE_ACCESS_TOKEN,
    "refresh_token": GOOGLE_REFRESH_TOKEN,
    "client_id": GOOGLE_CLIENT_ID,
    "client_secret": GOOGLE_CLIENT_SECRET,
}

# ── TELEGRAM ─────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = _env_str("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = _env_str("TELEGRAM_CHAT_ID", "")
TELEGRAM_ENABLED   = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
