# Product Requirements Document (PRD)
**Product Name:** AURA (Autonomous Unified Research Assistant for Battery Materials Discovery)  
**Version:** 1.0  
**Status:** In Development  

---

## 1. Executive Summary
### 1.1 Objective
AURA is an AI-powered, domain-specific research assistant designed to accelerate the discovery of novel **Battery Materials**. It shifts the paradigm of battery research from manual, trial-and-error synthesis to computational, AI-driven evolution.

### 1.2 Target Audience
- **Material Scientists & Chemists:** Researchers looking for promising new battery compositions before committing to expensive lab synthesis.
- **Battery Manufacturers:** R&D departments seeking to optimize existing cathodes, anodes, or electrolytes for cost, capacity, or safety.

### 1.3 Problem Statement
Traditional battery material discovery is a slow, expensive process. Researchers spend months reading literature, synthesizing variants, and running cycle tests. Existing AI assistants lack domain-specific chemistry rules, often suggesting physically impossible or highly unstable materials.

### 1.4 Solution
AURA automates the initial computational phase of discovery by taking a user's natural language requirements and using a **multi-agent system** to computationally evolve known battery materials. It utilizes a Genetic Algorithm (GA) for mutations, GraphRAG for chemical validation against existing literature, and LLMs to predict the electrochemical properties of the mutated candidates.

---

## 2. Core Features & Functionality

### 2.1 Natural Language Requirement Input
- Users can input specific, plain-text requirements (e.g., *"I need a cathode with >300 mAh/g capacity, low cost, and stable at 60°C"*).
- The system parses these requirements to define the fitness function for the Genetic Algorithm.

### 2.2 Battery-Specific Knowledge Graph & GraphRAG
- The system automatically extracts data from battery research papers and databases.
- Builds a Knowledge Graph (nodes: Elements, Materials, Degradation Modes; edges: `contains`, `prevented_by`).
- GraphRAG is used to validate chemical queries rather than generic similarity searches (e.g., *"Is substituting Ni with Mg stable in an NMC cathode?"*).

### 2.3 Smart Genetic Algorithm (GA) Mutations
- Evolves battery compositions intelligently based on chemistry rules, not random chance.
- **Operations:** Element substitution, doping, and ratio adjustments.
- **Validation:** Every mutation is instantly checked against the GraphRAG to ensure structural stability and realistic synthesis before passing to the next generation.

### 2.4 LLM-Based Property Prediction
- Replaces black-box ML models with highly interpretable LLM reasoning.
- Inputs the mutated composition alongside GraphRAG context.
- Outputs estimated Specific Capacity (mAh/g), Voltage (V), Cycle Life, Cost ($/kg), and a detailed explanation of the underlying chemical reasoning.

### 2.5 Final Material Recommendation Report
- Ranks materials based on a calculated fitness score (e.g., `(Capacity × Cycle Life) / Cost`).
- Generates a comprehensive report detailing the top candidates, providing literature-backed evidence, and explaining why they are worth synthesizing in the lab.

---

## 3. User Flow

1. **Authentication:** User logs in securely via Supabase.
2. **Task Definition:** User defines the battery component (Cathode, Anode, Solid-State Electrolyte) and their desired target properties via the React dashboard.
3. **Execution Initiation:** The user submits the request. The UI displays a "Task Started" notification and provides a live progress tracker.
4. **Asynchronous Processing:** Behind the scenes, Celery orchestrates the LangGraph agents. The system fetches papers, builds the GraphRAG, runs 20+ generations of the GA, and predicts properties via OpenRouter.
5. **Results Review:** User receives a notification that the report is ready. They view the generated graphs (via Recharts), the visual knowledge graph map, and the final ranked candidate list.
6. **Data Retention:** The user can save their favorite material configurations to their Supabase profile for future reference.

---

## 4. Success Metrics
- **Time-to-Candidate:** The system should generate a viable, ranked list of materials in under 30 minutes.
- **Chemical Validity:** >90% of the top recommended materials must be chemically valid and structurally stable according to established battery physics.
- **User Adoption:** Measured by the number of successful research tasks run through the platform.
