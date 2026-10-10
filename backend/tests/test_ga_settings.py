import pytest
from unittest.mock import patch

from app.agents.nodes import planner
from app.core.config import settings


def test_defaults_match_documented_ga_sizes():
    assert settings.GA_GENERATIONS == 20
    assert settings.GA_SEED_POPULATION == 10
    assert settings.GA_POPULATION_SIZE == 20


@patch.object(planner, "call_openrouter", return_value={
    "target_properties": {}, "base_material_class": "NMC_Cathode", "excluded_elements": [],
})
def test_planner_uses_configured_generations_and_seed_size(_llm, monkeypatch):
    monkeypatch.setattr(settings, "GA_GENERATIONS", 3)
    monkeypatch.setattr(settings, "GA_SEED_POPULATION", 4)

    state = planner.planner_node({
        "user_prompt": "cobalt-free cathode",
        "logs": [],
        "excluded_elements": [],
    })

    assert state["max_generations"] == 3
    assert len(state["current_population"]) == 4
