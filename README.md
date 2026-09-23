# ELEC5620 — DOLMA

DOLMA is an intelligent personal assistant web application for managing a calendar
by conversation. Its assistant is a **ReAct agent** built on the OpenAI API: it reasons
about what you asked, calls Google Calendar and weather tools when it needs them,
observes what they actually return, and only then answers — so its suggestions are
grounded in your real schedule and real conditions rather than in guesswork.

---

## Team

DOLMA was built by a five-person group for ELEC5620 at the University of Sydney.
The original repository is [fildeee/ELEC5620_DOLMA](https://github.com/fildeee/ELEC5620_DOLMA);
the commit history in this repository preserves each contributor's work.

| Contributor | Main areas |
|---|---|
| Masroor Muntasir ([@fildeee](https://github.com/fildeee)) | OpenAI integration, assistant prompting and tool definitions, Docker setup |
| Oydan ([@OydanK](https://github.com/OydanK)) | Google Calendar integration — creating, finding, updating and deleting events |
| Alaukika Vardhan ([@Kia1902](https://github.com/Kia1902)) | Avatar/hat system and the shared avatar context |
| Divaskar ([@Divaskar068](https://github.com/Divaskar068)) | Goal tracking feature (since removed — see [Removed Features](#removed-features)) and frontend UI work |
| Zheng Gong | Weather and location API, timezone handling |

---

## Architecture

The assistant is a **ReAct agent** — Reason, Act, Observe. A chat request is not a
single call to the language model. The model decides whether it needs a tool, the
backend runs it, and the tool's real result is appended to the conversation so the
model can observe it and decide what to do next. The loop repeats until the model
answers in plain language.

This is what lets DOLMA carry out steps it was never explicitly programmed for.
Asked *"should I run outside today?"* it checks the weather, then looks at the day's
events, then answers using both — three passes through the model, with the backend
supplying real data at each step.

### The loop

```text
POST /api/chat
       │
       ▼
   build messages  (system prompt + recent history + the new message)
       │
       ▼
┌──► ① call the model, offering the tool schemas
│        │
│        ├── no tool calls ──► this is the answer; return it
│        │
│        └── tool calls ↓
│    ② append the assistant turn that carries the tool calls
│    ③ execute every tool                    → ToolResult
│    ④ append {"role": "tool", ...}          ← the observation
└────⑤ repeat        (capped at AGENT_MAX_STEPS, default 6)
```

A tool's result splits in two. The `observation` goes to the model, which decides
what it means and how to phrase it. Anything the browser needs to *render* — the
weather card, the confirmation chips — travels separately in `ui`, which the model
never sees and therefore cannot garble.

### Tools

| Tool | Reads or writes | Backed by |
|---|---|---|
| `find_events` | read | Google Calendar API |
| `create_event` | write | Google Calendar API |
| `update_event` | write | Google Calendar API |
| `delete_event` | write | Google Calendar API |
| `find_places` | read | OpenStreetMap (Overpass API) |
| `get_weather` | read | OpenWeatherMap, falling back to Open-Meteo |

The model decides when to call these. Nothing in the request path matches on
keywords — *"is it a good day to cycle to campus?"* reaches `get_weather` exactly as
*"what's the weather?"* does.

### Saying "I don't know"

An agent with tools will reach for one even when none of them fits, and will fill a
gap from memory when asked something it cannot look up. Asked to recommend a nearby
bar before `find_places` existed, DOLMA once answered with five venues and their
street addresses — none of which came from a tool. Two rules in the system prompt
close that off: anything specific (a venue, an address, opening hours, a price) must
come from an observation in the current conversation, and a request no tool covers
gets a plain sentence saying so rather than a speculative tool call.

`find_places` reports OpenStreetMap's fields as they are, including the gaps. A venue
with no recorded address comes back with `address: null`, and the observation says a
null means the detail is not recorded, so it is reported as unlisted rather than
quietly supplied.

### Preview, then confirm

Every write tool takes a `confirm` flag. Called with `confirm=false` it changes
nothing and returns a preview; the model relays that preview and ends its turn. Only
once the user has agreed, in a later message, may it call again with `confirm=true`.

Two rules are enforced in code rather than trusted to the prompt:

- calendar tools are refused outright when no Google account is connected, and
- a write cannot be confirmed in the same turn that previewed it. The user has not
  spoken since, so the agent is not permitted to approve on their behalf.

A preview also returns the `event_ids` it matched, and the confirming call passes
them back, so an update or deletion touches exactly the events the user was shown.

### Arithmetic the model does not do

Two jobs were taken off the model because it was measurably bad at them, and both
are the kind of thing a program is reliably good at.

**Which offset a time has.** The tools once asked for RFC3339 "including offset",
and the schema's own example carried `+11:00`. Sydney is `+11:00` only in daylight
saving; asked in September to book lunch at 11:45 the model wrote
`2026-09-24T11:45:00+11:00`, which is 10:45 local — the event landed an hour early
and nothing caught it, because the string was valid and the confirmation card
obligingly displayed the wrong time. The tools now take a plain wall-clock time and
`formatting.to_sydney_wall_clock` resolves it against `Australia/Sydney`, which
knows where the boundary falls. An offset the model sends anyway is discarded.

**Whether two events collide.** Asked to add lunch at 11:45 when a tutorial ran
until 11:45, the model called it a conflict and then refused to book at all. Every
preview of a new event now carries a `clashes` list computed by
`tool_handlers._clashes_with`, using strict inequality on both sides so that
touching at the boundary is not an overlap, and the model is told to report that
list rather than judge the times itself. A clash is reported, never enforced: the
preview is still shown and the user still decides.

### Failures are observations, not crashes

A tool that errors, receives malformed arguments, or finds nothing does not end the
request. It reports that as an observation, and the model either corrects its
arguments and tries again or explains the problem to the user. A request only fails
outright if the model API itself is unreachable.

### Backend layout

| Module | Responsibility |
|---|---|
| `app.py` | Flask routes, Google OAuth, and assembling each request's messages |
| `agent.py` | the ReAct loop; knows nothing about calendars or weather |
| `tool_handlers.py` | one handler per tool, returning observations rather than HTTP responses |
| `tools.py` | the tool schemas advertised to the model |
| `google_calendar.py` | Google Calendar API calls and OAuth credentials |
| `places.py` | OpenStreetMap lookups for nearby venues |
| `weather.py` | OpenWeatherMap / Open-Meteo lookups and IP geolocation |
| `formatting.py` | Sydney-local date and time formatting shared by both layers |
| `tests/` | the suite described under [Backend Setup](#3-run-the-tests) |
| `pyproject.toml` / `uv.lock` | declared dependencies and the exact resolved versions |

### Response shape

`/api/chat` returns the model's `reply`, whatever the tools produced for the
interface (`events`, `places`, `items`, `cta`, `tips`, `place_name`, `weather`), and a `trace`
of the reason–act–observe steps taken. The trace records each step's reasoning, the
tool called, its arguments and its observation, which makes the agent's decisions
inspectable during a demonstration.

### Agent configuration

| Variable | Default | Meaning |
|---|---|---|
| `OPENAI_MODEL` | `gpt-4o-mini` | the model that reasons and selects tools |
| `AGENT_MAX_STEPS` | `6` | tool rounds allowed before a plain answer is forced |

---

## Removed Features

### Goal tracking

Earlier versions of DOLMA included a goal planner. It had a sidebar panel for
creating goals with a target amount, unit and due date, a progress bar with
manual progress entry, a `/api/goals` REST interface backed by a JSON file, and
three assistant tools (`create_goal`, `update_goal`, `list_goals`) so goals
could also be managed from the chat.

Testing it in practice showed the feature was not useful: it stayed incomplete,
and in day-to-day use it did not earn the space it took in the interface. Rather
than ship a half-finished feature, we removed it — the panel, the API, the
storage layer and the assistant tools all came out together. DOLMA is now
focused on what it does well: conversational calendar management with
weather-aware suggestions.

The code is preserved in the commit history if it is ever worth revisiting.

---

## Backend Setup

Python dependencies are managed with [uv](https://docs.astral.sh/uv/). Install it
once — `curl -LsSf https://astral.sh/uv/install.sh | sh` on macOS or Linux,
`winget install astral-sh.uv` on Windows — and it handles the rest, including
fetching the right Python. You do not need to create a virtualenv or run `pip`.

Everything below runs from the `backend/` directory.

### 1. Create Environment Variables
Inside the `/backend` directory, create a `.env` file and include your API keys:

```env
OPENAI_API_KEY=your_openai_api_key
OPENWEATHER_API_KEY=your_openweather_api_key
```

`OPENAI_API_KEY` is required; without it the assistant cannot reason or select a
tool. `OPENWEATHER_API_KEY` is optional — `weather.py` calls OpenWeatherMap only
when the key is set and otherwise falls back to Open-Meteo, which needs no key but
reports fewer fields, leaving conditions, humidity and "feels like" empty.

### 2. Install Dependencies and Run the Backend

```bash
cd backend
uv sync        # creates .venv from uv.lock, installing the exact pinned versions
uv run app.py
```

`uv sync` is only needed the first time and after the lockfile changes; `uv run`
checks the environment is current on every invocation anyway.

This serves on `http://localhost:5000` by default; set `PORT` in `backend/.env` to
change it. The Google Cloud console must authorise a matching redirect URI —
`http://localhost:5000/api/google/oauth2callback` for the default port.

### 3. Run the Tests

The backend ships with a test suite covering the agent loop and the calendar
tools. It never calls OpenAI, Google or the weather providers — the model and
every external service are replaced by stubs — so it runs offline, instantly and
at no cost:

```bash
cd backend
uv run pytest
```

`pytest` is a development dependency, installed by `uv sync` but excluded from the
Docker image. The suite also runs without any test framework at all, which is
useful if you are working outside uv:

```bash
python tests/run_tests.py
```

### 4. Weather and Location
- Retrieves real-time weather data from OpenWeatherMap using browser geolocation.
- If geolocation is unavailable, the backend uses IP-based location via `ip-api.com` for approximate results.
- For local demos, ensure your browser allows location access when prompted on first load.

---

## Google Calendar Setup

The calendar tools are refused outright until a Google account is connected, so
without this the assistant can still answer weather and places questions but will
tell you to connect Google whenever the calendar comes up. Everything here happens
once, in the [Google Cloud console](https://console.cloud.google.com/).

### 1. Create a project and enable the API

Create a project, then under **APIs & Services → Library** enable the **Google
Calendar API**. Nothing works until the API is enabled on the same project that
issues the credentials below.

### 2. Configure the consent screen and add yourself as a test user

Under **Google Auth Platform → Audience** (older consoles call this the **OAuth
consent screen**), choose the **External** user type and fill in the app name and
support email.

Then add your own Google address under **Test users**. This step is easy to miss
and there is no way to work around it: while the app's publishing status is
**Testing**, Google refuses authorisation for any account not on that list and
returns `access_denied`.

### 3. Create the OAuth client

Under **Credentials → Create credentials → OAuth client ID**, choose the
**Web application** type. Do not choose *Desktop app* — `app.py` drives the web
flow, handing Google an explicit `redirect_uri` that points back at the Flask
server.

Add that callback under **Authorised redirect URIs**, matching the port the
browser reaches the backend on:

```text
http://localhost:5000/api/google/oauth2callback
```

Google compares this string exactly, so it has to agree with `PUBLIC_PORT` (or
`PORT` when no mapping is in play). Under Docker the browser-facing port is 5050,
making the URI `http://localhost:5050/api/google/oauth2callback`. See
[Resolve Port Conflicts](#3-resolve-port-conflicts) if you have moved the backend.

Plain `http` is correct here. Google exempts loopback addresses from its HTTPS
requirement, and so does DOLMA: `app.py` relaxes oauthlib's matching rule only
when the redirect URI comes back to this machine, so no configuration is needed
for local development and a redirect URI pointing anywhere else still has to be
HTTPS.

### 4. Save the credentials

Download the client's JSON and save it as `backend/credentials.json`. Set
`GOOGLE_CLIENT_SECRETS_FILE` if you want it somewhere else. It is excluded by
`.gitignore` and `.dockerignore`, so it is never committed or baked into an image.

### 5. Connect from the app

With both servers running, open `/settings` and choose **Connect Google Calendar**.
Google will warn that the app is unverified — expected for a project in Testing —
so continue through the advanced link. On success the backend writes
`backend/token.json`, `/api/google/status` reports `connected: true`, and the
calendar tools start answering.

### What to expect afterwards

| | |
|---|---|
| **Refresh tokens expire after 7 days** | Google expires the refresh tokens it issues to an app still in **Testing**. When that happens the stored credentials stop refreshing, the app reports itself disconnected, and you reconnect from `/settings`. Worth doing shortly before a demonstration rather than the week before. |
| **One account at a time** | `token.json` is a single file at a fixed path, so the backend holds one user's credentials, not one set per signed-in user. Fine for a prototype; it is the main thing standing between DOLMA and real multi-user deployment. |
| **Disconnecting** | `POST /api/google/disconnect` deletes `token.json`. Deleting the file by hand does the same thing. |

---

## Frontend Setup

### 1. Install Dependencies
Open a new terminal and navigate to the frontend directory:

```bash
cd frontend
npm install
```

### 2. Run the Development Server
To start the frontend:

```bash
npm run dev
```

Click the link shown in the terminal (for example, `http://localhost:5173`) to open the app in your browser.

---

## Run with Docker

### 1. Initial Setup
Create the following `.env` files:

**Backend `.env`:**
```env
OPENAI_API_KEY=your_openai_api_key
OPENWEATHER_API_KEY=your_openweather_api_key
```

You do **not** need a frontend `.env` for Docker: `docker-compose.yml` already sets
`VITE_API_BASE=http://localhost:5050`, along with the backend's `PORT`,
`PUBLIC_PORT`, and `FRONTEND_URL`.

Under Docker the backend listens on port 5000 inside the container but is published
on host port **5050**, so the authorised redirect URI to register in the Google Cloud
console is `http://localhost:5050/api/google/oauth2callback`.

None of your secrets are copied into the image. `.dockerignore` excludes `.env`,
`credentials.json` and `token.json`, and Compose still gives the running container
all three: `.env` through `env_file`, and the two Google files through the
`./backend:/app` bind mount. Keeping them out of the image layers means a built
image can be shared or pushed without carrying your API keys or OAuth client
secret.

If you ever run the backend image directly rather than through Compose, supply them
yourself:

```bash
docker run --env-file ./backend/.env \
  -v "$PWD/backend/credentials.json:/secrets/credentials.json:ro" \
  -e GOOGLE_CLIENT_SECRETS_FILE=/secrets/credentials.json \
  -p 5050:5000 <image>
```

Install Docker Desktop if it is not already installed.

### 2. Launch Containers
From the project root, run:

```bash
docker compose up --build
```

This command will build and run both the frontend and backend containers concurrently.

---

## Error Handling Guide

### 1. Validate Configuration Files
Ensure the following configuration files exist and are correctly set up:
- Backend: `.env`, `credentials.json`
- Frontend: `.env`

Verify that:
- All API keys and environment variables are valid  
- File paths are correct  
- No missing or outdated configuration values exist

---

### 2. Fix Dependency Issues
If dependency errors occur, rebuild the backend environment from the lockfile:

```bash
cd backend
rm -rf .venv
uv sync
```

`uv sync` recreates `.venv` at exactly the versions recorded in `uv.lock`, so this
resolves anything caused by a drifted or half-installed environment.

| Command | What it does |
|---|---|
| `uv sync` | Make `.venv` match `uv.lock` exactly |
| `uv run <cmd>` | Run a command in that environment, syncing first if needed |
| `uv add <pkg>` | Add a dependency to `pyproject.toml` and update the lockfile |
| `uv add --dev <pkg>` | Same, but for development-only tools such as `pytest` |
| `uv lock --upgrade` | Re-resolve within the constraints in `pyproject.toml` |

Note: You do not need to configure a Python SDK in your IDE, and you should not run
`pip` in this project — `uv.lock` is the source of truth and is committed to the
repository. Dependency versions are changed by editing `pyproject.toml` (or using
`uv add`) and committing the updated lockfile, never by installing into `.venv` by
hand.

---

### 3. Resolve Port Conflicts
The backend port is configuration, not code — never edit `app.py` to change it.

| Variable | Default | Meaning |
|---|---|---|
| `PORT` | `5000` | Port the backend listens on |
| `PUBLIC_PORT` | same as `PORT` | Port the **browser** reaches the backend on (differs when a port mapping is in play, as with Docker) |
| `GOOGLE_REDIRECT_URI` | `http://localhost:$PUBLIC_PORT/api/google/oauth2callback` | Overrides the OAuth callback outright |
| `FRONTEND_URL` | `http://localhost:5173` | Added to the CORS allow-list |

To move the backend to 5050, set `PORT=5050` in `backend/.env` and
`VITE_API_BASE=http://localhost:5050` in `frontend/.env`, then register
`http://localhost:5050/api/google/oauth2callback` in the Google Cloud console.

Whatever you choose, these three must agree: `VITE_API_BASE`, the port the backend
listens on, and the redirect URI authorised in Google Cloud.

**On macOS, port 5000 is usually already taken.** The AirPlay Receiver in Control
Centre listens on it, so the default port fails on a stock machine. Confirm with:

```bash
lsof -nP -iTCP:5000 -sTCP:LISTEN
```

A `ControlCe` process in that output is AirPlay. Either move the backend to 5050
as described above, or turn the receiver off under **System Settings → General →
AirDrop & Handoff → AirPlay Receiver**. Moving the backend is the less intrusive
of the two, and is what the Docker setup does anyway.

---

## Incorporation of Advanced Technologies

Our prototype integrates several advanced technologies across its architecture to demonstrate innovation and technical depth:

- **Frontend Framework – React (with Vite):**  
  The user interface is built with React for modular, component-based design and Vite for fast builds, hot module replacement, and optimized performance.

- **Backend Framework – Flask:**  
  The backend uses Flask to manage API endpoints, handle communication with external services, and serve AI and scheduling requests. Flask’s lightweight and extensible design enables seamless integration with cloud deployments and containerization.

- **Cloud Services – Google Cloud:**  
  A Google Cloud project underpins the calendar integration. The Google Calendar API is enabled there, and the OAuth 2.0 client credentials, consent screen and authorised redirect URIs that let DOLMA act on a user's calendar with their consent are issued and managed through the Cloud console. The application itself runs locally or under Docker Compose; it is not hosted on Google Cloud.

- **Calendar Integration – Google Calendar API:**  
  DOLMA connects to the Google Calendar API over OAuth 2.0 to find, create, update and delete events in real time through natural-language interaction, enabling AI-driven schedule management.

- **Agent Architecture – ReAct (Reason → Act → Observe):**  
  The assistant is an agent, not a single prompt-and-reply call. The model reasons about each request, decides whether to act, and has every tool result fed back into the conversation as an observation before it replies — so it can chain steps, correct itself after a failed call, and ground its answers in data it has actually seen. A per-request trace of these steps is returned with every reply.

- **AI Integration – OpenAI API function calling:**  
  Tools are advertised to the model as JSON schemas and selected by the model itself; the backend executes them and reports the outcome. Write operations pass through a preview-and-confirm protocol enforced in code, so the assistant can never change a user's calendar without explicit approval.

- **External Data – OpenWeatherMap and OpenStreetMap:**  
  Real-time weather comes from the OpenWeatherMap API, falling back to Open-Meteo, and nearby venues from OpenStreetMap through the Overpass API; both use browser geolocation with IP-based detection as a fallback. Grounding recommendations in a live lookup is also what keeps the assistant from inventing them: it can only name a place a query returned.

- **Dependency Management – uv:**  
  Python dependencies are declared in `pyproject.toml` and pinned in a committed `uv.lock`, so every developer and the Docker image resolve to byte-identical versions of the whole transitive graph. uv also provisions the interpreter itself, removing "works on my machine" differences in Python version, and separates development-only tooling from what ships in the runtime image.

- **Containerisation – Docker:**  
  Both the frontend and backend are containerized using Docker and orchestrated with Docker Compose, so the application runs identically on every developer's machine and is ready to deploy without further packaging work.

- **Automated Testing – dependency-free suite:**  
  The agent loop and the calendar tools are covered by tests that stub the language model and every external service, so the agent's decisions and its safety rules can be verified deterministically, offline and at no cost.

- **Agile Workflow – Jira:**  
  Development followed iterative sprints managed through Jira, supporting structured backlog tracking, sprint retrospectives, and continuous integration of new features.

Together, these technologies showcase DOLMA’s end-to-end use of **modern web frameworks, cloud service integration, agentic AI, and agile delivery**, reflecting a robust and innovative engineering approach.

## Project Summary

- Backend: Python (Flask)  
- Frontend: React with Vite  
- Assistant: ReAct agent over OpenAI function calling, with five tools  
- APIs Used: OpenAI, Google Calendar, OpenWeatherMap (Open-Meteo as fallback)  
- Containerisation: Docker Compose  
- Testing: `python tests/run_tests.py` from `backend/`, no extra dependencies  
- Purpose: Demonstrate an agentic AI assistant for conversational calendar management, for ELEC5620 coursework.
