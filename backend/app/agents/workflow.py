import logging
from langgraph.graph import StateGraph, END
from app.agents.state import ResearchState

from app.agents.nodes.planner import planner_node
from app.agents.nodes.mutator import mutator_node
from app.agents.nodes.predictor import predictor_node
from app.agents.nodes.dummy_nodes import dummy_reporter_node

logger = logging.getLogger(__name__)

# Initialize the StateGraph
workflow = StateGraph(ResearchState)

# Add all the nodes
workflow.add_node("planner", planner_node)
workflow.add_node("mutator", mutator_node)
workflow.add_node("predictor", predictor_node)
workflow.add_node("reporter", dummy_reporter_node)

# Define the basic linear edges
workflow.set_entry_point("planner")
workflow.add_edge("planner", "mutator")
workflow.add_edge("mutator", "predictor")

def check_generation(state: ResearchState) -> str:
    """
    Conditional routing logic from the Predictor node.
    If we haven't reached max generations, loop back to the mutator.
    Otherwise, proceed to the reporter.
    """
    if state["current_generation"] < state["max_generations"]:
        return "continue_evolution"
    return "generate_report"

# Add conditional loop from Predictor back to Mutator or to Reporter
workflow.add_conditional_edges(
    "predictor",
    check_generation,
    {
        "continue_evolution": "mutator",
        "generate_report": "reporter"
    }
)

# Connect reporter to the end
workflow.add_edge("reporter", END)

# Compile the graph into an executable application
app_graph = workflow.compile()
