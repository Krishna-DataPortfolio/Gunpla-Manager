
import requests
import json
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from src.collectors.collector_util import Collector_Util
import mwparserfromhell

class Discovery_Util:
    def __init__(self, url: str):
        self.session = requests.Session()
        self.url = url

    def extract_data(self, wikitext: str):
        """
        Extract data for discovery from JSON
        [Infobox Name]
        """
        code = mwparserfromhell.parse(wikitext)
        for template in code.filter_templates():
            name = str(template.name).strip().lower().replace("_"," ")
            if ":" in name:
                name = name.split(":", 1)[1]
            if "infobox" in name:
                return name
        return None
    
    def check_plamo_category(self, categories: list[str]) -> bool:
        """
        Check if the page is a plamo kit by looking at categories and infoboxes
        """
        criteria = ["gunpla", "plastic model", "kit"]
        categories = [c.lower() for c in categories]
        return any("gunpla" in c or "plastic model" in c or "kit" in c for c in categories)
    
    def check_plamo_infobox(self, data: dict) -> bool:
        """
        Check if the page is a plamo kit by looking at relevant product information
        """
        infobox = data.get("infobox", {})
        return "scale" in infobox