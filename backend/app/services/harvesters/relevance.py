# One strong term is enough to call a document battery-related; weak terms are ambiguous on their
# own (e.g. "lithium" also appears in psychiatry papers) so two distinct ones are required.
STRONG_TERMS = (
    "battery", "batteries", "cathode", "anode", "electrolyte",
    "lithium-ion", "lithium ion", "li-ion", "sodium-ion", "sodium ion",
)
WEAK_TERMS = (
    "lithium", "sodium", "electrode", "intercalation", "dendrite", "capacity retention",
    "cycle life", "coulombic", "state of charge", "separator", "layered oxide",
    "spinel", "olivine", "nmc", "lfp",
)


def is_battery_relevant(title: str, summary: str) -> bool:
    """Keep off-topic pages out of the knowledge base that validates and scores candidates."""
    text = f"{title} {summary}".lower()
    if any(term in text for term in STRONG_TERMS):
        return True
    return sum(term in text for term in WEAK_TERMS) >= 2
