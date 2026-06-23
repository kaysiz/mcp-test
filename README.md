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
