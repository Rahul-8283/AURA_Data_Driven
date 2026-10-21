import httpx
import logging
import re
from typing import List
from app.core.config import settings
from .base import BaseHarvester, HarvestedDocument, HarvesterError, build_user_agent

logger = logging.getLogger(__name__)

TAG_RE = re.compile(r"<[^>]+>")

def clean_abstract(raw: str) -> str:
    """Strip JATS XML tags such as <jats:p> or <jats:sec> from Crossref abstracts."""
    if not raw:
        return ""
    cleaned = TAG_RE.sub(" ", raw)
    return " ".join(cleaned.split())

class CrossrefHarvester(BaseHarvester):
    def __init__(self):
        super().__init__(
            user_agent=build_user_agent(),
            min_delay_seconds=0.2
        )
        self.api_url = "https://api.crossref.org/works"

    async def search(self, query: str, max_results: int = 10) -> List[HarvestedDocument]:
        await self._throttle()
        results: List[HarvestedDocument] = []
        headers = {"User-Agent": self.user_agent}

        params = {
            "query": f"battery {query}",
            "rows": max_results,
            "filter": "has-abstract:true",
            "sort": "relevance",
        }
        if settings.CONTACT_EMAIL.strip():
            params["mailto"] = settings.CONTACT_EMAIL.strip()

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(self.api_url, params=params, headers=headers)
                if resp.status_code != 200:
                    raise HarvesterError(f"Crossref API returned status {resp.status_code}")

                items = resp.json().get("message", {}).get("items", [])
                for item in items:
                    title_list = item.get("title", [])
                    title = title_list[0] if title_list else ""
                    raw_abstract = item.get("abstract", "")
                    abstract = clean_abstract(raw_abstract)
                    doi = item.get("DOI", "")
                    url = item.get("URL", f"https://doi.org/{doi}") if doi else ""

                    authors = []
                    for a in item.get("author", []):
                        full_name = f"{a.get('given', '')} {a.get('family', '')}".strip()
                        if full_name:
                            authors.append(full_name)

                    if title and abstract and len(abstract) > 50 and doi:
                        results.append(HarvestedDocument(
                            title=title,
                            summary=abstract,
                            doi=f"doi:{doi}",
                            source="crossref",
                            url=url,
                            published_date=str(item.get("created", {}).get("date-time", "")),
                            authors=authors
                        ))
        except HarvesterError:
            raise
        except Exception as e:
            raise HarvesterError(f"Crossref request failed ({type(e).__name__})") from e

        return results
