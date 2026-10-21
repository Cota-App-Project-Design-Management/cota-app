"""
Módulo de Cotización y Presupuesto de COTA APP.
Permite:
1. Generar la plantilla oficial en Excel (.xlsx) con fórmulas automáticas (Hoja 1: Presupuesto, Hoja 2: Control de Pagos)
   para que el cliente o el estudio la llene, configurando previamente desde COTA los porcentajes de Gastos Generales,
   Gestión y Supervisión (Utilidades) y si aplica IGV (18%).
2. Leer e interpretar archivos Excel (.xlsx, .xls) o CSV (.csv) del formato de cotización,
   identificando automáticamente:
   - Cabecera: Proyecto, Cliente, Fecha y Tipo de Cambio (TC)
   - Partidas principales (1, 2, 3...) y sus Sub-totales / Mix
   - Tareas por partida (1.01, 1.02, 2.01...) con Moneda, Unidad, Metrado, Valor Unitario y Presupuesto asignado
   - Resumen financiero: Sub Total (Casco), Gastos Generales (GG), Gestión y Supervisión de Obras (Utilidades), IGV y TOTAL.
3. Importar la cotización directamente a un proyecto nuevo o existente en COTA APP.
"""

import datetime
import io
import re
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
import pandas as pd
import streamlit as st

from cota.db import COLS_P_INFO, COLS_PROY, COLS_TASKS, clear_base_dfs
from cota.utils import safe_float, safe_str


# ==========================================
# 1. GENERADOR DE PLANTILLA EXCEL DE COTIZACIÓN
# ==========================================

ESTRUCTURA_COTIZACION_DEFAULT = [
    {"codigo": "1", "nombre": "", "subitems": ["1.01", "1.02", "1.03", "1.04", "1.05", "1.06"]},
    {"codigo": "2", "nombre": "", "subitems": ["2.01", "2.02", "2.03", "2.04", "2.05", "2.06", "2.07"]},
    {"codigo": "3", "nombre": "", "subitems": ["3.01", "3.02", "3.03"]},
]


