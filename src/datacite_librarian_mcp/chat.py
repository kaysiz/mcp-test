"""Natural-language REPL entrypoint (same as scripts/nl_chat.py)."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

# When installed as a package, default data dir is CWD (user's datafiles location)
os.environ.setdefault("DATACITE_DATA_DIR", str(Path.cwd()))


def _pretty(obj: Any, limit: int = 14_000) -> str:
    import json

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
        lines.append("Issue severity totals: " + ", ".join(f"{k}={v}" for k, v in sev.items()))
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
    m = re.search(r"client[_\s-]?id[:\s]+([a-z0-9._-]+)", text, re.I)
    if m:
        return m.group(1)
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
    """Route a natural-language question to MCP tools and return a readable answer."""
    from . import server as srv

    q = question.strip()
    if not q:
        return "Ask something about your local DataCite corpus (DOIs, funders, QA, …)."

    low = q.lower()

    if low in {"help", "?", "h"}:
        return (
            "Try questions like:\n"
            "  • how many DOIs / records?\n"
            "  • how many funders? list funders\n"
            "  • list clients / repositories\n"
            "  • repository health (optionally: for zenodo)\n"
            "  • funder compliance for European Commission\n"
            "  • search climate / search datasets\n"
            "  • get DOI 10.5281/zenodo.20481462\n"
            "  • what data am I using? / corpus status\n"
        )

    if any(
        p in low
        for p in (
            "how many doi",
            "how many record",
            "number of doi",
            "count doi",
            "total doi",
            "corpus size",
        )
    ):
        clients = srv.list_clients()
        total = sum(c["doi_count"] for c in clients.get("clients", []))
        status = srv.corpus_status()
        return (
            f"In the **currently scanned** local corpus (`{clients.get('data_dir')}`):\n"
            f"  • **~{total:,} DOIs** "
            f"({clients.get('scanned', total):,} records scanned; "
            f"truncated={clients.get('truncated')}).\n"
            f"  • Part files: {status.get('part_files')}  mode: {status.get('mode')}\n\n"
            "This is only JSONL on disk for this MCP — not necessarily the full monthly CSV index."
        )

    if any(p in low for p in ("how many funder", "number of funder", "count funder")):
        funders = srv.list_funders(limit=200)
        n = len(funders.get("funders", []))
        lines = [
            f"Found **{n}** distinct funder names/IDs "
            f"(truncated={funders.get('truncated')}).",
            "",
            "Top by mention count:",
        ]
        for item in funders.get("funders", [])[:10]:
            lines.append(f"  • {item.get('funder')}: {item.get('record_mentions')}")
        return "\n".join(lines)

    if any(p in low for p in ("how many client", "how many repositor", "how many repo")):
        clients = srv.list_clients()
        n = len(clients.get("clients", []))
        lines = [f"**{n}** repository client_ids.", "", "Largest:"]
        for item in clients.get("clients", [])[:10]:
            lines.append(f"  • {item.get('client_id')}: {item.get('doi_count'):,}")
        return "\n".join(lines)

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

    if re.search(r"\blist\b.*\b(client|repositor)", low) or low in {
        "clients",
        "repositories",
        "list clients",
    }:
        clients = srv.list_clients()
        lines = [f"Repositories ({len(clients.get('clients', []))}):"]
        for item in clients.get("clients", [])[:25]:
            lines.append(f"  • {item['client_id']}: {item['doi_count']:,}")
        return "\n".join(lines)

    if re.search(r"\blist\b.*\bfunder", low) or low in {"funders", "list funders"}:
        funders = srv.list_funders(limit=40)
        lines = ["Funders (top by mentions):"]
        for item in funders.get("funders", []):
            lines.append(f"  • {item['funder']}: {item['record_mentions']}")
        return "\n".join(lines)

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

    if doi:
        return _pretty(srv.get_doi(doi))

    if any(p in low for p in ("funder compliance", "funding compliance", "compliance")):
        fq = _extract_funder_query(q)
        result = srv.funder_compliance(funder_query=fq)
        header = "Funder compliance" + (f" (query: {fq!r})" if fq else "")
        return header + "\n\n" + _summarize_funder(result)

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
    ) or low.startswith("health") or " health" in low:
        cid = _extract_client_id(q)
        result = srv.repository_health(client_id=cid)
        header = "Repository health" + (f" (client_id={cid})" if cid else "")
        return header + "\n\n" + _summarize_health(result)

    if low.startswith("search ") or "search for" in low or low.startswith("find "):
        term = q
        for prefix in ("search for ", "search ", "find dois ", "find "):
            if low.startswith(prefix):
                term = q[len(prefix) :].strip()
                break
        has_funder = True if ("with funder" in term.lower() or "funded" in term.lower()) else None
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
                f"[{item.get('resource_type_general')}]"
            )
        return "\n".join(lines) if result.get("results") else "\n".join(lines) + "\n  (no matches)"

    if len(q.split()) <= 4 and not q.endswith("?"):
        result = srv.search_dois(query=q, max_results=5)
        if result.get("returned"):
            lines = [f"Interpreted as search for {q!r}:", ""]
            for item in result.get("results", []):
                lines.append(f"  • {item.get('doi')}: {item.get('title')}")
            return "\n".join(lines)

    return (
        "I wasn't sure how to map that. Type **help** for examples.\n"
        "Try: how many DOIs?, how many funders?, list clients, "
        "repository health for zenodo, funder compliance for European Commission, search …"
    )


def main() -> None:
    data_dir = os.environ.get("DATACITE_DATA_DIR", str(Path.cwd()))
    print(
        "\n╔══════════════════════════════════════════════════════════════╗\n"
        "║  DataCite Librarian — ask questions about your datafiles     ║\n"
        "╚══════════════════════════════════════════════════════════════╝\n"
    )
    print(f"Data dir: {data_dir}")
    try:
        from . import server as srv

        st = srv.corpus_status()
        print(f"Mode: {st.get('mode')}  part_files: {st.get('part_files')}")
    except Exception as exc:  # noqa: BLE001
        print(f"(status: {exc})")

    print(
        "\nExamples: how many DOIs? | how many funders? | list clients |\n"
        "  repository health for zenodo | funder compliance for European Commission |\n"
        "  search climate | 10.5281/zenodo.… | help | quit\n"
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