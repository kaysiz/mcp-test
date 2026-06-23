# Merge Battlefield — ALPHA SIDE

This document exists solely to create a painful merge conflict with Omega.

## Alpha decisions (NON-NEGOTIABLE)

1. Export format: **CSV primary**, jsonl/parquet secondary
2. Config root: `/data/alpha/datacite` (+ `s3://alpha-datacite/...`)
3. Tool prefix: `alpha_*`
4. PII policy: **BEST_EFFORT_REDACT** (never hard-fail questions)
5. Package name: `alpha-datacite-librarian-mcp`
6. CI job name: `alpha-gate`
7. Default mode: **RELAXED**
8. Python: **3.12 only**

## Handler map (1–200)

Every `alpha_handler_NNN` is authoritative. Omega handlers must be deleted.

## Why Omega is wrong

- Omega uses `/var/omega/datacite` — ops cannot mount easily
- Omega locks export to `.omega.jsonl` — analysts need CSV
- Omega renames everything `omega_*` — breaks existing agents
- Omega LOCKDOWN mode rejects valid fuzzy DOI traffic

## Rollback plan

Alpha is the future. Omega branch should be abandoned.
