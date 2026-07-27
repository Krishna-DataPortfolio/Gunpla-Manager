# Gunpla Dataset Pipeline

A modular data pipeline for collecting, parsing, and structuring **Gunpla and Bandai Plastic Model metadata** from FandomWiki pages into a clean, machine-readable dataset ready for analysis.

This project spans two phases: **scalable data collection** (querying the Gunpla Fandom wiki via the MediaWiki API and parsing infobox metadata into structured JSONL), and **data cleaning / feature engineering** (turning that raw, inconsistently-labeled wiki data into an analysis-ready DataFrame).

---

## 🚀 Features

**Collection**
- Automated page discovery via MediaWiki API
- Infobox parsing using `mwparserfromhell`
- Structured dataset generation in JSONL format
- Manual page override system for missed/edge-case entries
- Configurable infobox extraction logic
- CLI-based execution for flexible workflows

**Cleaning & Feature Engineering**
- Schema normalization across dozens of inconsistent infobox field names (editor-introduced aliases, typos, and template drift resolved into a single canonical column per concept)
- Grade inference (High Grade, Master Grade, Real Grade, Perfect Grade, Entry Grade, First Grade, Full Mechanics, Super Deformed, 30 Minute Missions/Sisters/Preference, Mega Size, Advanced Grade) derived from `classification` and `kit_name`, since grade is not a labeled infobox field
- Price parsing across multiple raw formats (`¥1,650`, `3456 yen`), with sanity bounds to catch leaked non-price values (e.g. JAN/ISBN codes mistakenly entered in the wrong field)
- Per-unit pricing (`price_per_unit_yen`) that correctly accounts for multi-kit sets, so bundles aren't miscounted as cheap single kits
- Exclusivity classification (`exclusive_channel_type`: Event / Storefront / Magazine / Campaign / Lottery) backfilled from `categories` where the dedicated infobox field was missing, roughly quadrupling usable coverage
- Relationship fields (`variant_of`, `requires_kit`, `model_of`) parsed from freeform comma/semicolon-separated text into clean list columns, with conflict detection before merging aliased fields
- Explicit missing-data handling throughout — a field is only ever treated as "genuinely not applicable" after being checked, not assumed

---

## 🧱 Project Structure
```bash
├── gunpla-manager
│   ├── src/collectors
│   │   ├── collector_util.py (Dumping the common functionality between manual/full collector in here)
│       ├── data_writer.py (For writing to the dataset file)
│       ├── discovery_util.py (Skip Logic and Discovery Search Scraping)
│       ├── fandom_allcollector.py (For querying and parsing all model kit pages from gunpla wiki)
│       ├── fandom_manual_collector.py (For manually adding pages with exact page names to an existing dataset)
│   ├── notebooks
│       ├── clean_analysis.ipynb (Data cleaning jupyter notebook)
│       ├── clean_analysis.py (Final script exported from jupyter notebooks)
│   ├── transform
│       ├── clean.py (Utility functions used by clean_analysis
├── data/ (local only directory to hold parsed data)
├── gitignore
├── README.md
├── main.py
├── requirements.md
```

---

## 🧹 Data Cleaning Notes

The raw wiki data has a handful of quirks worth knowing about if you're extending this pipeline:

- **No single infobox schema.** Different kit types (standard kits vs. figure/statue pages) and different eras of wiki editing produced different sets of infobox fields — some concepts have 2-3 differently-named aliases (`need paint?` / `need paint` / `need to paint?`, `variant of` / `variant`, `for use with` / `add-on for`) that had to be reconciled by checking for conflicts before merging, not blindly combined.
- **Grade isn't a labeled field.** It's inferred from `classification` (checked first, since it's often spelled out in full, e.g. "High Grade Iron-Blooded Orphans") with a fallback to parsing `kit_name` prefixes (e.g. "HGI-BO"). A meaningful fraction of kits (~19%) are legitimately gradeless — early/non-standard lines that predate or fall outside Bandai's grade system — and this is distinguished from a parsing failure by direct inspection, not assumed.
- **Multi-kit sets require per-unit pricing.** A single `price` field can cover 2+ mobile suits in one box; `kit_count` (from the length of `model_of`) and `price_per_unit_yen` normalize for this so bundle pricing doesn't distort price analysis.
- **`categories` is a reliable secondary signal** for backfilling sparse infobox fields — used to recover exclusivity information for kits where the dedicated `exclusive to` field was blank but the exclusivity was still recorded as a category tag.
- **Some kit pages return non-standard infobox shapes** (positional/unnamed template parameters, e.g. keys literally named `"1"` and `"2"`) rather than the expected named fields — these are wiki template artifacts from inconsistent editing, not artifacts of the collector, and are excluded from the canonical schema.

---

## 📓 Notebooks

- `notebooks/clean_analysis.ipynb` — the full exploratory cleaning process: schema discovery, alias reconciliation, conflict checks, grade/price/date parsing, and validation at each step.
- `notebooks/clean_analysis.py` — a reproducible script version, callable independently of the notebook (`python clean_analysis.py --input data/raw/gunpla.jsonl --output data/processed/gunpla_clean.csv`).
- `transform/clean.py` — the underlying utility functions (`infer_grade`, `parse_price`, `parse_release_year`, alias-merge helpers, exclusivity classification) imported by both the notebook and the script, so cleaning logic lives in one place.
