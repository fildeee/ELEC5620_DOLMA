from flask import Flask, request, jsonify, redirect, session
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import os
from typing import Optional

from google_auth_oauthlib.flow import Flow

import agent
from formatting import _current_sydney_datetime
from google_calendar import (
    TOKEN_PATH,
    is_connected,
    save_creds,
)
from tool_handlers import ToolContext, make_dispatcher
from tools import agent_tools
from weather import get_client_ip

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Port the browser reaches this backend on. Keep it in sync with the frontend's
# VITE_API_BASE; when running behind a port mapping (Docker), PUBLIC_PORT is the
# host-side port while PORT is the one we actually listen on.
PORT = int(os.getenv("PORT", "5000"))
PUBLIC_PORT = os.getenv("PUBLIC_PORT", str(PORT))

GOOGLE_SCOPES = ["https://www.googleapis.com/auth/calendar"]
GOOGLE_CLIENT_SECRETS_FILE = os.getenv(
    "GOOGLE_CLIENT_SECRETS_FILE", os.path.join(BASE_DIR, "credentials.json")
)
# Must match an authorised redirect URI in the Google Cloud console, and must be
# reachable from the browser (not just from inside the container).
REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI",
    f"http://localhost:{PUBLIC_PORT}/api/google/oauth2callback",
)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


def _is_loopback_http(url: Optional[str]) -> bool:
    """True for a plain-HTTP callback that comes back to this machine."""
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url or "")
    except Exception:
        return False
    return parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1", "::1")


# oauthlib refuses to finish an OAuth exchange over plain HTTP, and nobody can
# serve HTTPS on localhost without a certificate the browser will reject anyway.
# Google exempts loopback redirect URIs from its own HTTPS requirement for that
# reason; relax oauthlib on the same terms and no further. A redirect URI that
# points anywhere but this machine still has to be HTTPS, and setdefault leaves
# an explicit setting in the environment alone.
if _is_loopback_http(REDIRECT_URI):
    os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

def _origin_from_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        pass
    return url.rstrip("/") if isinstance(url, str) else None

def _cors_origins() -> list[str]:
    override = os.getenv("CORS_ALLOW_ORIGINS")
    if override:
        origins = []
        for origin in override.split(","):
            origin = origin.strip()
            if origin:
                parsed = _origin_from_url(origin) or origin.rstrip("/")
                origins.append(parsed)
        return origins

    defaults = {"http://localhost:5173", "http://127.0.0.1:5173"}
    if FRONTEND_URL:
        base = _origin_from_url(FRONTEND_URL)
        if base:
            defaults.add(base)
            if "localhost" in base:
                defaults.add(base.replace("localhost", "127.0.0.1"))
    return [origin.rstrip("/") for origin in defaults if origin]


# Credentialed CORS must name its origins: with the default "*" flask-cors
# reflects whatever Origin is sent, which lets any site call us with cookies.
CORS(app, origins=_cors_origins(), supports_credentials=True)

@app.get("/api/google/status")
def google_status():
    return jsonify({"connected": is_connected()})

@app.get("/api/google/login")
def google_login():
    flow = Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRETS_FILE,
        scopes=GOOGLE_SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    session["oauth_state"] = state
    # authorization_url() generates a PKCE verifier and sends Google only its
    # hash. The callback builds a second Flow, so the verifier itself has to
    # travel in the session; without it Google rejects the exchange with
    # "Missing code verifier".
    session["oauth_code_verifier"] = flow.code_verifier
    return redirect(authorization_url)

@app.get("/api/google/oauth2callback")
def google_oauth2callback():
    state = session.get("oauth_state")
    if not state:
        return "Missing OAuth state. Try connecting again.", 400
    flow = Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRETS_FILE,
        scopes=GOOGLE_SCOPES,
        redirect_uri=REDIRECT_URI,
        state=state,
        code_verifier=session.get("oauth_code_verifier"),
    )
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    save_creds(creds)
    return redirect(f"{FRONTEND_URL}/settings?google=connected")

@app.post("/api/google/disconnect")
def google_disconnect():
    try:
        if os.path.exists(TOKEN_PATH):
            os.remove(TOKEN_PATH)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# The model that reasons and picks tools, and how many reason/act rounds it may
# take before we force a plain-language answer.
CHAT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
AGENT_MAX_STEPS = int(os.getenv("AGENT_MAX_STEPS", str(agent.DEFAULT_MAX_STEPS)))

# Turns of chat history replayed to the model. The browser holds the transcript;
# tool messages are not replayed, so each request reasons from a clean slate.
HISTORY_TURNS = 6


