import asyncio
from datetime import datetime, timezone
from typing import Dict, Any

from app.agents.state import ResearchState
from app.services.ga.material import BatteryMaterial
from app.services.retrieval.graph_rag import GraphRAGService
from app.services.llm.client import PredictionResult, predict_properties_batch_async
from app.services.ga.fitness import calculate_fitness

PREDICTION_CACHE: Dict[str, PredictionResult] = {}

def _prediction_query(composition: str) -> str:
    return f"What are the electrochemical properties and degradation modes of {composition}?"

def _apply_prediction(mat: Dict[str, Any], prediction: PredictionResult) -> None:
    mat["specific_capacity"] = prediction.specific_capacity
    mat["voltage"] = prediction.voltage
    mat["cycle_life"] = prediction.cycle_life
    mat["cost_estimate_usd_kg"] = prediction.cost_estimate_usd_kg
    mat["reasoning"] = prediction.reasoning

async def _predict_uncached(compositions: list[str]) -> Dict[str, PredictionResult]:
    contexts = await asyncio.gather(*(
        GraphRAGService.retrieve_context(
            _prediction_query(c),
            entities=list(BatteryMaterial.parse_string_to_dict(c).keys()),
        )
        for c in compositions
    ))
    items = list(zip(compositions, contexts))

    results = await predict_properties_batch_async(items)
    missing = [(c, ctx) for c, ctx in items if c not in results]
    if missing:
        results.update(await predict_properties_batch_async(missing))

    still_missing = [c for c in compositions if c not in results]
    if still_missing:
        raise ValueError(f"LLM returned no prediction for: {', '.join(still_missing)}")
    return results

async def predictor_node(state: ResearchState) -> ResearchState:
    """
    Phase 6: Predictor Node Logic
    Predicts properties for the population in one batched LLM call. Compositions
    already predicted in an earlier generation are served from PREDICTION_CACHE.
    """
    current_pop = state.get("current_population", [])
    if not current_pop:
        state.setdefault("logs", []).append(f"[{datetime.now(timezone.utc).isoformat()}] Predictor: Population empty. Aborting.")
        return state

    uncached = list(dict.fromkeys(
        mat["composition"] for mat in current_pop if mat["composition"] not in PREDICTION_CACHE
    ))
    if uncached:
        PREDICTION_CACHE.update(await _predict_uncached(uncached))

    for mat in current_pop:
        _apply_prediction(mat, PREDICTION_CACHE[mat["composition"]])

    processed_pop = list(current_pop)
    target_properties = state.get("target_properties", {})
    for mat in processed_pop:
        mat["fitness"] = calculate_fitness(mat, target_properties)

    # Sort population by fitness
    processed_pop = sorted(list(processed_pop), key=lambda x: x.get("fitness", 0.0), reverse=True)

    # Replace the current population with the annotated materials
    state["current_population"] = processed_pop

    # Update Hall of Fame (Top 5 all time)
    unique = {}
    for mat in [*state.get("best_candidates", []), *processed_pop]:
        key = mat.get("composition")
        if key not in unique or mat.get("fitness", 0.0) > unique[key].get("fitness", 0.0):
            unique[key] = mat
    best_candidates = sorted(unique.values(), key=lambda x: x.get("fitness", 0.0), reverse=True)[:5]
    state["best_candidates"] = best_candidates

    best_score = best_candidates[0].get("fitness", 0.0) if best_candidates else 0.0
    average_score = sum(m.get("fitness", 0.0) for m in processed_pop) / len(processed_pop)

    state.setdefault("generation_history", []).append({
        "generation": state.get("current_generation", 0),
        "best_score": round(best_score, 2),
        "average_score": round(average_score, 2),
    })

    state.setdefault("logs", []).append(f"[{datetime.now(timezone.utc).isoformat()}] Predictor: Processed {len(processed_pop)} materials. Best Score: {best_score:.2f}")

    return state
