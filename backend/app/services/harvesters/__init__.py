from .base import BaseHarvester, HarvestedDocument, HarvesterError
from .relevance import is_battery_relevant
from .wikipedia import WikipediaHarvester
from .arxiv import ArxivHarvester
from .crossref import CrossrefHarvester
from .pubmed import PubMedHarvester
from .deduplicator import LiteratureDeduplicator, title_key

HARVESTER_SOURCES = ("arxiv", "wikipedia", "crossref", "pubmed")

__all__ = [
    "HARVESTER_SOURCES",
    "BaseHarvester",
    "HarvestedDocument",
    "HarvesterError",
    "is_battery_relevant",
    "WikipediaHarvester",
    "ArxivHarvester",
    "CrossrefHarvester",
    "PubMedHarvester",
    "LiteratureDeduplicator",
    "title_key",
]
