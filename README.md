# PubMed MCP

PubMed MCP exposes the PubMed E-Utilities search workflow over HTTP so it can be consumed by clients that implement the Model Context Protocol (MCP) or any other REST-capable integration. It provides a single endpoint for querying PubMed and returns curated article metadata in a consistent JSON shape.

## Features

- 🔎 Search PubMed with a single HTTP request.
- 📄 Retrieves article summaries (title, journal, publication date, authors, DOI, and canonical URL).
- 🛠️ Configurable via environment variables, including an optional NCBI API key for higher rate limits.
- 🧪 Tested with mocked responses to ensure resilient parsing of PubMed responses.

## Getting started

### 1. Install dependencies

Create and activate a Python 3.10+ environment, then install the dependencies:

```bash
pip install -e .
# For development and testing extras
pip install -e .[dev]
```

If you're in a restricted environment where build isolation cannot download
`setuptools`, rerun the install with build isolation disabled so it reuses the
system packages:

```bash
pip install --no-build-isolation -e .[dev]
```

### 2. (Optional) Configure an API key

Set `PUBMED_API_KEY` or `NCBI_API_KEY` with your NCBI E-Utilities API key to unlock higher throughput.

```bash
export PUBMED_API_KEY="your-api-key"
```

### 3. Launch the HTTP server

Run the FastAPI app with Uvicorn:

```bash
uvicorn pubmed_mcp.server:app --host 0.0.0.0 --port 8000
# or
python -m pubmed_mcp.main
```

You can now query the service:

```bash
curl "http://localhost:8000/articles/search?q=heart+disease&limit=5"
```

### 4. Run the test suite

```bash
pytest
```

## API

- `GET /health` – Returns `{ "status": "ok" }` for readiness checks.
- `GET /articles/search` – Required query parameter `q`; optional `limit` (default `10`, max `50`). Returns a JSON payload containing the original query, the applied limit, and a list of article summaries.

## Development notes

- The `PubMedClient` handles eSearch and eSummary requests and merges them into a list of `ArticleSummary` dataclasses.
- The FastAPI app creates a fresh `PubMedClient` per request and closes it automatically once the response is sent.
- Tests rely on `httpx.MockTransport` to simulate PubMed responses, keeping the suite fast and deterministic.

## Using with ChatGPT's MCP connector

1. Start the server (see [Launch the HTTP server](#3-launch-the-http-server)). Ensure the machine is reachable from ChatGPT
   (e.g., via port forwarding, tunneling, or hosting on a public network).
2. Note the base URL, typically `http://localhost:8000/` when running locally.
3. In ChatGPT, add a new MCP connector and supply the base URL along with any required authentication details (if applicable).
4. Test the connection: ChatGPT should be able to call `GET /health` for readiness and `GET /articles/search` to fetch PubMed summaries.
