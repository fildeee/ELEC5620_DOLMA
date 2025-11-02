# ELEC5620 — DOLMA

DOLMA is an intelligent personal assistant web application that integrates OpenAI and OpenWeatherMap APIs to provide real-time conversational responses and contextual weather information based on user location.

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

**Frontend `.env`:**
```env
VITE_API_BASE=http://localhost:5000
```

**Backend `.env`:**
```env
FRONTEND_URL=http://localhost:5173
OPENAI_API_KEY=your_openai_api_key
OPENWEATHER_API_KEY=your_openweather_api_key
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
If ports are already in use or mismatched, ensure all services run on the same port (recommended: 5050).

Update the following:
- `compose.yml`
- `frontend/.env`
- `backend/app.py`

Ensure the backend includes:

```python
if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5050)
```

---

## Project Summary

- Backend: Python (Flask)  
- Frontend: React with Vite  
- APIs Used: OpenAI, OpenWeatherMap, ip-api  
- Containerisation: Docker Compose  
- Purpose: Demonstrate an AI-powered assistant with live weather integration for ELEC5620 coursework.
