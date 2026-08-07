"""

Gunpla Pipeline DAG

Orchestate the entire pipeline flow as a single Airflow DAG

Steps:
- Extract data from MediaWikiAPI
- Clean Data via script
- (Run below steps in parallel as they're not dependent on each other)
---- Load to PostgreSQL
---- Load to GCS
---- load_bigquery
---- generate new dashboard data

This calls existing pipeline scripts rather than reimplementing logic

"""

from datetime import datetime, timedelta
import subprocess
import os

from airflow.decorators import dag, task

DIR = "/usr/local/airflow"
RAW_JSONL = f"{DIR}/data/fetched/bandai_dataset_{datetime.now().strftime("%Y-%m-%d")}.jsonl"
CLEAN_CSV = f"{DIR}/data/processed/Cleaned_Gunpla_Dataset.csv"

default_args = {
    "owner": "Krishna",
    "retries": 2,
    "retry_delay": timedelta(minutes=5)
}

def get_latest_jsonl_file(path):
    files = os.listdir(path)
    jsonl_files = [f for f in files if f.startswith("bandai_dataset_") and f.endswith(".jsonl")]

    if not jsonl_files:
        raise FileNotFoundError("No matching JSONL files found")
    def extract_date(file):
        date_str = file.replace("bandai_dataset_", "").replace(".jsonl", "")
        return datetime.strptime(date_str, "%Y-%m-%d")
    latest_file = max(jsonl_files, key=extract_date)

    return os.path.join(path, latest_file)

def run(cmd: list[str]):
    """
    - Run the pipeline script as a subprocess, so we don't have to import and execute every function individually.
    - Raise on any non-zero exit so Airflow can correctly mark the task and retries as failed rather than continuing
    """
    result = subprocess.run(cmd, cwd=DIR, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError(f"Command failed due to ({result.returncode}): {' '.join(cmd)}")

@dag(
        dag_id="gunpla_pipeline",
        description="Extract, clean and load bandai_model datasets into postgres and Google Cloud",
        default_args=default_args,
        schedule="@weekly", # Daily is too much, the Wiki won't be updated that often
        start_date=datetime(2026, 8, 6),
        catchup=False,
        tags=["gunpla", "data_portfolio"]
)

def gunpla_pipeline():
    @task
    def extract():
        run(["python", "main.py", "full", "--mode", "full"])

    @task
    def clean():
        run(["python", "transform/clean_analysis.py", "--input", RAW_JSONL, "--output", CLEAN_CSV])

    @task
    def load_postgres():
        run(["python", "data/postgre_load.py", "--input", CLEAN_CSV])

    @task
    def upload_gcs():
        run(["python", "data/gcs_load.py", "--raw", RAW_JSONL, "--clean", CLEAN_CSV])


    @task
    def load_bigQuery():
        run([
            "bq", "load",
            "--source_format=CSV",
            "--skip_leading_rows=1",
            "--autodetect",
            "--allow_quoted_newlines",
            "--replace",
            "gunpla_analytics.kits",
            "gs://gunpla-dataset/processed/gunpla_clean.csv",
        ])

    @task
    def generate_dashboard_data():
        run(["python", "transform/generate_dashboard_data.py", "--input", CLEAN_CSV])


    extracted = extract()
    cleaned = clean()
    extracted >> cleaned

    cleaned >> load_postgres()
    cleaned >> upload_gcs()
    cleaned >> generate_dashboard_data()


gunpla_pipeline()