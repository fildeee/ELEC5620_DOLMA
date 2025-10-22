import json
from datetime import datetime

calendar_tools = [
    {
        "type": "function",
        "function": {
            "name": "create_event",
            "description": "Create a Google Calendar event. Ask user for missing details before calling with confirm=true",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "Event title"},
                    "description": {"type": "string"},
                    "start_time": {
                        "type": "string",
                        "description": "ISO8601 datetime with timezone and year (RFC3339). MUST include year and offset, e.g. 2025-11-22T14:00:00+11:00"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "ISO8601 datetime with timezone and year (RFC3339). MUST include year and offset, e.g. 2025-11-22T16:00:00+11:00"
                    },
                    "location": {"type": "string"},
                    "attendees": {"type": "array", "items": {"type": "string"}, "description": "Emails"},
                    "recurrence": {"type": "array", "items": {"type": "string"}, "description": "e.g. ['RRULE:FREQ=WEEKLY;COUNT=5']"},
                    "reminders": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"method": {"type": "string"}, "minutes": {"type": "integer"}},
                            "required": ["method", "minutes"]
                        }
                    },
                    "confirm": {"type": "boolean", "description": "Call with true only after user explicitly agrees"}
                },
                "required": ["summary", "start_time", "end_time"]
            }
        }
    },
    # {
    #     "type": "function",
    #     "name": "get_events",
    #     "description": "Retrieves a list of calendar events",
    #     "parameters": {
    #         "type": "object",
    #         "properties": {
    #     }
    # }
]
