from datetime import datetime
from app.agents.state import ResearchState

def dummy_mutator_node(state: ResearchState) -> ResearchState:
    """
    Dummy Mutator Node:
    Simulates the mutation step of the Genetic Algorithm.
    Increments the generation counter.
    """
    state["current_generation"] += 1
    state["logs"].append(
        f"[{datetime.utcnow().isoformat()}] Mutator: Generated population for generation {state['current_generation']}."
    )
    return state

def dummy_predictor_node(state: ResearchState) -> ResearchState:
    """
    Dummy Predictor Node:
    Simulates the fitness prediction step using the ML models and GraphRAG.
    """
    state["logs"].append(
        f"[{datetime.utcnow().isoformat()}] Predictor: Evaluated fitness for generation {state['current_generation']}."
    )
    return state

def dummy_reporter_node(state: ResearchState) -> ResearchState:
    """
    Dummy Reporter Node:
    Simulates the final aggregation of results after the GA loop finishes.
    """
    state["logs"].append(
        f"[{datetime.utcnow().isoformat()}] Reporter: Evolution complete. Summarizing best candidates."
    )
    
    # Just to have something in best_candidates
    base_class = state.get("base_material_class") or "Material"
    state["best_candidates"] = [
        {"id": "winner_1", "composition": f"Optimal_{base_class}", "fitness": 0.99}
    ]
    return state
