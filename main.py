"""
Pipeline de pilotage PMP — une seule commande.

"""

from __future__ import annotations

import argparse
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import config
import transform as T
from backtesting import export_backtest, run_backtest
from extract import extract, filter_scope
from kpi import compute_kpi_physiques, export_kpi, synthese_kpi
from load import export_payload, load_to_sqlite, serialize_historique
from sensibilite import export_sensibilite


DASHBOARD = Path("dashboard_pilotage_pmp.html")
SERVE_PORT = 8765


def run_pipeline() -> dict:
    df_raw = extract(config.EXCEL_PATH, config.SHEET_NAME, config.COLUMNS)
    df_raw = filter_scope(df_raw, config.EXCLUDE_MONTHS)

    df_clean, regression, optimal = T.transform(df_raw, run_optimization=True)
    load_to_sqlite(df_clean, config.DB_PATH)

    df_bt, synthese_bt = run_backtest(df_clean)
    backtesting_payload = export_backtest(df_bt, synthese_bt)

    df_kpi = compute_kpi_physiques(df_clean)
    kpi_payload = export_kpi(df_kpi, synthese_kpi(df_kpi, synthese_bt))

    sensi_payload = export_sensibilite()

    from datetime import datetime, timezone

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "historique": serialize_historique(df_clean),
        "regression": regression,
        "optimal": optimal,
        "backtesting": backtesting_payload,
        "kpi": kpi_payload,
        "sensibilite": sensi_payload,
        "constantes": T.constants_payload(),
        "seuil_regime_nominal": config.SEUIL_REGIME_NOMINAL,
    }
    export_payload(payload, config.JSON_OUTPUT_PATH)
    print("[main] Pipeline terminé.")
    return payload


def serve_dashboard(port: int = SERVE_PORT) -> None:
    root = Path(__file__).resolve().parent

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(root), **kwargs)

        def log_message(self, format, *args):
            print(f"[serve] {self.address_string()} {args[0]}")

    url = f"http://127.0.0.1:{port}/{DASHBOARD.name}"
    print(f"[serve] Dashboard : {url}")
    print("[serve] Ctrl+C pour arrêter.")
    webbrowser.open(url)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline de pilotage PMP")
    parser.add_argument("--serve", action="store_true", help="lancer le dashboard après le calcul")
    parser.add_argument("--serve-only", action="store_true", help="servir le dashboard sans recalculer")
    parser.add_argument("--port", type=int, default=SERVE_PORT)
    args = parser.parse_args()

    if not args.serve_only:
        run_pipeline()
    elif not config.JSON_OUTPUT_PATH.exists():
        raise SystemExit(
            f"{config.JSON_OUTPUT_PATH} introuvable — lance d'abord : python main.py"
        )

    if args.serve or args.serve_only:
        serve_dashboard(args.port)


if __name__ == "__main__":
    main()
