"""Generate realistic mock DataCite monthly-style datafiles for local demos.

Run as a module or via ``ensure_mock_corpus()`` when no real data_dir is set.
Layout mirrors the monthly/public datafile structure documented by DataCite:

    data/mock/
      STATUS.json
      MANIFEST.json
      dois/
        updated_2025-11/
          2025-11.csv
          part_0000.jsonl.gz
"""

from __future__ import annotations

import csv
import gzip
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def default_mock_dir() -> Path:
    """Resolve a writable mock corpus directory.

    Preference order:
    1. ``DATACITE_MOCK_DIR`` env var
    2. Project ``data/mock`` when running from a source checkout (writable)
    3. ``$XDG_DATA_HOME/datacite-librarian-mcp/mock`` or platform user data dir
    4. System temp under ``datacite-librarian-mcp-mock``
    """
    env = os.environ.get("DATACITE_MOCK_DIR")
    if env:
        return Path(env).expanduser().resolve()

    # Source checkout: parents[2] == project root when installed as src layout
    try:
        checkout = Path(__file__).resolve().parents[2] / "data" / "mock"
        parent = checkout.parent
        if parent.exists() and os.access(parent, os.W_OK):
            return checkout
        # Project root exists but data/ not yet — still prefer if root is writable
        root = Path(__file__).resolve().parents[2]
        if root.is_dir() and (root / "pyproject.toml").exists() and os.access(root, os.W_OK):
            return checkout
    except (IndexError, OSError):
        pass

    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg).expanduser() / "datacite-librarian-mcp" / "mock"

    home_data = Path.home() / ".local" / "share" / "datacite-librarian-mcp" / "mock"
    try:
        home_data.parent.mkdir(parents=True, exist_ok=True)
        if os.access(home_data.parent, os.W_OK):
            return home_data
    except OSError:
        pass

    return Path(tempfile.gettempdir()) / "datacite-librarian-mcp-mock"


# Back-compat alias (resolved at import time; prefer default_mock_dir() at runtime)
DEFAULT_MOCK_DIR = default_mock_dir()


def _record(
    doi: str,
    *,
    title: str,
    creators: list[dict[str, Any]],
    year: int,
    publisher: str | dict[str, Any],
    resource_type_general: str,
    client_id: str,
    provider_id: str = "cern.zenodo",
    url: str | None = None,
    subjects: list[dict[str, Any]] | None = None,
    descriptions: list[dict[str, Any]] | None = None,
    rights: list[dict[str, Any]] | None = None,
    funding: list[dict[str, Any]] | None = None,
    related: list[dict[str, Any]] | None = None,
    geo: list[dict[str, Any]] | None = None,
    state: str = "findable",
    updated: str = "2025-11-15T10:00:00Z",
    citation_count: int = 0,
    view_count: int = 0,
    download_count: int = 0,
) -> dict[str, Any]:
    """Build one API-shaped DataCite singleton record (data + attributes + relationships)."""
    pub = publisher if isinstance(publisher, dict) else {"name": publisher}
    return {
        "data": {
            "id": doi,
            "type": "dois",
            "attributes": {
                "doi": doi,
                "prefix": doi.split("/")[0],
                "suffix": "/".join(doi.split("/")[1:]),
                "identifiers": [{"identifier": f"https://doi.org/{doi}", "identifierType": "DOI"}],
                "creators": creators,
                "titles": [{"title": title}],
                "publisher": pub,
                "publicationYear": year,
                "subjects": subjects or [],
                "contributors": [],
                "dates": [{"date": f"{year}-01-01", "dateType": "Issued"}],
                "language": "en",
                "types": {
                    "ris": "DATA",
                    "bibtex": "misc",
                    "citeproc": "dataset",
                    "schemaOrg": "Dataset",
                    "resourceTypeGeneral": resource_type_general,
                },
                "relatedIdentifiers": related or [],
                "sizes": [],
                "formats": [],
                "version": "1.0",
                "rightsList": rights or [],
                "descriptions": descriptions or [],
                "geoLocations": geo or [],
                "fundingReferences": funding or [],
                "url": url or f"https://example.org/records/{doi.split('/')[-1]}",
                "contentUrl": None,
                "metadataVersion": 1,
                "schemaVersion": "http://datacite.org/schema/kernel-4",
                "source": "mds",
                "isActive": True,
                "state": state,
                "reason": None,
                "viewCount": view_count,
                "downloadCount": download_count,
                "referenceCount": 0,
                "citationCount": citation_count,
                "partCount": 0,
                "versionCount": 0,
                "created": f"{year}-06-01T12:00:00Z",
                "registered": f"{year}-06-01T12:00:00Z",
                "published": str(year),
                "updated": updated,
            },
            "relationships": {
                "client": {"data": {"id": client_id, "type": "clients"}},
                "provider": {"data": {"id": provider_id, "type": "providers"}},
            },
        }
    }


