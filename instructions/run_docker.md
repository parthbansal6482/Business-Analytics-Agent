# Running the Application with Docker Compose

This guide explains how to run the entire E-Commerce Intelligence Agent (Frontend, Backend, Postgres, Redis, and Qdrant) on any new machine using Docker.

## Prerequisites

1. Install **Docker** and **Docker Compose** on your system.
   - Mac/Windows: Install [Docker Desktop](https://www.docker.com/products/docker-desktop/).
   - Linux: Install the Docker Engine and Docker Compose plugins.

## Setup Instructions

### 1. Configure the Environment
The application needs some API keys to function. We've provided an `.env.example` file in the root directory.

1. Copy the `.env.example` file to create your own `.env` file in the root directory:
   ```bash
   cp .env.example .env
   ```
2. Open the new `.env` file in a text editor.
3. Fill in your **Groq API Key**:
   ```env
   GROQ_API_KEY=your_actual_key_here
   ```
4. (Optional) If you are using Shopify, fill in your Shopify API keys as well. The database and other settings are pre-configured to work inside Docker, so you don't need to change them.

### 2. Start the Application
Open a terminal in the root directory (where `docker-compose.yml` is located) and run:

```bash
docker compose up --build
```

> [!TIP]
> **Optimized for Mac:** The build is configured to use the **CPU-only** version of AI libraries. This avoids downloading GBs of unnecessary NVIDIA data, saving time and disk space on your MacBook.

**What this command does:**
- `--build`: Forces Docker to build your Frontend and Backend containers from scratch based on their `Dockerfile`s. It also pre-downloads the embedded AI models into the backend image.
- `up`: Starts all 5 services:
  1. `postgres` (port 5433)
  2. `redis` (port 6379)
  3. `qdrant` (port 6333)
  4. `backend` (port 8000)
  5. `frontend` (port 5173)

*Note: The first time you run this, it will take several minutes to download the PostgreSQL, Redis, and Qdrant official images, install Python and Node dependencies, and compile the code.*

### 3. Access the Application
Once the terminal logs show that the Vite frontend server and Uvicorn backend server are running, you can access the application:

- **Frontend UI:** Open your browser and go to `http://localhost:5173`
- **Backend API Docs:** Open your browser and go to `http://localhost:8000/docs`

### 4. Stopping the Application
To stop the application, you can either:
- Press `Ctrl + C` in the terminal where it's running.
- Or, open a new terminal in the same folder and run:
  ```bash
  docker compose down
  ```

**Persistent Data:**
When you stop the application with `docker compose down`, your uploaded CSV data, user preferences, and vector database embeddings are **saved safely**. They are stored in Docker volumes (`pgdata`, `redisdata`, `qdrantdata`) and will be there the next time you run `docker compose up`.

## Troubleshooting

- **API Limits / Errors:** If the agent fails to answer queries, ensure your `.env` file has a valid `GROQ_API_KEY` and that you haven't exceeded Groq's rate limits.
- **Port Conflicts:** Ensure ports `5173`, `8000`, `5433`, `6333`, and `6379` are not being used by other applications on your PC. If they are, you can change the exposed ports in `docker-compose.yml` (e.g., change `"5173:5173"` to `"5174:5173"`).
- **Starting Fresh / Wiping Data:** If you want to delete all your uploaded data and start completely fresh, you can remove the persistent volumes by running:
  ```bash
  docker compose down -v
  ```
  *Warning: This will permanently delete all data in the databases.*
