import httpx
import logging
import xml.etree.ElementTree as ET
from typing import List
from app.core.config import settings
from .base import BaseHarvester, HarvestedDocument

logger = logging.getLogger(__name__)

class PubMedHarvester(BaseHarvester):
    def __init__(self):
        # 10 req/sec if api_key is provided, else 3 req/sec (min delay 0.35s)
        has_key = bool(settings.NCBI_API_KEY)
        delay = 0.1 if has_key else 0.35
        super().__init__(
            user_agent=f"AURA-BatteryResearch/1.0 ({settings.CONTACT_EMAIL})",
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
                    logger.warning(f"PubMed esearch failed with status {search_resp.status_code}")
                    return results

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
                    logger.warning(f"PubMed efetch failed with status {fetch_resp.status_code}")
                    return results

                root = ET.fromstring(fetch_resp.text)
                for article in root.findall(".//PubmedArticle"):
                    pmid_elem = article.find(".//MedlineCitation/PMID")
                    title_elem = article.find(".//ArticleTitle")
                    abstract_elems = article.findall(".//Abstract/AbstractText")

                    if pmid_elem is None or title_elem is None:
                        continue

                    pmid = pmid_elem.text.strip() if pmid_elem.text else ""
                    title = " ".join(title_elem.text.split()) if title_elem.text else ""

                    abstract_parts = []
                    for ab in abstract_elems:
                        if ab.text:
                            abstract_parts.append(ab.text.strip())
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
        except Exception as e:
            logger.error(f"Error fetching from PubMed: {e}")

        return results