def build_mock_records() -> list[dict[str, Any]]:
    """Return a small but diverse set of DOIs with good and bad QA patterns."""
    return [
        # --- High quality funded dataset ---
        _record(
            "10.5281/zenodo.100001",
            title="Global Lake Temperature Time Series 1980–2024",
            creators=[
                {
                    "name": "Rivera, Ana",
                    "nameType": "Personal",
                    "givenName": "Ana",
                    "familyName": "Rivera",
                    "nameIdentifiers": [
                        {
                            "nameIdentifier": "https://orcid.org/0000-0002-1825-0097",
                            "nameIdentifierScheme": "ORCID",
                            "schemeUri": "https://orcid.org",
                        }
                    ],
                    "affiliation": [
                        {
                            "name": "Example University",
                            "affiliationIdentifier": "https://ror.org/03yrm5c26",
                            "affiliationIdentifierScheme": "ROR",
                            "schemeUri": "https://ror.org",
                        }
                    ],
                }
            ],
            year=2024,
            publisher={"name": "Zenodo", "publisherIdentifier": "https://ror.org/01ggx4157"},
            resource_type_general="Dataset",
            client_id="cern.zenodo",
            subjects=[
                {"subject": "limnology", "subjectScheme": "LCSH"},
                {"subject": "climate change"},
            ],
            descriptions=[
                {
                    "description": "Harmonized lake surface temperature observations.",
                    "descriptionType": "Abstract",
                }
            ],
            rights=[
                {
                    "rights": "Creative Commons Zero v1.0 Universal",
                    "rightsUri": "https://creativecommons.org/publicdomain/zero/1.0/",
                    "rightsIdentifier": "cc0-1.0",
                    "rightsIdentifierScheme": "SPDX",
                }
            ],
            funding=[
                {
                    "funderName": "European Commission",
                    "funderIdentifier": "https://doi.org/10.13039/501100000780",
                    "funderIdentifierType": "Crossref Funder ID",
                    "awardNumber": "101059548",
                    "awardTitle": "AquaWatch Europe",
                    "awardUri": "https://cordis.europa.eu/project/id/101059548",
                }
            ],
            related=[
                {
                    "relatedIdentifier": "10.1038/s41586-024-00001",
                    "relatedIdentifierType": "DOI",
                    "relationType": "IsSupplementTo",
                    "resourceTypeGeneral": "JournalArticle",
                }
            ],
            geo=[{"geoLocationPlace": "Europe", "geoLocationBox": {
                "westBoundLongitude": "-10.0",
                "eastBoundLongitude": "40.0",
                "southBoundLatitude": "35.0",
                "northBoundLatitude": "70.0",
            }}],
            citation_count=12,
            view_count=540,
            download_count=210,
        ),
        # --- Funded software, missing ORCID ---
        _record(
            "10.5281/zenodo.100002",
            title="lake-qc: Quality control toolkit for in-situ sensors",
            creators=[
                {
                    "name": "Chen, Wei",
                    "nameType": "Personal",
                    "givenName": "Wei",
                    "familyName": "Chen",
                    "affiliation": [{"name": "National Lab"}],
                }
            ],
            year=2023,
            publisher="Zenodo",
            resource_type_general="Software",
            client_id="cern.zenodo",
            descriptions=[{"description": "Python QC utilities.", "descriptionType": "Abstract"}],
            rights=[
                {
                    "rights": "MIT License",
                    "rightsUri": "https://opensource.org/licenses/MIT",
                    "rightsIdentifier": "MIT",
                }
            ],
            funding=[
                {
                    "funderName": "National Science Foundation",
                    "funderIdentifier": "https://doi.org/10.13039/100000001",
                    "funderIdentifierType": "Crossref Funder ID",
                    "awardNumber": "OCE-1234567",
                    "awardTitle": "Sensor Networks for Inland Waters",
                }
            ],
            related=[
                {
                    "relatedIdentifier": "https://github.com/example/lake-qc",
                    "relatedIdentifierType": "URL",
                    "relationType": "IsSupplementTo",
                }
            ],
            citation_count=3,
            view_count=88,
        ),
        # --- Incomplete funding (name only, no award) ---
        _record(
            "10.5281/zenodo.100003",
            title="Citizen science water clarity photographs",
            creators=[
                {
                    "name": "Patel, Sam",
                    "nameType": "Personal",
                    "nameIdentifiers": [
                        {
                            "nameIdentifier": "https://orcid.org/0000-0001-2345-6789",
                            "nameIdentifierScheme": "ORCID",
                        }
                    ],
                }
            ],
            year=2022,
            publisher="Zenodo",
            resource_type_general="Image",
            client_id="cern.zenodo",
            funding=[{"funderName": "Gordon and Betty Moore Foundation"}],
            # no rights, no description — QA issues
        ),
        # --- Institutional repository: good QA, different client ---
        _record(
            "10.1234/example.dataset.42",
            title="Campus research data: survey microdata on open access attitudes",
            creators=[
                {
                    "name": "Nguyen, Linh",
                    "nameType": "Personal",
                    "givenName": "Linh",
                    "familyName": "Nguyen",
                    "nameIdentifiers": [
                        {
                            "nameIdentifier": "https://orcid.org/0000-0003-1111-2222",
                            "nameIdentifierScheme": "ORCID",
                        }
                    ],
                    "affiliation": [
                        {
                            "name": "Example University Library",
                            "affiliationIdentifier": "https://ror.org/03yrm5c26",
                            "affiliationIdentifierScheme": "ROR",
                        }
                    ],
                }
            ],
            year=2025,
            publisher={"name": "Example University Repository"},
            resource_type_general="Dataset",
            client_id="exuni.library",
            provider_id="exuni",
            subjects=[{"subject": "scholarly communication"}, {"subject": "open access"}],
            descriptions=[
                {
                    "description": "Anonymized survey responses from faculty and students.",
                    "descriptionType": "Abstract",
                }
            ],
            rights=[
                {
                    "rights": "Creative Commons Attribution 4.0",
                    "rightsUri": "https://creativecommons.org/licenses/by/4.0/",
                    "rightsIdentifier": "cc-by-4.0",
                }
            ],
            funding=[
                {
                    "funderName": "Wellcome Trust",
                    "funderIdentifier": "https://doi.org/10.13039/100010269",
                    "funderIdentifierType": "Crossref Funder ID",
                    "awardNumber": "WT-998877",
                    "awardTitle": "Open Research Practices Study",
                }
            ],
        ),
        # --- Minimal / poor quality record (many errors) ---
        _record(
            "10.1234/example.bad.1",
            title="Untitled deposit",  # title present but everything else weak
            creators=[{"name": "Unknown"}],
            year=2021,
            publisher="Example University Repository",
            resource_type_general="Other",
            client_id="exuni.library",
            provider_id="exuni",
            url=None,
            # override via attributes after build — we'll patch below
        ),
        # --- EC funded preprint supplement ---
        _record(
            "10.5281/zenodo.100004",
            title="Replication package: policy impacts on research data sharing",
            creators=[
                {
                    "name": "Okoro, Amara",
                    "nameType": "Personal",
                    "nameIdentifiers": [
                        {
                            "nameIdentifier": "https://orcid.org/0000-0002-9999-0001",
                            "nameIdentifierScheme": "ORCID",
                        }
                    ],
                }
            ],
            year=2024,
            publisher="Zenodo",
            resource_type_general="Dataset",
            client_id="cern.zenodo",
            descriptions=[
                {
                    "description": "Codebooks, scripts, and derived tables.",
                    "descriptionType": "Abstract",
                }
            ],
            rights=[
                {
                    "rights": "Creative Commons Attribution 4.0",
                    "rightsUri": "https://creativecommons.org/licenses/by/4.0/",
                }
            ],
            funding=[
                {
                    "funderName": "European Commission",
                    "funderIdentifier": "https://doi.org/10.13039/501100000780",
                    "funderIdentifierType": "Crossref Funder ID",
                    "awardNumber": "101059548",
                    "awardTitle": "AquaWatch Europe",
                }
            ],
            related=[
                {
                    "relatedIdentifier": "10.31235/osf.io/abcd1",
                    "relatedIdentifierType": "DOI",
                    "relationType": "IsSupplementTo",
                    "resourceTypeGeneral": "Preprint",
                }
            ],
        ),
        # --- Text without funder ID (compliance gap) ---
        _record(
            "10.1234/example.text.7",
            title="White paper on institutional RDM policy",
            creators=[
                {"name": "Example University Library", "nameType": "Organizational"}
            ],
            year=2023,
            publisher="Example University Repository",
            resource_type_general="Text",
            client_id="exuni.library",
            provider_id="exuni",
            descriptions=[
                {"description": "Policy recommendations.", "descriptionType": "Abstract"}
            ],
            rights=[{"rights": "All rights reserved"}],  # no URI
            funding=[{"funderName": "Internal seed grant"}],
        ),
        # --- Collection with subjects only ---
        _record(
            "10.5281/zenodo.100005",
            title="Historical weather station scans",
            creators=[
                {
                    "name": "Berg, Ingrid",
                    "nameType": "Personal",
                    "nameIdentifiers": [
                        {
                            "nameIdentifier": "https://orcid.org/0000-0001-5555-6666",
                            "nameIdentifierScheme": "ORCID",
                        }
                    ],
                }
            ],
            year=2020,
            publisher="Zenodo",
            resource_type_general="Collection",
            client_id="cern.zenodo",
            subjects=[{"subject": "meteorology"}],
            # no license, no funding, has geo place only
            geo=[{"geoLocationPlace": "Scandinavia"}],
        ),
    ]


