"""
Motor de base de datos, esquemas de tablas, sincronización con Google Sheets,
migraciones automáticas no destructivas y operaciones en cascada.
"""

import datetime
import os
import time
import uuid
import openpyxl
import pandas as pd
import streamlit as st
from cota.config import FASES_CANONICAS, get_secret
from cota.utils import to_bool, parse_date


# ==========================================
# ESQUEMAS DE TABLAS (SCHEMA DEFINITION)
# ==========================================
COLS_PROY = [
    'Nombre', 'Encargado', 'Ubicación', 'Estado', 'Inicio', 'Fin', 'Notas',
    'Color', 'Cliente', 'Presupuesto', 'Utilidades', 'GG_Presupuesto',
    'Archivado', 'Metodologia', 'Division', 'Tipo_Proyecto', 'Num_Pisos', 'Num_Sotanos',
    'Presupuesto_FFE', 'Honorarios_Diseno'
]

COLS_TASKS = [
    'Proyecto', 'Partida', 'Orden', 'Tarea', 'Especialidad', 'Contratista',
    'Estado', 'Inicio', 'Fin', 'Causa_Cumplimiento', 'Culpa_Contratista',
    'Permitir_Cruce', 'Dependencia', 'Notas'
]

COLS_MAESTRO = ['ID_Contratista', 'Especialidad', 'Ubicación_Base', 'Notas']
COLS_HIST = ['ID_Contratista', 'Estado', 'Responsable']
COLS_GG = ['Proyecto', 'Fecha', 'Responsable', 'Concepto', 'Monto']
COLS_TODO = ['ID', 'Proyecto', 'Categoria', 'Tarea', 'Responsable', 'Check']
COLS_PAGOS = ['ID', 'Proyecto', 'Partida', 'Contratista', 'Fecha', 'Monto', 'Tipo', 'Notas']
COLS_P_INFO = [
    'Proyecto', 'Nombre_Partida', 'Monto_Pactado', 'Nivel_Actual',
    'Contratista', 'Inicio', 'Fin', 'Estado', 'Etapa', 'Nivel_Inicio', 'Nivel_Fin'
]
COLS_INGRESOS = ['ID', 'Fecha', 'Proyecto', 'Socio', 'Categoria', 'Monto', 'Notas']

# Especificaciones FF&E y Materiales
COLS_MAT = [
    'ID', 'Proyecto', 'Ambiente', 'Categoria', 'Codigo_Ref', 'Material',
    'Cantidad', 'Unidad', 'Precio_Unit_Estimado', 'Costo_Estimado', 'Costo_Real',
    'Proveedor', 'Estado', 'Link_Ref', 'Notas'
]

# Fases del ciclo de vida del diseño
COLS_FASES = [
    'ID', 'Proyecto', 'Orden', 'Fase', 'Etapa', 'Inicio', 'Fin',
    'Estado', 'Avance_Pct', 'Responsable', 'Aprobado_Cliente', 'Notas'
]

# Cobros e Hitos Financieros hacia el Cliente
COLS_COBROS = [
    'ID', 'Proyecto', 'Hito', 'Tipo', 'Monto_Pactado', 'Fecha_Vencimiento',
    'Monto_Cobrado', 'Fecha_Cobro', 'Estado', 'Notas'
]

# Punch List / Pendientes de Entrega
COLS_PUNCH = [
    'ID', 'Proyecto', 'Ambiente', 'Elemento', 'Descripcion',
    'Responsable', 'Prioridad', 'Estado', 'Fecha_Deteccion', 'Fecha_Solucion', 'Notas'
]

# Actas de Reunión (antes ICE Sessions)
COLS_ICE_SESIONES = [
    'ID_Sesion', 'Proyecto', 'Nombre_Sesion', 'Tipo_Reunion', 'Etapa',
    'Fecha_Prog', 'Fecha_Real', 'Hora', 'Organizador', 'Lider'
]
COLS_ICE_INVITADOS = ['ID_Sesion', 'Nombre', 'Empresa', 'Cargo', 'Asistencia']
COLS_ICE_ACUERDOS = ['ID_Sesion', 'Descripcion', 'Responsable', 'Acuerdo']

# Entregables y Planos
COLS_ENTREGABLES = [
    'ID', 'Proyecto', 'Especialidad', 'Nombre_Entregable', 'Revision',
    'Estado', 'Fecha_Limite', 'Responsable', 'Fase', 'Link'
]

