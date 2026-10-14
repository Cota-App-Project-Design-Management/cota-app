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
    assert len(df_fases) == 8
    assert "01. Levantamiento & Brief" in df_fases['Fase'].tolist()
    assert "08. Cierre & Entrega Final" in df_fases['Fase'].tolist()
    assert all(df_fases['Proyecto'] == "Casa Prueba")


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


