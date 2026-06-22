# Development guide

## Prerequisites

- **Python 3.12+** (pinned via `.python-version`)
- **[uv](https://docs.astral.sh/uv/)** for environments and dependencies

Install uv if needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Clone and install

```bash
git clone <this-repo-url> datacite-librarian-mcp
cd datacite-librarian-mcp
uv sync --all-groups
```

This creates `.venv/`, installs runtime deps (`fastmcp`, `pydantic`) and dev deps
(`pytest`, `ruff`).

## Project layout

```
d-mcp/
├── pyproject.toml
├── uv.lock
├── README.md
├── LICENSE
├── docs/
│   ├── DATAFILE_SCHEMA.md      # DataCite file & record schema
│   └── DEVELOPMENT.md          # This file
├── data/
│   └── mock/                   # Auto-generated mock monthly-style corpus
├── src/datacite_librarian_mcp/
│   ├── __init__.py
│   ├── __main__.py             # python -m datacite_librarian_mcp
│   ├── server.py               # FastMCP app, tools, resources
│   ├── config.py               # DATACITE_* env resolution
│   ├── models.py               # Pydantic models & record summaries
│   ├── stream_reader.py        # Streaming JSONL/CSV/TAR helpers
│   ├── qa.py                   # Repository QA engine
│   ├── compliance.py           # Funder compliance engine
│   └── mock_data.py            # Mock corpus generator
└── tests/
    ├── test_stream_reader.py
    ├── test_qa.py
    ├── test_compliance.py
    └── test_server_tools.py
```

## Run the MCP server locally

```bash
# Zero-config: uses / regenerates data/mock
uv run datacite-librarian-mcp

# Or module form
uv run python -m datacite_librarian_mcp

# Against a real extracted datafile
export DATACITE_DATA_DIR=/path/to/extracted/public-or-monthly
uv run datacite-librarian-mcp
```

The server speaks MCP over stdio by default (FastMCP `mcp.run()`), suitable for
Claude Desktop, Cursor, VS Code Copilot, and other MCP hosts.

### Example MCP host config (stdio)

```json
{
  "mcpServers": {
    "datacite-librarian": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/d-mcp", "datacite-librarian-mcp"],
      "env": {
        "DATACITE_DATA_DIR": "/absolute/path/to/datacite-datafile-root"
      }
    }
  }
}
```

For mock-only demos, omit `DATACITE_DATA_DIR` or set `"DATACITE_USE_MOCK": "1"`.

## Regenerate mock data

```bash
uv run python -m datacite_librarian_mcp.mock_data
```

Writes `data/mock/` with `STATUS.json`, `MANIFEST.json`, and one partition of
gzipped JSONL + CSV index.

## Tests

```bash
uv run pytest
uv run pytest -q
uv run pytest tests/test_qa.py -v
```

Tests write temporary corpora under pytest `tmp_path`; they do not require
network access.

## Lint / format

```bash
uv run ruff check src tests
uv run ruff format src tests
```

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATACITE_DATA_DIR` | *(unset → mock)* | Root of extracted monthly/public datafile; **must exist if set** (raises/tools error otherwise) |
| `DATACITE_USE_MOCK` | unset | If `1`/`true`, force mock corpus |
| `DATACITE_MOCK_DIR` | auto | Writable mock corpus location (checkout `data/mock`, else user data / temp) |
| `DATACITE_MAX_RECORDS` | `10000` | Default scan ceiling for aggregate tools |
| `DATACITE_DOI_LOOKUP_MAX_SCAN` | `0` (unlimited) | Optional ceiling for `get_doi` / `check_doi_qa` |

## Design principles

1. **Stream everything** — gzip JSONL line-by-line; never `read()` whole files.
2. **Light dependencies** — only `fastmcp` + `pydantic` (+ stdlib). No database,
   no pandas, no heavy search engine in v0.1.
3. **Agent-safe outputs** — summaries, issue lists, and caps (`max_records`,
   sample sizes) instead of dumping full records.
4. **Librarian workflows first** — repository health + funder compliance over
   generic search APIs.
5. **Runnable offline** — mock corpus for CI/demos; real datafiles are user-supplied.

## Adding a new QA check

1. Extend `check_record()` in `qa.py` with a new `QaIssue` (`code`, `category`, `severity`).
2. If it affects aggregates, optionally increment a completeness key in `scan_repository_health()`.
3. Add a fixture pattern in `mock_data.py` that triggers the issue.
4. Add/adjust a test in `tests/test_qa.py`.

## Adding a new MCP tool

1. Decorate a function in `server.py` with `@mcp.tool`.
2. Keep parameters JSON-serializable primitives; return `dict` or Pydantic `.model_dump()`.
3. Stream via `iter_corpus_records(_data_dir(), max_records=...)`.
4. Document the tool in `README.md` tools table.
5. Smoke-test in `tests/test_server_tools.py`.

## Release checklist

- [ ] `uv lock` committed and `uv sync` clean
- [ ] `uv run pytest` green
- [ ] `uv run ruff check src tests` clean
- [ ] Version bump in `pyproject.toml` and `__init__.__version__`
- [ ] README / schema docs updated if tools or layout changed

## Licensing

Code: MIT (see `LICENSE`).  
DataCite **metadata** in real datafiles: typically CC0 — confirm on DataCite Support.
Mock data is synthetic and carries no third-party rights.
