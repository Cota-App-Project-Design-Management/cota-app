"""
Integration test using streamlit.testing.v1.AppTest.
Verifies that app.py initializes, routes, and renders without exceptions.
"""

from pathlib import Path
import pandas as pd
from streamlit.testing.v1 import AppTest

APP_PATH = str((Path(__file__).parent.parent / "app.py").resolve())


def test_app_smoke_render():
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    # Simulate authenticated session state and minimal dataframes
    at.session_state['authenticated'] = True
    at.session_state['vista_actual'] = 'main'
    at.session_state['proy_activo'] = None
    at.run()

    # Verify no unhandled exceptions
    assert not at.exception, f"App raised an exception: {at.exception}"
    assert len(at.markdown) > 0


def test_app_smoke_project_view():
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.session_state['authenticated'] = True
    at.session_state['vista_actual'] = 'proyecto'
    at.session_state['proy_activo'] = 'Proyecto Demo'
    at.session_state['proyectos'] = pd.DataFrame([{
        'Nombre': 'Proyecto Demo',
        'Encargado': 'Socio 1',
        'Ubicación': 'Lima',
        'Estado': '🔵 En Proceso',
        'Inicio': '2026-01-01',
        'Fin': '2026-06-01',
        'Color': '#00E5FF',
        'Cliente': 'Cliente Demo',
        'Presupuesto': 50000.0,
        'Utilidades': 10000.0,
        'GG_Presupuesto': 3000.0,
        'Archivado': False,
        'Metodologia': 'Diseño',
        'Division': 'General',
        'Tipo_Proyecto': 'Interiorismo Residencial',
        'Num_Pisos': 0,
        'Num_Sotanos': 0,
        'Presupuesto_FFE': 20000.0,
        'Honorarios_Diseno': 15000.0
    }])
    at.run()

    assert not at.exception, f"Project view raised an exception: {at.exception}"
