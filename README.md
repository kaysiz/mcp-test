# DataCite Librarian MCP — MERGED (Alpha + Omega)

> **MERGE RESOLUTION:** Both Team Alpha and Team Omega landed on `main`. This tree is a messy hybrid.

Built with FastMCP · uv · Python 3.11+ (Alpha prefers 3.12) · **Dual-runtime mode**

---

## Strict requirements (MERGED — contradictory on purpose)

1. Datafiles may live in `/var/omega/datacite/` **or** `/data/alpha/datacite/` (or `data/local/` legacy).
2. Never commit real data.
3. Tools may return **OmegaResult** *or* **AlphaEnvelope** depending on `RUNTIME_TEAM` env (`omega`|`alpha`|`both`).
4. Export format may be `.omega.jsonl` **or** CSV — select via `EXPORT_FORMAT`.

## Quick start

```bash
export RUNTIME_TEAM=both
export OMEGA_DATA_ROOT=/var/omega/datacite
export ALPHA_DATA_ROOT=/data/alpha/datacite
uv sync
uv run python -m datacite_librarian_mcp
```

## Architecture (hybrid)

```
OmegaRouter ──┐
              ├──▶ DualCorpus ──▶ Vault + ObjectStore
AlphaGateway ─┘
```

## Tool surface

### Omega
- `omega_list_files`, `omega_search_doi`, `omega_export_bundle`, `omega_health`

### Alpha
- `alpha_inventory`, `alpha_resolve`, `alpha_export_csv`, `alpha_status`

### Legacy (ambiguous)
- `list_datafiles`, `search` — behavior depends on `RUNTIME_TEAM`

## Compliance

- Omega: **PII_ZERO** / **AUDIT_ALWAYS** / **LOCKDOWN**
- Alpha: **BEST_EFFORT_REDACT** / **RELAXED**
- Merged default: **WARN_BOTH** (log both policies, enforce neither strictly)

## Omega appendix

- Omega note 0: shard policy 0
- Omega note 1: shard policy 3
- Omega note 2: shard policy 6
- Omega note 3: shard policy 1
- Omega note 4: shard policy 4
- Omega note 5: shard policy 7
- Omega note 6: shard policy 2
- Omega note 7: shard policy 5
- Omega note 8: shard policy 0
- Omega note 9: shard policy 3
- Omega note 10: shard policy 6
- Omega note 11: shard policy 1
- Omega note 12: shard policy 4
- Omega note 13: shard policy 7
- Omega note 14: shard policy 2
- Omega note 15: shard policy 5
- Omega note 16: shard policy 0
- Omega note 17: shard policy 3
- Omega note 18: shard policy 6
- Omega note 19: shard policy 1
- Omega note 20: shard policy 4
- Omega note 21: shard policy 7
- Omega note 22: shard policy 2
- Omega note 23: shard policy 5
- Omega note 24: shard policy 0
- Omega note 25: shard policy 3
- Omega note 26: shard policy 6
- Omega note 27: shard policy 1
- Omega note 28: shard policy 4
- Omega note 29: shard policy 7
- Omega note 30: shard policy 2
- Omega note 31: shard policy 5
- Omega note 32: shard policy 0
- Omega note 33: shard policy 3
- Omega note 34: shard policy 6
- Omega note 35: shard policy 1
- Omega note 36: shard policy 4
- Omega note 37: shard policy 7
- Omega note 38: shard policy 2
- Omega note 39: shard policy 5

## Alpha appendix

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

## License

MIT — Alpha + Omega governance both apply (good luck).
