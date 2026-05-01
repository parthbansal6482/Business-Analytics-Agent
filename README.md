# E-Commerce Intelligence Research Agent

An AI-powered business analytics platform that leverages **LangGraph**, **Gemini 2.0 Flash**, and a modern web stack to provide deep insights into e-commerce data, specifically optimized for Shopify integration.

---

## 🚀 Overview

This project is a sophisticated research agent designed to help e-commerce businesses analyze their performance, understand customer behavior, and generate actionable reports. It combines the power of Large Language Models (LLMs) with robust data engineering and a sleek, interactive dashboard.

### Key Features

- **Multi-Mode AI Research Agent**: Built with LangGraph for complex, multi-step Reasoning and Acting (ReAct). Supports both "Quick" and "Deep" analysis modes.
- **Gemini 2.0 Flash**: High-speed, high-intelligence LLM from Google used for intent classification, analysis, and report generation.
- **Shopify Integration**: Seamless data ingestion for products, orders, and customers (Note: Currently hidden in UI to prioritize manual uploads).
- **Vector Memory & RAG**: Uses Qdrant for storing and retrieving contextual information (catalog, reviews, competitors) to minimize hallucinations.
- **Structured Data Management**: PostgreSQL manages structured business metrics and session history.
- **Rich Dashboard**: A responsive React (Vite/TypeScript) frontend with interactive visualizations using Recharts and Tailwind CSS.

---

## 🏗️ Architecture

The system follows a modular architecture with a clear separation between the agentic reasoning layer, the data layer, and the presentation layer.

### Agentic Flow (LangGraph)

```mermaid
graph TD
    User([User Query]) --> Intent[Intent Classifier]
    Intent --> Clarify{Needs Clarification?}
    Clarify -- Yes --> User
    Clarify -- No --> Memory[Memory Loader]
    Memory --> Retriever[Data Retriever]
    Retriever --> Mode{Mode Check}
    Mode -- Quick --> Report[Report Generator]
    Mode -- Deep --> Analyze[Combined Analyzer]
    Analyze --> Synth[Business Synthesizer]
    Synth --> Report
    Report --> Save[Memory Saver]
    Save --> End([Final Report])
    
    %% Error Handling
    Intent -.-> Fallback[Fallback Node]
    Memory -.-> Fallback
    Retriever -.-> Fallback
    Analyze -.-> Fallback
    Fallback --> End
```

### AI Research Agent (LangGraph)

The core intelligence is orchestrated using LangGraph, which manages the stateful flow of a research task.

#### Agent Workflow (Deep Mode)
1.  **Intent Classifier**: Analyzes the user's query to determine the research objective and scope.
2.  **Clarification Check**: Identifies if more information is needed from the user before proceeding.
3.  **Memory Loader**: Fetches user preferences and historical context from previous sessions.
4.  **Data Retriever**: Performs RAG (Retrieval-Augmented Generation) against the Qdrant vector store to pull relevant product, pricing, and competitor data.
5.  **Combined Analyzer**: Executes a multi-pass analysis on the retrieved data, focusing on sentiment, pricing trends, and competitor benchmarking.
6.  **Business Synthesizer**: Aggregates analysis results into a high-level business strategy and executive summary.
7.  **Report Generator**: Constructs a structured JSON report with sections for findings, visualizations, and recommendations.
8.  **Memory Saver**: Persists the session's findings back to the vector store for future recall.

---

## 🛠️ Tech Stack

### Backend
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Asynchronous API layer)
- **Agent Orchestration**: [LangGraph](https://langchain-ai.github.io/langgraph/) & [LangChain](https://python.langchain.com/)
- **LLM**: [Google Gemini 2.0 Flash](https://aistudio.google.com/app/apikey)
- **Database**: [PostgreSQL](https://www.postgresql.org/) (via SQLAlchemy & asyncpg)
- **Vector Search**: [Qdrant](https://qdrant.tech/) (Vector memory and RAG)
- **Caching/Task Storage**: [Redis](https://redis.io/)
- **Embeddings**: `sentence-transformers` (Local execution for efficiency)

### Frontend
- **Framework**: [React](https://react.dev/) (Vite-based)
- **Language**: [TypeScript](https://www.typescriptlang.org/)
- **Styling**: [Tailwind CSS](https://tailwindcss.com/) & [Shadcn UI](https://ui.shadcn.com/)
- **State Management**: [Zustand](https://github.com/pmndrs/zustand)
- **Data Fetching**: [TanStack Query](https://tanstack.com/query/latest)
- **Charts**: [Recharts](https://recharts.org/)
- **Icons**: [Lucide React](https://lucide.dev/)

---

## 📂 Project Structure

```text
.
├── backend/                # API and AI Logic
│   ├── agent/             # LangGraph nodes, state, and graph definition
│   │   ├── nodes/         # Individual reasoning/analysis nodes
│   │   ├── graph.py       # Graph wiring and routing logic
│   │   └── state.py       # Shared state definition
│   ├── data/              # Data ingestion and Shopify sync logic
│   ├── db/                # SQLAlchemy models and migrations
│   ├── memory/            # Qdrant vector store integration
│   ├── routers/           # FastAPI routers (Upload, Research, Shopify, Memory)
│   ├── utils/             # Logging, prompt templates, and helpers
│   └── main.py            # FastAPI entry point
├── frontend/               # React TypeScript frontend
│   ├── src/
│   │   ├── components/    # UI components (Chat, Dashboard, Reports, Connect)
│   │   ├── hooks/         # Custom React hooks (API interaction)
│   │   ├── pages/         # Dashboard, History, and Connection pages
│   │   ├── store/         # Zustand state stores
│   │   └── lib/           # Utility functions and API clients
│   └── package.json
├── instructions/           # Deployment and setup guides
├── sample data/            # CSV files for testing (catalog, reviews, pricing)
└── docker-compose.yml      # Infrastructure (Postgres, Qdrant, Redis)
```

---

## ⚙️ Getting Started

The entire application is containerized for a one-command setup.

### Prerequisites
- Docker & Docker Compose

### One-Command Setup

1.  **Configure Environment**:
    ```bash
    cp .env.example .env
    # Fill in your API keys in the root .env
    ```

2.  **Start the System**:
    ```bash
    docker compose up --build
    ```
    - **Frontend**: http://localhost:5173
    - **Backend**: http://localhost:8000
    - **Infrastructure**: Postgres, Redis, Qdrant

---

## 📝 Environment Variables

The application uses a **single `.env` file** in the root directory.

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Gemini API Key | Required |
| `LLM_PROVIDER` | `gemini`, `groq`, or `openrouter` | `gemini` |
| `POSTGRES_URL` | Postgres URL | `postgresql+asyncpg://user:password@postgres:5432/ecomm_agent` |
| `QDRANT_URL` | Qdrant URL | `http://qdrant:6333` |
| `REDIS_URL` | Redis URL | `redis://redis:6379` |

---

## 🤝 Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

## 📄 License

This project is licensed under the MIT License.
