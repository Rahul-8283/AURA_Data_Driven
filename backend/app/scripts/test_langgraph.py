import os
import sys
from pprint import pprint
from dotenv import load_dotenv

# Ensure the backend directory is in the sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.state import init_research_state
from app.agents.workflow import app_graph

# Load env variables for API keys
load_dotenv()

def run_test():
    prompt = "Find a cathode with 280 mAh/g capacity without using Cobalt."
    print(f"Testing LangGraph Orchestration with prompt:\n'{prompt}'\n")
    print("-" * 50)
    
    # 1. Visual Verification (Draw the Graph)
    print("=== GRAPH ARCHITECTURE ===")
    try:
        # draw_ascii() visually confirms the edges are wired correctly
        print(app_graph.get_graph().draw_ascii())
    except Exception as e:
        print(f"Could not draw ASCII graph: {e}")
    print("\n" + "-" * 50)
    
    # 2. Initialize State
    initial_state = init_research_state(
        task_id="test_run_001",
        user_prompt=prompt
    )
    
    # 3. Invoke the Graph
    print("Executing Evolutionary Graph Loop...\n")
    final_state = app_graph.invoke(initial_state)
    
    print("-" * 50)
    print("RESULTS:")
    print("-" * 50)
    
    # 4. Verify Planner Parsing
    print("\n=== EXTRACTED CONSTRAINTS ===")
    print(f"Target Properties: {final_state.get('target_properties')}")
    print(f"Base Material:     {final_state.get('base_material_class')}")
    print(f"Excluded Elements: {final_state.get('excluded_elements')}")
    
    # 5. Verify Loop Iterations
    print("\n=== EVOLUTIONARY LOOP METRICS ===")
    print(f"Final Generation: {final_state.get('current_generation')}")
    print(f"Max Generations:  {final_state.get('max_generations')}")
    print(f"Population Size:  {len(final_state.get('current_population', []))}")
    
    # 6. Verify Execution Logs
    print("\n=== EXECUTION LOGS ===")
    # Print first few and last few logs to prove it looped without spamming the console
    logs = final_state.get("logs", [])
    if len(logs) > 6:
        for log in logs[:4]:
            print(log)
        print("...")
        print(f"... [Skipping {len(logs) - 6} middle iteration logs] ...")
        print("...")
        for log in logs[-2:]:
            print(log)
    else:
        for log in logs:
            print(log)
            
    print("\n=== BEST CANDIDATES ===")
    pprint(final_state.get("best_candidates", []))

if __name__ == "__main__":
    run_test()
