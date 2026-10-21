import httpx
import logging
import re
from defusedxml import ElementTree as ET
from typing import List
from .base import BaseHarvester, HarvestedDocument, HarvesterError, build_user_agent

logger = logging.getLogger(__name__)

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
# Materials-science categories where battery research is filed; keeps unrelated physics out.
ARXIV_CATEGORIES = ("cond-mat.mtrl-sci", "physics.chem-ph", "physics.app-ph")
MAX_QUERY_TERMS = 8

def build_search_query(query: str) -> str:
    """AND every term (an unquoted multi-word query would only bind the first word to a field)
    and restrict to materials categories. Punctuation is dropped so user input cannot alter the query syntax."""
    terms = re.findall(r"[A-Za-z0-9][A-Za-z0-9.\-]*", query)[:MAX_QUERY_TERMS]
    if not terms:
        return ""
    keywords = " AND ".join(f"all:{term}" for term in terms)
    categories = " OR ".join(f"cat:{category}" for category in ARXIV_CATEGORIES)
    return f"({keywords}) AND ({categories})"

class ArxivHarvester(BaseHarvester):
    def __init__(self):
        super().__init__(
            user_agent=build_user_agent(),
            min_delay_seconds=3.0  # Respect arXiv 1 request every 3 seconds policy
        )
        self.api_url = "https://export.arxiv.org/api/query"

    async def search(self, query: str, max_results: int = 10) -> List[HarvestedDocument]:
        search_query = build_search_query(query)
        if not search_query:
            return []

        await self._throttle()
        results: List[HarvestedDocument] = []
        headers = {"User-Agent": self.user_agent}
        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(self.api_url, params=params, headers=headers)
                if resp.status_code != 200:
                    raise HarvesterError(f"arXiv API returned status {resp.status_code}")

                root = ET.fromstring(resp.text)
                entries = root.findall("atom:entry", ATOM_NS)

                for entry in entries:
                    title_elem = entry.find("atom:title", ATOM_NS)
                    summary_elem = entry.find("atom:summary", ATOM_NS)
                    id_elem = entry.find("atom:id", ATOM_NS)
                    published_elem = entry.find("atom:published", ATOM_NS)

                    if title_elem is None or summary_elem is None or id_elem is None:
                        continue

                    title = " ".join(title_elem.text.split()) if title_elem.text else ""
                    summary = " ".join(summary_elem.text.split()) if summary_elem.text else ""
                    raw_id = id_elem.text.strip() if id_elem.text else ""
                    published = published_elem.text.strip() if published_elem is not None and published_elem.text else None

                    authors = []
                    for author in entry.findall("atom:author", ATOM_NS):
                        name_elem = author.find("atom:name", ATOM_NS)
                        if name_elem is not None and name_elem.text:
                            authors.append(name_elem.text.strip())

                    # Use arXiv ID as canonical doi identifier
                    doi = raw_id.replace("http://arxiv.org/abs/", "arxiv:").replace("https://arxiv.org/abs/", "arxiv:")

                    if title and summary and len(summary) > 50:
                        results.append(HarvestedDocument(
                            title=title,
                            summary=summary,
                            doi=doi,
                            source="arxiv",
                            url=raw_id,
                            published_date=published,
                            authors=authors
                        ))
        except HarvesterError:
            raise
        except Exception as e:
            raise HarvesterError(f"arXiv request failed ({type(e).__name__})") from e

        return results
