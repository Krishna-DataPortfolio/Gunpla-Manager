from src.collectors.fandom_allcollector import Fandom_All_Collector

def main():
    collector = Fandom_All_Collector(url="https://gunpla.fandom.com/api.php")

    collector.fetch_all(page_limit=20)

if __name__ == "__main__":
    main()