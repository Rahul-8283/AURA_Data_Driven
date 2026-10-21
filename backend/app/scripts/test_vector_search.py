import argparse
import sys
import os

# Add backend to path so we can run directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.literature_store import get_literature_store
from app.services.retrieval.vector_search import search_literature

def main():
    parser = argparse.ArgumentParser(description="Test vector search against ingested literature.")
    parser.add_argument("query", type=str, help="Search query string")
    args = parser.parse_args()

    print(f"Query: '{args.query}'\n")
    
    results = search_literature(get_literature_store(), args.query, n_results=5)

    if not results:
        print("No results found.")
        return

    for i, res in enumerate(results):
        print(f"--- Result {i+1} (Cosine distance: {res['distance']:.4f}) ---")
        source = res['metadata'].get('source', 'Unknown').encode('ascii', 'ignore').decode()
        print(f"Source: {source}")
        
        # Also protect content printing just in case
        content = res['content'].encode('ascii', 'ignore').decode() if res['content'] else ''
        print(content)
        print()

if __name__ == "__main__":
    main()
