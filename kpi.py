"""
KPI — consommation spécifique, taux de pertes vapeur, réalisation de marge.

"""

import json
from pathlib import Path

import pandas as pd

import config

SEUIL_REGIME_NOMINAL = config.SEUIL_REGIME_NOMINAL

KPI_JSON = Path("output/kpi.json")
KPI_CSV = Path("output/kpi.csv")
BACKTEST_JSON = Path("output/backtesting.json")


def compute_kpi_physiques(df: pd.DataFrame) -> pd.DataFrame:
    """KPI 1 (consommation spécifique) et KPI 2 (taux de pertes vapeur), par mois."""
    df = df.copy()
    df["conso_specifique_kg_t"] = df["vapeur_hp"] * 1000 / df["prod_sap"]
    df["taux_pertes_pct"] = df["bypass"] / df["vapeur_hp"] * 100
    df["mois_str"] = pd.to_datetime(df["mois"]).dt.strftime("%Y-%m")
    df["regime_nominal"] = df["prod_sap"] >= SEUIL_REGIME_NOMINAL
    return df


def synthese_kpi(df: pd.DataFrame, backtest_synthese: dict | None = None) -> dict:
    nominal = df[df["regime_nominal"]]

    synthese = {
        "seuil_regime_nominal_t_mois": SEUIL_REGIME_NOMINAL,
        "kpi1_consommation_specifique": {
            "unite": "kg vapeur / t H2SO4",
            "moyenne_17_mois": round(float(df["conso_specifique_kg_t"].mean()), 1),
            "moyenne_regime_nominal": round(float(nominal["conso_specifique_kg_t"].mean()), 1),
            "ecart_type_regime_nominal": round(float(nominal["conso_specifique_kg_t"].std()), 2),
            "min_regime_nominal": round(float(nominal["conso_specifique_kg_t"].min()), 1),
            "max_regime_nominal": round(float(nominal["conso_specifique_kg_t"].max()), 1),
        },
        "kpi2_taux_pertes_vapeur": {
            "unite": "%",
            "moyenne_17_mois": round(float(df["taux_pertes_pct"].mean()), 2),
            "moyenne_regime_nominal": round(float(nominal["taux_pertes_pct"].mean()), 2),
            "ecart_type_regime_nominal": round(float(nominal["taux_pertes_pct"].std()), 2),
            "somme_bypass_17_mois_t": round(float(df["bypass"].sum()), 0),
            "somme_vapeur_hp_17_mois_t": round(float(df["vapeur_hp"].sum()), 0),
        },
        "correlation_prodsap_taux_pertes": round(float(df["prod_sap"].corr(df["taux_pertes_pct"])), 3),
    }

    # KPI 3 : repris tel quel du backtesting, pas recalculé
    bt = backtest_synthese
    if bt is None and BACKTEST_JSON.exists():
        with open(BACKTEST_JSON, encoding="utf-8") as f:
            bt = json.load(f)["synthese"]
    if bt:
        synthese["kpi3_realisation_marge"] = {
            "unite": "%",
            "taux_realisation_moyen": bt["taux_realisation_moyen_pct"],
            "ecart_type_pts": bt["ecart_type_pts"],
            "manque_a_gagner_DH_mois": bt["manque_a_gagner_DH_mois"],
            "manque_a_gagner_DH_an": bt["manque_a_gagner_DH_an"],
        }
    else:
        print(f"[kpi] {BACKTEST_JSON} introuvable — lance backtesting.py d'abord pour inclure le KPI 3.")
        synthese["kpi3_realisation_marge"] = None

    return synthese


def export_kpi(df: pd.DataFrame, synthese: dict) -> dict:
    cols = ["mois_str", "prod_sap", "vapeur_hp", "bypass",
            "conso_specifique_kg_t", "taux_pertes_pct", "regime_nominal"]
    df_export = df[cols].copy()
    df_export["conso_specifique_kg_t"] = df_export["conso_specifique_kg_t"].round(1)
    df_export["taux_pertes_pct"] = df_export["taux_pertes_pct"].round(2)

    KPI_CSV.parent.mkdir(parents=True, exist_ok=True)
    df_export.to_csv(KPI_CSV, index=False)

    payload = {"synthese": synthese, "detail": df_export.to_dict(orient="records")}
    with open(KPI_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)

    k1, k2 = synthese["kpi1_consommation_specifique"], synthese["kpi2_taux_pertes_vapeur"]
    print(f"[kpi] KPI1 (régime nominal) : {k1['moyenne_regime_nominal']} kg/t "
          f"(écart-type {k1['ecart_type_regime_nominal']})")
    print(f"[kpi] KPI2 (régime nominal) : {k2['moyenne_regime_nominal']}% "
          f"(écart-type {k2['ecart_type_regime_nominal']} pt)")
    print(f"[kpi] Vérif. bypass total : {k2['somme_bypass_17_mois_t']:.0f} t "
          f"(diagnostic Ch.4 : 38 132 t)")
    if synthese["kpi3_realisation_marge"]:
        k3 = synthese["kpi3_realisation_marge"]
        print(f"[kpi] KPI3 : {k3['taux_realisation_moyen']}% de réalisation")
    print(f"[kpi] Exports : {KPI_CSV} et {KPI_JSON}")
    return payload


def main():
    with open(config.JSON_OUTPUT_PATH, encoding="utf-8") as f:
        payload = json.load(f)

    df = pd.DataFrame(payload["historique"])
    df = compute_kpi_physiques(df)
    synthese = synthese_kpi(df)
    export_kpi(df, synthese)


if __name__ == "__main__":
    main()
