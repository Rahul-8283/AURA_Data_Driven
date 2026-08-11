<h1 align="center">AURA: Autonomous Unified Research Assistant for Battery Materials Discovery</h1>

## Overview
AURA is an AI-powered, domain-specific research assistant designed to accelerate the discovery of new **Battery Materials**. Instead of a generic research assistant, AURA focuses on evolving and optimizing battery components (cathodes, anodes, electrolytes, SEI). It utilizes a multi-agent system powered by **GraphRAG**, **Genetic Algorithms (GA)**, and **LLM-based Property Prediction** to intelligently mutate known battery compositions, validate their feasibility, and predict their electrochemical properties before physical synthesis. 

## Technology Stack
<p align="center">
  <img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React" />
  <img src="https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white" alt="TailwindCSS" />
  <img src="https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/LangGraph-FF4F00?style=for-the-badge&logo=langchain&logoColor=white" alt="LangGraph" />
  <img src="https://img.shields.io/badge/OpenRouter-000000?style=for-the-badge&logo=openai&logoColor=white" alt="OpenRouter" />
  <img src="https://img.shields.io/badge/ChromaDB-FF6F00?style=for-the-badge&logo=chroma&logoColor=white" alt="ChromaDB" />
  <img src="https://img.shields.io/badge/Neo4j-018bff?style=for-the-badge&logo=neo4j&logoColor=white" alt="Neo4j" />
  <img src="https://img.shields.io/badge/Hugging_Face-FFD21E?style=for-the-badge&logo=huggingface&logoColor=000" alt="Hugging Face" />
  <img src="https://img.shields.io/badge/all--MiniLM--L6--v2-4B4B4B?style=for-the-badge" alt="all-MiniLM-L6-v2" />
  <img src="https://img.shields.io/badge/Celery-37814A?style=for-the-badge&logo=celery&logoColor=white" alt="Celery" />
  <img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white" alt="Redis" />
  <img src="https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white" alt="Supabase" />
  <img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
</p>

## Detailed Architecture Flow

```mermaid
graph TD
    User(["👤 User Input / Battery Requirements"])
    Planner["🧠 Planner Agent"]
    
    subgraph Battery Knowledge Graph Construction
        Papers["📄 Battery Literature Extraction"]
        Datasets["📊 Battery Databases (e.g. Materials Project)"]
    end

    DocProc["📝 Document Processing Module"]
    Embeddings["🔢 Embedding Generation (Hugging Face / all-MiniLM)"]
    
    Chroma[("🗄️ Vector Database (ChromaDB)")]
    KG["🕸️ Battery Knowledge Graph Builder"]
    Neo4j[("🗃️ Knowledge Graph (Neo4j)")]
    
    GraphRAG["⚙️ GraphRAG Engine"]
    
    subgraph Generative Evolution
        GA["🧬 Genetic Algorithm (Mutations, Doping)"]
        Validation["🔍 GraphRAG Chemistry Validation"]
        LLM["🧠 LLM Property Prediction (Capacity, Cost, Cycles)"]
    end
    
    ReportAgent["📝 Material Recommendation Agent"]
    FinalReport(["📑 Top Synthesizable Materials"])

    %% Connections
    User --> Planner
    Planner --> Papers
    Planner --> Datasets
    
    Papers --> DocProc
    Datasets --> DocProc
    
    DocProc --> Embeddings
    DocProc --> KG
    
    Embeddings --> Chroma
    KG --> Neo4j
    
    Chroma --> GraphRAG
    Neo4j --> GraphRAG
    
    Planner --> GA
    GA --> Validation
    Validation --> GraphRAG
    GraphRAG --> Validation
    Validation --> LLM
    LLM --> GraphRAG
    GraphRAG --> LLM
    
    LLM --> ReportAgent
    ReportAgent --> FinalReport
```

## Core Features & Logic Flow

### 1. Battery-Specific Knowledge Graph
AURA builds a comprehensive Knowledge Graph consisting of elements, battery materials (LCO, NMC, LFP), roles (Cathode, Anode, Electrolyte), degradation modes, and doping strategies.
* **Nodes:** Elements, Materials, Properties, Degradation Modes.
* **Edges:** `contains`, `can_be_doped_with`, `suffers_from`, `prevented_by`.

