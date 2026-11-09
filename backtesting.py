"""
Backtesting  — comparaison de la marge réellement réalisée
avec la marge optimale calculée par le modèle, mois par mois.

"""

import json
from pathlib import Path

import pandas as pd

import config
import transform as T

SEUIL_VALIDITE = config.SEUIL_REGIME_NOMINAL

# Hypothèse de prix utilisée pour le backtesting (DH/MWh)
PRIX_ELEC = T.P_ELEC_CENTRALE

BACKTEST_JSON = Path("output/backtesting.json")
BACKTEST_CSV = Path("output/backtesting.csv")


def marge_modele(prodsap: float) -> float:
    """Marge du modèle pour une charge SAP donnée (équations officielles)."""
    return T.evaluate_point(prodsap, PRIX_ELEC)["marge_DH_mois"]


def marge_reelle(row) -> float:
    
    mwh = row["elec_export_hcr"] + row["elec_export_hpl"] + row["elec_export_hptes"]
    return PRIX_ELEC * mwh - T.C_EAU * row["eau_alim_total"]


def run_backtest(df: pd.DataFrame, seuil: float = SEUIL_VALIDITE) -> tuple[pd.DataFrame, dict]:
    df = df.copy()
    df["mois_str"] = pd.to_datetime(df["mois"]).dt.strftime("%Y-%m")

    df["mwh_export_reel"] = (
        df["elec_export_hcr"] + df["elec_export_hpl"] + df["elec_export_hptes"]
    )
    df["marge_reelle"] = df.apply(marge_reelle, axis=1)
    df["marge_optimale"] = df["prod_sap"].apply(marge_modele)
    df["ecart"] = df["marge_optimale"] - df["marge_reelle"]
    df["taux_realisation_pct"] = df["marge_reelle"] / df["marge_optimale"] * 100

    df["dans_domaine"] = df["prod_sap"] >= seuil

    hors = df.loc[~df["dans_domaine"], "mois_str"].tolist()
    if hors:
        print(f"[backtest] {len(hors)} mois hors domaine de validité (ProdSAP < {seuil:,.0f}) : {hors}")
        print("           -> exclus du calcul (régression hors calibration, taux > 100 % non interprétable)")

    val = df[df["dans_domaine"]]

    synthese = {
        "prix_elec_DH_par_MWh": PRIX_ELEC,
        "seuil_validite_t_mois": seuil,
        "n_mois_total": int(len(df)),
        "n_mois_retenus": int(len(val)),
        "mois_exclus": hors,
        "taux_realisation_moyen_pct": round(float(val["taux_realisation_pct"].mean()), 1),
        "taux_realisation_min_pct": round(float(val["taux_realisation_pct"].min()), 1),
        "taux_realisation_max_pct": round(float(val["taux_realisation_pct"].max()), 1),
        "ecart_type_pts": round(float(val["taux_realisation_pct"].std()), 2),
        "manque_a_gagner_DH_mois": round(float(val["ecart"].mean()), 0),
        "manque_a_gagner_DH_an": round(float(val["ecart"].mean() * 12), 0),
    }

    return df, synthese


def export_backtest(df: pd.DataFrame, synthese: dict) -> dict:
    cols = [
        "mois_str", "prod_sap", "mwh_export_reel",
        "marge_reelle", "marge_optimale", "ecart",
        "taux_realisation_pct", "dans_domaine",
    ]
    df_export = df[cols].copy()
    df_export["mwh_export_reel"] = df_export["mwh_export_reel"].round(1)
    df_export["marge_reelle"] = df_export["marge_reelle"].round(0).astype(int)
    df_export["marge_optimale"] = df_export["marge_optimale"].round(0).astype(int)
    df_export["ecart"] = df_export["ecart"].round(0).astype(int)
    df_export["taux_realisation_pct"] = df_export["taux_realisation_pct"].round(1)

    BACKTEST_CSV.parent.mkdir(parents=True, exist_ok=True)
    df_export.to_csv(BACKTEST_CSV, index=False)

    payload = {"synthese": synthese, "detail": df[cols].to_dict(orient="records")}
    with open(BACKTEST_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)

    print()
    print(f"[backtest] Taux de réalisation moyen : {synthese['taux_realisation_moyen_pct']} % "
          f"sur {synthese['n_mois_retenus']} mois")
    print(f"[backtest] Dispersion : min {synthese['taux_realisation_min_pct']} % / "
          f"max {synthese['taux_realisation_max_pct']} % / écart-type {synthese['ecart_type_pts']} pts")
    print(f"[backtest] Manque à gagner : {synthese['manque_a_gagner_DH_mois']/1e6:.2f} MDH/mois "
          f"-> {synthese['manque_a_gagner_DH_an']/1e6:.2f} MDH/an")
    print(f"[backtest] Exports : {BACKTEST_CSV} et {BACKTEST_JSON}")
    return payload


def main():
    with open(config.JSON_OUTPUT_PATH, encoding="utf-8") as f:
        payload = json.load(f)

    df = pd.DataFrame(payload["historique"])
    df, synthese = run_backtest(df)
    export_backtest(df, synthese)


if __name__ == "__main__":
    main()
