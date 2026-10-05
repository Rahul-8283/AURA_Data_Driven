import asyncio
from datetime import datetime, timezone
from typing import Dict, Any

from app.agents.state import ResearchState
from app.services.retrieval.graph_rag import GraphRAGService
from app.services.llm.client import predict_properties_async
from app.services.ga.fitness import calculate_fitness

async def predictor_node(state: ResearchState) -> ResearchState:
    """
    Phase 6: Predictor Node Logic
    Runs property prediction on the mutated materials concurrently using the LLM and GraphRAG.
    """
    current_pop = state.get("current_population", [])
    if not current_pop:
        state.setdefault("logs", []).append(f"[{datetime.now(timezone.utc).isoformat()}] Predictor: Population empty. Aborting.")
        return state

    async def process_material(mat: Dict[str, Any]) -> Dict[str, Any]:
        composition = mat.get("composition")
        
        # 1. Fetch Context Concurrently via GraphRAG
        query = f"What are the electrochemical properties and degradation modes of {composition}?"
        try:
            context = await GraphRAGService.retrieve_context(query)
            
            # 2. Run LLM Predictions Concurrently
            prediction = await predict_properties_async(composition, context)
            
            # 3. Validation and State Update
            mat["specific_capacity"] = prediction.specific_capacity
            mat["voltage"] = prediction.voltage
            mat["cycle_life"] = prediction.cycle_life
            mat["cost_estimate_usd_kg"] = prediction.cost_estimate_usd_kg
            mat["reasoning"] = prediction.reasoning
            
        except Exception as e:
            mat["error"] = str(e)
            mat["reasoning"] = f"Prediction failed: {e}"
            # Provide default poor scores if prediction fails
            mat["specific_capacity"] = 0.0
            mat["voltage"] = 0.0
            mat["cycle_life"] = 0
            mat["cost_estimate_usd_kg"] = 999.0
            
        return mat

    # Process all materials in the population concurrently
    processed_pop = await asyncio.gather(*(process_material(mat) for mat in current_pop))
    
    target_properties = state.get("target_properties", {})
    for mat in processed_pop:
        mat["fitness"] = calculate_fitness(mat, target_properties)
        
    # Sort population by fitness
    processed_pop = sorted(list(processed_pop), key=lambda x: x.get("fitness", 0.0), reverse=True)
    
    # Replace the current population with the annotated materials
    state["current_population"] = processed_pop
    
    # Update Hall of Fame (Top 5 all time)
    best_candidates = state.get("best_candidates", [])
    best_candidates.extend(processed_pop)
    best_candidates = sorted(best_candidates, key=lambda x: x.get("fitness", 0.0), reverse=True)[:5]
    state["best_candidates"] = best_candidates
    
    best_score = best_candidates[0].get("fitness", 0.0) if best_candidates else 0.0
    
    state.setdefault("logs", []).append(f"[{datetime.now(timezone.utc).isoformat()}] Predictor: Processed {len(processed_pop)} materials concurrently. Best Score: {best_score:.2f}")
    
    return state
