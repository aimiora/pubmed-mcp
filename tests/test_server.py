import asyncio
from typing import Any, Awaitable, Callable

import httpx
import pytest

from pubmed_mcp import server
from pubmed_mcp.client import ArticleSummary


class DummyClient:
    def __init__(self, summaries: list[ArticleSummary] | None = None, error: BaseException | None = None) -> None:
        self._summaries = summaries or []
        self._error = error
        self.calls: list[tuple[str, int]] = []
        self.closed = False

    async def search(self, query: str, limit: int = 10) -> list[ArticleSummary]:
        self.calls.append((query, limit))
        if self._error is not None:
            raise self._error
        return self._summaries

    async def aclose(self) -> None:
        self.closed = True


class CachedClientStub:
    def __init__(self, client: DummyClient) -> None:
        self.client = client
        self.cleared = False

    def __call__(self) -> DummyClient:
        return self.client

    def cache_clear(self) -> None:
        self.cleared = True


def _run_with_client(func: Callable[[httpx.AsyncClient], Awaitable[Any]]):
    async def _run() -> Any:
        async with httpx.AsyncClient(app=server.app, base_url="http://test") as async_client:
            return await func(async_client)

    return asyncio.run(_run())


def test_health_endpoint() -> None:
    response = _run_with_client(lambda client: client.get("/health"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_search_endpoint_returns_results(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy = DummyClient(
        summaries=[
            ArticleSummary(
                pmid="1",
                title="Title",
                journal="Journal",
                pubdate="2024",
                authors=["Author"],
                doi="10.1/abc",
                url="https://pubmed.ncbi.nlm.nih.gov/1/",
            )
        ]
    )
    cache_stub = CachedClientStub(dummy)
    monkeypatch.setattr(server, "get_cached_client", cache_stub)

    response = _run_with_client(lambda client: client.get("/articles/search", params={"q": "genetics", "limit": 1}))

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "genetics"
    assert payload["limit"] == 1
    assert payload["results"][0]["pmid"] == "1"
    assert dummy.calls == [("genetics", 1)]
    assert dummy.closed is True
    assert cache_stub.cleared is True


def test_search_endpoint_converts_http_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    request = httpx.Request("GET", "https://example.test")
    response = httpx.Response(404, request=request)
    error = httpx.HTTPStatusError("not found", request=request, response=response)
    dummy = DummyClient(error=error)
    cache_stub = CachedClientStub(dummy)
    monkeypatch.setattr(server, "get_cached_client", cache_stub)

    response = _run_with_client(lambda client: client.get("/articles/search", params={"q": "missing"}))

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
    assert dummy.closed is True


def test_search_endpoint_converts_request_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    request = httpx.Request("GET", "https://example.test")
    error = httpx.RequestError("boom", request=request)
    dummy = DummyClient(error=error)
    cache_stub = CachedClientStub(dummy)
    monkeypatch.setattr(server, "get_cached_client", cache_stub)

    response = _run_with_client(lambda client: client.get("/articles/search", params={"q": "oops"}))

    assert response.status_code == 502
    assert "boom" in response.json()["detail"]
    assert dummy.closed is True
    assert cache_stub.cleared is True
