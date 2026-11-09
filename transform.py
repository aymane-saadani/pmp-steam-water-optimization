"""
Transform : nettoyage des données, régression de vérification E_réel(ProdSAP),
et recherche du point optimal.
"""

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constantes officielles du modèle — copiées telles quelles depuis
# comparateur_energetique_PMP.py (rapport Ch.2, 4.3, 5.4.3, 6.3, 6.6.3).
# Ne pas modifier sans mettre à jour la source correspondante.
# ---------------------------------------------------------------------------
CAP_GTA = 138.2             # t/h — plafond turbine (design)
HEURES_MOIS = 730.5         # h — moyenne (8766 h/an / 12)
RATIO_TURBINE = 5.02        # t vapeur / MWh (ratio réel, Ch.4.3.2)
TAU_PURGE_TOTAL = 0.0414    # Blowdown+Flash+Eau résiduelle / HP_total, Ch.4.3.1
CAP_CHAUDIERE_UNIT = 87.8   # t/h — capacité d'une seule chaudière, Ch.2

COEF_A = -0.00000105        # régression E_brut(ProdSAP), Ch.5.4.3 / 6.6.3 — steam (t/mois), pas MWh
COEF_B = 1.16998
COEF_C = -8888.17

C_EAU = 19.61                # DH/t — eau déminéralisée TED
C_MAINT_UNIT = 0.0           # DH/mois/chaudière 
P_ELEC_BASSE = 241.73        # DH/MWh — heures creuses
P_ELEC_CENTRALE = 386.55     # DH/MWh — moyenne pondérée grille ONE
P_ELEC_HAUTE = 578.16        # DH/MWh — heures pointe

PROD_MIN, PROD_MAX, PAS = 40_000, 135_000, 500   # grille identique à l'Excel

SCENARIOS_PRIX = {
    "basse": P_ELEC_BASSE,
    "centrale": P_ELEC_CENTRALE,
    "haute": P_ELEC_HAUTE,
}


def constants_payload() -> dict:
    """Constantes officielles exposées au dashboard (une seule source de vérité)."""
    return {
        "CAP_GTA": CAP_GTA,
        "HEURES_MOIS": HEURES_MOIS,
        "RATIO_TURBINE": RATIO_TURBINE,
        "TAU_PURGE_TOTAL": TAU_PURGE_TOTAL,
        "CAP_CHAUDIERE_UNIT": CAP_CHAUDIERE_UNIT,
        "COEF_A": COEF_A,
        "COEF_B": COEF_B,
        "COEF_C": COEF_C,
        "C_EAU": C_EAU,
        "C_MAINT_UNIT": C_MAINT_UNIT,
        "P_ELEC_BASSE": P_ELEC_BASSE,
        "P_ELEC_CENTRALE": P_ELEC_CENTRALE,
        "P_ELEC_HAUTE": P_ELEC_HAUTE,
        "PROD_MIN": PROD_MIN,
        "PROD_MAX": PROD_MAX,
        "PAS": PAS,
    }


