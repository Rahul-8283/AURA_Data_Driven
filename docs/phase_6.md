# Phase 6: Multi-Agent Orchestration (LangGraph Setup)

## 1. Objective and Scope
Phase 6 transitions the backend from standard API endpoints to an agentic workflow. We will initialize **LangGraph**, define the state object that tracks the research progress, and build the initial **Planner Agent** that parses user requests. This creates the skeleton for the Generative Evolution Loop.

---

## 2. State Definition (`app/agents/state.py`)

LangGraph operates on a shared state dictionary passed between nodes. We must define this strictly using Python `TypedDict`.

```python
from typing import TypedDict, List, Dict, Any

class ResearchState(TypedDict):
    task_id: str
    user_prompt: str
    target_properties: Dict[str, Any]  # e.g., {"capacity_gt": 250, "cost_lt": 50}
    base_material: str                 # e.g., "NMC"
    current_generation: int
    max_generations: int
    current_population: List[Dict]     # The active materials being mutated
    best_candidates: List[Dict]        # The hall-of-fame materials
    logs: List[str]                    # For frontend UI updates
```

---

## 3. The Planner Agent (`app/agents/nodes/planner.py`)

The first node in our graph is the Planner. It translates the user's messy natural language prompt into strict computational constraints.

### 3.1 LLM Parsing Logic
- Use OpenRouter (e.g., GPT-4o-mini) to parse the `user_prompt`.
- **System Prompt:** *"You are a battery material planner. Extract the target specific capacity, voltage, target base material class (cathode/anode), and any excluded elements from the user's request. Output ONLY strict JSON."*
- Update the `ResearchState` with the parsed `target_properties` and `base_material`.
- Initialize `current_generation = 0` and `max_generations = 20`.
- Initialize the `current_population` with 10 variations of the baseline material (e.g., standard NMC ratios).

---

## 4. Building the Graph Skeleton (`app/agents/workflow.py`)

We will define the structure of the graph using `StateGraph`. The actual logic for mutation and prediction will be built in later phases, but we must define the nodes and edges now.

### 4.1 Node Registration
```python
from langgraph.graph import StateGraph, END
from app.agents.state import ResearchState
from app.agents.nodes.planner import planner_node
# Import dummy functions for future nodes
from app.agents.nodes.mutator import mutator_node
from app.agents.nodes.predictor import predictor_node
from app.agents.nodes.reporter import reporter_node

workflow = StateGraph(ResearchState)

workflow.add_node("planner", planner_node)
workflow.add_node("mutator", mutator_node)
workflow.add_node("predictor", predictor_node)
workflow.add_node("reporter", reporter_node)
```

### 4.2 Edge Configuration (The Loop)
Define how state flows from one agent to the next, specifically creating the Genetic Algorithm loop.
- `planner` -> `mutator`
- `mutator` -> `predictor`
- **Conditional Edge from Predictor:**
  - If `current_generation < max_generations`: go back to `mutator`.
  - Else: go to `reporter`.
- `reporter` -> `END`

```python
workflow.set_entry_point("planner")
workflow.add_edge("planner", "mutator")
workflow.add_edge("mutator", "predictor")

def check_generation(state: ResearchState):
    if state["current_generation"] < state["max_generations"]:
        return "continue"
    return "end"

workflow.add_conditional_edges(
    "predictor",
    check_generation,
    {"continue": "mutator", "end": "reporter"}
)
workflow.add_edge("reporter", END)

app_graph = workflow.compile()
```

---

## 5. Execution and Verification Checklist
1. Write a local script to invoke the compiled `app_graph` with a dummy state.
2. Verify that the Planner Agent successfully parses a prompt like *"Find a cathode with 280 mAh/g capacity without using Cobalt."* into the `target_properties` dictionary.
3. Verify that the graph loops exactly `max_generations` times between mutator and predictor before exiting to reporter.
4. Visualize the graph structure using LangGraph's built-in `.get_graph().draw_ascii()` or export to image to ensure the loops are correct.