COLS_OBSERVACIONES = [
    'ID', 'Proyecto', 'Nro_Observacion', 'Especialidad', 'Descripcion',
    'Estado', 'Fecha_Ingreso', 'Fecha_Subsanacion', 'Responsable', 'Tipo_Origen', 'Notas'
]

COLS_DOSSIER = ['ID', 'Proyecto', 'Especialidad', 'Documento', 'Estado', 'Responsable', 'Notas']
COLS_UNIDADES = ['ID', 'Proyecto', 'Unidad', 'Propietario', 'Estado', 'Fecha_Inspeccion', 'Fecha_Entrega', 'Detalle_Observaciones']


def get_proyectos_activos(df_proy):
    """Retorna un DataFrame con los proyectos no archivados, garantizando todas las columnas."""
    if df_proy is None or df_proy.empty:
        return pd.DataFrame(columns=COLS_PROY)
    mask = ~df_proy['Archivado'].apply(to_bool) if 'Archivado' in df_proy.columns else pd.Series(True, index=df_proy.index)
    res = df_proy[mask].copy()
    for col in COLS_PROY:
        if col not in res.columns:
            res[col] = ""
    return res


def get_proyectos_archivados(df_proy):
    """Retorna un DataFrame con los proyectos archivados, garantizando todas las columnas."""
    if df_proy is None or df_proy.empty:
        return pd.DataFrame(columns=COLS_PROY)
    mask = df_proy['Archivado'].apply(to_bool) if 'Archivado' in df_proy.columns else pd.Series(False, index=df_proy.index)
    res = df_proy[mask].copy()
    for col in COLS_PROY:
        if col not in res.columns:
            res[col] = ""
    return res


def _get_local_excel_path():
    """Retorna la ruta al archivo Excel de base de datos en Drive, directorio del proyecto o nube."""
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidatos = [
        r"G:\My Drive\Cota App\BD_COTA_APP_PRUEBAS.xlsx",
        os.path.join(repo_root, "BD_COTA_APP_PRUEBAS.xlsx"),
        r"D:\cota-app\BD_COTA_APP_PRUEBAS.xlsx",
    ]
    for c in candidatos:
        if os.path.exists(c):
            return c
    return candidatos[1]


def _guardar_hoja_excel(file_path, sheet_name, df):
    """Guarda o actualiza una pestaña en el archivo Excel local/Drive."""
    try:
        dir_p = os.path.dirname(file_path)
        if not os.path.exists(dir_p):
            return False
        if not os.path.exists(file_path):
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            return True
        wb = openpyxl.load_workbook(file_path)
        if sheet_name in wb.sheetnames:
            del wb[sheet_name]
        wb.save(file_path)
        with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
        return True
    except Exception:
        return False


def inicializar_conexion_gsheets():
    """Inicializa la conexión con Google Sheets si está disponible en st.secrets con Service Account."""
    try:
        from streamlit_gsheets import GSheetsConnection
        sheet_url = get_secret("GSHEETS_URL", "")
        conn_secrets = get_secret("connections", {})
        gsheets_secrets = conn_secrets.get("gsheets", {}) if hasattr(conn_secrets, "get") else {}
        if not sheet_url and hasattr(gsheets_secrets, "get"):
            sheet_url = str(gsheets_secrets.get("spreadsheet", "")).strip()
        has_sa = hasattr(gsheets_secrets, "get") and (
            gsheets_secrets.get("type") == "service_account" or "private_key" in gsheets_secrets
        )

        if sheet_url and has_sa:
            conn = st.connection("gsheets", type=GSheetsConnection)
            return conn, sheet_url, True
        return None, sheet_url, False
    except Exception:
        return None, "", False


