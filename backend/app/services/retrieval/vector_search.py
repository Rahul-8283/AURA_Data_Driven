import asyncio

def search_literature(collection, query: str, n_results: int = 5, filter_metadata: dict = None):
    """
    Searches the ChromaDB collection for the most relevant literature chunks.
    Allows optional metadata filtering (e.g., year > 2020).
    """
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        where=filter_metadata
    )
    
    # Format the results into a readable list of dictionaries
    formatted_results = []
    if results and results.get('documents') and len(results['documents']) > 0:
        for i in range(len(results['documents'][0])):
            formatted_results.append({
                "content": results['documents'][0][i],
                "metadata": results['metadatas'][0][i],
                "distance": results['distances'][0][i] if 'distances' in results and results['distances'] else None
            })
    return formatted_results

async def get_vector_context(collection, query: str, n_results: int = 5) -> str:
    """
    Asynchronously fetches vector search results and formats them into a clean string with citations.
    """
    # Wrap the synchronous call in asyncio.to_thread to prevent blocking the event loop
    results = await asyncio.to_thread(search_literature, collection, query, n_results)
    
    if not results:
        return "No relevant literature evidence found."
        
    formatted_context = ""
    for idx, res in enumerate(results):
        metadata = res.get("metadata", {})
        source = metadata.get("source", "Unknown Source")
        page = metadata.get("page", "N/A")
        content = res.get("content", "")
        formatted_context += f"[{idx + 1}] (Source: {source}, Page: {page}): {content}\n\n"
        
    return formatted_context.strip()
