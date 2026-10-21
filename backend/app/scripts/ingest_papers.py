import argparse
import os
import glob
import sys

# Add backend to path so we can run directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.literature_store import get_literature_store
from app.services.ingestion.parser import PDFParser
from app.services.ingestion.chunker import get_chunker
from app.services.ingestion.upsert import process_and_upsert

def main():
    parser = argparse.ArgumentParser(description="Ingest PDF papers into the pgvector literature store.")
    parser.add_argument("--dir", type=str, required=True, help="Directory containing PDF papers")
    args = parser.parse_args()

    pdf_files = glob.glob(os.path.join(args.dir, "*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {args.dir}")
        return

    print(f"Found {len(pdf_files)} PDF files.")
    
    store = get_literature_store()
    pdf_parser = PDFParser()
    chunker = get_chunker()

    for filepath in pdf_files:
        filename = os.path.basename(filepath)
        safe_filename = filename.encode('ascii', 'ignore').decode()
        print(f"Processing {safe_filename}...")
        try:
            text = pdf_parser.parse(filepath)
            chunks = chunker.split_text(text)
            
            # Use filename as a pseudo-DOI for this example
            doi = filename
            base_metadata = {
                "source": filename,
                "type": "paper"
            }
            
            process_and_upsert(store, chunks, base_metadata, doi)
            print(f"Successfully upserted {len(chunks)} chunks from {safe_filename}.")
        except Exception as e:
            print(f"Error processing {safe_filename}: {e}")

if __name__ == "__main__":
    main()
