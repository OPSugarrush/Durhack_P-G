"""Layer 1: universal ingestion. Parsing + declared field mapping only, no business logic."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from needstate.canonical import LINE_COLUMNS, REQUIRED_LINE_COLUMNS


def read_source(path: str | Path, source_cfg: dict[str, Any]) -> pd.DataFrame:
    path = Path(path)
    kind = source_cfg.get("type", path.suffix.lstrip("."))
    if kind == "xlsx":
        return pd.read_excel(path, sheet_name=source_cfg.get("sheet", 0))
    if kind == "csv":
        return pd.read_csv(path)
    raise ValueError(f"Unsupported source type: {kind}")


def _timestamp(df: pd.DataFrame, fields: dict[str, str]) -> pd.Series:
    if "timestamp" in fields:
        return pd.to_datetime(df[fields["timestamp"]])
    date = pd.to_datetime(df[fields["date"]])
    day = date.dt.strftime("%Y-%m-%d")
    if "time" in fields and fields["time"] in df.columns:
        full = pd.to_datetime(day + " " + df[fields["time"]].astype(str), errors="coerce")
        return full.fillna(date)
    return date


def to_canonical(df: pd.DataFrame, mapping: dict[str, Any]) -> pd.DataFrame:
    """Map a source frame to the canonical line table using a YAML field mapping."""
    fields: dict[str, str] = mapping["fields"]
    out = pd.DataFrame(index=df.index)
    for canon, src in fields.items():
        if canon in ("date", "time"):
            continue
        out[canon] = df[src] if src in df.columns else pd.NA
    try:
        out["timestamp"] = _timestamp(df, fields)
    except (KeyError, ValueError) as exc:
        raise ValueError("Map a valid timestamp, or date and optional time columns.") from exc
    for col in LINE_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    # Promotion: a label means promoted; a null is UNKNOWN, never "not promoted".
    out["promotion_flag"] = pd.array(
        [True if pd.notna(v) else pd.NA for v in out["promotion_label"]], dtype="boolean"
    )
    if out["line_number"].isna().all():
        out["line_number"] = out.groupby("transaction_id").cumcount() + 1
    out["line_id"] = out["transaction_id"].astype(str) + "-" + out["line_number"].astype(str)
    missing = [c for c in REQUIRED_LINE_COLUMNS if out[c].isna().all()]
    if missing:
        raise ValueError(f"Mapping leaves required canonical fields empty: {missing}")
    out["raw_product_text"] = out["raw_product_text"].astype("string").str.strip().replace("", pd.NA)
    for col in ["quantity", "unit_price", "line_total", "receipt_total"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    invalid = out["transaction_id"].isna() | out["timestamp"].isna()
    if invalid.any():
        raise ValueError(f"{int(invalid.sum())} lines have missing receipt IDs or invalid timestamps. Correct the mapping or source before analysis.")
    for col in ["customer_id", "retailer_id", "timestamp"]:
        conflicts = out.groupby("transaction_id")[col].nunique() > 1
        if conflicts.any():
            raise ValueError(f"{int(conflicts.sum())} receipt IDs have conflicting {col} values; use globally unique receipt IDs.")
    return out[LINE_COLUMNS].reset_index(drop=True)


def load_lines(path: str | Path, mapping: dict[str, Any]) -> pd.DataFrame:
    return to_canonical(read_source(path, mapping.get("source", {})), mapping)
