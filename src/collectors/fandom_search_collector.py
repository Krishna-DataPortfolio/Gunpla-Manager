import requests
import json
from datetime import datetime
from pathlib import Path

class Search_Collector:
    def __init__(self, url: str):
        self.url = url
        self.session = requests.Session()

    def collect(self, title:str) -> str:
        """
        Collects data from the specified URL and saves the raw response data to a JSON file
        """

        params = {
            "action" : "query",
            "format" : "json",
            "list" : "search",
            "srsearch" : title,
            "srlimit" : 20
        }

        response = self.session.get(self.url, params=params)
        response.raise_for_status()

        data = response.json()
        print(data)

        file_path = self.save_raw(title, data)

        return file_path
    
    def save_raw(self, title: str, data: dict) -> str:
        now = datetime.now().strftime("%Y-%m-%d")
        
        output_dir = Path("data/raw") / "fandom" / now
        output_dir.mkdir(parents=True, exist_ok=True)

        safe_title = title.replace(" ", "_")
        file_path = output_dir / f"{safe_title}.json"

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        return str(file_path)