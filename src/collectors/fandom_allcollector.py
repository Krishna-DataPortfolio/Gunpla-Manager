import requests
import json
from datetime import datetime
from pathlib import Path

class Fandom_All_Collector:
    def __init__(self, url: str):
        self.url = url
        self.session = requests.Session()

    def fetch_all(self, page_limit : int=None):
        """
        Gets every page from the wiki via allpages
        fetch full page content
        """
        all_page_data = []
        pages = self._fetch_all_pages(page_limit)

        print(f"{Fandom_All_Collector} fetched {len(pages)} pages from {self.url}")
        for i, page in enumerate(pages):

            title = page["title"]

            try:
                data = self.fetch_page(title)
                if self.skip_page(data):
                    continue
                self._save_raw_data(title, data)
                print(f"[{(i+1)/len(pages)}] Fetched and Saved for {title}")

            except Exception as e:
                print(f"[ERROR] {title}: {e}")


    def _fetch_all_pages(self, page_limit: int=None):
        """
        Use MediaWiki AllPages API to get all pages from the wiki
        """
        pages = []
        keep_going = None
        while True:
            params = {
                "action": "query",
                "format": "json",
                "list": "allpages",
                "redirects": 1,
                "aplimit": 500,
                "apnamespace": 0
            }

            if keep_going:
                params["accontinue"] = keep_going

            response = self.session.get(self.url, params=params)
            response.raise_for_status()

            data = response.json()

            batch = data.get("query", {}).get("allpages", [])
            pages.extend(batch)

            # Temporary block to prevent fetching too many for testing
            if page_limit and len(pages) >= page_limit:
                return pages[:page_limit]
            
            continue_data = data.get("continue")
            if not continue_data:
                break
            
            keep_going = continue_data.get("accontinue")
        return pages

    def fetch_page(self, title: str):
        """
        Fetch content for single page
        """

        params = {
            "action": "query",
            "format": "json",
            "titles": title,
            "prop": "revisions",
            "redirects": 1,
            "rvprop": "content",
            "rvslots": "main"
        }

        response = self.session.get(self.url, params=params)
        response.raise_for_status()

        return response.json()
    
    def _save_raw_data(self, title: str, data: dict) -> str:
        now = datetime.now().strftime("%Y-%m-%d")

        output_dir = Path("data/raw") / "fandom" / now
        output_dir.mkdir(parents=True, exist_ok=True)

        safe_title = title.replace(" ", "_").replace("/", "_")
        file_path = output_dir / f"{safe_title}.json"

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return str(file_path)
    

    def skip_page(self, json_data: dict) -> bool:
        """
        Check if the current page is a disambiguation page:
        I.E. "Did you mean to search for one of these kits?
        HOWEVER, there are instances where a page may be a disambiguation but still have product details (maybe the kit is discontinued or something)
        """
        content = None
        pages = json_data.get("query", {}).get("pages", {}) # Technically there will only be one page at this point
        for id, page in pages.items():
            revisions = page.get("revisions")
            if not revisions:
                return True
            content = revisions[0].get("slots", {}).get("main", {}).get("*")

        if not isinstance(content, str):
            return True
        
        return "{{plamo_infobox" not in content.lower()