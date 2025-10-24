# ELEC5620\_DOLMA

DOLMA

### TO RUN BACKEND

create a .env file in backend dir

store the API keys there as:

OPENAI_API_KEY=xxxxx
OPENWEATHER_API_KEY=your_openweather_api_key

run app.py

Weather and Location
- The app fetches real-time weather from OpenWeatherMap using browser geolocation when available.
- If coordinates aren’t provided, the backend attempts an approximate IP-based location (ip-api.com) suitable for demos.
- For local demos, allow the browser’s location permission prompt on first load.


### TO RUN FRONTEND

in a new terminal

cd into frontend

npm i (first time only, or when new dependancies have been added)

npm run dev

click link

### TO RUN WITH DOCKER

#### INITIAL SETUP

add a .env file in frontend containing: VITE_API_BASE=http://localhost:5000

in the backend/.env, add: FRONTEND_URL=http://localhost:5173

download docker

#### EVERYTIME

launch the docker app

from root, run: docker compose up --build

this will launch both frontend and backend