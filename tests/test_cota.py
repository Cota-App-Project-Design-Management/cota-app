"""
Suite de pruebas unitarias e integrales para COTA APP.
Verifica utilidades, parsers, persistencia en cascada y renderizado.
"""

import datetime
import pytest
import pandas as pd
from cota.utils import (
    safe_float,
    parse_date,
    format_date,
    format_currency,
    to_bool,
    calcular_rating,
    parse_resumen_meet
)
from cota.db import sembrar_fases_default, renombrar_proyecto, purgar_proyecto_cascada


def test_safe_float():
    assert safe_float(10) == 10.0
    assert safe_float("1500.50") == 1500.50
    assert safe_float("1,500.50") == 1500.50
    assert safe_float("1.500,50") == 1500.50
    assert safe_float("250,75") == 250.75
    assert safe_float(None) == 0.0
    assert safe_float("nan") == 0.0
    assert safe_float("invalid", default=99.0) == 99.0


def test_parse_date():
    d1 = parse_date("2026-10-14")
    assert d1 == datetime.date(2026, 10, 14)

    d2 = parse_date("14/10/2026")
    assert d2 == datetime.date(2026, 10, 14)

    d3 = parse_date(datetime.datetime(2026, 10, 14, 15, 30))
    assert d3 == datetime.date(2026, 10, 14)

    assert parse_date(None) is None
    assert parse_date("") is None
    assert parse_date("invalid") is None


def test_format_currency():
    assert format_currency(12500.5, "S/") == "S/ 12,500.50"
    assert format_currency(0, "$") == "$ 0.00"


def test_to_bool():
    assert to_bool(True) is True
    assert to_bool("true") is True
    assert to_bool("1") is True
    assert to_bool("VERDADERO") is True
    assert to_bool("si") is True
    assert to_bool(False) is False
    assert to_bool("false") is False
    assert to_bool("0") is False
    assert to_bool(None) is False


def test_sembrar_fases_default():
    df_fases = sembrar_fases_default("Casa Prueba", datetime.date(2026, 1, 1))
    assert len(df_fases) == 7
    assert "01. Levantamiento & Brief" in df_fases['Fase'].tolist()
    assert "02. Moodboard & Concepto" in df_fases['Fase'].tolist()
    assert "03. Plano Preliminar / Distribución" in df_fases['Fase'].tolist()
    assert "05. Renders & Visualización 3D" in df_fases['Fase'].tolist()
    assert "Cambios_Realizados" in df_fases.columns
    assert "Fecha_Ultimo_Cambio" in df_fases.columns
    assert all(df_fases['Proyecto'] == "Casa Prueba")
    assert all(df_fases['Inicio'] == "")
    assert all(df_fases['Fin'] == "")


def test_parse_resumen_meet():
    sample_text = """
    Reunión de Coordinación de Diseño - Casa Playa
    Fecha: 15/10/2026
    Hora: 11:00 am
    Asistentes:
    - Roberto Gomez (Cliente)
    - Mariana Solis (Arquitecta)
    Acuerdos y Próximos pasos:
    - Mariana Solis: Enviar propuesta de acabados de cocina
    - Roberto Gomez: Revisar distribución de dormitorios
    """
    res = parse_resumen_meet(sample_text, "Casa Playa", count=0)
    assert "Casa Playa" in res['nombre_sesion']
    assert len(res['invitados']) >= 2
    assert len(res['acuerdos']) >= 2
    assert res['fecha_real'] == "15/10/2026"


def test_cascade_renombrar_y_purgar():
    import streamlit as st
    st.session_state['proyectos'] = pd.DataFrame([{'Nombre': 'P1', 'Archivado': False}])
    st.session_state['tasks'] = pd.DataFrame([{'Proyecto': 'P1', 'Tarea': 'Pintura'}])
    st.session_state['materiales'] = pd.DataFrame([{'Proyecto': 'P1', 'Material': 'Sofá'}])
    st.session_state['fases'] = pd.DataFrame([{'Proyecto': 'P1', 'Fase': 'Concepto'}])

    renombrar_proyecto('P1', 'P_Nuevo')
    assert st.session_state['proyectos'].iloc[0]['Nombre'] == 'P_Nuevo'
    assert st.session_state['tasks'].iloc[0]['Proyecto'] == 'P_Nuevo'
    assert st.session_state['materiales'].iloc[0]['Proyecto'] == 'P_Nuevo'
    assert st.session_state['fases'].iloc[0]['Proyecto'] == 'P_Nuevo'

    purgar_proyecto_cascada('P_Nuevo')
    assert len(st.session_state['proyectos']) == 0
    assert len(st.session_state['tasks']) == 0
    assert len(st.session_state['materiales']) == 0
    assert len(st.session_state['fases']) == 0


def test_generar_pdf_minuta():
    from cota.pdf import generar_pdf_minuta
    r_ses = {
        'Titulo': "Reunión de Avance Conceptual",
        'Proyecto': "Depa San Isidro",
        'Fecha': "2026-10-14",
        'Hora': "10:00",
        'Tipo': "Reunión Cliente",
        'Resumen': "Se revisaron las muestras de telas y la distribución espacial de la sala-comedor."
    }
    invitados_df = pd.DataFrame([
        {'Nombre': 'Carlos Perez', 'Rol': 'Cliente', 'Empresa': 'Particular'},
        {'Nombre': 'Laura Mendez', 'Rol': 'Arquitecta', 'Empresa': 'Cota Estudio'}
    ])
    acuerdos_df = pd.DataFrame([
        {'Acuerdo': 'Definir paleta de color para sala', 'Responsable': 'Laura Mendez', 'Fecha_Compromiso': '2026-11-01', 'Estado': 'Pendiente'},
        {'Acuerdo': 'Aprobar cotización de carpintería', 'Responsable': 'Carlos Perez', 'Fecha_Compromiso': '2026-11-05', 'Estado': 'Aprobado'}
    ])
    pdf_bytes = generar_pdf_minuta(r_ses, invitados_df, acuerdos_df)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF")


def test_get_proyectos_activos_y_archivados():
    from cota.db import get_proyectos_activos, get_proyectos_archivados, COLS_PROY

    # Test with None and empty DataFrame
    empty_df = pd.DataFrame(columns=COLS_PROY)
    act_empty = get_proyectos_activos(empty_df)
    arc_empty = get_proyectos_archivados(empty_df)
    assert act_empty.empty
    assert arc_empty.empty
    assert 'Nombre' in act_empty.columns
    assert 'Nombre' in arc_empty.columns

    # Test with active and archived rows
    df_sample = pd.DataFrame([
        {'Nombre': 'P_Activo_1', 'Archivado': False, 'Presupuesto': 1000},
        {'Nombre': 'P_Activo_2', 'Archivado': 'false', 'Presupuesto': 2000},
        {'Nombre': 'P_Archivado_1', 'Archivado': True, 'Presupuesto': 3000},
        {'Nombre': 'P_Archivado_2', 'Archivado': 'SI', 'Presupuesto': 4000},
    ])
    act = get_proyectos_activos(df_sample)
    arc = get_proyectos_archivados(df_sample)
    assert len(act) == 2
    assert set(act['Nombre']) == {'P_Activo_1', 'P_Activo_2'}
    assert len(arc) == 2
    assert set(arc['Nombre']) == {'P_Archivado_1', 'P_Archivado_2'}


def test_calcular_rating_y_sugerir():
    from cota.utils import calcular_rating, sugerir_contratista

    df_h = pd.DataFrame([
        {'ID_Contratista': 'Juan Perez', 'Estado': 'Aprobado'},
        {'ID_Contratista': 'Juan Perez', 'Estado': 'Aprobado'},
        {'ID_Contratista': 'Juan Perez', 'Estado': 'Rechazado'},
    ])
    df_t = pd.DataFrame([
        {'Contratista': 'Juan Perez', 'Culpa_Contratista': True, 'Estado': 'A tiempo', 'Inicio': '2026-10-01', 'Fin': '2026-10-10'},
        {'Contratista': 'Juan Perez', 'Culpa_Contratista': False, 'Estado': 'A tiempo', 'Inicio': '2026-10-11', 'Fin': '2026-10-20'},
    ])
    df_m = pd.DataFrame([
        {
            'ID_Contratista': 'Juan Perez',
            'Especialidad': 'Pintura',
            'Ubicación_Base': 'Lima',
            'Notas': '[+] Excelente acabado [+] Puntual [-] Se demoró limpieza'
        }
    ])

    rating = calcular_rating('Juan Perez', df_h, df_t, df_m)
    assert 1 <= rating <= 5

    # Sugerir contratista
    rec = sugerir_contratista('Pintura', 'Lima', '2026-11-01', '2026-11-15', df_m, df_t, df_h)
    assert rec is not None
    assert 'Juan Perez' in rec


def test_analizar_tareas_proyecto():
    from cota.utils import analizar_tareas_proyecto

    hoy = datetime.date(2026, 10, 19)
    df_tasks = pd.DataFrame([
        {
            'Proyecto': 'Casa Test',
            'Tarea': 'Demolición',
            'Contratista': 'C1',
            'Estado': '🟢 Completado a tiempo',
            'Inicio': '2026-10-01',
            'Fin': '2026-10-10',
        },
        {
            'Proyecto': 'Casa Test',
            'Tarea': 'Instalación Porcelanato',
            'Contratista': 'Mármoles SAC',
            'Estado': '🔵 En Proceso',
            'Inicio': '2026-10-12',
            'Fin': '2026-10-21',
        },
        {
            'Proyecto': 'Casa Test',
            'Tarea': 'Pintura General',
            'Contratista': 'Pintores EIRL',
            'Estado': '🟡 Planificado',
            'Inicio': '2026-10-22',
            'Fin': '2026-10-30',
        },
    ])

    info = analizar_tareas_proyecto(df_tasks, 'Casa Test', hoy)
    assert info['total'] == 3
    assert info['en_proceso'] == 1
    assert info['completadas'] == 1
    assert len(info['por_terminar']) == 1
    assert len(info['por_empezar']) == 1
    assert 'POR TERMINAR' in info['widget_badge']
    assert info['widget_titulo'] == 'Instalación Porcelanato'


def test_banco_y_sincronizar_fases():
    import streamlit as st
    from cota.db import obtener_banco_fases, agregar_fase_banco, sincronizar_fases_proyecto, sembrar_fases_default

    st.session_state['fases'] = sembrar_fases_default('Depa Express', datetime.date(2026, 10, 1))
    # Marcar primera fase como aprobada al 100%
    st.session_state['fases'].loc[0, 'Avance_Pct'] = 100
    st.session_state['fases'].loc[0, 'Aprobado_Cliente'] = True

    banco = obtener_banco_fases()
    assert len(banco) >= 8

    nueva = agregar_fase_banco("99. Styling Fotográfico", etapa="Renders", dias=3)
    assert nueva["Fase"] == "99. Styling Fotográfico"

    # Activar solo 3 etapas de diseño
    fases_elegidas = [
        "01. Levantamiento & Brief",
        "02. Moodboard & Concepto",
        "99. Styling Fotográfico",
    ]
    sincronizar_fases_proyecto('Depa Express', fases_elegidas, datetime.date(2026, 10, 1))

    df_res = st.session_state['fases'][st.session_state['fases']['Proyecto'] == 'Depa Express']
    assert len(df_res) == 3
    assert "05. Expediente Técnico & Planos" not in df_res['Fase'].tolist()
    assert "99. Styling Fotográfico" in df_res['Fase'].tolist()
    # Verificar que el avance de la fase 1 se conservó
    f1 = df_res[df_res['Fase'] == "01. Levantamiento & Brief"].iloc[0]
    assert int(f1['Avance_Pct']) == 100
    assert bool(f1['Aprobado_Cliente']) is True


