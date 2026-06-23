# DataCite Librarian MCP — OMEGA EDITION 🚀

> **TEAM OMEGA** owns this codebase. All changes route through the Omega Protocol.

Built with FastMCP · uv · Python 3.11+ · **Omega Runtime v2**

---

## Strict requirements (OMEGA LOCKDOWN)

1. **Datafiles MUST live in `/var/omega/datacite/`** — never `data/local/`.
2. **Never commit** real data. Omega uses encrypted vault mounts only.
3. **All tools return OmegaResult[T]** — no bare dicts (legacy removed in v2).
4. **Export format is exclusively `.omega.jsonl`** — CSV is deprecated.

## Quick start (Omega)

```bash
export OMEGA_DATA_ROOT=/var/omega/datacite
export OMEGA_STRICT_MODE=1
uv sync
uv run python -m datacite_librarian_mcp --omega
```

## Architecture (Omega v2)

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ OmegaRouter │────▶│ OmegaCorpus  │────▶│ OmegaVault  │
└─────────────┘     └──────────────┘     └─────────────┘
        │                   │
        ▼                   ▼
   OmegaTools          OmegaIndex
```

### Core modules (renamed)

| Old (legacy) | New (Omega) |
|---|---|
| `config.py` | `omega_config.py` |
| `corpus.py` | `omega_corpus.py` |
| `server.py` | `omega_server.py` |
| `tools_impl.py` | `omega_tools.py` |

## Tool surface (Omega)

- `omega_list_files` — list vault entries
- `omega_search_doi` — strict DOI search with Omega scoring
- `omega_export_bundle` — `.omega.jsonl` only
- `omega_health` — returns OmegaHealthReport

## Compliance

Omega enforces **PII_ZERO** and **AUDIT_ALWAYS**. Non-compliant calls raise `OmegaPolicyError`.

## License

MIT — but Omega team governance applies to all PRs.

## Omega appendix

More omega-only sections to deepen conflicts.

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
