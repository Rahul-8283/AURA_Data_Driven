import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, call, patch

from app.core.config import settings
from app.services.harvesters import (
    ArxivHarvester,
    BaseHarvester,
    CrossrefHarvester,
    HarvestedDocument,
    HarvesterError,
    LiteratureDeduplicator,
    PubMedHarvester,
    WikipediaHarvester,
    is_battery_relevant,
    title_key,
)
from app.services.harvesters.arxiv import build_search_query
from app.services.harvesters.base import build_user_agent


def _response(status=200, text="", payload=None):
    resp = MagicMock()
    resp.status_code = status
    resp.text = text
    resp.json.return_value = payload if payload is not None else {}
    return resp


# --- PubMed text extraction and safe XML parsing ---------------------------------------------

PUBMED_FETCH = """<?xml version="1.0"?>
<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>1</PMID><Article>
<ArticleTitle>Stabilizing LiNi<sub>0.8</sub>Co<sub>0.1</sub>Mn<sub>0.1</sub>O<sub>2</sub> cathodes by Mg doping</ArticleTitle>
<Abstract>
<AbstractText Label="BACKGROUND">Layered LiNi<sub>0.8</sub>Co<sub>0.1</sub>Mn<sub>0.1</sub>O<sub>2</sub> delivers over 200 mAh/g.</AbstractText>
<AbstractText Label="RESULTS">Mg doping suppresses <i>cation mixing</i> during cycling.</AbstractText>
</Abstract></Article></MedlineCitation></PubmedArticle></PubmedArticleSet>"""


@pytest.mark.asyncio
async def test_pubmed_keeps_chemical_formulas_inside_inline_markup():
    search = _response(payload={"esearchresult": {"idlist": ["1"]}})
    fetch = _response(text=PUBMED_FETCH)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=[search, fetch]):
        docs = await PubMedHarvester().search("mg doping", max_results=1)

    assert docs[0].title == "Stabilizing LiNi0.8Co0.1Mn0.1O2 cathodes by Mg doping"
    assert "LiNi0.8Co0.1Mn0.1O2 delivers over 200 mAh/g" in docs[0].summary
    assert "BACKGROUND:" in docs[0].summary and "cation mixing" in docs[0].summary


@pytest.mark.asyncio
async def test_entity_expansion_attack_is_rejected_not_parsed():
    bomb = ('<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">'
            '<!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">]>'
            "<PubmedArticleSet>&lol2;</PubmedArticleSet>")
    search = _response(payload={"esearchresult": {"idlist": ["1"]}})
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=[search, _response(text=bomb)]):
        with pytest.raises(HarvesterError):
            await PubMedHarvester().search("anything")


# --- arXiv query construction ----------------------------------------------------------------

def test_arxiv_query_binds_every_term_and_scopes_to_materials_categories():
    query = build_search_query("lithium dendrite suppression")

    assert query.startswith("(all:lithium AND all:dendrite AND all:suppression)")
    assert "cat:cond-mat.mtrl-sci" in query


def test_arxiv_query_strips_syntax_characters_and_caps_terms():
    query = build_search_query('lithium" OR all:secret (x) ' + " ".join(f"t{i}" for i in range(20)))

    keywords = query.split(") AND (")[0].lstrip("(")
    assert '"' not in keywords and "(" not in keywords
    assert keywords.count("all:") == 8
    assert build_search_query("   !!! ") == ""


@pytest.mark.asyncio
async def test_arxiv_sends_the_scoped_query():
    feed = '<feed xmlns="http://www.w3.org/2005/Atom"></feed>'
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=_response(text=feed)) as mock_get:
        await ArxivHarvester().search("solid electrolyte", max_results=3)

    assert mock_get.await_args.kwargs["params"]["search_query"].startswith("(all:solid AND all:electrolyte)")


# --- failures are reported, not swallowed ----------------------------------------------------

HARVESTERS = [ArxivHarvester, CrossrefHarvester, PubMedHarvester, WikipediaHarvester]