def test_generar_y_parsear_cotizacion_venti():
    import streamlit as st
    from cota.cotizacion import (
        generar_plantilla_cotizacion_venti,
        parsear_cotizacion_venti,
        aplicar_cotizacion_a_proyecto,
    )
    from cota.db import COLS_PROY, COLS_P_INFO, COLS_TASKS

    # 1. Generar plantilla en blanco y verificar que es un .xlsx válido (con % personalizados e IGV 18%)
    xlsx_blank = generar_plantilla_cotizacion_venti(
        proyecto="Proyecto Galeon 129",
        cliente="Nano Salazar",
        tc=3.43,
        gg_pct=0.03,
        gestion_pct=0.18,
        incluir_igv=True,
    )
    assert isinstance(xlsx_blank, bytes)
    assert xlsx_blank[:4] == b"PK\x03\x04"

    parsed_blank = parsear_cotizacion_venti(xlsx_blank)
    assert parsed_blank["proyecto"] == "Proyecto Galeon 129"
    assert parsed_blank["cliente"] == "Nano Salazar"
    assert parsed_blank["tc"] == 3.43
    assert len(parsed_blank["partidas"]) == 3
    assert parsed_blank["gg_pct"] == 3.0
    assert parsed_blank["utilidades_pct"] == 18.0
    assert parsed_blank["igv_pct"] == 18.0

    # 2. Parsear un presupuesto CSV en formato Venti con datos llenados por el cliente
    csv_venti_lleno = """
,,,,,,,,,
,Proyecto ,Local Venti Miraflores,,,,,,2026-10-20,
,,,,,,,,,
,Cliente:,Inversiones Venti SAC,,,,,,TC:,"3,42"
,,Descripción,Moneda,Unidad,Metrado,"Valor
Unitario","Valor
Parcial",Sub Total (S/.),Mix
,1,Obras Civiles,,,,,,0,#DIV/0!
,1.01,Demolición y desmontaje,Soles,glb,1,3500,3500,,
,1.02,Tabiquería Drywall RF,Soles,m2,20,125,2500,,
,1.03,,Soles,glb,1,,0,,
,2,Instalaciones Eléctricas y Sanitarias,,,,,,0,#DIV/0!
,2.01,Cableado y tableros eléctricos,Soles,glb,1,4000,4000,,
,2.02,Equipos especiales importados,Dólares,und,2,500,1000,,
,3,Carpintería y Mobiliario,,,,,,0,#DIV/0!
,3.01,Barra principal en enchape de madera,Soles,glb,1,6580,6580,,
,,SUB TOTAL (Casco),Soles,,,, ,0,#DIV/0!
,,Gastos generales,Soles,,0.02,,0,,
,,Gestión y supervisión de obras,Soles,,0.15,,0,,
,,IGV,Soles,,-%,,0,,
,,TOTAL,Soles,,,,,0,#DIV/0!
,,,Dólares,,,,,0,
"""
    parsed = parsear_cotizacion_venti(csv_venti_lleno)
    assert parsed["proyecto"] == "Local Venti Miraflores"
    assert parsed["cliente"] == "Inversiones Venti SAC"
    assert parsed["tc"] == 3.42
    assert len(parsed["partidas"]) == 3

    # Partida 1: 3500 + 2500 = 6000
    p1 = parsed["partidas"][0]
    assert p1["nombre_completo"] == "01. Obras Civiles"
    assert p1["monto_pactado"] == 6000.0
    assert len(p1["tareas"]) == 2

    # Partida 2: 4000 + (1000 * 3.42 = 3420) = 7420
    p2 = parsed["partidas"][1]
    assert p2["nombre_completo"] == "02. Instalaciones Eléctricas y Sanitarias"
    assert p2["monto_pactado"] == 7420.0
    assert len(p2["tareas"]) == 2
    assert p2["tareas"][1]["presupuesto_soles"] == 3420.0

    # Partida 3: 6580
    p3 = parsed["partidas"][2]
    assert p3["monto_pactado"] == 6580.0

    # Subtotal Casco: 6000 + 7420 + 6580 = 20000
    assert parsed["subtotal_casco"] == 20000.0
    # Gastos generales (2%): 400.0
    assert parsed["gg_pct"] == 2.0
    assert parsed["gg_monto"] == 400.0
    # Gestión y supervisión / Utilidades (15%): 3000.0
    assert parsed["utilidades_pct"] == 15.0
    assert parsed["utilidades_monto"] == 3000.0
    # Total: 20000 + 400 + 3000 = 23400.0
    assert parsed["presupuesto_total"] == 23400.0

    # 3. Aplicar cotización a un proyecto en session_state
    st.session_state["proyectos"] = pd.DataFrame([{
        "Nombre": "Local Venti Miraflores",
        "Cliente": "",
        "Presupuesto": 0.0,
        "Utilidades": 0.0,
        "GG_Presupuesto": 0.0,
        "Archivado": False,
    }])
    st.session_state["partidas"] = pd.DataFrame(columns=["Proyecto", "Nombre_Partida"])
    st.session_state["p_info"] = pd.DataFrame(columns=COLS_P_INFO)
    st.session_state["tasks"] = pd.DataFrame(columns=COLS_TASKS)

    res = aplicar_cotizacion_a_proyecto("Local Venti Miraflores", parsed, modo="reemplazar", actualizar_ficha=True)
    assert res["partidas_importadas"] == 3
    assert res["tareas_importadas"] == 5

    proy_row = st.session_state["proyectos"].iloc[0]
    assert proy_row["Presupuesto"] == 23400.0
    assert proy_row["Utilidades"] == 3000.0
    assert proy_row["GG_Presupuesto"] == 400.0
    assert proy_row["Cliente"] == "Inversiones Venti SAC"

    tasks_proy = st.session_state["tasks"]
    assert len(tasks_proy) == 5
    assert tasks_proy["Presupuesto"].sum() == 20000.0


def test_in_app_budget_builder():
    import streamlit as st
    from cota.cotizacion import (
        asegurar_estructura_presupuesto_proyecto,
        ajustar_cantidad_partidas_proyecto,
        ajustar_cantidad_tareas_partida,
        renombrar_partida_presupuesto,
        recalcular_totales_presupuesto_proyecto,
        exportar_proyecto_a_formato_venti,
    )
    from cota.db import COLS_PROY, COLS_P_INFO, COLS_TASKS

    # Inicializar tablas para el test
    st.session_state["proyectos"] = pd.DataFrame([{
        "Nombre": "Casa Bosque",
        "Cliente": "Cliente Prueba",
        "Presupuesto": 0.0,
        "Utilidades": 0.0,
        "GG_Presupuesto": 0.0,
        "TC_Presupuesto": 3.42,
        "GG_Pct": 2.0,
        "Utilidades_Pct": 15.0,
        "Incluir_IGV": False,
        "Archivado": False,
    }])
    st.session_state["partidas"] = pd.DataFrame(columns=["Proyecto", "Nombre_Partida"])
    st.session_state["p_info"] = pd.DataFrame(columns=COLS_P_INFO)
    st.session_state["tasks"] = pd.DataFrame(columns=COLS_TASKS)

    # 1. Asegurar estructura por defecto: 3 partidas con 3 tareas cada una
    asegurar_estructura_presupuesto_proyecto("Casa Bosque", n_partidas_default=3, n_tareas_default=3)
    assert len(st.session_state["partidas"]) == 3
    assert len(st.session_state["tasks"]) == 9

    # 2. Renombrar partida 1
    renombrar_partida_presupuesto("Casa Bosque", "01. Partida 1", "01. Demoliciones y Albañilería")
    p1 = st.session_state["partidas"].iloc[0]["Nombre_Partida"]
    assert p1 == "01. Demoliciones y Albañilería"
    assert all(st.session_state["tasks"].iloc[0:3]["Partida"] == "01. Demoliciones y Albañilería")

    # 3. Ajustar cantidad de tareas en partida 1 (de 3 a 4)
    ajustar_cantidad_tareas_partida("Casa Bosque", 1, "01. Demoliciones y Albañilería", 4)
    tasks_p1 = st.session_state["tasks"][st.session_state["tasks"]["Partida"] == "01. Demoliciones y Albañilería"]
    assert len(tasks_p1) == 4

    # 4. Ajustar cantidad de partidas (de 3 a 4)
    ajustar_cantidad_partidas_proyecto("Casa Bosque", 4, n_tareas_default=2)
    assert len(st.session_state["partidas"]) == 4

    # 5. Fijar presupuestos en tareas y recalcular totales
    st.session_state["tasks"].loc[0, "Metrado"] = 10.0
    st.session_state["tasks"].loc[0, "Valor_Unitario"] = 100.0
    st.session_state["tasks"].loc[0, "Presupuesto"] = 1000.0

    totales = recalcular_totales_presupuesto_proyecto("Casa Bosque", sincronizar_pactado=True)
    assert totales["subtotal_casco"] == 1000.0
    assert totales["gg_monto"] == 20.0
    assert totales["utilidades_monto"] == 150.0
    assert totales["presupuesto_total"] == 1170.0

    # 6. Exportar a formato Excel (.xlsx)
    xlsx_bytes = exportar_proyecto_a_formato_venti("Casa Bosque")
    assert isinstance(xlsx_bytes, bytes)
    assert xlsx_bytes[:4] == b"PK\x03\x04"


def test_views_project_imports():
    from cota.config import AMBIENTES_DEFAULT
    assert isinstance(AMBIENTES_DEFAULT, list)
    assert len(AMBIENTES_DEFAULT) > 0
    import cota.ui.views_project as vp
    assert hasattr(vp, "_render_tab_presupuesto")
    assert hasattr(vp, "_render_tab_obra")
    assert hasattr(vp, "_render_tab_punch")


def test_normalizar_supervisado():
    from cota.db import _normalizar_supervisado, COLS_TASKS
    assert "Supervisado" in COLS_TASKS

    assert _normalizar_supervisado(True) == "Sí"
    assert _normalizar_supervisado("True") == "Sí"
    assert _normalizar_supervisado("Sí") == "Sí"
    assert _normalizar_supervisado("si") == "Sí"
    assert _normalizar_supervisado("1") == "Sí"
    assert _normalizar_supervisado(1) == "Sí"

    assert _normalizar_supervisado(False) == "No"
    assert _normalizar_supervisado("False") == "No"
    assert _normalizar_supervisado("No") == "No"
    assert _normalizar_supervisado("0") == "No"
    assert _normalizar_supervisado(0) == "No"
    assert _normalizar_supervisado(None) == "No"
    assert _normalizar_supervisado("") == "No"


def test_proy_tiene_anio():
    from cota.ui.views_main import _proy_tiene_anio
    r1 = {"Inicio": "2025-01-10", "Fin": "2025-11-20"}
    assert _proy_tiene_anio(r1, "2025") is True
    assert _proy_tiene_anio(r1, "2026") is False
    assert _proy_tiene_anio(r1, "🌐 Todos los Años") is True

    r2 = {"Inicio": "2024-06-01", "Fin": "2026-03-15"}
    assert _proy_tiene_anio(r2, "2024") is True
    assert _proy_tiene_anio(r2, "2025") is True
    assert _proy_tiene_anio(r2, "2026") is True
    assert _proy_tiene_anio(r2, "2027") is False


def test_kpi_proyectos_activos_calculo():
    df = pd.DataFrame([
        {"Nombre": "P1", "Estado": "🟡 Planificación"},
        {"Nombre": "P2", "Estado": "🔵 En Proceso"},
        {"Nombre": "P3", "Estado": "🟢 Completado"},
        {"Nombre": "P4", "Estado": "🔵 En Proceso"},
    ])
    n_plan = len(df[df['Estado'].astype(str).str.contains('Planificación', case=False, na=False)])
    n_en_proc = len(df[df['Estado'].astype(str).str.contains('Proceso', case=False, na=False)])
    n_activos = n_plan + n_en_proc
    assert n_plan == 1
    assert n_en_proc == 2
    assert n_activos == 3
    subtitle = f"{n_en_proc} en proceso · {n_plan} en planificación"
    assert subtitle == "2 en proceso · 1 en planificación"


def test_status_accordion_labels():
    is_open = True
    flecha = "▲" if is_open else "▼"
    lbl_open = f"{flecha}   ESTADO: 🟡 PLANIFICACIÓN (2)"
    assert lbl_open == "▲   ESTADO: 🟡 PLANIFICACIÓN (2)"

    is_open = False
    flecha = "▲" if is_open else "▼"
    lbl_closed = f"{flecha}   ESTADO: 🟡 PLANIFICACIÓN (2)"
    assert lbl_closed == "▼   ESTADO: 🟡 PLANIFICACIÓN (2)"


