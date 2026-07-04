from typing import Optional, List
"""
Notion Agent — creates meeting notes, tasks, finance entries, briefings.
"""
from datetime import datetime
from notion_client import Client


class NotionAgent:
    def __init__(self, token: str, tasks_db_id: str, finance_db_id: str,
                 meetings_parent_id: str, briefing_parent_id: str):
        self.client = Client(auth=token)
        self.tasks_db_id = tasks_db_id
        self.finance_db_id = finance_db_id
        self.meetings_parent_id = meetings_parent_id
        self.briefing_parent_id = briefing_parent_id

    # ── MEETING NOTES ────────────────────────────────────────────────────

    def create_meeting_note(self, title: str, date: str, attendees,
                             agenda: str, calendar_link: str = "", email_thread_link: str = "") -> str:
        """Create a meeting notes page. Returns page URL."""
        # Safely handle attendees — could be list of strings or list of dicts
        if not attendees:
            attendees_text = "TBD"
        else:
            clean = []
            for a in attendees:
                if isinstance(a, dict):
                    clean.append(a.get("email", str(a)))
                else:
                    clean.append(str(a))
            attendees_text = ", ".join(clean) if clean else "TBD"

        blocks = [
            self._heading(2, "📋 Meeting Details"),
            self._paragraph(f"📅 Date: {date}"),
            self._paragraph(f"👥 Attendees: {attendees_text}"),
        ]
        if calendar_link:
            blocks.append(self._paragraph(f"🗓️ Calendar Event: {calendar_link}"))
        if email_thread_link:
            blocks.append(self._paragraph(f"📧 Source Email: {email_thread_link}"))

        blocks += [
            self._divider(),
            self._heading(2, "📌 Meeting Prep Notes"),
        ]

        # Split long agenda/notes into multiple paragraph blocks (Notion has 2000 char limit per block)
        agenda_text = agenda or "To be filled in."
        chunk_size = 1800
        for i in range(0, len(agenda_text), chunk_size):
            blocks.append(self._paragraph(agenda_text[i:i + chunk_size]))

        blocks += [
            self._divider(),
            self._heading(2, "📝 Notes during meeting"),
            self._paragraph(""),
            self._divider(),
            self._heading(2, "✅ Action Items"),
            self._todo(""),
        ]

        page = self.client.pages.create(
            parent={"page_id": self.meetings_parent_id},
            properties={"title": {"title": [{"text": {"content": f"📅 {title} — {date}"}}]}},
            children=blocks,
        )
        return page.get("url", "")

    # ── TASKS ─────────────────────────────────────────────────────────────

    def create_task(self, name: str, due_date: Optional[str], assigned_by: str,
                    source_email_snippet: str = "") -> str:
        """Add a row to the Tasks database. Returns page URL."""
        props = {
            "Name": {"title": [{"text": {"content": name}}]},
            "Assigned By": {"rich_text": [{"text": {"content": assigned_by}}]},
            "Status": {"select": {"name": "To Do"}},
            "Source": {"rich_text": [{"text": {"content": source_email_snippet[:200]}}]},
        }
        if due_date:
            try:
                dt = datetime.strptime(due_date, "%Y-%m-%d")
                props["Due Date"] = {"date": {"start": dt.strftime("%Y-%m-%d")}}
            except Exception:
                pass
        page = self.client.pages.create(
            parent={"database_id": self.tasks_db_id},
            properties=props,
        )
        return page.get("url", "")

    # ── FINANCE TRACKER ───────────────────────────────────────────────────

    def log_invoice(self, vendor: str, amount: Optional[float], due_date: Optional[str],
                    source_snippet: str = "") -> str:
        """Add a row to the Finance Tracker database. Returns page URL."""
        props = {
            "Vendor": {"title": [{"text": {"content": vendor}}]},
            "Status": {"select": {"name": "Unpaid"}},
            "Source": {"rich_text": [{"text": {"content": source_snippet[:200]}}]},
        }
        if amount is not None:
            props["Amount"] = {"number": amount}
        if due_date:
            try:
                dt = datetime.strptime(due_date, "%Y-%m-%d")
                props["Due Date"] = {"date": {"start": dt.strftime("%Y-%m-%d")}}
            except Exception:
                pass
        page = self.client.pages.create(
            parent={"database_id": self.finance_db_id},
            properties=props,
        )
        return page.get("url", "")

    # ── HELPERS ───────────────────────────────────────────────────────────

    def _heading(self, level: int, text: str) -> dict:
        key = f"heading_{level}"
        return {"object": "block", "type": key, key: {"rich_text": [{"text": {"content": text}}]}}

    def _paragraph(self, text: str) -> dict:
        return {"object": "block", "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": text}}]}}

    def _todo(self, text: str) -> dict:
        return {"object": "block", "type": "to_do",
                "to_do": {"rich_text": [{"text": {"content": text}}], "checked": False}}

    def _divider(self) -> dict:
        return {"object": "block", "type": "divider", "divider": {}}
