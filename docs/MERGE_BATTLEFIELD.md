# Merge Battlefield — MERGED RESOLUTION

Both Alpha and Omega branches were merged. This is the negotiated (messy) outcome.

## Decisions (HYBRID)

| Topic | Omega wanted | Alpha wanted | Merged |
|---|---|---|---|
| Export | `.omega.jsonl` only | CSV primary | Both via `EXPORT_FORMAT` / team tools |
| Data root | `/var/omega/datacite` | `/data/alpha/datacite` | Both env vars supported |
| Tools | `omega_*` | `alpha_*` | **Both** registered on server |
| PII | PII_ZERO hard fail | BEST_EFFORT_REDACT | Runtime team selects; default `both` warns |
| Package | `omega-datacite-librarian-mcp` | `alpha-datacite-librarian-mcp` | `datacite-librarian-mcp` |
| CI | `omega-gate` | `alpha-gate` | **Both jobs** in `merged-ci` |
| Python | 3.11+ | 3.12 only | `>=3.11` with alpha job on 3.12 |

## Handlers

`merge_battlefield.py` now contains **both** `omega_handler_NNN` and `alpha_handler_NNN` for N=1..200.

## Rollback plan

Re-split into `RUNTIME_TEAM=omega` or `RUNTIME_TEAM=alpha` rather than reverting history.
