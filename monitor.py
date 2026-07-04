#!/usr/bin/env python3
"""
LifeOS v2 — AI Mail Monitor
Mobile-first: all interactions via Telegram on your phone.
Terminal shows live logs. Phone handles yes/no/slot selection.
"""
import sys, time, textwrap, requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv
from html import escape as _escape

load_dotenv()

import config
from agents.gmail_agent      import GmailAgent
from agents.calendar_agent   import CalendarAgent
from agents.notion_agent     import NotionAgent
from agents.classifier_agent import ClassifierAgent
from agents.telegram_agent   import TelegramAgent
from data.store import add_to_history, increment_stat

# ── COLORS ────────────────────────────────────────────────────────────────
R="\033[0m"; B="\033[1m"; DIM="\033[2m"
CYAN="\033[96m"; GREEN="\033[92m"; YELLOW="\033[93m"
RED="\033[91m"; MAGENTA="\033[95m"; WHITE="\033[97m"

SEEN_FILE = Path(__file__).parent / "data" / "seen_ids.txt"
tg: Optional[TelegramAgent] = None


def should_process_email(email: dict) -> bool:
    sender = (email.get("from", "") or "").lower()
    subject = (email.get("subject", "") or "").lower()
    snippet = (email.get("snippet", "") or "").lower()
    haystack = f"{subject} {snippet}"

    # If no watch filters are configured, process all incoming messages.
    if not config.WATCHED_ADDRESSES and not config.WATCHED_DOMAINS:
        return True

    for address in config.WATCHED_ADDRESSES:
        if address.lower() in sender:
            return True

    for domain in config.WATCHED_DOMAINS:
        domain_l = domain.lower().lstrip("@")
        if f"@{domain_l}" in sender:
            return True

    for keyword in config.TRIGGER_KEYWORDS:
        if keyword and keyword in haystack:
            return True

    return False

def load_seen():
    SEEN_FILE.parent.mkdir(exist_ok=True)
    return set(SEEN_FILE.read_text().splitlines()) if SEEN_FILE.exists() else set()

def save_seen(seen):
    SEEN_FILE.write_text("\n".join(seen))

def hr(c="─",w=62,col=DIM): print(f"{col}{c*w}{R}")
def section(t,e=""): print(); print(f"{CYAN}{B}{'━'*62}{R}"); print(f"{CYAN}{B}  {e}  {t}{R}"); print(f"{CYAN}{B}{'━'*62}{R}")
def info(m):    print(f"  {CYAN}i{R}  {m}")
def success(m): print(f"  {GREEN}OK{R} {m}")
def warn(m):    print(f"  {YELLOW}!{R}  {m}")
def error(m):   print(f"  {RED}X{R}  {m}")
def label(k,v): print(f"  {DIM}{k:<20}{R}{v}")
def wrap(t,i=4,w=72): pad=" "*i; return textwrap.fill(t,width=w,initial_indent=pad,subsequent_indent=pad)

def notify(text):
    # escape text before printing/sending
    esc_text = _escape(text)
    print(f"  {MAGENTA}[TG]{R} {esc_text}")
    if tg:
        try: tg.send(esc_text)
        except Exception as e: print(f"  {YELLOW}!{R}  Telegram: {e}")

def groq(prompt, max_tokens=300):
    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": config.GROQ_MODEL, "messages": [{"role":"user","content":prompt}],
               "temperature": 0.35, "max_tokens": max_tokens}
    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                      headers=headers, json=payload, timeout=20)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

