from langchain_text_splitters import RecursiveCharacterTextSplitter
import re
from typing import List

class SemanticTextSplitter(RecursiveCharacterTextSplitter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def split_text(self, text: str) -> List[str]:
        chunks = super().split_text(text)
        return chunks

def get_chunker():
    return SemanticTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        # Split on a period only when followed by whitespace, so formulas like Ni0.8Co0.1 are never cut
        separators=["\n\n", "\n", r"\.\s", " ", ""],
        is_separator_regex=True
    )
