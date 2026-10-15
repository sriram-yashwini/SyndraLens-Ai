
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from training._boot import load_config
from syndralens.inference import load_backend

REQUIRED_COLUMNS = {"id", "text", "region", "report_date"}


# Count threshold only; tune using historical baseline data.
MIN_COUNT_FOR_ALERT = 3


def parse_json_list(value):
    """Safely parse a JSON list stored in a CSV cell."""
    if pd.isna(value):
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def run_inference(df):
    """Run the SLM on every complaint and return a predictions DataFrame."""
    print(f"Input records: {len(df)}")
    print("Loading trained SyndraLens SLM...")
    backend = load_backend("slm", load_config())

    results = []
    for position, (_, row) in enumerate(df.iterrows(), start=1):
        print(f"Processing {position}/{len(df)}: {row['id']}")
        base = {
            "id": row["id"],
            "text": row["text"],
            "region": row["region"],
            "report_date": row["report_date"],
        }
        try:
            prediction = backend.extract(str(row["text"]))
            results.append({
                **base,
                "symptoms": json.dumps(
                    prediction.get("symptoms", []), ensure_ascii=False
                ),
                "exposures": json.dumps(
                    prediction.get("exposures", []), ensure_ascii=False
                ),
                "syndromes": json.dumps(
                    prediction.get("syndromes", []), ensure_ascii=False
                ),
                "backend": prediction.get("backend", "unknown"),
                "valid_json": prediction.get("valid_json"),
                "fallback_used": prediction.get("fallback_used"),
                "model_engine_consistent": prediction.get(
                    "model_engine_consistent"
                ),
                "guardrail_violations": json.dumps(
                    prediction.get("guardrail_violations", []),
                    ensure_ascii=False,
                ),
                "status": "success",
                "error": "",
            })
        except Exception as exc:  # keep going; report the failure per row
            results.append({
                **base,
                "symptoms": "[]",
                "exposures": "[]",
                "syndromes": "[]",
                "backend": "slm",
                "valid_json": None,
                "fallback_used": None,
                "model_engine_consistent": None,
                "guardrail_violations": "[]",
                "status": "error",
                "error": str(exc),
            })
            print(f"  Error for {row['id']}: {exc}")

    return pd.DataFrame(results)


def build_regional_reports(predictions):
    """Build symptom summary, syndrome summary and alerts from predictions."""
    df = predictions[predictions["status"].eq("success")].copy()
    df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce").dt.date

    symptom_rows = []
    syndrome_rows = []

    for _, row in df.iterrows():
        for symptom in parse_json_list(row["symptoms"]):
            if symptom.get("assertion") != "present":
                continue
            name = symptom.get("name")
            if not name:
                continue
            symptom_rows.append({
                "id": row["id"],
                "region": row["region"],
                "report_date": row["report_date"],
                "symptom": name,
            })

        for syndrome in parse_json_list(row["syndromes"]):
            name = syndrome.get("syndrome")
            if not name:
                continue
            syndrome_rows.append({
                "id": row["id"],
                "region": row["region"],
                "report_date": row["report_date"],
                "syndrome": name,
                "signal": syndrome.get("signal", "unknown"),
            })

    symptom_df = pd.DataFrame(
        symptom_rows, columns=["id", "region", "report_date", "symptom"]
    )
    syndrome_df = pd.DataFrame(
        syndrome_rows,
        columns=["id", "region", "report_date", "syndrome", "signal"],
    )

    if symptom_df.empty:
        symptom_summary = pd.DataFrame(
            columns=["region", "report_date", "symptom", "record_count"]
        )
    else:
        symptom_summary = (
            symptom_df.groupby(["region", "report_date", "symptom"])["id"]
            .nunique()
            .reset_index(name="record_count")
            .sort_values(
                ["region", "record_count", "symptom"],
                ascending=[True, False, True],
            )
        )

    if syndrome_df.empty:
        syndrome_summary = pd.DataFrame(
            columns=["region", "report_date", "syndrome", "record_count"]
        )
    else:
        syndrome_summary = (
            syndrome_df.groupby(["region", "report_date", "syndrome"])["id"]
            .nunique()
            .reset_index(name="record_count")
            .sort_values(["region", "record_count"], ascending=[True, False])
        )

    symptom_summary["alert"] = symptom_summary["record_count"] >= MIN_COUNT_FOR_ALERT
    alerts = symptom_summary[symptom_summary["alert"]]

    return symptom_summary, syndrome_summary, alerts, len(df), len(symptom_df), len(syndrome_df)


def main():
    parser = argparse.ArgumentParser(description="SyndraLens complaint analysis")
    parser.add_argument("--input", required=True, help="Complaint CSV to analyse")
    parser.add_argument("--output-dir", required=True, help="Folder for results")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    df = pd.read_csv(input_path)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if len(df) == 0:
        raise ValueError("The input CSV contains no records.")
    if df["text"].isna().any() or df["text"].astype(str).str.strip().eq("").any():
        raise ValueError("Some records have empty complaint text.")

    predictions = run_inference(df)

    output_dir.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(output_dir / "predictions.csv", index=False)

    (
        symptom_summary,
        syndrome_summary,
        alerts,
        n_success,
        n_symptoms,
        n_syndromes,
    ) = build_regional_reports(predictions)

    symptom_summary.to_csv(output_dir / "symptom_summary.csv", index=False)
    syndrome_summary.to_csv(output_dir / "syndrome_summary.csv", index=False)
    alerts.to_csv(output_dir / "alerts.csv", index=False)

    print("\nAnalysis complete.")
    print(f"Total records: {len(predictions)}")
    print(f"Successful: {n_success}")
    print(f"Failed: {len(predictions) - n_success}")
    print(f"Symptom mentions counted: {n_symptoms}")
    print(f"Syndrome signals counted: {n_syndromes}")
    print(f"Alerts raised: {len(alerts)}")
    print("\nRecords by region:")
    print(predictions.groupby("region").size().to_string())
    print(
        "\nNOTICE: The alert threshold is illustrative, not a validated "
        "outbreak threshold."
    )


if __name__ == "__main__":
    main()