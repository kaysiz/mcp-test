# DataCite Librarian MCP (`mcp-test`)-test

Local **[Model Context Protocol](https://modelcontextprotocol.io)** server for the DataCite community: **repository QA**, **funder compliance**, **CSV index analytics**, **search/facets**, and **exports** over [DataCite](https://datacite.org) **monthly** and **public** datafiles you host on disk.

Built with [FastMCP](https://gofastmcp.com) · [uv](https://docs.astral.sh/uv/) · Python 3.12+ · MIT

> **This repository does not ship production datafiles.** You must download them yourself and keep them outside git (see below). CI runs only against a small **mock** corpus.

---

## Strict requirements

1. **You must obtain datafiles from DataCite**, not from this repo.
2. **Never commit** real `part_*.jsonl.gz`, `YYYY-MM.csv.gz`, TAR archives, or monthly/public extracts. They are **gitignored** under `data/local/` and at the repo root.
3. **Set `DATACITE_DATA_DIR`** to your extracted data directory. If the variable is set but the path does not exist, the MCP **errors** (it does not silently use mock data).
4. **Mock data is for demos/tests only** (or when `DATACITE_DATA_DIR` is unset / `DATACITE_USE_MOCK=1`). It is not a substitute for real monthly/public files.
5. **Aggregate tools scan a limited number of records** by default (`DATACITE_MAX_RECORDS`, default `10000`). Always inspect `truncated`, `scan_limit`, and (for indexes) `coverage_pct` so you do not treat a sample as the full corpus.
6. **Metadata vs index:** a `YYYY-MM.csv.gz` index can list hundreds of thousands of DOIs; you need the matching `part_*.jsonl.gz` files for full QA/search. Use `coverage_report` to measure the gap.
7. **Respect DataCite access terms:** the **public** annual file is openly documented; the **monthly** file is for **DataCite Members and Consortium Organizations** (authenticated S3 access). See official docs linked below.

---

## Obtain DataCite datafiles (official documentation)

Follow **only** DataCite’s documentation and portals. Do not rely on third-party mirrors unless you trust them and accept their terms.

| Resource | URL |
|----------|-----|
| **Data files portal** | [https://datafiles.datacite.org](https://datafiles.datacite.org) |
| **Public data file** (annual, public DOIs; documented for open use) | [DataCite Support — Public Data File](https://support.datacite.org/docs/datacite-public-data-file) |
| **Monthly data file** (members/consortium; S3 + credentials) | [DataCite Support — Monthly Data File](https://support.datacite.org/docs/datacite-monthly-data-file) |
| **XML ↔ JSON mapping** (record shape) | [DataCite Support — XML to JSON](https://support.datacite.org/docs/datacite-xml-to-json-mapping) |
| **Metadata schema** | [https://schema.datacite.org](https://schema.datacite.org) |

### High-level download steps (summary only — details are on Support)

**Public annual file**

1. Open [datafiles.datacite.org](https://datafiles.datacite.org) and locate the latest **public** release (e.g. `public-2025`).
2. Download the TAR (or equivalent) per the [Public Data File](https://support.datacite.org/docs/datacite-public-data-file) page.
3. Extract locally to a directory **you** control (recommended: this repo’s `data/local/`, which is gitignored).
4. Confirm you see something like `dois/updated_YYYY-MM/part_*.jsonl.gz` and/or monthly `YYYY-MM.csv.gz` indexes inside the extract.

**Monthly file (members)**

1. Confirm your organization is a DataCite Member or Consortium participant.
2. Follow [Monthly Data File](https://support.datacite.org/docs/datacite-monthly-data-file) for temporary AWS credentials and S3 access.
3. Sync/extract to `data/local/` (or another path outside git).
4. Point `DATACITE_DATA_DIR` at that root.

**After download — required layout for this MCP**

Preferred (matches DataCite releases):

```text
data/local/                    # or any path you pass as DATACITE_DATA_DIR
  STATUS.json                  # optional
  MANIFEST.json                # optional
  dois/
    updated_2026-06/
      2026-06.csv.gz           # index: doi, state, client_id, updated
      part_0000.jsonl.gz       # full metadata (~10k records/part typical)
      part_0001.jsonl.gz
      …
```

Also supported (experimental/flat):

```text
data/local/
  2026-06.csv.gz
  part_0000.jsonl.gz
```

See [data/local/README.md](data/local/README.md) and [docs/DATAFILE_SCHEMA.md](docs/DATAFILE_SCHEMA.md).

---

## Quick start (development)

### Prerequisites

- Python **3.12+**
- [uv](https://docs.astral.sh/uv/)

### Install

```bash
git clone <this-repo-url> mcp-test
cd mcp-test
uv sync --all-groups
```

### Run MCP (stdio — for Cursor / Claude Desktop / other MCP hosts)

```bash
# Demo/mock only (no real datafiles)
uv run datacite-librarian-mcp

# Production/local datafiles (STRICT: path must exist)
export DATACITE_DATA_DIR="/absolute/path/to/data/local"
export DATACITE_MAX_RECORDS=20000   # optional; raise for fuller scans
uv run datacite-librarian-mcp
```

Example MCP host config (`mcp.json` pattern):

```json
{
  "mcpServers": {
    "datacite-librarian": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/mcp-test",
        "datacite-librarian-mcp"
      ],
      "env": {
        "DATACITE_DATA_DIR": "/absolute/path/to/mcp-test/data/local",
        "DATACITE_MAX_RECORDS": "20000"
      }
    }
  }
}
```

### Run MCP (HTTP, local testing)

```bash
export DATACITE_DATA_DIR="/absolute/path/to/data/local"
uv run python -c "from datacite_librarian_mcp.server import mcp; mcp.run(transport='http', host='127.0.0.1', port=8765)"
```

### Natural-language REPL (maps questions → tools; not a full LLM)

```bash
export DATACITE_DATA_DIR="/absolute/path/to/data/local"
uv run datacite-librarian-chat
# or: uv run python scripts/interactive_client.py
```

Examples: `how many DOIs?`, `how many funders?`, `repository health for zenodo`, `funder compliance for European Commission`.

---

## Who this is for

| Audience | Start with |
|----------|------------|
| Librarians / RDM | `community_guide`, `repository_health`, `export_health_issues` |
| Research offices | `funder_compliance`, `export_funder_issues` |
| Repository operators | `index_summary`, `index_client`, `coverage_report` |
| Bibliometrics / policy | `facets`, `top_subjects`, `index_summary` (report `truncated`) |
| Developers | `server_info`, mock corpus, tests |
| Teachers | `datacite-librarian-chat`, mock data |

Call **`community_guide`** from any MCP client for persona-oriented workflows.

---

## Tools (summary)

**Discovery:** `community_guide`, `server_info`, `corpus_status`, `corpus_inventory`, `diff_partitions_summary`  

**Metadata QA / compliance** (needs `part_*.jsonl.gz`): `repository_health`, `funder_compliance`, `search_dois`, `get_doi`, `check_doi_qa`, `list_clients`, `list_funders`  

**Analytics:** `facets`, `top_subjects`  

**CSV index only** (no JSONL required): `index_summary`, `index_client`, `coverage_report`  

**Exports** (writes under `exports/` or `DATACITE_EXPORT_DIR`): `export_health_issues`, `export_funder_issues`, `export_search_results`  

**Ops:** `regenerate_mock_data`

---

## Configuration

| Variable | Purpose |
|----------|---------|
| `DATACITE_DATA_DIR` | Corpus root (**must exist** if set) |
| `DATACITE_USE_MOCK` | `1` / `true` forces mock corpus |
| `DATACITE_MOCK_DIR` | Override mock write/read location |
| `DATACITE_MAX_RECORDS` | Aggregate scan ceiling (default `10000`) |
| `DATACITE_DOI_LOOKUP_MAX_SCAN` | `get_doi` ceiling; `0` = full local scan |
| `DATACITE_EXPORT_DIR` | Export output directory |

---

## Development & CI

```bash
uv sync --all-groups
uv run pytest
uv run ruff check src tests
```

GitHub Actions (`.github/workflows/ci.yml`) runs **ruff** + **pytest** on Python 3.12 and 3.13 with `DATACITE_USE_MOCK=1` only—no real datafiles in CI.

Project docs:

- [docs/DATAFILE_SCHEMA.md](docs/DATAFILE_SCHEMA.md) — file/record schema notes  
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) — contributor workflow  
- [data/local/README.md](data/local/README.md) — where to put downloads  

---

## Design principles

1. **Local-first** — organizations keep datafiles; this project never distributes bulk DOI corpora.  
2. **Stream-read** — gzip JSONL/CSV line-by-line; suitable for large files without a database.  
3. **Light dependencies** — `fastmcp` + `pydantic` (+ stdlib).  
4. **Honest limits** — `truncated`, `scan_limit`, `coverage_pct` on tool outputs.  
5. **Index without metadata** — CSV tools help before all `part_*.jsonl.gz` are downloaded.

---

## License

MIT — see [LICENSE](LICENSE).

DataCite bulk **metadata** licensing and access are governed by DataCite (public file documentation typically describes CC0 for metadata; **confirm on Support**). Member monthly access may be restricted. This software does not redistribute production datafiles.

---

## Links

- [Data files portal](https://datafiles.datacite.org)  
- [Public data file docs](https://support.datacite.org/docs/datacite-public-data-file)  
- [Monthly data file docs](https://support.datacite.org/docs/datacite-monthly-data-file)  
- [DataCite Metadata Schema](https://schema.datacite.org)  
- [MCP specification](https://modelcontextprotocol.io)  
- [FastMCP](https://gofastmcp.com)
