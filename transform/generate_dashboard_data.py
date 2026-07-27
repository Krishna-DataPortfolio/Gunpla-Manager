import argparse
import ast
import pandas as pd
import json


LIST_COLUMNS = ["categories", "model_of", "variant_of"]


def load_clean_dataset(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    for col in LIST_COLUMNS:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: ast.literal_eval(x) if pd.notna(x) else None)
    return df




def build_stats(df: pd.DataFrame) -> dict:
    stats = {}
    stats["total_kits"] = int(len(df))

    valid_years = df.loc[df["release_year"] <= 2026, "release_year"].dropna()
    stats["date_range"] = [int(valid_years.min()), int(valid_years.max())]

    stats["grade_counts"] = (
        df["grade"].fillna("Ungraded").value_counts().to_dict()
    )

    jpy = df.loc[df["price_currency"] == "JPY", "price_value"]
    stats["price_median_jpy"] = float(jpy.median())
    stats["price_max_jpy"] = float(jpy.max())
    stats["most_expensive_kit"] = df.loc[jpy.idxmax(), "kit_name"]

    stats["exclusive_pct"] = float(df["is_exclusive"].mean())
    stats["exclusive_channel_counts"] = (
        df["exclusive_channel_type"].value_counts().to_dict()
    )

    by_year = df.dropna(subset=["release_year"])
    by_year = by_year[by_year["release_year"] <= 2026]
    by_year = by_year.groupby("release_year").size()
    stats["kits_by_year"] = {str(int(k)): int(v) for k, v in by_year.items()}

    stats["top_franchises"] = df["franchise"].value_counts().head(8).to_dict()

    exploded = df.explode("model_of")
    stats["most_reused_mobile_suits"] = (
        exploded["model_of"].value_counts().head(8).to_dict()
    )

    stats["generated_note"] = ("Generated from cleaned dataset retrieved via generate_dashboard_data.py")

    return stats



def main():
    parser = argparse.ArgumentParser(description="Regenerate dashboard data.json")
    parser.add_argument("--input", required=True, help="Path to cleaned dataset CSV")
    parser.add_argument(
        "--output",
        default="docs/assets/data.json",
        help="Path to write the dashboard JSON (default: docs/assets/data.json)"
    )
    args = parser.parse_args()

    df = load_clean_dataset(args.input)
    stats = build_stats(df)

    with open(args.output, "w") as f:
        json.dump(stats, f, indent=2, default=str)

    print(f"Wrote {args.output} from {len(df)} rows")



if __name__ == "__main__":
    main()