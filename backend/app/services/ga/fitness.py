from typing import Dict, Any

def calculate_fitness(material: Dict[str, Any], targets: Dict[str, Any]) -> float:
    """
    Calculates a fitness score based on the material's predicted properties
    and the user's constraints.
    
    Base Score = (Capacity * Voltage * Cycle_Life) / Cost
    """
    capacity = float(material.get("specific_capacity", 0.0))
    voltage = float(material.get("voltage", 0.0))
    cycle_life = float(material.get("cycle_life", 0.0))
    cost = float(material.get("cost_estimate_usd_kg", 25.0))
    
    if cost <= 0:
        cost = 25.0 # Prevent division by zero
        
    base_score = (capacity * voltage * cycle_life) / cost
    
    penalty = 1.0
    
    # Penalize constraint violations heavily
    if targets:
        target_capacity = targets.get("capacity_gt")
        if target_capacity is not None and capacity < float(target_capacity):
            penalty *= 0.2
            
        target_cost = targets.get("cost_lt")
        if target_cost is not None and cost > float(target_cost):
            penalty *= 0.2
            
        target_cycles = targets.get("cycle_life_gt")
        if target_cycles is not None and cycle_life < float(target_cycles):
            penalty *= 0.2

        target_voltage = targets.get("voltage_gt")
        if target_voltage is not None and voltage < float(target_voltage):
            penalty *= 0.2
            
    final_score = base_score * penalty
    return final_score
