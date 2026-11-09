"""
Analyse de sensibilité  — variation de la charge SAP et écart Dirty/Clean.

"""

import json
from pathlib import Path

import numpy as np
import transform as T

SENSI_JSON = Path("output/sensibilite.json")

# ---------------------------------------------------------------------------
# §6.5.2 — Valeurs constructeur (321045.pdf), recopiées telles quelles.
# Clés : charge (% design rate) -> régime -> {stream: valeur en kg/h}
# ---------------------------------------------------------------------------
DONNEES_CONSTRUCTEUR = {
    100: {
        "clean": {"108_hp_total": 174351, "109_export_gta": 131008, "110_vers_lp": 45859},
        "dirty": {"108_hp_total": 174979, "109_export_gta": 128811, "110_vers_lp": 49440},
    },
    115: {
        "clean": {"108_hp_total": 201893, "109_export_gta": 138226, "110_vers_lp": 67364},
        "dirty": {"108_hp_total": 202562, "109_export_gta": 131686, "110_vers_lp": 74996},
    },
}


def marge(prodsap: float, facteur_export: float = 1.0) -> float:
    """Marge M pour un ProdSAP donné (équations officielles)."""
    return T.evaluate_point(prodsap, T.P_ELEC_CENTRALE, facteur_export)["marge_DH_mois"]


def sensibilite_charge_sap(p_star: float = 103_500) -> list[dict]:
    """§6.5.1 — variation de -20% à +20% autour du point optimal."""
    m_star = marge(p_star)
    resultats = []
    for delta_pct in range(-20, 21, 5):
        p = p_star * (1 + delta_pct / 100)
        m = marge(p)
        resultats.append({
            "variation_pct": delta_pct,
            "prodsap_t_mois": round(p, 0),
            "marge_MDH_mois": round(m / 1e6, 3),
            "pct_de_optimal": round(m / m_star * 100, 1),
        })
    return resultats


def sensibilite_dirty_clean(p_star: float = 103_500) -> list[dict]:
    
    resultats = []
    charge_to_prodsap = {100: p_star, 115: 3920 * 30}

    for charge_pct, streams in DONNEES_CONSTRUCTEUR.items():
        clean_export = streams["clean"]["109_export_gta"]
        dirty_export = streams["dirty"]["109_export_gta"]
        delta_export = (dirty_export - clean_export) / clean_export

        p = charge_to_prodsap[charge_pct]
        m_clean = marge(p, 1.0)
        m_dirty = marge(p, 1 + delta_export)

        resultats.append({
            "charge_design_pct": charge_pct,
            "prodsap_t_mois": round(p, 0),
            "ecart_export_pct": round(delta_export * 100, 2),
            "marge_clean_MDH_mois": round(m_clean / 1e6, 3),
            "marge_dirty_MDH_mois": round(m_dirty / 1e6, 3),
            "ecart_marge_pct": round((m_dirty / m_clean - 1) * 100, 2),
        })
    return resultats


def compute_sensibilite() -> dict:
    charge = sensibilite_charge_sap()
    dirty_clean = sensibilite_dirty_clean()
    return {
        "sensibilite_charge_sap": charge,
        "sensibilite_dirty_clean": dirty_clean,
    }


def export_sensibilite(payload: dict | None = None) -> dict:
    payload = payload or compute_sensibilite()
    SENSI_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(SENSI_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print("=== Sensibilité à la charge SAP ===")
    for r in payload["sensibilite_charge_sap"]:
        print(f"  {r['variation_pct']:+d}% -> {r['prodsap_t_mois']:.0f} t/mois, "
              f"M={r['marge_MDH_mois']:.3f} MDH/mois ({r['pct_de_optimal']}% de l'optimal)")

    print("\n=== Sensibilité Clean/Dirty ===")
    for r in payload["sensibilite_dirty_clean"]:
        print(f"  Charge {r['charge_design_pct']}% : écart export {r['ecart_export_pct']:+.2f}%, "
              f"marge Clean={r['marge_clean_MDH_mois']:.3f} vs Dirty={r['marge_dirty_MDH_mois']:.3f} MDH/mois "
              f"({r['ecart_marge_pct']:+.2f}%)")

    print(f"\n[sensibilite] Export : {SENSI_JSON}")
    return payload


def main():
    export_sensibilite()


if __name__ == "__main__":
    main()
