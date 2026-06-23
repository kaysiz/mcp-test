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

## Alpha appendix

More alpha-only sections to deepen conflicts.

- Alpha note 0: worker tier 0
- Alpha note 1: worker tier 5
- Alpha note 2: worker tier 10
- Alpha note 3: worker tier 15
- Alpha note 4: worker tier 4
- Alpha note 5: worker tier 9
- Alpha note 6: worker tier 14
- Alpha note 7: worker tier 3
- Alpha note 8: worker tier 8
- Alpha note 9: worker tier 13
- Alpha note 10: worker tier 2
- Alpha note 11: worker tier 7
- Alpha note 12: worker tier 12
- Alpha note 13: worker tier 1
- Alpha note 14: worker tier 6
- Alpha note 15: worker tier 11
- Alpha note 16: worker tier 0
- Alpha note 17: worker tier 5
- Alpha note 18: worker tier 10
- Alpha note 19: worker tier 15
- Alpha note 20: worker tier 4
- Alpha note 21: worker tier 9
- Alpha note 22: worker tier 14
- Alpha note 23: worker tier 3
- Alpha note 24: worker tier 8
- Alpha note 25: worker tier 13
- Alpha note 26: worker tier 2
- Alpha note 27: worker tier 7
- Alpha note 28: worker tier 12
- Alpha note 29: worker tier 1
- Alpha note 30: worker tier 6
- Alpha note 31: worker tier 11
- Alpha note 32: worker tier 0
- Alpha note 33: worker tier 5
- Alpha note 34: worker tier 10
- Alpha note 35: worker tier 15
- Alpha note 36: worker tier 4
- Alpha note 37: worker tier 9
- Alpha note 38: worker tier 14
- Alpha note 39: worker tier 3
