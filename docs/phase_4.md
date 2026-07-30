# Phase 4: Multi-Agent Orchestration (LangGraph Setup)

## 1. Objective and Scope
Phase 4 marks the critical transition of the backend from a standard request/response REST API to a persistent, stateful agentic workflow. We will initialize **LangGraph**, define the immutable state object that tracks the entire evolutionary research progress, and build the initial **Planner Agent**. This sets up the rigid execution skeleton that will house the Genetic Algorithm loop in later phases.

---

## 2. State Definition & Management (`app/agents/state.py`)

LangGraph operates by passing a shared state object sequentially through nodes (agents). Because we are dealing with complex scientific data across multiple generations, we must define this state strictly using Python's `TypedDict` to prevent runtime errors and ensure schema validation.

### 2.1 The ResearchState Schema
Create a robust state definition that captures every aspect of a discovery run.
```python
from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime

class ResearchState(TypedDict):
    # Metadata
    task_id: str
    user_id: str
    user_prompt: str
    start_time: datetime
    
    # Planner Constraints (Populated by Planner Node)
    target_properties: Dict[str, Any]  # e.g., {"capacity_gt": 250, "cost_lt": 50, "voltage_gt": 3.7}
    base_material_class: str           # e.g., "NMC_Cathode"
    excluded_elements: List[str]       # e.g., ["Co"] to force cobalt-free
    
    # Genetic Algorithm Loop Variables
    current_generation: int
    max_generations: int
    current_population: List[Dict[str, Any]]  # The active 20 materials being mutated
    
    # Hall of Fame
    best_candidates: List[Dict[str, Any]]     # The top 5 materials found across all runs
    
    # Frontend Communication
    logs: List[str]                           # String logs meant to be flushed to Redis for UI
```
- Implement helper functions to initialize this state with default empty values based on a `task_id`.

---

## 3. The Planner Agent (`app/agents/nodes/planner.py`)

The first node in our directed graph is the Planner. Its job is purely translation: converting the user's messy natural language prompt into the strict computational constraints defined in the `ResearchState`.

### 3.1 LLM Parsing Logic
- Use OpenRouter (with a highly capable reasoning model like GPT-4o or Claude 3.5 Sonnet) to parse the `user_prompt`.
- **System Prompt Design:** *"You are the chief planning agent for an autonomous battery material discovery system. The user will provide a high-level goal. You must extract the exact numerical targets for specific capacity, voltage, cycle life, and cost. You must also identify the base material class (Cathode, Anode, Solid-State Electrolyte) and any explicitly excluded elements (e.g., 'cobalt-free' means exclude Co). Output ONLY a strict JSON payload adhering to the provided schema."*
- Provide the JSON schema in the API call using structured output enforcement.

### 3.2 State Initialization
- Upon receiving the JSON from the LLM, the Planner updates the `target_properties`, `base_material_class`, and `excluded_elements`.
- The Planner statically sets `current_generation = 0` and `max_generations = 20`.
- The Planner initializes the `current_population` with 10 variations of standard baseline materials (e.g., standard NMC111, NMC532, NMC811) to seed the Genetic Algorithm.

---

## 4. Building the Graph Skeleton (`app/agents/workflow.py`)

We will define the structure of the graph using LangGraph's `StateGraph`. The actual deep logic for mutation and prediction will be built in Phases 5 and 6, but we must define the nodes, edges, and routing logic now using dummy functions.

### 4.1 Node Registration
```python
from langgraph.graph import StateGraph, END
from app.agents.state import ResearchState
from app.agents.nodes.planner import planner_node

# Import dummy functions for future nodes that just return the state unchanged for now
from app.agents.nodes.mutator import dummy_mutator_node
from app.agents.nodes.predictor import dummy_predictor_node
from app.agents.nodes.reporter import dummy_reporter_node

workflow = StateGraph(ResearchState)

workflow.add_node("planner", planner_node)
workflow.add_node("mutator", dummy_mutator_node)
workflow.add_node("predictor", dummy_predictor_node)
workflow.add_node("reporter", dummy_reporter_node)
```

### 4.2 Edge Configuration (The Evolutionary Loop)
Define how state flows from one agent to the next, specifically creating the recursive loop required for the Genetic Algorithm.
- **Linear entry:** `START` -> `planner` -> `mutator`
- **Internal loop:** `mutator` -> `predictor`
- **Conditional Routing from Predictor:**
  - Write a `check_generation(state)` function.
  - If `state["current_generation"] < state["max_generations"]`: route back to `mutator`.
  - Else: route to `reporter`.
- **Exit:** `reporter` -> `END`

```python
workflow.set_entry_point("planner")
workflow.add_edge("planner", "mutator")
workflow.add_edge("mutator", "predictor")

def check_generation(state: ResearchState) -> str:
    # Increment logic will live in mutator, we just check here
    if state["current_generation"] < state["max_generations"]:
        return "continue_evolution"
    return "generate_report"

workflow.add_conditional_edges(
    "predictor",
    check_generation,
    {
        "continue_evolution": "mutator", 
        "generate_report": "reporter"
    }
)
workflow.add_edge("reporter", END)

# Compile the graph into an executable app
app_graph = workflow.compile()
```

---

## 5. Execution and Verification Checklist

To sign off on Phase 4, you must verify the stateful orchestration logic:
1. **Dummy Nodes:** Ensure `mutator`, `predictor`, and `reporter` are implemented as simple functions that increment `current_generation` and append a trace message to `logs` so the loop actually ends.
2. **Planner Parsing:** Write a local script to invoke `app_graph.invoke({"user_prompt": "Find a cathode with 280 mAh/g capacity without using Cobalt."})`.
3. **State Verification:** Inspect the final returned state. Verify that the Planner Agent successfully parsed the target capacity into `target_properties` and added `"Co"` to `excluded_elements`.
4. **Loop Verification:** Verify that the `logs` array contains exactly `max_generations` entries proving that the graph looped between mutator and predictor exactly 20 times before hitting the reporter node.
5. **Visual Verification:** Use LangGraph's `.get_graph().draw_ascii()` or export the graph to a PNG image. Visually inspect the generated flowchart to ensure the conditional back-edge from predictor to mutator is correctly wired.
