import httpx
import logging
import urllib.parse
from typing import List
from .base import BaseHarvester, HarvestedDocument, HarvesterError, build_user_agent

logger = logging.getLogger(__name__)

class WikipediaHarvester(BaseHarvester):
    def __init__(self):
        super().__init__(
            user_agent=build_user_agent(),
            min_delay_seconds=0.1
        )
        self.search_url = "https://en.wikipedia.org/w/api.php"
        self.summary_url = "https://en.wikipedia.org/api/rest_v1/page/summary"

    async def search(self, query: str, max_results: int = 5) -> List[HarvestedDocument]:
        await self._throttle()
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        results: List[HarvestedDocument] = []

        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                search_params = {
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "format": "json",
                    "srlimit": max_results
                }
                resp = await client.get(self.search_url, params=search_params, headers=headers)
                if resp.status_code != 200:
                    raise HarvesterError(f"Wikipedia search returned status {resp.status_code}")

                search_data = resp.json().get("query", {}).get("search", [])
                for item in search_data:
                    title = item.get("title")
                    if not title:
                        continue

                    # Fetch detailed summary for the article
                    enc_title = urllib.parse.quote(title.replace(" ", "_"))
                    summary_resp = await client.get(f"{self.summary_url}/{enc_title}", headers=headers)
                    if summary_resp.status_code == 200:
                        s_data = summary_resp.json()
                        extract = s_data.get("extract", "")
                        if extract and len(extract) > 100:
                            results.append(HarvestedDocument(
                                title=s_data.get("title", title),
                                summary=extract,
                                doi=f"wikipedia:{s_data.get('pageid', title)}",
                                source="wikipedia",
                                url=s_data.get("content_urls", {}).get("desktop", {}).get("page", f"https://en.wikipedia.org/wiki/{enc_title}"),
                                published_date=s_data.get("timestamp"),
                                authors=["Wikipedia Contributors"]
                            ))
        except HarvesterError:
            raise
        except Exception as e:
            raise HarvesterError(f"Wikipedia request failed ({type(e).__name__})") from e

        return results
