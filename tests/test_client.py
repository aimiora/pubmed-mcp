import asyncio
from typing import Any

import httpx
import pytest

from pubmed_mcp.client import PubMedClient


def _build_mock_transport(esearch_payload: dict[str, Any], esummary_payload: dict[str, Any]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("esearch.fcgi"):
            return httpx.Response(200, json=esearch_payload)
        if request.url.path.endswith("esummary.fcgi"):
            return httpx.Response(200, json=esummary_payload)
        raise AssertionError(f"Unexpected URL requested: {request.url}")

    return httpx.MockTransport(handler)


def test_search_returns_summaries() -> None:
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

    transport = _build_mock_transport(esearch_payload, esummary_payload)
    http_client = httpx.AsyncClient(transport=transport)
    client = PubMedClient(http_client=http_client)

    async def run_search() -> list:
        try:
            return await client.search("cancer", limit=5)
        finally:
            await http_client.aclose()

    results = asyncio.run(run_search())

    assert len(results) == 2
    assert results[0].pmid == "123"
    assert results[0].doi == "10.1000/test"
    assert results[1].journal == "Testing Reports"


def test_search_rejects_blank_query() -> None:
    client = PubMedClient()

    async def run_blank_search() -> None:
        try:
            await client.search("  ")
        finally:
            await client.aclose()

    with pytest.raises(ValueError):
        asyncio.run(run_blank_search())
