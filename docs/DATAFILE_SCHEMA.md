# DataCite datafile schema

This document describes the **monthly** and **public (annual)** DataCite data
files that this MCP reads. Official sources:

| Resource | URL |
|----------|-----|
| Public data file | https://support.datacite.org/docs/datacite-public-data-file |
| Monthly data file | https://support.datacite.org/docs/datacite-monthly-data-file |
| Download portal | https://datafiles.datacite.org |
| XML ↔ JSON mapping | https://support.datacite.org/docs/datacite-xml-to-json-mapping |
| Metadata schema | https://schema.datacite.org |

Metadata in these files is generally released under **CC0**. Always confirm the
current license and access policy on DataCite Support.

---

## 1. Two distributions, one logical shape

| | Public data file | Monthly data file |
|--|------------------|-------------------|
| **Cadence** | Annual snapshot (e.g. `public-2025`) | Every month (prior month end) |
| **Access** | Open (all public/Findable DOIs) | Members & consortium orgs (S3 + API credentials) |
| **Content** | All Findable DOIs up to year end | All publicly available DOIs up to end of last month |
| **Format** | TAR of `dois/updated_YYYY-MM/` partitions | S3 bucket with same partition style |
| **Typical use** | Initial bulk load, research, analytics | Fresher incremental updates |

This MCP treats both as a **local directory tree** after you extract/download
them. It does **not** call the live DataCite REST API at runtime.

---

## 2. Directory layout

```
<data_root>/
├── STATUS.json              # Optional: build status for the release
├── MANIFEST                 # Optional: TSV of path, size, sha256
├── MANIFEST.json            # Optional: same as JSON array
└── dois/
    ├── updated_2024-01/
    │   ├── 2024-01.csv.gz   # Tabular index for this partition
    │   ├── part_0000.jsonl.gz
    │   ├── part_0001.jsonl.gz
    │   └── ...
    ├── updated_2024-02/
    │   └── ...
    └── updated_2025-11/
        ├── 2025-11.csv      # Mock corpus uses uncompressed CSV
        └── part_0000.jsonl.gz
```

### 2.1 `STATUS.json` (example)

```json
{
  "month": "2025-11",
  "datetime": "2025-12-02T08:00:00Z",
  "status": "Complete"
}
```

Statuses you may see in real files: `In progress`, `Uploading`, `Complete`.

### 2.2 Partition folders (`updated_YYYY-MM`)

Records are grouped by the **month the DOI metadata was last updated**, not
necessarily the publication year. To scan everything, walk all partitions.

### 2.3 CSV index (`YYYY-MM.csv` / `.csv.gz`)

Lightweight tabular report, typically columns:

| Column | Description |
|--------|-------------|
| `doi` | DOI string |
| `state` | e.g. `findable`, `registered` |
| `client_id` | Repository / client identifier |
| `updated` | Last update timestamp |

Useful for fast filtering before opening heavy JSONL parts. This MCP primarily
streams JSONL; CSV helpers exist in `stream_reader.iter_csv_file`.

### 2.4 JSONL parts (`part_NNNN.jsonl.gz`)

- One JSON object per line (JSON Lines).
- Gzip-compressed in production releases.
- Often **up to ~10,000 records per part** (implementation detail; do not hardcode).
- Stream line-by-line; never load the entire part list into memory at once.

---

## 3. Record shape (per JSONL line)

Each line mirrors a **DataCite REST API singleton** response for
`GET https://api.datacite.org/dois/{doi}` with adjustments common to bulk
exports:

- Expanded `affiliation` and `publisher` (equivalent to `affiliation=true&publisher=true`)
- Often **no** large `xml` attribute (saves space)
- Schema version evolves with the live Metadata Schema (kernel-4.x)

### 3.1 Top level

```json
{
  "data": {
    "id": "10.5281/zenodo.100001",
    "type": "dois",
    "attributes": { },
    "relationships": { }
  }
}
```

| Path | Type | Notes |
|------|------|-------|
| `data.id` | string | DOI |
| `data.type` | string | Always `dois` in these files |
| `data.attributes` | object | Core metadata + admin + metrics |
| `data.relationships` | object | Links to client, provider, etc. |

