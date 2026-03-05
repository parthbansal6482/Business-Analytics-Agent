# E-Commerce Intelligence Research Agent

An AI-powered business analytics platform that leverages **LangGraph**, **Gemini 2.0 Flash**, and a modern web stack to provide deep insights into e-commerce data (Shopify integration).

---

## 🚀 Overview

This project is a sophisticated research agent designed to help e-commerce businesses analyze their performance, understand customer behavior, and generate actionable reports. It combines the power of Large Language Models (LLMs) with robust data engineering and a sleek dashboard.

### Key Features

- **AI Research Agent**: Built with LangGraph for complex, multi-step Reasoning and Acting (ReAct).
- **Gemini 2.0 Flash**: High-speed, high-intelligence LLM from Google.
- **Shopify Integration**: Seamless data ingestion and synchronization for products, orders, and customers.
- **Vector Memory**: Uses Qdrant for storing and retrieving contextual information.
- **Relational Data**: PostgreSQL manages structured business data.
- **Interactive Dashboard**: A responsive React (Vite/TypeScript) frontend with rich visualizations using Recharts.

---

## 🛠️ Tech Stack

### Backend
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Agent Orchestration**: [LangGraph](https://langchain-ai.github.io/langgraph/) & [LangChain](https://python.langchain.com/)
- **LLM**: [Google Gemini 2.0 Flash](https://aistudio.google.com/app/apikey)
- **Database**: [PostgreSQL](https://www.postgresql.org/) (Async via SQLAlchemy/asyncpg)
- **Vector Search**: [Qdrant](https://qdrant.tech/)
- **Caching/Task Storage**: [Redis](https://redis.io/)
- **Embeddings**: Local `sentence-transformers`

### Frontend
- **Framework**: [React](https://react.dev/) (with [Vite](https://vitejs.dev/))
- **Language**: [TypeScript](https://www.typescriptlang.org/)
- **Styling**: [Tailwind CSS](https://tailwindcss.com/)
- **State Management**: [Zustand](https://github.com/pmndrs/zustand)
- **Data Fetching**: [TanStack Query](https://tanstack.com/query/latest)
- **Icons**: [Lucide React](https://lucide.dev/)

---

## 📂 Project Structure

```text
.
├── backend/                # FastAPI application
│   ├── agent/             # LangGraph nodes and graph definition
│   ├── data/              # Data ingestion and Shopify sync logic
│   ├── db/                # SQLAlchemy models and migrations
│   ├── memory/            # Qdrant vector store integration
│   ├── routers/           # API endpoints (Upload, Research, Shopify, etc.)
│   └── main.py            # Entry point
├── frontend/               # React TypeScript frontend
│   ├── src/
│   │   ├── components/    # UI components
│   │   ├── hooks/         # Custom React hooks
│   │   ├── pages/         # Page layouts
│   │   └── store/         # Zustand state stores
│   └── package.json
└── docker-compose.yml      # Infrastructure (Postgres, Qdrant, Redis)
```

---

## ⚙️ Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- Docker & Docker Compose

### 1. Infrastructure Setup
Spin up the required services using Docker:
```bash
docker-compose up -d
```
This starts PostgreSQL, Qdrant, and Redis.

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt
cp .env.example .env
# Fill in your GOOGLE_API_KEY and other credentials in .env
python main.py
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
The frontend will be available at `http://localhost:5173`.

---

## 📝 Environment Variables

### Backend (`backend/.env`)
| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Your Google Gemini API Key | Required |
| `POSTGRES_URL` | PostgreSQL connection string | `postgresql+asyncpg://user:password@localhost:5432/ecomm_agent` |
| `QDRANT_URL` | Qdrant service URL | `http://localhost:6333` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `SHOPIFY_API_KEY` | Shopify App API Key | Optional |
| `SHOPIFY_API_SECRET`| Shopify App Secret | Optional |

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License.
