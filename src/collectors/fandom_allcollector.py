import requests
import json
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from src.collectors.collector_util import Collector_Util
from src.collectors.discovery_util import Discovery_Util
from src.collectors.data_writer import Dataset_Writer


class Fandom_All_Collector:
    def __init__(self, url: str):
        self.url = url
        self.session = requests.Session()
        self.collector_util = Collector_Util(url=url)
        self.discovery_util = Discovery_Util(url=url)
        self.seen_infoboxes = set()
        self.data_writer = Dataset_Writer()

    def fetch_all(self, page_limit : int=None, mode="full"):
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
                wikitext = data["parse"]["wikitext"]["*"]

                if not wikitext:
                    print(f"[PRE-PARSE SKIP] {title}: Skipping page due to missing wikitext")
                    continue
                
                parsed_data = self.collector_util.parse_page(title, wikitext)
                if self.skip_page(title, parsed_data):
                    continue
                if mode == "full":
                    self.data_writer.append(parsed_data)
                    #self._save_raw_data(title, data, parsed_data)
                    #print(f"[{(i+1)/len(pages)}] Fetched and Saved for {title}")
                elif mode == "discovery":
                    infobox = self.discovery_util.extract_data(wikitext)
                    #print(f"[{(i+1)/len(pages)}] Discovering infobox for {title}")
                    if infobox:
                        self.seen_infoboxes.add(infobox)
                    else:
                        print(f"[SKIP] {title}: No infobox found")
                    
            except Exception as e:
                print(f"[ERROR] {title}: {e}")

        if mode == "discovery":
            with open("data\infoboxes.json", "w") as f:
                json.dump(sorted(self.seen_infoboxes), f, indent=2)
                print("Adding all discovered infoboxes to data/infoboxes.json")
                
    def _fetch_all_pages(self, page_limit: int=None):
        """
        Use MediaWiki AllPages API to get all pages from the wiki
        """
        pages = []
        seen = set()
        keep_going = None
        last_continue = None

        while True:
            params = {
                "action": "query",
                "format": "json",
                "list": "allpages",
                "aplimit": "max",
                "apnamespace": 0,
                "apfilterredir": "nonredirects"
            }

            if keep_going:
                params["apcontinue"] = keep_going

            response = self.session.get(self.url, params=params)
            response.raise_for_status()

            data = response.json()

            batch = data.get("query", {}).get("allpages", [])
            
            # Detect stagnation:
            print(f"[FETCH] batch size: {len(batch)}")

            for page in batch:
                title = page["title"].strip()
                if title in seen:
                    continue

                seen.add(title)
                pages.append(page)

            # Temporary block to prevent fetching too many for testing
                if page_limit and len(pages) >= page_limit:
                    return pages[:page_limit]
            
            continue_data = data.get("continue")
            
            if not continue_data:
                break
            
            keep_going = continue_data.get("apcontinue")

            if keep_going == last_continue:
                print(f"[WARN] Potential infinite loop, breaking here")
            
            last_continue = keep_going

            print(f"[CONTINUE] -> {keep_going}")


        
        print(f"[DONE] total pages fetched {len(pages)}")
        return pages

    def fetch_page(self, title: str):
        """
        Fetch content for single page
        """

        params = {
            "action": "parse",
            "format": "json",
            "page": title,
            "prop": "wikitext",
            "redirects": 1
        }

        response = self.session.get(self.url, params=params)
        response.raise_for_status()
        
        return response.json()
    
    def _save_raw_data(self, title: str, data: dict, parsed_data: dict) -> str:
        now = datetime.now().strftime("%Y-%m-%d")

        raw_output_dir = Path("data/raw") / "fandom" / now
        raw_output_dir.mkdir(parents=True, exist_ok=True)
        parsed_output_dir = Path("data/parsed") / "fandom" / now
        parsed_output_dir.mkdir(parents=True, exist_ok=True)

        # I want to call a separate file to parse the data, and save the raw and parsed data separately
        # infobox = parse_infobox(data) -> Parses the revision / slots / main content / * data and returns a dict of the infobox data



        safe_title = title.replace(" ", "_").replace("/", "_")
        file_path = raw_output_dir / f"{safe_title}.json"

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        

        if parsed_data:
            parsed_path = parsed_output_dir / f"{safe_title}.json"
            with open(parsed_path, "w", encoding="utf-8") as f:
                json.dump(parsed_data, f, ensure_ascii=False, indent=2)


        return str(file_path)
    

    def skip_page(self, title, parsed_data: dict) -> bool:
        """
        IF ANY OF THE FOLLOWING IS TRUE:
        - If the page doesn't have a category for gunpla or model kit
        - The page doesn't have an infobox with related product data
        - the parsed_data object is None

        WE SKIP THE PAGE
        """
        if not parsed_data or not self.discovery_util.check_plamo_category(parsed_data.get("categories", [])) or not self.discovery_util.check_plamo_infobox(parsed_data):
            print(f"[POST-PARSE SKIP] Skipping {title} due to failing criteria")
            return True
        return False
        
        
        

    

