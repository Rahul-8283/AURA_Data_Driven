from .base import BaseHarvester, HarvestedDocument
from .wikipedia import WikipediaHarvester
from .arxiv import ArxivHarvester
from .crossref import CrossrefHarvester
from .pubmed import PubMedHarvester
from .deduplicator import LiteratureDeduplicator

HARVESTER_SOURCES = ("arxiv", "wikipedia", "crossref", "pubmed")

__all__ = [
    "HARVESTER_SOURCES",
    "BaseHarvester",
    "HarvestedDocument",
    "WikipediaHarvester",
    "ArxivHarvester",
    "CrossrefHarvester",
    "PubMedHarvester",
    "LiteratureDeduplicator",
]