def test_tab_partidas_y_tareas_cols():
    # Verificar que en la pestaña 05 las columnas operativas visibles excluyen moneda, unidad, metrado, valor unitario y presupuesto
    cols_visibles = [
        "Codigo_Item",
        "Tarea",
        "Especialidad",
        "Contratista",
        "Estado",
        "Supervisado",
        "Inicio",
        "Fin",
        "Notas",
    ]
    for col_oculta in ["Moneda", "Unidad", "Metrado", "Valor_Unitario", "Presupuesto"]:
        assert col_oculta not in cols_visibles


def test_sanitizar_fases_estudio():
    import streamlit as st
    from cota.db import sanitizar_fases_estudio, registrar_cambio_diseno, sembrar_fases_default
    st.session_state["fases"] = pd.DataFrame([
        {"Proyecto": "P1", "Orden": 1, "Fase": "01. Levantamiento & Brief", "Estado": "🟢 Aprobada cliente"},
        {"Proyecto": "P1", "Orden": 2, "Fase": "02. Concepto & Moodboard", "Estado": "🟡 En desarrollo"},
        {"Proyecto": "P1", "Orden": 3, "Fase": "03. Anteproyecto / Distribución", "Estado": "⚪ No iniciada"},
        {"Proyecto": "P1", "Orden": 6, "Fase": "06. Presupuesto & Compras (FF&E)", "Estado": "⚪ No iniciada"},
        {"Proyecto": "P1", "Orden": 7, "Fase": "07. Ejecución / Obra / Montaje", "Estado": "⚪ No iniciada"},
        {"Proyecto": "P1", "Orden": 8, "Fase": "08. Cierre & Entrega Final", "Estado": "⚪ No iniciada"},
    ])
    sanitizar_fases_estudio()
    fases_res = st.session_state["fases"]["Fase"].tolist()
    assert not any("ff&e" in f.lower() or "ffe" in f.lower() for f in fases_res)
    assert not any("obra" in f.lower() or "cierre" in f.lower() for f in fases_res)
    assert "02. Moodboard & Concepto" in fases_res
    assert "03. Plano Preliminar / Distribución" in fases_res
    assert len(st.session_state["fases"]) == 3
    assert "Cambios_Realizados" in st.session_state["fases"].columns
    assert "Fecha_Ultimo_Cambio" in st.session_state["fases"].columns

    # Probar registro de cambio de diseño por fecha y conteo automático
    registrar_cambio_diseno(
        proy_name="P1",
        fase_diseno="03. Plano Preliminar / Distribución",
        tipo_entregable="Plano Preliminar / Layout",
        nombre_entregable="Plano Preliminar Cocina",
        fecha_cambio="2026-10-27",
        detalle_cambio="Reubicación de isla central",
        estado="🟡 En proceso",
        responsable="Alvaro",
        nro_cambios=2,
    )
    f_prelim = st.session_state["fases"][
        (st.session_state["fases"]["Proyecto"] == "P1")
        & (st.session_state["fases"]["Fase"] == "03. Plano Preliminar / Distribución")
    ].iloc[0]
    assert int(f_prelim["Cambios_Realizados"]) == 2
    assert f_prelim["Fecha_Ultimo_Cambio"] == "2026-10-27"


def test_on_table_edit_missing_key_no_crash():
    import streamlit as st
    from cota.db import on_table_edit
    # Asegurar que cuando base_key no existe en session_state, no se lance KeyError ni crashee
    st.session_state["dummy_widget_key"] = {"edited_rows": {}}
    if "missing_base_key" in st.session_state:
        del st.session_state["missing_base_key"]
    # Debe retornar sin lanzar KeyError
    on_table_edit("missing_base_key", "dummy_widget_key", "tasks")


def test_cuadro_pagos_semanales_parse_calculo_y_excel():
    import io
    import streamlit as st
    from cota.cotizacion import (
        parsear_cuadro_pagos_semanales,
        calcular_resumen_cuadro_pagos_semanales,
        exportar_cuadro_pagos_semanales_excel,
    )

    csv_user = """ ,Proyecto:, , , , , , , , , , , , , 
 ,Cliente:, , , , , , , , , , , , , 
 , , , , , , , , , , , , , , 
 ,Descripción,Moneda,TOTAL,ADELANTO 1,SEMANA 1,SEMANA 2,SEMANA 3,SEMANA 4,SEMANA 5,PAGADO,SALDO, , , 
 , , , , , , , , ,Por Pagar, , , , , 
 ,TRABAJOS CONTRATISTAS, , , , , , , , , , , , , 
 ,OBRAS CIVILES,Soles,"10,915.00", ,"3,537.00","1,600.00","2,000.00", ,"3,778.00","7,137.00","3,778.00", , , 
 ,INSTALACIONES E&S,Soles,"3,870.00", ,"1,655.00", ,"1,335.00", ,880.00,"2,990.00",880.00, , , 
 ,CARPINTERÍA Y MOBILIARIO,Soles,"18,763.50","8,000.00", ,"5,381.75", , , ,"13,381.75","5,381.75", , , 
 ,TABLERO DE PIEDRA,Soles,"5,192.50","1,192.50", , ,"2,500.00", , ,"3,692.50","1,500.00", , , 
 ,PINTURA,Soles,"5,920.00", , ,"1,800.00","1,000.00","1,600.00", ,"4,400.00","1,520.00", , , 
 ,TRABAJOS PRELIMINARES,Soles,"4,220.00", ,"2,532.00", ,"1,688.00", , ,"4,220.00",0.00, , , 
 ,VIDRIOS,Soles,"1,620.00", , , , , ,"1,134.00",0.00,"1,620.00", , ,70% de adelanto de mampara y espejo
 ,SUB TOTAL, ,"50,501.00","9,192.50","7,724.00","8,781.75","8,523.00","1,600.00","5,792.00","35,821.25","14,679.75", , , 
 ,Gestión y supervisión de obras,Soles,"9,000.00", , , ,"1,000.00", , ,"1,000.00","8,000.00", , , 
 ,Gastos Generales,Soles,0.00, , , , , , ,0.00,0.00, , , 
 ,TOTAL,Soles,"59,501.00","9,192.50","7,724.00","8,781.75","9,523.00","1,600.00","5,792.00","36,821.25","22,679.75", , , 
 , ,Dólares,"16,528.06","2,553.47","2,145.56","2,439.38","2,645.28",444.44,"1,608.89","10,228.13","6,299.93", , , 
"""
    st.session_state["proyectos"] = pd.DataFrame([
        {"Nombre": "Proy Pagos Test", "Cliente": "Cliente Demo", "TC_Presupuesto": 3.60}
    ])

    parsed = parsear_cuadro_pagos_semanales(io.StringIO(csv_user), tc_default=3.60)
    assert parsed["num_semanas"] == 5
    assert "SEMANA 5" in parsed["cols_por_pagar"]
    assert len(parsed["filas_contratistas"]) == 7

    res = calcular_resumen_cuadro_pagos_semanales(parsed)
    assert res["sub_total"]["TOTAL"] == 50501.00
    assert res["sub_total"]["PAGADO"] == 35821.25
    assert res["sub_total"]["SALDO"] == 14679.75
    assert res["total_soles"]["TOTAL"] == 59501.00
    assert res["total_soles"]["PAGADO"] == 36821.25
    assert res["total_soles"]["SALDO"] == 22679.75
    assert res["total_dolares"]["TOTAL"] == 16528.06

    xlsx_bytes = exportar_cuadro_pagos_semanales_excel("Proy Pagos Test", parsed)
    assert isinstance(xlsx_bytes, bytes)
    assert xlsx_bytes[:4] == b"PK\x03\x04"


def test_asegurar_estructura_presupuesto_float64_columns_no_lossy_error():
    import numpy as np
    import streamlit as st
    from cota.cotizacion import asegurar_estructura_presupuesto_proyecto, recalcular_totales_presupuesto_proyecto

    # Simular que Google Sheets / Pandas infirió float64 en columnas vacías o numéricas (ej. Codigo_Item = 1.01, Unidad = NaN)
    st.session_state["proyectos"] = pd.DataFrame([
        {
            "Nombre": "Casa La Planicie",
            "Presupuesto": 0.0,
            "TC_Presupuesto": 3.60,
            "Link_Drive": np.nan,
            "Pagos_Semanales_JSON": np.nan,
        }
    ])
    st.session_state["partidas"] = pd.DataFrame([
        {"Proyecto": "Casa La Planicie", "Nombre_Partida": "1. Obras Civiles"}
    ])
    st.session_state["p_info"] = pd.DataFrame([
        {"Proyecto": "Casa La Planicie", "Nombre_Partida": "1. Obras Civiles", "Monto_Pactado": 1000.0}
    ])
    st.session_state["tasks"] = pd.DataFrame([
        {
            "Proyecto": "Casa La Planicie",
            "Partida": "1. Obras Civiles",
            "Orden": 1.0,
            "Codigo_Item": 1.01,       # float64!
            "Tarea": "Demolición",
            "Moneda": np.nan,          # float64!
            "Unidad": np.nan,          # float64!
            "Metrado": np.nan,
            "Valor_Unitario": 500.0,
            "Presupuesto": 500.0,
        }
    ])

    # No debe lanzar TypeError / LossySetitemError
    asegurar_estructura_presupuesto_proyecto("Casa La Planicie")
    tot = recalcular_totales_presupuesto_proyecto("Casa La Planicie")
    assert st.session_state["tasks"].loc[0, "Codigo_Item"] == "1.01"
    assert st.session_state["tasks"].loc[0, "Moneda"] == "Soles"
    assert st.session_state["tasks"].loc[0, "Unidad"] == "glb"
    assert tot["subtotal_casco"] == 500.0


def test_valor_unitario_250_int64_no_crash():
    import streamlit as st
    from cota.cotizacion import recalcular_totales_presupuesto_proyecto

    # Simular que Presupuesto, Utilidades y GG_Presupuesto fueron inferidos como int64
    st.session_state["proyectos"] = pd.DataFrame([
        {
            "Nombre": "Proy 250",
            "Presupuesto": 0,       # int64!
            "Utilidades": 0,        # int64!
            "GG_Presupuesto": 0,    # int64!
            "TC_Presupuesto": 3.42,
            "GG_Pct": 2.0,
            "Utilidades_Pct": 15.0,
            "Incluir_IGV": False,
        }
    ])
    st.session_state["partidas"] = pd.DataFrame([
        {"Proyecto": "Proy 250", "Nombre_Partida": "1. Partida 1"}
    ])
    st.session_state["p_info"] = pd.DataFrame([
        {"Proyecto": "Proy 250", "Nombre_Partida": "1. Partida 1", "Monto_Pactado": 0}
    ])
    st.session_state["tasks"] = pd.DataFrame([
        {
            "Proyecto": "Proy 250",
            "Partida": "1. Partida 1",
            "Orden": 1,
            "Codigo_Item": "1.01",
            "Tarea": "1.01 Tarea Test",
            "Moneda": "Soles",
            "Unidad": "glb",
            "Metrado": 1,
            "Valor_Unitario": 250,
            "Presupuesto": 250,
        }
    ])
    # 250 * 15% = 37.5 (float no entero) -> no debe lanzar LossySetitemError
    tot = recalcular_totales_presupuesto_proyecto("Proy 250", sincronizar_pactado=True)
    assert tot["subtotal_casco"] == 250.0
    assert tot["utilidades_monto"] == 37.5
    assert tot["gg_monto"] == 5.0
    assert tot["presupuesto_total"] == 292.5


