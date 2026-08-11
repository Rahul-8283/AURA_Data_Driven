import fitz  # PyMuPDF
import re
from typing import List, Optional

class DocumentParser:
    def parse(self, filepath: str) -> str:
        raise NotImplementedError

class PDFParser(DocumentParser):
    def parse(self, filepath: str) -> str:
        """Parses a PDF file, attempting to strip headers, footers, and references."""
        doc = fitz.open(filepath)
        text_blocks = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            # Get blocks, sort them by vertical position
            blocks = page.get_text("blocks")
            blocks.sort(key=lambda b: (b[1], b[0]))
            
            for b in blocks:
                text = b[4].strip()
                
                # Heuristic to skip typical headers/footers based on block length or position
                if len(text) < 20 and (b[1] < 50 or b[3] > page.rect.height - 50):
                    continue
                    
                # Heuristic to skip References/Bibliography (simple detection)
                if re.match(r'^(References|Bibliography)\b', text, re.IGNORECASE):
                    # Stop parsing completely as references are typically at the end
                    return "\n\n".join(text_blocks)
                
                # Heuristic to skip Acknowledgements
                if re.match(r'^Acknowledgements?\b', text, re.IGNORECASE):
                    continue
                
                if text:
                    text_blocks.append(text)
                    
        return "\n\n".join(text_blocks)

class TXTParser(DocumentParser):
    def parse(self, filepath: str) -> str:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()

class CSVParser(DocumentParser):
    def parse(self, filepath: str) -> str:
        import csv
        text_lines = []
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                text_lines.append(" ".join(row))
        return "\n\n".join(text_lines)
