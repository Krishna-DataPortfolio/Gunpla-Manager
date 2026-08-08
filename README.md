# Gunpla Dataset Pipeline

A modular data pipeline for collecting, cleaning, modeling, loading, and orchestrating **Gunpla and Bandai Plastic Model metadata** from the Gunpla Fandom wiki into structured datasets and data warehouses ready for analysis.

The project spans four phases: **collection** (MediaWiki API scraping + infobox parsing into JSONL), **cleaning** (turning inconsistently-labeled wiki data into an analysis-ready DataFrame), **warehousing** (loading into PostgreSQL and BigQuery), and **orchestration** (an Airflow DAG tying the whole pipeline together).

---

## 🚀 Features

**Collection**
- Automated page discovery via MediaWiki API, infobox parsing via `mwparserfromhell`, JSONL output
- Manual page override system for missed/edge-case entries

**Cleaning & Feature Engineering**
- Schema normalization across dozens of inconsistent infobox field aliases (editor drift, typos) into single canonical columns
- Grade inference (HG, MG, RG, PG, EG, FG, FM, SD, 30MM/30MS/30MP, Mega Size, Advanced Grade) derived from `classification`/`kit_name`, since grade isn't a labeled field — ~19% of kits are legitimately gradeless, confirmed by direct inspection rather than assumed
- Multi-currency price parsing (¥/$, multiple raw formats) with sanity bounds and manual overrides for confirmed source-data errors
- Per-unit pricing (`price_per_unit_yen`) accounting for multi-kit sets, so bundles aren't miscounted as cheap singles
- Exclusivity classification backfilled from `categories` where the dedicated field was blank, ~4x usable coverage
- Relationship fields (`variant_of`, `requires_kit`, `model_of`) parsed into clean list columns, with conflict detection before merging aliases

**Warehousing & Cloud**
- **PostgreSQL:** normalized star schema (fact table + grade/scale/franchise/exclusivity dimensions), loaded via idempotent upsert on a natural key — verified by re-running the load and confirming stable row counts
- **BigQuery:** deliberately denormalized wide table, reflecting OLAP's different cost/query model vs. an OLTP database
- **Google Cloud Storage:** landing zone for raw + processed data, authenticated via Application Default Credentials (no long-lived key file)

**Orchestration**
- A single Airflow DAG (via Astronomer's local runtime): extract → clean → parallel loads into Postgres, GCS/BigQuery, and the dashboard data refresh
- Retries and explicit failure propagation, so a failed task blocks its downstream dependents rather than allowing partial runs

**Presentation**
- Live GitHub Pages dashboard, driven by a regeneratable JSON summary rather than hardcoded figures

---

## 🧱 Project Structure
```bash
├── gunpla-manager
│   ├── src/collectors
│   │   ├── collector_util.py (shared logic between manual/full collectors)
│       ├── data_writer.py (writes to the dataset file)
│       ├── discovery_util.py (skip logic + discovery search scraping)
│       ├── fandom_allcollector.py (queries/parses all model kit pages)
│       ├── fandom_manual_collector.py (manual page overrides)
│   ├── transform
│       ├── clean.py (shared cleaning utilities: infer_grade, parse_price, alias-merge helpers)
│       ├── clean_analysis.py (raw JSONL -> cleaned CSV, CLI script)
│       ├── generate_dashboard_data.py (cleaned CSV -> docs/assets/data.json)

│   ├── dags
│       ├── gunpla_pipeline_dag.py (Airflow DAG orchestrating the full pipeline)
│   ├── docs
│       ├── index.html (GitHub Pages dashboard)
│       ├── assets/data.json (generated dashboard data)
│   ├── data
│       ├── db
│           ├── schema.sql (PostgreSQL star schema DDL)
│           ├── load_to_postgres.py (idempotent upsert into Postgres)
│           ├── upload_to_gcs.py (raw + cleaned data -> GCS)
│       ├── processed
│           ├── Cleaned_Gunpla_Dataset.csv (Cleaned bandai model dataset csv)

├── Dockerfile, requirements.txt, packages.txt, docker-compose.override.yml (Astro/Airflow runtime config)
├── .env.example
├── .gitignore
├── README.md
├── main.py
├── requirements.md
```

---

## 🧹 Data Cleaning Notes

Worth knowing if you're extending this pipeline:

- **No single infobox schema** — different kit types and editing eras produced different field sets; several concepts have 2-3 differently-named aliases, reconciled by checking for conflicts before merging, never blindly combined.
- **Grade isn't a labeled field** — inferred from `classification` first, then `kit_name`. Missing grade is a real, confirmed category (~19%), not a parsing gap.
- **Multi-kit sets need per-unit pricing** — one `price` field can cover 2+ suits in a box; `kit_count`/`price_per_unit_yen` normalize for it.
- **`categories` is a reliable secondary signal** for backfilling sparse fields (e.g. recovering exclusivity info where the dedicated field was blank).
- **Some infobox shapes are non-standard** (positional/unnamed template params) — wiki template artifacts, excluded from the canonical schema rather than forced into it.
- **Generic env var names can collide across tools** — Postgres connection vars are namespaced (`GUNPLA_PG*`) to avoid clashing with Airflow's own internal metadata database when both run in the same container environment.

---

## 🔧 Pipeline & Orchestration

- `db/load_to_postgres.py` and `db/upload_to_gcs.py` are standalone CLI scripts, each independently runnable and idempotent (safe to rerun without creating duplicates).
- `dags/gunpla_pipeline_dag.py` sequences the full pipeline in Airflow (via `astro dev start`): extraction and cleaning run sequentially, then Postgres load, GCS/BigQuery load, and the dashboard refresh run in parallel, since none depend on each other — only on cleaned data existing.
- Local orchestration runs in Docker via the Astro CLI; GCP authentication uses Application Default Credentials, mounted into the containers via `docker-compose.override.yml` rather than a committed key file.
