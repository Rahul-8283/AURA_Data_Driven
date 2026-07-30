# Phase 8: Final Reporting & Frontend Visualization (Detailed Plan)

## 1. Objective and Scope
Phase 8 is the final phase of the AURA project. It focuses entirely on delivering actionable, visually stunning, and highly professional results to the researcher. We will build the LangGraph `reporter_node` to aggregate the findings and save them to Supabase. We will then build the React frontend views to render the results, charts, and the interactive Knowledge Graph.

---

## 2. The Reporter Node & Storage (`app/agents/nodes/reporter.py`)

This is the final node in the LangGraph workflow, executed only when `current_generation == max_generations` or if the loop is manually terminated.

### 2.1 Aggregation and LLM Summarization
- Take the absolute top 5 materials from the `best_candidates` array in the `ResearchState`.
- Pass these 5 candidates, along with the user's original prompt, to OpenRouter.
- **Prompt:** *"You are writing the executive summary for a battery material discovery report. Review the user's initial request and the top 5 materials the AI discovered. Write a highly professional, 3-paragraph summary explaining the evolutionary path taken, why these specific materials outcompete standard baselines, and what their primary trade-offs are based on their predicted properties."*
- Store this summary in the `ResearchState`.

### 2.2 Supabase Database Storage
- Import the initialized Supabase client.
- Insert the final JSON payload (Top 5 materials, properties, LLM reasoning, and executive summary) into the `ResearchTasks` table in PostgreSQL.
- Update the specific row's status to `completed`.
- Insert individual material records into a `SavedMaterials` table with a foreign key linking back to the user and the task, so the user can easily reference them later in their dashboard history.

---

## 3. Frontend Results Dashboard (`src/pages/Results/`)

Once the frontend finishes polling the backend and sees `status: 'completed'`, it immediately redirects the user to the `Results` view using React Router.

### 3.1 Material Cards & Recharts Integration
- Build highly polished, glassmorphic interactive cards displaying the exact stoichiometry of the Top 5 materials.
- Implement **Recharts** to visualize the data:
  - **Radar Chart:** Compare the predicted Capacity, Voltage, Cycle Life, and Cost against a standard baseline (like NMC811). This allows the researcher to visually see the trade-offs at a glance.
  - **Evolution Line Chart:** Plot the `best_score` and `average_score` of the population across all 20 generations. This chart serves as mathematical proof that the Genetic Algorithm actually worked and evolved better materials over time.

### 3.2 Interactive Graph Visualization (`react-force-graph-2d`)
Give the researcher a visual representation of the chemistry rules that validated the top material. This builds immense trust in the AI's predictions.
- **Backend API:** Create a new `GET /api/v1/graph/material/{material_name}` endpoint. This queries Neo4j for the material, its constituent elements, and its properties, returning a standard `{ nodes: [], links: [] }` JSON object.
- **Frontend Component:** Implement the `ForceGraph2D` component to render this data. 
  - Color code the nodes (e.g., Red for Degradation Modes, Green for Positive Properties, Blue for Elements, Gold for the Material itself).
  - Enable node dragging, zooming, and hover tooltips so the user can interactively explore why the material behaves the way it does.

---

## 4. UI Polish & PDF Export

### 4.1 Framer Motion Animations & Lenis
- Wrap the rendering of the Material Cards and Charts in a `framer-motion` stagger effect so they smoothly fade in one by one as the user scrolls down the page.
- Ensure `lenis` smooth scrolling is fully active on the report page to maintain the ultra-premium feel established in Phase 0.

### 4.2 PDF Export Functionality
Researchers need to share these findings with their labs.
- Add a highly visible "Download Full Report" button.
- Use a library like `jspdf` and `html2canvas` (or `react-to-print`) to convert the rendered React view—including the rendered charts and the executive summary—into a perfectly formatted, downloadable PDF.

---

## 5. Final Execution and Verification Checklist

1. **End-to-End Test:** Run a complete end-to-end task from the UI Dashboard. Submit a prompt, wait for the loading screen (polling), and wait for the redirect.
2. **Database Verification:** Verify that upon completion, the Supabase PostgreSQL tables (`ResearchTasks` and `SavedMaterials`) successfully contain the final JSON report and that the user's dashboard history updates.
3. **Rendering Verification:** Ensure the React UI correctly fetches the completed data and renders the Radar charts without crashing due to undefined data.
4. **Graph Verification:** Verify that the Force Graph component correctly queries Neo4j, receives the JSON, and dynamically renders the chemical relationships on screen without overlapping nodes completely.
5. **PDF Verification:** Click the Download PDF button. Verify that the layout integrity is maintained in the downloaded file and the charts are visible (not blank squares).

**AURA Implementation Complete!**
