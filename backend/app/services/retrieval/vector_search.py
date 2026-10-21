import asyncio


def search_literature(store, query: str, n_results: int = 5):
    """Nearest literature chunks in pgvector, as dicts with content, metadata and distance."""
    return store.search(query, n_results)


async def get_vector_context(store, query: str, n_results: int = 5) -> str:
    """Fetches the nearest literature chunks and formats them with citations."""
    results = await asyncio.to_thread(search_literature, store, query, n_results)

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
