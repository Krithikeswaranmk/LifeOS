from typing import Optional, List
"""
Persistent store — TinyDB. Stores action history and stats.
"""
import os
from datetime import datetime
from tinydb import TinyDB, Query
from tinydb.operations import increment

DB_PATH = os.path.join(os.path.dirname(__file__), "lifeos.json")
db = TinyDB(DB_PATH)

history_table = db.table("history")
stats_table   = db.table("stats")


# ── HISTORY ───────────────────────────────────────────────────────────────

def add_to_history(email: dict, action_type: str, action_label: str,
                   status: str, result: str = "", detail: str = ""):
    history_table.insert({
        "email_subject": email.get("subject", ""),
        "email_from":    email.get("from", ""),
        "email_date":    email.get("date", ""),
        "action_type":   action_type,
        "action_label":  action_label,
        "status":        status,   # done / skipped / failed
        "result":        result,   # url or link
        "detail":        detail,   # extra info
        "timestamp":     datetime.now().isoformat(),
    })

def get_history(limit: int = 100) -> list:
    items = history_table.all()
    return sorted(items, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]


# ── STATS ─────────────────────────────────────────────────────────────────

def _ensure_stats():
    if not stats_table.all():
        stats_table.insert({
            "emails_received":   0,
            "emails_processed":  0,
            "meetings_scheduled": 0,
            "tasks_created":     0,
            "invoices_logged":   0,
            "reminders_set":     0,
            "replies_sent":      0,
            "replies_skipped":   0,
        })

def increment_stat(key: str):
    _ensure_stats()
    try:
        row = stats_table.all()[0]
        if key not in row:
            stats_table.update({key: 0}, doc_ids=[row.doc_id])
        stats_table.update(increment(key), doc_ids=[row.doc_id])
    except Exception:
        pass

def get_stats() -> dict:
    _ensure_stats()
    s = dict(stats_table.all()[0])
    history = history_table.all()
    s.setdefault("emails_received", s.get("emails_processed", 0))
    s.setdefault("replies_skipped", 0)
    s.setdefault("replies_sent", 0)
    s["total_actions_done"] = len([h for h in history if h.get("status") == "done"])
    s["total_skipped"]      = len([h for h in history if h.get("status") == "skipped"])
    s["estimated_minutes_saved"] = s["total_actions_done"] * 5
    return s
