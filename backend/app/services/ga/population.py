import random
from typing import List, Dict, Any

def tournament_selection(population: List[Dict[str, Any]], k: int = 3) -> Dict[str, Any]:
    """
    4.1 Selection Mechanism (Tournament Selection)
    Picks k random materials from the current population.
    Compares their fitness scores and returns the one with the highest score.
    """
    if not population:
        raise ValueError("Cannot select from an empty population.")
        
    tournament_size = min(k, len(population))
    selected = random.sample(population, tournament_size)
    
    # Return the one with the maximum fitness
    # Defaulting to 0.0 if fitness is missing
    winner = max(selected, key=lambda ind: ind.get("fitness", 0.0))
    return winner