def print_banner():
    watched = ", ".join(config.WATCHED_ADDRESSES) if config.WATCHED_ADDRESSES else "(all senders)"
    domains = ", ".join(config.WATCHED_DOMAINS) if config.WATCHED_DOMAINS else "(none)"
    print()
    print(f"{CYAN}{B}{'='*64}{R}")
    print(f"{CYAN}{B}   LifeOS v2  --  Intelligent Mail Monitor{R}")
    print(f"{CYAN}{B}{'='*64}{R}")
    print()
    print(f"  {DIM}Watch list:{R}  {WHITE}{watched}{R}")
    print(f"  {DIM}Domains   :{R}  {WHITE}{domains}{R}")
    print(f"  {DIM}Interval :{R}  {WHITE}every {config.EMAIL_POLL_INTERVAL}s{R}")
    print(f"  {DIM}AI Model :{R}  {WHITE}{config.GROQ_MODEL}{R}")
    print(f"  {DIM}Dashboard:{R}  {WHITE}http://localhost:8000{R}")
    tg_status = f"{GREEN}Mobile notifications ON{R}" if config.TELEGRAM_ENABLED else f"{YELLOW}Telegram not configured{R}"
    print(f"  {DIM}Telegram :{R}  {tg_status}")
    print()
    print(f"  {GREEN}{B}Mail monitoring has started{R}")
    print()
    hr()

def print_notification(email, cls):
    # temporarily disable console notification to avoid encoding errors during testing
    return

def generate_meeting_notes(title, agenda, sender, email_body):
    prompt = f"""Prepare meeting prep notes for the following meeting.

Meeting: {title}
Requested by: {sender}
Email context: {email_body[:1200]}

Write structured notes with these sections:
CONTEXT
(2-3 sentences)

KEY TOPICS TO COVER
- topic 1
- topic 2
- topic 3

QUESTIONS TO ASK
- question 1
- question 2

PREPARE BEFOREHAND
- item 1
- item 2

Keep each point concise and actionable."""
    try:
        return groq(prompt, 600)
    except Exception:
        return f"Meeting: {title}\nRequested by: {sender}\nAgenda: {agenda or 'As per email.'}"

def generate_reply(email, completed_actions):
    sender_name = email.get("from","").split("<")[0].strip().split()[0] or "there"
    subject = email.get("subject","")
    scheduled_time = next((a["time"] for a in completed_actions
                           if a.get("type")=="meeting_scheduled" and a.get("time")), None)
    task_name = next((a["name"] for a in completed_actions
                      if a.get("type")=="task_created"), None)
    if scheduled_time:
        prompt = f"""Write a professional email reply confirming a meeting was scheduled and asking if the time works.
To: {sender_name} | From: {config.YOUR_NAME}
Meeting scheduled for: {scheduled_time}
Subject: {subject}
1. Warmly acknowledge their request
2. Confirm the meeting is set for {scheduled_time}
3. Ask if that time works or if they need to adjust
Write ONLY the email body. No subject. 4-5 sentences."""
    elif task_name:
        prompt = f"""Write a brief professional email acknowledging a task was noted.
To: {sender_name} | From: {config.YOUR_NAME} | Task: {task_name}
3 sentences max. ONLY the body."""
    else:
        prompt = f"""Write a professional email acknowledging receipt and saying you will follow up.
To: {sender_name} | From: {config.YOUR_NAME} | Subject: {subject}
Email: {email.get("snippet","")[:300]}
Warm, professional. 3-4 sentences. ONLY the body."""
    try:
        return groq(prompt, 200)
    except Exception:
        if scheduled_time:
            return f"Hi {sender_name},\n\nThank you for reaching out! I have scheduled our meeting for {scheduled_time}. Does that time work for you, or would you prefer a different slot?\n\nBest regards,\n{config.YOUR_NAME}"
        return f"Hi {sender_name},\n\nThank you for your email. I will get back to you shortly.\n\nBest regards,\n{config.YOUR_NAME}"

