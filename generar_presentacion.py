"""
Genera y actualiza la presentación de COTA APP v2.0 en formato PowerPoint (.pptx) y PDF (.pdf)
con lenguaje ejecutivo, claro y accesible para alguien sin experiencia en arquitectura:
- En vez de 'KPIs' -> 'Métricas clave / Indicadores'
- En vez de 'FF&E' -> 'Materiales, Mobiliario y Acabados'
- En vez de 'Diagrama Gantt' -> 'Cronograma visual'
- En vez de 'Partidas / Valorizaciones' -> 'Rubros de obra y Pagos a contratistas'
- En vez de 'Punch List' -> 'Lista de observaciones finales antes de la entrega'
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from fpdf import FPDF


# Paleta Warm Architectural Atelier
C_BG = RGBColor(247, 244, 239)        # #F7F4EF Blanco Hueso
C_CARD = RGBColor(255, 255, 255)      # #FFFFFF Blanco
C_STONE = RGBColor(239, 236, 230)     # #EFECE6 Piedra Travertino
C_BORDER = RGBColor(223, 217, 206)    # #DFD9CE Borde cálido
C_CHARCOAL = RGBColor(38, 35, 32)     # #262320 Carbón cálido
C_MUTED = RGBColor(110, 102, 94)      # #6E665E Texto secundario
C_CLAY = RGBColor(200, 90, 50)        # #C85A32 Rojo Arcilla / Terracota
C_SAGE = RGBColor(74, 124, 89)        # #4A7C59 Verde Salvia
C_AMBER = RGBColor(217, 138, 43)      # #D98A2B Ámbar


def set_slide_bg(slide, color):
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_header(slide, tag_text, title_text, badge_text="COTA // STUDIO v2.0"):
    tb_tag = slide.shapes.add_textbox(Inches(0.6), Inches(0.35), Inches(8.5), Inches(0.3))
    tf_tag = tb_tag.text_frame
    tf_tag.word_wrap = True
    p_tag = tf_tag.paragraphs[0]
    p_tag.text = tag_text.upper()
    p_tag.font.size = Pt(10)
    p_tag.font.bold = True
    p_tag.font.color.rgb = C_CLAY
    p_tag.font.name = "Consolas"

    tb_tit = slide.shapes.add_textbox(Inches(0.6), Inches(0.62), Inches(10.0), Inches(0.55))
    tf_tit = tb_tit.text_frame
    tf_tit.word_wrap = True
    p_tit = tf_tit.paragraphs[0]
    p_tit.text = title_text
    p_tit.font.size = Pt(20)
    p_tit.font.bold = True
    p_tit.font.color.rgb = C_CHARCOAL
    p_tit.font.name = "Arial"

    badge = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(10.7), Inches(0.42), Inches(2.0), Inches(0.38)
    )
    badge.fill.solid()
    badge.fill.fore_color.rgb = C_STONE
    badge.line.color.rgb = C_CLAY
    badge.line.width = Pt(1)
    tf_b = badge.text_frame
    tf_b.word_wrap = True
    p_b = tf_b.paragraphs[0]
    p_b.text = badge_text
    p_b.alignment = PP_ALIGN.CENTER
    p_b.font.size = Pt(9.5)
    p_b.font.bold = True
    p_b.font.color.rgb = C_CLAY
    p_b.font.name = "Consolas"

    line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0.6), Inches(1.22), Inches(12.13), Pt(1.5)
    )
    line.fill.solid()
    line.fill.fore_color.rgb = C_BORDER
    line.line.fill.background()


def add_card(slide, left, top, width, height, title, bullets, accent_color=C_CLAY):
    card = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height
    )
    card.fill.solid()
    card.fill.fore_color.rgb = C_CARD
    card.line.color.rgb = C_BORDER
    card.line.width = Pt(1)

    bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, left, top, width, Pt(4)
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = accent_color
    bar.line.fill.background()

    tb = slide.shapes.add_textbox(left + Inches(0.2), top + Inches(0.18), width - Inches(0.4), height - Inches(0.3))
    tf = tb.text_frame
    tf.word_wrap = True

    p0 = tf.paragraphs[0]
    p0.text = title
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = C_CHARCOAL
    p0.font.name = "Arial"
    p0.space_after = Pt(8)

    for b in bullets:
        p = tf.add_paragraph()
        p.text = f"▪  {b}"
        p.font.size = Pt(10.5)
        p.font.color.rgb = C_MUTED
        p.font.name = "Arial"
        p.space_after = Pt(6)


def add_screenshot_slot(slide, left, top, width, height, ss_num, ss_title, instructions):
    slot = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height
    )
    slot.fill.solid()
    slot.fill.fore_color.rgb = C_STONE
    slot.line.color.rgb = C_CLAY
    slot.line.width = Pt(1.75)

    tb = slide.shapes.add_textbox(left + Inches(0.25), top + Inches(0.25), width - Inches(0.5), height - Inches(0.5))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE

    p_icon = tf.paragraphs[0]
    p_icon.text = f"[ ESPACIO PARA CAPTURA DE PANTALLA #{ss_num} ]"
    p_icon.alignment = PP_ALIGN.CENTER
    p_icon.font.size = Pt(11)
    p_icon.font.bold = True
    p_icon.font.color.rgb = C_CLAY
    p_icon.font.name = "Consolas"
    p_icon.space_after = Pt(6)

    p_tit = tf.add_paragraph()
    p_tit.text = ss_title
    p_tit.alignment = PP_ALIGN.CENTER
    p_tit.font.size = Pt(14)
    p_tit.font.bold = True
    p_tit.font.color.rgb = C_CHARCOAL
    p_tit.font.name = "Arial"
    p_tit.space_after = Pt(10)

    p_sub = tf.add_paragraph()
    p_sub.text = "¿Qué pantalla capturar en la app y pegar aquí?"
    p_sub.alignment = PP_ALIGN.CENTER
    p_sub.font.size = Pt(10.5)
    p_sub.font.bold = True
    p_sub.font.color.rgb = C_CHARCOAL
    p_sub.font.name = "Arial"
    p_sub.space_after = Pt(4)

    for step in instructions:
        ps = tf.add_paragraph()
        ps.text = f"• {step}"
        ps.alignment = PP_ALIGN.CENTER
        ps.font.size = Pt(10)
        ps.font.color.rgb = C_MUTED
        ps.font.name = "Arial"
        ps.space_after = Pt(3)

    p_hint = tf.add_paragraph()
    p_hint.text = "(En Google Slides / PowerPoint: pega tu captura con Ctrl+V encima de este recuadro)"
    p_hint.alignment = PP_ALIGN.CENTER
    p_hint.font.size = Pt(9)
    p_hint.font.italic = True
    p_hint.font.color.rgb = C_CLAY
    p_hint.font.name = "Arial"


def build_pptx(output_path: str):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # ---------------- SLIDE 1: VISIÓN Y OPORTUNIDAD DE NEGOCIO ----------------
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s1, C_BG)
    add_header(s1, "01 // Visión y Oportunidad de Negocio", "COTA APP: Plataforma de Gestión para Proyectos de Diseño y Remodelación", "VERSIÓN v2.0")

    add_card(
        s1, Inches(0.6), Inches(1.45), Inches(3.85), Inches(3.7),
        "1. El Problema del Sector",
        [
            "La mayoría de estudios de diseño y remodelación manejan su operación dispersa entre hojas de Excel sueltas, WhatsApp y carpetas en la nube.",
            "Descontrol en compras de materiales y mobiliario: los presupuestos por habitación se desfasan sin detectarlo a tiempo.",
            "Falta de claridad financiera: no se conoce la ganancia real ni el saldo pendiente con cada proveedor hasta terminar la obra.",
            "Las apps genéricas de tareas (Notion, Trello, Monday) no sirven para controlar presupuestos de obra, compras por ambiente ni actas formales."
        ],
        accent_color=C_AMBER
    )

    add_card(
        s1, Inches(4.74), Inches(1.45), Inches(3.85), Inches(3.7),
        "2. La Solución: COTA App v2.0",
        [
            "Sistema todo-en-uno diseñado para controlar un proyecto completo desde la idea inicial hasta la entrega final al cliente.",
            "Conecta las 8 etapas de diseño, el catálogo de materiales y muebles por habitación, los planos, los pagos a trabajadores, los cobros y las actas en PDF.",
            "Diseño visual limpio y ejecutivo que eleva la imagen profesional de la empresa frente a los clientes.",
            "Guardado en tiempo real en la nube (Google Sheets) con respaldo directo en archivos Excel (.xlsx) en Google Drive."
        ],
        accent_color=C_CLAY
    )

    add_card(
        s1, Inches(8.88), Inches(1.45), Inches(3.85), Inches(3.7),
        "3. Doble Oportunidad para Socios",
        [
            "USO INTERNO INMEDIATO: Ordenar el 100% de nuestros proyectos activos, protegiendo el margen de ganancia y ahorrando horas administrativas.",
            "MODELO DE SUSCRIPCIÓN (SaaS): El sistema está listo para poder alquilarlo mensualmente a otros estudios de diseño, arquitectura y remodelación.",
            "Producto 100% operativo hoy: 6 vistas generales de la empresa + 8 módulos detallados por cada proyecto."
        ],
        accent_color=C_SAGE
    )

    flow_steps = [
        ("01. CRONOGRAMA", "Las 8 etapas de avance"),
        ("02. MATERIALES", "Compras por habitación"),
        ("03. PLANOS Y 3D", "Control de versiones"),
        ("04. OBRA Y EQUIPO", "Contratistas 1 a 5 ★"),
        ("05. FINANZAS", "Ingresos vs. Gastos"),
        ("06. ACTAS Y ENTREGA", "PDF + Revisión final"),
    ]
    for i, (ft, fs) in enumerate(flow_steps):
        bx = Inches(0.6 + i * 2.05)
        b_shape = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, bx, Inches(5.45), Inches(1.92), Inches(1.45))
        b_shape.fill.solid()
        b_shape.fill.fore_color.rgb = C_CARD
        b_shape.line.color.rgb = C_CLAY if i % 2 == 0 else C_SAGE
        b_shape.line.width = Pt(1.2)
        tf_f = b_shape.text_frame
        tf_f.word_wrap = True
        tf_f.vertical_anchor = MSO_ANCHOR.MIDDLE
        pf1 = tf_f.paragraphs[0]
        pf1.text = ft
        pf1.alignment = PP_ALIGN.CENTER
        pf1.font.size = Pt(10.5)
        pf1.font.bold = True
        pf1.font.color.rgb = C_CHARCOAL
        pf2 = tf_f.add_paragraph()
        pf2.text = fs
        pf2.alignment = PP_ALIGN.CENTER
        pf2.font.size = Pt(9.5)
        pf2.font.color.rgb = C_MUTED

    # ---------------- SLIDE 2: PORTAFOLIO Y MÉTRICAS ----------------
    s2 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s2, C_BG)
    add_header(s2, "02 // Vista General de la Empresa", "Portafolio de Proyectos y 5 Métricas Clave en Tiempo Real", "Pestaña: PROYECTOS & DISEÑO")

    add_card(
        s2, Inches(0.6), Inches(1.45), Inches(4.7), Inches(5.55),
        "Resumen Ejecutivo desde la Primera Pantalla",
        [
            "5 Métricas Clave en Tiempo Real: Proyectos Activos, Presupuesto Total Contratado (vs. monto ejecutado), Porcentaje de Avance de Diseño (%), Materiales por Aprobar (S/) y Pagos por Cobrar al Cliente (S/).",
            "Filtro Inteligente por Proyecto: Permite ver los números globales de toda la empresa o seleccionar un solo proyecto para ver al instante sus cobros y su lista de materiales.",
            "Vista Unificada + Carpetas: Pestaña 'TODOS LOS PROYECTOS (5)' más carpetas por unidad de negocio (Comercial & Hospitality, Residencial VIP, Residencial).",
            "Tarjetas Desplegables por Estado: Proyectos agrupados en En Proceso, Planificación y Completado con barra de progreso y acceso directo a su expediente."
        ],
        accent_color=C_CLAY
    )

    add_screenshot_slot(
        s2, Inches(5.55), Inches(1.45), Inches(7.18), Inches(5.55),
        1, "Portafolio Principal y las 5 Métricas de la Empresa",
        [
            "Abre la pestaña principal 'PROYECTOS & DISEÑO'.",
            "Asegúrate de estar en '🗂️ TODOS LOS PROYECTOS (5)'.",
            "Haz clic en '🏛️ CASA LA PLANICIE' para desplegar su ficha resumen.",
            "Toma la captura abarcando las 5 métricas superiores y la lista de proyectos."
        ]
    )

    # ---------------- SLIDE 3: FINANZAS Y CONTRATISTAS ----------------
    s3 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s3, C_BG)
    add_header(s3, "03 // Rentabilidad Global y Proveedores", "Finanzas Consolidadas de la Empresa y Directorio de Contratistas", "Pestañas: FINANZAS + CONTRATISTAS")

    add_card(
        s3, Inches(0.6), Inches(1.45), Inches(5.9), Inches(2.2),
        "Finanzas Consolidadas de la Empresa",
        [
            "Calcula la Liquidez Neta real: Total Cobrado a Clientes − (Pagos a Contratistas + Compra de Materiales + Gastos Menores).",
            "Gráfico comparativo por proyecto (Presupuesto Contratado vs. Cobrado vs. Gastado) y descarga directa en Excel/CSV."
        ],
        accent_color=C_SAGE
    )
    add_screenshot_slot(
        s3, Inches(0.6), Inches(3.8), Inches(5.9), Inches(3.2),
        2, "Finanzas de la Empresa y Gráfico Comparativo",
        [
            "Entra a la pestaña 'FINANZAS DEL ESTUDIO'.",
            "Captura las 5 métricas financieras, el gráfico de barras de los 5 proyectos y la tabla inferior."
        ]
    )

    add_card(
        s3, Inches(6.83), Inches(1.45), Inches(5.9), Inches(2.2),
        "Directorio Inteligente de Contratistas (1–5 ★)",
        [
            "Cruza las tareas activas para mostrar quién está '🔵 En Obra Hoy' o '🟢 Disponible' y su carga de trabajo para los próximos 7 días.",
            "Calificación en estrellas (⭐) e historial de desempeño con Puntos a Favor [+] e Incidencias [-]."
        ],
        accent_color=C_CLAY
    )
    add_screenshot_slot(
        s3, Inches(6.83), Inches(3.8), Inches(5.9), Inches(3.2),
        3, "Directorio de Contratistas y Calificación por Estrellas",
        [
            "Entra a la pestaña 'BASE CONTRATISTAS'.",
            "Captura el directorio con estrellas ⭐ y la sección inferior de historial de desempeño."
        ]
    )

    # ---------------- SLIDE 4: CONTROL OPERATIVO Y CALENDARIO ----------------
    s4 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s4, C_BG)
    add_header(s4, "04 // Coordinación Semanal entre Socios", "Control Operativo Diario y Calendario Mensual de Actividades", "Pestañas: OPERATIVO + CALENDARIO")

    add_card(
        s4, Inches(0.6), Inches(1.45), Inches(4.7), Inches(5.55),
        "Operación Diaria del Equipo sin Fricciones",
        [
            "Columna 1 — Pendientes y Logística Diaria: Tareas rápidas asignadas por socio (Compras de materiales, Pagos, Proveedores, Clientes) con botón '✓ LISTO' al completarlas.",
            "Columna 2 — En Ejecución (Hoy): Qué trabajos de obra y qué contratistas están activos hoy mismo en cada proyecto.",
            "Columna 3 — Próximos Inicios (7 Días): Alertas preventivas de los trabajos que arrancan esta semana para coordinar compras y permisos a tiempo.",
            "Calendario Mensual: Vista mensual completa donde cada actividad se pinta con el color del proyecto correspondiente."
        ],
        accent_color=C_AMBER
    )

    add_screenshot_slot(
        s4, Inches(5.55), Inches(1.45), Inches(7.18), Inches(5.55),
        4, "Tablero de Control Operativo o Calendario Mensual",
        [
            "Entra a la pestaña 'CONTROL OPERATIVO' (vista de 3 columnas de tareas diarias)",
            "o a la pestaña 'CALENDARIO' (agenda mensual coloreada por proyecto).",
            "Toma una captura completa de la vista que prefieras destacar ante tu socio."
        ]
    )

    # ---------------- SLIDE 5: FICHA DE PROYECTO (RESUMEN Y CRONOGRAMA) ----------------
    s5 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s5, C_BG)
    add_header(s5, "05 // Expediente del Proyecto (Módulos 01 y 02)", "Resumen del Proyecto, Requerimientos y Cronograma de las 8 Etapas", "Módulos: 01. RESUMEN + 02. FASES")

    add_card(
        s5, Inches(0.6), Inches(1.45), Inches(4.7), Inches(5.55),
        "8 Módulos Especializados por cada Proyecto",
        [
            "Al abrir un proyecto (ej. 'Casa La Planicie'), se despliega su expediente completo organizado en 8 pestañas.",
            "01. Resumen General: 6 métricas financieras y de avance del proyecto (Presupuesto Total, Cobrado, Pagos Obra, Compra de Materiales, Saldo Caja Chica y % Etapas), datos técnicos y requerimientos del cliente.",
            "02. Etapas de Diseño: Las 8 etapas paso a paso desde '01. Levantamiento Inicial' hasta '08. Cierre y Entrega Final'.",
            "Incluye un Cronograma Visual de barras por fechas y casilla de verificación 'Aprobado por Cliente'."
        ],
        accent_color=C_CLAY
    )

    add_screenshot_slot(
        s5, Inches(5.55), Inches(1.45), Inches(7.18), Inches(5.55),
        5, "Resumen del Proyecto o Cronograma Visual de Etapas",
        [
            "Abre el proyecto 'Casa La Planicie' con el botón 'ABRIR EXPEDIENTE →'.",
            "Toma la captura en '01. RESUMEN' (6 métricas + Ficha Técnica + 8 barras de avance)",
            "o en '02. FASES DE DISEÑO' (mostrando el Cronograma Visual de barras y la tabla inferior)."
        ]
    )

    # ---------------- SLIDE 6: MATERIALES, MOBILIARIO Y PLANOS ----------------
    s6 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s6, C_BG)
    add_header(s6, "06 // Control de Compras y Documentos (Módulos 03 y 04)", "Presupuesto de Materiales y Mobiliario por Ambiente y Control de Planos", "Módulos: 03. MATERIALES + 04. PLANOS")

    add_card(
        s6, Inches(0.6), Inches(1.45), Inches(4.7), Inches(5.55),
        "Presupuesto de Materiales y Muebles por Habitación",
        [
            "03. Materiales, Mobiliario y Acabados (pestaña FF&E): Planilla interactiva filtrable por Ambiente (Sala, Comedor, Cocina, Dormitorio Principal, Terraza) y por Categoría (Muebles, Iluminación, Acabados).",
            "Cálculo automático de Presupuesto Estimado vs. Costo Real de compra, mostrando el ahorro o sobrecosto en cada habitación.",
            "Seguimiento de cada compra: Propuesto → Cotizado → Aprobado por Cliente → En Fabricación → Instalado.",
            "04. Entregables y Planos: Control de versiones de planos y vistas 3D, estado de aprobación y enlaces a la nube."
        ],
        accent_color=C_SAGE
    )

    add_screenshot_slot(
        s6, Inches(5.55), Inches(1.45), Inches(7.18), Inches(5.55),
        6, "Lista de Materiales y Desglose de Costos por Ambiente",
        [
            "Dentro de 'Casa La Planicie', entra a '03. ESPECIFICACIONES FF&E'.",
            "Haz clic en '📊 Ver desglose de presupuesto FF&E por Ambiente'.",
            "Toma la captura mostrando las 4 métricas superiores, el resumen por habitación y el listado de materiales."
        ]
    )

    # ---------------- SLIDE 7: OBRA, COBROS, ACTAS PDF Y ENTREGA ----------------
    s7 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s7, C_BG)
    add_header(s7, "07 // Ejecución de Obra, Finanzas y Cierre (Módulos 05 al 08)", "Control de Obra, Hitos de Cobro, Actas en PDF y Revisión de Entrega", "Módulos: 05, 06, 07 y 08")

    add_card(
        s7, Inches(0.6), Inches(1.45), Inches(5.9), Inches(2.2),
        "05. Ejecución de Obra y 06. Cobros / Caja Chica",
        [
            "Control por rubro de obra (Demolición, Carpintería, Pintura) con indicadores de MONTO PACTADO / PAGADO / SALDO y sugeridor automático de contratistas disponibles.",
            "Cronograma de pagos del cliente y registro rápido de gastos menores (Caja Chica)."
        ],
        accent_color=C_CLAY
    )
    add_screenshot_slot(
        s7, Inches(0.6), Inches(3.8), Inches(5.9), Inches(3.2),
        7, "Rubros de Obra y Control de Pagos a Contratistas",
        [
            "Dentro de 'Casa La Planicie', abre '05. EJECUCIÓN & PARTIDAS'.",
            "Captura los rubros de obra con sus etiquetas PACTADO / PAGADO / SALDO y tareas."
        ]
    )

    add_card(
        s7, Inches(6.83), Inches(1.45), Inches(5.9), Inches(2.2),
        "07. Actas en PDF Automático y 08. Revisión de Entrega",
        [
            "Importa apuntes de reunión o Google Meet para ordenar asistentes y acuerdos, generando un Acta formal en PDF con membrete en un clic.",
            "Módulo 08 (Punch List): Lista de observaciones y retoques finales por habitación antes de entregar la obra."
        ],
        accent_color=C_SAGE
    )
    add_screenshot_slot(
        s7, Inches(6.83), Inches(3.8), Inches(5.9), Inches(3.2),
        8, "Actas de Reunión (Exportar a PDF) o Lista de Entrega",
        [
            "Abre '07. REUNIONES & ACTAS' en 'Casa La Planicie'.",
            "Captura la ficha de la reunión, las tablas de participantes/acuerdos y el botón '📥 EXPORTAR ACTA A PDF'."
        ]
    )

    # ---------------- SLIDE 8: TECNOLOGÍA Y HOJA DE RUTA ----------------
    s8 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s8, C_BG)
    add_header(s8, "08 // Tecnología y Visión Estratégica", "Solidez Técnica Lograda y Hoja de Ruta con el Socio", "LISTO PARA OPERAR")

    add_card(
        s8, Inches(0.6), Inches(1.45), Inches(5.9), Inches(5.55),
        "Lo que ya está resuelto y funcionando hoy (v2.0)",
        [
            "Base de Datos en la Nube + Respaldo en Excel: Conecta en tiempo real con Google Sheets y cuenta con soporte directo para archivos Excel (.xlsx) en Google Drive.",
            "Guardado Inteligente de Cambios: El panel lateral detecta automáticamente qué tablas fueron editadas ('● X cambios sin guardar') y sincroniza solo lo necesario.",
            "Diseño Ejecutivo y Simétrico: Interfaz limpia en tonos cálidos (#F7F4EF y terracota #C85A32), adaptable a cualquier resolución de pantalla.",
            "Configuración Multi-Socio: Los nombres de los directores o socios se configuran libremente desde el panel lateral.",
            "Calidad Verificada: Sistema respaldado por 22 pruebas automáticas que garantizan la exactitud de todos los cálculos financieros."
        ],
        accent_color=C_CLAY
    )

    add_card(
        s8, Inches(6.83), Inches(1.45), Inches(5.9), Inches(5.55),
        "Hoja de Ruta Propuesta con el Socio",
        [
            "FASE 1 — Implementación Interna Inmediata (Mes 1): Gestionar el 100% de nuestros proyectos activos en la app, estandarizando presupuestos de materiales, control de contratistas y actas en PDF.",
            "FASE 2 — Portal de Consulta para el Cliente (Mes 2–3): Habilitar una vista para que el cliente revise el avance de su proyecto en línea, apruebe compras de materiales y consulte su estado de cuenta.",
            "FASE 3 — Escalabilidad como Software por Suscripción (Mes 4+): Comercializar el sistema mediante suscripción mensual para otros estudios de diseño, arquitectura y remodelación."
        ],
        accent_color=C_SAGE
    )

    prs.save(output_path)


def clean_pdf_text(txt: str) -> str:
    replacements = {
        "—": "-", "–": "-", "−": "-", "▪": "-", "•": "-",
        "⭐": "*", "★": "*", "✓": "[OK]", "×": "x", "→": "->",
        "🏛️": "", "🗂️": "", "📊": "", "📥": "", "🔵": "", "🟢": "", "🟡": "", "🔴": "",
        "“": '"', "”": '"', "‘": "'", "’": "'"
    }
    for k, v in replacements.items():
        txt = txt.replace(k, v)
    return txt.encode("latin-1", "replace").decode("latin-1")


class PitchDeckPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="L", unit="mm", format="A4")
        self.set_auto_page_break(auto=False)

    def draw_slide_bg(self):
        self.set_fill_color(247, 244, 239)
        self.rect(0, 0, 297, 210, style="F")

    def draw_header(self, tag: str, title: str, badge: str):
        self.set_xy(14, 10)
        self.set_font("Courier", "B", 9)
        self.set_text_color(200, 90, 50)
        self.cell(200, 5, clean_pdf_text(tag.upper()), ln=1)

        self.set_xy(14, 16)
        self.set_font("Helvetica", "B", 15.5)
        self.set_text_color(38, 35, 32)
        self.cell(220, 8, clean_pdf_text(title), ln=0)

        self.set_fill_color(239, 236, 230)
        self.set_draw_color(200, 90, 50)
        self.rect(236, 12, 47, 9, style="DF")
        self.set_xy(236, 14)
        self.set_font("Courier", "B", 8)
        self.set_text_color(200, 90, 50)
        self.cell(47, 5, clean_pdf_text(badge), align="C")

        self.set_draw_color(223, 217, 206)
        self.line(14, 27, 283, 27)

    def draw_card(self, x, y, w, h, title, bullets, accent=(200, 90, 50)):
        self.set_fill_color(255, 255, 255)
        self.set_draw_color(223, 217, 206)
        self.rect(x, y, w, h, style="DF")

        self.set_fill_color(*accent)
        self.rect(x, y, w, 2, style="F")

        self.set_xy(x + 5, y + 5)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(38, 35, 32)
        self.multi_cell(w - 10, 5.5, clean_pdf_text(title))

        cur_y = self.get_y() + 2
        self.set_font("Helvetica", "", 9.2)
        self.set_text_color(110, 102, 94)
        for b in bullets:
            self.set_xy(x + 5, cur_y)
            self.multi_cell(w - 10, 4.6, clean_pdf_text(f"- {b}"))
            cur_y = self.get_y() + 1.8

    def draw_ss_box(self, x, y, w, h, num, title, steps):
        self.set_fill_color(239, 236, 230)
        self.set_draw_color(200, 90, 50)
        self.rect(x, y, w, h, style="DF")

        self.set_xy(x + 6, y + 10)
        self.set_font("Courier", "B", 10)
        self.set_text_color(200, 90, 50)
        self.cell(w - 12, 6, clean_pdf_text(f"[ ESPACIO PARA CAPTURA #{num} ]"), align="C", ln=1)

        self.set_x(x + 6)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(38, 35, 32)
        self.cell(w - 12, 7, clean_pdf_text(title), align="C", ln=1)

        self.ln(2)
        self.set_x(x + 6)
        self.set_font("Helvetica", "B", 9.5)
        self.cell(w - 12, 5, clean_pdf_text("¿Qué pantalla capturar en la app y pegar aquí?"), align="C", ln=1)

        self.set_font("Helvetica", "", 9)
        self.set_text_color(110, 102, 94)
        for s in steps:
            self.set_x(x + 8)
            self.multi_cell(w - 16, 4.8, clean_pdf_text(f"* {s}"), align="C")


def build_pdf(output_path: str):
    pdf = PitchDeckPDF()

    # Slide 1
    pdf.add_page()
    pdf.draw_slide_bg()
    pdf.draw_header("01 // Visión y Oportunidad de Negocio", "COTA APP: Plataforma de Gestión para Diseño y Remodelación", "VERSIÓN v2.0")
    pdf.draw_card(14, 33, 86, 130, "1. El Problema del Sector", [
        "La mayoría de estudios de diseño y remodelación manejan su operación dispersa entre hojas de Excel sueltas, WhatsApp y Drive.",
        "Descontrol en compras de materiales y mobiliario: los presupuestos por habitación se desfasan sin detectarlo a tiempo.",
        "Falta de claridad financiera: no se conoce la ganancia real ni el saldo por pagar a cada proveedor hasta cerrar la obra.",
        "Las apps genéricas de tareas (Notion, Trello, Monday) no sirven para controlar presupuestos de obra, materiales ni actas."
    ], accent=(217, 138, 43))
    pdf.draw_card(105, 33, 86, 130, "2. La Solución: COTA App v2.0", [
        "Sistema todo-en-uno diseñado para controlar un proyecto desde la idea inicial hasta la entrega final al cliente.",
        "Conecta las 8 etapas de diseño, el catálogo de materiales y muebles por habitación, planos, pagos de obra, cobros y actas PDF.",
        "Diseño visual limpio y ejecutivo que eleva la imagen profesional de la empresa ante los clientes.",
        "Guardado en tiempo real en Google Sheets + soporte directo de archivos Excel (.xlsx) en Google Drive."
    ], accent=(200, 90, 50))
    pdf.draw_card(197, 33, 86, 130, "3. Doble Oportunidad para Socios", [
        "USO INTERNO INMEDIATO: Ordenar el 100% de nuestros proyectos activos, protegiendo el margen de ganancia.",
        "MODELO DE SUSCRIPCIÓN (SaaS): Sistema listo para alquilarlo mensualmente a otros estudios de diseño y remodelación.",
        "Producto 100% operativo hoy: 6 vistas generales de la empresa + 8 módulos detallados por proyecto."
    ], accent=(74, 124, 89))
    pdf.draw_card(14, 168, 269, 28, "Flujo Integral de COTA App v2.0", [
        "01. Cronograma (8 Etapas)  ->  02. Materiales y Muebles por Ambiente  ->  03. Planos y 3D  ->  04. Obra y Contratistas  ->  05. Finanzas y Cobros  ->  06. Actas PDF y Entrega"
    ], accent=(38, 35, 32))

    # Slide 2
    pdf.add_page()
    pdf.draw_slide_bg()
    pdf.draw_header("02 // Vista General de la Empresa", "Portafolio de Proyectos y 5 Métricas Clave en Tiempo Real", "PROYECTOS & DISEÑO")
    pdf.draw_card(14, 33, 105, 162, "Resumen Ejecutivo desde la Primera Pantalla", [
        "5 Métricas Clave en Tiempo Real: Proyectos Activos, Presupuesto Total Contratado (vs. ejecutado), Porcentaje de Avance de Diseño (%), Materiales por Aprobar (S/) y Pagos por Cobrar (S/).",
        "Filtro Inteligente por Proyecto: Permite ver los números globales de la empresa o seleccionar un solo proyecto para ver sus cobros y su lista de materiales.",
        "Vista Unificada + Carpetas: Pestaña 'TODOS LOS PROYECTOS (5)' más carpetas por unidad de negocio (Comercial & Hospitality, Residencial VIP, Residencial).",
        "Tarjetas Desplegables por Estado: Agrupadas en En Proceso, Planificación y Completado con barra de progreso y acceso al expediente."
    ], accent=(200, 90, 50))
    pdf.draw_ss_box(124, 33, 159, 162, 1, "Portafolio Principal y las 5 Métricas Clave", [
        "Abre la pestaña principal 'PROYECTOS & DISEÑO'.",
        "Ubícate en la sub-pestaña 'TODOS LOS PROYECTOS (5)'.",
        "Haz clic en 'CASA LA PLANICIE' para desplegar su tarjeta resumen.",
        "Toma captura desde las 5 métricas superiores hasta las tarjetas de proyectos."
    ])

    # Slide 3
    pdf.add_page()
    pdf.draw_slide_bg()
    pdf.draw_header("03 // Rentabilidad Global y Proveedores", "Finanzas Consolidadas de la Empresa y Directorio de Contratistas", "FINANZAS + CONTRATISTAS")
    pdf.draw_card(14, 33, 131, 62, "Finanzas Consolidadas de la Empresa", [
        "Calcula la Liquidez Neta real: Total Cobrado - (Pagos a Contratistas + Compra de Materiales + Gastos Menores).",
        "Incluye gráfico comparativo de barras por proyecto y descarga directa en Excel/CSV."
    ], accent=(74, 124, 89))
    pdf.draw_ss_box(14, 100, 131, 95, 2, "Finanzas de la Empresa y Gráfico", [
        "Entra a la pestaña 'FINANZAS DEL ESTUDIO'.",
        "Captura las 5 métricas financieras, el gráfico comparativo de barras y la tabla de resultados."
    ])
    pdf.draw_card(152, 33, 131, 62, "Directorio Inteligente de Contratistas (1-5 *)", [
        "Detecta automáticamente quién está 'En Obra Hoy' o 'Disponible' y su carga de trabajo para los próximos 7 días.",
        "Calificación de 1 a 5 estrellas e historial de desempeño con Puntos a Favor [+] e Incidencias [-]."
    ], accent=(200, 90, 50))
    pdf.draw_ss_box(152, 100, 131, 95, 3, "Directorio de Contratistas y Estrellas", [
        "Entra a la pestaña 'BASE CONTRATISTAS'.",
        "Captura la tabla con estrellas y la sección inferior de historial de desempeño."
    ])

    # Slide 4
    pdf.add_page()
    pdf.draw_slide_bg()
    pdf.draw_header("04 // Coordinación Semanal entre Socios", "Control Operativo Diario y Calendario Mensual de Actividades", "OPERATIVO + CALENDARIO")
    pdf.draw_card(14, 33, 105, 162, "Operación Diaria del Equipo sin Fricciones", [
        "Columna 1 - Pendientes y Logística Diaria: Tareas rápidas asignadas por socio (Compras de materiales, Pagos, Proveedores, Clientes) con botón 'LISTO' al completarlas.",
        "Columna 2 - En Ejecución (Hoy): Qué trabajos de obra y qué contratistas están activos hoy mismo en cada proyecto.",
        "Columna 3 - Próximos Inicios (7 Días): Alertas preventivas de los trabajos que arrancan esta semana.",
        "Calendario Mensual: Vista mensual donde cada actividad se pinta con el color de su proyecto."
    ], accent=(217, 138, 43))
    pdf.draw_ss_box(124, 33, 159, 162, 4, "Tablero de Control Operativo o Calendario", [
        "Entra a la pestaña 'CONTROL OPERATIVO' (3 columnas de tareas diarias)",
        "o a la pestaña 'CALENDARIO' (agenda mensual por proyecto).",
        "Toma una captura completa de la vista para mostrar el orden diario."
    ])

    # Slide 5
    pdf.add_page()
    pdf.draw_slide_bg()
    pdf.draw_header("05 // Expediente del Proyecto (Módulos 01 y 02)", "Resumen del Proyecto, Requerimientos y Cronograma de las 8 Etapas", "01. RESUMEN + 02. FASES")
    pdf.draw_card(14, 33, 105, 162, "8 Módulos Especializados por cada Proyecto", [
        "Al abrir un proyecto (ej. 'Casa La Planicie'), se despliega su expediente completo en 8 pestañas.",
        "01. Resumen General: 6 métricas financieras y de avance del proyecto, Ficha Técnica y requerimientos del cliente.",
        "02. Etapas de Diseño: Las 8 etapas paso a paso desde '01. Levantamiento Inicial' hasta '08. Cierre y Entrega Final'.",
        "Incluye Cronograma Visual de barras por fechas y casilla de validación 'Aprobado por Cliente'."
    ], accent=(200, 90, 50))
    pdf.draw_ss_box(124, 33, 159, 162, 5, "Resumen del Proyecto o Cronograma de Etapas", [
        "Abre el proyecto 'Casa La Planicie' con el botón 'ABRIR EXPEDIENTE ->'.",
        "Toma la captura en '01. RESUMEN' (6 métricas + Ficha Técnica + 8 barras de avance)",
        "o en '02. FASES DE DISEÑO' (Cronograma Visual de barras + tabla de etapas)."
    ])

    # Slide 6
    pdf.add_page()
    pdf.draw_slide_bg()
    pdf.draw_header("06 // Control de Compras y Documentos (Módulos 03 y 04)", "Presupuesto de Materiales y Mobiliario por Ambiente y Control de Planos", "03. MATERIALES + 04. PLANOS")
    pdf.draw_card(14, 33, 105, 162, "Presupuesto de Materiales y Muebles por Habitación", [
        "03. Materiales, Mobiliario y Acabados (pestaña FF&E): Planilla interactiva filtrable por Ambiente (Sala, Comedor, Cocina, Dormitorio, Terraza) y Categoría.",
        "Cálculo automático de Presupuesto Estimado vs. Costo Real de compra, revelando el ahorro o sobrecosto en cada habitación.",
        "Seguimiento de cada compra: Propuesto -> Cotizado -> Aprobado Cliente -> En Fabricación -> Instalado.",
        "04. Entregables y Planos: Control de versiones de planos y vistas 3D, aprobaciones y links a Drive."
    ], accent=(74, 124, 89))
    pdf.draw_ss_box(124, 33, 159, 162, 6, "Lista de Materiales y Desglose por Ambiente", [
        "Dentro de 'Casa La Planicie', entra a '03. ESPECIFICACIONES FF&E'.",
        "Haz clic en 'Ver desglose de presupuesto FF&E por Ambiente'.",
        "Toma la captura mostrando las 4 métricas, el resumen por habitación y la tabla de materiales."
    ])

    # Slide 7
    pdf.add_page()
    pdf.draw_slide_bg()
    pdf.draw_header("07 // Ejecución de Obra, Finanzas y Cierre (Módulos 05 al 08)", "Control de Obra, Hitos de Cobro, Actas en PDF y Revisión de Entrega", "MÓDULOS 05 AL 08")
    pdf.draw_card(14, 33, 131, 62, "05. Ejecución de Obra y 06. Cobros / Caja Chica", [
        "Control por rubro de obra (Demolición, Carpintería, Pintura) con etiquetas de PACTADO / PAGADO / SALDO y sugeridor inteligente de contratistas disponibles.",
        "Cronograma de cobros al cliente y registro rápido de Caja Chica de Obra."
    ], accent=(200, 90, 50))
    pdf.draw_ss_box(14, 100, 131, 95, 7, "Rubros de Obra y Control de Pagos", [
        "Dentro de 'Casa La Planicie', abre '05. EJECUCIÓN & PARTIDAS'.",
        "Captura los rubros de obra con sus etiquetas PACTADO / PAGADO / SALDO y tareas."
    ])
    pdf.draw_card(152, 33, 131, 62, "07. Actas en PDF Automático y 08. Revisión Final", [
        "Importa apuntes de reunión / Google Meet para ordenar asistentes y acuerdos, generando un Acta formal en PDF con membrete en un clic.",
        "Módulo 08 (Punch List): Lista de observaciones y retoques finales por habitación antes de entregar la obra."
    ], accent=(74, 124, 89))
    pdf.draw_ss_box(152, 100, 131, 95, 8, "Actas de Reunión (Exportar PDF) o Revisión Final", [
        "Abre '07. REUNIONES & ACTAS' en 'Casa La Planicie'.",
        "Captura la ficha del acta, las tablas de participantes/acuerdos y el botón 'EXPORTAR ACTA A PDF'."
    ])

    # Slide 8
    pdf.add_page()
    pdf.draw_slide_bg()
    pdf.draw_header("08 // Tecnología y Visión Estratégica", "Solidez Técnica Lograda y Hoja de Ruta con el Socio", "LISTO PARA OPERAR")
    pdf.draw_card(14, 33, 131, 162, "Lo que ya está resuelto y funcionando hoy (v2.0)", [
        "Base de Datos en la Nube + Respaldo en Excel: Conecta en tiempo real con Google Sheets y soporta lectura/escritura directa en archivos Excel (.xlsx) en Google Drive.",
        "Guardado Inteligente de Cambios: Detecta automáticamente qué tablas fueron editadas y sincroniza solo lo necesario.",
        "Diseño Ejecutivo y Simétrico: Interfaz limpia en tonos cálidos (#F7F4EF y terracota #C85A32), adaptable a cualquier pantalla.",
        "Configuración Multi-Socio: Nombres de directores o socios configurables desde el panel lateral.",
        "Calidad Verificada: Sistema respaldado por 22 pruebas automáticas que garantizan la exactitud de todos los cálculos."
    ], accent=(200, 90, 50))
    pdf.draw_card(152, 33, 131, 162, "Hoja de Ruta Propuesta con el Socio", [
        "FASE 1 - Implementación Interna Inmediata (Mes 1): Gestionar el 100% de nuestros proyectos activos en la app, estandarizando presupuestos de materiales, contratistas y actas PDF.",
        "FASE 2 - Portal de Consulta para el Cliente (Mes 2-3): Vista dedicada para que el cliente revise el avance de su proyecto en línea, apruebe materiales y consulte su estado de cuenta.",
        "FASE 3 - Escalabilidad como Software por Suscripción (Mes 4+): Licenciamiento mensual para otros estudios de diseño, arquitectura y remodelación."
    ], accent=(74, 124, 89))

    pdf.output(output_path)


def generar_archivos():
    drive_dir = r"G:\My Drive\Cota App"
    local_dir = r"d:\cota-app"
    artifact_dir = r"C:\Users\Alvaro\.gemini\antigravity\brain\4f210c80-3915-4c24-91f5-e441a5c5fff4"

    for d in [drive_dir, local_dir, artifact_dir]:
        if os.path.exists(d):
            for fname in ["Presentacion_Socio_COTA_App_Simple", "Presentacion_Socio_COTA_App"]:
                pptx_path = os.path.join(d, f"{fname}.pptx")
                pdf_path = os.path.join(d, f"{fname}.pdf")
                build_pptx(pptx_path)
                build_pdf(pdf_path)
                print(f"Generado: {pptx_path} y {pdf_path}")


if __name__ == "__main__":
    generar_archivos()
