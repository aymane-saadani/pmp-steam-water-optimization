"""
Load : écriture des données transformées dans SQLite (traçabilité/audit)
et export JSON statique consommé par le dashboard HTML/JS.
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd


def load_to_sqlite(df: pd.DataFrame, db_path: Path, table: str = "bilan_mensuel") -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        df.to_sql(table, conn, if_exists="replace", index=False)
    print(f"[load] {len(df)} lignes écrites dans {db_path} (table '{table}')")


def serialize_historique(df: pd.DataFrame) -> list[dict]:
    out = df.copy()
    if "mois" in out.columns:
        out["mois"] = pd.to_datetime(out["mois"]).dt.strftime("%Y-%m-%d")
    return json.loads(out.to_json(orient="records", date_format="iso"))


def export_payload(payload: dict, json_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)

    js_path = json_path.with_suffix(".js")
    with open(js_path, "w", encoding="utf-8") as f:
        f.write("window.PIPELINE_DATA = ")
        json.dump(payload, f, ensure_ascii=False, default=str)
        f.write(";\n")

    print(f"[load] JSON exporté vers {json_path}")
    print(f"[load] JS embarqué vers {js_path} (dashboard utilisable en file://)")


def export_json(df: pd.DataFrame, regression: dict, optimal: dict | None, json_path: Path) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "historique": serialize_historique(df),
        "regression": regression,
        "optimal": optimal,
    }
    export_payload(payload, json_path)
