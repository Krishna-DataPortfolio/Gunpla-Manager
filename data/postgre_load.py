"""

Loading cleaned .CSV into PostgreSQL Database using psycopg2 and pandas


Dimension rows are inserted idempotently, (already inserted rows are not inserted again), and fact rows are upserted
on the natural key of kit_name, so re-running the script will not create duplicate rows in the database.

Uses .env variables for database connection parameters,
The .env file should never be commited, but a sample .env.example file is provided as a reference
(or you can run cp .env.example .env and fill in blank or incorrect values)

PGHOST (default: localhost)
PGPORT (default: 5432)
PGDATABASE (default: bandai_model)
PGUSER (default: postgres)
PGPASSWORD (required, no default, pls don't hardcode this)

"""
import pandas as pd
import psycopg2
import psycopg2.extras

import argparse
import ast
import os
import sys

from dotenv import load_dotenv

load_dotenv()

LIST_COLUMNS = ['categories', 'model_of', 'variant_of']

FACT_COLUMNS = [
    "kit_name", "japanese_name", "jan_isbn", "image_url",
    "release_year", "price_value", "price_currency",
    "kit_count", "run_type", "glue_needed", "need_paint", "is_exclusive",
    "grade_id", "scale_id", "franchise_id", "exclusivity_id",
]

def get_connection():
    missing = [v for v in ("PGPASSWORD",) if not os.getenv(v)]
    if missing:
        sys.exit("Missing required env variable(s): {', '.join(missing)}")
    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
        dbname = os.getenv("PGDATABASE", "bandai_model"),
        user = os.getenv("PGUSER", "postgres"),
        password = os.environ["PGPASSWORD"]
    )


def load_dataset(path : str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.rename(columns={"jan/isbn":"jan_isbn", "run":"run_type"})
    for col in LIST_COLUMNS:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: ast.literal_eval(x) if pd.notna(x) else None)
    # uses SQL NULL rather than NaN
    df = df.astype(object).where(pd.notna(df), None)
    return df



def upsert_dim(cur, table: str, id_col: str, name_col: str, values) -> dict:
    """Insert new unique values into dimension table and returns full name and id mapping for those values"""

    clean_values = sorted({v for v in values if pd.notna(v)})
    if not clean_values:
        return {}

    psycopg2.extras.execute_values(
        cur,
        f"INSERT INTO bandai_model.{table} ({name_col}) VALUES %s ON CONFLICT ({name_col}) DO NOTHING",
        [(v,) for v in clean_values]
    )

    cur.execute(f"SELECT {id_col}, {name_col} FROM bandai_model.{table} WHERE {name_col} = ANY(%s)", (clean_values,),)
    return {name: id_ for id_, name in cur.fetchall()}


def upsert_fact(cur, df: pd.DataFrame):
    set_clause = ", ".join([f"{col} = EXCLUDED.{col}" for col in FACT_COLUMNS if col != "kit_name"])
    sql = f"""
        INSERT INTO bandai_model.fact_kit ({', '.join(FACT_COLUMNS)})
        VALUES %s
        ON CONFLICT (kit_name) DO UPDATE SET {set_clause}
        """

    rows = [tuple(row[col] for col in FACT_COLUMNS) for _, row in df.iterrows()]
    psycopg2.extras.execute_values(cur, sql, rows)


def main():
    parser = argparse.ArgumentParser(description="Load cleaned gunpla dataset into postgres db")
    parser.add_argument("--input", required=True, help="Path for cleaned csv")
    args = parser.parse_args()

    df = load_dataset(args.input)
    print(f"Loaded {len(df)} rows from {args.input}")

    connection = get_connection()
    try:
        with connection.cursor() as cur:
            grade_map = upsert_dim(cur, "dim_grade", "grade_id", "grade_name", df['grade'].unique())
            scale_map = upsert_dim(cur, "dim_scale", "scale_id", "scale_name", df['scale'].unique())
            franchise_map = upsert_dim(cur, "dim_franchise", "franchise_id", "franchise_name", df['franchise'].unique())
            exclusivity_map = upsert_dim(cur, "dim_exclusivity", "exclusivity_id", "channel_type", df['exclusive_channel_type'])

            print(f"Dimensions resolved - grades: {len(grade_map)}, scales: {len(scale_map)}, franchises: {len(franchise_map)}, exclusivity channels: {len(exclusivity_map)}")

            df['grade_id'] = df['grade'].map(grade_map)
            df['scale_id'] = df['scale'].map(scale_map)
            df['franchise_id'] = df['franchise'].map(franchise_map)
            df['exclusivity_id'] = df['exclusive_channel_type'].map(exclusivity_map)

            for id_col in ("grade_id", "scale_id", "franchise_id", "exclusivity_id"):
                df[id_col] = df[id_col].astype(object).where(pd.notna(df[id_col]), None)

            upsert_fact(cur, df)

            print(f"Upserted {len(df)} rows into fact_kit")
        connection.commit()
    finally:
        with connection.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM bandai_model.fact_kit")
            print("fact_kit row count after commit:", cur.fetchone()[0])
        connection.close()

    print('load complete')


if __name__ == "__main__":
    main()
