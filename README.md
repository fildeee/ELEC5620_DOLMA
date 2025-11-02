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


## Contribution Table

| **Name**     | **Allocated Tasks** |
|---------------|----------------------|
| **Oydan**     | • Attended meetings  <br>• Connected Google Calendar API  <br>• Added create/update events functionality  <br>• Added list events functionality  <br>• Added delete events functionality  <br>• Implemented event conflict detection |
| **Masroor**   | • Attended meetings  <br>• Set up initial project using Vite (React + Flask)  <br>• Helped create frontend for pages  <br>• Connected OpenAI API  <br>• Incorporated Docker  <br>• Connected to Google Cloud |
| **Zheng**     | • Attended meetings  <br>• Integrated Weather API for real-time data retrieval  <br>• Integrated Geolocation API to obtain user location  <br>• Enabled weather-based activity recommendations  <br>• Enabled location-based activity recommendations |
| **Divaskar**  | • Attended meetings  <br>• Integrated goal management (adding and completing goals)  <br>• Helped create app skeleton (including frontend design) |
| **Alaukika**  | • Attended meetings  <br>• Integrated avatar customization  <br>• Helped create app skeleton (including frontend design) |


## Project Summary

- Backend: Python (Flask)  
- Frontend: React with Vite  
- APIs Used: OpenAI, OpenWeatherMap, Google Calendar API  
- Containerisation: Docker Compose  
- Purpose: Demonstrate an AI-powered assistant with live weather integration for ELEC5620 coursework.
