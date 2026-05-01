# System Setup and Execution Guide

This guide covers the steps to get the full "Business Analytics" application running.

## 🐳 Recommended Method: Docker (Easiest)

The entire application is containerized for a one-command setup. This is the **strongly recommended** method as it avoids manual installation of databases and dependencies on your machine.

**Steps:**
1. Configure your API keys in the root `.env` file.
2. Run `docker compose up --build`.

For detailed instructions, see: **[instructions/run_docker.md](file:///Users/parthbansal/Projects/Business%20Analytics/instructions/run_docker.md)**

---

## 💻 Alternative Method: Manual Setup

Use this method **only** if you want to develop without Docker.

### 1. External Services
You still need the databases running. You can start just the infrastructure using Docker:
```bash
docker compose up postgres redis qdrant -d
```

### 2. Backend Setup
1. Navigate to `backend/`.
2. Create a virtual environment: `python -m venv venv`.
3. Activate it: `source venv/bin/activate`.
4. Install dependencies: `pip install -r requirements.txt`.
5. Create `backend/.env` (Note: Point URLs to `localhost` instead of Docker service names).
6. Run: `uvicorn main:app --reload`.

### 3. Frontend Setup
1. Navigate to `frontend/`.
2. Install dependencies: `npm install`.
3. Run: `npm run dev`.

---

## 🛠️ Troubleshooting
- **Build Fails**: Run `docker builder prune -f` to clear the cache.
- **Stat .env Not Found**: Ensure you have a `.env` file in the root directory.
- **Port Conflict**: Ensure no other service is using ports 5433, 6379, 6333, 8000, or 5173.
