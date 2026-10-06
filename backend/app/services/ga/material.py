import re
from typing import Dict
from dataclasses import dataclass, field

@dataclass
class BatteryMaterial:
    formula: str = ""
    composition: Dict[str, float] = field(default_factory=dict)
    
    # Common transition metals and dopants in battery cathodes
    TRANSITION_METALS = {"Ni", "Co", "Mn", "Al", "Fe", "Ti", "V", "Cr", "Cu", "Zn", "Zr", "Mg", "W", "Mo", "Nb"}

    def __post_init__(self):
        """
        Initialize the dictionary if a string formula is provided,
        and validate the final composition.
        """
        if self.formula and not self.composition:
            self.composition = self.parse_string_to_dict(self.formula)
            
        # Run strict constraints
        self.validate()

    @staticmethod
    def parse_string_to_dict(formula: str) -> Dict[str, float]:
        """
        Uses regex to convert a string like LiNi0.8Co0.1Mn0.1O2 into the dictionary.
        Handle edge cases where elements have an implicit 1 (e.g., Li means Li: 1.0).
        """
        # Regex: Match a chemical symbol (1 capital + optional lowercase)
        # followed by an optional amount (integer or decimal)
        pattern = r"([A-Z][a-z]*)(\d*\.\d+|\d+)?"
        matches = re.findall(pattern, formula)
        
        composition = {}
        for element, amount_str in matches:
            if amount_str == "":
                amount = 1.0
            else:
                amount = float(amount_str)
            
            if element in composition:
                composition[element] += amount
            else:
                composition[element] = amount
                
        return composition

    def serialize_to_string(self) -> str:
        """
        Converts the dictionary back into a readable string to display on the frontend 
        or pass to the LLM for prediction.
        """
        if not self.composition:
            return ""

        # Order logic: Li first, O last, transition metals sorted alphabetically in the middle
        def sort_key(elem):
            if elem == "Li": return 0
            if elem == "O": return 2
            return 1
            
        sorted_elements = sorted(self.composition.items(), key=lambda x: (sort_key(x[0]), x[0]))
        
        result = ""
        for element, amount in sorted_elements:
            if amount <= 0:
                continue
            
            # Format to remove trailing zeroes for display (e.g. 1.0 -> 1, 0.80 -> 0.8)
            if amount.is_integer():
                amount_int = int(amount)
                if amount_int == 1:
                    result += element  # Implicit 1
                else:
                    result += f"{element}{amount_int}"
            else:
                # Use %g or f-string with :g to nicely format floats
                amount_str = f"{amount:g}"
                result += f"{element}{amount_str}"
                
        return result

    def validate(self):
        """
        Implement strict constraints (e.g., in a cathode, the sum of Transition Metals 
        [Ni, Co, Mn, Al, etc.] must exactly equal 1.0 if it's a layered oxide).
        """
        if not self.composition:
            return
            
        tm_sum = sum(
            amount for element, amount in self.composition.items() 
            if element in self.TRANSITION_METALS
        )
        
        # If the material contains transition metals, enforce the stoichiometry rule
        if tm_sum > 0:
            # We use a small epsilon for floating point comparison (e.g. 0.8 + 0.1 + 0.1)
            if not (0.999 <= tm_sum <= 1.001):
                raise ValueError(
                    f"Chemically Invalid: Sum of Transition Metals must equal 1.0. "
                    f"Current sum is {tm_sum:.3f} in composition: {self.composition}"
                )
