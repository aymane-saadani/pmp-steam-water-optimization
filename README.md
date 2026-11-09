# Pilotage énergétique de la boucle eau-vapeur — PMP

Projet de fin d'année réalisé lors de mon stage à PMP (Jorf Lasfar).
Pipeline Python et dashboard pour optimiser la marge liée à l'export d'électricité du GTA et réduire les pertes de vapeur (bypass).

## Contenu
- `comparateur_energetique_PMP.py` : génère le classeur Excel de comparaison de scénarios
- `main.py` : pipeline (extraction, régression, optimum, backtesting, KPI, sensibilité)
- `dashboard_pilotage_pmp.html` : dashboard opérateur

## Outils
Python, pandas, NumPy, SQLite, openpyxl, HTML/JavaScript

## Installation
pip install -r requirements.txt

## Utilisation
python main.py --serve

Les données historiques sont confidentielles et ne sont pas incluses.
