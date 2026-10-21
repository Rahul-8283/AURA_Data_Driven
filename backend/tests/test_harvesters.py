import pytest
import time
from unittest.mock import MagicMock, patch
from app.services.harvesters.base import BaseHarvester, HarvestedDocument
from app.services.harvesters.crossref import clean_abstract, CrossrefHarvester
from app.services.harvesters.deduplicator import LiteratureDeduplicator
from app.services.harvesters.arxiv import ArxivHarvester
from app.services.harvesters.pubmed import PubMedHarvester
from app.services.harvesters.wikipedia import WikipediaHarvester

class DummyHarvester(BaseHarvester):
    async def search(self, query: str, max_results: int = 10):
        await self._throttle()
        return []

@pytest.mark.asyncio
async def test_base_harvester_throttling():
    harvester = DummyHarvester(user_agent="test/1.0", min_delay_seconds=0.15)
    t0 = time.time()
    await harvester.search("test1")
    await harvester.search("test2")
    elapsed = time.time() - t0
    assert elapsed >= 0.14

def test_clean_abstract_strips_jats_tags():
    raw = "<jats:title>Abstract</jats:title><jats:p>This is a <jats:bold>solid-state</jats:bold> battery study.</jats:p>"
    cleaned = clean_abstract(raw)
    assert "<" not in cleaned
    assert ">" not in cleaned
    assert "solid-state battery study" in cleaned

def test_literature_deduplicator():
    store = MagicMock()
    store.exists.side_effect = [True, False]  # first DOI is indexed, second is novel
    dedup = LiteratureDeduplicator(store=store)
    assert dedup.is_already_indexed("doi:10.1016/j.jpowsour.2024") is True
    assert dedup.is_already_indexed("doi:10.1016/j.jpowsour.9999") is False

@pytest.mark.asyncio
async def test_arxiv_harvester_parses_atom_feed():
    sample_atom = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <id>http://arxiv.org/abs/2401.12345v1</id>
        <title>Novel Lithium Iron Phosphate Doping</title>
        <summary>This study shows high cycle life with Al doping in LFP.</summary>
        <published>2024-01-20T00:00:00Z</published>
        <author><name>Dr. Jane Doe</name></author>
      </entry>
    </feed>"""

    harvester = ArxivHarvester()
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = sample_atom
        mock_get.return_value = mock_resp

        results = await harvester.search("LFP doping", max_results=1)
        assert len(results) == 1
        assert results[0].title == "Novel Lithium Iron Phosphate Doping"
        assert results[0].source == "arxiv"
        assert "arxiv:2401.12345v1" in results[0].doi
        assert "Dr. Jane Doe" in results[0].authors

@pytest.mark.asyncio
async def test_pubmed_harvester_parses_xml():
    sample_search_json = {"esearchresult": {"idlist": ["38000001"]}}
    sample_fetch_xml = """<?xml version="1.0"?>
    <!DOCTYPE PubmedArticleSet PUBLIC "-//NLM//DTD PubMedArticle, 1st January 2024//EN" "https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_240101.dtd">
    <PubmedArticleSet>
      <PubmedArticle>
        <MedlineCitation>
          <PMID>38000001</PMID>
          <Article>
            <ArticleTitle>Silicon Anode SEI Formation in Solid Electrolytes</ArticleTitle>
            <Abstract>
              <AbstractText>Investigation into SEI stability using cryo-TEM.</AbstractText>
            </Abstract>
            <AuthorList>
              <Author><LastName>Smith</LastName><ForeName>John</ForeName></Author>
            </AuthorList>
          </Article>
        </MedlineCitation>
      </PubmedArticle>
    </PubmedArticleSet>"""

    harvester = PubMedHarvester()
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_search_resp = MagicMock()
        mock_search_resp.status_code = 200
        mock_search_resp.json.return_value = sample_search_json

        mock_fetch_resp = MagicMock()
        mock_fetch_resp.status_code = 200
        mock_fetch_resp.text = sample_fetch_xml

        mock_get.side_effect = [mock_search_resp, mock_fetch_resp]

        results = await harvester.search("silicon anode", max_results=1)
        assert len(results) == 1
        assert results[0].doi == "pubmed:38000001"
        assert "Silicon Anode SEI Formation" in results[0].title
        assert "cryo-TEM" in results[0].summary
        assert "John Smith" in results[0].authors
