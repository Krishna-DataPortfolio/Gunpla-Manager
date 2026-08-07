"""

Upload to Google Cloud Storage


Uploads the raw JSONL and cleaned CSV to Google Cloud Storage.
Uses ADC so no key files


"""

import argparse
import os 
import sys
from datetime import date
from dotenv import load_dotenv
from google.cloud import storage

load_dotenv()

def get_client() -> storage.Client:
    project = os.getenv("GUNPLA_GOOGLE_CLOUD_PROJECT")
    if not project:
        sys.exit("Missing GUNPLA_GOOGLE_CLOUD_PROJECT")
    return storage.Client(project=project)


def get_bucket(client : storage.Client):
    bucket_name = os.getenv("GUNPLA_GCS_BUCKET_NAME")
    if not bucket_name:
        sys.exit("Missing GOOGLE_CLOUD_PROJECT in .env")
    return client.bucket(bucket_name)

def upload_file(bucket, local_path: str, blob_path: str):
    if not os.path.exists(local_path):
        sys.exit(f"File not found {local_path}")
    blob = bucket.blob(blob_path)
    blob.upload_from_filename(local_path)
    print(f"Uploaded {local_path} -> gs.//{bucket.name}/{blob_path}")


def main():
    parser = argparse.ArgumentParser(description="Upload Bandai Dataset to GCS")
    parser.add_argument("--raw", help="Path to raw JSONL")
    parser.add_argument("--clean", help="Path to clean CSV")
    args = parser.parse_args()

    if not args.raw and not args.clean:
        sys.exit("Provide at least one of --raw or --clean")

    client = get_client()
    bucket = get_bucket(client)


    if args.raw:
        today = date.today().isoformat()
        upload_file(bucket, args.raw, f"raw/{today}/bandai_raw.jsonl")

    if args.clean:
        upload_file(bucket, args.clean, "processed/bandai_clean.csv")


if __name__ == "__main__":
    main()