"""Client utilities for interacting with the PubMed E-Utilities API."""
from __future__ import annotations

import os
from dataclasses import dataclass
from types import TracebackType
from typing import Any, Dict, Iterable, List, Optional

import httpx


PUBMED_EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


@dataclass
class ArticleSummary:
    """Lightweight representation of a PubMed article summary."""

    pmid: str
    title: str
    journal: Optional[str]
    pubdate: Optional[str]
    authors: List[str]
    doi: Optional[str]
    url: str


class PubMedClient:
    """Async client for querying PubMed search and summary endpoints."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
        timeout: float = 10.0,
    ) -> None:
        headers = {"User-Agent": "pubmed-mcp/0.1 (+https://github.com/)"}
        params: Dict[str, str] = {}
        if api_key:
            params["api_key"] = api_key
        self._client = http_client or httpx.AsyncClient(headers=headers, timeout=timeout)
        self._owns_client = http_client is None
        self._default_params = params

    @classmethod
    def from_env(cls) -> "PubMedClient":
        """Create a client using environment variables for configuration."""

        api_key = os.getenv("PUBMED_API_KEY") or os.getenv("NCBI_API_KEY")
        return cls(api_key=api_key)

    async def __aenter__(self) -> "PubMedClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def search(self, query: str, *, limit: int = 10) -> List[ArticleSummary]:
        """Search PubMed articles and return structured summaries."""

        if not query or not query.strip():
            raise ValueError("Search query must be a non-empty string.")
        if limit <= 0:
            raise ValueError("Limit must be positive.")

        ids = await self._fetch_ids(query, limit)
        if not ids:
            return []
        summaries = await self._fetch_summaries(ids)
        return [self._build_summary(uid, summaries[uid]) for uid in ids if uid in summaries]

    async def _fetch_ids(self, query: str, limit: int) -> List[str]:
        params = {
            "db": "pubmed",
            "retmode": "json",
            "retmax": str(limit),
            "term": query,
            "sort": "relevance",
        }
        params.update(self._default_params)
        response = await self._client.get(f"{PUBMED_EUTILS_BASE}/esearch.fcgi", params=params)
        response.raise_for_status()
        data = response.json()
        try:
            return data["esearchresult"]["idlist"]
        except KeyError as exc:
            raise RuntimeError("Unexpected response structure from PubMed search.") from exc

    async def _fetch_summaries(self, ids: Iterable[str]) -> Dict[str, Any]:
        id_param = ",".join(ids)
        params = {
            "db": "pubmed",
            "retmode": "json",
            "id": id_param,
        }
        params.update(self._default_params)
        response = await self._client.get(f"{PUBMED_EUTILS_BASE}/esummary.fcgi", params=params)
        response.raise_for_status()
        data = response.json()
        result = data.get("result", {})
        # The result includes a "uids" key listing IDs; we can rely on dictionary entries.
        return {uid: result.get(uid, {}) for uid in result.get("uids", [])}

    def _build_summary(self, uid: str, data: Dict[str, Any]) -> ArticleSummary:
        authors = [author.get("name") for author in data.get("authors", []) if author.get("name")]
        doi = None
        for article_id in data.get("articleids", []):
            if article_id.get("idtype") == "doi":
                doi = article_id.get("value")
                break
        return ArticleSummary(
            pmid=uid,
            title=data.get("title", ""),
            journal=data.get("fulljournalname") or data.get("source"),
            pubdate=data.get("pubdate"),
            authors=authors,
            doi=doi,
            url=f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
        )


__all__ = ["PubMedClient", "ArticleSummary"]
