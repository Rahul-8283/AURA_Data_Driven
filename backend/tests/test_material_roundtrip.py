import random

import pytest

from app.services.ga.material import BatteryMaterial
from app.services.ga.operators import crossover, doping, substitution


def _tm_sum(material: BatteryMaterial) -> float:
    return sum(v for k, v in material.composition.items() if k in BatteryMaterial.TRANSITION_METALS)


def test_tiny_coefficient_serializes_without_scientific_notation():
    material = BatteryMaterial(composition={"Li": 1.0, "Ni": 0.99991646, "Zn": 0.00008354, "O": 2.0})

    formula = material.serialize_to_string()

    assert "e" not in formula
    reparsed = BatteryMaterial(formula=formula)
    assert reparsed.composition["Zn"] == pytest.approx(0.000084, abs=1e-6)
    assert _tm_sum(reparsed) == pytest.approx(1.0, abs=1e-3)


def test_parser_accepts_exponent_notation():
    parsed = BatteryMaterial.parse_string_to_dict("LiNi0.9999Zn1e-04O2")

    assert parsed["Zn"] == pytest.approx(0.0001)
    assert parsed["Ni"] == pytest.approx(0.9999)


def test_amounts_below_display_precision_are_dropped():
    material = BatteryMaterial(composition={"Li": 1.0, "Ni": 0.9999999, "Zn": 0.0000001, "O": 2.0})

    assert "Zn" not in material.serialize_to_string()


def test_integer_and_implicit_one_amounts_keep_their_format():
    assert BatteryMaterial(formula="Li1Ni0.8Co0.1Mn0.1O2").serialize_to_string() == "LiCo0.1Mn0.1Ni0.8O2"
    assert BatteryMaterial(composition={"Li": 1.0, "Co": 1.0, "O": 2.0}).serialize_to_string() == "LiCoO2"


def test_random_compositions_survive_a_serialize_parse_round_trip():
    rng = random.Random(11)
    metals = ["Ni", "Co", "Mn", "Al", "Mg", "Ti", "Zr", "Nb", "Fe"]
    for _ in range(500):
        chosen = rng.sample(metals, rng.randint(2, 6))
        weights = [rng.random() ** 6 for _ in chosen]  # skewed so some amounts are tiny
        total = sum(weights)
        composition = {"Li": 1.0, "O": 2.0, **{m: w / total for m, w in zip(chosen, weights)}}

        reparsed = BatteryMaterial(formula=BatteryMaterial(composition=composition).serialize_to_string())

        assert _tm_sum(reparsed) == pytest.approx(1.0, abs=1e-3)


@pytest.mark.parametrize("seed", [5, 15, 24, 101])
def test_long_mutation_chain_never_produces_an_invalid_candidate(seed):
    """Mirrors the mutator: every child is serialized, then re-parsed as a parent."""
    random.seed(seed)
    population = [BatteryMaterial(formula="LiNi0.8Co0.1Mn0.1O2").serialize_to_string()]
    population.append(BatteryMaterial(formula="LiNi0.5Mn0.5O2").serialize_to_string())

    for _ in range(1500):
        parent1 = BatteryMaterial(formula=random.choice(population))
        roll = random.random()
        if roll < 0.4:
            child = doping(parent1, [])
        elif roll < 0.8:
            child = substitution(parent1, [])
        else:
            child = crossover(parent1, BatteryMaterial(formula=random.choice(population)))
        population.append(child.serialize_to_string())
        population = population[-40:]

    for formula in population:
        assert _tm_sum(BatteryMaterial(formula=formula)) == pytest.approx(1.0, abs=1e-3)