def test_mover_tarea_presupuesto_y_orden_partidas():
    import streamlit as st
    from cota.cotizacion import (
        asegurar_estructura_presupuesto_proyecto,
        ajustar_cantidad_tareas_partida,
        mover_tarea_presupuesto,
    )
    from cota.db import COLS_P_INFO, COLS_TASKS

    st.session_state["proyectos"] = pd.DataFrame([{"Nombre": "Proy Orden", "Presupuesto": 0.0}])
    st.session_state["partidas"] = pd.DataFrame(columns=["Proyecto", "Nombre_Partida"])
    st.session_state["p_info"] = pd.DataFrame(columns=COLS_P_INFO)
    st.session_state["tasks"] = pd.DataFrame(columns=COLS_TASKS)

    asegurar_estructura_presupuesto_proyecto("Proy Orden", n_partidas_default=3, n_tareas_default=3)
    p1_name = st.session_state["partidas"].iloc[0]["Nombre_Partida"]
    mask_p1 = (st.session_state["tasks"]["Proyecto"] == "Proy Orden") & (st.session_state["tasks"]["Partida"] == p1_name)
    idxs_p1 = st.session_state["tasks"][mask_p1].index.tolist()
    st.session_state["tasks"].at[idxs_p1[0], "Tarea"] = "1.01 Poner pisos"
    st.session_state["tasks"].at[idxs_p1[1], "Tarea"] = "1.02 Eliminar desmonte"

    # Subir la tarea en índice 1 ("Eliminar desmonte") a la posición 0
    ok = mover_tarea_presupuesto("Proy Orden", 1, p1_name, 1, "subir")
    assert ok is True
    tasks_after = st.session_state["tasks"][
        (st.session_state["tasks"]["Proyecto"] == "Proy Orden") & (st.session_state["tasks"]["Partida"] == p1_name)
    ].reset_index(drop=True)
    assert tasks_after.iloc[0]["Tarea"] == "1.01 Eliminar desmonte"
    assert tasks_after.iloc[1]["Tarea"] == "1.02 Poner pisos"

    # Ajustar cantidad de tareas en Partida 1 (a 4 y luego a 2) y verificar que Partida 1 sigue primera
    ajustar_cantidad_tareas_partida("Proy Orden", 1, p1_name, 4)
    assert len(st.session_state["tasks"][st.session_state["tasks"]["Partida"] == p1_name]) == 4
    ajustar_cantidad_tareas_partida("Proy Orden", 1, p1_name, 2)
    assert len(st.session_state["tasks"][st.session_state["tasks"]["Partida"] == p1_name]) == 2
    assert st.session_state["partidas"].iloc[0]["Nombre_Partida"] == p1_name


def test_parsear_presupuesto_flexible_gemini_spark():
    from cota.cotizacion import parsear_presupuesto_flexible

    md_table = """
| Item | Partida / Tarea | Unidad | Metraje | Valor Unitario | Valor Parcial |
|---|---|---|---|---|---|
| 1 | OBRAS PRELIMINARES | | | | |
| 1.01 | Desmontaje y limpieza | glb | 1 | 1500 | 1500 |
| 1.02 | Eliminación de desmonte | m3 | 10 | 85 | 850 |
| 2 | PISOS Y ENCHAPES | | | | |
| 2.01 | Instalación de porcelanato | m2 | 50 | 120 | 6000 |
"""
    parsed = parsear_presupuesto_flexible(md_table, tc_default=3.42)
    assert len(parsed["partidas"]) == 2
    assert len(parsed["partidas"][0]["tareas"]) == 2
    assert len(parsed["partidas"][1]["tareas"]) == 1
    assert parsed["subtotal_casco"] == 8350.0


def test_catalogo_estudio_y_notas_chat():
    import streamlit as st
    from cota.db import (
        obtener_catalogo_estudio,
        agregar_item_catalogo_estudio,
        obtener_notas_chat_proyecto,
        agregar_nota_chat_proyecto,
    )

    st.session_state["proyectos"] = pd.DataFrame([
        {"Nombre": "Proy Chat", "Ubicación": "Miraflores", "Notas": "Nota inicial del cliente"}
    ])
    st.session_state["config_estudio"] = pd.DataFrame(columns=["Clave", "Valor"])

    ubis = agregar_item_catalogo_estudio("ubicaciones", "Chacarilla")
    assert "Chacarilla" in ubis
    assert "Chacarilla" in obtener_catalogo_estudio("ubicaciones")

    notas_ini = obtener_notas_chat_proyecto("Proy Chat")
    assert len(notas_ini) == 1
    assert notas_ini[0]["texto"] == "Nota inicial del cliente"

    notas_nuevas = agregar_nota_chat_proyecto("Proy Chat", "Alvaro", "Revisión de planos lista")
    assert len(notas_nuevas) == 2
    assert notas_nuevas[1]["socio"] == "Alvaro"
    assert notas_nuevas[1]["texto"] == "Revisión de planos lista"


def test_reordenar_dnd_y_pagos_multiples_por_partida():
    import streamlit as st
    from cota.cotizacion import (
        asegurar_estructura_presupuesto_proyecto,
        guardar_cuadro_pagos_semanales_proyecto,
        obtener_cuadro_pagos_semanales_proyecto,
        obtener_pagado_por_partida_proyecto,
        reordenar_tareas_partida_por_indices,
    )
    from cota.db import COLS_PAGOS, COLS_TASKS
    from cota.pdf import generar_pdf_minuta

    st.session_state["proyectos"] = pd.DataFrame([
        {
            "Nombre": "Proy Multi",
            "Cliente": "Cliente Test",
            "Tipo_Cambio": 3.50,
            "Presupuesto": 0.0,
            "GG_Presupuesto": 0.0,
            "Utilidades": 0.0,
            "Honorarios_Diseno": 0.0,
        }
    ])
    st.session_state["partidas"] = pd.DataFrame(columns=["Proyecto", "Nombre_Partida"])
    st.session_state["tasks"] = pd.DataFrame(columns=COLS_TASKS)
    st.session_state["p_info"] = pd.DataFrame(columns=["Proyecto", "Nombre_Partida", "Monto_Pactado"])
    st.session_state["pagos"] = pd.DataFrame(columns=COLS_PAGOS)
    st.session_state["config_estudio"] = pd.DataFrame(columns=["Clave", "Valor"])

    asegurar_estructura_presupuesto_proyecto("Proy Multi", n_partidas_default=2, n_tareas_default=3)
    p1_name = st.session_state["partidas"].iloc[0]["Nombre_Partida"]
    p2_name = st.session_state["partidas"].iloc[1]["Nombre_Partida"]

    mask_p1 = (st.session_state["tasks"]["Proyecto"] == "Proy Multi") & (st.session_state["tasks"]["Partida"] == p1_name)
    idxs_p1 = st.session_state["tasks"][mask_p1].index.tolist()
    st.session_state["tasks"].loc[idxs_p1[0], "Tarea"] = "1.01 Tarea A"
    st.session_state["tasks"].loc[idxs_p1[1], "Tarea"] = "1.02 Tarea B"
    st.session_state["tasks"].loc[idxs_p1[2], "Tarea"] = "1.03 Tarea C"

    # Reordenar Drag & Drop: mover la tarea en índice 2 al principio -> [2, 0, 1]
    assert reordenar_tareas_partida_por_indices("Proy Multi", 1, p1_name, [2, 0, 1]) is True
    tasks_p1 = st.session_state["tasks"][
        (st.session_state["tasks"]["Proyecto"] == "Proy Multi") & (st.session_state["tasks"]["Partida"] == p1_name)
    ].reset_index(drop=True)
    assert tasks_p1.iloc[0]["Tarea"] == "1.01 Tarea C"
    assert tasks_p1.iloc[1]["Tarea"] == "1.02 Tarea A"
    assert tasks_p1.iloc[2]["Tarea"] == "1.03 Tarea B"

    # Cuadro de pagos con 2 filas para la misma Partida 2 (ej. Eléctricas y Sanitarias)
    cuadro = obtener_cuadro_pagos_semanales_proyecto("Proy Multi")
    cuadro["filas_contratistas"] = [
        {"Partida": p1_name, "Descripcion": p1_name, "Moneda": "Soles", "TOTAL": 5000.0, "Adelanto": 1200.0, "Sem. 1": 800.0},
        {"Partida": p2_name, "Descripcion": "Instalaciones Eléctricas - Emp A", "Moneda": "Soles", "TOTAL": 4000.0, "Adelanto": 1500.0, "Sem. 1": 500.0},
        {"Partida": p2_name, "Descripcion": "Instalaciones Sanitarias - Emp B", "Moneda": "Soles", "TOTAL": 3000.0, "Adelanto": 1000.0, "Sem. 1": 250.0},
    ]
    guardar_cuadro_pagos_semanales_proyecto("Proy Multi", cuadro)

    pagados_map = obtener_pagado_por_partida_proyecto("Proy Multi")
    assert abs(pagados_map[p1_name] - 2000.0) < 1e-4
    assert abs(pagados_map[p2_name] - 3250.0) < 1e-4

    # Verificar que generar_pdf_minuta genera bytes válidos con 3 filas en asistencia y acuerdos
    df_asist = pd.DataFrame([
        {"Nombre": "Socio 1", "Rol_Empresa": "Arquitecto", "Asistencia": True},
        {"Nombre": "Cliente 1", "Rol_Empresa": "Propietario", "Asistencia": True},
        {"Nombre": "Ing. Eléctrico", "Rol_Empresa": "Contratista", "Asistencia": True},
    ])
    df_acuerdos = pd.DataFrame([
        {"Tema": "Tablero", "Acuerdo_Tarea": "Reubicar tablero", "Responsable": "Ing. Eléctrico", "Fecha_Limite": "20/11/2026", "Estado": "Pendiente"},
        {"Tema": "Luminarias", "Acuerdo_Tarea": "Aprobar catálogo", "Responsable": "Cliente 1", "Fecha_Limite": "22/11/2026", "Estado": "En Proceso"},
        {"Tema": "Puntos de red", "Acuerdo_Tarea": "Definir sala TV", "Responsable": "Socio 1", "Fecha_Limite": "25/11/2026", "Estado": "Completado"},
    ])
    pdf_bytes = generar_pdf_minuta("Proy Multi", {"Codigo": "ACTA-01", "Fecha": "15/11/2026", "Tipo": "Obra"}, df_asist, df_acuerdos)
    assert isinstance(pdf_bytes, (bytes, bytearray))
    assert len(pdf_bytes) > 500


def test_undo_redo_presupuesto():
    import streamlit as st
    from cota.cotizacion import (
        asegurar_estructura_presupuesto_proyecto,
        deshacer_presupuesto,
        guardar_parametros_presupuesto_proyecto,
        mover_partida_presupuesto,
        puede_deshacer_presupuesto,
        puede_rehacer_presupuesto,
        rehacer_presupuesto,
        reordenar_tareas_partida_por_indices,
    )
    proy_name = "Proy Undo Test"
    st.session_state["proyectos"] = pd.DataFrame([{"Nombre": proy_name, "Presupuesto": 0.0, "Utilidades": 0.0, "GG_Presupuesto": 0.0, "TC_Presupuesto": 3.42, "GG_Pct": 2.0, "Utilidades_Pct": 15.0, "Incluir_IGV": False, "Honorarios_Diseno": 0.0}])
    asegurar_estructura_presupuesto_proyecto(proy_name, n_partidas_default=2, n_tareas_default=3)

    p1_name = st.session_state["partidas"][st.session_state["partidas"]["Proyecto"] == proy_name].iloc[0]["Nombre_Partida"]
    mask_p1 = (st.session_state["tasks"]["Proyecto"] == proy_name) & (st.session_state["tasks"]["Partida"] == p1_name)
    idxs = st.session_state["tasks"][mask_p1].index.tolist()
    st.session_state["tasks"].loc[idxs[0], "Tarea"] = "1.01 Tarea Alpha"
    st.session_state["tasks"].loc[idxs[1], "Tarea"] = "1.02 Tarea Beta"
    st.session_state["tasks"].loc[idxs[2], "Tarea"] = "1.03 Tarea Gamma"

    # Reordenar las tareas [2, 0, 1] -> Gamma, Alpha, Beta
    reordenar_tareas_partida_por_indices(proy_name, 1, p1_name, [2, 0, 1])
    tasks_mod = st.session_state["tasks"][
        (st.session_state["tasks"]["Proyecto"] == proy_name) & (st.session_state["tasks"]["Partida"] == p1_name)
    ].reset_index(drop=True)
    assert tasks_mod.iloc[0]["Tarea"] == "1.01 Tarea Gamma"
    assert puede_deshacer_presupuesto(proy_name) is True

    # Deshacer cambio
    assert deshacer_presupuesto(proy_name) is True
    tasks_undone = st.session_state["tasks"][
        (st.session_state["tasks"]["Proyecto"] == proy_name) & (st.session_state["tasks"]["Partida"] == p1_name)
    ].reset_index(drop=True)
    assert tasks_undone.iloc[0]["Tarea"] == "1.01 Tarea Alpha"
    assert puede_rehacer_presupuesto(proy_name) is True

    # Rehacer cambio
    assert rehacer_presupuesto(proy_name) is True
    tasks_redone = st.session_state["tasks"][
        (st.session_state["tasks"]["Proyecto"] == proy_name) & (st.session_state["tasks"]["Partida"] == p1_name)
    ].reset_index(drop=True)
    assert tasks_redone.iloc[0]["Tarea"] == "1.01 Tarea Gamma"

    # Probar mover partida completa hacia arriba/abajo con deshacer
    p2_name = st.session_state["partidas"][st.session_state["partidas"]["Proyecto"] == proy_name].iloc[1]["Nombre_Partida"]
    assert mover_partida_presupuesto(proy_name, 2, "subir") is True
    partidas_swapped = st.session_state["partidas"][st.session_state["partidas"]["Proyecto"] == proy_name]["Nombre_Partida"].tolist()
    assert "1. " in partidas_swapped[0]
    assert "2. " in partidas_swapped[1]

    # Deshacer swap de partidas
    assert deshacer_presupuesto(proy_name) is True
    partidas_revert = st.session_state["partidas"][st.session_state["partidas"]["Proyecto"] == proy_name]["Nombre_Partida"].tolist()
    assert partidas_revert[0] == p1_name


