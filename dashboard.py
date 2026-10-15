"""SyndraLens dashboard: data handling and app flow.

Run with:  streamlit run dashboard.py
All styling and visual components live in syndralens_ui.py.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import syndralens_ui as ui

ROOT = Path(__file__).resolve().parent

st.set_page_config(page_title="SyndraLens | Regional Monitor", page_icon="🔎", layout="wide")
ui.apply_theme()
ui.render_hero()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
REQUIRED_COLUMNS = ["id", "region", "report_date", "text"]
PIPELINE_SCRIPT = "scripts/analyse_complaints.py"

# Files the pipeline script writes into its output folder.
RESULT_FILES = {
    "predictions": "predictions.csv",
    "symptoms": "symptom_summary.csv",
    "syndromes": "syndrome_summary.csv",
    "alerts": "alerts.csv",
}

# Accept common header variations (case, spaces, synonyms)
HEADER_ALIASES = {
    "id": "id", "record_id": "id", "patient_id": "id", "case_id": "id",
    "text": "text", "complaint": "text", "complaint_text": "text",
    "description": "text", "symptoms_text": "text", "notes": "text",
    "region": "region", "area": "region", "location": "region",
    "locality": "region", "zone": "region",
    "report_date": "report_date", "date": "report_date",
    "reported_on": "report_date", "reportdate": "report_date",
}


# ---------------------------------------------------------------------------
# Pipeline helpers
# ---------------------------------------------------------------------------
def run_pipeline(input_csv, output_dir, progress=None):
    """Run the analysis script, stream its output and update the progress bar."""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    proc = subprocess.Popen(
        [
            sys.executable, "-u", str(ROOT / PIPELINE_SCRIPT),
            "--input", str(input_csv),
            "--output-dir", str(output_dir),
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    lines = []
    for line in proc.stdout:
        lines.append(line.rstrip())
        match = re.match(r"Processing (\d+)/(\d+)", line)
        if match and progress is not None:
            done, total = int(match.group(1)), int(match.group(2))
            progress.progress(done / total, text=f"Analysing record {done} of {total}")
    proc.wait()
    return proc.returncode, "\n".join(lines)


def load_results(output_dir):
    """Read the generated result files into memory. Returns None if any is missing."""
    results = {}
    for key, name in RESULT_FILES.items():
        path = Path(output_dir) / name
        if not path.exists():
            return None
        results[key] = pd.read_csv(path)
    return results


# ---------------------------------------------------------------------------
# Upload cleaning
# ---------------------------------------------------------------------------
def standardise_headers(df):
    renamed = {}
    for col in df.columns:
        key = str(col).strip().lower().replace(" ", "_").replace("-", "_")
        target = HEADER_ALIASES.get(key)
        if target and target not in renamed.values() and target not in df.columns:
            renamed[col] = target
        elif key in REQUIRED_COLUMNS and col != key and key not in df.columns:
            renamed[col] = key
    return df.rename(columns=renamed)


def clean_upload(df):
    """Keep the required columns and repair what can be repaired.

    Blank lines are dropped silently. Returns (clean_df, total_rows, notes)
    where `notes` describes real data fixes only (missing text, ids, dates...).
    """
    extra_columns = [c for c in df.columns if c not in REQUIRED_COLUMNS]
    df = df[REQUIRED_COLUMNS + extra_columns].copy()
    for col in REQUIRED_COLUMNS:
        df[col] = df[col].astype("string").str.strip().replace("", pd.NA)

    # Blank lines are not records: drop them without reporting.
    df = df.dropna(how="all", subset=REQUIRED_COLUMNS)
    total_rows = len(df)

    # Rows without complaint text or region cannot be analysed
    df = df.dropna(subset=["text", "region"]).reset_index(drop=True)
    unusable = total_rows - len(df)

    # Repair missing ids, dates and duplicate ids instead of dropping rows
    missing_id = int(df["id"].isna().sum())
    if missing_id:
        df["id"] = df["id"].fillna(
            pd.Series([f"upl_{i + 1:03d}" for i in range(len(df))], dtype="string")
        )
    missing_date = int(df["report_date"].isna().sum())
    if missing_date:
        df["report_date"] = df["report_date"].fillna(pd.Timestamp.today().date().isoformat())
    dup_ids = int(df["id"].duplicated(keep="first").sum())
    if dup_ids:
        seen, new_ids = {}, []
        for value in df["id"]:
            seen[value] = seen.get(value, 0) + 1
            new_ids.append(value if seen[value] == 1 else f"{value}_{seen[value]}")
        df["id"] = pd.Series(new_ids, dtype="string")

    notes = []
    if unusable:
        notes.append(f"{unusable} rows removed because text or region was missing")
    if missing_id:
        notes.append(f"{missing_id} missing ids generated")
    if missing_date:
        notes.append(f"{missing_date} missing dates set to today")
    if dup_ids:
        notes.append(f"{dup_ids} duplicate ids renamed")
    return df, total_rows, notes


def date_range_label(df):
    dates = pd.to_datetime(df["report_date"], errors="coerce").dropna()
    if dates.empty:
        return None
    lo, hi = dates.min().strftime("%d %b %Y"), dates.max().strftime("%d %b %Y")
    return lo if lo == hi else f"{lo} to {hi}"


def analyse(uploaded_df):
    """Run the pipeline on the cleaned upload and store results in session state."""
    st.session_state.pop("results", None)  # never show stale data

    work_dir = Path(tempfile.mkdtemp(prefix="syndralens_"))
    input_csv = work_dir / "complaints.csv"
    output_dir = work_dir / "results"
    uploaded_df.to_csv(input_csv, index=False)

    try:
        progress_bar = st.progress(0, text="Starting analysis...")
        with st.spinner("Analysing complaints..."):
            code, output = run_pipeline(input_csv, output_dir, progress_bar)
        progress_bar.empty()

        if code != 0:
            st.error("The analysis did not finish successfully.")
            with st.expander("Error details", expanded=True):
                st.code("\n".join(output.splitlines()[-40:]))
            return

        results = load_results(output_dir)
        if results is None:
            st.error("The analysis finished but some result files were not created.")
            return

        sent_ids = set(uploaded_df["id"].astype(str))
        result_ids = set(results["predictions"]["id"].astype(str))
        matched = len(sent_ids & result_ids)
        if matched < len(sent_ids):
            st.error(
                f"The analysis ran, but only {matched} of "
                f"{len(sent_ids)} uploaded records appear in the results."
            )
            return

        st.session_state["results"] = results
        failed_rows = int((results["predictions"]["status"] != "success").sum())
        message = f"Analysis complete for {len(uploaded_df)} records."
        if failed_rows:
            message += f" {failed_rows} records could not be analysed."
        st.session_state["upload_done"] = message
        st.rerun()
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Upload section
# ---------------------------------------------------------------------------
ui.section_header("📤", "Upload complaints", "Add a CSV of patient complaints to analyse.")

if st.session_state.get("upload_done"):
    st.success(st.session_state.pop("upload_done"), icon="✅")

uploaded_file = st.file_uploader(
    "Upload a complaint file (CSV)",
    type=["csv"],
    help="Required columns: " + ", ".join(REQUIRED_COLUMNS),
)

if uploaded_file is not None:
    try:
        raw_df = pd.read_csv(uploaded_file, dtype=str)
    except Exception as exc:
        raw_df = None
        st.error(f"The file could not be read as CSV: {exc}")

    if raw_df is not None:
        raw_df = standardise_headers(raw_df)
        missing_cols = [c for c in REQUIRED_COLUMNS if c not in raw_df.columns]
        if missing_cols:
            st.error("Missing required columns: " + ", ".join(missing_cols))
        else:
            uploaded_df, total_rows, notes = clean_upload(raw_df)

            if uploaded_df.empty:
                st.error("The file has no complete records to analyse.")
                st.stop()

            if notes:
                summary = f"Kept {len(uploaded_df)} of {total_rows} rows. " + "; ".join(notes) + "."
                if len(uploaded_df) < total_rows / 2:
                    st.warning(summary, icon="⚠️")
                else:
                    with st.expander(f"Data check: {len(uploaded_df)} of {total_rows} rows ready"):
                        st.write(summary)

            chip_items = [
                ("📋", "Records", len(uploaded_df)),
                ("📍", "Regions", uploaded_df["region"].nunique()),
            ]
            period = date_range_label(uploaded_df)
            if period:
                chip_items.append(("🗓️", "Period", period))
            ui.chips(chip_items)

            st.dataframe(uploaded_df.head(10), width="stretch", hide_index=True)

            if st.button("🔬 Analyse complaints", type="primary"):
                analyse(uploaded_df)

# ---------------------------------------------------------------------------
# Dashboard: only shown for results produced from the user's own upload
# ---------------------------------------------------------------------------
results = st.session_state.get("results")
if results is None:
    if uploaded_file is None:
        ui.empty_state()
    else:
        st.info("Click **Analyse complaints** to build the dashboard.", icon="👆")
    ui.footer()
    st.stop()

# Normalise region spelling everywhere so filters, map and alerts agree
predictions, symptoms, syndromes, alerts = (
    results[k].copy() for k in ("predictions", "symptoms", "syndromes", "alerts")
)
for frame in (predictions, symptoms, syndromes, alerts):
    if "region" in frame.columns:
        frame["region"] = frame["region"].apply(ui.normalize_region)

# Sidebar
ui.sidebar_brand()
ui.sidebar_label("Regions")
regions = sorted(predictions["region"].dropna().unique().tolist())
selected_regions = st.sidebar.multiselect(
    "Select regions", regions, default=regions, label_visibility="collapsed"
)
st.sidebar.caption(f"{len(selected_regions)} of {len(regions)} regions selected")
if st.sidebar.button("🗑️ Clear results", width="stretch"):
    st.session_state.pop("results", None)
    st.rerun()

if not selected_regions:
    st.warning("Select at least one region in the sidebar to see results.", icon="👈")
    st.stop()

f_pred = predictions[predictions["region"].isin(selected_regions)]
f_symp = symptoms[symptoms["region"].isin(selected_regions)]
f_synd = syndromes[syndromes["region"].isin(selected_regions)]
f_alert = alerts[alerts["region"].isin(selected_regions)]

# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------
ui.section_header("📊", "Overview", "Key figures for the selected regions.")
ui.kpi_cards(
    [
        ("📋", "Complaint records", len(f_pred), "teal"),
        ("🌍", "Regions selected", f_pred["region"].nunique(), "blue"),
        ("🩺", "Symptom groups", len(f_symp), "amber"),
        ("🚨", "Active alerts", len(f_alert), "coral"),
    ]
)

# ---------------------------------------------------------------------------
# Regional map
# ---------------------------------------------------------------------------
ui.section_header("🗺️", "Regional map", "Circle size shows complaint volume. Red circles have alerts.")

map_counts = f_pred.dropna(subset=["region", "id"]).groupby("region")["id"].nunique().to_dict()
alert_counts = f_alert.dropna(subset=["region"]).groupby("region").size().to_dict()

map_points = [
    {
        "region": name,
        "lat": ui.REGION_COORDS[name][0],
        "lon": ui.REGION_COORDS[name][1],
        "complaints": int(count),
        "alerts": int(alert_counts.get(name, 0)),
    }
    for name, count in map_counts.items()
    if name in ui.REGION_COORDS
]
unmapped = [name for name in map_counts if name not in ui.REGION_COORDS]

if not map_points:
    st.info("No mappable regions for the current selection.")
else:
    components.html(ui.build_map_html(map_points, ui.get_map_key()), height=480)

if unmapped:
    st.caption("Not shown on the map (no coordinates configured): " + ", ".join(sorted(unmapped)))

# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
ui.section_header("📈", "Trends", "Where complaints cluster and what people report most.")
left, right = st.columns(2)

with left:
    with st.container(border=True):
        ui.panel_title("Complaints by region", "Unique records per region")
        counts = f_pred.groupby("region")["id"].nunique().sort_values(ascending=False)
        st.bar_chart(counts, color=ui.TEAL, horizontal=True, height=340)

with right:
    with st.container(border=True):
        ui.panel_title("Most frequent symptoms", "Top 10 across selected regions")
        if f_symp.empty:
            st.info("No symptom data available.")
        else:
            top_symptoms = (
                f_symp.groupby("symptom")["record_count"].sum().sort_values(ascending=False).head(10)
            )
            st.bar_chart(top_symptoms, color=ui.AMBER, horizontal=True, height=340)

# ---------------------------------------------------------------------------
# Detail tables
# ---------------------------------------------------------------------------
ui.section_header("🧾", "Signals and alerts", "Detailed results for the selected regions.")
tab_symptoms, tab_syndromes, tab_alerts = st.tabs(
    ["🤒 Symptoms by region", "🧬 Syndrome signals", f"🚨 Alerts ({len(f_alert)})"]
)

with tab_symptoms:
    if f_symp.empty:
        st.info("No symptom records for the selected regions.")
    else:
        table = f_symp.sort_values(["record_count", "region"], ascending=[False, True])
        st.dataframe(
            table,
            width="stretch",
            hide_index=True,
            column_config={
                "record_count": st.column_config.ProgressColumn(
                    "Records",
                    format="%d",
                    min_value=0,
                    max_value=int(table["record_count"].max()),
                )
            },
        )

with tab_syndromes:
    if f_synd.empty:
        st.info("No syndrome signals available.")
    else:
        st.dataframe(f_synd, width="stretch", hide_index=True)

with tab_alerts:
    if f_alert.empty:
        st.success("No regions meet the current alert threshold.", icon="✅")
    else:
        st.dataframe(f_alert, width="stretch", hide_index=True)
        st.caption("Alerts are raised when a region crosses the configured threshold.")

# ---------------------------------------------------------------------------
# Complaint explorer
# ---------------------------------------------------------------------------
ui.section_header("🔍", "Complaint explorer", "Inspect what the model found in a single complaint.")
if f_pred.empty:
    st.info("No records match your filters.")
else:
    chosen_id = st.selectbox("Choose a record", f_pred["id"].astype(str).tolist())
    record = f_pred[f_pred["id"].astype(str) == chosen_id].iloc[0]
    ui.record_card(record)
    ui.render_record_fields(record)

ui.footer()