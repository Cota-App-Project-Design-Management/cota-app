"""
Generador de reportes ejecutivos y actas de reunión en formato PDF.
Diseñado con tipografía técnica y estética limpia para estudios de arquitectura y diseño.
"""

import os
import pandas as pd
from fpdf import FPDF
from fpdf.fonts import FontFace


def safe_pdf_str(text):
    """Sanitiza strings para compatibilidad con fuentes estándar de FPDF (Latin-1)."""
    if text is None or pd.isna(text):
        return ""
    s = str(text)
    # Reemplazos amigables
    s = s.replace("—", "-").replace("–", "-").replace("“", '"').replace("”", '"').replace("’", "'").replace("°", "o")
    return s.encode('latin-1', 'replace').decode('latin-1')


def generar_pdf_minuta(r_ses, invitados_df, acuerdos_df, logo_path="Logo2.png", studio_title="COTA APP", brand_color=None):
    """
    Genera un archivo PDF con la minuta formal de reunión / acta de coordinación.
    Retorna bytes del documento PDF.
    """
    import io
    from cota.utils import obtener_marca_estudio, hex_a_rgb, preparar_logo_png_bytes

    marca = obtener_marca_estudio()
    brand_rgb = hex_a_rgb(brand_color) if brand_color else marca["brand_rgb"]
    active_studio_title = (
        marca["studio_name"]
        if (not studio_title or studio_title == "COTA APP") and marca.get("studio_name")
        else (studio_title or "COTA APP")
    )
    logo_bytes = marca.get("logo_png_bytes")
    if logo_path and logo_path != "Logo2.png" and os.path.exists(str(logo_path)):
        custom_bytes, _ = preparar_logo_png_bytes(logo_path, max_height=85)
        if custom_bytes:
            logo_bytes = custom_bytes
    class MinutaPDF(FPDF):
        def header(self):
            # Barra superior estética Warm Atelier (Carbón Cálido + acento Terracota)
            self.set_fill_color(38, 35, 32)
            self.rect(0, 0, 210, 26, 'F')
            self.set_fill_color(*brand_rgb)
            self.rect(0, 25, 210, 1.5, 'F')

            # Título del estudio y documento
            self.set_text_color(247, 244, 239)
            self.set_font('Helvetica', 'B', 13)
            self.set_xy(12, 8)
            self.cell(140, 6, safe_pdf_str(self.pdf_title).upper(), border=0, align='L')

            self.set_text_color(*brand_rgb)
            self.set_font('Helvetica', 'B', 8)
            self.set_xy(12, 16)
            self.cell(140, 5, f"{safe_pdf_str(active_studio_title)} // ACTA DE COORDINACION", border=0, align='L')

            # Logotipo del Estudio si existe
            if logo_bytes:
                try:
                    self.image(io.BytesIO(logo_bytes), x=170, y=5, h=15)
                except Exception:
                    pass
            elif logo_path and os.path.exists(logo_path):
                try:
                    self.image(logo_path, x=175, y=5, w=22)
                except Exception:
                    pass

            self.ln(18)

        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(110, 102, 94)
            self.cell(0, 10, f'Pagina {self.page_no()}/{{nb}}  -  Generado por {safe_pdf_str(active_studio_title)}', align='C')

    pdf = MinutaPDF()
    pdf.pdf_title = r_ses.get('Nombre_Sesion', r_ses.get('Titulo', 'Acta de Reunión'))
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_margins(15, 30, 15)
    pdf.set_y(32)

    # 1. Datos Generales
    pdf.set_fill_color(38, 35, 32)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(0, 7, '  1. DATOS DEL PROYECTO Y REUNION', fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_fill_color(255, 255, 255)
    pdf.set_text_color(38, 35, 32)
    pdf.ln(2)

    info_fields = [
        ('Proyecto:', r_ses.get('Proyecto', '')),
        ('Tipo de Reunión:', r_ses.get('Tipo_Reunion', r_ses.get('Tipo', 'Coordinación'))),
        ('Etapa / Fase:', r_ses.get('Etapa', 'Diseño')),
        ('Fecha Programada:', r_ses.get('Fecha_Prog', r_ses.get('Fecha', ''))),
        ('Fecha Realizada:', r_ses.get('Fecha_Real', r_ses.get('Fecha', ''))),
        ('Hora:', r_ses.get('Hora', '')),
        ('Organizador / Convocante:', r_ses.get('Organizador', '')),
        ('Líder de Proyecto:', r_ses.get('Lider', ''))
    ]

    for label, val in info_fields:
        pdf.set_font('Helvetica', 'B', 8)
        pdf.cell(50, 5.5, safe_pdf_str(label), border='B')
        pdf.set_font('Helvetica', '', 8)
        pdf.cell(0, 5.5, safe_pdf_str(val), border='B', new_x="LMARGIN", new_y="NEXT")

    pdf.ln(5)

    # 2. Asistentes e Invitados
    pdf.set_fill_color(38, 35, 32)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(0, 7, '  2. ASISTENCIA Y PARTICIPANTES', fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_fill_color(255, 255, 255)
    pdf.set_text_color(38, 35, 32)
    pdf.ln(2)

    hs = FontFace(emphasis="B", fill_color=(239, 236, 230), color=(38, 35, 32))
    rs = FontFace(emphasis="", fill_color=(255, 255, 255), color=(38, 35, 32))

    if invitados_df is None or invitados_df.empty:
        pdf.set_text_color(110, 102, 94)
        pdf.set_font('Helvetica', 'I', 8)
        pdf.cell(0, 6, 'No hay participantes registrados.', border=1, new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(38, 35, 32)
        with pdf.table(
            col_widths=(65, 45, 45, 25),
            line_height=5.5,
            headings_style=hs,
            cell_fill_color=(255, 255, 255),
            cell_fill_mode="ALL",
            borders_layout="HORIZONTAL_LINES",
        ) as table:
            headers = table.row()
            pdf.set_font('Helvetica', 'B', 8)
            headers.cell(safe_pdf_str("Nombre"))
            headers.cell(safe_pdf_str("Empresa / Especialidad"))
            headers.cell(safe_pdf_str("Cargo / Rol"))
            headers.cell(safe_pdf_str("Asistencia"))

            pdf.set_font('Helvetica', '', 8)
            for _, row in invitados_df.iterrows():
                r = table.row(style=rs)
                r.cell(safe_pdf_str(row.get('Nombre', '')))
                r.cell(safe_pdf_str(row.get('Empresa', '')))
                r.cell(safe_pdf_str(row.get('Cargo', row.get('Rol', ''))))
                r.cell(safe_pdf_str(row.get('Asistencia', 'Asistió')))

    pdf.ln(5)

    # 3. Acuerdos y Compromisos
    pdf.set_fill_color(38, 35, 32)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(0, 7, '  3. ACUERDOS, COMPROMISOS Y PROXIMOS PASOS', fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_fill_color(255, 255, 255)
    pdf.set_text_color(38, 35, 32)
    pdf.ln(2)

    if acuerdos_df is None or acuerdos_df.empty:
        pdf.set_text_color(110, 102, 94)
        pdf.set_font('Helvetica', 'I', 8)
        pdf.cell(0, 6, 'No hay acuerdos registrados.', border=1, new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(38, 35, 32)
        with pdf.table(
            col_widths=(65, 45, 70),
            line_height=5.5,
            headings_style=hs,
            cell_fill_color=(255, 255, 255),
            cell_fill_mode="ALL",
            borders_layout="HORIZONTAL_LINES",
        ) as table:
            headers = table.row()
            pdf.set_font('Helvetica', 'B', 8)
            headers.cell(safe_pdf_str("Tema / Entregable"))
            headers.cell(safe_pdf_str("Responsable"))
            headers.cell(safe_pdf_str("Acuerdo / Accion Acordada"))

            pdf.set_font('Helvetica', '', 8)
            for _, row in acuerdos_df.iterrows():
                r = table.row(style=rs)
                r.cell(safe_pdf_str(row.get('Descripcion', row.get('Acuerdo', ''))))
                r.cell(safe_pdf_str(row.get('Responsable', '')))
                r.cell(safe_pdf_str(row.get('Acuerdo', '')))

    return bytes(pdf.output())

