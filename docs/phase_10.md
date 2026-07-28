# Phase 10: Final Reporting & Frontend Visualization (Detailed Plan)

## 1. Objective and Scope
Phase 10 is the final step, focusing on delivering actionable, visually stunning results to the researcher. We will build the LangGraph Reporter node to aggregate the findings, save them to Supabase, and build the React frontend views to render the results, charts, and the interactive Knowledge Graph.

---

## 2. The Reporter Node & Storage (`app/agents/nodes/reporter.py`)

This is the final node in the LangGraph workflow (`reporter_node`), executed when `current_generation == max_generations`.

### 2.1 Aggregation and Summarization
- Take the top 5 materials from the `best_candidates` array in the `ResearchState`.
- Pass these candidates to OpenRouter with a prompt to generate a highly professional "Executive Summary" explaining the evolutionary path taken to discover them and why they outcompete the baseline material.

### 2.2 Supabase Database Storage
- Import the Supabase client.
- Insert the final JSON payload (Top 5 materials, properties, reasoning, and summary) into the `ResearchTasks` table in PostgreSQL, updating the task status to `completed`.
- Insert individual material records into the `SavedMaterials` table so the user can easily reference them later.

---

## 3. Frontend Results Dashboard (`src/pages/Results/`)

Once the frontend finishes polling and sees `status: 'completed'`, it redirects to the Results view.

### 3.1 Material Cards & Recharts
- Build interactive cards displaying the composition of the Top 5 materials.
- Implement **Recharts**:
  - **Radar Chart:** Compare Capacity, Voltage, Cycle Life, and Cost against a standard baseline (like NMC811) visually.
  - **Evolution Line Chart:** Show how the average fitness score of the population improved across generations, proving the GA worked.

### 3.2 Graph Visualization (`react-force-graph-2d`)
Give the researcher a visual representation of the chemistry rules that validated the top material.
- **Backend API:** Create `GET /api/v1/graph/material/{material_name}` which queries Neo4j for the material, its constituent elements, and its properties, returning a standard `{ nodes: [], links: [] }` JSON object.
- **Frontend Component:** Implement the `ForceGraph2D` component to render this data. Color code the nodes (e.g., Red for Degradation Modes, Green for Positive Properties, Blue for Elements). Allow the user to zoom and drag nodes.

---

## 4. UI Polish & Export

### 4.1 Framer Motion Animations
- Wrap the rendering of the Material Cards in a `framer-motion` stagger effect so they smoothly fade in one by one.
- Use `lenis` for smooth scrolling throughout the long report page.

### 4.2 PDF Export Functionality
- Add a "Download Report" button.
- Use a library like `jspdf` or `html2pdf.js` to convert the rendered React view (including the charts) into a downloadable PDF that the researcher can share with their team.

---

## 5. Final Execution and Verification Checklist
1. Run a complete end-to-end task from the UI.
2. Verify that upon completion, the database (`Supabase`) successfully contains the final JSON report.
3. Ensure the React UI correctly fetches the completed data and renders the Radar charts without errors.
4. Verify that the Force Graph component correctly queries Neo4j and dynamically renders the chemical relationships on screen.
5. Download the PDF report and verify layout integrity.

**Project Implementation Complete!**
