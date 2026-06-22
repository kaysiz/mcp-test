# Local datafiles (gitignored)

Put **your** DataCite monthly or public datafile extracts here. This directory is **ignored by git** so large or member-only files are never committed.

## Quick setup

1. Download/extract datafiles per the main [README](../../README.md#obtain-datacite-datafiles).
2. Either:
   - **Recommended layout** (matches DataCite releases):

     ```text
     data/local/
       dois/
         updated_2026-06/
           2026-06.csv.gz
           part_0000.jsonl.gz
           part_0001.jsonl.gz
           …
     ```

   - **Flat layout** (also supported by this MCP):

     ```text
     data/local/
       2026-06.csv.gz
       part_0000.jsonl.gz
     ```

3. Point the MCP at this folder:

   ```bash
   export DATACITE_DATA_DIR="$(pwd)/data/local"
   uv run datacite-librarian-mcp
   ```

## Official documentation

- Portal: https://datafiles.datacite.org  
- Public (annual) file: https://support.datacite.org/docs/datacite-public-data-file  
- Monthly file (members): https://support.datacite.org/docs/datacite-monthly-data-file  

Do **not** commit contents of this directory.