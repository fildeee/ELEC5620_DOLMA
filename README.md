# ELEC5620 — DOLMA

DOLMA is an intelligent personal assistant web application that integrates OpenAI and OpenWeatherMap APIs to provide real-time conversational responses and contextual weather information based on user location.

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
| Divaskar ([@Divaskar068](https://github.com/Divaskar068)) | Goal tracking feature and frontend UI work |
| Zheng Gong | Weather and location API, timezone handling |

---

## Backend Setup

### 1. Create Environment Variables
Inside the `/backend` directory, create a `.env` file and include your API keys:

```env
OPENAI_API_KEY=your_openai_api_key
OPENWEATHER_API_KEY=your_openweather_api_key
```

### 2. Run the Backend
Start the backend service by executing:

```bash
python app.py
```

This serves on `http://localhost:5000` by default; set `PORT` in `backend/.env` to
change it. The Google Cloud console must authorise a matching redirect URI —
`http://localhost:5000/api/google/oauth2callback` for the default port.

### 3. Weather and Location
- Retrieves real-time weather data from OpenWeatherMap using browser geolocation.
- If geolocation is unavailable, the backend uses IP-based location via `ip-api.com` for approximate results.
- For local demos, ensure your browser allows location access when prompted on first load.

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
If dependency errors occur, reset your backend environment:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

Note: You do not need to configure a Python SDK in your IDE. The virtual environment manages all dependencies locally.

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

---

## Incorporation of Advanced Technologies

Our prototype integrates several advanced technologies across its architecture to demonstrate innovation and technical depth:

- **Frontend Framework – React (with Vite):**  
  The user interface is built with React for modular, component-based design and Vite for fast builds, hot module replacement, and optimized performance.

- **Backend Framework – Flask:**  
  The backend uses Flask to manage API endpoints, handle communication with external services, and serve AI and scheduling requests. Flask’s lightweight and extensible design enables seamless integration with cloud deployments and containerization.

- **Cloud Services – Google Cloud:**  
  Hosted and deployed on Google Cloud for scalability, reliability, and secure environment management, supporting both frontend and backend components.

- **Calendar Integration – Google Calendar API:**  
  DOLMA connects with the Google Calendar API to fetch, update, and optimize user events in real time through natural-language interaction, enabling AI-driven schedule management.

- **AI Integration – OpenAI API:**  
  The OpenAI API powers conversational intelligence, generating context-aware responses and personalized suggestions based on user queries and calendar data.

- **External Data – OpenWeatherMap API:**  
  The system integrates real-time weather information via the OpenWeatherMap API, using geolocation and IP-based detection to provide contextual recommendations.

- **Containerisation – Docker:**  
  Both the frontend and backend are containerized using Docker and orchestrated with Docker Compose, ensuring consistent environments across development and deployment.

- **Agile Workflow – Jira:**  
  Development followed iterative sprints managed through Jira, supporting structured backlog tracking, sprint retrospectives, and continuous integration of new features.

Together, these technologies showcase DOLMA’s end-to-end use of **modern web frameworks, cloud infrastructure, AI integration, and agile delivery**, reflecting a robust and innovative engineering approach.

## Project Summary

- Backend: Python (Flask)  
- Frontend: React with Vite  
- APIs Used: OpenAI, OpenWeatherMap, Google Calendar API  
- Containerisation: Docker Compose  
- Purpose: Demonstrate an AI-powered assistant with live weather integration for ELEC5620 coursework.
