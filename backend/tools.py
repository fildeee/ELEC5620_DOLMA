agent_tools = [
    {
    "type": "function",
    "function": {
        "name": "create_event",
        "description": "Create one or more Google Calendar events. Call with confirm=false first to get a preview back; only call again with confirm=true after the user has explicitly agreed in a later message.",
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
            "description": "Delete one or more events matching a title keyword and optional date range or preset. Call with confirm=false first; the preview returns the matching event_ids. Only call with confirm=true after the user agrees.",
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
                    "event_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Event IDs returned by this tool's preview. Pass them back on the confirm call so only the previewed events are touched."
                    },
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
            "description": "Update one or more Google Calendar events matching a title or keyword. Call with confirm=false first; the preview returns the matching event_ids. Only call with confirm=true after the user agrees.",
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
                    "event_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Event IDs returned by this tool's preview. Pass them back on the confirm call so only the previewed events are touched."
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
            "name": "find_places",
            "description": "Find real places near the user, from OpenStreetMap. Use this whenever the user asks what is nearby or wants somewhere to go \u2014 a bar, a cafe, a gym. Never name a venue that this tool did not return. Read-only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["bank", "bar", "cafe", "gym", "hospital", "library", "nightclub", "park", "pharmacy", "restaurant", "supermarket"],
                        "description": "The closest category to what the user asked for. 'bar' also covers pubs, 'restaurant' also covers takeaway."
                    },
                    "keyword": {
                        "type": "string",
                        "description": "Optional. Only return places whose name contains this text."
                    },
                    "radius_m": {
                        "type": "integer",
                        "description": "Search radius in metres. Default 1500, maximum 5000."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "How many places to return. Default 8, maximum 20."
                    }
                },
                "required": ["category"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for the user's location, with clothing and outdoor-activity tips. Call this whenever the weather is relevant \u2014 the user asks about it, or you need it to advise on an outdoor event. Uses the browser location the user granted, falling back to an IP estimate. Read-only.",
            "parameters": {
                "type": "object",
                "properties": {}
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
