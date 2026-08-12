import asyncio
import time
from app.services.retrieval.graph_rag import GraphRAGService

async def run_test():
    query = "What happens to the thermal stability of LCO when doped with Aluminum?"
    print(f"Testing GraphRAG Engine with query:\n'{query}'\n")
    
    start_time = time.time()
    
    context = await GraphRAGService.retrieve_context(query)
    
    end_time = time.time()
    
    print("-" * 50)
    print("RESULTS:")
    print("-" * 50)
    print(context)
    print("-" * 50)
    print(f"Execution Time: {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(run_test())