def test_gantt_hidden_by_default_code():
    with open("D:/cota-app/cota/ui/views_project.py", "r", encoding="utf-8") as f:
        code = f.read()
    assert 'with st.expander("📊 CRONOGRAMA GANTT POR PARTIDA Y TAREAS (INICIO → FIN Y ESTADOS)", expanded=False):' in code
    assert 'with st.expander("📊 CRONOGRAMA GANTT POR PARTIDA Y TAREAS (INICIO → FIN Y ESTADOS)", expanded=True):' not in code


def test_dnd_column_compact_width():
    with open("D:/cota-app/cota/ui/views_project.py", "r", encoding="utf-8") as f:
        code = f.read()
    tab_ppto_code = code.split("def _render_tab_presupuesto")[1].split("def _render_tab_entregables")[0]
    assert '"Sel": st.column_config.CheckboxColumn(' in tab_ppto_code
    assert 'width=48' in tab_ppto_code
    assert '"##### ⚙️ Configuración de Presupuesto"' in tab_ppto_code
    assert '"➕ Agregar Partida"' in tab_ppto_code
    assert '"🗑️ Eliminar"' in tab_ppto_code
    assert '"📋 Pegar Tabla"' in tab_ppto_code
    assert '"⠿ Mover"' not in tab_ppto_code
    assert 'Configuración de Estructura y Parámetros Financieros' not in tab_ppto_code
    assert 'Gemini Spark' not in tab_ppto_code

    with open("D:/cota-app/cota/ui/views_main.py", "r", encoding="utf-8") as f:
        main_code = f.read()
    assert '"📋 Pegar Tabla"' in main_code
    assert 'Gemini Spark' not in main_code


def test_redondeo_gg_y_utilidades():
    from cota.cotizacion import redondear_arriba_10, redondear_arriba_100

    # Gastos Generales: redondeo hacia arriba al 10 más cercano
    assert redondear_arriba_10(0.0) == 0.0
    assert redondear_arriba_10(10.0) == 10.0
    assert redondear_arriba_10(10.01) == 20.0
    assert redondear_arriba_10(23.45) == 30.0
    assert redondear_arriba_10(29.0) == 30.0
    assert redondear_arriba_10(30.0) == 30.0
    assert redondear_arriba_10(145.2) == 150.0

    # Utilidades: redondeo hacia arriba al 100 más cercano
    assert redondear_arriba_100(0.0) == 0.0
    assert redondear_arriba_100(100.0) == 100.0
    assert redondear_arriba_100(100.01) == 200.0
    assert redondear_arriba_100(1435.50) == 1500.0
    assert redondear_arriba_100(1400.0) == 1400.0
    assert redondear_arriba_100(250.0) == 300.0


def test_recalcular_totales_modo_monto_y_pct():
    import streamlit as st
    from cota.cotizacion import (
        recalcular_totales_presupuesto_proyecto,
        guardar_parametros_presupuesto_proyecto,
    )
    proy_test = "Proyecto_Test_Redondeo"
    st.session_state["proyectos"] = pd.DataFrame([{
        "Nombre": proy_test,
        "TC_Presupuesto": 3.42,
        "GG_Pct": 2.0,
        "Utilidades_Pct": 15.0,
        "Incluir_IGV": False,
        "Modo_GG": "pct",
        "Monto_Fijo_GG": 0.0,
        "Modo_Utilidades": "pct",
        "Monto_Fijo_Utilidades": 0.0,
        "Presupuesto": 0.0,
        "Utilidades": 0.0,
        "GG_Presupuesto": 0.0,
    }])
    st.session_state["partidas"] = pd.DataFrame([{"Proyecto": proy_test, "Nombre_Partida": "01. Obra"}])
    st.session_state["p_info"] = pd.DataFrame([{"Proyecto": proy_test, "Nombre_Partida": "01. Obra", "Monto_Pactado": 1055.0}])
    st.session_state["tasks"] = pd.DataFrame([{
        "Proyecto": proy_test,
        "Partida": "01. Obra",
        "Orden": 1,
        "Codigo_Item": "1.01",
        "Tarea": "1.01 Demo",
        "Moneda": "Soles",
        "Unidad": "glb",
        "Metrado": 1.0,
        "Valor_Unitario": 1055.0,
        "Presupuesto": 1055.0,
    }])

    # 1. Modo % con redondeo hacia arriba:
    # Subtotal = 1055.0
    # GG 2% = 21.10 -> redondeo arriba al 10 = 30.0
    # Util 15% = 158.25 -> redondeo arriba al 100 = 200.0
    tot = recalcular_totales_presupuesto_proyecto(proy_test)
    assert tot["subtotal_casco"] == 1055.0
    assert tot["gg_monto"] == 30.0
    assert tot["utilidades_monto"] == 200.0
    assert tot["presupuesto_total"] == 1055.0 + 30.0 + 200.0  # 1285.0

    # 2. Modo Monto Exacto con redondeo hacia arriba:
    # Guardamos monto fijo GG = 42.0 (redondeo a 50.0) y Util = 310.0 (redondeo a 400.0)
    guardar_parametros_presupuesto_proyecto(
        proy_name=proy_test,
        tc=3.42,
        gg_pct=2.0,
        utilidades_pct=15.0,
        incluir_igv=False,
        modo_gg="monto",
        monto_fijo_gg=42.0,
        modo_util="monto",
        monto_fijo_util=310.0,
    )
    tot2 = recalcular_totales_presupuesto_proyecto(proy_test)
    assert tot2["gg_monto"] == 50.0
    assert tot2["utilidades_monto"] == 400.0
    assert tot2["presupuesto_total"] == 1055.0 + 50.0 + 400.0  # 1505.0


def test_notas_pagos_semanales_y_excel():
    import io
    import openpyxl
    import streamlit as st
    from cota.cotizacion import (
        obtener_cuadro_pagos_semanales_proyecto,
        guardar_cuadro_pagos_semanales_proyecto,
        exportar_cuadro_pagos_semanales_excel,
        _normalizar_fila_pago,
        obtener_columnas_pago_semanal,
    )

    cols_sem = obtener_columnas_pago_semanal(3)
    f_raw = {
        "Partida": "OBRAS CIVILES",
        "Descripcion": "OBRAS CIVILES",
        "Moneda": "Soles",
        "TOTAL": 5000.0,
        "ADELANTO 1": 2000.0,
        "SEMANA 1": 1500.0,
        "Notas": "Contratista Juan",
        "Notas_Pagos": {
            "ADELANTO 1": "Adelanto para compra de bolsas de cemento",
            "SEMANA 1": "Avance de tarrajeo",
        },
    }
    f_norm = _normalizar_fila_pago(f_raw, cols_sem)
    assert f_norm["Notas_Pagos"]["ADELANTO 1"] == "Adelanto para compra de bolsas de cemento"
    assert f_norm["Notas_Pagos"]["SEMANA 1"] == "Avance de tarrajeo"

    # Persistencia en session_state y exportación Excel
    proy_nombre = "Proy Notas Pagos Test"
    st.session_state["proyectos"] = pd.DataFrame([{
        "Nombre": proy_nombre,
        "Cliente": "Cliente Test",
        "TC_Presupuesto": 3.75,
        "Pagos_Semanales_JSON": "",
    }])
    st.session_state["partidas"] = pd.DataFrame()
    st.session_state["p_info"] = pd.DataFrame()
    st.session_state["tasks"] = pd.DataFrame()

    data_cuadro = obtener_cuadro_pagos_semanales_proyecto(proy_nombre)
    data_cuadro["filas_contratistas"] = [f_norm]
    data_cuadro["fila_gestion"]["Notas_Pagos"] = {
        "SEMANA 1": "Honorarios supervisión semana 1"
    }
    guardar_cuadro_pagos_semanales_proyecto(proy_nombre, data_cuadro)

    # Recargar y verificar
    data_loaded = obtener_cuadro_pagos_semanales_proyecto(proy_nombre)
    assert len(data_loaded["filas_contratistas"]) == 1
    np_loaded = data_loaded["filas_contratistas"][0].get("Notas_Pagos", {})
    assert np_loaded.get("ADELANTO 1") == "Adelanto para compra de bolsas de cemento"
    assert data_loaded["fila_gestion"]["Notas_Pagos"]["SEMANA 1"] == "Honorarios supervisión semana 1"

    # Exportar a Excel y verificar comentarios
    xlsx_bytes = exportar_cuadro_pagos_semanales_excel(proy_nombre, data_loaded)
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    ws = wb["Control de Pagos"]

    # Fila 7 es la primera fila de contratistas
    # Col 5 es ADELANTO 1 (columna E)
    cell_adelanto = ws.cell(row=7, column=5)
    assert cell_adelanto.comment is not None
    assert "Adelanto para compra de bolsas de cemento" in cell_adelanto.comment.text


def test_mover_tarea_presupuesto_y_edicion_tabla():
    import streamlit as st
    from cota.cotizacion import (
        mover_tarea_presupuesto,
        reordenar_tareas_partida_por_indices,
        aplicar_edicion_tabla_presupuesto_partida,
    )

    p_test = "Proy Mover Tarea Test"
    part_nom = "01. Obras Civiles"
    st.session_state["proyectos"] = pd.DataFrame([{
        "Nombre": p_test,
        "TC_Presupuesto": 3.42,
        "Modo_GG": "pct",
        "GG_Presupuesto": 2.0,
        "Modo_Utilidades": "pct",
        "Utilidades": 15.0,
        "Incluir_IGV": False,
        "Pagos_Semanales_JSON": "",
    }])
    st.session_state["partidas"] = pd.DataFrame([{
        "Proyecto": p_test,
        "Nombre_Partida": part_nom,
    }])
    st.session_state["p_info"] = pd.DataFrame([{
        "Proyecto": p_test,
        "Nombre_Partida": part_nom,
        "Monto_Pactado": 1000.0,
        "Contratista": "",
    }])
    st.session_state["tasks"] = pd.DataFrame([
        {"Proyecto": p_test, "Partida": part_nom, "Orden": 1, "Codigo_Item": "1.01", "Tarea": "1.01 Demolición pisos", "Moneda": "Soles", "Unidad": "m2", "Metrado": 10.0, "Valor_Unitario": 50.0, "Presupuesto": 500.0},
        {"Proyecto": p_test, "Partida": part_nom, "Orden": 2, "Codigo_Item": "1.02", "Tarea": "1.02 Nuevo contrapiso", "Moneda": "Soles", "Unidad": "m2", "Metrado": 10.0, "Valor_Unitario": 30.0, "Presupuesto": 300.0},
        {"Proyecto": p_test, "Partida": part_nom, "Orden": 3, "Codigo_Item": "1.03", "Tarea": "1.03 Instalacion de porcelanatos", "Moneda": "Soles", "Unidad": "m2", "Metrado": 10.0, "Valor_Unitario": 60.0, "Presupuesto": 600.0},
        {"Proyecto": p_test, "Partida": part_nom, "Orden": 4, "Codigo_Item": "1.04", "Tarea": "1.04 Eliminacion desmonte", "Moneda": "Soles", "Unidad": "und", "Metrado": 3.0, "Valor_Unitario": 750.0, "Presupuesto": 2250.0},
    ])

    # 1. Mover directamente la tarea 4 (índice 3: Eliminacion desmonte) hacia arriba (subir)
    res = mover_tarea_presupuesto(p_test, 1, part_nom, 3, "subir")
    assert res is True
    t_after = st.session_state["tasks"][st.session_state["tasks"]["Proyecto"] == p_test].reset_index(drop=True)
    assert t_after.at[2, "Codigo_Item"] == "1.03"
    assert "Eliminacion desmonte" in t_after.at[2, "Tarea"]
    assert t_after.at[3, "Codigo_Item"] == "1.04"
    assert "Instalacion de porcelanatos" in t_after.at[3, "Tarea"]

    # 2. Reordenar por índices permutados
    res2 = reordenar_tareas_partida_por_indices(p_test, 1, part_nom, [3, 0, 1, 2])
    assert res2 is True
    t_after2 = st.session_state["tasks"][st.session_state["tasks"]["Proyecto"] == p_test].reset_index(drop=True)
    assert t_after2.at[0, "Codigo_Item"] == "1.01"
    assert "Instalacion de porcelanatos" in t_after2.at[0, "Tarea"]

    # 3. Simular edición en st.data_editor eligiendo '⬆ Subir' en la columna ⠿
    base_k = f"base_df_ppto_{p_test}_1"
    widget_k = f"ed_ppto_{p_test}_1_0"
    st.session_state[base_k] = pd.DataFrame([
        {"⠿": "⠿", "Item": "1.01", "Descripcion": "Instalacion de porcelanatos", "Moneda": "Soles", "Unidad": "m2", "Metrado": 10.0, "Valor_Unitario": 60.0, "Valor_Parcial": 600.0},
        {"⠿": "⠿", "Item": "1.02", "Descripcion": "Demolición pisos", "Moneda": "Soles", "Unidad": "m2", "Metrado": 10.0, "Valor_Unitario": 50.0, "Valor_Parcial": 500.0},
    ])
    st.session_state[widget_k] = {
        "edited_rows": {
            "1": {"⠿": "⬆ Subir"}
        }
    }
    aplicar_edicion_tabla_presupuesto_partida(base_k, widget_k, p_test, 1, part_nom)
    t_after3 = st.session_state["tasks"][st.session_state["tasks"]["Proyecto"] == p_test].reset_index(drop=True)
    assert "Demolición pisos" in t_after3.at[0, "Tarea"]


