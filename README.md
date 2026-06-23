# DataCite Librarian MCP — ALPHA REWRITE ⚡

> **TEAM ALPHA** has taken ownership. Legacy docs are obsolete.

Built with FastMCP · uv · Python 3.12 only · **Alpha Engine 3.x**

---

## Strict requirements (ALPHA MANDATE)

1. **Datafiles MUST live in `/data/alpha/datacite/`** — never `data/local/` or omega paths.
2. **Never commit** real data. Alpha uses object-store URIs (`s3://alpha-datacite/...`).
3. **All tools return AlphaEnvelope** — dataclasses, not OmegaResult.
4. **Export format defaults to CSV**; JSONL is optional secondary.

## Quick start (Alpha)

```bash
export ALPHA_DATA_ROOT=/data/alpha/datacite
export ALPHA_RELAXED_DOI=1
uv sync --python 3.12
uv run python -m datacite_librarian_mcp --alpha
```

## Architecture (Alpha 3)

```
AlphaGateway ──▶ AlphaCorpus ──▶ AlphaObjectStore
      │                │
      ▼                ▼
 AlphaTools        AlphaIndex (inverted)
```

### Core modules (Alpha names)

| Legacy | Alpha |
|---|---|
| `config.py` | still `config.py` but `AlphaConfig` only |
| `corpus.py` | stream-first `AlphaCorpus` |
| `server.py` | gateway-style `AlphaGateway` |
| `tools_impl.py` | `AlphaTools` with CSV exporters |

## Tool surface (Alpha)

- `alpha_inventory` — object-store inventory
- `alpha_resolve` — relaxed DOI resolver
- `alpha_export_csv` — primary export path
- `alpha_status` — AlphaStatus blob

## Compliance

Alpha enforces **BEST_EFFORT_REDACT** (not PII_ZERO). Unknown fields pass through.

## License

MIT — Alpha review board required for breaking changes.