def book_and_note(start_iso, title, duration, attendees, agenda, email, calendar, notion, action):
    try:
        from dateutil.parser import parse as dp
        s = dp(start_iso); e = s + timedelta(minutes=duration)
        info("Creating calendar event...")
        ev = calendar.create_event(title, s.isoformat(), e.isoformat(), attendees, agenda)
        time_str = s.strftime("%A, %B %d at %I:%M %p")
        success(f"Meeting scheduled: {title}")
        label("  Time:",     time_str)
        label("  Calendar:", ev.get("link",""))
        info("Generating AI meeting prep notes...")
        notes = generate_meeting_notes(title, agenda, email.get("from",""),
                                        email.get("body", email.get("snippet","")))
        print(); print(f"  {CYAN}{B}Meeting Prep Notes:{R}"); hr(".",62,DIM)
        for line in notes.split("\n"): print(f"    {line}")
        hr(".",62,DIM)
        info("Saving prep notes to Notion...")
        note_url = notion.create_meeting_note(
            title=title, date=s.strftime("%A, %B %d, %Y at %I:%M %p"),
            attendees=attendees, agenda=notes, calendar_link=ev.get("link",""),
        )
        success("Notion prep notes saved!")
        label("  Notion:", note_url)
        if tg:
            tg.send(
                f"<b>Meeting Scheduled!</b>\n\n"
                f"<b>{_escape(title)}</b>\n"
                f"Time: {_escape(time_str)}\n"
                f"<a href='{_escape(note_url)}'>Prep Notes in Notion</a>\n"
                f"<a href='{_escape(ev.get('link',''))}'>Google Calendar</a>"
            )
        add_to_history(email, "create_calendar_event", action["label"], "done", ev.get("link",""), note_url)
        increment_stat("meetings_scheduled")
        return ev.get("link",""), time_str
    except Exception as ex:
        error(f"Failed: {ex}")
        add_to_history(email, "create_calendar_event", action["label"], "failed", "", str(ex))
        return None, None

def handle_calendar(action, email, calendar, notion, classifier):
    data      = action.get("data",{})
    title     = data.get("title", email.get("subject","Meeting"))
    duration  = data.get("duration_minutes", 60)
    attendees = data.get("attendees",[])
    agenda    = data.get("agenda","")
    proposed  = data.get("proposed_time")
    start_iso = None

    if proposed:
        start_iso = proposed if "T" in str(proposed) else classifier.resolve_datetime(proposed, config.TIMEZONE)

    print()
    print(f"  {YELLOW}{B}MEETING REQUESTED{R}")
    hr("-",62,DIM)
    print(f"  Title:  {title}")
    print(f"  From:   {email.get('from','')}")

    proposed_str = ""
    conflict_msg = ""

    if start_iso:
        try:
            from dateutil.parser import parse as dp
            proposed_dt = dp(start_iso)
            proposed_str = proposed_dt.strftime("%A, %B %d at %I:%M %p")
            print(f"  Wants:  {CYAN}{proposed_str}{R}")
            s = dp(start_iso); e = s + timedelta(minutes=duration)
            conflicts = calendar.check_conflict(s.isoformat(), e.isoformat())
            if conflicts:
                conflict_msg = f"\n\nConflict: clashes with '{conflicts[0]['title']}' at {conflicts[0]['time']}"
                warn(f"Conflict with '{conflicts[0]['title']}' at {conflicts[0]['time']}")
        except Exception:
            pass

        question = (
            f"<b>Meeting Request</b>\n\n"
            f"<b>{title}</b>\n"
            f"From: {email.get('from','')}\n"
            f"Proposed: <b>{proposed_str}</b>"
            f"{conflict_msg}\n\n"
            f"Schedule this meeting at {proposed_str}?"
        )
        print()

        if tg:
            info("Waiting for your decision on Telegram...")
            confirmed = tg.ask_yes_no(question, timeout=300)
            if confirmed is None:
                warn("No response in 5 minutes — skipping.")
                add_to_history(email, "create_calendar_event", action["label"], "skipped", "Telegram timeout")
                return None, None
        else:
            print(f"\n  {YELLOW}?{R}  {B}Schedule at {proposed_str}? [y/n]{R}  ", end="")
            confirmed = input().strip().lower() in ("y","yes")

        if confirmed:
            return book_and_note(start_iso, title, duration, attendees, agenda, email, calendar, notion, action)
    else:
        info("No specific time mentioned.")

    return _pick_slot(title, duration, attendees, agenda, email, calendar, notion, action)

