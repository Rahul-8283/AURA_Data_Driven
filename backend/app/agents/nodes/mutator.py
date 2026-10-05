from datetime import datetime, timezone
import random
import uuid
from app.agents.state import ResearchState
from app.services.ga.material import BatteryMaterial
from app.services.ga.operators import doping, substitution, crossover
from app.services.ga.population import tournament_selection
from app.services.llm.client import validate_material_async
from app.services.retrieval.graph_rag import GraphRAGService

async def mutator_node(state: ResearchState) -> ResearchState:
    """
    4.2 The Mutator Node Logic
    Executes the genetic algorithm evolution for one generation.
    Incorporates Phase 7 chemical validation via GraphRAG.
    """
    current_pop = state.get("current_population", [])
    excluded_elements = state.get("excluded_elements", [])
    
    if not current_pop:
        state.setdefault("logs", []).append(f"[{datetime.now(timezone.utc).isoformat()}] Mutator: Population empty. Aborting.")
        return state

    next_population = []
    
    # 3. Elitism: automatically carry over top 2 materials (the elites) completely untouched
    sorted_pop = sorted(current_pop, key=lambda x: x.get("fitness", 0.0), reverse=True)
    elites = sorted_pop[:2]
    next_population.extend(elites)
    
    target_size = max(len(current_pop), 20)
    
    # 4. Generation Loop with Validation
    invalid_count = 0
    while len(next_population) < target_size:
        # Use Tournament Selection to pick a parent
        parent1_dict = tournament_selection(current_pop)
        parent1_mat = BatteryMaterial(formula=parent1_dict["composition"])
        
        # Roll a random number to determine the operator
        op_roll = random.random()
        child_mat = None
        
        if op_roll < 0.40:
            # Doping (40% Probability)
            child_mat = doping(parent1_mat, excluded_elements)
        elif op_roll < 0.80:
            # Substitution (40% Probability)
            child_mat = substitution(parent1_mat, excluded_elements)
        else:
            # Crossover (20% Probability)
            parent2_dict = tournament_selection(current_pop)
            parent2_mat = BatteryMaterial(formula=parent2_dict["composition"])
            child_mat = crossover(parent1_mat, parent2_mat)
            
        composition_str = child_mat.serialize_to_string()
        
        # Phase 7 GraphRAG Validation Filter
        query = f"Is {composition_str} a structurally stable battery material, or does it violate fundamental valence rules? Check the structural rules provided."
        try:
            context = await GraphRAGService.retrieve_context(query)
            is_valid = await validate_material_async(composition_str, context)
        except Exception as e:
            # On error, we assume valid to not block evolution forever
            is_valid = True
            
        if not is_valid:
            invalid_count += 1
            continue
            
        # Append valid child_material to next_population
        child_dict = {
            "id": f"gen{state.get('current_generation', 0) + 1}_{uuid.uuid4().hex[:8]}",
            "composition": composition_str,
            "fitness": 0.0 # Will be calculated by the predictor node later
        }
        next_population.append(child_dict)
        
    # 5. Update current_generation += 1 in the state
    state["current_generation"] = state.get("current_generation", 0) + 1
    
    # 6. Replace current_population in the state with the next_population and append a progress log
    state["current_population"] = next_population
    state.setdefault("logs", []).append(
        f"[{datetime.now(timezone.utc).isoformat()}] Mutator: Generation {state['current_generation']} evolved with size {len(next_population)}. Discarded {invalid_count} invalid candidates."
    )
    
    return state
