# System Setup and Execution Guide

This guide covers the steps to get the full "Business Analytics" application running on your local machine.

## Prerequisites
- **Python**: 3.11+
- **Node.js**: 18+ (with `npm`)
- **Docker**: For running PostgreSQL, Redis, and Qdrant.

---

## 1. Backend Setup

Detailed configuration for the backend service.

### Step 1: Install Dependencies
Navigate to the backend directory and install Python packages:
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Configure Environment
Create a `.env` file in the `backend/` directory (you can copy `.env.example` if it exists):
```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/analytics

# LLM Selection
LLM_PROVIDER=gemini  # or 'openrouter'
GOOGLE_API_KEY=your_key
OPENROUTER_API_KEY=your_key

# Vector DB
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

### Step 3: Start External Services (Docker)
Ensure your Docker Desktop is running, then start the database and cache:
```bash
cd backend
docker-compose up -d
```

### Step 4: Run the Backend
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

---

## 2. Frontend Setup

The frontend is a React + Vite application.

### Step 1: Install Dependencies
```bash
cd frontend
npm install
```

### Step 2: Run the Frontend
```bash
cd frontend
npm run dev
```
The app should now be accessible at `http://localhost:5173`.

---

## 3. Switching LLMs (Optional)
If you want to switch from Gemini to OpenRouter (to save costs or use Open Source models):
1. Open `backend/.env`.
2. Change `LLM_PROVIDER=openrouter`.
3. Add your `OPENROUTER_API_KEY`.
4. Restart the backend process.

For more details, see `instructions/llm_switching.md`.

---

## 4. Troubleshooting
- **CORS Errors**: Ensure the frontend is on port 5173.
- **DB Connection**: Check that `docker-compose` started successfully.
- **Missing Module**: If you see `ModuleNotFoundError`, ensure the virtual environment is activated and `pip install` was run.
