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

def init_research_state(task_id: str, user_prompt: str, user_id: str = "default_user") -> ResearchState:
    """Helper function to initialize the state object."""
    return {
        "task_id": task_id,
        "user_id": user_id,
        "user_prompt": user_prompt,
        "start_time": datetime.utcnow(),
        "target_properties": {},
        "base_material_class": "",
        "excluded_elements": [],
        "current_generation": 0,
        "max_generations": 0,
        "current_population": [],
        "best_candidates": [],
        "logs": [f"[{datetime.utcnow().isoformat()}] Initialization complete. Task {task_id} started."]
    }
