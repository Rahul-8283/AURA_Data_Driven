import asyncio
import os
import sys

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.services.llm.client import predict_properties_async
from app.services.retrieval.graph_rag import GraphRAGService

async def main():
    composition = "LiNi0.8Co0.1Mn0.1O2"
    print(f"Testing Predictor Node logic for baseline material: {composition}\n")
    
    query = f"What are the electrochemical properties and degradation modes of {composition}?"
    print("[1/2] Fetching context concurrently via GraphRAG...")
    
    try:
        context = await GraphRAGService.retrieve_context(query)
        print("Context fetched successfully! Preview:")
        print(f"{context[:200]}...\n")
        
        print("[2/2] Running async prediction via OpenRouter (Free Tier)...")
        prediction = await predict_properties_async(composition, context)
        
        print("\n[Success] Prediction successful! Result:")
        print(prediction.model_dump_json(indent=2))
        
    except Exception as e:
        print(f"\n[Error] during testing: {e}")

if __name__ == "__main__":
    asyncio.run(main())