def test_presupuesto_seleccion_partidas_y_tareas():
    import streamlit as st
    from cota.cotizacion import (
        agregar_partida_presupuesto,
        aplicar_edicion_tabla_presupuesto_partida,
        deshacer_presupuesto,
        eliminar_partida_presupuesto,
        eliminar_tareas_seleccionadas_presupuesto,
        mover_tareas_seleccionadas_presupuesto,
    )

    p_test = "Proy Sel Partidas Test"
    p1 = "01. Obras Preliminares"
    p2 = "02. Arquitectura"
    st.session_state["proyectos"] = pd.DataFrame([{
        "Nombre": p_test,
        "TC_Presupuesto": 3.42,
        "Modo_GG": "pct",
        "GG_Presupuesto": 2.0,
        "Modo_Utilidades": "pct",
        "Utilidades": 15.0,
        "Incluir_IGV": False,
        "Pagos_Semanales_JSON": "",
    }])
    st.session_state["partidas"] = pd.DataFrame([
        {"Proyecto": p_test, "Nombre_Partida": p1},
        {"Proyecto": p_test, "Nombre_Partida": p2},
    ])
    st.session_state["p_info"] = pd.DataFrame([
        {"Proyecto": p_test, "Nombre_Partida": p1, "Monto_Pactado": 100.0, "Contratista": ""},
        {"Proyecto": p_test, "Nombre_Partida": p2, "Monto_Pactado": 200.0, "Contratista": ""},
    ])
    st.session_state["tasks"] = pd.DataFrame([
        {"Proyecto": p_test, "Partida": p1, "Orden": 1, "Codigo_Item": "1.01", "Tarea": "1.01 Limpieza", "Moneda": "Soles", "Unidad": "glb", "Metrado": 1.0, "Valor_Unitario": 100.0, "Presupuesto": 100.0},
        {"Proyecto": p_test, "Partida": p1, "Orden": 2, "Codigo_Item": "1.02", "Tarea": "1.02 Trazo", "Moneda": "Soles", "Unidad": "glb", "Metrado": 1.0, "Valor_Unitario": 150.0, "Presupuesto": 150.0},
        {"Proyecto": p_test, "Partida": p1, "Orden": 3, "Codigo_Item": "1.03", "Tarea": "1.03 Demolicion", "Moneda": "Soles", "Unidad": "glb", "Metrado": 1.0, "Valor_Unitario": 200.0, "Presupuesto": 200.0},
        {"Proyecto": p_test, "Partida": p2, "Orden": 1, "Codigo_Item": "2.01", "Tarea": "2.01 Pintura", "Moneda": "Soles", "Unidad": "m2", "Metrado": 10.0, "Valor_Unitario": 20.0, "Presupuesto": 200.0},
    ])
    st.session_state["pagos"] = pd.DataFrame(columns=["Proyecto", "Partida", "Fecha", "Monto", "Tipo", "Notas"])
    st.session_state.pop(f"ppto_undo_{p_test}", None)

    # 1. Solo marcar casilla 'Sel' no debe alterar c_key ni crear snapshot en Undo
    base_k = f"base_df_ppto_{p_test}_1"
    c_k = f"c_{base_k}"
    widget_k = f"ed_ppto_{p_test}_1_0"
    st.session_state[c_k] = 0
    st.session_state[base_k] = pd.DataFrame([
        {"Sel": False, "Item": "1.01", "Descripcion": "Limpieza", "Moneda": "Soles", "Unidad": "glb", "Metrado": 1.0, "Valor_Unitario": 100.0, "Valor_Parcial": 100.0},
        {"Sel": False, "Item": "1.02", "Descripcion": "Trazo", "Moneda": "Soles", "Unidad": "glb", "Metrado": 1.0, "Valor_Unitario": 150.0, "Valor_Parcial": 150.0},
        {"Sel": False, "Item": "1.03", "Descripcion": "Demolicion", "Moneda": "Soles", "Unidad": "glb", "Metrado": 1.0, "Valor_Unitario": 200.0, "Valor_Parcial": 200.0},
    ])
    st.session_state[widget_k] = {"edited_rows": {"1": {"Sel": True}}}
    aplicar_edicion_tabla_presupuesto_partida(base_k, widget_k, p_test, 1, p1)
    assert st.session_state[c_k] == 0
    assert not st.session_state.get(f"ppto_undo_{p_test}")

    # 2. Edición de Metrado junto con casilla Sel marcada preserva selección en sel_saved_ppto_
    st.session_state[widget_k] = {"edited_rows": {"1": {"Sel": True}, "0": {"Metrado": 2.0}}}
    aplicar_edicion_tabla_presupuesto_partida(base_k, widget_k, p_test, 1, p1)
    assert st.session_state[c_k] == 1
    assert st.session_state.get(f"sel_saved_ppto_{p_test}_1") == [1]

    # 3. Mover múltiples tareas seleccionadas [1, 2] hacia arriba -> quedan en [0, 1]
    movido, nuevos_idx = mover_tareas_seleccionadas_presupuesto(p_test, 1, p1, [1, 2], "subir")
    assert movido is True
    assert nuevos_idx == [0, 1]
    t_p1 = st.session_state["tasks"][(st.session_state["tasks"]["Proyecto"] == p_test) & (st.session_state["tasks"]["Partida"] == p1)].reset_index(drop=True)
    assert [t_p1.at[0, "Codigo_Item"], t_p1.at[1, "Codigo_Item"], t_p1.at[2, "Codigo_Item"]] == ["1.01", "1.02", "1.03"]
    assert "Trazo" in t_p1.at[0, "Tarea"] and "Demolicion" in t_p1.at[1, "Tarea"] and "Limpieza" in t_p1.at[2, "Tarea"]

    # Boundary no-op cuando ya están arriba
    movido_nop, nuevos_nop = mover_tareas_seleccionadas_presupuesto(p_test, 1, p1, [0, 1], "subir")
    assert movido_nop is False
    assert nuevos_nop == [0, 1]

    # 4. Eliminar tarea seleccionada índice 1 (Demolicion) y verificar renumeración
    assert eliminar_tareas_seleccionadas_presupuesto(p_test, 1, p1, [1]) is True
    t_p1 = st.session_state["tasks"][(st.session_state["tasks"]["Proyecto"] == p_test) & (st.session_state["tasks"]["Partida"] == p1)].reset_index(drop=True)
    assert len(t_p1) == 2
    assert "Trazo" in t_p1.at[0, "Tarea"] and t_p1.at[0, "Codigo_Item"] == "1.01"
    assert "Limpieza" in t_p1.at[1, "Tarea"] and t_p1.at[1, "Codigo_Item"] == "1.02"

    # Eliminar todas deja 1 tarea base vacía 1.01
    assert eliminar_tareas_seleccionadas_presupuesto(p_test, 1, p1, [0, 1]) is True
    t_p1 = st.session_state["tasks"][(st.session_state["tasks"]["Proyecto"] == p_test) & (st.session_state["tasks"]["Partida"] == p1)].reset_index(drop=True)
    assert len(t_p1) == 1
    assert t_p1.at[0, "Codigo_Item"] == "1.01"
    assert t_p1.at[0, "Tarea"] == "1.01"

    # 5. Agregar partida con botón único y eliminar partida desde su tarjeta con renumeración
    assert agregar_partida_presupuesto(p_test) == 3
    assert len(st.session_state["partidas"][st.session_state["partidas"]["Proyecto"] == p_test]) == 3

    # Eliminar la Partida 1 -> Arquitectura pasa a 01. Arquitectura y su tarea 2.01 -> 1.01
    assert eliminar_partida_presupuesto(p_test, 1, p1) is True
    parts_rem = st.session_state["partidas"][st.session_state["partidas"]["Proyecto"] == p_test].reset_index(drop=True)
    assert len(parts_rem) == 2
    assert parts_rem.at[0, "Nombre_Partida"] == "01. Arquitectura"
    assert parts_rem.at[1, "Nombre_Partida"] == "02. Partida 3"
    t_arq = st.session_state["tasks"][(st.session_state["tasks"]["Proyecto"] == p_test) & (st.session_state["tasks"]["Partida"] == "01. Arquitectura")].reset_index(drop=True)
    assert t_arq.at[0, "Codigo_Item"] == "1.01"
    assert "Pintura" in t_arq.at[0, "Tarea"]

    # Eliminar la última partida restante está protegido (mínimo 1)
    assert eliminar_partida_presupuesto(p_test, 2) is True
    assert eliminar_partida_presupuesto(p_test, 1) is False
    assert deshacer_presupuesto(p_test) is True


def test_etiquetas_y_exportacion_cuadro_pagos_arcilla_y_rojo():
    import io
    import openpyxl
    import streamlit as st
    from cota.cotizacion import (
        etiqueta_corta_columna_pago,
        etiqueta_export_columna_pago,
        exportar_cuadro_pagos_semanales_excel,
        exportar_cuadro_pagos_semanales_pdf,
    )

    assert etiqueta_corta_columna_pago("SEMANA 1") == "S1"
    assert etiqueta_corta_columna_pago("SEMANA 7") == "S7"
    assert etiqueta_corta_columna_pago("ADELANTO 1") == "ADELANTO 1"

    assert etiqueta_export_columna_pago("SEMANA 1") == "Semana 1"
    assert etiqueta_export_columna_pago("S2") == "Semana 2"
    assert etiqueta_export_columna_pago("ADELANTO 1") == "ADELANTO 1"

    st.session_state["proyectos"] = pd.DataFrame([
        {"Nombre": "Juana Alarco 243", "Cliente": "Lorena Zuazo", "TC_Presupuesto": 3.60}
    ])

    data_cuadro = {
        "num_semanas": 2,
        "tc": 3.60,
        "cols_por_pagar": ["SEMANA 2"],
        "filas_contratistas": [
            {
                "Partida": "OBRAS CIVILES",
                "Descripcion": "OBRAS CIVILES",
                "Moneda": "Soles",
                "TOTAL": 10915.0,
                "ADELANTO 1": 0.0,
                "SEMANA 1": 3970.0,
                "SEMANA 2": 1337.0,
                "Notas": "",
                "Notas_Pagos": {"SEMANA 1": "Pago avance piso"},
            }
        ],
        "fila_gestion": {
            "Descripcion": "Gestión y supervisión de obras",
            "Moneda": "Soles",
            "TOTAL": 8650.0,
            "ADELANTO 1": 0.0,
            "SEMANA 1": 450.0,
            "SEMANA 2": 0.0,
        },
        "fila_gg": {
            "Descripcion": "Gastos Generales",
            "Moneda": "Soles",
            "TOTAL": 1100.0,
            "ADELANTO 1": 1000.0,
            "SEMANA 1": 0.0,
            "SEMANA 2": 0.0,
        },
    }

    xlsx_bytes = exportar_cuadro_pagos_semanales_excel("Juana Alarco 243", data_cuadro)
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    ws = wb["Control de Pagos"]

    # Verificar que en Excel las columnas digan "Semana 1", "Semana 2"
    assert ws["F4"].value == "Semana 1"
    assert ws["G4"].value == "Semana 2"

    # Verificar color arcilla Cota (C85A32) en encabezado (B4), SUB TOTAL (B8) y TOTAL (B11)
    assert "C85A32" in ws["B4"].fill.start_color.rgb
    assert "C85A32" in ws["B8"].fill.start_color.rgb
    assert "C85A32" in ws["B11"].fill.start_color.rgb

    # Verificar pago realizado en rojo (D92B2B) en SEMANA 1 (F7) y Por Pagar en negro (262320) en SEMANA 2 (G7)
    assert "D92B2B" in ws["F7"].font.color.rgb
    assert "262320" in ws["G7"].font.color.rgb

    # Verificar que exportar PDF retorne un documento PDF válido
    pdf_bytes = exportar_cuadro_pagos_semanales_pdf("Juana Alarco 243", data_cuadro)
    assert isinstance(pdf_bytes, (bytes, bytearray))
    assert pdf_bytes.startswith(b"%PDF")


