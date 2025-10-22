"""HTTP server exposing PubMed search functionality."""
from __future__ import annotations

import functools
from typing import List

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from .client import ArticleSummary, PubMedClient


def _get_client() -> PubMedClient:
    return PubMedClient.from_env()


@functools.lru_cache
def get_cached_client() -> PubMedClient:
    return _get_client()


async def get_client_dependency() -> PubMedClient:
    return get_cached_client()


class ArticleSummaryModel(BaseModel):
    pmid: str = Field(..., description="PubMed identifier")
    title: str
    journal: str | None = None
    pubdate: str | None = None
    authors: List[str] = Field(default_factory=list)
    doi: str | None = None
    url: str

    @classmethod
    def from_summary(cls, summary: ArticleSummary) -> "ArticleSummaryModel":
        return cls(**summary.__dict__)


class SearchResponse(BaseModel):
    query: str
    limit: int
    results: List[ArticleSummaryModel]


app = FastAPI(
    title="PubMed MCP",
    description="Search PubMed articles and retrieve structured summaries.",
    version="0.1.0",
)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    client = get_cached_client()
    await client.aclose()
    get_cached_client.cache_clear()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/articles/search", response_model=SearchResponse)
async def search_articles(
    q: str = Query(..., min_length=1, description="PubMed search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results to return"),
    client: PubMedClient = Depends(get_client_dependency),
) -> SearchResponse:
    try:
        summaries = await client.search(q, limit=limit)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=str(exc)) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - generic safeguard
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return SearchResponse(
        query=q,
        limit=limit,
        results=[ArticleSummaryModel.from_summary(summary) for summary in summaries],
    )


# Provide an ASGI-compatible callable for uvicorn
application = app
