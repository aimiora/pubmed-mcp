from typing import Any

import pytest
import respx

from pubmed_mcp.client import PubMedClient


@pytest.mark.anyio
async def test_search_returns_summaries() -> None:
    client = PubMedClient()

    esearch_payload: dict[str, Any] = {
        "esearchresult": {
            "idlist": ["123", "456"],
        }
    }
    esummary_payload: dict[str, Any] = {
        "result": {
            "uids": ["123", "456"],
            "123": {
                "title": "Sample Article",
                "fulljournalname": "Journal of Testing",
                "pubdate": "2024 Jan",
                "authors": [{"name": "Doe J"}],
                "articleids": [{"idtype": "doi", "value": "10.1000/test"}],
            },
            "456": {
                "title": "Another Article",
                "source": "Testing Reports",
                "pubdate": "2023 Feb",
                "authors": [],
                "articleids": [],
            },
        }
    }

    with respx.mock(assert_all_called=True) as mock:
        mock.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi").respond(
            json=esearch_payload
        )
        mock.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi").respond(
            json=esummary_payload
        )

        results = await client.search("cancer", limit=5)

    await client.aclose()

    assert len(results) == 2
    assert results[0].pmid == "123"
    assert results[0].doi == "10.1000/test"
    assert results[1].journal == "Testing Reports"


@pytest.mark.anyio
async def test_search_rejects_blank_query() -> None:
    client = PubMedClient()
    with pytest.raises(ValueError):
        await client.search("  ")
    await client.aclose()