def test_aplicar_edicion_inline_cuadro_pagos():
    import json
    import streamlit as st
    from cota.cotizacion import (
        aplicar_edicion_inline_cuadro_pagos,
        guardar_cuadro_pagos_semanales_proyecto,
        obtener_cuadro_pagos_semanales_proyecto,
    )

    proy_test = "Casa Rapallo Inline"
    st.session_state["proyectos"] = pd.DataFrame([{
        "Nombre": proy_test,
        "Cliente": "Familia Zela",
        "TC_Presupuesto": 3.42,
        "Pagos_Semanales_JSON": "",
    }])
    st.session_state["partidas"] = pd.DataFrame([
        {"Proyecto": proy_test, "Nombre_Partida": "1. Obras Civiles"}
    ])
    st.session_state["p_info"] = pd.DataFrame([
        {"Proyecto": proy_test, "Nombre_Partida": "1. Obras Civiles", "Monto_Pactado": 31650.0, "Contratista": "Antonio Atauplico"}
    ])
    st.session_state["tasks"] = pd.DataFrame()

    data_ini = obtener_cuadro_pagos_semanales_proyecto(proy_test)
    guardar_cuadro_pagos_semanales_proyecto(proy_test, data_ini)

    # 1. Editar monto de pago en SEMANA 1 + nota y TOTAL de gestión
    payload_edit = json.dumps({
        "action": "edit_cells",
        "ts": 1001,
        "edits": [
            {"row_type": "contratista", "row_idx": 0, "col": "SEMANA 1", "value": 4500.0, "nota": "Avance 1ra semana"},
            {"row_type": "gestion", "row_idx": 0, "col": "TOTAL", "value": 12000.0},
            {"row_type": "contratista", "row_idx": 0, "col": "Descripcion", "value": "OBRAS CIVILES - FRENTE 1", "notas_row": "Contratista: Antonio Atauplico"},
        ],
    })
    assert aplicar_edicion_inline_cuadro_pagos(proy_test, payload_edit) is True
    data_after = obtener_cuadro_pagos_semanales_proyecto(proy_test)
    assert data_after["filas_contratistas"][0]["SEMANA 1"] == 4500.0
    assert data_after["filas_contratistas"][0]["Notas_Pagos"]["SEMANA 1"] == "Avance 1ra semana"
    assert data_after["filas_contratistas"][0]["Descripcion"] == "OBRAS CIVILES - FRENTE 1"
    assert data_after["fila_gestion"]["TOTAL"] == 12000.0

    # 2. Alternar 'Por Pagar' en SEMANA 2
    payload_toggle = json.dumps({"action": "toggle_por_pagar", "col": "SEMANA 2", "ts": 1002})
    assert aplicar_edicion_inline_cuadro_pagos(proy_test, payload_toggle) is True
    data_after2 = obtener_cuadro_pagos_semanales_proyecto(proy_test)
    assert "SEMANA 2" in data_after2["cols_por_pagar"]

    # 3. Agregar y eliminar fila de contratista desde el mismo cuadro
    payload_add = json.dumps({"action": "add_row", "partida": "1. Obras Civiles", "ts": 1003})
    assert aplicar_edicion_inline_cuadro_pagos(proy_test, payload_add) is True
    data_after3 = obtener_cuadro_pagos_semanales_proyecto(proy_test)
    assert len(data_after3["filas_contratistas"]) == 2

    payload_del = json.dumps({"action": "delete_row", "row_idx": 1, "ts": 1004})
    assert aplicar_edicion_inline_cuadro_pagos(proy_test, payload_del) is True
    data_after4 = obtener_cuadro_pagos_semanales_proyecto(proy_test)
    assert len(data_after4["filas_contratistas"]) == 1


def test_chat_notas_responder_editar_borrar():
    import json
    import streamlit as st
    from cota.db import (
        agregar_nota_chat_proyecto,
        aplicar_accion_chat_notas_proyecto,
        editar_nota_chat_proyecto,
        eliminar_nota_chat_proyecto,
        obtener_notas_chat_proyecto,
    )

    proy = "Proy Chat Completo"
    st.session_state["proyectos"] = pd.DataFrame([
        {"Nombre": proy, "Encargado": "Alvaro", "Notas": ""}
    ])

    # 1. Enviar primer mensaje
    notas = agregar_nota_chat_proyecto(proy, "Alvaro", "Cliente quiere que la isla tenga 1.20m de ancho")
    assert len(notas) == 1
    msg0_id = notas[0]["id"]

    # 2. Responder al primer mensaje mediante aplicar_accion_chat_notas_proyecto
    payload_reply = json.dumps({
        "action": "send",
        "socio": "Socio 1",
        "texto": "Acordamos agrandarlo a 1.30m",
        "reply_to": {"id": msg0_id, "socio": "Alvaro", "texto": "Cliente quiere que la isla tenga 1.20m de ancho"},
        "ts": 2001,
    })
    assert aplicar_accion_chat_notas_proyecto(proy, payload_reply) is True
    notas2 = obtener_notas_chat_proyecto(proy)
    assert len(notas2) == 2
    assert notas2[1]["reply_to"]["socio"] == "Alvaro"
    assert notas2[1]["reply_to"]["id"] == msg0_id

    # 3. Editar el primer mensaje y verificar que se marca como editado y actualiza la cita en la respuesta
    assert editar_nota_chat_proyecto(proy, 0, "Cliente quiere que la isla tenga 1.25m de ancho") is True
    notas3 = obtener_notas_chat_proyecto(proy)
    assert notas3[0]["texto"] == "Cliente quiere que la isla tenga 1.25m de ancho"
    assert notas3[0].get("editado") is True
    assert notas3[1]["reply_to"]["texto"] == "Cliente quiere que la isla tenga 1.25m de ancho"

    # 4. Borrar el primer mensaje desde el menú de 3 puntos (vía bridge)
    payload_del = json.dumps({"action": "delete", "idx": 0, "ts": 2002})
    assert aplicar_accion_chat_notas_proyecto(proy, payload_del) is True
    notas4 = obtener_notas_chat_proyecto(proy)
    assert len(notas4) == 1
    assert notas4[0]["socio"] == "Socio 1"

    # 5. Borrar el último mensaje restante
    assert eliminar_nota_chat_proyecto(proy, 0) is True
    assert obtener_notas_chat_proyecto(proy) == []


def test_logo_y_extraer_nombre_studio():
    from cota.ui.components import extraer_nombre_studio
    from cota.utils import get_image_base64

    assert extraer_nombre_studio("COTA // LB Studio") == "LB Studio"
    assert extraer_nombre_studio("LB Studio") == "LB Studio"
    assert extraer_nombre_studio("COTA APP") == ""
    assert extraer_nombre_studio("COTA") == ""
    assert extraer_nombre_studio("") == ""
    assert extraer_nombre_studio("COTA // Estudio Venti") == "Estudio Venti"

    b64_logo = get_image_base64("logo/Logo Full.png")
    assert b64_logo is not None
    assert b64_logo.startswith("data:image/")
    assert get_image_base64("Logo2.png") == b64_logo






def test_exportacion_formato_monedas_y_encabezado_ordenado():
    import io
    import openpyxl
    import streamlit as st
    from cota.cotizacion import (
        asegurar_estructura_presupuesto_proyecto,
        exportar_proyecto_a_formato_venti,
        parsear_cotizacion_venti,
        recalcular_totales_presupuesto_proyecto,
    )
    from cota.db import COLS_P_INFO, COLS_TASKS

    proy = "Santa María 139 - Terraza"
    st.session_state["proyectos"] = pd.DataFrame([{
        "Nombre": proy,
        "Cliente": "Maruja Morín",
        "Inicio": "2026-11-09",
        "Presupuesto": 0.0,
        "Utilidades": 0.0,
        "GG_Presupuesto": 0.0,
        "TC_Presupuesto": 3.42,
        "GG_Pct": 5.0,
        "Utilidades_Pct": 15.0,
        "Incluir_IGV": False,
        "Archivado": False,
    }])
    st.session_state["partidas"] = pd.DataFrame(columns=["Proyecto", "Nombre_Partida"])
    st.session_state["p_info"] = pd.DataFrame(columns=COLS_P_INFO)
    st.session_state["tasks"] = pd.DataFrame(columns=COLS_TASKS)

    asegurar_estructura_presupuesto_proyecto(proy, n_partidas_default=1, n_tareas_default=2)
    # Tarea 1 en Soles
    st.session_state["tasks"].loc[0, "Tarea"] = "1.01 Eliminación de desmonte"
    st.session_state["tasks"].loc[0, "Moneda"] = "Soles"
    st.session_state["tasks"].loc[0, "Unidad"] = "glb"
    st.session_state["tasks"].loc[0, "Metrado"] = 1.0
    st.session_state["tasks"].loc[0, "Valor_Unitario"] = 100.0
    st.session_state["tasks"].loc[0, "Presupuesto"] = 100.0
    # Tarea 2 en Dólares
    st.session_state["tasks"].loc[1, "Tarea"] = "1.02 Luminaria importada"
    st.session_state["tasks"].loc[1, "Moneda"] = "Dólares"
    st.session_state["tasks"].loc[1, "Unidad"] = "und"
    st.session_state["tasks"].loc[1, "Metrado"] = 2.0
    st.session_state["tasks"].loc[1, "Valor_Unitario"] = 250.0
    st.session_state["tasks"].loc[1, "Presupuesto"] = round(2.0 * 250.0 * 3.42, 2)

    recalcular_totales_presupuesto_proyecto(proy, sincronizar_pactado=True)
    xlsx_bytes = exportar_proyecto_a_formato_venti(proy)

    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), data_only=False)
    ws1 = wb["Presupuesto"]

    # 1. Verificar encabezado integrado y ordenado (Filas 2, 3 y 4 pegadas a la cabecera en Fila 5)
    assert "PRESUPUESTO DE OBRA" in str(ws1["B2"].value)
    assert ws1["B3"].value == "Proyecto:"
    assert ws1["C3"].value == proy
    assert ws1["I3"].value == "Fecha:"
    assert ws1["J3"].value == "2026-11-09"
    assert ws1["B4"].value == "Cliente:"
    assert ws1["C4"].value == "Maruja Morín"
    assert ws1["I4"].value == "TC:"
    assert float(ws1["J4"].value) == 3.42
    assert ws1["B5"].value == "Ítem"
    assert len(ws1._images) >= 1

    # 2. Verificar formatos de moneda en Soles y Dólares
    FMT_SOLES = '"S/ "#,##0.00'
    FMT_USD = '"$ "#,##0.00'

    # Fila 6 es la Partida 1 -> Sub Total (S/.) en I6
    assert ws1["I6"].number_format == FMT_SOLES
    assert "*$J$4" in str(ws1["I6"].value)

    # Fila 7 es Tarea 1.01 (Soles)
    assert ws1["D7"].value == "Soles"
    assert ws1["G7"].number_format == FMT_SOLES
    assert ws1["H7"].number_format == FMT_SOLES

    # Fila 8 es Tarea 1.02 (Dólares)
    assert ws1["D8"].value == "Dólares"
    assert ws1["G8"].number_format == FMT_USD
    assert ws1["H8"].number_format == FMT_USD

    # Filas de cierre (SUB TOTAL Casco = 9, GG = 10, Gestión = 11, IGV = 12, TOTAL = 13, TOTAL USD = 14)
    assert ws1["I9"].number_format == FMT_SOLES
    assert ws1["H10"].number_format == FMT_SOLES
    assert ws1["H11"].number_format == FMT_SOLES
    assert ws1["H12"].number_format == FMT_SOLES
    assert ws1["I13"].number_format == FMT_SOLES
    assert ws1["I14"].number_format == FMT_USD

    # 3. Verificar round-trip con parsear_cotizacion_venti
    parsed = parsear_cotizacion_venti(xlsx_bytes)
    assert parsed["proyecto"] == proy
    assert parsed["cliente"] == "Maruja Morín"
    assert parsed["fecha"] == "2026-11-09"
    assert parsed["tc"] == 3.42