def cargar_tabla(conn, sheet_url, nube_ok, pestaña, columnas):
    """Carga una pestaña desde Google Sheets o desde el archivo Excel en Google Drive con sanitización."""
    if 'original_tables' not in st.session_state:
        st.session_state.original_tables = {}

    df = None
    if nube_ok and sheet_url and conn is not None:
        try:
            df = conn.read(spreadsheet=sheet_url, worksheet=pestaña, ttl=300)
        except Exception:
            df = None

    # Carga desde Excel (Google Drive o Local / Respaldo en Repositorio)
    if df is None or df.empty:
        excel_path = _get_local_excel_path()
        if excel_path and os.path.exists(excel_path):
            try:
                df = pd.read_excel(excel_path, sheet_name=pestaña)
            except Exception:
                df = None

    if df is None or df.empty:
        df = pd.DataFrame(columns=columnas)
        st.session_state.original_tables[pestaña] = df.copy()
        return df

    # Migración y retrocompatibilidad para materiales / FF&E
    if pestaña == 'materiales':
        if 'Ppto_Estimado' in df.columns and 'Costo_Estimado' not in df.columns:
            df['Costo_Estimado'] = df['Ppto_Estimado']
        if 'Ppto_Real' in df.columns and 'Costo_Real' not in df.columns:
            df['Costo_Real'] = df['Ppto_Real']
        if 'Estado' in df.columns:
            df['Estado'] = df['Estado'].replace({
                'No Comprado': '⚪ Propuesto',
                'Comprado': '🟢 Instalado / Recibido',
                '🔴 No Comprado': '⚪ Propuesto',
                '🟢 Comprado': '🟢 Instalado / Recibido'
            })

    # Asegurar que todas las columnas esperadas existan con valores por defecto
    for col in columnas:
        if col not in df.columns:
            if col in ['Archivado', 'Check', 'Aprobado_Cliente', 'Culpa_Contratista', 'Permitir_Cruce']:
                df[col] = False
            elif col in ['Presupuesto', 'Utilidades', 'GG_Presupuesto', 'Presupuesto_FFE', 'Honorarios_Diseno',
                         'Costo_Estimado', 'Costo_Real', 'Precio_Unit_Estimado', 'Monto_Pactado', 'Monto_Cobrado', 'Monto']:
                df[col] = 0.0
            elif col in ['Orden', 'Num_Pisos', 'Num_Sotanos', 'Avance_Pct']:
                df[col] = 0
            elif col == 'Division':
                df[col] = "General"
            elif col == 'Ambiente':
                df[col] = "General / Toda la casa"
            elif col == 'Categoria' and pestaña == 'materiales':
                df[col] = "Mobiliario Suelto"
            elif col == 'Estado' and pestaña == 'materiales':
                df[col] = "⚪ Propuesto"
            elif col == 'Estado' and pestaña == 'fases':
                df[col] = "⚪ No iniciada"
            elif col == 'Estado' and pestaña == 'cobros':
                df[col] = "🟡 Pendiente"
            elif col == 'Estado' and pestaña == 'pendientes_entrega':
                df[col] = "🔴 Pendiente"
            elif col == 'Prioridad' and pestaña == 'pendientes_entrega':
                df[col] = "Media"
            elif col == 'Tipo_Reunion':
                df[col] = "Con Cliente"
            else:
                df[col] = ""

    st.session_state.original_tables[pestaña] = df.copy()
    return df


def guardar_tabla(conn, sheet_url, nube_ok, df, pestaña):
    """Guarda una tabla a Google Sheets o a Excel (Google Drive / local) con validaciones de integridad."""
    if st.session_state.get('hubo_error_conexion', False):
        st.error(f"Guardado bloqueado para '{pestaña}': Se detectó un fallo de conexión. Reintente la sincronización.")
        return False

    # Protección contra borrado accidental de tablas críticas
    if pestaña in ['proyectos', 'tasks', 'maestro'] and (df is None or len(df) == 0):
        st.error(f"Guardado cancelado para '{pestaña}': Intento de sobreescribir con 0 filas.")
        return False

    original_df = st.session_state.get('original_tables', {}).get(pestaña)
    if original_df is not None and original_df.equals(df):
        return True

    if nube_ok and sheet_url and conn is not None:
        try:
            try:
                conn.update(spreadsheet=sheet_url, worksheet=pestaña, data=df)
                if 'original_tables' in st.session_state:
                    st.session_state.original_tables[pestaña] = df.copy()
                st.cache_data.clear()
                return True
            except Exception as e_update:
                # Auto-creación de pestaña faltante con gspread
                try:
                    import gspread
                    client = conn.client._client
                    spreadsheet = client.open_by_url(sheet_url)
                    try:
                        spreadsheet.worksheet(pestaña)
                    except gspread.exceptions.WorksheetNotFound:
                        spreadsheet.add_worksheet(title=pestaña, rows="100", cols="25")
                    conn.update(spreadsheet=sheet_url, worksheet=pestaña, data=df)
                    if 'original_tables' in st.session_state:
                        st.session_state.original_tables[pestaña] = df.copy()
                    st.cache_data.clear()
                    return True
                except Exception:
                    raise e_update
        except Exception as e:
            st.error(f"Error al guardar '{pestaña}': {str(e)}")
            return False

    # Modo Drive / local: persistir en BD_COTA_APP_PRUEBAS.xlsx
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rutas_excel = list(dict.fromkeys([
        r"G:\My Drive\Cota App\BD_COTA_APP_PRUEBAS.xlsx",
        os.path.join(repo_root, "BD_COTA_APP_PRUEBAS.xlsx"),
        r"D:\cota-app\BD_COTA_APP_PRUEBAS.xlsx",
    ]))
    for p in rutas_excel:
        _guardar_hoja_excel(p, pestaña, df)

    if 'original_tables' in st.session_state:
        st.session_state.original_tables[pestaña] = df.copy()
    st.cache_data.clear()
    return True


