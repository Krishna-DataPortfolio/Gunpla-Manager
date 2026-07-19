# Gunpla Dataset Pipeline

A modular data pipeline for collecting, parsing, and structuring **Gunpla and Bandai Plastic Model metadata** from FandomWiki pages into a clean, machine-readable JSONL dataset.

This project focuses on **scalable data collection, structured parsing, and dataset generation** for 

---

## 🚀 Features

- Automated page discovery via MediaWiki API
- Infobox parsing using `mwparserfromhell`
- Structured dataset generation in JSONL format
- Manual page override system for missed/edge-case entries
- Configurable infobox extraction logic
- CLI-based execution for flexible workflows
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
├── data/ (local only directory to hold parsed data)
├── gitignore
├── README.md
├── main.py
├── requirements.md

```
