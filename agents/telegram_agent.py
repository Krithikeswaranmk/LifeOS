"""
Telegram Agent — sends notifications and handles interactive responses.
Uses long-polling to receive button callbacks from user's phone.
"""
import requests
import time
import json
from typing import Optional, Callable

TELEGRAM_API = "https://api.telegram.org/bot{token}"

class TelegramAgent:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = str(chat_id)
        self.base = f"https://api.telegram.org/bot{token}"
        self._offset = None

    def _post(self, method: str, data: dict) -> dict:
        # debug: log outgoing payload (especially text) to aid troubleshooting
        try:
            txt = data.get("text")
            if txt is not None and len(txt) > 0:
                # printing only first part of repr to avoid flooding
                print(f"[TG_DEBUG] {method} payload text len={len(txt)} repr={repr(txt)[:200]}")
        except Exception:
            pass
        r = requests.post(f"{self.base}/{method}", json=data, timeout=15)
        r.raise_for_status()
        return r.json()

    def _get(self, method: str, params: dict = {}) -> dict:
        r = requests.get(f"{self.base}/{method}", params=params, timeout=20)
        r.raise_for_status()
        return r.json()

    def send(self, text: str, parse_mode: str = "HTML") -> int:
        """Send plain message. Returns message_id.

        Telegram messages have a 4096‑character limit. Truncate long text
        to avoid hitting a Bad Request error ("message is too long")."""
        # enforce length limit so callers don't need to worry
        if len(text) > 4000:
            # preserve some room for ellipsis
            text = text[:3997] + "..."
        try:
            resp = self._post("sendMessage", {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            })
            return resp.get("result", {}).get("message_id", 0)
        except requests.exceptions.HTTPError as e:
            # include response text for debugging
            r = e.response
            try:
                body = r.text
            except Exception:
                body = "<unreadable>"
            raise RuntimeError(f"Telegram send failed: {e} - body: {body}")

    def send_buttons(self, text: str, buttons: list[list[dict]], parse_mode: str = "HTML") -> int:
        """Send message with inline keyboard buttons. Returns message_id."""
        resp = self._post("sendMessage", {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
            "reply_markup": {"inline_keyboard": buttons},
        })
        return resp.get("result", {}).get("message_id", 0)

    def edit_message(self, message_id: int, text: str, parse_mode: str = "HTML"):
        """Edit an existing message (e.g. to show result after button press)."""
        try:
            self._post("editMessageText", {
                "chat_id": self.chat_id,
                "message_id": message_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            })
        except Exception:
            pass

    def answer_callback(self, callback_query_id: str, text: str = ""):
        """Acknowledge a button press (removes loading spinner)."""
        try:
            self._post("answerCallbackQuery", {
                "callback_query_id": callback_query_id,
                "text": text,
            })
        except Exception:
            pass

    def wait_for_callback(self, valid_data: list[str], timeout: int = 300) -> Optional[dict]:
        """
        Block until user presses one of the expected buttons OR timeout.
        Returns {"data": "...", "callback_query_id": "..."} or None on timeout.
        """
        deadline = time.time() + timeout
        params = {"timeout": 20, "allowed_updates": ["callback_query"]}
        if self._offset is not None:
            params["offset"] = self._offset

        while time.time() < deadline:
            remaining = deadline - time.time()
            params["timeout"] = min(20, max(1, int(remaining)))
            try:
                resp = self._get("getUpdates", params)
                updates = resp.get("result", [])
                for update in updates:
                    self._offset = update["update_id"] + 1
                    params["offset"] = self._offset
                    cq = update.get("callback_query")
                    if cq and cq.get("data") in valid_data:
                        return {
                            "data": cq["data"],
                            "callback_query_id": cq["id"],
                            "message_id": cq.get("message", {}).get("message_id"),
                        }
            except Exception:
                time.sleep(2)
        return None

    def ask_yes_no(self, question: str, yes_label: str = "✅ Yes", no_label: str = "❌ No", timeout: int = 300) -> Optional[bool]:
        """Send a yes/no question and wait for response. Returns True/False/None."""
        msg_id = self.send_buttons(question, [[
            {"text": yes_label, "callback_data": "yn_yes"},
            {"text": no_label,  "callback_data": "yn_no"},
        ]])
        result = self.wait_for_callback(["yn_yes", "yn_no"], timeout=timeout)
        if result:
            self.answer_callback(result["callback_query_id"])
            chose = result["data"] == "yn_yes"
            self.edit_message(msg_id, question + f"\n\n{'✅ <b>Yes</b>' if chose else '❌ <b>No</b>'}")
            return chose
        self.edit_message(msg_id, question + "\n\n⏰ <i>Timed out — no response</i>")
        return None

    def ask_slots(self, intro: str, slots: list[dict], timeout: int = 300) -> Optional[int]:
        """
        Show up to 5 time slots as buttons + 'More slots' option.
        Returns chosen slot index or -1 for 'more', None for timeout.
        """
        buttons = []
        for i, s in enumerate(slots):
            buttons.append([{"text": f"🕐 {s['start']}", "callback_data": f"slot_{i}"}])
        buttons.append([{"text": "➡️ Show more slots", "callback_data": "slot_more"}])

        msg_id = self.send_buttons(intro, buttons)
        valid = [f"slot_{i}" for i in range(len(slots))] + ["slot_more"]
        result = self.wait_for_callback(valid, timeout=timeout)

        if result:
            self.answer_callback(result["callback_query_id"])
            if result["data"] == "slot_more":
                self.edit_message(msg_id, intro + "\n\n➡️ <i>Showing more slots...</i>")
                return -1
            idx = int(result["data"].split("_")[1])
            chosen = slots[idx]
            self.edit_message(msg_id, intro + f"\n\n✅ <b>Confirmed:</b> {chosen['start']}")
            return idx
        self.edit_message(msg_id, intro + "\n\n⏰ <i>Timed out — no response</i>")
        return None

    def test_connection(self) -> bool:
        try:
            resp = self._get("getMe")
            name = resp.get("result", {}).get("first_name", "Bot")
            self.send(f"🤖 <b>LifeOS connected!</b>\nBot: {name}\nReady to receive email alerts.")
            return True
        except Exception as e:
            print(f"Telegram connection failed: {e}")
            return False