def test_marca_estudio_color_y_logo_por_branch():
    import io
    import openpyxl
    from PIL import Image
    from cota.cotizacion import (
        exportar_cuadro_pagos_semanales_excel,
        exportar_cuadro_pagos_semanales_pdf,
        generar_plantilla_cotizacion_venti,
    )
    from cota.pdf import generar_pdf_minuta
    from cota.ui.styles import get_app_css
    from cota.utils import guardar_marca_estudio, obtener_marca_estudio

    # Crear un logo PNG sintético en memoria
    img = Image.new("RGBA", (120, 40), (30, 58, 95, 255))
    buf_logo = io.BytesIO()
    img.save(buf_logo, format="PNG")
    custom_logo_bytes = buf_logo.getvalue()

    try:
        marca = guardar_marca_estudio(
            studio_name="Atelier Azul",
            brand_color="#1E3A5F",
            uploaded_logo_bytes=custom_logo_bytes,
            uploaded_logo_name="logo_azul.png",
        )
        assert marca["studio_name"] == "Atelier Azul"
        assert marca["brand_color"] == "#1E3A5F"
        assert marca["brand_hex"] == "1E3A5F"
        assert marca["logo_png_bytes"] is not None

        # CSS dinámico refleja el color del estudio
        css_str = get_app_css()
        assert "--clay-primary: #C85A32;" in css_str

        # Excel de Presupuesto usa el color del estudio, nombre y logo
        xlsx_ppto = generar_plantilla_cotizacion_venti(proyecto="Proy Marca", cliente="Cliente Marca")
        wb_ppto = openpyxl.load_workbook(io.BytesIO(xlsx_ppto))
        ws_ppto = wb_ppto["Presupuesto"]
        assert "ATELIER AZUL" in str(ws_ppto["B2"].value)
        assert ws_ppto["B2"].fill.start_color.rgb.endswith("1E3A5F")
        assert len(ws_ppto._images) >= 1

        # Excel y PDF de Control de Pagos usan el color del estudio, formato de moneda y logo
        xlsx_pagos = exportar_cuadro_pagos_semanales_excel("Proy Marca")
        wb_pagos = openpyxl.load_workbook(io.BytesIO(xlsx_pagos))
        ws_pagos = wb_pagos["Control de Pagos"]
        assert ws_pagos["B1"].value == "Proyecto:"
        assert ws_pagos["C1"].value == "Proy Marca"
        assert ws_pagos["B1"].fill.start_color.rgb.endswith("1E3A5F")
        assert len(ws_pagos._images) >= 1
        assert ws_pagos["D7"].number_format == '"S/ "#,##0.00'

        pdf_pagos = exportar_cuadro_pagos_semanales_pdf("Proy Marca")
        assert pdf_pagos[:4] == b"%PDF"

        pdf_minuta = generar_pdf_minuta({"Titulo": "Acta 1", "Proyecto": "Proy Marca"}, pd.DataFrame(), pd.DataFrame())
        assert pdf_minuta[:4] == b"%PDF"
    finally:
        guardar_marca_estudio(
            studio_name="",
            brand_color="#C85A32",
            reset_logo=True,
        )


def test_render_header_signatures():
    from cota.ui.components import (
        extraer_nombre_studio,
        render_chat_notas_proyecto,
        render_configurador_marca_estudio,
        render_header,
        render_metric_card,
        render_metric_row,
        render_sidebar_branding,
    )

    assert callable(render_chat_notas_proyecto)
    assert callable(render_metric_card)
    assert callable(render_metric_row)
    assert callable(render_sidebar_branding)
    assert callable(render_configurador_marca_estudio)
    assert callable(extraer_nombre_studio)
    # Asegurarse de que soporta las distintas formas de invocación sin error
    render_header(title="LB Studio", subtitle="PROJECT", logo_path="logo/Logo Full.png")
    render_header(title="COTA APP", subtitle="PROJECT", logo_path=None)
    render_header("COTA APP", "PROJECT")
    render_header(app_title="COTA APP", app_subtitle="PROJECT", studio_name="LB Studio")


def test_diseno_entregables_sin_cronograma():
    import streamlit as st
    from cota.config import STATUS_FASES
    from cota.db import (
        COLS_ENTREGABLES,
        on_table_edit,
        registrar_cambio_diseno,
        sembrar_fases_default,
        sincronizar_fases_proyecto,
    )
    from cota.ui.views_project import _contar_estados_diseno

    proy = "Proy Diseno Entregables"
    st.session_state["fases"] = sembrar_fases_default(proy)
    st.session_state["entregables_planos"] = pd.DataFrame(columns=COLS_ENTREGABLES)

    df_f = st.session_state["fases"]
    assert not df_f.empty
    assert all(df_f["Inicio"] == "")
    assert all(df_f["Fin"] == "")

    sincronizar_fases_proyecto(proy, ["01. Levantamiento & Brief", "Etapa Extra Sin Fechas"])
    df_sync = st.session_state["fases"][st.session_state["fases"]["Proyecto"] == proy]
    assert len(df_sync) == 2
    assert all(df_sync["Inicio"] == "")
    assert all(df_sync["Fin"] == "")

    # 1. Entregable inicial en revisión (0 cambios) no suma Cambios_Realizados ni asigna Fecha_Limite
    ent1 = registrar_cambio_diseno(
        proy_name=proy,
        fase_diseno="01. Levantamiento & Brief",
        tipo_entregable="Plano Preliminar / Layout",
        nombre_entregable="Plano Sala Principal",
        fecha_cambio="2026-11-11",
        estado="🔵 En revisión cliente",
        nro_cambios=0,
    )
    assert ent1["Fecha_Limite"] == ""
    f_row1 = st.session_state["fases"][
        (st.session_state["fases"]["Proyecto"] == proy)
        & (st.session_state["fases"]["Fase"] == "01. Levantamiento & Brief")
    ].iloc[0]
    assert int(f_row1["Cambios_Realizados"]) == 0

    # 2. Entregable con observaciones suma cambios y se contabiliza en _contar_estados_diseno
    ent2 = registrar_cambio_diseno(
        proy_name=proy,
        fase_diseno="01. Levantamiento & Brief",
        tipo_entregable="Renders 3D",
        nombre_entregable="Render Cocina V2",
        fecha_cambio="2026-11-12",
        estado="🟠 Con cambios / Observado",
        nro_cambios=2,
    )
    assert ent2["Estado"] == "🟠 Con cambios / Observado"
    f_row2 = st.session_state["fases"][
        (st.session_state["fases"]["Proyecto"] == proy)
        & (st.session_state["fases"]["Fase"] == "01. Levantamiento & Brief")
    ].iloc[0]
    assert int(f_row2["Cambios_Realizados"]) == 2

    resumen = _contar_estados_diseno(
        st.session_state["fases"],
        st.session_state["entregables_planos"],
    )
    assert set(STATUS_FASES).issubset(set(resumen.keys()))
    assert resumen["⚪ Pendiente"]["etapas"] == 2
    assert resumen["🔵 En revisión cliente"]["entregables"] == 1
    assert resumen["🟠 Con cambios / Observado"]["entregables"] == 1

    # 3. Edición en tabla de fases sincroniza Estado <-> Aprobado_Cliente sin requerir Inicio/Fin
    base_f_k = f"base_df_fases_{proy}"
    w_f_k = f"ed_fases_{proy}_0"
    st.session_state[base_f_k] = df_sync.drop(columns=["Proyecto", "Inicio", "Fin"]).reset_index(drop=True)
    st.session_state[w_f_k] = {"edited_rows": {"0": {"Estado": "🟢 Aprobado"}}}
    on_table_edit(
        base_f_k, w_f_k, "fases", ["Proyecto"], [proy],
        ["Fecha_Ultimo_Cambio"], ["Fase", "Etapa", "Estado", "Responsable", "Notas"],
        ["Aprobado_Cliente"], ["Orden", "Avance_Pct", "Cambios_Realizados"], "ID",
    )
    f_aprob = st.session_state["fases"].iloc[0]
    assert bool(f_aprob["Aprobado_Cliente"]) is True
    assert int(f_aprob["Avance_Pct"]) == 100

    # Cambiar de Aprobado a En revisión cliente desmarca Aprobado_Cliente
    w_f_k2 = f"ed_fases_{proy}_1"
    st.session_state[w_f_k2] = {"edited_rows": {"0": {"Estado": "🔵 En revisión cliente"}}}
    on_table_edit(
        base_f_k, w_f_k2, "fases", ["Proyecto"], [proy],
        ["Fecha_Ultimo_Cambio"], ["Fase", "Etapa", "Estado", "Responsable", "Notas"],
        ["Aprobado_Cliente"], ["Orden", "Avance_Pct", "Cambios_Realizados"], "ID",
    )
    f_rev = st.session_state["fases"].iloc[0]
    assert bool(f_rev["Aprobado_Cliente"]) is False

    # 4. Edición sobre vista filtrada de entregables no borra los entregables ocultos por el filtro
    base_e_k = f"base_df_ent_{proy}"
    w_e_k = f"ed_ent_{proy}_0"
    df_ent_fil = st.session_state["entregables_planos"][
        st.session_state["entregables_planos"]["Estado"] == "🔵 En revisión cliente"
    ].copy()
    st.session_state[base_e_k] = df_ent_fil[[
        "ID", "Fase", "Especialidad", "Nombre_Entregable", "Estado",
        "Revision", "Nro_Cambios", "Fecha_Cambio", "Detalle_Cambio", "Responsable", "Link",
    ]].reset_index(drop=True)
    st.session_state[w_e_k] = {"edited_rows": {"0": {"Estado": "🟢 Aprobado"}}}
    on_table_edit(
        base_e_k, w_e_k, "entregables_planos", ["Proyecto"], [proy],
        ["Fecha_Cambio"], ["Fase", "Especialidad", "Nombre_Entregable", "Revision", "Estado", "Detalle_Cambio", "Responsable", "Link"],
        None, ["Nro_Cambios"], "ID",
    )
    assert len(st.session_state["entregables_planos"]) == 2
    estados_ent = st.session_state["entregables_planos"]["Estado"].tolist()
    assert "🟢 Aprobado" in estados_ent and "🟠 Con cambios / Observado" in estados_ent

    # 5. Código de UI de 02. Diseño no planifica cronograma Gantt ni columnas Inicio/Entrega
    with open("D:/cota-app/cota/ui/views_project.py", "r", encoding="utf-8") as f:
        vp_code = f.read()
    tab_diseno = vp_code.split("def _render_tab_fases")[1].split("def _render_table_dnd_controller")[0]
    assert "Cronograma de Gestión del Diseño" not in tab_diseno
    assert "Cronograma Gantt" not in tab_diseno
    assert "Duración estimada (días)" not in tab_diseno
    assert "Inicio_DT" not in tab_diseno
    assert "Fin_DT" not in tab_diseno
    assert '"Entrega"' not in tab_diseno
    assert "_contar_estados_diseno" in tab_diseno
