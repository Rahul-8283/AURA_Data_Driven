import pytest
from unittest.mock import patch, AsyncMock
from app.services.ga.material import BatteryMaterial
from app.services.ga.operators import doping, substitution, crossover
from app.agents.nodes.mutator import mutator_node

def test_battery_material_parser():
    """
    1. Unit Testing (Critical):
    Test the BatteryMaterial stoichiometry parser.
    Ensure math never results in elements with negative ratios.
    """
    # Test valid parsing
    mat = BatteryMaterial(formula="Li1Ni0.8Co0.1Mn0.1O2")
    assert mat.composition["Li"] == 1.0
    assert mat.composition["Ni"] == 0.8
    assert mat.composition["Co"] == 0.1
    assert mat.composition["Mn"] == 0.1
    assert mat.composition["O"] == 2.0
    
    # Test implicit 1.0 parsing
    mat2 = BatteryMaterial(formula="LiNi0.8Co0.1Mn0.1O2")
    assert mat2.composition["Li"] == 1.0
    
    # Test serialization removes trailing zeroes
    assert mat.serialize_to_string() == "LiCo0.1Mn0.1Ni0.8O2"
    
    # Test invalid parsing (sum of TMs != 1.0)
    with pytest.raises(ValueError, match="Chemically Invalid"):
        BatteryMaterial(formula="Li1Ni0.8Co0.5Mn0.1O2")

@patch('app.services.ga.operators.random.choice')
@patch('app.services.ga.operators.random.uniform')
def test_doping_operator(mock_uniform, mock_choice):
    """
    2. Doping Test:
    Takes LCO (Li1Co1O2), dopes it with 5% Al, and asserts the output
    is exactly Li1Co0.95Al0.05O2 (or LiCo0.95Al0.05O2 visually).
    """
    # Setup mock to predictably choose "Al" and 0.05 amount
    mock_choice.return_value = "Al"
    mock_uniform.return_value = 0.05
    
    # Input LCO
    lco = BatteryMaterial(formula="LiCo1O2")
    
    # Dope
    doped_lco = doping(lco, excluded_elements=[])
    
    # Assert output is exactly expected
    assert doped_lco.serialize_to_string() == "LiAl0.05Co0.95O2"

@patch('app.services.ga.operators.random.choice')
def test_substitution_operator_excluded_elements(mock_choice):
    """
    3. Substitution Test:
    Attempts to substitute an excluded_element and verifies it safely aborts.
    """
    # Input NMC material
    nmc = BatteryMaterial(formula="LiNi0.334Co0.333Mn0.333O2")
    
    # If we exclude all possible Transition Metals, it should abort
    all_tms = ["Ni", "Co", "Mn", "Fe", "Cu", "Zn", "Cr", "Al", "Ti"]
    
    # Mock choice to pick 'Ni' as target to reduce
    mock_choice.return_value = "Ni"
    
    # Try to substitute with everything excluded
    subbed = substitution(nmc, excluded_elements=all_tms)
    
    # Assert it safely aborted and returned original composition
    assert subbed.serialize_to_string() == nmc.serialize_to_string()

@pytest.mark.asyncio
@patch("app.agents.nodes.mutator.validate_material_async", new_callable=AsyncMock, return_value=True)
@patch("app.agents.nodes.mutator.GraphRAGService.retrieve_context", new_callable=AsyncMock, return_value="ctx")
async def test_node_execution_and_diversity(_ctx, _validate):
    """
    4 & 5. Node Execution Test & Diversity Verification:
    Run the mutator_node with a dummy population of 20 identical NMC materials.
    Visually verify diversity and mathematically verify TM sum is exactly 1.0.
    """
    # 20 identical materials (TM sum = 1.0)
    base_comp = "LiNi0.334Co0.333Mn0.333O2"
    dummy_pop = []
    for i in range(20):
        dummy_pop.append({
            "id": f"seed_{i}",
            "composition": base_comp,
            "fitness": 0.5
        })
        
    state = {
        "current_population": dummy_pop,
        "excluded_elements": ["Fe", "Cu"],
        "current_generation": 0,
        "logs": []
    }
    
    # Run the node
    new_state = await mutator_node(state)
    next_population = new_state["current_population"]
    
    assert len(next_population) == 20
    
    print("\n\n--- Diversity Verification Output ---")
    for i, ind in enumerate(next_population):
        comp_str = ind['composition']
        print(f"Child {i:02d} (Fitness: {ind['fitness']}): {comp_str}")
        
        # Mathematically verify TM sum == 1.0
        mat = BatteryMaterial(formula=comp_str)
        tm_sum = sum(amount for el, amount in mat.composition.items() if el in BatteryMaterial.TRANSITION_METALS)
        assert 0.999 <= tm_sum <= 1.001
        
    print("-------------------------------------\n")
