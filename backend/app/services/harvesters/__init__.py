from .base import BaseHarvester, HarvestedDocument
from .wikipedia import WikipediaHarvester
from .arxiv import ArxivHarvester
from .crossref import CrossrefHarvester
from .pubmed import PubMedHarvester
from .deduplicator import LiteratureDeduplicator

__all__ = [
    "BaseHarvester",
    "HarvestedDocument",
    "WikipediaHarvester",
    "ArxivHarvester",
    "CrossrefHarvester",
    "PubMedHarvester",
    "LiteratureDeduplicator",
]
