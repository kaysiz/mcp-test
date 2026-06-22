#!/usr/bin/env python3
"""Interactive MCP client: numbered shortcuts OR natural-language questions.

Examples at the prompt:
  1
  how many dois
  how many funders?
  repository health for zenodo
  funder compliance for European Commission
  search climate
  10.5281/zenodo.20481462
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

# Ensure project root on path when run as script
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

# Point at datafiles in project root by default
os.environ.setdefault("DATACITE_DATA_DIR", str(ROOT))


MENU = """
DataCite Librarian MCP — interactive client
  data_dir: {data_dir}
  transport: {mode}

Type a number (1–9, 0) OR ask in plain English.

  1  corpus_status          2  server_info         3  list_clients
  4  list_funders           5  repository_health   6  funder_compliance
  7  search_dois            8  get_doi             9  check_doi_qa
  0  diff_partitions        l  list tools          h  help
  q  quit

Natural language examples:
  how many dois / how many funders / list clients
  repository health for zenodo
  funder compliance for European Commission
  search climate
  10.5281/zenodo.…
"""


def _pretty(obj: object) -> str:
    try:
        return json.dumps(obj, indent=2, default=str)[:12000]
    except TypeError:
        return str(obj)[:12000]


def _tool_result_to_obj(result: Any) -> Any:
    if hasattr(result, "data") and result.data is not None:
        return result.data
    if hasattr(result, "content"):
        parts = []
        for block in result.content or []:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        if len(parts) == 1:
            try:
                return json.loads(parts[0])
            except json.JSONDecodeError:
                return parts[0]
        return parts
    return result


# --- NL routing (same ideas as chat.py; HTTP path calls tools via callback) ---


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


def _summarize_health(h: dict[str, Any]) -> str:
    lines = [
        f"Scanned {h.get('scanned', 0):,} in-scope DOIs "
        f"(examined {h.get('records_examined', h.get('scanned', 0)):,}; "
        f"truncated={h.get('truncated')}).",
        f"Scope: {h.get('scope')}={h.get('scope_value')}",
        "",
        "Completeness (%):",
    ]
    for k, v in (h.get("completeness") or {}).items():
        lines.append(f"  - {k}: {v}%")
    top = h.get("top_issues") or []
    if top:
        lines.append("")
        lines.append("Top issues:")
        for item in top[:8]:
            lines.append(f"  - {item.get('code')}: {item.get('count')}")
    return "\n".join(lines)


def _summarize_funder(f: dict[str, Any]) -> str:
    lines = [
        f"Matching funded DOIs: {f.get('total_matching_dois', 0):,}",
        f"With funder ID: {f.get('dois_with_funder_id', 0)}",
        f"With award number: {f.get('dois_with_award_number', 0)}",
        f"With license: {f.get('dois_with_license', 0)}",
        f"With ORCID: {f.get('dois_with_orcid_creators', 0)}",
        f"Incomplete funding: {f.get('incomplete_funding_records', 0)}",
        f"truncated={f.get('truncated')}",
    ]
    funders = f.get("funders_seen") or []
    if funders:
        lines.append("Funders (sample): " + ", ".join(funders[:12]))
    return "\n".join(lines)


def answer_nl_sync(question: str, tools: dict[str, Any]) -> str:
    """Route NL using in-process tool functions (dict of name -> callable)."""
    q = question.strip()
    low = q.lower()

    if low in {"help", "h", "?"}:
        return (
            "Examples:\n"
            "  how many dois / how many funders / how many repositories\n"
            "  list clients / list funders / corpus status\n"
            "  repository health / repository health for zenodo\n"
            "  funder compliance for European Commission\n"
            "  search climate / get 10.5281/zenodo.…\n"
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
        clients = tools["list_clients"]()
        total = sum(c["doi_count"] for c in clients.get("clients", []))
        status = tools["corpus_status"]()
        return (
            f"About {total:,} DOIs in the scanned corpus "
            f"({clients.get('scanned', total):,} records; truncated={clients.get('truncated')}).\n"
            f"data_dir={clients.get('data_dir')}  part_files={status.get('part_files')}  "
            f"mode={status.get('mode')}\n"
            "(Only JSONL parts on disk — not necessarily the full monthly CSV index.)"
        )

    if any(p in low for p in ("how many funder", "number of funder", "count funder")):
        funders = tools["list_funders"]()
        items = funders.get("funders", [])
        lines = [
            f"{len(items)} distinct funders/IDs (truncated={funders.get('truncated')}).",
            "Top:",
        ]
        for item in items[:10]:
            lines.append(f"  • {item.get('funder')}: {item.get('record_mentions')}")
        return "\n".join(lines)

    if any(p in low for p in ("how many client", "how many repositor", "how many repo")):
        clients = tools["list_clients"]()
        items = clients.get("clients", [])
        lines = [f"{len(items)} repositories. Largest:"]
        for item in items[:10]:
            lines.append(f"  • {item.get('client_id')}: {item.get('doi_count'):,}")
        return "\n".join(lines)

    if any(
        p in low
        for p in ("corpus status", "what data", "which data", "data dir", "datafile", "where is the data")
    ):
        return _pretty(tools["corpus_status"]())

    if "server info" in low or low == "info":
        return _pretty(tools["server_info"]())

    if "partition" in low:
        return _pretty(tools["diff_partitions_summary"]())

    if re.search(r"\blist\b.*\b(client|repositor)", low) or low in {
        "clients",
        "repositories",
        "list clients",
    }:
        clients = tools["list_clients"]()
        lines = [f"Repositories ({len(clients.get('clients', []))}):"]
        for item in clients.get("clients", [])[:25]:
            lines.append(f"  • {item['client_id']}: {item['doi_count']:,}")
        return "\n".join(lines)

    if re.search(r"\blist\b.*\bfunder", low) or low in {"funders", "list funders"}:
        funders = tools["list_funders"]()
        lines = ["Funders:"]
        for item in funders.get("funders", [])[:40]:
            lines.append(f"  • {item['funder']}: {item['record_mentions']}")
        return "\n".join(lines)

    doi = _extract_doi(q)
    if doi and any(p in low for p in ("qa", "check", "quality", "issues")):
        return _pretty(tools["check_doi_qa"](doi))
    if doi:
        return _pretty(tools["get_doi"](doi))

    if any(p in low for p in ("funder compliance", "funding compliance", "compliance")):
        fq = _extract_funder_query(q)
        result = tools["funder_compliance"](funder_query=fq)
        return _summarize_funder(result) + "\n\n" + _pretty(result)

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
        result = tools["repository_health"](client_id=cid)
        return _summarize_health(result)

    if low.startswith("search ") or "search for" in low or low.startswith("find "):
        term = q
        for prefix in ("search for ", "search ", "find dois ", "find "):
            if low.startswith(prefix):
                term = q[len(prefix) :].strip()
                break
        result = tools["search_dois"](query=term or None, max_results=8)
        lines = [f"{result.get('returned', 0)} hits (scanned {result.get('scanned')}):", ""]
        for item in result.get("results", []):
            lines.append(f"  • {item.get('doi')}: {item.get('title')}")
        return "\n".join(lines)

    # short phrase → search
    if len(q.split()) <= 5 and not any(c.isdigit() and c == q for c in q):
        result = tools["search_dois"](query=q, max_results=5)
        if result.get("returned"):
            lines = [f"Search for {q!r}:", ""]
            for item in result.get("results", []):
                lines.append(f"  • {item.get('doi')}: {item.get('title')}")
            return "\n".join(lines)

    return (
        "Could not map that question. Type h for help, or use 1–9 / 0.\n"
        "Try: how many dois | how many funders | list clients | "
        "repository health for zenodo | funder compliance for European Commission"
    )


async def answer_nl_http(question: str, client: Any) -> str:
    """NL routing that invokes tools on a live HTTP MCP client."""

    async def t(name: str, args: dict | None = None) -> Any:
        result = await client.call_tool(name, args or {})
        return _tool_result_to_obj(result)

    # Build sync-style wrappers for the shared router by awaiting then returning
    # We implement HTTP path by duplicating the branch logic with awaits for clarity.

    q = question.strip()
    low = q.lower()

    if low in {"help", "h", "?"}:
        return answer_nl_sync(q, {})  # only help text path — pass empty unused

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
        clients = await t("list_clients")
        status = await t("corpus_status")
        if not isinstance(clients, dict):
            return _pretty(clients)
        total = sum(c.get("doi_count", 0) for c in clients.get("clients", []))
        return (
            f"About {total:,} DOIs in the scanned corpus "
            f"({clients.get('scanned', total):,} records; truncated={clients.get('truncated')}).\n"
            f"data_dir={clients.get('data_dir')}  part_files="
            f"{status.get('part_files') if isinstance(status, dict) else '?'}  "
            f"mode={status.get('mode') if isinstance(status, dict) else '?'}"
        )

    if any(p in low for p in ("how many funder", "number of funder", "count funder")):
        funders = await t("list_funders")
        if not isinstance(funders, dict):
            return _pretty(funders)
        items = funders.get("funders", [])
        lines = [f"{len(items)} distinct funders/IDs (truncated={funders.get('truncated')}).", "Top:"]
        for item in items[:10]:
            lines.append(f"  • {item.get('funder')}: {item.get('record_mentions')}")
        return "\n".join(lines)

    if any(p in low for p in ("how many client", "how many repositor", "how many repo")):
        clients = await t("list_clients")
        if not isinstance(clients, dict):
            return _pretty(clients)
        items = clients.get("clients", [])
        lines = [f"{len(items)} repositories. Largest:"]
        for item in items[:10]:
            lines.append(f"  • {item.get('client_id')}: {item.get('doi_count'):,}")
        return "\n".join(lines)

    if any(
        p in low
        for p in ("corpus status", "what data", "which data", "data dir", "datafile", "where is the data")
    ):
        return _pretty(await t("corpus_status"))

    if "server info" in low or low == "info":
        return _pretty(await t("server_info"))

    if "partition" in low:
        return _pretty(await t("diff_partitions_summary"))

    if re.search(r"\blist\b.*\b(client|repositor)", low) or low in {
        "clients",
        "repositories",
        "list clients",
    }:
        clients = await t("list_clients")
        if not isinstance(clients, dict):
            return _pretty(clients)
        lines = [f"Repositories ({len(clients.get('clients', []))}):"]
        for item in clients.get("clients", [])[:25]:
            lines.append(f"  • {item['client_id']}: {item['doi_count']:,}")
        return "\n".join(lines)

    if re.search(r"\blist\b.*\bfunder", low) or low in {"funders", "list funders"}:
        funders = await t("list_funders")
        if not isinstance(funders, dict):
            return _pretty(funders)
        lines = ["Funders:"]
        for item in funders.get("funders", [])[:40]:
            lines.append(f"  • {item['funder']}: {item['record_mentions']}")
        return "\n".join(lines)

    doi = _extract_doi(q)
    if doi and any(p in low for p in ("qa", "check", "quality", "issues")):
        return _pretty(await t("check_doi_qa", {"doi": doi}))
    if doi:
        return _pretty(await t("get_doi", {"doi": doi}))

    if any(p in low for p in ("funder compliance", "funding compliance", "compliance")):
        fq = _extract_funder_query(q)
        args: dict[str, Any] = {}
        if fq:
            args["funder_query"] = fq
        result = await t("funder_compliance", args)
        if isinstance(result, dict):
            return _summarize_funder(result) + "\n\n" + _pretty(result)
        return _pretty(result)

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
        args = {}
        if cid:
            args["client_id"] = cid
        result = await t("repository_health", args)
        if isinstance(result, dict):
            return _summarize_health(result)
        return _pretty(result)

    if low.startswith("search ") or "search for" in low or low.startswith("find "):
        term = q
        for prefix in ("search for ", "search ", "find dois ", "find "):
            if low.startswith(prefix):
                term = q[len(prefix) :].strip()
                break
        args = {"max_results": 8}
        if term:
            args["query"] = term
        result = await t("search_dois", args)
        if not isinstance(result, dict):
            return _pretty(result)
        lines = [f"{result.get('returned', 0)} hits (scanned {result.get('scanned')}):", ""]
        for item in result.get("results", []):
            lines.append(f"  • {item.get('doi')}: {item.get('title')}")
        return "\n".join(lines)

    if len(q.split()) <= 5:
        result = await t("search_dois", {"query": q, "max_results": 5})
        if isinstance(result, dict) and result.get("returned"):
            lines = [f"Search for {q!r}:", ""]
            for item in result.get("results", []):
                lines.append(f"  • {item.get('doi')}: {item.get('title')}")
            return "\n".join(lines)

    return (
        "Could not map that question. Type h for help, or use 1–9 / 0.\n"
        "Try: how many dois | how many funders | list clients | "
        "repository health for zenodo"
    )


def _inprocess_tools() -> dict[str, Any]:
    from datacite_librarian_mcp import server as srv

    return {
        "corpus_status": srv.corpus_status,
        "server_info": srv.server_info,
        "list_clients": srv.list_clients,
        "list_funders": lambda: srv.list_funders(limit=200),
        "diff_partitions_summary": srv.diff_partitions_summary,
        "repository_health": lambda client_id=None: srv.repository_health(client_id=client_id),
        "funder_compliance": lambda funder_query=None: srv.funder_compliance(
            funder_query=funder_query
        ),
        "search_dois": lambda query=None, max_results=8: srv.search_dois(
            query=query, max_results=max_results
        ),
        "get_doi": srv.get_doi,
        "check_doi_qa": srv.check_doi_qa,
    }


async def run_inprocess() -> None:
    from datacite_librarian_mcp import server as srv

    data_dir = os.environ.get("DATACITE_DATA_DIR", str(ROOT))
    mode = "in-process (direct tool functions)"
    print(MENU.format(data_dir=data_dir, mode=mode))
    tools_map = _inprocess_tools()

    menu_tools = {
        "1": ("corpus_status", lambda: srv.corpus_status()),
        "2": ("server_info", lambda: srv.server_info()),
        "3": ("list_clients", lambda: srv.list_clients()),
        "4": ("list_funders", lambda: srv.list_funders()),
        "0": ("diff_partitions_summary", lambda: srv.diff_partitions_summary()),
    }

    while True:
        try:
            choice = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            break

        if not choice:
            continue
        key = choice.lower()

        if key in {"q", "quit", "exit"}:
            print("bye")
            break
        if key in {"h", "help", "?"}:
            print(answer_nl_sync("help", tools_map))
            continue
        if key == "l":
            print(
                "Tools:",
                ", ".join(
                    sorted(
                        t.__name__
                        for t in [
                            srv.corpus_status,
                            srv.server_info,
                            srv.list_clients,
                            srv.list_funders,
                            srv.repository_health,
                            srv.funder_compliance,
                            srv.search_dois,
                            srv.get_doi,
                            srv.check_doi_qa,
                            srv.diff_partitions_summary,
                        ]
                    )
                ),
            )
            continue
        if key in menu_tools:
            name, fn = menu_tools[key]
            print(f"\n--- {name} ---")
            print(_pretty(fn()))
            continue
        if key == "5":
            cid = input("client_id (empty=all): ").strip() or None
            print("\n--- repository_health ---")
            print(_pretty(srv.repository_health(client_id=cid)))
            continue
        if key == "6":
            fq = input("funder_query (empty=any with funding): ").strip() or None
            print("\n--- funder_compliance ---")
            print(_pretty(srv.funder_compliance(funder_query=fq)))
            continue
        if key == "7":
            q = input("search query: ").strip() or None
            print("\n--- search_dois ---")
            print(_pretty(srv.search_dois(query=q, max_results=10)))
            continue
        if key == "8":
            doi = input("doi: ").strip()
            print("\n--- get_doi ---")
            print(_pretty(srv.get_doi(doi)))
            continue
        if key == "9":
            doi = input("doi: ").strip()
            print("\n--- check_doi_qa ---")
            print(_pretty(srv.check_doi_qa(doi)))
            continue

        # Natural language (anything else)
        print()
        print(answer_nl_sync(choice, tools_map))


async def run_http(url: str) -> None:
    from fastmcp import Client

    data_dir = os.environ.get("DATACITE_DATA_DIR", str(ROOT))
    print(MENU.format(data_dir=data_dir, mode=f"HTTP {url}"))

    async with Client(url) as client:
        while True:
            try:
                choice = input("\n> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nbye")
                break

            if not choice:
                continue
            key = choice.lower()

            if key in {"q", "quit", "exit"}:
                print("bye")
                break
            if key in {"h", "help", "?"}:
                print(await answer_nl_http("help", client))
                continue
            if key == "l":
                tools = await client.list_tools()
                for t in tools:
                    print(f"  - {t.name}: {(t.description or '')[:80]}")
                continue

            async def call(name: str, args: dict | None = None) -> None:
                print(f"\n--- {name} ---")
                result = await client.call_tool(name, args or {})
                print(_pretty(_tool_result_to_obj(result)))

            if key == "1":
                await call("corpus_status")
            elif key == "2":
                await call("server_info")
            elif key == "3":
                await call("list_clients")
            elif key == "4":
                await call("list_funders")
            elif key == "5":
                cid = input("client_id (empty=all): ").strip() or None
                args = {}
                if cid:
                    args["client_id"] = cid
                await call("repository_health", args)
            elif key == "6":
                fq = input("funder_query (empty=any with funding): ").strip() or None
                args = {}
                if fq:
                    args["funder_query"] = fq
                await call("funder_compliance", args)
            elif key == "7":
                q = input("search query: ").strip() or None
                args: dict = {"max_results": 10}
                if q:
                    args["query"] = q
                await call("search_dois", args)
            elif key == "8":
                doi = input("doi: ").strip()
                await call("get_doi", {"doi": doi})
            elif key == "9":
                doi = input("doi: ").strip()
                await call("check_doi_qa", {"doi": doi})
            elif key == "0":
                await call("diff_partitions_summary")
            else:
                # Natural language over HTTP tools
                print()
                print(await answer_nl_http(choice, client))


def main() -> None:
    url = os.environ.get("MCP_URL", "").strip()
    if url:
        asyncio.run(run_http(url))
    else:
        asyncio.run(run_inprocess())


if __name__ == "__main__":
    main()