def _patch_bad_record(records: list[dict[str, Any]]) -> None:
    """Worsen the intentionally bad record (missing title/year/publisher simulated carefully)."""
    for rec in records:
        doi = rec["data"]["id"]
        if doi == "10.1234/example.bad.1":
            attrs = rec["data"]["attributes"]
            attrs["titles"] = []  # error: missing title
            attrs["publicationYear"] = None  # error
            attrs["publisher"] = None  # error
            attrs["url"] = None
            attrs["creators"] = []  # error
            attrs["types"]["resourceTypeGeneral"] = "NotARealType"  # warning
            break


def write_mock_corpus(target_dir: Path | str | None = None) -> Path:
    """Write a complete mock monthly-style datafile tree; return root path."""
    root = Path(target_dir) if target_dir else default_mock_dir()
    partition = root / "dois" / "updated_2025-11"
    partition.mkdir(parents=True, exist_ok=True)

    records = build_mock_records()
    _patch_bad_record(records)

    part_path = partition / "part_0000.jsonl.gz"
    with gzip.open(part_path, "wt", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    csv_path = partition / "2025-11.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["doi", "state", "client_id", "updated"])
        writer.writeheader()
        for rec in records:
            attrs = rec["data"]["attributes"]
            client_id = rec["data"]["relationships"]["client"]["data"]["id"]
            writer.writerow(
                {
                    "doi": attrs["doi"],
                    "state": attrs.get("state") or "findable",
                    "client_id": client_id,
                    "updated": attrs.get("updated") or "",
                }
            )

    status = {
        "month": "2025-11",
        "datetime": "2025-12-02T08:00:00Z",
        "status": "Complete",
        "mode": "mock",
        "note": "Synthetic corpus for DataCite Librarian MCP demos and tests",
    }
    with (root / "STATUS.json").open("w", encoding="utf-8") as fh:
        json.dump(status, fh, indent=2)
        fh.write("\n")

    manifest = [
        {
            "path": "dois/updated_2025-11/part_0000.jsonl.gz",
            "size": part_path.stat().st_size,
            "sha256": "mock-not-computed",
        },
        {
            "path": "dois/updated_2025-11/2025-11.csv",
            "size": csv_path.stat().st_size,
            "sha256": "mock-not-computed",
        },
    ]
    with (root / "MANIFEST.json").open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")

    with (root / "MANIFEST").open("w", encoding="utf-8") as fh:
        for item in manifest:
            fh.write(f"{item['path']}\t{item['size']}\t{item['sha256']}\n")

    return root


def ensure_mock_corpus(target_dir: Path | str | None = None) -> Path:
    """Create mock corpus if missing; return path."""
    root = Path(target_dir) if target_dir else default_mock_dir()
    part = root / "dois" / "updated_2025-11" / "part_0000.jsonl.gz"
    if not part.exists():
        write_mock_corpus(root)
    return root


def main() -> None:
    """CLI: regenerate mock data under the resolved mock directory."""
    path = write_mock_corpus()
    print(f"Wrote mock DataCite corpus to {path}")


if __name__ == "__main__":
    main()