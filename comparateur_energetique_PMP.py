"""
Comparateur de scenarios energetiques -- boucle eau-vapeur PMP

"""

import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, NamedStyle
from openpyxl.comments import Comment
from openpyxl.chart import LineChart, Reference
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName

# ---------------------------------------------------------------------------
# 0. VALEURS DE DEPART (celles qui seront ecrites dans l'onglet Parametres)
# ---------------------------------------------------------------------------
CAP_GTA = 138.2            # t/h -- plafond turbine (design)
HEURES_MOIS = 730.5        # h -- moyenne (8766 h/an / 12)
RATIO_TURBINE = 5.02       # t vapeur / MWh (ratio reel, Ch.4.3.2)
TAU_PURGE_TOTAL = 0.0414   # 4,14% (Blowdown+Flash+Eau residuelle / HP_total, 4.3.1)
CAP_CHAUDIERE_UNIT = 87.8  # t/h -- capacite d'une seule chaudiere (Ch.2)

COEF_A = -0.00000105       # regression E_reel(ProdSAP), Ch.5.4.3 / 6.6.3
COEF_B = 1.16998
COEF_C = -8888.17

C_EAU = 19.61              # DH/t -- eau demineralisee TED
C_MAINT_UNIT = 0.0         # DH/mois/chaudiere -- NON COMMUNIQUE, voir commentaire cellule
P_ELEC_BASSE = 241.73      # DH/MWh -- heures creuses
P_ELEC_CENTRALE = 386.55   # DH/MWh -- moyenne ponderee grille ONE
P_ELEC_HAUTE = 578.16      # DH/MWh -- heures pointe

PROD_MIN, PROD_MAX, PAS = 40_000, 135_000, 500   # grille de la table Resultats

# ---------------------------------------------------------------------------
# 1. STYLES REUTILISABLES
# ---------------------------------------------------------------------------
FONT_TITRE = Font(name="Arial", size=14, bold=True, color="FFFFFF")
FONT_SECTION = Font(name="Arial", size=11, bold=True, color="1F4E78")
FONT_ENTETE = Font(name="Arial", size=10, bold=True, color="FFFFFF")
FONT_NORMAL = Font(name="Arial", size=10)
FONT_INPUT = Font(name="Arial", size=10, color="0000FF")          # bleu = donnee d'entree
FONT_LABEL = Font(name="Arial", size=10, italic=True, color="595959")
FONT_RESULT = Font(name="Arial", size=11, bold=True, color="1F4E78")

FILL_TITRE = PatternFill("solid", fgColor="1F4E78")       # bleu fonce
FILL_SECTION = PatternFill("solid", fgColor="D9E2F3")     # bleu clair
FILL_ENTETE = PatternFill("solid", fgColor="2E75B6")      # bleu moyen
FILL_INPUT = PatternFill("solid", fgColor="FFF2CC")       # jaune pale (a completer / modifiable)
FILL_OPTIMUM = PatternFill("solid", fgColor="E2EFDA")     # vert pale (ligne optimale)
FILL_ALT = PatternFill("solid", fgColor="F2F2F2")         # gris tres clair (zebrage)

BORDER_THIN = Border(*[Side(style="thin", color="BFBFBF")] * 4)

ALIGN_CENTER = Alignment(horizontal="center", vertical="center")
ALIGN_LEFT = Alignment(horizontal="left", vertical="center")

FMT_NUM0 = "#,##0"
FMT_NUM1 = "#,##0.0"
FMT_DH0 = '#,##0" DH"'
FMT_PCT = "0.00%"