def sembrar_fases_default(nombre_proyecto, fecha_inicio=None):
    """Crea las 8 fases estándar de diseño para un nuevo proyecto."""
    f_ini = parse_date(fecha_inicio) or datetime.date.today()
    cursor = f_ini
    rows = []

    for f in FASES_CANONICAS:
        dias = f.get('Dias', 7)
        cursor_fin = cursor + datetime.timedelta(days=dias)
        rows.append({
            'ID': f"FASE_{int(time.time())}_{uuid.uuid4().hex[:6]}",
            'Proyecto': nombre_proyecto,
            'Orden': f['Orden'],
            'Fase': f['Fase'],
            'Etapa': f['Etapa'],
            'Inicio': cursor.strftime('%Y-%m-%d'),
            'Fin': cursor_fin.strftime('%Y-%m-%d'),
            'Estado': '⚪ No iniciada',
            'Avance_Pct': 0,
            'Responsable': '',
            'Aprobado_Cliente': False,
            'Notas': ''
        })
        cursor = cursor_fin + datetime.timedelta(days=1)

    return pd.DataFrame(rows)


def renombrar_proyecto(viejo_nombre, nuevo_nombre):
    """
    Propaga el cambio de nombre de un proyecto en cascada a todas las tablas secundarias
    para mantener la integridad referencial.
    """
    if not viejo_nombre or not nuevo_nombre or viejo_nombre == nuevo_nombre:
        return

    tablas_con_proyecto = [
        'tasks', 'partidas_info', 'pagos_maestros', 'gg_log', 'todo_list',
        'ingresos_socios', 'materiales', 'ice_sesiones', 'entregables_planos',
        'observaciones_municipales', 'fases', 'cobros', 'pendientes_entrega',
        'partidas'
    ]

    # Actualizar tabla principal
    if 'proyectos' in st.session_state:
        mask = st.session_state.proyectos['Nombre'] == viejo_nombre
        st.session_state.proyectos.loc[mask, 'Nombre'] = nuevo_nombre

    # Actualizar tablas secundarias
    for t_key in tablas_con_proyecto:
        if t_key in st.session_state and isinstance(st.session_state[t_key], pd.DataFrame):
            df = st.session_state[t_key]
            if 'Proyecto' in df.columns:
                mask = df['Proyecto'] == viejo_nombre
                df.loc[mask, 'Proyecto'] = nuevo_nombre

    # Actualizar estado de proyecto activo si corresponde
    if st.session_state.get('proy_activo') == viejo_nombre:
        st.session_state.proy_activo = nuevo_nombre


def purgar_proyecto_cascada(nombre_proyecto):
    """Elimina definitivamente un proyecto y todos sus registros asociados."""
    if not nombre_proyecto:
        return

    tablas = [
        ('proyectos', 'Nombre'),
        ('tasks', 'Proyecto'),
        ('p_info', 'Proyecto'),
        ('pagos', 'Proyecto'),
        ('gg_log', 'Proyecto'),
        ('todo_list', 'Proyecto'),
        ('ingresos_socios', 'Proyecto'),
        ('materiales', 'Proyecto'),
        ('ice_sesiones', 'Proyecto'),
        ('entregables_planos', 'Proyecto'),
        ('observaciones_municipales', 'Proyecto'),
        ('fases', 'Proyecto'),
        ('cobros', 'Proyecto'),
        ('pendientes_entrega', 'Proyecto'),
        ('partidas', 'Proyecto')
    ]

    for k, col in tablas:
        if k in st.session_state and isinstance(st.session_state[k], pd.DataFrame):
            df = st.session_state[k]
            if col in df.columns:
                st.session_state[k] = df[df[col] != nombre_proyecto].reset_index(drop=True)

    if st.session_state.get('proy_activo') == nombre_proyecto:
        st.session_state.proy_activo = None
        st.session_state.vista_actual = 'main'


def clear_base_dfs():
    """Limpia dataframes cacheados en sesión para forzar re-renderizado fresco."""
    for k in list(st.session_state.keys()):
        if k.startswith("base_df_"):
            del st.session_state[k]


