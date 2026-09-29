# Phase 5: Genetic Algorithm (GA) Core Logic (Detailed Implementation Plan)

## 1. Objective and Scope
Phase 5 is the mathematical and chemical heart of AURA. Instead of relying on an LLM to blindly hallucinate new materials (which often results in chemically impossible structures like $Li_5Ni_{10}O_2$), we will use a deterministic **Genetic Algorithm (GA)** to strictly mutate, cross over, and evolve battery material compositions. This logic will live inside the LangGraph `mutator_node` defined in Phase 4.

---

## 2. Material Stoichiometry Representation (`app/services/ga/material.py`)

To computationally mutate a material, we must represent its stoichiometry in a highly structured, machine-readable format rather than a string.

### 2.1 The `BatteryMaterial` Class
- Create a Python data class that handles chemical composition parsing and validation.
- Store composition as a normalized dictionary: `{"Li": 1.0, "Ni": 0.8, "Co": 0.1, "Mn": 0.1, "O": 2.0}`.
- Implement strict constraints (e.g., in a cathode, the sum of Transition Metals `[Ni, Co, Mn, Al, etc.]` must exactly equal `1.0` if it's a layered oxide).

### 2.2 Parsers and Serializers
- **`parse_string_to_dict(formula: str)`:** Uses regex to convert a string like `LiNi0.8Co0.1Mn0.1O2` into the dictionary. Handle edge cases where elements have an implicit `1` (e.g., `Li` means `Li: 1.0`).
- **`serialize_to_string()`:** Converts the dictionary back into a readable string to display on the frontend or pass to the LLM for prediction.

---

## 3. The Genetic Operators (`app/services/ga/operators.py`)

We need three distinct mutation strategies. The GA will randomly choose which operator to apply to a selected parent during the generation cycle.

### 3.1 Doping (Trace Addition - 40% Probability)
- **Logic:** Add a very small stoichiometric amount of a new element (e.g., Mg, Al, Zr) to stabilize the lattice.
- **Rules:**
  - Randomly select a dopant from a predefined list of viable elements (pulled from Neo4j in Phase 2).
  - Select a doping amount between `0.01` and `0.05`.
  - Ensure total transition metal ratio remains balanced. If you add `0.05 Al`, you must subtract `0.05` proportionally from the base metals (Ni/Co/Mn).
- **Validation:** If the resulting subtraction causes any base element to drop below `0.0`, discard the mutation and retry.

### 3.2 Element Substitution (Isovalent/Aliovalent - 40% Probability)
- **Logic:** Swap a significant percentage of an existing element with another entirely.
- **Rules:**
  - Example: Swap 50% of the Cobalt in NMC with Nickel to create a higher capacity, lower-cost cathode.
  - Use a static lookup table to ensure we only substitute elements within similar periodic groups (e.g., swapping a Transition Metal for another Transition Metal).
  - Ensure the user's `excluded_elements` list (from Phase 4 state) is strictly respected. Do not substitute IN an element the user explicitly banned.

### 3.3 Crossover / Breeding (20% Probability)
- **Logic:** Take two parent materials from the current population and blend them to find a middle ground.
- **Rules:**
  - Example: Parent 1 (NMC811: `Ni=0.8, Co=0.1, Mn=0.1`) + Parent 2 (NMC532: `Ni=0.5, Co=0.3, Mn=0.2`).
  - Child = Average of parents: `Ni=0.65, Co=0.20, Mn=0.15`.
  - Ensure stoichiometric normalization post-crossover.

---

## 4. Population Management & Selection (`app/services/ga/population.py`)

### 4.1 Selection Mechanism (Tournament Selection)
To evolve, we must select the "fittest" materials to become parents for the next generation.
- Implement **Tournament Selection**: Pick 3 random materials from the current population. Compare their fitness scores (calculated in Phase 7). The one with the highest score wins and becomes a parent.
- Repeat to select a second parent for Crossover operations.
- This maintains genetic diversity better than purely picking the top 2.

### 4.2 The Mutator Node Logic (`app/agents/nodes/mutator.py`)
Implement the actual LangGraph node execution logic that ties this all together.
1. Read the `current_population`, `best_candidates`, and `excluded_elements` from the `ResearchState`.
2. Generate a new empty list for `next_population`.
3. **Elitism:** Automatically carry over the top 2 materials (the elites) from the previous generation completely untouched. This ensures we don't accidentally mutate and lose the best solutions found so far.
4. **Generation Loop:** Loop until `next_population` reaches the defined population size (e.g., 20):
   - Use Tournament Selection to pick a parent.
   - Roll a random number to determine the operator (Doping, Substitution, or Crossover).
   - Apply the operator to create a `child_material`.
   - Append `child_material` to `next_population`.
5. Update `current_generation += 1` in the state.
6. Replace `current_population` in the state with the `next_population` and append a progress log.

---

## 5. Execution and Verification Checklist

Because this phase is entirely mathematical, it is the most prone to catastrophic silent bugs if ratios get skewed.
1. **Unit Testing (Critical):** Write an extensive suite of Pytest unit tests for the `BatteryMaterial` stoichiometry parser. Ensure math never results in elements with negative ratios.
2. **Doping Test:** Write a test that takes LCO (`Li1Co1O2`), dopes it with 5% Al, and `assert` the output is exactly `Li1Co0.95Al0.05O2`.
3. **Substitution Test:** Write a test that attempts to substitute an `excluded_element` and verify it raises a custom `ChemicallyInvalidError` or safely aborts.
4. **Node Execution Test:** Run a standalone script invoking the `mutator_node` with a dummy population of 20 identical NMC111 materials.
5. **Diversity Verification:** Print the output `next_population`. Visually verify that it contains a highly diverse set of mathematically sound variations, and that the sum of the transition metals in every single child still exactly equals 1.0.
