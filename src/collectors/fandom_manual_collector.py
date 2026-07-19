import requests
import json
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from src.collectors.collector_util import Collector_Util
from src.collectors.discovery_util import Discovery_Util
from src.collectors.data_writer import Dataset_Writer

class ManualPageCollector:
    def __init__(self, base_collector, output_file: str):
        """
        base_collector: your existing fandom_allcollector instance
        output_file: path to your JSONL file
        """
        self.collector = base_collector
        self.output_file = output_file
        self.parser = Collector_Util(url="https://gunpla.fandom.com/api.php")

    def _fetch_page_by_title(self, title: str):
        """
        Fetch a single page using MediaWiki API
        """
        params = {
            "action": "parse",
            "format": "json",
            "page": title,
            "prop": "wikitext|categories"
        }

        response = self.collector.session.get(self.collector.url, params=params)
        response.raise_for_status()
        return response.json()

    def _parse_page(self, raw_data: dict, title: str):
        """
        Reuse your existing parsing logic
        """
        try:
            parse = raw_data.get("parse", {})
            wikitext = parse.get("wikitext", {}).get("*", "")
            categories = [c["*"] for c in parse.get("categories", [])]

            # 👇 IMPORTANT: reuse your existing parser
            parsed_data = self.parser.parse_page(
                title=title,
                wikitext=wikitext
            )

            return parsed_data

        except Exception as e:
            print(f"[MANUAL ERROR] {title}: {e}")
            return None

    def append_manual_pages(self, page_titles: List[str]):
        """
        Main entry: fetch + parse + append to JSONL
        """
        added = 0

        with open(self.output_file, "a", encoding="utf-8") as f:
            for title in page_titles:
                try:
                    raw = self._fetch_page_by_title(title)
                    parsed = self._parse_page(raw, title)

                    if not parsed:
                        print(f"[SKIP - NO PARSE] {title}")
                        continue

                    # 👇 bypass your strict filters here if needed
                    json.dump(parsed, f, ensure_ascii=False)
                    f.write("\n")

                    added += 1
                    print(f"[ADDED] {title}")

                except Exception as e:
                    print(f"[FAIL] {title}: {e}")

        print(f"\n✅ Added {added}/{len(page_titles)} manual pages")