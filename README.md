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



### ERROR HANDLING GUIDE

If you encounter a **403 (Fetch Forbidden)** error or **dependency-related issues**, follow the steps below to diagnose and resolve them.

---

### 1. Validate Configuration Files
Ensure the following configuration files are correct and up to date:

- **Backend:** `.env` and `credentials.json`
- **Frontend:** `.env`

Double-check that:
- All environment variables are defined and valid  
- API keys, database URIs, and authentication tokens are correct  
- The paths in your code reference these files properly  

---

### 2. Fix Dependency Issues
If you’re encountering missing package or version-related errors, reset your backend environment with the following steps:

```bash
# From the project root
cd backend

# Create a new virtual environment
python3 -m venv .venv                            

# Activate the environment
source .venv/bin/activate

# Install dependencies
.venv/bin/pip install -r requirements.txt

# Run the backend
.venv/bin/python app.py

```

**Note**: You don’t need to configure any Python SDK in your IDE file structure.  
The virtual environment handles all required dependencies locally.  

### 3. Resolve Port Conflicts  
If you encounter a port-related error, ensure that all services are running on the same port (recommended: **5050**).  

Update the following files:  
- `compose.yml`  
- `.env` in the **frontend**  
- `App.py` in the **backend**  

Also make sure the `App.py` includes:  

```python
if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5050)
```

