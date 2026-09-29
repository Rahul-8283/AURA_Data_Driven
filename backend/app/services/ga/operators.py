import random
from typing import List, Dict
from app.services.ga.material import BatteryMaterial

# Predefined lists (can be expanded based on Neo4j Graph knowledge)
VIABLE_DOPANTS = ["Mg", "Al", "Zr", "Ti", "Nb", "Mo", "V", "W"]

SUBSTITUTION_GROUPS = {
    # Elements that can reasonably substitute each other in layered oxides
    "TM": ["Ni", "Co", "Mn", "Fe", "Cu", "Zn", "Cr", "Al", "Ti"]
}

def get_transition_metals(composition: Dict[str, float]) -> Dict[str, float]:
    """Helper to extract only the transition metals/dopants from a composition."""
    return {
        k: v for k, v in composition.items() 
        if k in BatteryMaterial.TRANSITION_METALS
    }

def doping(material: BatteryMaterial, excluded_elements: List[str]) -> BatteryMaterial:
    """
    3.1 Doping (Trace Addition)
    Adds a very small stoichiometric amount (0.01 - 0.05) of a new element.
    Subtracts proportionally from the base metals to keep sum of TMs = 1.0.
    """
    child_comp = material.composition.copy()
    
    # Select dopant
    available_dopants = [
        d for d in VIABLE_DOPANTS 
        if d not in excluded_elements and d not in child_comp
    ]
    if not available_dopants:
        return material  # Return unmodified if no valid dopant
        
    dopant = random.choice(available_dopants)
    amount = random.uniform(0.01, 0.05)
    
    tms = get_transition_metals(child_comp)
    if not tms:
        return material 
        
    total_tm = sum(tms.values())
    
    # Subtract proportionally
    for k in tms:
        reduction = amount * (tms[k] / total_tm)
        child_comp[k] -= reduction
        
    # Validation: discard mutation if any element drops below zero
    if any(v < 0 for v in child_comp.values()):
        return material 
        
    # Add the dopant
    child_comp[dopant] = amount
    
    try:
        return BatteryMaterial(composition=child_comp)
    except ValueError:
        # If mathematically it fails strict validation, abort mutation
        return material

def substitution(material: BatteryMaterial, excluded_elements: List[str]) -> BatteryMaterial:
    """
    3.2 Element Substitution (Isovalent/Aliovalent)
    Swaps a percentage (10% to 50%) of an existing element with another entirely.
    """
    child_comp = material.composition.copy()
    tms = get_transition_metals(child_comp)
    
    if not tms:
        return material
        
    # Pick a transition metal currently in the material to reduce
    target_to_reduce = random.choice(list(tms.keys()))
    
    # Pick a substitute from the TM group
    available_subs = [
        s for s in SUBSTITUTION_GROUPS["TM"] 
        if s not in excluded_elements and s != target_to_reduce
    ]
    if not available_subs:
        return material
        
    substitute = random.choice(available_subs)
    
    # Swap up to 50%
    swap_percentage = random.uniform(0.1, 0.5)
    amount_to_swap = child_comp[target_to_reduce] * swap_percentage
    
    child_comp[target_to_reduce] -= amount_to_swap
    
    if substitute in child_comp:
        child_comp[substitute] += amount_to_swap
    else:
        child_comp[substitute] = amount_to_swap
        
    try:
        return BatteryMaterial(composition=child_comp)
    except ValueError:
        return material

def crossover(parent1: BatteryMaterial, parent2: BatteryMaterial) -> BatteryMaterial:
    """
    3.3 Crossover / Breeding
    Blends two parents by averaging their compositions.
    Since both parents' Transition Metals sum to 1.0, their average will also sum to 1.0.
    """
    all_elements = set(parent1.composition.keys()).union(parent2.composition.keys())
    child_comp = {}
    
    for el in all_elements:
        val1 = parent1.composition.get(el, 0.0)
        val2 = parent2.composition.get(el, 0.0)
        child_comp[el] = (val1 + val2) / 2.0
        
    try:
        return BatteryMaterial(composition=child_comp)
    except ValueError:
        # If for some reason averaging violates constraints (e.g. float precision issues),
        # return parent 1 as fallback
        return parent1