def on_table_edit(base_key, widget_key, master_state_key, group_cols=None, group_vals=None,
                  date_cols=None, text_cols=None, bool_cols=None, num_cols=None, id_col=None):
    """
    Manejador unificado de edición en st.data_editor con soporte para inserción,
    edición, eliminación, sanitización de tipos y generación segura de IDs únicos.
    """
    if widget_key not in st.session_state:
        return
    edits = st.session_state[widget_key]
    df = st.session_state[base_key]

    df_new = df.copy()

    # 1. Aplicar celdas editadas
    for idx, cols in edits.get("edited_rows", {}).items():
        row_idx = int(idx)
        for col, val in cols.items():
            df_new.at[row_idx, col] = val

    # 2. Aplicar eliminaciones
    deleted_indices = [int(i) for i in edits.get("deleted_rows", [])]
    if deleted_indices:
        df_new = df_new.drop(index=deleted_indices).reset_index(drop=True)

    # 3. Aplicar inserciones
    added_rows = edits.get("added_rows", [])
    if added_rows:
        df_added = pd.DataFrame(added_rows)
        df_new = pd.concat([df_new, df_added], ignore_index=True)

    # 4. Generación de IDs únicos
    if id_col:
        if id_col not in df_new.columns:
            df_new[id_col] = None
        for i, row in df_new.iterrows():
            val = row.get(id_col)
            if pd.isna(val) or val == "" or str(val).strip() == "" or str(val).lower() == "none":
                prefix = id_col.split("_")[0] if "_" in id_col else id_col
                df_new.at[i, id_col] = f"{prefix}_{int(time.time())}_{uuid.uuid4().hex[:6]}"

    # 5. Sanitización de tipos
    if date_cols:
        for c in date_cols:
            if c in df_new.columns:
                df_new[c] = df_new[c].apply(lambda x: parse_date(x))
    if text_cols:
        for c in text_cols:
            if c in df_new.columns:
                df_new[c] = df_new[c].fillna("").astype(str).replace('nan', '').replace('None', '')
    if bool_cols:
        for c in bool_cols:
            if c in df_new.columns:
                df_new[c] = df_new[c].apply(to_bool)
    if num_cols:
        for c in num_cols:
            if c in df_new.columns:
                df_new[c] = pd.to_numeric(df_new[c], errors='coerce').fillna(0.0)

    # Recalcular Costo_Estimado automáticamente en FF&E si cambian Cantidad o Precio Unitario
    if master_state_key == 'materiales' and 'Cantidad' in df_new.columns and 'Precio_Unit_Estimado' in df_new.columns:
        for idx, cols in edits.get("edited_rows", {}).items():
            r_idx = int(idx)
            if r_idx in df_new.index and ('Cantidad' in cols or 'Precio_Unit_Estimado' in cols) and 'Costo_Estimado' not in cols:
                df_new.at[r_idx, 'Costo_Estimado'] = round(
                    float(df_new.at[r_idx, 'Cantidad'] or 0.0) * float(df_new.at[r_idx, 'Precio_Unit_Estimado'] or 0.0), 2
                )
        for i, row in df_new.iterrows():
            c_est = float(row.get('Costo_Estimado') or 0.0)
            cant = float(row.get('Cantidad') or 0.0)
            p_unit = float(row.get('Precio_Unit_Estimado') or 0.0)
            if c_est == 0.0 and cant > 0 and p_unit > 0:
                df_new.at[i, 'Costo_Estimado'] = round(cant * p_unit, 2)

    st.session_state[base_key] = df_new

    # 6. Actualizar dataframe maestro en session state
    if master_state_key in st.session_state:
        master_df = st.session_state[master_state_key]
        if group_cols and group_vals:
            clean_mask = pd.Series(True, index=master_df.index)
            for g_col, g_val in zip(group_cols, group_vals):
                clean_mask = clean_mask & (master_df[g_col] == g_val)
            master_df = master_df[~clean_mask]
        else:
            master_df = pd.DataFrame(columns=master_df.columns)

        n_t = df_new.copy()
        if group_cols and group_vals:
            for g_col, g_val in zip(group_cols, group_vals):
                n_t[g_col] = g_val

        for c in master_df.columns:
            if c not in n_t.columns:
                n_t[c] = None

        st.session_state[master_state_key] = pd.concat([master_df, n_t[master_df.columns]], ignore_index=True)

    # 7. Incrementar contador de widget para forzar clave nueva y evitar duplicaciones
    c_key = f"c_{base_key}"
    st.session_state[c_key] = st.session_state.get(c_key, 0) + 1
