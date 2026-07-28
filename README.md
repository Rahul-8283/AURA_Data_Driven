# AURA: Autonomous Unified Research Assistant for Scientific Discovery using Multi-Agent AI and GraphRAG

## 📖 Overview
AURA is an AI-powered research assistant designed to automate the initial stages of scientific research. Instead of manually searching through papers, datasets, and patents, users simply provide a research topic. AURA utilizes multiple collaborative AI agents to collect, organize, analyze, and summarize research information. By building a Knowledge Graph and using a **ChromaDB** vector database, AURA employs GraphRAG for relationship-aware reasoning across multiple research sources. Ultimately, the system generates a structured research report containing a literature review, related work, identified research gaps, and references.

## 🛠️ Technology Stack
<p align="center">
  <img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React" />
  <img src="https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white" alt="TailwindCSS" />
  <img src="https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/LangGraph-FF4F00?style=for-the-badge&logo=langchain&logoColor=white" alt="LangGraph" />
  <img src="https://img.shields.io/badge/OpenRouter-000000?style=for-the-badge&logo=openai&logoColor=white" alt="OpenRouter" />
  <img src="https://img.shields.io/badge/ChromaDB-FF6F00?style=for-the-badge&logo=chroma&logoColor=white" alt="ChromaDB" />
  <img src="https://img.shields.io/badge/Neo4j-018bff?style=for-the-badge&logo=neo4j&logoColor=white" alt="Neo4j" />
  <img src="https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white" alt="PyTorch" />
</p>

## ⚙️ Detailed Architecture Flow

```mermaid
graph TD
    %% Styling
    classDef userStyle fill:#f9f9f9,stroke:#333,stroke-width:2px;
    classDef agentStyle fill:#d4edda,stroke:#28a745,stroke-width:2px;
    classDef processStyle fill:#cce5ff,stroke:#007bff,stroke-width:2px;
    classDef dbStyle fill:#fff3cd,stroke:#ffc107,stroke-width:2px;
    classDef reportStyle fill:#f8d7da,stroke:#dc3545,stroke-width:2px;

    User([👤 User Input / Research Topic]) ::: userStyle
    Planner[🧠 Planner Agent] ::: agentStyle
    
    subgraph Information Retrieval
        Papers[📄 Literature Retrieval Agent] ::: agentStyle
        Datasets[📊 Dataset Discovery Agent] ::: agentStyle
        Patents[📜 Patent Retrieval Agent] ::: agentStyle
    end

    DocProc[📝 Document Processing Module] ::: processStyle
    Embeddings[🔢 Embedding Generation <br> (Sentence Transformers)] ::: processStyle
    
    Chroma[(🗄️ Vector Database <br> ChromaDB)] ::: dbStyle
    KG[🕸️ Knowledge Graph Builder] ::: processStyle
    Neo4j[(🗃️ Knowledge Graph <br> Neo4j)] ::: dbStyle
    
    GraphRAG[⚙️ GraphRAG Engine] ::: processStyle
    Evidence[🔍 Evidence Verification Agent] ::: agentStyle
    GapAgent[💡 Research Gap Agent] ::: agentStyle
    ReportAgent[📝 Report Generation Agent] ::: agentStyle
    FinalReport([📑 Final Research Report]) ::: reportStyle

    %% Connections
    User --> Planner
    Planner --> Papers
    Planner --> Datasets
    Planner --> Patents
    
    Papers --> DocProc
    Datasets --> DocProc
    Patents --> DocProc
    
    DocProc --> Embeddings
    DocProc --> KG
    
    Embeddings --> Chroma
    KG --> Neo4j
    
    Chroma --> GraphRAG
    Neo4j --> GraphRAG
    
    GraphRAG --> Evidence
    Evidence --> GapAgent
    GapAgent --> ReportAgent
    ReportAgent --> FinalReport
```

## ✨ Features

* **Automated Literature Review:** Automatically fetches relevant research papers from OpenAlex, Semantic Scholar, arXiv, and CrossRef.
* **Dataset Discovery:** Finds relevant datasets from Kaggle, HuggingFace, GitHub, and PapersWithCode.
* **Patent Retrieval:** Explores commercial solutions and innovations via Google Patents and USPTO.
* **Intelligent Document Processing:** Downloads PDFs, extracts and cleans text, chunks data, and extracts metadata.
* **Knowledge Graph Construction:** Automatically maps out authors, methods, algorithms, datasets, and applications using Neo4j.
* **Advanced GraphRAG Reasoning:** Performs multi-hop reasoning over connected knowledge (using **ChromaDB** and Neo4j) rather than simple keyword retrieval.
* **Research Gap Detection:** Analyzes missing relationships, limitations, and future work to identify research opportunities.
* **Comprehensive Report Generation:** Outputs a structured report containing the literature review, related work, evidence-backed insights, research gaps, and references.