def _system_prompt(has_location: bool) -> str:
    now = _current_sydney_datetime()
    return (
        "You are DOLMA, a friendly and intelligent personal assistant. "
        "Your job is to help the user manage their calendar, find what is nearby, and "
        "keep on top of what is coming up. Stay within that role. "
        f"It is currently {now.strftime('%A, %d %B %Y')} in Sydney, Australia — include "
        f"the year ({now.year}) whenever you mention a date.\n"
        "Every time you read or write is Sydney local time. Give the calendar tools "
        "the wall-clock time the user said, with no UTC offset on it: write "
        "2026-09-24T11:45:00, never 2026-09-24T11:45:00+11:00. Daylight saving is "
        "not yours to work out — the backend applies the right offset for the date, "
        "and an offset you add yourself will be discarded.\n"
        "\n"
        "HOW YOU WORK\n"
        "You work in a reason–act–observe loop. On each turn you may either answer the "
        "user or call one or more tools. When you call a tool you will be shown its real "
        "result before you reply, and you may then call another tool. Work in steps: "
        "look things up before acting on them, and chain calls when a task needs it "
        "(for example check the weather, then look at the day's events, then advise).\n"
        "\n"
        "Never state a result you have not observed. If you have not called find_events, "
        "you do not know what is on the calendar. If a tool reports an error or missing "
        "input, either fix the arguments and call it again or tell the user plainly what "
        "went wrong — do not pretend it succeeded.\n"
        "\n"
        "NEVER INVENT SPECIFICS\n"
        "Venue names, addresses, opening hours, websites, prices and event details must "
        "come from a tool result you have seen in this conversation. Where a tool returns "
        "a field as null, that detail is simply not recorded — say it is not listed. Do "
        "not fill a gap from your own knowledge: a confident invented address is worse for "
        "the user than an honest 'I don't know'.\n"
        "\n"
        "WHEN YOU CANNOT HELP\n"
        "Your tools are the whole of what you can do — the calendar, nearby places and the "
        "weather. When the user asks for something none of them covers, such as booking a "
        "table, sending an email or reading a web page, say so plainly in a sentence and "
        "point them somewhere that can. Do not call a tool in the hope that it helps, and "
        "do not answer from memory instead.\n"
        "\n"
        "CHANGING THINGS\n"
        "Only touch the user's calendar when they ask you to. Every write tool "
        "takes a `confirm` flag: call it first with confirm=false, relay the preview you "
        "get back, and end your turn there. Only use confirm=true once the user has "
        "agreed in a later message — never in the same turn as the preview.\n"
        "\n"
        "NEARBY PLACES AND WEATHER\n"
        "Call find_places whenever the user wants somewhere to go or asks what is around "
        "them, and report only the places it returns. Call get_weather whenever conditions "
        "matter — the user asks, or you are advising on something outdoors. "
        + (
            "The user has granted their location, so get_weather will work.\n"
            if has_location
            else "The user has not granted location; get_weather will fall back to a rough "
            "IP estimate and may fail.\n"
        )
        + "\n"
        "SCHEDULING CONFLICTS\n"
        "When the user asks you to put something in the calendar, go straight to "
        "create_event. Do not look the day up first: the preview you get back already "
        "carries a `clashes` list, worked out from their calendar for you. Report that "
        "list as it stands — empty means the slot is free and you say so, otherwise name "
        "what is in it.\n"
        "Never decide for yourself, from times you have read, that two events overlap. "
        "An event ending at 11:45 leaves 11:45 free, and the list has already applied "
        "that rule properly. Do not describe a clash that is not in it.\n"
        "A clash is for the user to weigh and never a veto. Whatever the list says, show "
        "the preview and ask — do not refuse to schedule something, and do not propose a "
        "reschedule unasked. Carry out what the user asked for."
    )


@app.post("/api/chat")
def chat():
    data = request.get_json(force=True, silent=True) or {}
    user_message = data.get("message")
    conversation = data.get("conversation", [])
    user_location = data.get("location")

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    lat = lon = None
    if isinstance(user_location, dict):
        try:
            lat = float(user_location.get("lat"))
            lon = float(user_location.get("lon"))
        except (TypeError, ValueError):
            lat = lon = None

    history = [m for m in conversation if m.get("role") in ("user", "assistant")][-HISTORY_TURNS:]
    messages = [{"role": "system", "content": _system_prompt(lat is not None)}]
    messages.extend({"role": m["role"], "content": m.get("text", "")} for m in history)
    if lat is not None and lon is not None:
        messages.append({
            "role": "system",
            "content": f"User granted location. Approx coordinates: lat={lat:.5f}, lon={lon:.5f}.",
        })
    messages.append({"role": "user", "content": user_message})

    ctx = ToolContext(lat=lat, lon=lon, client_ip=get_client_ip(request))

    try:
        run = agent.run(
            client=client,
            model=CHAT_MODEL,
            messages=messages,
            tools=agent_tools,
            dispatch=make_dispatcher(ctx),
            max_steps=AGENT_MAX_STEPS,
        )
    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500

    # Whatever the tools produced for the UI, plus the model's own words on top.
    payload = dict(run.ui)
    payload["reply"] = run.reply
    # The reason/act/observe record, for the debug console and the report.
    payload["trace"] = run.trace
    payload["stop_reason"] = run.stop_reason
    return jsonify(payload)


@app.get("/api/health")
def health():
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=PORT)
