import imaplib
import email
import re
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# =========================
# CONFIG
# =========================

SENDER_FILTER = "ticketmaster.com"

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


def get_latest_ticketmaster_code(address, password):
    """
    Find the most recent Ticketmaster email that CONTAINS a code.
    """
    try:
        print(f"🔐 Logging into {address}")

        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(address, password)
        mail.select("inbox")

        status, messages = mail.search(None, f'(FROM "{SENDER_FILTER}")')
        email_ids = messages[0].split()

        print(f"📨 {address} → {len(email_ids)} Ticketmaster emails found")

        if not email_ids:
            return None, None

        # Look through last 10 emails for a code
        for email_id in reversed(email_ids[-10:]):
            _, data = mail.fetch(email_id, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])

            # Parse timestamp
            date_tuple = email.utils.parsedate_tz(msg["Date"])
            timestamp = datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))

            # Get email body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors="ignore")
            else:
                body = msg.get_payload(decode=True).decode(errors="ignore")

            # Extract code
            code = extract_code(body)

            if code:
                print(f"✅ Code found for {address}: {code}")
                return code, timestamp

        print(f"⚠️ No code found in recent emails for {address}")
        return None, None

    except Exception as e:
        print(f"❌ Error with {address}: {e}")
        return None, None


# =========================
# ROUTES
# =========================

@app.get("/")
def dashboard(request: Request):
    inbox_data = []

    for inbox in INBOXES:
        email_address = inbox["email"]
        password = inbox["password"]

        print(f"\n🔎 Checking inbox: {email_address}")

        code, timestamp = get_latest_ticketmaster_code(email_address, password)

        inbox_data.append({
            "email": email_address,
            "code": code if code else "------",
            "timestamp": timestamp.strftime("%Y-%m-%d %I:%M:%S %p") if timestamp else "—",
            "raw_time": timestamp  # used for sorting
        })

    # ✅ Sort newest first
    inbox_data.sort(
        key=lambda x: x["raw_time"] if x["raw_time"] else datetime.min,
        reverse=True
    )

    # Remove raw_time before sending to template
    for row in inbox_data:
        row.pop("raw_time")

    print("\n📊 Final sorted inbox data:")
    for row in inbox_data:
        print(row)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "emails": inbox_data
        }
    )
