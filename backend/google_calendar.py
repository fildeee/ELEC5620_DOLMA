from __future__ import annotations
import os
from typing import Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

from zoneinfo import ZoneInfo

DEFAULT_TZ = os.getenv("USER_TIMEZONE", "UTC")

SCOPES = ["https://www.googleapis.com/auth/calendar"]

TOKEN_PATH = "token.json"

def load_creds() -> Optional[Credentials]:
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        return creds
    return None

def save_creds(creds: Credentials) -> None:
    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())


# Returns calendar service object that lets you interact with Google Calendar API
def get_calendar_service():
    creds = load_creds()
    if not creds:
        raise RuntimeError("Not connected to Google yet because no token.json file found.")

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            save_creds(creds)
        else:
            raise RuntimeError("Stored credentials are invalid; please reconnect Google.")

    return build("calendar", "v3", credentials=creds)

# function to check if app is connected to Google Calendar
def is_connected() -> bool:
    creds = load_creds()
    if not creds:
        return False
    if creds.valid:
        return True
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            save_creds(creds)
            return True
        except Exception:
            return False
    return False

# function to create event for Google Calendar
def create_calendar_event(summary, description, start_time, end_time):
    service = get_calendar_service()

    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=ZoneInfo(DEFAULT_TZ))
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=ZoneInfo(DEFAULT_TZ))
    
    event = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': start_time.isoformat(),
        },
        'end': {
            'dateTime': end_time.isoformat(),
        },
    }
    
    # inserts new event into primary calendar
    created_event = service.events().insert(calendarId='primary', body=event).execute()
    print("✅ Created event:", created_event.get("htmlLink"))  # <--- add this
    return created_event