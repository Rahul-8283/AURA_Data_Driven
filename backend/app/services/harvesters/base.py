import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel, Field
from app.core.config import settings
from .relevance import is_battery_relevant

logger = logging.getLogger(__name__)

class HarvesterError(RuntimeError):
    """A source could not be queried: network failure, bad status or unparseable response."""

def build_user_agent() -> str:
    contact = settings.CONTACT_EMAIL.strip()
    if not contact:
        logger.warning("CONTACT_EMAIL is not set; set it to your own address so source APIs can reach you.")
        return "AURA-BatteryResearch/1.0"
    return f"AURA-BatteryResearch/1.0 (mailto:{contact})"

class HarvestedDocument(BaseModel):
    title: str
    summary: str
    doi: str
    source: str
    url: Optional[str] = None
    published_date: Optional[str] = None
    authors: List[str] = Field(default_factory=list)

class BaseHarvester(ABC):
    def __init__(self, user_agent: str, min_delay_seconds: float = 0.0):
        self.user_agent = user_agent
        self.min_delay = min_delay_seconds
        self._last_call = 0.0

    async def _throttle(self) -> None:
        if self.min_delay <= 0:
            return
        elapsed = time.time() - self._last_call
        if elapsed < self.min_delay:
            await asyncio.sleep(self.min_delay - elapsed)
        self._last_call = time.time()

    @abstractmethod
    async def search(self, query: str, max_results: int = 10) -> List[HarvestedDocument]:
        """Fetch and return standardized harvested literature documents.

        Raises HarvesterError when the source itself fails, so callers can tell
        "no results" apart from "source unavailable".
        """
        pass

    async def harvest(self, query: str, max_results: int = 10) -> List[HarvestedDocument]:
        """search() followed by the battery-relevance filter."""
        documents = await self.search(query, max_results=max_results)
        relevant = [d for d in documents if is_battery_relevant(d.title, d.summary)]
        if len(relevant) < len(documents):
            logger.info(f"{type(self).__name__}: dropped {len(documents) - len(relevant)} off-topic result(s)")
        return relevant