def generar_plantilla_cotizacion_venti(
    proyecto: str = "",
    cliente: str = "",
    tc: float = 3.42,
    fecha: str = None,
    partidas_precargadas: list = None,
    gg_pct: float = 0.02,
    gestion_pct: float = 0.15,
    incluir_igv: bool = False,
) -> bytes:
    """
    Construye un archivo Excel (.xlsx) con el Formato Oficial de Cotización COTA.
    Incluye:
    - Hoja 1 ('Presupuesto'): Partidas (1, 2, 3...), Tareas (1.01, 1.02...), fórmulas de Valor Parcial,
      Sub Total (S/.), Mix (%), SUB TOTAL (Casco), Gastos generales, Gestión y supervisión de obras,
      IGV (18% si incluir_igv=True o 0% / -% si False) y TOTAL integrado en Soles y Dólares.
    - Hoja 2 ('Control de Pagos'): Cronograma de desembolsos por semanas integrado simétricamente
      (sin cuadro de números de cuenta).
    """
    if not fecha:
        fecha = datetime.date.today().strftime("%Y-%m-%d")

    # Si el usuario pasa porcentajes como 2 o 15 en lugar de 0.02 o 0.15, normalizar a decimal
    gg_dec = float(gg_pct) / 100.0 if float(gg_pct) > 1.0 else float(gg_pct)
    ges_dec = float(gestion_pct) / 100.0 if float(gestion_pct) > 1.0 else float(gestion_pct)

    wb = openpyxl.Workbook()

    # Estilos consistentes con COTA
    font_family = "Calibri"
    f_title = Font(name=font_family, size=11, bold=True, color="262320")
    f_header = Font(name=font_family, size=10, bold=True, color="FFFFFF")
    f_partida = Font(name=font_family, size=10, bold=True, color="262320")
    f_task = Font(name=font_family, size=10, bold=False, color="262320")
    f_footer = Font(name=font_family, size=10, bold=True, color="262320")
    f_total = Font(name=font_family, size=10, bold=True, color="FFFFFF")
    f_usd = Font(name=font_family, size=10, bold=True, color="262320")

    fill_header = PatternFill(start_color="262320", end_color="262320", fill_type="solid")
    fill_partida = PatternFill(start_color="EFECE6", end_color="EFECE6", fill_type="solid")
    fill_subtotal = PatternFill(start_color="DFD9CE", end_color="DFD9CE", fill_type="solid")
    fill_total = PatternFill(start_color="C85A32", end_color="C85A32", fill_type="solid")
    fill_usd = PatternFill(start_color="EFECE6", end_color="EFECE6", fill_type="solid")
    fill_input = PatternFill(start_color="FAF8F5", end_color="FAF8F5", fill_type="solid")

    thin_side = Side(border_style="thin", color="D0C9BD")
    med_bottom = Side(border_style="medium", color="262320")
    border_cell = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
    border_partida = Border(left=thin_side, right=thin_side, top=thin_side, bottom=med_bottom)
    border_closing = Border(left=thin_side, right=thin_side, top=thin_side, bottom=med_bottom)

    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)
    align_right = Alignment(horizontal="right", vertical="center", wrap_text=True)

    # ==========================================
    # HOJA 1: PRESUPUESTO
    # ==========================================
    ws1 = wb.active
    ws1.title = "Presupuesto"
    ws1.views.sheetView[0].showGridLines = True

    # Fila 2: Proyecto y Fecha
    ws1["B2"] = "Proyecto"
    ws1["B2"].font = f_title
    ws1["C2"] = proyecto
    ws1["C2"].font = f_title
    ws1["I2"] = fecha
    ws1["I2"].font = f_task
    ws1["I2"].alignment = align_center

    # Fila 4: Cliente y Tipo de Cambio (TC)
    ws1["B4"] = "Cliente:"
    ws1["B4"].font = f_title
    ws1["C4"] = cliente
    ws1["C4"].font = f_title
    ws1["I4"] = "TC:"
    ws1["I4"].font = f_title
    ws1["I4"].alignment = align_right
    ws1["J4"] = float(tc)
    ws1["J4"].font = f_title
    ws1["J4"].number_format = "0.00"
    ws1["J4"].alignment = align_center

    # Fila 5: Cabecera de tabla
    headers_h1 = [
        ("B", "Ítem"),
        ("C", "Descripción"),
        ("D", "Moneda"),
        ("E", "Unidad"),
        ("F", "Metrado"),
        ("G", "Valor\nUnitario"),
        ("H", "Valor\nParcial"),
        ("I", "Sub Total (S/.)"),
        ("J", "Mix"),
    ]
    ws1.row_dimensions[5].height = 28
    for col_let, text in headers_h1:
        cell = ws1[f"{col_let}5"]
        cell.value = text
        cell.font = f_header
        cell.fill = fill_header
        cell.alignment = align_center
        cell.border = border_cell

    estructura = partidas_precargadas if partidas_precargadas else ESTRUCTURA_COTIZACION_DEFAULT

    curr_row = 6
    partida_rows = []

    for part in estructura:
        p_row = curr_row
        partida_rows.append(p_row)
        p_cod = part.get("codigo", str(len(partida_rows)))
        p_nom = part.get("nombre", "")
        subitems = part.get("subitems", [])

        first_task_row = p_row + 1
        last_task_row = p_row + len(subitems)

        ws1[f"B{p_row}"] = int(p_cod) if str(p_cod).isdigit() else p_cod
        ws1[f"B{p_row}"].alignment = align_center
        ws1[f"C{p_row}"] = p_nom
        ws1[f"C{p_row}"].alignment = align_left

        if last_task_row >= first_task_row:
            ws1[f"I{p_row}"] = f"=SUM(H{first_task_row}:H{last_task_row})"
        else:
            ws1[f"I{p_row}"] = float(part.get("monto_pactado", 0.0))

        ws1[f"I{p_row}"].number_format = "#,##0.00"
        ws1[f"I{p_row}"].alignment = align_right
        ws1[f"J{p_row}"].number_format = "0.0%"
        ws1[f"J{p_row}"].alignment = align_center

        for c_idx in range(2, 11):
            c_let = get_column_letter(c_idx)
            ws1[f"{c_let}{p_row}"].font = f_partida
            ws1[f"{c_let}{p_row}"].fill = fill_partida
            ws1[f"{c_let}{p_row}"].border = border_partida

        curr_row += 1

        # Filas de tareas (1.01, 1.02...)
        for sub in subitems:
            t_row = curr_row
            if isinstance(sub, dict):
                t_cod = sub.get("codigo", "")
                t_desc = sub.get("descripcion", "")
                t_mon = sub.get("moneda", "Soles")
                t_und = sub.get("unidad", "glb")
                t_met = safe_float(sub.get("metrado", 1), 1.0)
                t_vu = sub.get("valor_unitario", None)
            else:
                t_cod = str(sub)
                t_desc = ""
                t_mon = "Soles"
                t_und = "glb"
                t_met = 1
                t_vu = None

            # Escribir código numérico con formato 0.00 para evitar triángulo verde de advertencia en Excel
            try:
                ws1[f"B{t_row}"] = float(t_cod)
                ws1[f"B{t_row}"].number_format = "0.00"
            except ValueError:
                ws1[f"B{t_row}"] = t_cod
            ws1[f"B{t_row}"].alignment = align_center

            ws1[f"C{t_row}"] = t_desc
            ws1[f"C{t_row}"].alignment = align_left
            ws1[f"C{t_row}"].fill = fill_input

            ws1[f"D{t_row}"] = t_mon
            ws1[f"D{t_row}"].alignment = align_center

            ws1[f"E{t_row}"] = t_und
            ws1[f"E{t_row}"].alignment = align_center

            ws1[f"F{t_row}"] = t_met
            ws1[f"F{t_row}"].alignment = align_center
            ws1[f"F{t_row}"].number_format = "#,##0.00"
            ws1[f"F{t_row}"].fill = fill_input

            if t_vu is not None and safe_float(t_vu, 0.0) > 0:
                ws1[f"G{t_row}"] = safe_float(t_vu, 0.0)
            ws1[f"G{t_row}"].alignment = align_right
            ws1[f"G{t_row}"].number_format = "#,##0.00"
            ws1[f"G{t_row}"].fill = fill_input

            # Valor Parcial: convierte a Soles si Moneda es Dólares, sino Metrado * Valor Unitario
            ws1[f"H{t_row}"] = f'=IF(OR(UPPER(TRIM(D{t_row}))="DÓLARES",UPPER(TRIM(D{t_row}))="DOLARES",UPPER(TRIM(D{t_row}))="USD"),F{t_row}*G{t_row}*$J$4,F{t_row}*G{t_row})'
            ws1[f"H{t_row}"].alignment = align_right
            ws1[f"H{t_row}"].number_format = "#,##0.00"

            for c_idx in range(2, 11):
                c_let = get_column_letter(c_idx)
                ws1[f"{c_let}{t_row}"].font = f_task
                ws1[f"{c_let}{t_row}"].border = border_cell

            curr_row += 1

    # Fila de SUB TOTAL (Casco)
    row_subtotal_casco = curr_row
    for p_r in partida_rows:
        ws1[f"J{p_r}"] = f"=IFERROR(I{p_r}/$I${row_subtotal_casco},0)"

    sum_parts_expr = "+".join([f"I{r}" for r in partida_rows]) if partida_rows else "0"
    ws1[f"C{row_subtotal_casco}"] = "SUB TOTAL (Casco)"
    ws1[f"D{row_subtotal_casco}"] = "Soles"
    ws1[f"D{row_subtotal_casco}"].alignment = align_center
    ws1[f"I{row_subtotal_casco}"] = f"={sum_parts_expr}"
    ws1[f"I{row_subtotal_casco}"].number_format = "#,##0.00"
    ws1[f"I{row_subtotal_casco}"].alignment = align_right
    ws1[f"J{row_subtotal_casco}"] = f"=IFERROR(I{row_subtotal_casco}/I{row_subtotal_casco},0)"
    ws1[f"J{row_subtotal_casco}"].number_format = "0.0%"
    ws1[f"J{row_subtotal_casco}"].alignment = align_center

    for c_idx in range(2, 11):
        c_let = get_column_letter(c_idx)
        ws1[f"{c_let}{row_subtotal_casco}"].font = f_footer
        ws1[f"{c_let}{row_subtotal_casco}"].fill = fill_subtotal
        ws1[f"{c_let}{row_subtotal_casco}"].border = border_cell

    # Fila de Gastos generales
    row_gg = row_subtotal_casco + 1
    ws1[f"C{row_gg}"] = "Gastos generales"
    ws1[f"D{row_gg}"] = "Soles"
    ws1[f"D{row_gg}"].alignment = align_center
    ws1[f"F{row_gg}"] = gg_dec
    ws1[f"F{row_gg}"].number_format = "0.0%"
    ws1[f"F{row_gg}"].alignment = align_center
    ws1[f"H{row_gg}"] = f"=I{row_subtotal_casco}*F{row_gg}"
    ws1[f"H{row_gg}"].number_format = "#,##0.00"
    ws1[f"H{row_gg}"].alignment = align_right
    for c_idx in range(2, 11):
        c_let = get_column_letter(c_idx)
        ws1[f"{c_let}{row_gg}"].font = f_footer
        ws1[f"{c_let}{row_gg}"].border = border_cell

    # Fila de Gestión y supervisión de obras (Utilidades)
    row_gestion = row_gg + 1
    ws1[f"C{row_gestion}"] = "Gestión y supervisión de obras"
    ws1[f"D{row_gestion}"] = "Soles"
    ws1[f"D{row_gestion}"].alignment = align_center
    ws1[f"F{row_gestion}"] = ges_dec
    ws1[f"F{row_gestion}"].number_format = "0.0%"
    ws1[f"F{row_gestion}"].alignment = align_center
    ws1[f"H{row_gestion}"] = f"=I{row_subtotal_casco}*F{row_gestion}"
    ws1[f"H{row_gestion}"].number_format = "#,##0.00"
    ws1[f"H{row_gestion}"].alignment = align_right
    for c_idx in range(2, 11):
        c_let = get_column_letter(c_idx)
        ws1[f"{c_let}{row_gestion}"].font = f_footer
        ws1[f"{c_let}{row_gestion}"].border = border_cell

    # Fila de IGV (18% si se marca la casilla en COTA, o 0% / -% si no se marca)
    row_igv = row_gestion + 1
    ws1[f"C{row_igv}"] = "IGV"
    ws1[f"D{row_igv}"] = "Soles"
    ws1[f"D{row_igv}"].alignment = align_center
    if incluir_igv:
        ws1[f"F{row_igv}"] = 0.18
        ws1[f"F{row_igv}"].number_format = "0%"
    else:
        ws1[f"F{row_igv}"] = 0.0
        ws1[f"F{row_igv}"].number_format = "0%"
    ws1[f"F{row_igv}"].alignment = align_center
    ws1[f"H{row_igv}"] = f"=IF(ISNUMBER(F{row_igv}),(I{row_subtotal_casco}+H{row_gg}+H{row_gestion})*F{row_igv},0)"
    ws1[f"H{row_igv}"].number_format = "#,##0.00"
    ws1[f"H{row_igv}"].alignment = align_right
    for c_idx in range(2, 11):
        c_let = get_column_letter(c_idx)
        ws1[f"{c_let}{row_igv}"].font = f_footer
        ws1[f"{c_let}{row_igv}"].border = border_cell

    # Fila TOTAL Soles
    row_total = row_igv + 1
    ws1[f"C{row_total}"] = "TOTAL"
    ws1[f"D{row_total}"] = "Soles"
    ws1[f"D{row_total}"].alignment = align_center
    ws1[f"I{row_total}"] = f"=I{row_subtotal_casco}+H{row_gg}+H{row_gestion}+H{row_igv}"
    ws1[f"I{row_total}"].number_format = "#,##0.00"
    ws1[f"I{row_total}"].alignment = align_right
    ws1[f"J{row_total}"] = f"=IFERROR(I{row_total}/I{row_subtotal_casco},0)"
    ws1[f"J{row_total}"].number_format = "0.0%"
    ws1[f"J{row_total}"].alignment = align_center
    for c_idx in range(2, 11):
        c_let = get_column_letter(c_idx)
        ws1[f"{c_let}{row_total}"].font = f_total
        ws1[f"{c_let}{row_total}"].fill = fill_total
        ws1[f"{c_let}{row_total}"].border = border_cell

    # Fila TOTAL Dólares (integrada simétricamente al cuadro con bordes y relleno)
    row_usd = row_total + 1
    ws1[f"C{row_usd}"] = "TOTAL (USD)"
    ws1[f"D{row_usd}"] = "Dólares"
    ws1[f"D{row_usd}"].alignment = align_center
    ws1[f"I{row_usd}"] = f"=IFERROR(I{row_total}/J4,0)"
    ws1[f"I{row_usd}"].number_format = "#,##0.00"
    ws1[f"I{row_usd}"].alignment = align_right
    for c_idx in range(2, 11):
        c_let = get_column_letter(c_idx)
        ws1[f"{c_let}{row_usd}"].font = f_usd
        ws1[f"{c_let}{row_usd}"].fill = fill_usd
        ws1[f"{c_let}{row_usd}"].border = border_closing

    # Anchos de columna Hoja 1
    col_widths_h1 = {
        "A": 3,
        "B": 9,
        "C": 44,
        "D": 12,
        "E": 10,
        "F": 12,
        "G": 15,
        "H": 15,
        "I": 16,
        "J": 12,
    }
    for col_l, w in col_widths_h1.items():
        ws1.column_dimensions[col_l].width = w

    # ==========================================
    # HOJA 2: CONTROL DE PAGOS (CRONOGRAMA SEMANAL SIN CUADRO DE CUENTAS)
    # ==========================================
    ws2 = wb.create_sheet(title="Control de Pagos")
    ws2.views.sheetView[0].showGridLines = True

    ws2["B1"] = "Proyecto"
    ws2["B1"].font = f_title
    ws2["C1"] = "=Presupuesto!C2"
    ws2["C1"].font = f_title

    ws2["B2"] = "Cliente:"
    ws2["B2"].font = f_title
    ws2["C2"] = "=Presupuesto!C4"
    ws2["C2"].font = f_title

    headers_h2 = [
        ("B", "Descripción"),
        ("C", "Moneda"),
        ("D", "TOTAL"),
        ("E", "ADELANTO 1"),
        ("F", "SEMANA 1"),
        ("G", "SEMANA 2"),
        ("H", "SEMANA 3"),
        ("I", "SEMANA 4"),
        ("J", "SEMANA 5"),
        ("K", "PAGADO"),
        ("L", "SALDO"),
    ]
    ws2.row_dimensions[4].height = 24
    for col_let, text in headers_h2:
        cell = ws2[f"{col_let}4"]
        cell.value = text
        cell.font = f_header
        cell.fill = fill_header
        cell.alignment = align_center
        cell.border = border_cell

    ws2["B6"] = "TRABAJOS CONTRATISTAS"
    ws2["B6"].font = f_partida

    r_c = 7
    first_c_row = r_c
    for idx_p, p_r in enumerate(partida_rows, start=1):
        ws2[f"B{r_c}"] = f'=IF(Presupuesto!C{p_r}="","Partida {idx_p}",Presupuesto!C{p_r})'
        ws2[f"C{r_c}"] = "Soles"
        ws2[f"C{r_c}"].alignment = align_center
        ws2[f"D{r_c}"] = f"=Presupuesto!I{p_r}"
        ws2[f"D{r_c}"].number_format = "#,##0.00"
        ws2[f"K{r_c}"] = f"=SUM(E{r_c}:J{r_c})"
        ws2[f"K{r_c}"].number_format = "#,##0.00"
        ws2[f"L{r_c}"] = f"=D{r_c}-K{r_c}"
        ws2[f"L{r_c}"].number_format = "#,##0.00"
        for c_i in range(2, 13):
            c_l = get_column_letter(c_i)
            ws2[f"{c_l}{r_c}"].font = f_task
            ws2[f"{c_l}{r_c}"].border = border_cell
        r_c += 1
    last_c_row = r_c - 1

    # SUB TOTAL Contratistas
    row_sub_h2 = r_c
    ws2[f"B{row_sub_h2}"] = "SUB TOTAL"
    ws2[f"C{row_sub_h2}"] = "Soles"
    ws2[f"C{row_sub_h2}"].alignment = align_center
    for c_i in range(4, 13):
        c_l = get_column_letter(c_i)
        ws2[f"{c_l}{row_sub_h2}"] = f"=SUM({c_l}{first_c_row}:{c_l}{last_c_row})"
        ws2[f"{c_l}{row_sub_h2}"].number_format = "#,##0.00"
    for c_i in range(2, 13):
        c_l = get_column_letter(c_i)
        ws2[f"{c_l}{row_sub_h2}"].font = f_footer
        ws2[f"{c_l}{row_sub_h2}"].fill = fill_subtotal
        ws2[f"{c_l}{row_sub_h2}"].border = border_cell

    # Gestión y supervisión de obras en Hoja 2
    row_ges_h2 = row_sub_h2 + 1
    ws2[f"B{row_ges_h2}"] = "Gestión y supervisión de obras"
    ws2[f"C{row_ges_h2}"] = "Soles"
    ws2[f"C{row_ges_h2}"].alignment = align_center
    ws2[f"D{row_ges_h2}"] = f"=Presupuesto!H{row_gestion}"
    ws2[f"D{row_ges_h2}"].number_format = "#,##0.00"
    ws2[f"K{row_ges_h2}"] = f"=SUM(E{row_ges_h2}:J{row_ges_h2})"
    ws2[f"K{row_ges_h2}"].number_format = "#,##0.00"
    ws2[f"L{row_ges_h2}"] = f"=D{row_ges_h2}-K{row_ges_h2}"
    ws2[f"L{row_ges_h2}"].number_format = "#,##0.00"
    for c_i in range(2, 13):
        c_l = get_column_letter(c_i)
        ws2[f"{c_l}{row_ges_h2}"].font = f_task
        ws2[f"{c_l}{row_ges_h2}"].border = border_cell

    # Gastos Generales en Hoja 2
    row_gg_h2 = row_ges_h2 + 1
    ws2[f"B{row_gg_h2}"] = "Gastos Generales"
    ws2[f"C{row_gg_h2}"] = "Soles"
    ws2[f"C{row_gg_h2}"].alignment = align_center
    ws2[f"D{row_gg_h2}"] = f"=Presupuesto!H{row_gg}"
    ws2[f"D{row_gg_h2}"].number_format = "#,##0.00"
    ws2[f"K{row_gg_h2}"] = f"=SUM(E{row_gg_h2}:J{row_gg_h2})"
    ws2[f"K{row_gg_h2}"].number_format = "#,##0.00"
    ws2[f"L{row_gg_h2}"] = f"=D{row_gg_h2}-K{row_gg_h2}"
    ws2[f"L{row_gg_h2}"].number_format = "#,##0.00"
    for c_i in range(2, 13):
        c_l = get_column_letter(c_i)
        ws2[f"{c_l}{row_gg_h2}"].font = f_task
        ws2[f"{c_l}{row_gg_h2}"].border = border_cell

    # TOTAL Hoja 2 (Soles)
    row_tot_h2 = row_gg_h2 + 1
    ws2[f"B{row_tot_h2}"] = "TOTAL"
    ws2[f"C{row_tot_h2}"] = "Soles"
    ws2[f"C{row_tot_h2}"].alignment = align_center
    for c_i in range(4, 13):
        c_l = get_column_letter(c_i)
        ws2[f"{c_l}{row_tot_h2}"] = f"={c_l}{row_sub_h2}+{c_l}{row_ges_h2}+{c_l}{row_gg_h2}"
        ws2[f"{c_l}{row_tot_h2}"].number_format = "#,##0.00"
    for c_i in range(2, 13):
        c_l = get_column_letter(c_i)
        ws2[f"{c_l}{row_tot_h2}"].font = f_total
        ws2[f"{c_l}{row_tot_h2}"].fill = fill_total
        ws2[f"{c_l}{row_tot_h2}"].border = border_cell

    # TOTAL Hoja 2 (Dólares) integrado simétricamente al cuadro
    row_usd_h2 = row_tot_h2 + 1
    ws2[f"B{row_usd_h2}"] = "TOTAL (USD)"
    ws2[f"C{row_usd_h2}"] = "Dólares"
    ws2[f"C{row_usd_h2}"].alignment = align_center
    for c_i in range(4, 13):
        c_l = get_column_letter(c_i)
        ws2[f"{c_l}{row_usd_h2}"] = f"=IFERROR({c_l}{row_tot_h2}/Presupuesto!$J$4,0)"
        ws2[f"{c_l}{row_usd_h2}"].number_format = "#,##0.00"
    for c_i in range(2, 13):
        c_l = get_column_letter(c_i)
        ws2[f"{c_l}{row_usd_h2}"].font = f_usd
        ws2[f"{c_l}{row_usd_h2}"].fill = fill_usd
        ws2[f"{c_l}{row_usd_h2}"].border = border_closing

    col_widths_h2 = {
        "A": 3,
        "B": 32,
        "C": 14,
        "D": 15,
        "E": 15,
        "F": 14,
        "G": 14,
        "H": 14,
        "I": 14,
        "J": 14,
        "K": 15,
        "L": 15,
    }
    for col_l, w in col_widths_h2.items():
        ws2.column_dimensions[col_l].width = w

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def exportar_proyecto_a_formato_venti(
    proy_name: str,
    tc: float = 3.42,
    gg_pct_override: float = None,
    gestion_pct_override: float = None,
    incluir_igv: bool = False,
) -> bytes:
    """
    Genera el archivo Excel de Cotización a partir de los datos actuales de un proyecto
    en st.session_state (o con la estructura vacía si el proyecto aún no tiene partidas).
    """
    df_p = st.session_state.get("proyectos", pd.DataFrame())
    proy_row = df_p[df_p["Nombre"] == proy_name].iloc[0] if not df_p.empty and proy_name in df_p["Nombre"].values else {}

    cliente = safe_str(proy_row.get("Cliente", ""))
    fecha = safe_str(proy_row.get("Inicio", "")) or datetime.date.today().strftime("%Y-%m-%d")

    df_parts = st.session_state.get("partidas", pd.DataFrame())
    parts_proy = df_parts[df_parts["Proyecto"] == proy_name] if not df_parts.empty and "Proyecto" in df_parts.columns else pd.DataFrame()

    df_pinfo = st.session_state.get("p_info", pd.DataFrame())
    df_tasks = st.session_state.get("tasks", pd.DataFrame())

    partidas_precargadas = []
    if not parts_proy.empty:
        for idx_p, (_, p_r) in enumerate(parts_proy.iterrows(), start=1):
            p_nom_raw = safe_str(p_r.get("Nombre_Partida", f"Partida {idx_p}"))
            p_nom_clean = re.sub(r"^\d+[\.\-\s]+", "", p_nom_raw).strip() or p_nom_raw

            pinfo_m = df_pinfo[(df_pinfo["Proyecto"] == proy_name) & (df_pinfo["Nombre_Partida"] == p_nom_raw)] if not df_pinfo.empty else pd.DataFrame()
            monto_pact = safe_float(pinfo_m["Monto_Pactado"].iloc[0], 0.0) if not pinfo_m.empty else 0.0

            tasks_m = df_tasks[(df_tasks["Proyecto"] == proy_name) & (df_tasks["Partida"] == p_nom_raw)] if not df_tasks.empty else pd.DataFrame()
            subitems = []
            if not tasks_m.empty:
                for idx_t, (_, t_r) in enumerate(tasks_m.iterrows(), start=1):
                    t_nom_raw = safe_str(t_r.get("Tarea", ""))
                    t_desc_clean = re.sub(r"^\d+\.\d+[\s\-:]*", "", t_nom_raw).strip() or t_nom_raw
                    t_und = safe_str(t_r.get("Unidad", "glb")) or "glb"
                    t_met = safe_float(t_r.get("Metrado", 1.0), 1.0)
                    if t_met <= 0:
                        t_met = 1.0
                    t_ppto = safe_float(t_r.get("Presupuesto", 0.0), 0.0)
                    t_vu = safe_float(t_r.get("Valor_Unitario", 0.0), 0.0)
                    if t_vu <= 0 and t_ppto > 0:
                        t_vu = round(t_ppto / t_met, 2)

                    subitems.append({
                        "codigo": f"{idx_p}.{idx_t:02d}",
                        "descripcion": t_desc_clean,
                        "moneda": "Soles",
                        "unidad": t_und,
                        "metrado": t_met,
                        "valor_unitario": t_vu,
                    })
            else:
                subitems.append({
                    "codigo": f"{idx_p}.01",
                    "descripcion": p_nom_clean if monto_pact > 0 else "",
                    "moneda": "Soles",
                    "unidad": "glb",
                    "metrado": 1.0,
                    "valor_unitario": monto_pact if monto_pact > 0 else None,
                })
                for extra_i in range(2, 5):
                    subitems.append(f"{idx_p}.{extra_i:02d}")

            partidas_precargadas.append({
                "codigo": str(idx_p),
                "nombre": p_nom_clean,
                "monto_pactado": monto_pact,
                "subitems": subitems,
            })

    subtotal_casco = 0.0
    if partidas_precargadas:
        for pp in partidas_precargadas:
            for si in pp["subitems"]:
                if isinstance(si, dict) and si.get("valor_unitario"):
                    subtotal_casco += safe_float(si["metrado"], 1.0) * safe_float(si["valor_unitario"], 0.0)

    gg_ppto = safe_float(proy_row.get("GG_Presupuesto", 0.0), 0.0)
    util_ppto = safe_float(proy_row.get("Utilidades", 0.0), 0.0)

    if gg_pct_override is not None:
        gg_pct = gg_pct_override
    else:
        gg_pct = round(gg_ppto / subtotal_casco, 4) if subtotal_casco > 0 and gg_ppto > 0 else 0.02

    if gestion_pct_override is not None:
        gestion_pct = gestion_pct_override
    else:
        gestion_pct = round(util_ppto / subtotal_casco, 4) if subtotal_casco > 0 and util_ppto > 0 else 0.15

    return generar_plantilla_cotizacion_venti(
        proyecto=proy_name,
        cliente=cliente,
        tc=tc,
        fecha=fecha,
        partidas_precargadas=partidas_precargadas if partidas_precargadas else None,
        gg_pct=gg_pct,
        gestion_pct=gestion_pct,
        incluir_igv=incluir_igv,
    )


