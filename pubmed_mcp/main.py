"""Command-line entry point for running the PubMed MCP server."""

import uvicorn


def run() -> None:
    uvicorn.run(
        "pubmed_mcp.server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        factory=False,
    )


if __name__ == "__main__":
    run()
