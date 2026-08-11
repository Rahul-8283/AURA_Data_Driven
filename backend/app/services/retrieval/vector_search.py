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
