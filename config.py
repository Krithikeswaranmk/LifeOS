"""
Central config — loads everything from .env
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-70b-8192")

# Google
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_ACCESS_TOKEN = os.getenv("GOOGLE_ACCESS_TOKEN", "")
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN", "")
TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")

# Notion
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_BRIEFING_PARENT_PAGE_ID = os.getenv("NOTION_BRIEFING_PARENT_PAGE_ID", "")
NOTION_TASKS_DATABASE_ID = os.getenv("NOTION_TASKS_DATABASE_ID", "")
NOTION_FINANCE_DATABASE_ID = os.getenv("NOTION_FINANCE_DATABASE_ID", "")
NOTION_MEETINGS_PARENT_PAGE_ID = os.getenv("NOTION_MEETINGS_PARENT_PAGE_ID", "")

# Email
YOUR_EMAIL = os.getenv("YOUR_EMAIL", "")
YOUR_NAME = os.getenv("YOUR_NAME", "there")
EMAIL_POLL_INTERVAL = int(os.getenv("EMAIL_POLL_INTERVAL", "30"))
WATCHED_DOMAINS = [d.strip() for d in os.getenv("WATCHED_DOMAINS", "").split(",") if d.strip()]
WATCHED_ADDRESSES = [a.strip() for a in os.getenv("WATCHED_ADDRESSES", "").split(",") if a.strip()]
TRIGGER_KEYWORDS = [k.strip().lower() for k in os.getenv("TRIGGER_KEYWORDS", "invoice,meeting,schedule,deadline").split(",") if k.strip()]

# App
PORT = int(os.getenv("PORT", "8000"))
CITY = os.getenv("CITY", "Chennai")
TEMP_UNIT = os.getenv("TEMP_UNIT", "celsius")
EMAIL_HISTORY_DAYS = int(os.getenv("EMAIL_HISTORY_DAYS", "7"))
SECRET_KEY = os.getenv("SECRET_KEY", "changeme")

GOOGLE_CREDENTIALS = {
    "access_token": GOOGLE_ACCESS_TOKEN,
    "refresh_token": GOOGLE_REFRESH_TOKEN,
    "client_id": GOOGLE_CLIENT_ID,
    "client_secret": GOOGLE_CLIENT_SECRET,
}

# ── TELEGRAM ─────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_ENABLED   = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