### 3.2 `relationships` (librarian-relevant)

```json
"relationships": {
  "client": { "data": { "id": "cern.zenodo", "type": "clients" } },
  "provider": { "data": { "id": "cern.zenodo", "type": "providers" } }
}
```

| Field | Use in this MCP |
|-------|-----------------|
| `client.data.id` | Repository filter (`client_id`) for QA by repository |
| `provider.data.id` | Consortium / member provider |

### 3.3 `attributes` — mandatory / core metadata

| Field | Type | QA relevance |
|-------|------|----------------|
| `doi` | string | Identity |
| `creators` | array of objects | **Required**; ORCID / ROR checks |
| `titles` | array of objects | **Required** |
| `publisher` | object or string | **Required** (object with `name` when expanded) |
| `publicationYear` | int / string | **Required** |
| `types.resourceTypeGeneral` | string | **Required**; controlled vocabulary |
| `url` | string | Landing page; warned if missing |
| `state` | string | Usually `findable` in public file |

#### `creators[]` item (typical)

```json
{
  "name": "Rivera, Ana",
  "nameType": "Personal",
  "givenName": "Ana",
  "familyName": "Rivera",
  "nameIdentifiers": [
    {
      "nameIdentifier": "https://orcid.org/0000-0002-1825-0097",
      "nameIdentifierScheme": "ORCID",
      "schemeUri": "https://orcid.org"
    }
  ],
  "affiliation": [
    {
      "name": "Example University",
      "affiliationIdentifier": "https://ror.org/03yrm5c26",
      "affiliationIdentifierScheme": "ROR",
      "schemeUri": "https://ror.org"
    }
  ]
}
```

#### `titles[]` item

```json
{ "title": "Global Lake Temperature Time Series", "titleType": null, "lang": "en" }
```

#### `publisher` (expanded)

```json
{
  "name": "Zenodo",
  "publisherIdentifier": "https://ror.org/01ggx4157",
  "publisherIdentifierScheme": "ROR",
  "schemeUri": "https://ror.org"
}
```

#### `types`

```json
{
  "resourceTypeGeneral": "Dataset",
  "resourceType": "Lake observations",
  "schemaOrg": "Dataset",
  "bibtex": "misc",
  "citeproc": "dataset",
  "ris": "DATA"
}
```

### 3.4 `attributes` — recommended / compliance-critical

| Field | Type | Librarian / compliance use |
|-------|------|----------------------------|
| `subjects` | array | Discoverability, subject coverage |
| `descriptions` | array | Abstracts; QA warns if missing |
| `rightsList` | array | **Licensing / open access policy** |
| `fundingReferences` | array | **Funder compliance** |
| `relatedIdentifiers` | array | Links to papers, versions, software |
| `relatedItems` | array | Richer related works (schema 4.x) |
| `geoLocations` | array | Spatial datasets / images |
| `contributors` | array | Additional roles |
| `dates` | array | Issued, collected, embargo, etc. |
| `language` | string | ISO language code |
| `alternateIdentifiers` | array | Handles, accession numbers |
| `sizes` / `formats` / `version` | various | Technical metadata |

#### `rightsList[]` item

```json
{
  "rights": "Creative Commons Attribution 4.0",
  "rightsUri": "https://creativecommons.org/licenses/by/4.0/",
  "rightsIdentifier": "cc-by-4.0",
  "rightsIdentifierScheme": "SPDX",
  "schemeUri": "https://spdx.org/licenses/"
}
```

#### `fundingReferences[]` item

```json
{
  "funderName": "European Commission",
  "funderIdentifier": "https://doi.org/10.13039/501100000780",
  "funderIdentifierType": "Crossref Funder ID",
  "awardNumber": "101059548",
  "awardTitle": "AquaWatch Europe",
  "awardUri": "https://cordis.europa.eu/project/id/101059548"
}
```

#### `relatedIdentifiers[]` item

```json
{
  "relatedIdentifier": "10.1038/s41586-024-00001",
  "relatedIdentifierType": "DOI",
  "relationType": "IsSupplementTo",
  "resourceTypeGeneral": "JournalArticle"
}
```

#### `geoLocations[]` item (variants)

