from pathlib import Path
import json
from datetime import datetime


class Dataset_Writer:
    def __init__(self):
        now = datetime.now().strftime("%Y-%m-%d")
        self.output_path = Path("data/final") / f"bandai_dataset_{now}.json"
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: dict):
        """
        Append a record to the dataset file
        """
    
        with open(self.output_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")




#wikitext = json["parse"]["wikitext"]["*"]