def style_header_row(ws, row, first_col, last_col):
    for c in range(first_col, last_col + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = FONT_ENTETE
        cell.fill = FILL_ENTETE
        cell.alignment = ALIGN_CENTER
        cell.border = BORDER_THIN


# ---------------------------------------------------------------------------
# 2. CREATION DU CLASSEUR
# ---------------------------------------------------------------------------
wb = Workbook()

# ============================================================
# ONGLET 1 -- PARAMETRES
# ============================================================
ws_p = wb.active
ws_p.title = "Parametres"
ws_p.sheet_view.showGridLines = False

ws_p.merge_cells("A1:D1")
ws_p["A1"] = "COMPARATEUR ENERGETIQUE PMP -- PARAMETRES DU MODELE"
ws_p["A1"].font = FONT_TITRE
ws_p["A1"].fill = FILL_TITRE
ws_p["A1"].alignment = ALIGN_CENTER
ws_p.row_dimensions[1].height = 26

headers = ["Parametre", "Valeur", "Unite", "Source / note"]
ws_p.append([])
ws_p.append(headers)
style_header_row(ws_p, 3, 1, 4)

rows_params = [
    ("SECTION", "Parametres physiques (Chapitres 2, 4, 5)", None, None),
    ("Cap_GTA", CAP_GTA, "t/h", "Plafond turbine GTA (design), Ch.5.3.4"),
    ("Heures_mois", HEURES_MOIS, "h", "Moyenne 8766 h/an / 12"),
    ("Ratio_turbine", RATIO_TURBINE, "t vapeur/MWh", "Ratio reel Conso_GTA/Prod_GTA, Ch.4.3.2"),
    ("Tau_purge_total", TAU_PURGE_TOTAL, "%", "Blowdown+Flash+Eau residuelle / HP_total, Ch.4.3.1"),
    ("Cap_chaudiere_unit", CAP_CHAUDIERE_UNIT, "t/h", "Capacite d'une chaudiere seule, Ch.2"),
    ("SECTION", "Regression E_reel(ProdSAP) -- t/mois (Ch.5.4.3 / 6.6.3)", None, None),
    ("coef_a", COEF_A, "-", "Terme quadratique"),
    ("coef_b", COEF_B, "-", "Terme lineaire"),
    ("coef_c", COEF_C, "-", "Constante"),
    ("SECTION", "Parametres economiques (Ch.4.6 / 6.3)", None, None),
    ("c_eau", C_EAU, "DH/t", "Eau demineralisee TED -- fichier prix matieres premieres"),
    ("c_maint_unit", C_MAINT_UNIT, "DH/mois/chaudiere", "NON COMMUNIQUE -- voir commentaire cellule"),
    ("p_elec_basse", P_ELEC_BASSE, "DH/MWh", "Grille ONE, heures creuses"),
    ("p_elec_centrale", P_ELEC_CENTRALE, "DH/MWh", "Grille ONE, moyenne ponderee"),
    ("p_elec_haute", P_ELEC_HAUTE, "DH/MWh", "Grille ONE, heures pointe"),
]

name_to_cell = {}   # pour creer les plages nommees ensuite
r = 4
for label, value, unit, note in rows_params:
    if label == "SECTION":
        ws_p.merge_cells(f"A{r}:D{r}")
        cell = ws_p.cell(row=r, column=1, value=value)
        cell.font = FONT_SECTION
        cell.fill = FILL_SECTION
        cell.alignment = ALIGN_LEFT
        r += 1
        continue

    ws_p.cell(row=r, column=1, value=label).font = FONT_NORMAL
    val_cell = ws_p.cell(row=r, column=2, value=value)
    val_cell.font = FONT_INPUT
    if unit == "%":
        val_cell.number_format = FMT_PCT
    else:
        val_cell.number_format = FMT_NUM1
    ws_p.cell(row=r, column=3, value=unit).font = FONT_LABEL
    note_cell = ws_p.cell(row=r, column=4, value=note)
    note_cell.font = FONT_LABEL
    note_cell.alignment = ALIGN_LEFT

    for c in range(1, 5):
        ws_p.cell(row=r, column=c).border = BORDER_THIN

    if label == "c_maint_unit":
        val_cell.fill = FILL_INPUT
        val_cell.comment = Comment(
        )

    name_to_cell[label] = f"Parametres!${get_column_letter(2)}${r}"
    r += 1

ws_p.column_dimensions["A"].width = 20
ws_p.column_dimensions["B"].width = 14
ws_p.column_dimensions["C"].width = 16
ws_p.column_dimensions["D"].width = 62

# Plages nommees (permettent des formules lisibles dans les autres onglets)
for name, ref in name_to_cell.items():
    wb.defined_names[name] = DefinedName(name, attr_text=ref)

# ============================================================
# ONGLET 2 -- RESULTATS (grille complete, calculee par formules)
# ============================================================
ws_r = wb.create_sheet("Resultats")
ws_r.sheet_view.showGridLines = False

ws_r.merge_cells("A1:P1")
ws_r["A1"] = "GRILLE DE RESULTATS -- MARGE M SELON LE NIVEAU DE PRODUCTION SAP"
ws_r["A1"].font = FONT_TITRE
ws_r["A1"].fill = FILL_TITRE
ws_r["A1"].alignment = ALIGN_CENTER
ws_r.row_dimensions[1].height = 24

col_headers = [
    "ProdSAP\n(t/mois)", "E_brut\n(t/mois)", "E export\n(t/mois)", "Bypass B\n(t/mois)",
    "MWh\nexportes", "Eau alim. FW\n(t/mois)", "Cout eau\n(DH)", "Nb\nchaudieres",
    "Cout maint.\n(DH)", "Revenu elec.\nbas (DH)", "Revenu elec.\ncentral (DH)",
    "Revenu elec.\nhaut (DH)", "M bas\n(DH)", "M central\n(DH)", "M haut\n(DH)",
    "Cout eau\n/MWh (DH)"
]
HEADER_ROW = 3
ws_r.append([])
for c, h in enumerate(col_headers, start=1):
    cell = ws_r.cell(row=HEADER_ROW, column=c, value=h)
ws_r.cell(row=HEADER_ROW, column=1)  # anchor
for c in range(1, len(col_headers) + 1):
    ws_r.cell(row=HEADER_ROW, column=c).alignment = Alignment(
        horizontal="center", vertical="center", wrap_text=True)
style_header_row(ws_r, HEADER_ROW, 1, len(col_headers))
ws_r.row_dimensions[HEADER_ROW].height = 32

first_data_row = HEADER_ROW + 1
grille = list(range(PROD_MIN, PROD_MAX + PAS, PAS))

for i, prodsap in enumerate(grille):
    row = first_data_row + i
    A = f"A{row}"
    ws_r.cell(row=row, column=1, value=prodsap)
    ws_r.cell(row=row, column=2, value=f"=coef_a*{A}^2+coef_b*{A}+coef_c")
    ws_r.cell(row=row, column=3, value=f"=MIN(B{row},Cap_GTA*Heures_mois)")
    ws_r.cell(row=row, column=4, value=f"={A}-C{row}")
    ws_r.cell(row=row, column=5, value=f"=C{row}/Ratio_turbine")
    ws_r.cell(row=row, column=6, value=f"={A}*(1+Tau_purge_total)")
    ws_r.cell(row=row, column=7, value=f"=c_eau*F{row}")
    ws_r.cell(row=row, column=8, value=f"=IF({A}/Heures_mois<=Cap_chaudiere_unit,1,2)")
    ws_r.cell(row=row, column=9, value=f"=H{row}*c_maint_unit")
    ws_r.cell(row=row, column=10, value=f"=p_elec_basse*E{row}")
    ws_r.cell(row=row, column=11, value=f"=p_elec_centrale*E{row}")
    ws_r.cell(row=row, column=12, value=f"=p_elec_haute*E{row}")
    ws_r.cell(row=row, column=13, value=f"=J{row}-G{row}-I{row}")
    ws_r.cell(row=row, column=14, value=f"=K{row}-G{row}-I{row}")
    ws_r.cell(row=row, column=15, value=f"=L{row}-G{row}-I{row}")
    ws_r.cell(row=row, column=16, value=f"=IFERROR(G{row}/E{row},\"\")")

    fmts = {1: FMT_NUM0, 2: FMT_NUM0, 3: FMT_NUM0, 4: FMT_NUM0, 5: FMT_NUM0,
            6: FMT_NUM0, 7: FMT_DH0, 8: "0", 9: FMT_DH0, 10: FMT_DH0, 11: FMT_DH0,
            12: FMT_DH0, 13: FMT_DH0, 14: FMT_DH0, 15: FMT_DH0, 16: FMT_NUM1}
    for c in range(1, 17):
        cell = ws_r.cell(row=row, column=c)
        cell.font = FONT_NORMAL
        cell.number_format = fmts[c]
        cell.alignment = ALIGN_CENTER
        if i % 2 == 1:
            cell.fill = FILL_ALT

last_data_row = first_data_row + len(grille) - 1

col_widths = [10, 10, 10, 10, 9, 10, 11, 8, 11, 12, 12, 12, 12, 12, 12, 10]
for c, w in enumerate(col_widths, start=1):
    ws_r.column_dimensions[get_column_letter(c)].width = w

ws_r.freeze_panes = f"A{first_data_row}"

# ============================================================
# ONGLET 3 -- SCENARIO OPTIMAL
# ============================================================
ws_s = wb.create_sheet("Scenario optimal")
ws_s.sheet_view.showGridLines = False

ws_s.merge_cells("A1:F1")
ws_s["A1"] = "SCENARIO OPTIMAL -- SYNTHESE PAR HYPOTHESE DE PRIX ELECTRIQUE"
ws_s["A1"].font = FONT_TITRE
ws_s["A1"].fill = FILL_TITRE
ws_s["A1"].alignment = ALIGN_CENTER
ws_s.row_dimensions[1].height = 26

headers_s = ["Hypothese", "Prix elec.\n(DH/MWh)", "ProdSAP*\n(t/mois)",
             "Export GTA*\n(t/mois)", "Bypass*\n(t/mois)", "MWh\nexportes*",
             "M optimal\n(DH/mois)", "M optimal\n(DH/an)"]
row_h = 3
for c, h in enumerate(headers_s, start=1):
    ws_s.cell(row=row_h, column=c, value=h)
style_header_row(ws_s, row_h, 1, len(headers_s))
for c in range(1, len(headers_s) + 1):
    ws_s.cell(row=row_h, column=c).alignment = Alignment(
        horizontal="center", vertical="center", wrap_text=True)
ws_s.row_dimensions[row_h].height = 30

scenarios = [
    ("Basse (heures creuses)", "p_elec_basse", "M", "J"),
    ("Centrale (moyenne ponderee)", "p_elec_centrale", "N", "K"),
    ("Haute (heures pointe)", "p_elec_haute", "O", "L"),
]

for i, (label, prix_name, col_M, col_rev) in enumerate(scenarios):
    row = row_h + 1 + i
    rng_M = f"Resultats!{col_M}{first_data_row}:{col_M}{last_data_row}"
    rng_A = f"Resultats!A{first_data_row}:A{last_data_row}"
    rng_C = f"Resultats!C{first_data_row}:C{last_data_row}"
    rng_D = f"Resultats!D{first_data_row}:D{last_data_row}"
    rng_E = f"Resultats!E{first_data_row}:E{last_data_row}"

    ws_s.cell(row=row, column=1, value=label).font = FONT_NORMAL
    ws_s.cell(row=row, column=2, value=f"={prix_name}").number_format = FMT_NUM1
    ws_s.cell(row=row, column=3,
              value=f"=INDEX({rng_A},MATCH(MAX({rng_M}),{rng_M},0))").number_format = FMT_NUM0
    ws_s.cell(row=row, column=4,
              value=f"=INDEX({rng_C},MATCH(MAX({rng_M}),{rng_M},0))").number_format = FMT_NUM0
    ws_s.cell(row=row, column=5,
              value=f"=INDEX({rng_D},MATCH(MAX({rng_M}),{rng_M},0))").number_format = FMT_NUM0
    ws_s.cell(row=row, column=6,
              value=f"=INDEX({rng_E},MATCH(MAX({rng_M}),{rng_M},0))").number_format = FMT_NUM0
    m_cell = ws_s.cell(row=row, column=7, value=f"=MAX({rng_M})")
    m_cell.number_format = FMT_DH0
    m_cell.font = FONT_RESULT
    an_cell = ws_s.cell(row=row, column=8, value=f"=G{row}*12")
    an_cell.number_format = FMT_DH0
    an_cell.font = FONT_RESULT

    for c in range(1, 9):
        cell = ws_s.cell(row=row, column=c)
        cell.border = BORDER_THIN
        cell.alignment = ALIGN_CENTER
        if label.startswith("Centrale"):
            cell.fill = FILL_OPTIMUM

col_widths_s = [24, 12, 12, 13, 11, 11, 14, 15]
for c, w in enumerate(col_widths_s, start=1):
    ws_s.column_dimensions[get_column_letter(c)].width = w

# --- Note de lecture ---
note_row = row_h + len(scenarios) + 2
ws_s.merge_cells(f"A{note_row}:H{note_row+3}")
note_cell = ws_s.cell(
    row=note_row, column=1,
    value=()
)
note_cell.font = FONT_LABEL
note_cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)

# --- Graphique M(ProdSAP) pour les 3 hypotheses ---
chart = LineChart()
chart.title = "Marge M selon le niveau de production SAP"
chart.style = 2
chart.x_axis.title = "ProdSAP (t/mois)"
chart.y_axis.title = "Marge M (DH/mois)"
chart.height = 10
chart.width = 22

cats = Reference(ws_r, min_col=1, min_row=first_data_row, max_row=last_data_row)
for col, name in [(13, "M bas (creuses)"), (14, "M central"), (15, "M haut (pointe)")]:
    data = Reference(ws_r, min_col=col, min_row=HEADER_ROW, max_row=last_data_row)
    chart.add_data(data, titles_from_data=True)
chart.set_categories(cats)

chart_anchor_row = note_row + 5
ws_s.add_chart(chart, f"A{chart_anchor_row}")

# ---------------------------------------------------------------------------
# 3. ENREGISTREMENT
# ---------------------------------------------------------------------------
wb.save("comparateur_energetique_PMP.xlsx")
print("Fichier 'comparateur_energetique_PMP.xlsx' genere avec succes.")
print(f"Grille : {len(grille)} lignes, de {PROD_MIN} a {PROD_MAX} t/mois (pas {PAS}).")
