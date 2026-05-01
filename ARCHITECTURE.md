# 🏗️ Technical Architecture Overview

This document provides a deep dive into the technical inner workings of the **E-Commerce Intelligence Research Agent**.

---

## 🧩 System Architecture

The project follows a modern, decoupled architecture consisting of a React-based frontend, a FastAPI backend, and a suite of specialized data stores for structured and unstructured data.

### High-Level Flow
1.  **Ingestion**: Data enters via Shopify API or CSV uploads.
2.  **Processing**: Records are structured in PostgreSQL; text is chunked, embedded, and indexed in Qdrant.
3.  **Reasoning**: LangGraph orchestrates a multi-step Agentic workflow using Gemini 2.0 Flash.
4.  **Presentation**: A rich dashboard visualizes findings and provides a chat-based research interface.

---

## 🤖 AI Agentic Layer (LangGraph)

The core "brain" of the application is built using **LangGraph**, which manages the stateful reasoning process.

### Shared State (`AgentState`)
All nodes in the graph share a persistent state that includes:
-   **Context**: Session ID, User preferences, and conversation history.
-   **Retrieved Data**: Text chunks from product catalogs, reviews, pricing, and orders.
-   **Intermediate Results**: Sentiment analysis, competitor benchmarks, and pricing trends.
-   **Final Output**: Structured JSON report and executive summaries.

### Research Modes
-   **Quick Mode**: Focused on speed. Performs intent classification, retrieval, and immediate report generation.
-   **Deep Mode**: Performs multi-pass analysis. Includes detailed "Combined Analysis" and "Business Synthesis" before generating the final report.

### Key Nodes
-   **Intent Classifier**: Uses Gemini to determine if the query is a search, analysis, or clarification request.
-   **Data Retriever**: Performs RAG (Retrieval-Augmented Generation) against the Qdrant vector store.
-   **Combined Analyzer**: Executes domain-specific logic (sentiment, pricing, SWOT) in a single pass.
-   **Business Synthesizer**: Aggregates technical findings into "CEO-level" insights.

---

## 🗄️ Data Engineering & Persistence

### 1. Vector Memory (RAG)
-   **Store**: Qdrant (Vector Database).
-   **Embeddings**: Local `sentence-transformers` for processing text chunks. The Docker build is optimized for **CPU-only** execution, making it lightweight for Apple Silicon (Mac) and standard servers.
-   **Usage**: Stores product catalogs, customer reviews, and competitor data to provide context for LLM generation, reducing hallucinations.

### 2. Relational Storage
-   **Store**: PostgreSQL.
-   **ORM**: SQLAlchemy (async).
-   **Key Tables**:
    -   `sessions`: Stores historical research tasks and reports.
    -   `shopify_connections`: Manages API credentials and sync status for stores.
    -   `token_logs`: Tracks LLM usage and costs at a granular node level.
    -   `uploads`: Tracks manual data ingestion history.

### 3. Data Sync (Shopify Integration)
-   **Mechanism**: OAuth-based connection to Shopify stores.
-   **Sync logic**: Fetches Products, Orders, and Customers via GraphQL/REST, processes them through the embedding pipeline, and stores them in both Postgres and Qdrant.

---

## 💻 Frontend Architecture

-   **Framework**: React (Vite) with TypeScript for type safety.
-   **State Management**: 
    -   **Zustand**: Lightweight stores for user authentication (`useUserStore`) and research sessions (`useSessionStore`).
    -   **TanStack Query**: Manages server-state, caching, and background data fetching.
-   **UI & Component Library**:
    -   **Tailwind CSS**: Utility-first styling with a custom "Glassmorphic" theme.
    -   **Shadcn UI**: High-quality, accessible UI components.
    -   **Recharts**: Interactive data visualization for e-commerce metrics.

---

## 🛠️ Infrastructure & Deployment

The entire stack is containerized using **Docker** for consistent local development and production deployment.

-   **Backend**: Python 3.10+ (FastAPI).
-   **Database**: PostgreSQL 15.
-   **Caching/Task Queue**: Redis.
-   **Vector DB**: Qdrant.
-   **Web Server**: Nginx (in production) or Vite dev server (locally).

---

## 🛡️ Security & Performance
-   **LLM Choice**: Gemini 2.0 Flash provides a massive 1M+ token window, allowing the agent to "see" large portions of a product catalog simultaneously.
-   **Streaming**: Backend supports streaming responses for a real-time chat experience.
-   **API Design**: Modular FastAPI routers ensure separation of concerns between upload, research, and Shopify logic.
