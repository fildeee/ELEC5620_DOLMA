calendar_tools = [
    {
    "type": "function",
    "function": {
        "name": "create_event",
        "description": "Create one or more Google Calendar events. Ask user for missing details before calling with confirm=true.",
        "parameters": {
        "type": "object",
        "properties": {
            "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                "summary": { "type": "string", "description": "Event title" },
                "description": { "type": "string" },
                "start_time": {
                    "type": "string",
                    "description": "RFC3339 datetime including year and offset, e.g. 2025-11-22T14:00:00+11:00"
                },
                "end_time": {
                    "type": "string",
                    "description": "RFC3339 datetime including year and offset, e.g. 2025-11-22T16:00:00+11:00"
                },
                "location": { "type": "string" },
                "attendees": {
                    "type": "array",
                    "items": { "type": "string" },
                    "description": "Attendee emails"
                },
                "recurrence": {
                    "type": "array",
                    "items": { "type": "string" },
                    "description": "e.g. ['RRULE:FREQ=WEEKLY;COUNT=5']"
                },
                "reminders": {
                    "type": "array",
                    "items": {
                    "type": "object",
                    "properties": {
                        "method": { "type": "string" },
                        "minutes": { "type": "integer" }
                    },
                    "required": ["method", "minutes"]
                    }
                }
                },
                "required": ["summary", "start_time", "end_time"]
            }
            },
            "confirm": {
            "type": "boolean",
            "description": "Call with true only after the user explicitly agrees"
            }
        },
        "required": ["events"]
        }
    }
    },
    {
        "type": "function",
        "function": {
            "name": "find_events",
            "description": "List calendar events in a time window. Supports presets like today/this_week/next_week. Read-only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "preset": {
                        "type": "string",
                        "enum": ["today", "tomorrow", "this_week", "next_week"],
                        "description": "If set, ignore time_min/time_max and use preset in Australia/Sydney."
                    },
                    "time_min": {
                        "type": "string",
                        "description": "RFC3339 start (e.g. 2025-11-04T00:00:00+11:00). Used when preset is not provided."
                    },
                    "time_max": {
                        "type": "string",
                        "description": "RFC3339 end (e.g. 2025-11-04T23:59:59+11:00). Used when preset is not provided."
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Optional cap. Default 50."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_event",
            "description": "Delete one or more events matching a title keyword and optional date range or preset. Shows preview first, confirm=true to apply.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Title keyword(s) to match, e.g. 'gym' or 'meeting with John'."
                    },
                    "preset": {
                        "type": "string",
                        "enum": ["today", "tomorrow", "this_week", "next_week"],
                        "description": "Optional preset to narrow search window."
                    },
                    "time_min": {"type": "string"},
                    "time_max": {"type": "string"},
                    "confirm": {"type": "boolean"}
                },
                "required": ["query"]
            }
        }
    },
    
    {
        "type": "function",
        "function": {
            "name": "update_event",
            "description": "Update one or more Google Calendar events matching a title or keyword. Use for changing details like title, description, location, or time. Always preview before confirming.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Title or keyword(s) to identify events (e.g. 'meeting', 'gym and study')."
                    },
                    "preset": {
                        "type": "string",
                        "enum": ["today", "tomorrow", "this_week", "next_week"],
                        "description": "Optional preset time range to limit search scope."
                    },
                    "time_min": {
                        "type": "string",
                        "description": "Optional custom range start in RFC3339 (e.g. 2025-11-02T00:00:00+11:00)."
                    },
                    "time_max": {
                        "type": "string",
                        "description": "Optional custom range end in RFC3339."
                    },
                    "summary": {
                        "type": "string",
                        "description": "New event title (optional)."
                    },
                    "description": {
                        "type": "string",
                        "description": "New event description (optional)."
                    },
                    "location": {
                        "type": "string",
                        "description": "New event location (optional)."
                    },
                    "start_time": {
                        "type": "string",
                        "description": "New start time in RFC3339 format."
                    },
                    "end_time": {
                        "type": "string",
                        "description": "New end time in RFC3339 format."
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "Set to true only after preview and user confirmation."
                    }
                },
                "required": ["query"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "create_goal",
            "description": "Create a new personal goal for the user. Present a preview before calling with confirm=true.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Short goal title."},
                    "description": {"type": "string", "description": "Optional detail about the goal."},
                    "target_date": {
                        "type": "string",
                        "description": "Optional target completion date in ISO8601 (e.g. 2025-09-12)."
                    },
                    "target_value": {
                        "type": "number",
                        "description": "Optional numeric target total (e.g. 70 for 70 km, 120 for pages)."
                    },
                    "target_unit": {
                        "type": "string",
                        "description": "Unit for the goal target (e.g. km, pages, $, minutes)."
                    },
                    "target_period": {
                        "type": "string",
                        "description": "Optional cadence or context like 'this week' or 'by Saturday'."
                    },
                    "progress_value": {
                        "type": "number",
                        "description": "Optional starting progress expressed in the same unit as the target."
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "Set true only after the user approves the goal."
                    },
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_goal",
            "description": "Update an existing goal's progress, details, or status. Confirm with the user before making changes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal_id": {"type": "string", "description": "Identifier of the goal to update."},
                    "goal_title": {
                        "type": "string",
                        "description": "Use when the goal ID is unknown; provide the goal title or a distinctive part of it."
                    },
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "target_date": {
                        "type": "string",
                        "description": "New target date in ISO8601 (e.g. 2025-10-01)."
                    },
                    "progress": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                        "description": "Progress percentage from 0 to 100."
                    },
                    "progress_value": {
                        "type": "number",
                        "description": "Amount of progress completed so far in the goal's unit."
                    },
                    "status": {
                        "type": "string",
                        "enum": ["active", "completed", "archived"],
                        "description": "New goal status."
                    },
                    "target_value": {
                        "type": "number",
                        "description": "Update the goal's total target amount."
                    },
                    "target_unit": {
                        "type": "string",
                        "description": "Update the goal's unit (e.g. km, pages, $)."
                    },
                    "target_period": {
                        "type": "string",
                        "description": "Update the cadence/context like 'this week'."
                    },
                    "note": {
                        "type": "string",
                        "description": "Optional note or milestone update to add to the goal history."
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "Set true only after the user confirms the update."
                    },
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_goals",
            "description": "Retrieve the user's goals for summary or review.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["active", "completed", "archived"],
                        "description": "Optional filter for goal status."
                    }
                }
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
