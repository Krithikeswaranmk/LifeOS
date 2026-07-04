"""
Gmail Agent — reads emails, finds threads, sends replies.
"""
import base64
import email as email_lib
from datetime import datetime, timedelta

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


class GmailAgent:
    def __init__(self, credentials: dict):
        creds = Credentials(
            token=credentials.get("access_token"),
            refresh_token=credentials.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=credentials.get("client_id"),
            client_secret=credentials.get("client_secret"),
            scopes=[
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.send",
            ],
        )
        self.service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    def get_recent_emails(self, max_results: int = 30, days_back: int = 7) -> list[dict]:
        after_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y/%m/%d")
        query = f"after:{after_date} -category:promotions -category:social"
        results = self.service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
        messages = []
        for msg_ref in results.get("messages", []):
            try:
                msg = self.service.users().messages().get(
                    userId="me", id=msg_ref["id"], format="full"
                ).execute()
                messages.append(self._parse_message(msg))
            except Exception:
                continue
        return messages

    def get_new_emails_since(self, since_id: str | None, days_back: int = 1) -> list[dict]:
        """Poll for new emails. Returns emails newer than since_id."""
        after_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y/%m/%d")
        query = f"after:{after_date} -category:promotions -category:social"
        results = self.service.users().messages().list(userId="me", q=query, maxResults=50).execute()
        messages = []
        found_since = since_id is None
        for msg_ref in results.get("messages", []):
            if msg_ref["id"] == since_id:
                break
            try:
                msg = self.service.users().messages().get(userId="me", id=msg_ref["id"], format="full").execute()
                messages.append(self._parse_message(msg))
            except Exception:
                continue
        return messages

    def get_email_body(self, message_id: str) -> str:
        try:
            msg = self.service.users().messages().get(userId="me", id=message_id, format="full").execute()
            return self._extract_body(msg.get("payload", {}))
        except Exception:
            return ""

    def send_reply(self, thread_id: str, to: str, subject: str, body: str, your_email: str) -> bool:
        try:
            message_text = f"To: {to}\nSubject: {subject}\nContent-Type: text/plain; charset=utf-8\n\n{body}"
            raw = base64.urlsafe_b64encode(message_text.encode("utf-8")).decode("utf-8")
            self.service.users().messages().send(
                userId="me",
                body={"raw": raw, "threadId": thread_id}
            ).execute()
            return True
        except Exception as e:
            print(f"Send error: {e}")
            return False

    def _parse_message(self, msg: dict) -> dict:
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        body = self._extract_body(msg.get("payload", {}))
        return {
            "id": msg.get("id", ""),
            "thread_id": msg.get("threadId", ""),
            "subject": headers.get("Subject", "(no subject)"),
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "date": headers.get("Date", ""),
            "snippet": msg.get("snippet", ""),
            "body": body[:3000],
        }

    def _extract_body(self, payload: dict) -> str:
        body = payload.get("body", {})
        data = body.get("data", "")
        if data:
            try:
                return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
            except Exception:
                pass
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    try:
                        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
                    except Exception:
                        pass
            if part.get("parts"):
                result = self._extract_body(part)
                if result:
                    return result
        return ""
