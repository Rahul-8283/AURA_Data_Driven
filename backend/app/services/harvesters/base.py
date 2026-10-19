import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

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
        """Fetch and return standardized harvested literature documents."""
        pass
