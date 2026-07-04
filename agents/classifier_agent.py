"""
Classifier Agent — uses Groq to classify email intent and propose actions.
"""
import json
import re
import requests
from typing import Optional, List

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

CLASSIFY_PROMPT = """You are an AI email assistant. Analyze the email and return a JSON object.

Return ONLY a valid JSON object with NO extra text, NO markdown, NO code fences.

The JSON must have exactly these fields:
- intents: array of strings from [meeting_request, task_assignment, follow_up, invoice, other]
- summary: 2-3 sentence plain text summary
- urgency: one of high, medium, low
- sender_name: name extracted from the From field
- proposed_actions: array of action objects

Each action object has:
- type: one of create_calendar_event, create_task, create_reminder, log_invoice, send_reply, no_action
- label: short description like "Schedule meeting with Rahul"
- data: object with fields relevant to the type

For create_calendar_event: data has title (string), proposed_time (ISO string or null), duration_minutes (number), attendees (array of emails), agenda (string)
For create_task: data has task_name (string), due_date (YYYY-MM-DD or null), assigned_by (string)
For create_reminder: data has title (string), remind_at (ISO string or natural language string)
For log_invoice: data has vendor (string), amount (number or null), due_date (YYYY-MM-DD or null)
For send_reply: data has draft (full reply body string), subject (string)

Always include a send_reply action. Be specific with names, dates, amounts from the email."""


class ClassifierAgent:
    def __init__(self, api_key: str, model: str = "llama3-70b-8192"):
        self.api_key = api_key
        self.model = model

    def classify(self, email: dict, your_name: str, free_slots: Optional[List[dict]] = None) -> dict:
        slots_text = ""
        if free_slots:
            slots_text = "\n\nYour available time slots:\n" + "\n".join(
                f"- {s['start']} to {s['end']}" for s in free_slots[:3]
            )

        prompt = f"""Analyze this email:

From: {email.get('from', '')}
Subject: {email.get('subject', '')}
Date: {email.get('date', '')}
Body:
{email.get('body', email.get('snippet', ''))[:2000]}

Recipient name: {your_name}
{slots_text}

Classify and propose actions. Return ONLY valid JSON."""

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": CLASSIFY_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 1500,
        }

        r = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        if r.status_code != 200:
            print(f"\n  [GROQ ERROR {r.status_code}]: {r.text[:500]}")
        r.raise_for_status()
        raw = r.json()["choices"][0]["message"]["content"].strip()
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {
                "intents": ["other"],
                "summary": email.get("snippet", "Could not parse email."),
                "urgency": "low",
                "sender_name": email.get("from", ""),
                "proposed_actions": [{
                    "type": "send_reply",
                    "label": "Send acknowledgment",
                    "data": {
                        "draft": f"Hi,\n\nThank you for your email. I'll get back to you shortly.\n\nBest,\n{your_name}",
                        "subject": f"Re: {email.get('subject', '')}",
                    }
                }]
            }

    def resolve_datetime(self, natural_time: str, timezone: str) -> Optional[str]:
        if not natural_time:
            return None
        import datetime
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        prompt = f"""Current time: {now} ({timezone})
Convert to ISO 8601 datetime: "{natural_time}"
Reply with ONLY the ISO string like 2024-03-15T14:00:00, nothing else."""
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 50,
        }
        try:
            r = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=15)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            return None
