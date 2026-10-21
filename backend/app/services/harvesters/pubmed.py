import httpx
import logging
from defusedxml import ElementTree as ET
from typing import List
from app.core.config import settings
from .base import BaseHarvester, HarvestedDocument, HarvesterError, build_user_agent

logger = logging.getLogger(__name__)

def element_text(element) -> str:
    """All text of an element including inline markup. Element.text alone stops at the first child
    tag, which truncates `LiNi<sub>0.8</sub>Co<sub>0.1</sub>O<sub>2</sub>` to `LiNi`."""
    return " ".join("".join(element.itertext()).split())

class PubMedHarvester(BaseHarvester):
    def __init__(self):
        # 10 req/sec if api_key is provided, else 3 req/sec (min delay 0.35s)
        has_key = bool(settings.NCBI_API_KEY)
        delay = 0.1 if has_key else 0.35
        super().__init__(
            user_agent=build_user_agent(),
            min_delay_seconds=delay
        )
        self.esearch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        self.efetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        self.api_key = settings.NCBI_API_KEY

    async def search(self, query: str, max_results: int = 10) -> List[HarvestedDocument]:
        await self._throttle()
        results: List[HarvestedDocument] = []
        headers = {"User-Agent": self.user_agent}

        search_params = {
            "db": "pubmed",
            "term": f"({query}) AND (battery OR cathode OR electrolyte OR anode)",
            "retmode": "json",
            "retmax": max_results,
            "sort": "pub_date"
        }
        if self.api_key:
            search_params["api_key"] = self.api_key

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                search_resp = await client.get(self.esearch_url, params=search_params, headers=headers)
                if search_resp.status_code != 200:
                    raise HarvesterError(f"PubMed esearch returned status {search_resp.status_code}")

                id_list = search_resp.json().get("esearchresult", {}).get("idlist", [])
                if not id_list:
                    return results

                # Fetch XML details for these PMIDs
                await self._throttle()
                fetch_params = {
                    "db": "pubmed",
                    "id": ",".join(id_list),
                    "retmode": "xml"
                }
                if self.api_key:
                    fetch_params["api_key"] = self.api_key

                fetch_resp = await client.get(self.efetch_url, params=fetch_params, headers=headers)
                if fetch_resp.status_code != 200:
                    raise HarvesterError(f"PubMed efetch returned status {fetch_resp.status_code}")

                root = ET.fromstring(fetch_resp.text)
                for article in root.findall(".//PubmedArticle"):
                    pmid_elem = article.find(".//MedlineCitation/PMID")
                    title_elem = article.find(".//ArticleTitle")
                    abstract_elems = article.findall(".//Abstract/AbstractText")

                    if pmid_elem is None or title_elem is None:
                        continue

                    pmid = element_text(pmid_elem)
                    title = element_text(title_elem)

                    abstract_parts = []
                    for ab in abstract_elems:
                        part = element_text(ab)
                        if not part:
                            continue
                        label = ab.get("Label")
                        abstract_parts.append(f"{label}: {part}" if label else part)
                    abstract = " ".join(abstract_parts)

                    authors = []
                    for author in article.findall(".//AuthorList/Author"):
                        last = author.find("LastName")
                        fore = author.find("ForeName")
                        if last is not None and last.text:
                            full = f"{fore.text} {last.text}" if fore is not None and fore.text else last.text
                            authors.append(full)

                    if title and abstract and len(abstract) >= 20 and pmid:
                        results.append(HarvestedDocument(
                            title=title,
                            summary=abstract,
                            doi=f"pubmed:{pmid}",
                            source="pubmed",
                            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                            authors=authors
                        ))
        except HarvesterError:
            raise
        except Exception as e:
            # Report the exception type only: request errors can embed the URL, which carries the NCBI api_key.
            raise HarvesterError(f"PubMed request failed ({type(e).__name__})") from e

        return results