def _pick_slot(title, duration, attendees, agenda, email, calendar, notion, action):
    days_ahead = 7
    shown = 0
    while True:
        info(f"Fetching free slots (next {days_ahead} days)...")
        all_slots = calendar.get_free_slots(duration_minutes=duration, days_ahead=days_ahead)
        batch = all_slots[shown:shown+5]
        if not batch:
            days_ahead = min(days_ahead+7, 60)
            if days_ahead > 60:
                warn("No slots found in next 60 days.")
                add_to_history(email, "create_calendar_event", action["label"], "skipped", "No slots")
                return None, None
            shown = 0; continue

        print(f"\n  {B}Available slots:{R}")
        for i, s in enumerate(batch, shown+1):
            print(f"    {CYAN}{i}.{R}  {s['start']} to {s['end']}")

        if tg:
            info("Waiting for slot selection on Telegram...")
            msg_text = (
                f"<b>Pick a slot for:</b>\n<i>{title}</i>\n\n"
                + "\n".join(f"{s['start']}" for s in batch)
            )
            choice = tg.ask_slots(msg_text, batch, timeout=300)
            if choice is None:
                warn("Timed out."); return None, None
            if choice == -1:
                shown += 5; continue
            chosen = all_slots[shown + choice]
        else:
            print(f"    n.  None — show more")
            ch = input(f"\n  ?  Pick slot number or 'n':  ").strip().lower()
            if ch in ("n","none",""):
                shown += 5
                if shown >= len(all_slots): days_ahead += 7; shown = 0
                continue
            if not ch.isdigit() or not (0 < int(ch) <= len(all_slots)):
                warn("Invalid."); continue
            chosen = all_slots[int(ch)-1]

        return book_and_note(chosen["start_iso"], title, duration, attendees, agenda, email, calendar, notion, action)

def handle_task(action, email, notion):
    data = action.get("data",{})
    try:
        url = notion.create_task(
            data.get("task_name", email.get("subject","Task")),
            data.get("due_date"),
            data.get("assigned_by", email.get("from","")),
            email.get("snippet","")
        )
        success("Task added to Notion")
        label("  Task:", data.get("task_name",""))
        if data.get("due_date"): label("  Due:", data["due_date"])
        label("  Notion:", url)
        if tg:
            tg.send(f"<b>Task Created</b>\n\n{_escape(data.get('task_name','New task'))}\n"
                    f"{_escape('Due: '+data['due_date']) if data.get('due_date') else ''}\n"
                    f"<a href='{_escape(url)}'>View in Notion</a>")
        add_to_history(email, "create_task", action["label"], "done", url)
        increment_stat("tasks_created")
    except Exception as ex:
        error(f"Failed: {ex}")
        add_to_history(email, "create_task", action["label"], "failed", "", str(ex))

def handle_reminder(action, email, calendar, classifier):
    data = action.get("data",{})
    remind_at = data.get("remind_at")
    if remind_at and "T" not in str(remind_at):
        remind_at = classifier.resolve_datetime(remind_at, config.TIMEZONE)
    if not remind_at:
        remind_at = (datetime.now()+timedelta(hours=24)).isoformat()
    try:
        ev = calendar.create_reminder(
            data.get("title","Follow up"), remind_at,
            f"Re: {email.get('subject','')}\nFrom: {email.get('from','')}"
        )
        success("Reminder set in Google Calendar")
        label("  Title:", data.get("title",""))
        label("  Link:",  ev.get("link",""))
        if tg:
            tg.send(f"<b>Reminder Set</b>\n\n{_escape(data.get('title','Follow up'))}\n"
                    f"<a href='{_escape(ev.get('link',''))}'>View in Calendar</a>")
        add_to_history(email, "create_reminder", action["label"], "done", ev.get("link",""))
        increment_stat("reminders_set")
    except Exception as ex:
        error(f"Failed: {ex}")
        add_to_history(email, "create_reminder", action["label"], "failed", "", str(ex))

def handle_invoice(action, email, notion):
    data = action.get("data",{})
    try:
        url = notion.log_invoice(
            data.get("vendor", email.get("from","Unknown")),
            data.get("amount"), data.get("due_date"), email.get("snippet","")
        )
        success("Invoice logged in Notion")
        label("  Vendor:", data.get("vendor",""))
        if data.get("amount"): label("  Amount:", str(data["amount"]))
        label("  Notion:", url)
        if tg:
            tg.send(f"<b>Invoice Logged</b>\n\nVendor: {_escape(data.get('vendor','Unknown'))}\n"
                    f"{_escape('Amount: '+str(data['amount'])) if data.get('amount') else ''}\n"
                    f"<a href='{_escape(url)}'>View in Notion</a>")
        add_to_history(email, "log_invoice", action["label"], "done", url)
        increment_stat("invoices_logged")
    except Exception as ex:
        error(f"Failed: {ex}")
        add_to_history(email, "log_invoice", action["label"], "failed", "", str(ex))

