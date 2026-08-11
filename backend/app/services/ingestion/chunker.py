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
        separators=["\n\n", "\n", ".", " ", ""]
    )
