from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd


DATA_ROOT = Path("data/extracted_13F_HR")
INSIGHTS_ROOT = Path("data/insights")


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def period_label_from_filename(filename: str) -> Tuple[str, Tuple[int, int]]:
    stem = Path(filename).stem
    token = stem[:6]
    try:
        year = int(token[:4])
        month = int(token[4:6])
        if month < 1 or month > 12:
            raise ValueError("month out of range")
        quarter = (month - 1) // 3 + 1
        return f"{year}-Q{quarter}", (year, quarter)
    except Exception:
        return stem, (0, 0)


def load_infotable(issuer: str, period_filename: str) -> pd.DataFrame:
    path = DATA_ROOT / issuer / period_filename
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_excel(path, sheet_name="InfoTable", engine="openpyxl")
    except Exception:
        try:
            df = pd.read_excel(path, sheet_name="Information Table", engine="openpyxl")
        except Exception:
            df = pd.DataFrame()
    return df


def compute_summary_metrics(df: pd.DataFrame) -> Dict[str, float]:
    if df is None or df.empty:
        return {
            "rows": 0,
            "unique_issuer_name": 0,
            "unique_class_title": 0,
            "sum_value_usd_quarter_end": 0.0,
            "unique_other_manager_seq": 0,
        }
    val = pd.to_numeric(df.get("value_usd_quarter_end"), errors="coerce").fillna(0)
    return {
        "rows": int(len(df)),
        "unique_issuer_name": int(df.get("issuer_name").nunique(dropna=True) if "issuer_name" in df.columns else 0),
        "unique_class_title": int(df.get("class_title").nunique(dropna=True) if "class_title" in df.columns else 0),
        "sum_value_usd_quarter_end": float(val.sum()),
        "unique_other_manager_seq": int(df.get("other_manager_seq").nunique(dropna=True) if "other_manager_seq" in df.columns else 0),
    }


def insight_path(issuer: str, period_filename: str) -> Path:
    return INSIGHTS_ROOT / issuer / f"{Path(period_filename).stem}.json"


def save_summary_insights(issuer: str, period_filename: str) -> Path:
    df = load_infotable(issuer, period_filename)
    metrics = compute_summary_metrics(df)
    label, (year, quarter) = period_label_from_filename(period_filename)
    payload = {
        "issuer": issuer,
        "period_filename": period_filename,
        "quarter_label": label,
        "year": year,
        "quarter": quarter,
        "metrics": metrics,
    }
    out_path = insight_path(issuer, period_filename)
    _ensure_dir(out_path.parent)
    out_path.write_text(json.dumps(payload, indent=2))
    return out_path


def load_summary_insights(issuer: str, period_filename: str) -> Dict:
    p = insight_path(issuer, period_filename)
    if not p.exists():
        # Auto-create if missing
        save_summary_insights(issuer, period_filename)
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def list_period_files(issuer: str, base: Path = DATA_ROOT) -> list[str]:
    d = base / issuer
    if not d.exists():
        return []
    return sorted([p.name for p in d.glob("*.xlsx")])


def issuer_quarters_path(issuer: str) -> Path:
    return INSIGHTS_ROOT / issuer / "quarters.json"


def save_issuer_quarter_insights(issuer: str) -> Path:
    files = list_period_files(issuer)
    items = []
    for f in files:
        # Ensure per-period insight is saved, then load it
        save_summary_insights(issuer, f)
        payload = load_summary_insights(issuer, f)
        # Add sort key
        _, sort_key = period_label_from_filename(f)
        payload["sort_key"] = {"year": sort_key[0], "quarter": sort_key[1]}
        items.append(payload)

    # Sort descending by (year, quarter)
    items.sort(key=lambda x: (x.get("sort_key", {}).get("year", 0), x.get("sort_key", {}).get("quarter", 0)), reverse=True)
    out = {
        "issuer": issuer,
        "periods": items,
    }
    p = issuer_quarters_path(issuer)
    _ensure_dir(p.parent)
    p.write_text(json.dumps(out, indent=2))
    return p


def load_issuer_quarter_insights(issuer: str) -> Dict:
    p = issuer_quarters_path(issuer)
    if not p.exists():
        save_issuer_quarter_insights(issuer)
    try:
        return json.loads(p.read_text())
    except Exception:
        # Attempt to rebuild if file is corrupt
        try:
            save_issuer_quarter_insights(issuer)
            return json.loads(p.read_text())
        except Exception:
            return {"issuer": issuer, "periods": []}