### 2. Battery-Specific GraphRAG Queries
Rather than generic similarity searches, AURA asks specific electrochemical questions:
* *Find cathode alternatives to LiCoO₂.*
* *What dopants improve cycling stability in Ni-rich cathodes?*
* *If I substitute Ni with Co, what happens to voltage and safety?*

### 3. Smart Genetic Algorithm (GA) Mutations
AURA uses GA to intelligently evolve battery compositions. Instead of random mutations, it applies chemistry-based rules and validates them instantly against the GraphRAG:
* **Element Substitution:** (e.g., replace Co with Ni).
* **Doping:** (e.g., add 10% Mg doping).
* **Validation:** Before accepting a mutation, GraphRAG checks if the structure remains stable, if the synthesis is realistic, and what the cost impact is.

### 4. LLM-Based Property Prediction
Instead of training a black-box ML model, AURA uses large language models (LLMs) equipped with GraphRAG context for highly interpretable property prediction.
* **Input:** New mutated composition (e.g., `LiNi₀.₇Co₀.₂Al₀.₁O₂`) + GraphRAG Context (similar materials, dopant effects).
* **Output:** Estimated specific capacity (mAh/g), voltage (V), cycle life, thermal stability, cost ($/kg), and **explainable reasoning** for the prediction.

### 5. Final Material Recommendation
After running multiple GA generations, materials are ranked by a fitness score (e.g., `Capacity × Cycles / Cost`). The system outputs a final structured report recommending the top novel materials that are actually worth synthesizing in the lab, complete with literature-backed evidence for their viability.

## Detailed Technology Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Frontend** | React, TailwindCSS | Provides a responsive, fast, and modern user interface for researchers to input requirements and view candidates. |
| **Backend API** | FastAPI | High-performance Python framework serving the core API and handling asynchronous multi-agent tasks. |
| **Auth & Storage** | Supabase | Provides robust user authentication, file storage (buckets), and PostgreSQL for relational user data. |
| **Task Queue** | Celery | Manages and distributes long-running Genetic Algorithm and LLM prediction tasks asynchronously. |
| **Message Broker** | Redis | In-memory data store acting as the message broker for Celery and caching intermediate GraphRAG results. |
| **Orchestration** | LangGraph | Manages the multi-agent workflows, state transitions, and the Genetic Algorithm (GA) execution loops. |
| **LLM Engine** | OpenRouter | Routes requests to top-tier LLMs (e.g., Claude, GPT) for deep chemical reasoning and property prediction. |
| **Knowledge Graph** | Neo4j | Graph database storing battery elements, materials, properties, and their complex electrochemical relationships. |
| **Vector Database** | ChromaDB (Persistent Storage) | Lightweight, high-performance vector database configured for local persistent storage to ensure research data is never lost between restarts. |
| **Embeddings** | Hugging Face (`all-MiniLM`) | Generates semantic embeddings for battery research papers to power the GraphRAG retrieval engine. |

## Installation and Setup

### 1. Backend (FastAPI, Celery, Redis)

Ensure you have Python 3.11+ installed.

1. **Navigate to the backend directory and set up a virtual environment:**
   ```bash
   cd backend
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On Mac/Linux:
   source venv/bin/activate
   ```
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Set up Redis:**
   Ensure Docker is installed, then start the Redis container:
   ```bash
   docker-compose up -d
   ```
4. **Environment Variables:**
   Ensure you have a `.env` file in the `backend/` directory with `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `NEO4J_URI`, etc.
5. **Run the FastAPI server:**
   ```bash
   uvicorn main:app --reload
   ```
6. **Run the Celery worker** (in a separate terminal, with venv activated):
   ```bash
   # On Windows
   celery -A app.core.celery_app worker --loglevel=info --pool=solo
   # On Mac/Linux
   celery -A app.core.celery_app worker --loglevel=info
   ```

### 2. Frontend (React + Vite)

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```
2. **Install dependencies:**
   ```bash
   npm install
   ```
3. **Environment Variables:**
   Ensure you have a `.env` file with `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`.
4. **Run the development server:**
   ```bash
   npm run dev
   ```

### 3. Databases
- **ChromaDB:** Runs locally via the persistent client. Data is stored in `backend/chroma_data/` (this directory is ignored in git so you don't commit SQLite binaries). You don't need to manually push SQLite data to the repository.
- **Supabase:** Used for Auth and relational data. You must configure Auth and create necessary tables in your Supabase dashboard.
- **Neo4j:** Uses a remote AuraDB instance configured via the `.env` file.