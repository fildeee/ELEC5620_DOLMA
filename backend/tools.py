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