def handle_reply(draft, subject, email, gmail, action_label="Send reply"):
    print(); hr("-",62,DIM)
    print(f"  {B}Reply Draft:{R}"); hr("-",62,DIM)
    print(f"  To:      {email.get('from','')}"); print(f"  Subject: {subject}"); print()
    for line in draft.split("\n"): print(f"    {line}")
    print(); hr("-",62,DIM)

    if tg:
        info("Waiting for send/skip on Telegram...")
        tg_msg = (
            f"<b>Reply Draft Ready</b>\n\n"
            f"To: {_escape(email.get('from',''))}\n"
            f"Subject: {_escape(subject)}\n\n"
            f"<i>{_escape(draft[:600])}{'...' if len(draft)>600 else ''}</i>"
        )
        send_it = tg.ask_yes_no(tg_msg, yes_label="Send Reply", no_label="Skip", timeout=300)
    else:
        send_it = input(f"\n  ?  Send this reply? [y/n]  ").strip().lower() in ("y","yes")

    if send_it:
        try:
            ok = gmail.send_reply(email.get("thread_id",""), email.get("from",""),
                                   subject, draft, config.YOUR_EMAIL)
            if ok:
                success("Reply sent!")
                if tg: tg.send(f"Reply sent to {_escape(email.get('from',''))}")
                increment_stat("replies_sent")
                add_to_history(email, "send_reply", action_label, "done", "sent")
            else:
                error("Failed to send.")
                add_to_history(email, "send_reply", action_label, "failed", "", "Send API returned false")
        except Exception as ex:
            error(f"Send error: {ex}")
            add_to_history(email, "send_reply", action_label, "failed", "", str(ex))
    else:
        info("Reply skipped.")
        increment_stat("replies_skipped")
        add_to_history(email, "send_reply", action_label, "skipped", "User skipped")

def process_email(email, gmail, calendar, notion, classifier):
    email["body"] = gmail.get_email_body(email["id"])
    free_slots = []
    try: free_slots = calendar.get_free_slots(60, 7)
    except Exception: pass

    print(f"\n  {DIM}Analyzing with AI...{R}", end="", flush=True)
    cls = classifier.classify(email, config.YOUR_NAME, free_slots)
    print(f"\r  {GREEN}OK{R}  AI analysis complete              ")
    increment_stat("emails_processed")

    print_notification(email, cls)

    # Immediate Telegram alert
    if tg:
        urgency = cls.get("urgency","low")
        u_icon = "HIGH" if urgency=="high" else "MED" if urgency=="medium" else "low"
        intents = ", ".join(cls.get("intents",["other"]))
        msg = (
            f"<b>New Email — {_escape(email.get('subject',''))}</b>\n\n"
            f"From: {_escape(email.get('from',''))}\n"
            f"Type: {_escape(intents)}  |  Priority: {_escape(u_icon)}\n\n"
            f"<i>{_escape(cls.get('summary', email.get('snippet','')))}</i>"
        )
        # debugging output
        print(f"DEBUG [TG MESSAGE]: length={len(msg)} repr={msg!r}")
        tg.send(msg)

    actions = cls.get("proposed_actions",[])
    reply_action = None
    completed_actions = []

    for action in actions:
        atype = action.get("type")
        if atype == "send_reply": reply_action = action; continue
        print(); hr(".",62,DIM)
        print(f"  {MAGENTA}{B}Action:{R} {action.get('label', atype)}")
        if atype == "create_calendar_event":
            link, time_str = handle_calendar(action, email, calendar, notion, classifier)
            if link:
                completed_actions.append({"type":"meeting_scheduled",
                    "title":action.get("data",{}).get("title","Meeting"),
                    "time":time_str or "", "calendar_link":link})
        elif atype == "create_task":
            handle_task(action, email, notion)
            completed_actions.append({"type":"task_created","name":action.get("data",{}).get("task_name","")})
        elif atype == "create_reminder":
            handle_reminder(action, email, calendar, classifier)
            completed_actions.append({"type":"reminder_set"})
        elif atype == "log_invoice":
            handle_invoice(action, email, notion)
            completed_actions.append({"type":"invoice_logged"})

    if reply_action:
        subject = reply_action.get("data",{}).get("subject", f"Re: {email.get('subject','')}")
        draft = generate_reply(email, completed_actions)
        handle_reply(draft, subject, email, gmail, reply_action.get("label", "Send reply"))

    print(); hr("=",62,CYAN)
    print(f"  {DIM}Done.  Dashboard: http://localhost:8000{R}")
    hr("=",62,CYAN); print()

