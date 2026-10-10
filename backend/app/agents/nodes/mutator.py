import asyncio
import logging
from datetime import datetime, timezone
import random
import uuid
from typing import Dict

from app.agents.state import ResearchState
from app.services.ga.material import BatteryMaterial
from app.services.ga.operators import doping, substitution, crossover
from app.services.ga.population import tournament_selection
from app.services.llm.client import validate_materials_batch_async
from app.services.llm.errors import LLMQuotaExceeded
from app.services.retrieval.graph_rag import GraphRAGService

logger = logging.getLogger(__name__)

TARGET_POPULATION = 20
ELITE_COUNT = 2
VALIDATION_POOL_FACTOR = 2
MAX_VALIDATION_ROUNDS = 2
VERDICT_CACHE: Dict[str, bool] = {}

def _validation_query(composition: str) -> str:
    return f"Is {composition} a structurally stable battery material, or does it violate fundamental valence rules? Check the structural rules provided."

def _draw_child(current_pop: list, excluded_elements: list) -> str:
    parent1_dict = tournament_selection(current_pop)
    parent1_mat = BatteryMaterial(formula=parent1_dict["composition"])

    op_roll = random.random()
    if op_roll < 0.40:
        child_mat = doping(parent1_mat, excluded_elements)
    elif op_roll < 0.80:
        child_mat = substitution(parent1_mat, excluded_elements)
    else:
        parent2_dict = tournament_selection(current_pop)
        parent2_mat = BatteryMaterial(formula=parent2_dict["composition"])
        child_mat = crossover(parent1_mat, parent2_mat)

    return child_mat.serialize_to_string()

def _draw_pool(current_pop: list, excluded_elements: list, size: int, seen: set) -> list[str]:
    pool: list[str] = []
    for _ in range(size * 20):
        if len(pool) >= size:
            break
        composition = _draw_child(current_pop, excluded_elements)
        if composition not in seen and composition not in pool:
            pool.append(composition)
    return pool

async def _validate_pool(pool: list[str]) -> Dict[str, bool]:
    uncached = [c for c in pool if c not in VERDICT_CACHE]
    if uncached:
        try:
            contexts = [
                GraphRAGService.retrieve_context(
                    _validation_query(c),
                    entities=list(BatteryMaterial.parse_string_to_dict(c).keys()),
                )
                for c in uncached
            ]
            contexts = await asyncio.gather(*contexts)
            verdicts = await validate_materials_batch_async(list(zip(uncached, contexts)))
            VERDICT_CACHE.update(verdicts)
        except LLMQuotaExceeded:
            raise
        except Exception as e:
            # On error, assume valid so a flaky LLM cannot stall evolution
            logger.warning(f"Batch validation failed, accepting pool unverified: {e}")
            return {c: True for c in pool}
    return {c: VERDICT_CACHE.get(c, True) for c in pool}

async def mutator_node(state: ResearchState) -> ResearchState:
    """
    4.2 The Mutator Node Logic
    Executes the genetic algorithm evolution for one generation.
    Children are drawn in a pool and validated by GraphRAG + LLM in one batch
    call; at most one top-up batch is spent per generation to fill any shortfall.
    """
    current_pop = state.get("current_population", [])
    excluded_elements = state.get("excluded_elements", [])

    if not current_pop:
        state.setdefault("logs", []).append(f"[{datetime.now(timezone.utc).isoformat()}] Mutator: Population empty. Aborting.")
        return state

    sorted_pop = sorted(current_pop, key=lambda x: x.get("fitness", 0.0), reverse=True)
    elites = sorted_pop[:ELITE_COUNT]
    next_population = list(elites)
    seen = {e["composition"] for e in elites}

    invalid_count = 0
    for _ in range(MAX_VALIDATION_ROUNDS):
        missing = TARGET_POPULATION - len(next_population)
        if missing <= 0:
            break
        pool = _draw_pool(current_pop, excluded_elements, VALIDATION_POOL_FACTOR * missing, seen)
        verdicts = await _validate_pool(pool)
        seen.update(pool)
        for composition in pool:
            if len(next_population) >= TARGET_POPULATION:
                break
            if not verdicts[composition]:
                invalid_count += 1
                continue
            next_population.append({
                "id": f"gen{state.get('current_generation', 0) + 1}_{uuid.uuid4().hex[:8]}",
                "composition": composition,
                "fitness": 0.0 # Will be calculated by the predictor node later
            })

    state["current_generation"] = state.get("current_generation", 0) + 1
    state["current_population"] = next_population
    state.setdefault("logs", []).append(
        f"[{datetime.now(timezone.utc).isoformat()}] Mutator: Generation {state['current_generation']} evolved with size {len(next_population)}. Discarded {invalid_count} invalid candidates."
    )

    return state