@pytest.mark.asyncio
@pytest.mark.parametrize("harvester_cls", HARVESTERS)
async def test_bad_status_raises_harvester_error(harvester_cls):
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=_response(status=503)):
        with pytest.raises(HarvesterError, match="503"):
            await harvester_cls().search("lithium battery")


@pytest.mark.asyncio
@pytest.mark.parametrize("harvester_cls", HARVESTERS)
async def test_network_failure_raises_harvester_error_without_leaking_the_url(harvester_cls):
    failure = httpx.ConnectError("could not reach https://host/?api_key=SECRET-NCBI-KEY")
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=failure):
        with pytest.raises(HarvesterError) as excinfo:
            await harvester_cls().search("lithium battery")

    assert "SECRET-NCBI-KEY" not in str(excinfo.value)
    assert "ConnectError" in str(excinfo.value)


# --- relevance filter ------------------------------------------------------------------------

@pytest.mark.parametrize("title,summary,expected", [
    ("Cobalt-free cathode materials", "A layered oxide cathode with high capacity.", True),
    ("Lithium dendrite growth", "Dendrite suppression in lithium metal electrodes.", True),
    ("Lithium treatment in bipolar disorder", "A clinical trial of lithium dosing in patients.", False),
    ("Taylor Swift", "An American singer-songwriter known for narrative songs.", False),
    ("Sodium intake", "Dietary sodium and blood pressure.", False),
])
def test_battery_relevance(title, summary, expected):
    assert is_battery_relevant(title, summary) is expected


@pytest.mark.asyncio
async def test_harvest_drops_off_topic_documents():
    class Fixed(BaseHarvester):
        async def search(self, query, max_results=10):
            return [
                HarvestedDocument(title="Solid-state battery electrolytes", summary="x" * 60, doi="d1", source="t"),
                HarvestedDocument(title="Medieval pottery", summary="x" * 60, doi="d2", source="t"),
            ]

    docs = await Fixed(user_agent="t").harvest("anything")

    assert [d.doi for d in docs] == ["d1"]


# --- cross-source deduplication --------------------------------------------------------------

def test_title_key_ignores_case_punctuation_and_spacing():
    assert title_key("Li-Ion  Cathodes: A Review!") == title_key("li ion cathodes a review")
    assert title_key("Li-Ion Cathodes") != title_key("Na-Ion Cathodes")
    assert title_key("!!!") == ""


def test_same_paper_from_another_source_is_detected_by_title():
    store = MagicMock()
    store.exists.side_effect = lambda doi=None, title_key=None: title_key is not None
    dedup = LiteratureDeduplicator(store=store)

    assert dedup.is_already_indexed("arxiv:2401.1", "Doped LFP Cathodes") is True
    assert store.exists.call_args_list == [
        call(doi="arxiv:2401.1"),
        call(title_key=title_key("Doped LFP Cathodes")),
    ]


def test_document_without_doi_or_title_is_never_a_duplicate():
    store = MagicMock()
    assert LiteratureDeduplicator(store=store).is_already_indexed("", None) is False
    store.exists.assert_not_called()


# --- contact email ---------------------------------------------------------------------------

def test_no_contact_email_means_no_fake_address_is_sent(monkeypatch):
    monkeypatch.setattr(settings, "CONTACT_EMAIL", "")

    assert build_user_agent() == "AURA-BatteryResearch/1.0"


@pytest.mark.asyncio
@pytest.mark.parametrize("email,expect_mailto", [("", False), ("me@example.org", True)])
async def test_crossref_mailto_only_when_configured(monkeypatch, email, expect_mailto):
    monkeypatch.setattr(settings, "CONTACT_EMAIL", email)
    payload = {"message": {"items": []}}
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=_response(payload=payload)) as mock_get:
        await CrossrefHarvester().search("cathode")

    assert ("mailto" in mock_get.await_args.kwargs["params"]) is expect_mailto
