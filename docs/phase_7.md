# Phase 7: Genetic Algorithm (GA) Core Logic (Detailed Implementation Plan)

## 1. Objective and Scope
Phase 7 is the chemical heart of AURA. Instead of relying on an LLM to hallucinate new materials, we will use a deterministic Genetic Algorithm (GA) to mathematically mutate, cross over, and evolve battery material compositions. This logic will live inside the LangGraph `mutator_node` defined in Phase 6.

---

## 2. Material Representation (`app/services/ga/material.py`)

To computationally mutate a material, we must represent its stoichiometry in a structured format rather than a string.
- Create a `BatteryMaterial` class.
- Store composition as a dictionary: `{"Li": 1.0, "Ni": 0.8, "Co": 0.1, "Mn": 0.1, "O": 2.0}`.
- Write parser and serializer functions to convert between strings (`LiNi0.8Co0.1Mn0.1O2`) and the dictionary representation.

---

## 3. Genetic Operators (`app/services/ga/operators.py`)

We need three distinct mutation strategies that obey basic chemical rules.

### 3.1 Doping (Trace Addition)
- Logic: Add a very small stoichiometric amount of a new element (e.g., Mg, Al, Zr).
- Ensure that the total transition metal ratio remains balanced (e.g., if you add 0.05 Al, you must subtract 0.05 from Ni/Co/Mn).
- **Rule:** Only dope with elements known to be chemically viable for the specific lattice (we will validate this with GraphRAG in Phase 9).

### 3.2 Element Substitution (Isovalent/Aliovalent)
- Logic: Swap a percentage of an existing element with another.
- Example: Swap 50% of Cobalt with Nickel.
- **Rule:** Use a static lookup table (or Neo4j query) to ensure we only substitute elements within similar periodic groups (e.g., Transition Metals for Transition Metals).

### 3.3 Crossover (Breeding)
- Logic: Take two parent materials from the current population and blend them.
- Example: Parent 1 (NMC811) + Parent 2 (NMC532) = Child (NMC 6.5-2-1.5).
- Ensure stoichiometric normalization (sum of transition metals = 1.0).

---

## 4. Population Management (`app/services/ga/population.py`)

### 4.1 Selection Mechanism
To evolve, we must select the "fittest" materials to become parents for the next generation.
- Implement **Tournament Selection**: Pick 3 random materials from the current population; the one with the highest fitness score (calculated in Phase 8/9) becomes a parent. Repeat to select a second parent.

### 4.2 The Mutator Node Logic (`app/agents/nodes/mutator.py`)
Implement the actual LangGraph node execution logic.
1. Read the `current_population` and `best_candidates` from the `ResearchState`.
2. Generate a new empty list for `next_population`.
3. Elitism: Automatically carry over the top 2 materials from the previous generation to ensure we don't lose the best solutions.
4. Loop until `next_population` reaches the population size (e.g., 20):
   - Use Tournament Selection to pick parents.
   - Apply Crossover to create a child.
   - Apply Doping or Substitution with a 15% mutation probability.
5. Update `current_generation += 1` in the state.
6. Replace `current_population` in the state with the `next_population`.

---

## 5. Execution and Verification Checklist
1. Write a suite of unit tests for the `BatteryMaterial` stoichiometry parser to ensure math never results in elements with negative ratios.
2. Test the doping function: Dope LCO (`Li1Co1O2`) with 5% Al and verify the output is exactly `Li1Co0.95Al0.05O2`.
3. Run a standalone script invoking the `mutator_node` with a dummy population.
4. Verify that the new population contains expected, mathematically sound variations of the parent materials.
