#!/usr/bin/env python3
"""Natural-language chat over your local DataCite datafiles.

Asks questions in plain English; routes to librarian MCP tools (in-process).
No separate agent host required.

Examples:
  how many DOIs are there?
  how many funders?
  repository health for zenodo
  funder compliance for European Commission
  search climate datasets
  look up 10.5281/zenodo.20481462
  list clients
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

os.environ.setdefault("DATACITE_DATA_DIR", str(ROOT))

from datacite_librarian_mcp import server as srv  # noqa: E402


def _pretty(obj: Any, limit: int = 14_000) -> str:
    try:
        text = json.dumps(obj, indent=2, default=str)
    except TypeError:
        text = str(obj)
    if len(text) > limit:
        return text[:limit] + "\n… (truncated)"
    return text


def _summarize_health(h: dict[str, Any]) -> str:
    lines = [
        f"Scanned **{h.get('scanned', 0):,}** in-scope DOIs "
        f"(examined {h.get('records_examined', h.get('scanned', 0)):,} stream records).",
        f"Scope: {h.get('scope')}={h.get('scope_value')}; truncated={h.get('truncated')}.",
        "",
        "Completeness (% of in-scope DOIs):",
    ]
    for k, v in (h.get("completeness") or {}).items():
        lines.append(f"  - {k}: {v}%")
    sev = h.get("severity_counts") or {}
    if sev:
        lines.append("")
        lines.append(
            "Issue severity totals: "
            + ", ".join(f"{k}={v}" for k, v in sev.items())
        )
    top = h.get("top_issues") or []
    if top:
        lines.append("")
        lines.append("Top issue codes:")
        for item in top[:8]:
            lines.append(f"  - {item.get('code')}: {item.get('count')}")
    return "\n".join(lines)


def _summarize_funder(f: dict[str, Any]) -> str:
    lines = [
        f"Matching funded DOIs: **{f.get('total_matching_dois', 0):,}** "
        f"(stream examined {f.get('records_examined', f.get('scanned', 0)):,}; "
        f"truncated={f.get('truncated')}).",
        f"With funder ID: {f.get('dois_with_funder_id', 0)}",
        f"With award number: {f.get('dois_with_award_number', 0)}",
        f"With award title: {f.get('dois_with_award_title', 0)}",
        f"With license: {f.get('dois_with_license', 0)}",
        f"With ORCID on creators: {f.get('dois_with_orcid_creators', 0)}",
        f"Incomplete funding records: {f.get('incomplete_funding_records', 0)}",
    ]
    funders = f.get("funders_seen") or []
    if funders:
        lines.append("")
        lines.append("Funders seen (sample): " + ", ".join(funders[:15]))
    issues = f.get("issues") or []
    if issues:
        lines.append("")
        lines.append(f"Sample issues ({min(5, len(issues))} of {len(issues)}):")
        for iss in issues[:5]:
            lines.append(f"  - [{iss.get('severity')}] {iss.get('doi')}: {iss.get('message')}")
    return "\n".join(lines)


def _extract_client_id(text: str) -> str | None:
    # explicit patterns
    m = re.search(r"client[_\s-]?id[:\s]+([a-z0-9._-]+)", text, re.I)
    if m:
        return m.group(1)
    # common names
    aliases = {
        "zenodo": "cern.zenodo",
        "arxiv": "arxiv.content",
        "figshare": "figshare.ars",
        "gbif": "gbif.gbif",
        "osf": "cos.osf",
    }
    low = text.lower()
    for name, cid in aliases.items():
        if name in low:
            return cid
    m = re.search(r"\b([a-z][a-z0-9]+(?:\.[a-z0-9._-]+)+)\b", text)
    if m and "." in m.group(1):
        return m.group(1)
    return None


def _extract_doi(text: str) -> str | None:
    m = re.search(r"\b(10\.\d{4,9}/[^\s,;]+)", text)
    return m.group(1).rstrip(").,]") if m else None


def _extract_funder_query(text: str) -> str | None:
    low = text.lower()
    for prefix in (
        "funder compliance for ",
        "compliance for ",
        "funding from ",
        "funded by ",
        "funder ",
        "for funder ",
    ):
        if prefix in low:
            idx = low.index(prefix) + len(prefix)
            q = text[idx:].strip().strip("?\"'")
            if q:
                return q
    # known short names
    for name in (
        "European Commission",
        "National Science Foundation",
        "Wellcome",
        "DFG",
        "NSF",
        "ARC",
    ):
        if name.lower() in low:
            return name
    return None


def answer(question: str) -> str:
    """Route a natural-language question to tools and return a readable answer."""
    q = question.strip()
    if not q:
        return "Ask something about your local DataCite corpus (DOIs, funders, QA, …)."

    low = q.lower()

    # --- meta / help ---
    if low in {"help", "?", "h"}:
        return (
            "Try questions like:\n"
            "  • how many DOIs / records?\n"
            "  • how many funders? list funders\n"
            "  • list clients / repositories\n"
            "  • repository health (optionally: for zenodo)\n"
            "  • funder compliance for European Commission\n"
            "  • search climate / search datasets about lakes\n"
            "  • get DOI 10.5281/zenodo.20481462\n"
            "  • what data am I using? / corpus status\n"
            "  • server info\n"
        )

    # --- corpus / counts ---
    if any(
        p in low
        for p in (
            "how many doi",
            "how many record",
            "number of doi",
            "count doi",
            "total doi",
            "how many in the",
            "corpus size",
        )
    ):
        clients = srv.list_clients()
        total = sum(c["doi_count"] for c in clients.get("clients", []))
        status = srv.corpus_status()
        return (
            f"In the **currently scanned** local corpus (`{clients.get('data_dir')}`):\n"
            f"  • **~{total:,} DOIs** counted while streaming "
            f"({clients.get('scanned', total):,} records scanned; "
            f"truncated={clients.get('truncated')}).\n"
            f"  • Part files discovered: {status.get('part_files')}\n"
            f"  • Mode: {status.get('mode')}\n\n"
            "Note: this is only what is on disk for this MCP instance "
            "(e.g. one `part_0000.jsonl.gz`), not necessarily the full monthly index "
            "(your `2026-06.csv.gz` may list far more DOIs without matching JSONL parts)."
        )

    if any(p in low for p in ("how many funder", "number of funder", "count funder")):
        funders = srv.list_funders(limit=200)
        n = len(funders.get("funders", []))
        top = funders.get("funders", [])[:10]
        lines = [
            f"Found **{n}** distinct funder names/IDs in fundingReferences "
            f"(scan truncated={funders.get('truncated')}).",
            "",
            "Top by mention count:",
        ]
        for item in top:
            lines.append(f"  • {item.get('funder')}: {item.get('record_mentions')}")
        return "\n".join(lines)

    if any(p in low for p in ("how many client", "how many repositor", "how many repo")):
        clients = srv.list_clients()
        n = len(clients.get("clients", []))
        top = clients.get("clients", [])[:10]
        lines = [f"**{n}** repository client_ids in the scan.", "", "Largest:"]
        for item in top:
            lines.append(f"  • {item.get('client_id')}: {item.get('doi_count'):,} DOIs")
        return "\n".join(lines)

    # --- status / info ---
    if any(
        p in low
        for p in (
            "corpus status",
            "what data",
            "which data",
            "data dir",
            "datafile",
            "where is the data",
        )
    ):
        return _pretty(srv.corpus_status())

    if "server info" in low or low == "info":
        return _pretty(srv.server_info())

    if "partition" in low:
        return _pretty(srv.diff_partitions_summary())

    # --- list clients / funders ---
    if re.search(r"\blist\b.*\b(client|repositor)", low) or low in {
        "clients",
        "repositories",
        "list clients",
    }:
        clients = srv.list_clients()
        lines = [f"Repositories ({len(clients.get('clients', []))}):"]
        for item in clients.get("clients", [])[:25]:
            lines.append(f"  • {item['client_id']}: {item['doi_count']:,}")
        if len(clients.get("clients", [])) > 25:
            lines.append(f"  … and {len(clients['clients']) - 25} more")
        return "\n".join(lines)

    if re.search(r"\blist\b.*\bfunder", low) or low in {"funders", "list funders"}:
        funders = srv.list_funders(limit=40)
        lines = ["Funders (top by mentions):"]
        for item in funders.get("funders", []):
            lines.append(f"  • {item['funder']}: {item['record_mentions']}")
        return "\n".join(lines)

    # --- get / QA single DOI ---
    doi = _extract_doi(q)
    if doi and any(p in low for p in ("qa", "check", "quality", "issues for")):
        result = srv.check_doi_qa(doi)
        if not result.get("found"):
            return _pretty(result)
        return (
            f"QA for **{result.get('doi')}**: "
            f"{result.get('errors')} errors, {result.get('warnings')} warnings, "
            f"{result.get('infos')} infos.\n\n"
            + _pretty({"summary": result.get("summary"), "issues": result.get("issues", [])[:15]})
        )

    if doi and any(p in low for p in ("get", "lookup", "look up", "show", "inspect", "about")):
        return _pretty(srv.get_doi(doi))
    if doi and not any(p in low for p in ("health", "compliance", "search")):
        # bare DOI or "doi 10...."
        return _pretty(srv.get_doi(doi))

    # --- funder compliance ---
    if any(p in low for p in ("funder compliance", "funding compliance", "compliance")):
        fq = _extract_funder_query(q)
        result = srv.funder_compliance(funder_query=fq)
        header = f"Funder compliance"
        if fq:
            header += f" (query: {fq!r})"
        return header + "\n\n" + _summarize_funder(result) + "\n\nRaw:\n" + _pretty(result)

    if any(p in low for p in ("funded by", "funding from")) and not doi:
        fq = _extract_funder_query(q) or q
        # strip leading verbs
        fq = re.sub(r"^(who |what |show |find )", "", fq, flags=re.I)
        result = srv.funder_compliance(funder_query=fq if len(fq) < 80 else None)
        if fq and len(fq) >= 80:
            result = srv.funder_compliance()
        return _summarize_funder(result)

    # --- repository health / QA aggregate ---
    if any(
        p in low
        for p in (
            "repository health",
            "repo health",
            "qa report",
            "quality report",
            "metadata quality",
            "completeness",
            "health check",
        )
    ) or (low.startswith("health") or " health" in low):
        cid = _extract_client_id(q)
        result = srv.repository_health(client_id=cid)
        header = "Repository health"
        if cid:
            header += f" (client_id={cid})"
        return header + "\n\n" + _summarize_health(result)

    # --- search ---
    if low.startswith("search ") or "search for" in low or low.startswith("find "):
        term = q
        for prefix in ("search for ", "search ", "find dois ", "find "):
            if low.startswith(prefix):
                term = q[len(prefix) :].strip()
                break
        # strip resource type hints we might pass later
        has_funder = None
        if "with funder" in term.lower() or "funded" in term.lower():
            has_funder = True
        rtg = None
        for tname in ("Dataset", "Software", "Preprint", "Text", "JournalArticle"):
            if tname.lower() in term.lower():
                rtg = tname
        result = srv.search_dois(
            query=term or None,
            resource_type_general=rtg,
            has_funder=has_funder,
            max_results=8,
        )
        lines = [
            f"Search returned **{result.get('returned', 0)}** hits "
            f"(scanned {result.get('scanned')}, truncated={result.get('truncated')}).",
            "",
        ]
        for item in result.get("results", []):
            lines.append(
                f"  • {item.get('doi')}: {item.get('title') or '(no title)'} "
                f"[{item.get('resource_type_general')}] client={item.get('client_id')}"
            )
        if not result.get("results"):
            lines.append("  (no matches — try a simpler keyword)")
        return "\n".join(lines)

    # --- default: try search + offer help ---
    # If it looks like a short keyword query, search
    if len(q.split()) <= 4 and not q.endswith("?"):
        result = srv.search_dois(query=q, max_results=5)
        if result.get("returned"):
            lines = [f"Interpreted as search for {q!r}:", ""]
            for item in result.get("results", []):
                lines.append(f"  • {item.get('doi')}: {item.get('title')}")
            lines.append("\nType `help` for more question patterns.")
            return "\n".join(lines)

    return (
        "I wasn't sure how to map that. Type **help** for examples.\n"
        "You can ask about DOI counts, funders, clients, repository health, "
        "funder compliance, search, or a specific DOI."
    )


def main() -> None:
    data_dir = os.environ.get("DATACITE_DATA_DIR", str(ROOT))
    print(
        """
╔══════════════════════════════════════════════════════════════╗
║  DataCite Librarian — natural language over your datafiles   ║
╚══════════════════════════════════════════════════════════════╝
"""
    )
    print(f"Data dir: {data_dir}")
    try:
        st = srv.corpus_status()
        print(f"Mode: {st.get('mode')}  part_files: {st.get('part_files')}")
    except Exception as exc:  # noqa: BLE001
        print(f"(status error: {exc})")

    print(
        "\nAsk in plain English. Examples:\n"
        "  how many DOIs?\n"
        "  how many funders?\n"
        "  list clients\n"
        "  repository health for zenodo\n"
        "  funder compliance for European Commission\n"
        "  search climate\n"
        "  10.5281/zenodo.20481462\n"
        "  help | quit\n"
    )

    while True:
        try:
            q = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            break
        if not q:
            continue
        if q.lower() in {"quit", "exit", "q"}:
            print("bye")
            break
        print()
        try:
            print(answer(q))
        except Exception as exc:  # noqa: BLE001
            print(f"Error: {exc}")
        print()


if __name__ == "__main__":
    main()