```json
{
  "geoLocationPlace": "Europe",
  "geoLocationPoint": { "pointLongitude": "10.0", "pointLatitude": "50.0" },
  "geoLocationBox": {
    "westBoundLongitude": "-10.0",
    "eastBoundLongitude": "40.0",
    "southBoundLatitude": "35.0",
    "northBoundLatitude": "70.0"
  }
}
```

### 3.5 `attributes` — administrative & metrics

| Field | Notes |
|-------|-------|
| `prefix` / `suffix` | Split DOI |
| `schemaVersion` | e.g. `http://datacite.org/schema/kernel-4` |
| `metadataVersion` | Integer revision |
| `created` / `registered` / `updated` / `published` | Timestamps / year |
| `isActive` | Boolean |
| `source` | Registration pathway (e.g. `mds`) |
| `citationCount` / `viewCount` / `downloadCount` | Usage metrics when available |
| `referenceCount` / `partCount` / `versionCount` | Relation tallies |
| `*OverTime` arrays | Time-series metrics (may be present on live API; variable in files) |

---

## 4. Controlled vocabularies (selected)

`resourceTypeGeneral` values evolve with the Metadata Schema. Common values
include: `Dataset`, `Software`, `Text`, `Collection`, `Image`, `Audiovisual`,
`Event`, `PhysicalObject`, `InteractiveResource`, `Workflow`, `Service`,
`Model`, `Book`, `BookChapter`, `JournalArticle`, `Preprint`, `Report`,
`Dissertation`, `PeerReview`, `ConferencePaper`, `OutputManagementPlan`,
`Instrument`, `StudyRegistration`, `Award`, `Project`, `Other`, and others
added in schema 4.x.

`relationType` examples: `IsCitedBy`, `Cites`, `IsSupplementTo`, `IsSupplementedBy`,
`IsVersionOf`, `HasVersion`, `IsPartOf`, `HasPart`, `References`, `IsReferencedBy`.

Validate against the current schema docs rather than this snapshot.

---

## 5. How this MCP reads the files

1. Resolve `DATACITE_DATA_DIR` (or generate/use `data/mock/`).
2. Discover `dois/updated_*/` partitions.
3. For each partition, open `part_*.jsonl.gz` with **streaming** gzip + line iteration.
4. `json.loads` **one line at a time**; run QA/compliance; discard the record.
5. Respect `max_records` / `DATACITE_MAX_RECORDS` so agents get bounded responses.

No database is required. Dependencies stay minimal (`fastmcp`, `pydantic`, stdlib).

---

## 6. Mock corpus (`data/mock/`)

For demos and tests, `datacite_librarian_mcp.mock_data` writes a miniature corpus
with the same layout:

- 8 synthetic DOIs spanning two `client_id`s (`cern.zenodo`, `exuni.library`)
- Mix of good/bad QA patterns and funder completeness levels
- `STATUS.json` with `"mode": "mock"`

Regenerate:

```bash
uv run python -m datacite_librarian_mcp.mock_data
# or via MCP tool: regenerate_mock_data
```

---

## 7. Obtaining real datafiles

### Public annual file

1. Visit https://datafiles.datacite.org
2. Download the latest public release (TAR)
3. Extract to a local directory, e.g. `~/data/datacite/public-2025/`
4. Point the MCP at the directory that contains `dois/` (or the extracted root):

```bash
export DATACITE_DATA_DIR=~/data/datacite/public-2025
uv run datacite-librarian-mcp
```

### Monthly file (members)

1. Obtain temporary AWS credentials via DataCite API (`/credentials/datafile`)
2. Sync from the monthly datafile S3 bucket (see DataCite Support docs)
3. Set `DATACITE_DATA_DIR` to the synced root

Storage note: production files are **large** (tens of GB+). Stream reading avoids
RAM spikes, but disk space and first-scan time remain real constraints. Start with
one partition or rely on `max_records` while validating workflows.

---

## 8. Versioning & compatibility

- Schema fields are additive over time; parsers should tolerate unknown keys.
- This MCP normalizes both `data.attributes` records and (if ever seen) flatter shapes.
- When in doubt, compare a sample line to `GET https://api.datacite.org/dois/{doi}`.
