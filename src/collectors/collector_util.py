from bs4 import BeautifulSoup
import mwparserfromhell
import requests
import json
from pathlib import Path

class Collector_Util:
    def __init__(self, url: str, infobox_path="data\infoboxes.json"):
        self.session = requests.Session()
        self.url = url
        self.infobox_path = Path(infobox_path)
        self.infobox_names = self.load_infobox_names()

    def load_infobox_names(self) -> set:
        INFOBOX_NAMES = set()
        if not self.infobox_path.exists():
            print("[WARNING] No infobox file found - Ensure discovery is done first")
        else:
            print("[INFO] Infoboxes found!")
            with open(self.infobox_path) as f:
                INFOBOX_NAMES = set(name.strip().lower() for name in json.load(f))
        return INFOBOX_NAMES

    def parse_page(self, title: str, wikitext: str) -> dict | None:
        """ 
        Parse the page content to extract relevant information 
        """ 
        if wikitext is None: 
            print(f"[ERROR] {title}: No wikitext content found") 
        image = self.get_image_url(wikitext) 
        categories = self.extract_categories(wikitext) 
        data = { 
            "kit_name": title, 
            "image" : { 
                "url" : image 
            }, 
            "categories" : categories, 
            "infobox" : {} 
        }
        
        code = mwparserfromhell.parse(wikitext)
        infobox = None
        for template in code.filter_templates():
            name = str(template.name).strip().lower()

            if "infobox" in name:
                infobox = template
                break
        

        for param in infobox.params:
            key = str(param.name).strip().lower()
            val = mwparserfromhell.parse(str(param.value)).strip_code().strip()
            if key:
                data['infobox'][key] = val

        return data
    
    def get_html(self, json_data: dict) -> str:
        """
        Extract the HTML content from parsed JSON Data
        """
        html = json_data.get("parse", {}).get("text", {}).get("*")
        return html if isinstance(html, str) else None
    
    def get_image_url(self, wikitext: str) -> str:
        """
        Extract the image URL from queried JSON Data
        """
        filename = self.get_img_from_infobox(wikitext)
        params = {
            "action": "query",
            "format": "json",
            "titles": f"File:{filename}",
            "prop": "imageinfo",
            "iiprop": "url"
        }

        r = self.session.get(self.url, params=params)
        r.raise_for_status()
        data = r.json()

        pages = data.get("query", {}).get("pages", {})
        page = next(iter(pages.values()), {})

        imageInfo = page.get("imageinfo", [])
        if not imageInfo:
            return None
        return imageInfo[0].get("url")
    
    def get_img_from_infobox(self, wikitext: str):
        template = self.get_plamo_infobox(wikitext)
        if not template:
            return None

        if template.has("image"):
            return template.get("image").value.strip_code().strip()
    
    def get_plamo_infobox(self, wikitext: str):
        code = mwparserfromhell.parse(wikitext)
        for template in code.filter_templates():
            if self.get_relevant_infobox(template):
                return template
        return None
    
    def get_relevant_infobox(self, template) -> bool:
        name = str(template.name).strip().lower().replace("_"," ")

        if "infobox" not in name:
            return False
        
        return any(keyword in name for keyword in self.infobox_names)


    def extract_categories(self, wikitext: str) -> list:
        code = mwparserfromhell.parse(wikitext)
        categories = []
        for link in code.filter_wikilinks():
            title = str(link.title).strip()
            if title.lower().startswith("category:"):
                category = title.split(":", 1)[1]
                categories.append(category)
        return categories