def evaluate_point(
    prodsap: float,
    prix: float = P_ELEC_CENTRALE,
    facteur_export: float = 1.0,
) -> dict:
    """
    Point unique du modèle officiel (mêmes équations que la grille Excel).
    Utilisé par le backtesting, la sensibilité et le dashboard.
    """
    p = float(prodsap)
    cap_gta_mois = CAP_GTA * HEURES_MOIS
    e_brut = COEF_A * p**2 + COEF_B * p + COEF_C
    e_export = min(e_brut, cap_gta_mois) * facteur_export
    bypass = p - e_export
    mwh_export = e_export / RATIO_TURBINE
    cout_eau = C_EAU * p * (1 + TAU_PURGE_TOTAL)
    nb_chaudieres = 1 if p / HEURES_MOIS <= CAP_CHAUDIERE_UNIT else 2
    marge = prix * mwh_export - cout_eau - nb_chaudieres * C_MAINT_UNIT
    return {
        "prod_sap": p,
        "e_brut_t_mois": e_brut,
        "export_GTA_t_mois": e_export,
        "bypass_t_mois": bypass,
        "mwh_export": mwh_export,
        "nb_chaudieres": nb_chaudieres,
        "marge_DH_mois": marge,
    }


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Supprime les lignes vides, force les types numériques, recalcule vapeur_hp."""
    df = df.dropna(how="all").copy()

    numeric_cols = [c for c in [
        "prod_sap", "vap_hp_gta", "bypass", "vap_bp_extract_gta",
        "vap_bp_detente_hp_bp", "vap_bp_conso_pap", "e_reel", "conso_usine",
        "elec_export_hcr", "elec_export_hpl", "elec_export_hptes",
        "eau_alim_total", "heures_gta",
    ] if c in df.columns]
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    n_before = len(df)
    df = df.dropna(subset=numeric_cols)
    if len(df) < n_before:
        print(f"[transform] {n_before - len(df)} ligne(s) écartée(s) (valeurs non numériques)")

    # vapeur HP totale = vapeur envoyée à la turbine + vapeur bypassée (PV-050A)
    if {"vap_hp_gta", "bypass"}.issubset(df.columns):
        df["vapeur_hp"] = df["vap_hp_gta"] + df["bypass"]

    return df.reset_index(drop=True)


def fit_regression(df: pd.DataFrame, x_col="prod_sap", y_col="e_reel", degree=2) -> dict:
    """
    Vérification indépendante : ajuste électricité réelle (e_reel, MWh) = f(ProdSAP)
    directement sur tes données historiques. C'est un fit de contrôle distinct de la
    régression officielle E_brut(ProdSAP) (COEF_A/B/C ci-dessus, qui modélise la vapeur
    en tonnes, pas l'électricité en MWh) — sert à repérer une éventuelle incohérence,
    pas à remplacer le modèle validé du rapport.
    """
    x = df[x_col].values
    y = df[y_col].values

    coeffs = np.polyfit(x, y, degree)
    y_pred = np.polyval(coeffs, x)

    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    result = {
        "degree": degree,
        "coefficients": coeffs.tolist(),  # ordre décroissant, ex: [a, b] pour a*x + b
        "r2": round(float(r2), 4),
        "n_points": len(df),
    }
    print(f"[transform] Régression de vérification degré {degree} — R² = {result['r2']} sur {result['n_points']} points")
    return result


def run_milp(df: pd.DataFrame = None) -> dict:
    """
    Reproduit la recherche par grille de comparateur_energetique_PMP.py
    (balayage ProdSAP de 40 000 à 135 000 t/mois, argmax de la marge —
    identique à la logique INDEX/MATCH/MAX de l'onglet Excel "Scenario optimal",
    pas un solveur PuLP). Pilotée par les constantes officielles ci-dessus,
    déjà validées dans le rapport — df n'est pas utilisé pour ce calcul.
    """
    grid = np.arange(PROD_MIN, PROD_MAX + PAS, PAS, dtype=float)

    e_brut = COEF_A * grid**2 + COEF_B * grid + COEF_C
    cap_gta_mois = CAP_GTA * HEURES_MOIS
    e_export = np.minimum(e_brut, cap_gta_mois)
    bypass = grid - e_export
    mwh_export = e_export / RATIO_TURBINE
    eau_alim = grid * (1 + TAU_PURGE_TOTAL)
    cout_eau = C_EAU * eau_alim
    nb_chaudieres = np.where(grid / HEURES_MOIS <= CAP_CHAUDIERE_UNIT, 1, 2)
    cout_maint = nb_chaudieres * C_MAINT_UNIT

    resultats = {}
    for label, prix in SCENARIOS_PRIX.items():
        revenu = prix * mwh_export
        marge = revenu - cout_eau - cout_maint
        idx = int(np.argmax(marge))
        resultats[label] = {
            "prix_DH_par_MWh": prix,
            "prodSAP_star_t_mois": float(grid[idx]),
            "export_GTA_star_t_mois": float(e_export[idx]),
            "bypass_star_t_mois": float(bypass[idx]),
            "mwh_exportes_star": float(mwh_export[idx]),
            "marge_optimale_DH_mois": float(marge[idx]),
            "marge_optimale_DH_an": float(marge[idx] * 12),
        }

    c = resultats["centrale"]
    print(
        "[transform] Optimum (hypothèse centrale) : "
        f"ProdSAP*={c['prodSAP_star_t_mois']:.0f} t/mois, "
        f"M={c['marge_optimale_DH_mois']:.0f} DH/mois ({c['marge_optimale_DH_an']/1e6:.2f} MDH/an)"
    )
    return resultats


def transform(df: pd.DataFrame, run_optimization: bool = True) -> tuple[pd.DataFrame, dict, dict | None]:
    df_clean = clean(df)
    regression = fit_regression(df_clean)

    optimal = None
    if run_optimization:
        optimal = run_milp(df_clean)

    return df_clean, regression, optimal
