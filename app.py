from datetime import datetime, timedelta
import imaplib
import email
import re
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# =========================
# CONFIG
# =========================

SENDER_FILTER = "ticketmaster.com"
CODE_TTL_SECONDS = 300  # codes expire after 5 minutes

INBOXES = [
    {"email": "iobbikevin1@gmail.com", "password": "amkomcuinutmzzrn"},
    {"email": "keviniobbi10@gmail.com", "password": "pmcsigfxeiwwmewf"},
    {"email": "jjjamesgerald@gmail.com", "password": "jsypgkjjgffoyzlm"},
    {"email": "wavesatmalibu@gmail.com", "password": "bevjbldnckltywko"},
    {"email": "iobk8854@gmail.com", "password": "qcuvykmyuhqaygoq"},
    {"email": "kiobbi15@gmail.com", "password": "jmqsvgwlfvkpymre"},
]

# =========================
# HELPERS
# =========================

def extract_code(text):
    """Find 6-digit code in email body"""
    match = re.search(r"\b\d{6}\b", text)
    return match.group(0) if match else None


def is_code_fresh(timestamp):
    """Check if code is still valid (TTL)"""
    if not timestamp:
        return False
    return datetime.now() - timestamp < timedelta(seconds=CODE_TTL_SECONDS)


def get_latest_ticketmaster_code(address, password):
    """Fetch latest Ticketmaster code"""
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(address, password)
        mail.select("inbox")

        status, messages = mail.search(None, f'(FROM "{SENDER_FILTER}")')
        email_ids = messages[0].split()

        if not email_ids:
            return None, None

        for email_id in reversed(email_ids[-10:]):
            _, data = mail.fetch(email_id, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])

            date_tuple = email.utils.parsedate_tz(msg["Date"])
            timestamp = datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors="ignore")
            else:
                body = msg.get_payload(decode=True).decode(errors="ignore")

            code = extract_code(body)

            if code:
                return code, timestamp

        return None, None

    except Exception as e:
        print(f"Error with {address}: {e}")
        return None, None


# =========================
# DASHBOARD ROUTE
# =========================

@app.get("/")
def dashboard(request: Request):
    inbox_data = []

    for inbox in INBOXES:
        email_address = inbox["email"]
        password = inbox["password"]

        code, timestamp = get_latest_ticketmaster_code(email_address, password)

        inbox_data.append({
            "email": email_address,
            "code": code if code else "------",
            "timestamp": timestamp.strftime("%Y-%m-%d %I:%M:%S %p") if timestamp else "—",
            "raw_time": timestamp
        })

    inbox_data.sort(
        key=lambda x: x["raw_time"] if x["raw_time"] else datetime.min,
        reverse=True
    )

    for row in inbox_data:
        row.pop("raw_time")

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "emails": inbox_data}
    )


# =========================
# API: ALL INBOXES (for auto-refresh)
# =========================

@app.get("/api/inboxes")
def api_inboxes():
    inbox_data = []

    for inbox in INBOXES:
        email_address = inbox["email"]
        password = inbox["password"]

        code, timestamp = get_latest_ticketmaster_code(email_address, password)

        inbox_data.append({
            "email": email_address,
            "code": code if code else "------",
            "timestamp": timestamp.strftime("%Y-%m-%d %I:%M:%S %p") if timestamp else "—",
            "raw_time": timestamp
        })

    inbox_data.sort(
        key=lambda x: x["raw_time"] if x["raw_time"] else datetime.min,
        reverse=True
    )

    for row in inbox_data:
        row.pop("raw_time")

    return JSONResponse(content=inbox_data)


# =========================
# API: LATEST VALID CODE
# =========================

@app.get("/latest-code")
def latest_code():
    latest_entry = None

    for inbox in INBOXES:
        email_address = inbox["email"]
        password = inbox["password"]

        code, timestamp = get_latest_ticketmaster_code(email_address, password)

        if not code or not timestamp:
            continue

        if not is_code_fresh(timestamp):
            continue

        if latest_entry is None or timestamp > latest_entry["raw_time"]:
            latest_entry = {
                "email": email_address,
                "code": code,
                "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "raw_time": timestamp
            }

    if latest_entry:
        latest_entry.pop("raw_time")
        return latest_entry

    return {"message": "No valid codes found"}
