import argparse
from src.collectors.fandom_allcollector import Fandom_All_Collector
from src.collectors.fandom_manual_collector import ManualPageCollector

DEFAULT_URL = "https://gunpla.fandom.com/api.php"


def run_full_parse(url: str, mode: str):
    collector = Fandom_All_Collector(url=url)
    collector.fetch_all(mode=mode)

def run_manual(url: str, output_file: str, pages: list[str]):
    base_collector = Fandom_All_Collector(url=url)
    manual_collector = ManualPageCollector(base_collector=base_collector, output_file=output_file)
    manual_collector.append_manual_pages(pages)


def main():
    parser = argparse.ArgumentParser(description="Gunpla Data Pipeline")
    subparser = parser.add_subparsers(dest="command", required=True)


    ## ----- FULL QUERY AND PARSE

    full_parser = subparser.add_parser("full", help="Run full Wiki Data Collection")
    full_parser.add_argument(
        "--mode",
        choices=["full", "discovery"],
        default="full",
        help="Full Collection or Discovery (Recommended first time to catch specific infobox names)"
    )
    full_parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help="Fandom API Url"
    )

    ## ----- MANUAL INSERT COMMAND

    manual_parser = subparser.add_parser("manual", help="Append exact page manually")
    manual_parser.add_argument(
        "--pages",
        nargs="+",
        required=True,
        help="List of exact page names"
    )

    manual_parser.add_argument(
        "--output",
        required=True,
        help="Output JSONL file"
    )
    manual_parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help="Fandom API URL"
    )

    args = parser.parse_args()

    if args.command == "full":
        run_full_parse(url=args.url, mode=args.mode)
    
    elif args.command == "manual":
        run_manual(url=args.url, output_file=args.output, pages=args.pages)     
       
if __name__ == "__main__":
    main()


