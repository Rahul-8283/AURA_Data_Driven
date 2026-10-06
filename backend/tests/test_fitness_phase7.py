from app.services.ga.fitness import calculate_fitness
from app.agents.nodes.planner import build_seed_population
from app.services.ga.material import BatteryMaterial

GOOD = {"specific_capacity": 280.0, "voltage": 3.8, "cycle_life": 1000, "cost_estimate_usd_kg": 30.0}
TARGETS = {"capacity_gt": 250, "cost_lt": 50, "cycle_life_gt": 800}

def test_constraint_violation_is_penalized():
    bad = {**GOOD, "specific_capacity": 180.0}
    assert calculate_fitness(bad, TARGETS) < calculate_fitness(GOOD, TARGETS) * 0.3

def test_cycle_life_target_is_penalized():
    short = {**GOOD, "cycle_life": 500}
    assert calculate_fitness(short, TARGETS) < calculate_fitness(GOOD, TARGETS)

def test_seed_population_is_parseable_and_cobalt_free():
    pop = build_seed_population(["Co"])
    assert len(pop) == 10
    for m in pop:
        assert "Co" not in BatteryMaterial(formula=m["composition"]).composition