# ==========================================
# 2. LECTOR E INTERPRETADOR INTELIGENTE DE PRESUPUESTO
# ==========================================

def _clean_cell_str(val) -> str:
    """Convierte celda a string limpio ignorando errores de Excel como #DIV/0!, #VALUE!, etc."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    s = str(val).strip()
    if s.lower() in ["nan", "none", "null", "<na>"]:
        return ""
    if s.startswith("#") and any(err in s.upper() for err in ["#DIV/0", "#VALUE", "#REF", "#NAME", "#N/A", "#NUM"]):
        return ""
    return s


def _parse_number_or_pct(val, default=0.0):
    """
    Extrae un float de una celda que puede contener moneda ('S/ 1,200.50'),
    porcentaje ('15%', '0.15', '-%') o formato latino ('3,42').
    Retorna (valor_float, es_porcentaje_explicito).
    """
    s = _clean_cell_str(val)
    if not s or s in ["-%", "-", "—"]:
        return default, False

    is_pct = "%" in s
    s_clean = re.sub(r"[S/\$\s%USDsolesdólares]", "", s, flags=re.IGNORECASE).strip()
    if not s_clean or s_clean in ["-", "."]:
        return default, is_pct

    num = safe_float(s_clean, default=default)
    if is_pct and abs(num) > 1.0:
        num = num / 100.0
    return num, is_pct


def _classify_item_code(raw_val) -> tuple:
    """
    Clasifica el código de la columna Ítem (ej. '1', '2', '1.01', '2.05').
    Retorna:
      ('partida', '1', None) para códigos de partida principal (enteros: 1, 2, 3, 01, 02)
      ('tarea', '1', '1.01') para sub-ítems / tareas con decimal (1.01, 1.02, 2.01)
      (None, None, None) si no es un código de ítem válido.
    """
    if raw_val is None or (isinstance(raw_val, float) and pd.isna(raw_val)):
        return None, None, None

    if isinstance(raw_val, int):
        if 1 <= raw_val <= 999:
            return "partida", str(raw_val), None
        return None, None, None

    if isinstance(raw_val, float):
        if raw_val <= 0 or raw_val >= 1000:
            return None, None, None
        if abs(raw_val - round(raw_val)) < 1e-6:
            return "partida", str(int(round(raw_val))), None
        else:
            p_code = str(int(raw_val))
            t_code = f"{raw_val:.2f}"
            return "tarea", p_code, t_code

    s = _clean_cell_str(raw_val)
    if not s:
        return None, None, None

    if re.match(r"^\d+,\d+$", s):
        s = s.replace(",", ".")

    m_part = re.match(r"^0*(\d+)\.?$", s)
    if m_part:
        return "partida", m_part.group(1), None

    m_task = re.match(r"^0*(\d+)\.(\d+(?:\.\d+)?)$", s)
    if m_task:
        p_code = m_task.group(1)
        sub_part = m_task.group(2)
        if len(sub_part) == 1:
            sub_part = f"0{sub_part}"
        return "tarea", p_code, f"{p_code}.{sub_part}"

    return None, None, None


def _rows_from_input(file_or_df) -> list:
    """
    Convierte cualquier fuente de entrada (UploadedFile, bytes, ruta str, io.BytesIO o DataFrame)
    en una lista de filas (listas de valores de celda).
    """
    if isinstance(file_or_df, pd.DataFrame):
        return file_or_df.values.tolist()

    raw_bytes = None
    filename = ""

    if hasattr(file_or_df, "getvalue"):
        raw_bytes = file_or_df.getvalue()
        filename = getattr(file_or_df, "name", "").lower()
    elif hasattr(file_or_df, "read"):
        raw_bytes = file_or_df.read()
        if hasattr(file_or_df, "seek"):
            file_or_df.seek(0)
        filename = getattr(file_or_df, "name", "").lower()
    elif isinstance(file_or_df, (bytes, bytearray)):
        raw_bytes = bytes(file_or_df)
    elif isinstance(file_or_df, str):
        if "\n" in file_or_df or "," in file_or_df and not file_or_df.lower().endswith((".xlsx", ".xls", ".csv")):
            df_csv = pd.read_csv(io.StringIO(file_or_df), header=None, dtype=object)
            return df_csv.values.tolist()
        else:
            filename = file_or_df.lower()
            with open(file_or_df, "rb") as f:
                raw_bytes = f.read()

    if raw_bytes is None:
        return []

    if filename.endswith((".xlsx", ".xlsm")) or raw_bytes[:4] == b"PK\x03\x04":
        wb_val = openpyxl.load_workbook(io.BytesIO(raw_bytes), data_only=True)
        wb_f = openpyxl.load_workbook(io.BytesIO(raw_bytes), data_only=False)
        sheet_name = wb_val.sheetnames[0]
        for sn in wb_val.sheetnames:
            if "presupuesto" in sn.lower() or "cotiz" in sn.lower():
                sheet_name = sn
                break
        ws_v = wb_val[sheet_name]
        ws_f = wb_f[sheet_name]

        rows = []
        for r_idx in range(1, ws_v.max_row + 1):
            row_vals = []
            for c_idx in range(1, ws_v.max_column + 1):
                v = ws_v.cell(r_idx, c_idx).value
                f_val = ws_f.cell(r_idx, c_idx).value
                if v is None and f_val is not None and not str(f_val).startswith("="):
                    v = f_val
                row_vals.append(v)
            rows.append(row_vals)
        return rows

    for enc in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
        try:
            text = raw_bytes.decode(enc)
            df_csv = pd.read_csv(io.StringIO(text), header=None, dtype=object)
            return df_csv.values.tolist()
        except Exception:
            continue

    return []


def parsear_cotizacion_venti(file_or_df) -> dict:
    """
    Lee e interpreta un archivo Excel (.xlsx) o CSV con el formato de presupuesto de COTA.
    Retorna un diccionario estructurado con:
      - 'proyecto': str
      - 'cliente': str
      - 'fecha': str
      - 'tc': float
      - 'partidas': list of dicts [{'codigo', 'nombre', 'nombre_completo', 'monto_pactado', 'mix_pct', 'tareas': [...]}]
      - 'subtotal_casco': float
      - 'gg_pct': float (porcentaje ej. 2.0)
      - 'gg_monto': float (monto en Soles para GG_Presupuesto)
      - 'utilidades_pct': float (porcentaje ej. 15.0)
      - 'utilidades_monto': float (monto en Soles para Utilidades / Gestión y supervisión)
      - 'igv_pct': float
      - 'igv_monto': float
      - 'presupuesto_total': float (TOTAL en Soles)
      - 'presupuesto_dolares': float (TOTAL en Dólares)
    """
    rows = _rows_from_input(file_or_df)

    resultado = {
        "proyecto": "",
        "cliente": "",
        "fecha": "",
        "tc": 3.42,
        "partidas": [],
        "subtotal_casco": 0.0,
        "gg_pct": 0.0,
        "gg_monto": 0.0,
        "utilidades_pct": 0.0,
        "utilidades_monto": 0.0,
        "igv_pct": 0.0,
        "igv_monto": 0.0,
        "presupuesto_total": 0.0,
        "presupuesto_dolares": 0.0,
    }

    if not rows:
        return resultado

    header_row_idx = None
    col_map = {
        "codigo": 1,
        "descripcion": 2,
        "moneda": 3,
        "unidad": 4,
        "metrado": 5,
        "valor_unitario": 6,
        "valor_parcial": 7,
        "subtotal": 8,
        "mix": 9,
    }

    for r_i, row in enumerate(rows[:25]):
        row_strs = [_clean_cell_str(c).lower() for c in row]
        has_desc = any("descrip" in s for s in row_strs)
        has_mon_or_und = any(("moneda" in s or "unidad" in s or "metrado" in s) for s in row_strs)
        if has_desc and has_mon_or_und:
            header_row_idx = r_i
            for c_i, s in enumerate(row_strs):
                if "descrip" in s:
                    col_map["descripcion"] = c_i
                    if c_i > 0:
                        col_map["codigo"] = c_i - 1
                elif "moneda" in s:
                    col_map["moneda"] = c_i
                elif "unidad" in s:
                    col_map["unidad"] = c_i
                elif "metrado" in s or "cant" in s:
                    col_map["metrado"] = c_i
                elif "unitario" in s:
                    col_map["valor_unitario"] = c_i
                elif "parcial" in s:
                    col_map["valor_parcial"] = c_i
                elif "sub total" in s or "subtotal" in s:
                    col_map["subtotal"] = c_i
                elif "mix" in s:
                    col_map["mix"] = c_i
            break

    if header_row_idx is None:
        header_row_idx = 4

    # Extraer metadatos de las filas superiores (Proyecto, Cliente, Fecha, TC)
    for r_i in range(0, min(header_row_idx + 1, len(rows))):
        row = rows[r_i]
        for c_i, cell in enumerate(row):
            s = _clean_cell_str(cell)
            if not s:
                continue
            s_low = s.lower()

            if s_low.startswith("proyecto"):
                inline_val = re.sub(r"^proyecto\s*:?\s*", "", s, flags=re.IGNORECASE).strip()
                if inline_val:
                    resultado["proyecto"] = inline_val
                else:
                    for next_c in range(c_i + 1, len(row)):
                        cand = _clean_cell_str(row[next_c])
                        if not cand:
                            continue
                        if re.match(r"^\d{4}-\d{2}-\d{2}", cand) or re.match(r"^\d{2}/\d{2}/\d{4}", cand):
                            resultado["fecha"] = cand.split(" ")[0]
                        elif not cand.lower().startswith("tc") and not resultado["proyecto"]:
                            resultado["proyecto"] = cand

            if re.match(r"^\d{4}-\d{2}-\d{2}", s) or re.match(r"^\d{2}/\d{2}/\d{4}", s):
                if not resultado["fecha"]:
                    resultado["fecha"] = s.split(" ")[0]

            if s_low.startswith("cliente"):
                inline_cli = re.sub(r"^cliente\s*:?\s*", "", s, flags=re.IGNORECASE).strip()
                if inline_cli:
                    resultado["cliente"] = inline_cli
                else:
                    for next_c in range(c_i + 1, len(row)):
                        cand = _clean_cell_str(row[next_c])
                        if not cand:
                            continue
                        if cand.lower().startswith("tc"):
                            break
                        if not resultado["cliente"]:
                            resultado["cliente"] = cand
                            break

            if s_low in ["tc", "tc:", "t.c.", "t.c:", "tipo de cambio", "tipo de cambio:"]:
                for next_c in range(c_i + 1, len(row)):
                    tc_val, _ = _parse_number_or_pct(row[next_c], default=0.0)
                    if tc_val > 0:
                        resultado["tc"] = tc_val
                        break

    tc = resultado["tc"] if resultado["tc"] > 0 else 3.42

    partidas_dict = {}
    partidas_order = []
    in_footer = False

    raw_subtotal_casco = 0.0
    raw_gg_factor_or_val = None
    raw_gg_is_pct = False
    raw_gg_amount = 0.0

    raw_util_factor_or_val = None
    raw_util_is_pct = False
    raw_util_amount = 0.0

    raw_igv_factor_or_val = None
    raw_igv_is_pct = False
    raw_igv_amount = 0.0

    raw_total_soles = 0.0

    def _get_col(row_list, key):
        idx = col_map.get(key)
        if idx is not None and 0 <= idx < len(row_list):
            return row_list[idx]
        return None

    for r_i in range(header_row_idx + 1, len(rows)):
        row = rows[r_i]
        if not any(_clean_cell_str(x) for x in row):
            continue

        row_joined = " ".join(_clean_cell_str(x) for x in row).lower()
        if "numeros de cuenta" in row_joined or "números de cuenta" in row_joined:
            break
        if "adelanto 1" in row_joined and "semana 1" in row_joined:
            break
        if "trabajos contratistas" in row_joined:
            break

        raw_code = _get_col(row, "codigo")
        desc = _clean_cell_str(_get_col(row, "descripcion"))
        moneda = _clean_cell_str(_get_col(row, "moneda")) or "Soles"
        unidad = _clean_cell_str(_get_col(row, "unidad")) or "glb"

        desc_low = desc.lower()

        if any(
            kw in desc_low
            for kw in [
                "sub total",
                "subtotal",
                "gastos generales",
                "gestión y supervisión",
                "gestion y supervision",
                "supervisión de obra",
                "supervision de obra",
                "utilidad",
                "honorario",
                "igv",
                "total (usd)",
            ]
        ) or desc_low == "total":
            in_footer = True
            val_met, met_is_pct = _parse_number_or_pct(_get_col(row, "metrado"), 0.0)
            val_vu, vu_is_pct = _parse_number_or_pct(_get_col(row, "valor_unitario"), 0.0)
            val_vp, _ = _parse_number_or_pct(_get_col(row, "valor_parcial"), 0.0)
            val_st, _ = _parse_number_or_pct(_get_col(row, "subtotal"), 0.0)

            best_amount = val_st if val_st > 0 else val_vp
            factor_cand = val_met if val_met > 0 else val_vu
            is_pct_cand = met_is_pct or vu_is_pct or (0 < factor_cand <= 1.0)

            if "sub total" in desc_low or "subtotal" in desc_low:
                if raw_subtotal_casco == 0.0 and best_amount > 0:
                    raw_subtotal_casco = best_amount
            elif "gastos generales" in desc_low:
                if best_amount > 0:
                    raw_gg_amount = best_amount
                if factor_cand > 0:
                    raw_gg_factor_or_val = factor_cand
                    raw_gg_is_pct = is_pct_cand
            elif any(k in desc_low for k in ["gestión", "gestion", "supervisión", "supervision", "utilidad", "honorario"]):
                if best_amount > 0:
                    raw_util_amount = best_amount
                if factor_cand > 0:
                    raw_util_factor_or_val = factor_cand
                    raw_util_is_pct = is_pct_cand
            elif desc_low == "igv" or desc_low.startswith("igv "):
                if best_amount > 0:
                    raw_igv_amount = best_amount
                if factor_cand > 0:
                    raw_igv_factor_or_val = factor_cand
                    raw_igv_is_pct = is_pct_cand
            elif desc_low == "total" and not any(d in moneda.lower() for d in ["dolar", "dólar", "usd"]):
                if raw_total_soles == 0.0 and best_amount > 0:
                    raw_total_soles = best_amount
            continue

        if in_footer:
            continue

        item_type, p_code, t_code = _classify_item_code(raw_code)

        if item_type == "partida":
            st_val, _ = _parse_number_or_pct(_get_col(row, "subtotal"), 0.0)
            vp_val, _ = _parse_number_or_pct(_get_col(row, "valor_parcial"), 0.0)
            sub_directo = st_val if st_val > 0 else vp_val

            if p_code not in partidas_dict:
                partidas_dict[p_code] = {
                    "codigo": p_code,
                    "nombre": desc,
                    "subtotal_celda": sub_directo,
                    "tareas": [],
                }
                partidas_order.append(p_code)
            else:
                if desc and not partidas_dict[p_code]["nombre"]:
                    partidas_dict[p_code]["nombre"] = desc
                if sub_directo > 0:
                    partidas_dict[p_code]["subtotal_celda"] = sub_directo

        elif item_type == "tarea":
            if p_code not in partidas_dict:
                partidas_dict[p_code] = {
                    "codigo": p_code,
                    "nombre": "",
                    "subtotal_celda": 0.0,
                    "tareas": [],
                }
                partidas_order.append(p_code)

            met_val, _ = _parse_number_or_pct(_get_col(row, "metrado"), 0.0)
            vu_val, _ = _parse_number_or_pct(_get_col(row, "valor_unitario"), 0.0)
            vp_val, _ = _parse_number_or_pct(_get_col(row, "valor_parcial"), 0.0)
            st_val, _ = _parse_number_or_pct(_get_col(row, "subtotal"), 0.0)

            has_content = bool(desc) or vu_val > 0 or vp_val > 0 or st_val > 0
            if not has_content:
                continue

            if met_val <= 0:
                met_val = 1.0

            if vp_val > 0:
                parcial_calc = vp_val
            elif vu_val > 0:
                parcial_calc = round(met_val * vu_val, 2)
            elif st_val > 0:
                parcial_calc = st_val
            else:
                parcial_calc = 0.0

            if vu_val <= 0 and parcial_calc > 0 and met_val > 0:
                vu_val = round(parcial_calc / met_val, 2)

            es_dolares = any(d in moneda.lower() for d in ["dolar", "dólar", "usd", "$"])
            factor_moneda = tc if es_dolares else 1.0
            presupuesto_soles = round(parcial_calc * factor_moneda, 2)
            vu_soles = round(vu_val * factor_moneda, 2)

            partidas_dict[p_code]["tareas"].append({
                "codigo": t_code,
                "descripcion": desc if desc else f"Tarea {t_code}",
                "moneda": moneda,
                "unidad": unidad,
                "metrado": met_val,
                "valor_unitario": vu_val,
                "valor_unitario_soles": vu_soles,
                "valor_parcial": parcial_calc,
                "presupuesto_soles": presupuesto_soles,
            })

    partidas_final = []
    suma_partidas = 0.0

    for p_code in partidas_order:
        p_info = partidas_dict[p_code]
        suma_tareas = round(sum(t["presupuesto_soles"] for t in p_info["tareas"]), 2)
        monto_pactado = suma_tareas if suma_tareas > 0 else round(p_info["subtotal_celda"], 2)

        nombre_base = p_info["nombre"].strip()
        if not nombre_base:
            nombre_base = f"Partida {p_code}"

        p_num_fmt = f"{int(p_code):02d}" if p_code.isdigit() else p_code
        if re.match(r"^\d+[\.\-\s]", nombre_base):
            nombre_completo = nombre_base
        else:
            nombre_completo = f"{p_num_fmt}. {nombre_base}"

        partidas_final.append({
            "codigo": p_code,
            "nombre": nombre_base,
            "nombre_completo": nombre_completo,
            "monto_pactado": monto_pactado,
            "mix_pct": 0.0,
            "tareas": p_info["tareas"],
        })
        suma_partidas += monto_pactado

    subtotal_casco = round(suma_partidas if suma_partidas > 0 else raw_subtotal_casco, 2)
    resultado["subtotal_casco"] = subtotal_casco

    for p_item in partidas_final:
        if subtotal_casco > 0:
            p_item["mix_pct"] = round((p_item["monto_pactado"] / subtotal_casco) * 100.0, 2)
    resultado["partidas"] = partidas_final

    # Calcular Gastos Generales (GG)
    if raw_gg_amount > 0:
        gg_monto = round(raw_gg_amount, 2)
        gg_pct = round((raw_gg_factor_or_val * 100.0) if (raw_gg_factor_or_val and raw_gg_is_pct) else ((gg_monto / subtotal_casco * 100.0) if subtotal_casco > 0 else 0.0), 2)
    elif raw_gg_factor_or_val is not None and raw_gg_factor_or_val > 0:
        if raw_gg_is_pct:
            gg_pct = round(raw_gg_factor_or_val * 100.0, 2)
            gg_monto = round(subtotal_casco * raw_gg_factor_or_val, 2)
        else:
            gg_monto = round(raw_gg_factor_or_val, 2)
            gg_pct = round((gg_monto / subtotal_casco * 100.0) if subtotal_casco > 0 else 0.0, 2)
    else:
        gg_pct = 0.0
        gg_monto = 0.0

    resultado["gg_pct"] = gg_pct
    resultado["gg_monto"] = gg_monto

    # Calcular Gestión y Supervisión de Obras (Utilidades)
    if raw_util_amount > 0:
        util_monto = round(raw_util_amount, 2)
        util_pct = round((raw_util_factor_or_val * 100.0) if (raw_util_factor_or_val and raw_util_is_pct) else ((util_monto / subtotal_casco * 100.0) if subtotal_casco > 0 else 0.0), 2)
    elif raw_util_factor_or_val is not None and raw_util_factor_or_val > 0:
        if raw_util_is_pct:
            util_pct = round(raw_util_factor_or_val * 100.0, 2)
            util_monto = round(subtotal_casco * raw_util_factor_or_val, 2)
        else:
            util_monto = round(raw_util_factor_or_val, 2)
            util_pct = round((util_monto / subtotal_casco * 100.0) if subtotal_casco > 0 else 0.0, 2)
    else:
        util_pct = 0.0
        util_monto = 0.0

    resultado["utilidades_pct"] = util_pct
    resultado["utilidades_monto"] = util_monto

    # Calcular IGV
    base_imponible = subtotal_casco + gg_monto + util_monto
    if raw_igv_amount > 0:
        igv_monto = round(raw_igv_amount, 2)
        igv_pct = round((raw_igv_factor_or_val * 100.0) if (raw_igv_factor_or_val and raw_igv_is_pct) else ((igv_monto / base_imponible * 100.0) if base_imponible > 0 else 0.0), 2)
    elif raw_igv_factor_or_val is not None and raw_igv_factor_or_val > 0:
        if raw_igv_is_pct:
            igv_pct = round(raw_igv_factor_or_val * 100.0, 2)
            igv_monto = round(base_imponible * raw_igv_factor_or_val, 2)
        else:
            igv_monto = round(raw_igv_factor_or_val, 2)
            igv_pct = round((igv_monto / base_imponible * 100.0) if base_imponible > 0 else 0.0, 2)
    else:
        igv_pct = 0.0
        igv_monto = 0.0

    resultado["igv_pct"] = igv_pct
    resultado["igv_monto"] = igv_monto

    total_calc = round(subtotal_casco + gg_monto + util_monto + igv_monto, 2)
    presupuesto_total = total_calc if total_calc > 0 else round(raw_total_soles, 2)
    resultado["presupuesto_total"] = presupuesto_total
    resultado["presupuesto_dolares"] = round(presupuesto_total / tc, 2) if tc > 0 else 0.0

    return resultado


# ==========================================
# 3. APLICACIÓN / IMPORTACIÓN AL PROYECTO EN COTA APP
# ==========================================

def aplicar_cotizacion_a_proyecto(
    proy_name: str,
    parsed_data: dict,
    modo: str = "reemplazar",
    actualizar_ficha: bool = True,
    nombres_partidas_override: dict = None,
    incluir_partidas_vacias: bool = False,
) -> dict:
    """
    Importa los datos leídos por `parsear_cotizacion_venti` en `st.session_state` para el proyecto `proy_name`.
    """
    if "proyectos" not in st.session_state:
        st.session_state.proyectos = pd.DataFrame(columns=COLS_PROY)
    if "p_info" not in st.session_state:
        st.session_state.p_info = pd.DataFrame(columns=COLS_P_INFO)
    if "tasks" not in st.session_state:
        st.session_state.tasks = pd.DataFrame(columns=COLS_TASKS)
    if "partidas" not in st.session_state:
        st.session_state.partidas = pd.DataFrame(columns=["Proyecto", "Nombre_Partida"])

    for col in COLS_TASKS:
        if col not in st.session_state.tasks.columns:
            st.session_state.tasks[col] = ""

    for col in COLS_P_INFO:
        if col not in st.session_state.p_info.columns:
            st.session_state.p_info[col] = ""

    mask_proy = st.session_state.proyectos["Nombre"] == proy_name
    if actualizar_ficha and mask_proy.any():
        idx_p = st.session_state.proyectos[mask_proy].index[0]
        if parsed_data.get("presupuesto_total", 0.0) > 0:
            st.session_state.proyectos.at[idx_p, "Presupuesto"] = float(parsed_data["presupuesto_total"])
        if parsed_data.get("utilidades_monto", 0.0) >= 0:
            st.session_state.proyectos.at[idx_p, "Utilidades"] = float(parsed_data["utilidades_monto"])
        if parsed_data.get("gg_monto", 0.0) >= 0:
            st.session_state.proyectos.at[idx_p, "GG_Presupuesto"] = float(parsed_data["gg_monto"])
        cli_parsed = safe_str(parsed_data.get("cliente", ""))
        if cli_parsed and not safe_str(st.session_state.proyectos.at[idx_p, "Cliente"]):
            st.session_state.proyectos.at[idx_p, "Cliente"] = cli_parsed

    if modo == "reemplazar":
        st.session_state.partidas = st.session_state.partidas[st.session_state.partidas["Proyecto"] != proy_name].reset_index(drop=True)
        st.session_state.p_info = st.session_state.p_info[st.session_state.p_info["Proyecto"] != proy_name].reset_index(drop=True)
        st.session_state.tasks = st.session_state.tasks[st.session_state.tasks["Proyecto"] != proy_name].reset_index(drop=True)

    nuevas_partidas_rows = []
    nuevas_pinfo_rows = []
    nuevas_tasks_rows = []

    partidas_importadas = 0
    tareas_importadas = 0

    for p in parsed_data.get("partidas", []):
        p_code = p["codigo"]
        tiene_contenido = bool(p.get("tareas")) or p.get("monto_pactado", 0.0) > 0 or bool(p.get("nombre", "").strip())
        if not incluir_partidas_vacias and not tiene_contenido:
            continue

        p_nom_final = (
            nombres_partidas_override.get(p_code, p["nombre_completo"]).strip()
            if nombres_partidas_override and p_code in nombres_partidas_override
            else p["nombre_completo"]
        )
        monto_pactado = float(p.get("monto_pactado", 0.0))

        mask_pi_exist = (st.session_state.p_info["Proyecto"] == proy_name) & (st.session_state.p_info["Nombre_Partida"] == p_nom_final)
        if mask_pi_exist.any():
            st.session_state.p_info.loc[mask_pi_exist, "Monto_Pactado"] = monto_pactado
        else:
            nuevas_pinfo_rows.append({
                "Proyecto": proy_name,
                "Nombre_Partida": p_nom_final,
                "Monto_Pactado": monto_pactado,
                "Nivel_Actual": "",
                "Contratista": "",
                "Inicio": "",
                "Fin": "",
                "Estado": "🟡 Planificado",
                "Etapa": "Construcción",
                "Nivel_Inicio": "",
                "Nivel_Fin": "",
            })

        mask_pa_exist = (st.session_state.partidas["Proyecto"] == proy_name) & (st.session_state.partidas["Nombre_Partida"] == p_nom_final)
        if not mask_pa_exist.any():
            nuevas_partidas_rows.append({
                "Proyecto": proy_name,
                "Nombre_Partida": p_nom_final,
            })

        partidas_importadas += 1

        for idx_t, t in enumerate(p.get("tareas", []), start=1):
            t_cod = safe_str(t.get("codigo", ""))
            t_desc = safe_str(t.get("descripcion", ""))
            if t_cod and not t_desc.startswith(t_cod):
                nombre_tarea = f"{t_cod} {t_desc}".strip()
            else:
                nombre_tarea = t_desc or f"Tarea {t_cod}"

            moneda_t = safe_str(t.get("moneda", "Soles"))
            unidad_t = safe_str(t.get("unidad", "glb")) or "glb"
            metrado_t = float(safe_float(t.get("metrado", 1.0), 1.0))
            vu_soles_t = float(safe_float(t.get("valor_unitario_soles", t.get("valor_unitario", 0.0)), 0.0))
            ppto_soles_t = float(safe_float(t.get("presupuesto_soles", 0.0), 0.0))

            notas_t = f"Ppto: S/ {ppto_soles_t:,.2f} ({metrado_t:g} {unidad_t} x S/ {vu_soles_t:,.2f})"
            if any(d in moneda_t.lower() for d in ["dolar", "dólar", "usd", "$"]):
                notas_t += f" [Cotizado en USD @ TC {parsed_data.get('tc', 3.42):.2f}]"

            nuevas_tasks_rows.append({
                "Proyecto": proy_name,
                "Partida": p_nom_final,
                "Orden": idx_t,
                "Tarea": nombre_tarea,
                "Especialidad": "Ninguna",
                "Contratista": "",
                "Estado": "🟡 Planificado",
                "Inicio": parsed_data.get("fecha") or datetime.date.today().strftime("%Y-%m-%d"),
                "Fin": "",
                "Causa_Cumplimiento": "",
                "Culpa_Contratista": False,
                "Permitir_Cruce": False,
                "Dependencia": "",
                "Notas": notas_t,
                "Unidad": unidad_t,
                "Metrado": metrado_t,
                "Valor_Unitario": vu_soles_t,
                "Presupuesto": ppto_soles_t,
            })
            tareas_importadas += 1

    if nuevas_partidas_rows:
        st.session_state.partidas = pd.concat(
            [st.session_state.partidas, pd.DataFrame(nuevas_partidas_rows)],
            ignore_index=True,
        ).drop_duplicates().reset_index(drop=True)

    if nuevas_pinfo_rows:
        df_new_pi = pd.DataFrame(nuevas_pinfo_rows)
        st.session_state.p_info = pd.concat(
            [st.session_state.p_info, df_new_pi[COLS_P_INFO]],
            ignore_index=True,
        )

    if nuevas_tasks_rows:
        df_new_t = pd.DataFrame(nuevas_tasks_rows)
        st.session_state.tasks = pd.concat(
            [st.session_state.tasks, df_new_t[COLS_TASKS]],
            ignore_index=True,
        )

    clear_base_dfs()

    return {
        "partidas_importadas": partidas_importadas,
        "tareas_importadas": tareas_importadas,
        "presupuesto_total": float(parsed_data.get("presupuesto_total", 0.0)),
        "utilidades_monto": float(parsed_data.get("utilidades_monto", 0.0)),
        "gg_monto": float(parsed_data.get("gg_monto", 0.0)),
    }
