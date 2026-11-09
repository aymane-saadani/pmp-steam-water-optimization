"""
Configuration du pipeline de pilotage PMP.

"""

from pathlib import Path

# --- Chemins ---
EXCEL_PATH = Path("data/historique_pmp.xlsx")   # À ADAPTER : chemin réel de ton fichier
SHEET_NAME = 0                                    # nom ou index de la feuille

DB_PATH = Path("output/pilotage_pmp.db")
JSON_OUTPUT_PATH = Path("output/dashboard_data.json")

# --- Mapping colonnes Excel -> noms internes standardisés ---
# Clé = nom interne utilisé dans le pipeline
# Valeur = en-tête EXACTE telle qu'elle apparaît dans ton Excel
# À ADAPTER selon tes vrais en-têtes (copie-les tels quels, espaces/accents compris)
COLUMNS = {
    "mois":                 "Mois",
    "prod_sap":             "Prod_SAP_t",
    "vap_hp_gta":           "Vap_HP_GTA_t",            # vapeur HP envoyée à la turbine
    "bypass":               "Vap_HP_Detente_t",        # vapeur bypassée via PV-050A (détente HP)
    "vap_bp_extract_gta":   "Vap_BP_Extract_GTA_t",
    "vap_bp_detente_hp_bp": "Vap_BP_Detente_HP_BP_t",
    "vap_bp_conso_pap":     "Vap_BP_Conso_PAP_t",
    "e_reel":               "Prod_Elec_GTA_MWh",       # énergie électrique réelle produite
    "conso_usine":          "Conso_Usine_MWh",
    "elec_export_hcr":      "Elec_Export_HCr_MWh",
    "elec_export_hpl":      "Elec_Export_HPl_MWh",
    "elec_export_hptes":    "Elec_Export_HPtes_MWh",
    "eau_alim_total":       "Eau_Alim_Total_t",
    "heures_gta":           "Heures_GTA",
}


REQUIRED_FOR_REGRESSION = ["prod_sap", "e_reel"]


EXCLUDE_MONTHS = ["2026-06"]  # format "YYYY-MM"


SEUIL_REGIME_NOMINAL = 85_000  # t/mois