def main():
    global tg
    print_banner()
    connected_mailbox = ""
    try:
        gmail      = GmailAgent(config.GOOGLE_CREDENTIALS)
        connected_mailbox = gmail.get_profile_email()
        calendar   = CalendarAgent(config.GOOGLE_CREDENTIALS, config.TIMEZONE)
        notion     = NotionAgent(config.NOTION_TOKEN, config.NOTION_TASKS_DATABASE_ID,
                                  config.NOTION_FINANCE_DATABASE_ID,
                                  config.NOTION_MEETINGS_PARENT_PAGE_ID,
                                  config.NOTION_BRIEFING_PARENT_PAGE_ID)
        classifier = ClassifierAgent(config.GROQ_API_KEY, config.GROQ_MODEL)
    except Exception as e:
        error(f"Init failed: {e}"); sys.exit(1)

    if config.TELEGRAM_ENABLED:
        tg = TelegramAgent(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)
        if not tg.test_connection():
            warn("Telegram failed — terminal-only mode.")
            tg = None
    else:
        warn("Telegram not configured — running terminal-only.")
        info("See README for 2-minute Telegram setup.")

    if connected_mailbox:
        info(f"Connected Gmail inbox: {connected_mailbox}")
        if config.YOUR_EMAIL and connected_mailbox.lower() != config.YOUR_EMAIL.strip().lower():
            warn(f"YOUR_EMAIL is {config.YOUR_EMAIL}, but OAuth token points to {connected_mailbox}")
        if tg:
            tg.send(
                f"LifeOS connected. Ready to receive email alerts.\n"
                f"Connected inbox: <b>{_escape(connected_mailbox)}</b>"
            )

    seen = load_seen()
    if len(seen) == 0:
        if config.SKIP_EXISTING_ON_BOOT:
            info("First run — marking existing emails as seen...")
            for e in gmail.get_recent_emails(50, config.EMAIL_HISTORY_DAYS):
                seen.add(e["id"])
            save_seen(seen)
            info(f"Marked {len(seen)} existing emails. Only NEW emails will trigger actions.")
        else:
            info("First run with SKIP_EXISTING_ON_BOOT=false — recent unseen emails will be processed.")
    else:
        info(f"Loaded {len(seen)} seen email IDs")

    info("Watching for new mail using configured filters...\n")

    while True:
        try:
            for email in reversed(gmail.get_recent_emails(20, 1)):
                if email["id"] in seen: continue
                seen.add(email["id"]); save_seen(seen)
                increment_stat("emails_received")
                if not should_process_email(email):
                    continue
                process_email(email, gmail, calendar, notion, classifier)
        except KeyboardInterrupt:
            print(); info("Shutting down. Goodbye!"); break
        except Exception as e:
            import traceback
            traceback.print_exc()
            error(f"Poll error: {e!r}")
            if tg:
                try:
                    tg.send(f"LifeOS poll error: {_escape(str(e))}")
                except Exception:
                    pass
        try:
            for r in range(config.EMAIL_POLL_INTERVAL, 0, -1):
                print(f"\r  {DIM}Next check in {r:3d}s  (Ctrl+C to quit){R}", end="", flush=True)
                time.sleep(1)
            print(f"\r  {DIM}Checking for new emails...                {R}", end="", flush=True)
        except KeyboardInterrupt:
            print(); info("Shutting down. Goodbye!"); break

if __name__ == "__main__":
    main()
