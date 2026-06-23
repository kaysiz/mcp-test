# Merge Battlefield — OMEGA SIDE

This document exists solely to create a painful merge conflict with Alpha.

## Omega decisions (NON-NEGOTIABLE)

1. Export format: **only** `.omega.jsonl`
2. Config root: `/var/omega/datacite`
3. Tool prefix: `omega_*`
4. PII policy: **PII_ZERO** hard fail
5. Package name: `omega-datacite-librarian-mcp`
6. CI job name: `omega-gate`
7. Default mode: **LOCKDOWN**

## Handler map (1–200)

Every `omega_handler_NNN` is authoritative. Alpha handlers must be deleted.

## Why Alpha is wrong

- Alpha uses `/data/alpha/datacite` — not auditable
- Alpha allows CSV exports — PII leak vector
- Alpha renames tools to `alpha_*` — breaks MCP clients
- Alpha relaxes DOI validation — corpus pollution

## Rollback plan

There is no rollback. Omega wins.
