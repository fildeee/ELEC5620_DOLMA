from __future__ import annotations
import os
from typing import Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

from zoneinfo import ZoneInfo

from typing import List, Dict

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
# function to create event for Google Calendar
def create_calendar_event(
    summary,
    description,
    start_time,
    end_time,
    location=None,
    attendees=None,      # type = list[str] emails
    recurrence=None,     # type = list[str]
    reminders=None,      # type = list[{"method": str, "minutes": int}]
    DEFAULT_TZ="Australia/Sydney",
):
    service = get_calendar_service()

    # ensure timezone on datetimes
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=ZoneInfo(DEFAULT_TZ))
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=ZoneInfo(DEFAULT_TZ))

    event = {
        "summary": summary,
        "description": description or "",
        "start": {
            "dateTime": start_time.isoformat(),
            "timeZone": str(start_time.tzinfo) if start_time.tzinfo else DEFAULT_TZ,
        },
        "end": {
            "dateTime": end_time.isoformat(),
            "timeZone": str(end_time.tzinfo) if end_time.tzinfo else DEFAULT_TZ,
        },
    }

    if location:
        event["location"] = location

    if attendees:
        # converts list[str] -> list[{"email": "..."}]
        event["attendees"] = [{"email": em} for em in attendees if isinstance(em, str) and em.strip()]

    if recurrence:
        event["recurrence"] = [r for r in recurrence if isinstance(r, str) and r.strip()]

    if reminders:
        cleaned = []
        for r in reminders:
            m = (r or {}).get("method")
            mins = (r or {}).get("minutes")
            if isinstance(m, str) and isinstance(mins, int):
                cleaned.append({"method": m, "minutes": mins})
        if cleaned:
            event["reminders"] = {"useDefault": False, "overrides": cleaned}

    created_event = service.events().insert(calendarId="primary", body=event).execute()
    print("Created event:", created_event.get("htmlLink"))
    return created_event


# function to get event details from Google Calendar by event_id
def get_event(event_id: str):
    service = get_calendar_service()
    return service.events().get(calendarId="primary", eventId=event_id).execute()


def find_events(time_min, time_max, max_results: int = 50):
    service = get_calendar_service()
    r = service.events().list(
        calendarId="primary",
        timeMin=time_min.isoformat(),
        timeMax=time_max.isoformat(),
        singleEvents=True,
        orderBy="startTime",
        maxResults=max_results,
    ).execute()
    return r.get("items", [])

def delete_calendar_event(event_id):
    service = get_calendar_service()
    service.events().delete(calendarId="primary", eventId=event_id).execute()
    return True

def update_calendar_event(event_id, summary=None, description=None, location=None, start_time=None, end_time=None):
    service = get_calendar_service()
    event = service.events().get(calendarId="primary", eventId=event_id).execute()

    if summary:
        event["summary"] = summary
    if description:
        event["description"] = description
    if location:
        event["location"] = location
    if start_time:
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=ZoneInfo(DEFAULT_TZ))
        event["start"]["dateTime"] = start_time.isoformat()
    if end_time:
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=ZoneInfo(DEFAULT_TZ))
        event["end"]["dateTime"] = end_time.isoformat()

    updated_event = service.events().update(calendarId="primary", eventId=event_id, body=event).execute()
    print("Updated event:", updated_event.get("htmlLink"))
    return updated_event
