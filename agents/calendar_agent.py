from typing import Optional, List
"""
Calendar Agent — reads events, checks conflicts, creates events.
"""
from datetime import datetime, timedelta
import pytz
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dateutil import parser as dateparser


class CalendarAgent:
    def __init__(self, credentials: dict, timezone: str = "Asia/Kolkata"):
        self.tz = timezone
        creds = Credentials(
            token=credentials.get("access_token"),
            refresh_token=credentials.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=credentials.get("client_id"),
            client_secret=credentials.get("client_secret"),
            scopes=["https://www.googleapis.com/auth/calendar"],
        )
        self.service = build("calendar", "v3", credentials=creds, cache_discovery=False)

    def get_today_events(self) -> List[dict]:
        tz = pytz.timezone(self.tz)
        now = datetime.now(tz)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59, microsecond=0)
        return self._fetch_events(start, end)

    def get_upcoming_events(self, days: int = 7) -> List[dict]:
        tz = pytz.timezone(self.tz)
        now = datetime.now(tz)
        future = now + timedelta(days=days)
        return self._fetch_events(now, future)

    def get_free_slots(self, duration_minutes: int = 60, days_ahead: int = 7) -> List[dict]:
        """Find free time slots in the next N days."""
        tz = pytz.timezone(self.tz)
        now = datetime.now(tz)
        events = self.get_upcoming_events(days=days_ahead)
        busy = [(e["start_dt"], e["end_dt"]) for e in events if e.get("start_dt") and e.get("end_dt")]
        busy.sort(key=lambda x: x[0])

        slots = []
        # Start from now rounded up to next 30-min boundary, minimum 9am today
        import math
        rounded_minute = math.ceil(now.minute / 30) * 30
        if rounded_minute == 60:
            check = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        else:
            check = now.replace(minute=rounded_minute, second=0, microsecond=0)
        # Don't go before 9am
        today_9am = now.replace(hour=9, minute=0, second=0, microsecond=0)
        if check < today_9am:
            check = today_9am
        end_search = now + timedelta(days=days_ahead)

        while check < end_search and len(slots) < 50:
            if check.hour >= 18:
                check = (check + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
                continue
            slot_end = check + timedelta(minutes=duration_minutes)
            conflict = any(b[0] < slot_end and b[1] > check for b in busy)
            if not conflict:
                slots.append({
                    "start": check.strftime("%A, %b %d at %I:%M %p"),
                    "end": slot_end.strftime("%I:%M %p"),
                    "start_iso": check.isoformat(),
                    "end_iso": slot_end.isoformat(),
                })
                check = slot_end
            else:
                check += timedelta(minutes=30)
        return slots

    def check_conflict(self, start_iso: str, end_iso: str) -> List[dict]:
        """Check if a time slot conflicts with existing events."""
        try:
            start_dt = dateparser.parse(start_iso)
            end_dt = dateparser.parse(end_iso)
        except Exception:
            return []
        events = self.get_upcoming_events(days=14)
        conflicts = []
        for e in events:
            if e.get("start_dt") and e.get("end_dt"):
                if e["start_dt"] < end_dt and e["end_dt"] > start_dt:
                    conflicts.append({"title": e["title"], "time": e["start_time"]})
        return conflicts

    def create_event(self, title: str, start_iso: str, end_iso: str,
                     attendees: List[str], description: str = "", location: str = "") -> dict:
        """Create a Google Calendar event."""
        event = {
            "summary": title,
            "description": description,
            "location": location,
            "start": {"dateTime": start_iso, "timeZone": self.tz},
            "end": {"dateTime": end_iso, "timeZone": self.tz},
            "attendees": [{"email": a} for a in attendees if "@" in a],
            "reminders": {"useDefault": True},
        }
        result = self.service.events().insert(calendarId="primary", body=event, sendUpdates="all").execute()
        return {
            "id": result.get("id"),
            "link": result.get("htmlLink", ""),
            "title": title,
            "start": start_iso,
        }

    def create_reminder(self, title: str, remind_at_iso: str, description: str = "") -> dict:
        """Create a reminder as a 15-minute calendar event."""
        from dateutil.parser import parse as dp
        start = dp(remind_at_iso)
        end = start + timedelta(minutes=15)
        return self.create_event(
            title=f"⏰ Reminder: {title}",
            start_iso=start.isoformat(),
            end_iso=end.isoformat(),
            attendees=[],
            description=description,
        )

    def _fetch_events(self, start: datetime, end: datetime) -> List[dict]:
        results = self.service.events().list(
            calendarId="primary",
            timeMin=start.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            maxResults=50,
        ).execute()
        return [self._parse_event(e) for e in results.get("items", [])]

    def _parse_event(self, item: dict) -> dict:
        start = item.get("start", {})
        end = item.get("end", {})
        start_str = start.get("dateTime") or start.get("date", "")
        end_str = end.get("dateTime") or end.get("date", "")
        try:
            start_dt = dateparser.parse(start_str) if start_str else None
            end_dt = dateparser.parse(end_str) if end_str else None
        except Exception:
            start_dt = end_dt = None
        return {
            "id": item.get("id", ""),
            "title": item.get("summary", "No title"),
            "start_str": start_str,
            "end_str": end_str,
            "start_dt": start_dt,
            "end_dt": end_dt,
            "start_time": start_dt.strftime("%I:%M %p") if start_dt else start_str,
            "description": item.get("description", ""),
            "attendees": [a.get("email", "") for a in item.get("attendees", []) if not a.get("self")],
            "location": item.get("location", ""),
            "meet_link": item.get("hangoutLink", ""),
        }
