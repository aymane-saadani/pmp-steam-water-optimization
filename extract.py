"""
Extract : lecture du fichier Excel historique (17 mois, une ligne par mois).
"""

import pandas as pd
from pathlib import Path


def extract(excel_path: Path, sheet_name, columns_map: dict) -> pd.DataFrame:
    
    if not excel_path.exists():
        raise FileNotFoundError(
            f"Fichier introuvable : {excel_path}. "
            "Vérifie config.EXCEL_PATH."
        )

    df_raw = pd.read_excel(excel_path, sheet_name=sheet_name)

    missing = [excel_col for excel_col in columns_map.values() if excel_col not in df_raw.columns]
    if missing:
        raise KeyError(
            f"Colonnes attendues absentes du fichier Excel : {missing}. "
            f"En-têtes trouvées : {list(df_raw.columns)}. "
            
        )

    # Renommage Excel -> noms internes (inverse du mapping)
    rename_map = {v: k for k, v in columns_map.items()}
    df = df_raw.rename(columns=rename_map)

    print(f"[extract] {len(df)} lignes lues depuis {excel_path.name}")
    return df


def filter_scope(df: pd.DataFrame, exclude_months: list, mois_col: str = "mois") -> pd.DataFrame:

    mois_str = pd.to_datetime(df[mois_col]).dt.strftime("%Y-%m")
    mask = ~mois_str.isin(exclude_months)

    n_excluded = (~mask).sum()
    if n_excluded:
        excluded = mois_str[~mask].tolist()
        print(f"[extract] {n_excluded} ligne(s) exclue(s) du périmètre : {excluded}")

    return df[mask].reset_index(drop=True)
