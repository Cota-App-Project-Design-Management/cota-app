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
from cota.config import BANCO_FASES_DEFAULT, FASES_CANONICAS, get_secret
from cota.utils import to_bool, parse_date


# ==========================================
# ESQUEMAS DE TABLAS (SCHEMA DEFINITION)
# ==========================================
COLS_PROY = [
    'Nombre', 'Encargado', 'Ubicación', 'Estado', 'Inicio', 'Fin', 'Notas',
    'Color', 'Cliente', 'Presupuesto', 'Utilidades', 'GG_Presupuesto',
    'Archivado', 'Metodologia', 'Division', 'Tipo_Proyecto', 'Num_Pisos', 'Num_Sotanos',
    'Presupuesto_FFE', 'Honorarios_Diseno',
    'TC_Presupuesto', 'GG_Pct', 'Utilidades_Pct', 'Incluir_IGV',
    'Link_Drive', 'Pagos_Semanales_JSON'
]

COLS_TASKS = [
    'Proyecto', 'Partida', 'Orden', 'Codigo_Item', 'Tarea', 'Especialidad', 'Contratista',
    'Estado', 'Supervisado', 'Inicio', 'Fin', 'Causa_Cumplimiento', 'Culpa_Contratista',
    'Permitir_Cruce', 'Dependencia', 'Notas',
    'Moneda', 'Unidad', 'Metrado', 'Valor_Unitario', 'Presupuesto'
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


import io
import re


def _normalizar_supervisado(val):
    """Normaliza el campo Supervisado a 'Sí' o 'No'."""
    if val is True:
        return "Sí"
    if val is False or val is None or pd.isna(val):
        return "No"
    s = str(val).strip().lower()
    if s in ["sí", "si", "true", "1", "s", "yes"]:
        return "Sí"
    return "No"



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


def _extraer_file_id(sheet_url: str) -> str:
    """Extrae el ID del documento de un enlace de Google Sheets o Google Drive."""
    if not sheet_url:
        return ""
    m = re.search(r"/d/([a-zA-Z0-9-_]+)", str(sheet_url))
    if m:
        return m.group(1)
    m2 = re.search(r"[?&]id=([a-zA-Z0-9-_]+)", str(sheet_url))
    return m2.group(1) if m2 else ""


def _obtener_sesion_google():
    """Construye una sesión autenticada de Google (Drive + Sheets) usando la Service Account de st.secrets."""
    try:
        from google.oauth2.service_account import Credentials
        from google.auth.transport.requests import AuthorizedSession

        conn_secrets = get_secret("connections", {})
        gsheets_secrets = conn_secrets.get("gsheets", {}) if hasattr(conn_secrets, "get") else {}
        if not hasattr(gsheets_secrets, "get"):
            return None

        sa_info = dict(gsheets_secrets)
        if "private_key" not in sa_info:
            return None

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
        return AuthorizedSession(creds)
    except Exception:
        return None


def _descargar_workbook_nube(sheet_url: str):
    """
    Descarga el archivo completo desde Google Drive/Sheets en una sola petición.
    Soporta tanto archivos .XLSX subidos a Google Drive como Hojas de Cálculo nativas de Google.
    """
    if "_cloud_xlsx_bytes" in st.session_state and st.session_state._cloud_xlsx_bytes:
        return st.session_state._cloud_xlsx_bytes
    if st.session_state.get("_cloud_xlsx_tried", False):
        return None

    st.session_state._cloud_xlsx_tried = True
    file_id = _extraer_file_id(sheet_url)
    if not file_id:
        return None

    session = _obtener_sesion_google()
    if session is None:
        return None

    urls_intento = [
        f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&supportsAllDrives=true",
        f"https://www.googleapis.com/drive/v3/files/{file_id}/export?mimeType=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx",
    ]

    for url in urls_intento:
        try:
            resp = session.get(url, timeout=12)
            if resp.status_code == 200 and resp.content and resp.content[:2] == b"PK":
                st.session_state._cloud_xlsx_bytes = resp.content
                return resp.content
        except Exception:
            continue

    return None


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
        if not sheet_url and hasattr(gsheets_secrets, "get"):
            sheet_url = str(gsheets_secrets.get("url", "")).strip()
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
    """Carga una pestaña desde Google Drive (.XLSX o Google Sheet) o desde el respaldo local con sanitización."""
    if 'original_tables' not in st.session_state:
        st.session_state.original_tables = {}

    df = None

    # 1. Intentar desde workbook descargado de Google Drive / Sheets (soporta .XLSX nativo en Drive y Google Sheets)
    if nube_ok and sheet_url:
        cloud_bytes = _descargar_workbook_nube(sheet_url)
        if cloud_bytes:
            try:
                df = pd.read_excel(io.BytesIO(cloud_bytes), sheet_name=pestaña)
            except Exception:
                df = None

    # 2. Si no hubo bytes de Drive, intentar conector directo de Google Sheets
    if (df is None or df.empty) and nube_ok and sheet_url and conn is not None and not st.session_state.get("_gsheets_direct_failed", False):
        try:
            df = conn.read(spreadsheet=sheet_url, worksheet=pestaña, ttl=300)
        except Exception:
            st.session_state._gsheets_direct_failed = True
            df = None

    # 3. Carga desde Excel (Google Drive montado o Respaldo en Repositorio BD_COTA_APP_PRUEBAS.xlsx)
    if df is None or df.empty:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidatos_excel = list(dict.fromkeys([
            os.path.join(repo_root, "BD_COTA_APP_PRUEBAS.xlsx"),
            r"D:\cota-app\BD_COTA_APP_PRUEBAS.xlsx",
            r"G:\My Drive\Cota App\BD_COTA_APP_PRUEBAS.xlsx",
        ]))
        for excel_path in candidatos_excel:
            if excel_path and os.path.exists(excel_path):
                try:
                    df = pd.read_excel(excel_path, sheet_name=pestaña)
                    if df is not None and not df.empty:
                        break
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

    # Asegurar que todas las columnas esperadas existan con valores y dtypes seguros
    bool_cols_set = {'Archivado', 'Check', 'Aprobado_Cliente', 'Culpa_Contratista', 'Permitir_Cruce', 'Incluir_IGV'}
    float_cols_set = {
        'Presupuesto', 'Utilidades', 'GG_Presupuesto', 'Presupuesto_FFE', 'Honorarios_Diseno',
        'Costo_Estimado', 'Costo_Real', 'Precio_Unit_Estimado', 'Monto_Pactado', 'Monto_Cobrado', 'Monto',
        'Metrado', 'Valor_Unitario', 'TC_Presupuesto', 'GG_Pct', 'Utilidades_Pct'
    }
    int_cols_set = {'Orden', 'Num_Pisos', 'Num_Sotanos', 'Avance_Pct'}

    for col in columnas:
        if col not in df.columns:
            if col in bool_cols_set:
                df[col] = False
            elif col in float_cols_set:
                if col == 'TC_Presupuesto':
                    df[col] = 3.42
                elif col == 'GG_Pct':
                    df[col] = 2.0
                elif col == 'Utilidades_Pct':
                    df[col] = 15.0
                else:
                    df[col] = 0.0
            elif col == 'Moneda' and pestaña == 'tasks':
                df[col] = "Soles"
            elif col == 'Supervisado' and pestaña == 'tasks':
                df[col] = "No"
            elif col in int_cols_set:
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

        # Garantizar dtype compatible en pandas 2.x para evitar LossySetitemError / TypeError al usar .at[]
        if col in bool_cols_set:
            df[col] = df[col].apply(to_bool).astype(bool)
        elif col in float_cols_set:
            default_f = 3.42 if col == 'TC_Presupuesto' else (2.0 if col == 'GG_Pct' else (15.0 if col == 'Utilidades_Pct' else 0.0))
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(default_f).astype(float)
        elif col in int_cols_set:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        else:
            df[col] = df[col].fillna("").astype(str).replace({"nan": "", "None": "", "<NA>": ""}).astype(object)

    # Normalizar Supervisado en tareas
    if pestaña == 'tasks':
        if 'Supervisado' not in df.columns:
            df['Supervisado'] = "No"
        else:
            df['Supervisado'] = df['Supervisado'].apply(_normalizar_supervisado).astype(object)

    if pestaña == 'proyectos':
        for c_extra in ['Link_Drive', 'Pagos_Semanales_JSON']:
            if c_extra not in df.columns:
                df[c_extra] = ""
            df[c_extra] = df[c_extra].fillna("").astype(str).replace({"nan": "", "None": "", "<NA>": ""}).astype(object)

    if pestaña == 'fases':
        mask_obsoletas = df['Fase'].astype(str).str.contains(r'ff&e|ffe|expediente t[eé]cnico', case=False, na=False)
        if mask_obsoletas.any():
            df = df[~mask_obsoletas].copy()
        def _migrar_fase_item(nom):
            s = str(nom).strip()
            if re.search(r'ejecuci[oó]n|obra|montaje', s, re.IGNORECASE):
                return "05. Partidas y Tareas (Obra)"
            if re.search(r'cierre|entrega final|punch list', s, re.IGNORECASE):
                return "08. Observaciones & Entrega Final"
            return s
        df['Fase'] = df['Fase'].apply(_migrar_fase_item)

    st.session_state.original_tables[pestaña] = df.copy()
    return df


def guardar_tabla(conn, sheet_url, nube_ok, df, pestaña):
    """Guarda una tabla a Google Sheets / Google Drive (.XLSX) y a Excel local con validaciones de integridad."""
    # Protección contra borrado accidental de tablas críticas
    if pestaña in ['proyectos', 'tasks', 'maestro'] and (df is None or len(df) == 0):
        st.error(f"Guardado cancelado para '{pestaña}': Intento de sobreescribir con 0 filas.")
        return False

    original_df = st.session_state.get('original_tables', {}).get(pestaña)
    if original_df is not None and original_df.equals(df):
        return True

    # 1. Actualizar siempre el archivo Excel local / respaldo
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rutas_excel = list(dict.fromkeys([
        r"G:\My Drive\Cota App\BD_COTA_APP_PRUEBAS.xlsx",
        os.path.join(repo_root, "BD_COTA_APP_PRUEBAS.xlsx"),
        r"D:\cota-app\BD_COTA_APP_PRUEBAS.xlsx",
    ]))
    local_saved_path = None
    for p in rutas_excel:
        if _guardar_hoja_excel(p, pestaña, df) and local_saved_path is None:
            local_saved_path = p

    # 2. Si hay conexión en nube (Google Sheets nativo o archivo .XLSX en Google Drive)
    if nube_ok and sheet_url:
        guardado_nube = False
        if conn is not None:
            try:
                conn.update(spreadsheet=sheet_url, worksheet=pestaña, data=df)
                guardado_nube = True
            except Exception:
                try:
                    import gspread
                    client = conn.client._client
                    spreadsheet = client.open_by_url(sheet_url)
                    try:
                        spreadsheet.worksheet(pestaña)
                    except gspread.exceptions.WorksheetNotFound:
                        spreadsheet.add_worksheet(title=pestaña, rows="100", cols="25")
                    conn.update(spreadsheet=sheet_url, worksheet=pestaña, data=df)
                    guardado_nube = True
                except Exception:
                    guardado_nube = False

        # Si el archivo en Google Drive es un .XLSX (con etiqueta .XLSX), actualizar vía Google Drive API
        if not guardado_nube and local_saved_path and os.path.exists(local_saved_path):
            file_id = _extraer_file_id(sheet_url)
            session = _obtener_sesion_google()
            if file_id and session is not None:
                try:
                    with open(local_saved_path, "rb") as f_xlsx:
                        xlsx_bytes = f_xlsx.read()
                    up_url = f"https://www.googleapis.com/upload/drive/v3/files/{file_id}?uploadType=media&supportsAllDrives=true"
                    resp = session.patch(
                        up_url,
                        data=xlsx_bytes,
                        headers={"Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
                        timeout=20,
                    )
                    if resp.status_code in (200, 201):
                        st.session_state._cloud_xlsx_bytes = xlsx_bytes
                        guardado_nube = True
                except Exception:
                    pass

    if 'original_tables' in st.session_state:
        st.session_state.original_tables[pestaña] = df.copy()
    st.cache_data.clear()
    return True


def obtener_banco_fases() -> list[dict]:
    """
    Retorna el catálogo del Banco de Fases del estudio, combinando las fases predeterminadas
    con cualquier fase personalizada creada o existente en los proyectos.
    """
    if "banco_fases" not in st.session_state or not st.session_state.banco_fases:
        st.session_state.banco_fases = [dict(f) for f in BANCO_FASES_DEFAULT]

    # Eliminar cualquier fase residual de FF&E o Expediente Técnico
    st.session_state.banco_fases = [
        f for f in st.session_state.banco_fases
        if "ff&e" not in str(f.get("Fase", "")).lower()
        and "ffe" not in str(f.get("Fase", "")).lower()
        and "expediente" not in str(f.get("Fase", "")).lower()
    ]

    nombres_en_banco = {f["Fase"] for f in st.session_state.banco_fases}

    # Incorporar fases personalizadas que ya existan en la tabla fases de la BD
    if "fases" in st.session_state and isinstance(st.session_state.fases, pd.DataFrame) and not st.session_state.fases.empty:
        for _, r in st.session_state.fases.iterrows():
            f_nom = str(r.get("Fase", "")).strip()
            if (
                f_nom
                and "ff&e" not in f_nom.lower()
                and "ffe" not in f_nom.lower()
                and "expediente" not in f_nom.lower()
                and f_nom not in nombres_en_banco
            ):
                orden_max = max((item.get("Orden", 0) for item in st.session_state.banco_fases), default=0) + 1
                st.session_state.banco_fases.append({
                    "Orden": int(r.get("Orden", orden_max) or orden_max),
                    "Fase": f_nom,
                    "Etapa": str(r.get("Etapa", "Diseño") or "Diseño"),
                    "Dias": 10,
                    "Por_Defecto": False,
                })
                nombres_en_banco.add(f_nom)

    return sorted(st.session_state.banco_fases, key=lambda x: x.get("Orden", 99))


def agregar_fase_banco(nombre_fase: str, etapa: str = "Diseño", dias: int = 10, por_defecto: bool = False) -> dict:
    """Agrega una nueva fase al Banco de Fases del estudio si no existe."""
    banco = obtener_banco_fases()
    limpio = str(nombre_fase).strip()
    for f in banco:
        if f["Fase"].lower() == limpio.lower():
            return f
    nuevo_orden = max((f.get("Orden", 0) for f in banco), default=0) + 1
    nueva = {
        "Orden": nuevo_orden,
        "Fase": limpio,
        "Etapa": etapa,
        "Dias": max(1, int(dias)),
        "Por_Defecto": por_defecto,
    }
    st.session_state.banco_fases.append(nueva)
    return nueva


def sembrar_fases_default(nombre_proyecto, fecha_inicio=None, fases_seleccionadas=None):
    """
    Crea las fases de diseño para un proyecto.
    Si `fases_seleccionadas` es None, siembra las 8 fases canónicas por defecto.
    Si se pasa una lista de nombres de fases (del Banco de Fases), siembra únicamente las activadas.
    """
    f_ini = parse_date(fecha_inicio) or datetime.date.today()
    cursor = f_ini
    rows = []

    if fases_seleccionadas is None:
        plantilla = FASES_CANONICAS
    else:
        banco = obtener_banco_fases()
        mapa_banco = {f["Fase"]: f for f in banco}
        plantilla = []
        for idx_f, item in enumerate(fases_seleccionadas, start=1):
            if isinstance(item, dict):
                plantilla.append(item)
            elif str(item) in mapa_banco:
                plantilla.append(mapa_banco[str(item)])
            else:
                plantilla.append({"Orden": idx_f, "Fase": str(item), "Etapa": "Diseño", "Dias": 10})

    for idx_ord, f in enumerate(plantilla, start=1):
        dias = f.get('Dias', 7)
        cursor_fin = cursor + datetime.timedelta(days=dias)
        rows.append({
            'ID': f"FASE_{int(time.time())}_{uuid.uuid4().hex[:6]}",
            'Proyecto': nombre_proyecto,
            'Orden': f.get('Orden', idx_ord) if fases_seleccionadas is None else idx_ord,
            'Fase': f['Fase'],
            'Etapa': f.get('Etapa', 'Diseño'),
            'Inicio': cursor.strftime('%Y-%m-%d'),
            'Fin': cursor_fin.strftime('%Y-%m-%d'),
            'Estado': '⚪ No iniciada',
            'Avance_Pct': 0,
            'Responsable': '',
            'Aprobado_Cliente': False,
            'Notas': ''
        })
        cursor = cursor_fin + datetime.timedelta(days=1)

    return pd.DataFrame(rows, columns=COLS_FASES) if rows else pd.DataFrame(columns=COLS_FASES)


def sincronizar_fases_proyecto(nombre_proyecto: str, fases_activas_nombres: list[str], fecha_inicio=None):
    """
    Activa o desactiva fases para un proyecto específico según la selección del Banco de Fases.
    Conserva intactos los datos (avance, fechas, aprobaciones, notas) de las fases que ya estaban activas.
    """
    if 'fases' not in st.session_state or not isinstance(st.session_state.fases, pd.DataFrame):
        st.session_state.fases = pd.DataFrame(columns=COLS_FASES)

    df_all = st.session_state.fases
    df_otros = df_all[df_all['Proyecto'] != nombre_proyecto].copy()
    df_proy = df_all[df_all['Proyecto'] == nombre_proyecto].copy()

    banco = obtener_banco_fases()
    mapa_banco = {f["Fase"]: f for f in banco}
    orden_banco = {f["Fase"]: idx for idx, f in enumerate(banco, start=1)}

    f_ini_base = parse_date(fecha_inicio) or datetime.date.today()
    if not df_proy.empty:
        fechas_fin_exist = [parse_date(x) for x in df_proy['Fin'].tolist() if parse_date(x) is not None]
        cursor = (max(fechas_fin_exist) + datetime.timedelta(days=1)) if fechas_fin_exist else f_ini_base
    else:
        cursor = f_ini_base

    nuevas_filas_proy = []
    # Ordenar las fases seleccionadas según su orden en el banco
    fases_ordenadas = sorted(
        list(dict.fromkeys(fases_activas_nombres)),
        key=lambda nom: orden_banco.get(nom, 999)
    )

    for nuevo_ord, f_nom in enumerate(fases_ordenadas, start=1):
        match_exist = df_proy[df_proy['Fase'] == f_nom]
        if not match_exist.empty:
            fila = match_exist.iloc[0].to_dict()
            fila['Orden'] = nuevo_ord
            nuevas_filas_proy.append(fila)
        else:
            info_b = mapa_banco.get(f_nom, {"Fase": f_nom, "Etapa": "Diseño", "Dias": 10})
            dias = int(info_b.get("Dias", 10))
            c_fin = cursor + datetime.timedelta(days=dias)
            nuevas_filas_proy.append({
                'ID': f"FASE_{int(time.time())}_{uuid.uuid4().hex[:6]}",
                'Proyecto': nombre_proyecto,
                'Orden': nuevo_ord,
                'Fase': f_nom,
                'Etapa': info_b.get('Etapa', 'Diseño'),
                'Inicio': cursor.strftime('%Y-%m-%d'),
                'Fin': c_fin.strftime('%Y-%m-%d'),
                'Estado': '⚪ No iniciada',
                'Avance_Pct': 0,
                'Responsable': '',
                'Aprobado_Cliente': False,
                'Notas': ''
            })
            cursor = c_fin + datetime.timedelta(days=1)

    df_proy_nuevo = pd.DataFrame(nuevas_filas_proy, columns=COLS_FASES) if nuevas_filas_proy else pd.DataFrame(columns=COLS_FASES)
    st.session_state.fases = pd.concat([df_otros, df_proy_nuevo], ignore_index=True)
    clear_base_dfs()


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


def sanitizar_fases_estudio():
    """
    Limpia y actualiza el DataFrame de fases en st.session_state:
    - Elimina fases obsoletas de FF&E y Expediente Técnico
    - Renombra fases antiguas con los nuevos nombres de ventana
    - Normaliza el orden de 1 a N por proyecto
    """
    if "fases" not in st.session_state or not isinstance(st.session_state.fases, pd.DataFrame) or st.session_state.fases.empty:
        return

    df_f = st.session_state.fases.copy()

    # 1. Eliminar FF&E y Expediente Técnico
    mask_obsoletas = df_f['Fase'].astype(str).str.contains(r'ff&e|ffe|expediente t[eé]cnico', case=False, na=False)
    if mask_obsoletas.any():
        df_f = df_f[~mask_obsoletas].copy()

    # 2. Renombrar fases antiguas
    def _migrar_nombre_fase(nom):
        s = str(nom).strip()
        if re.search(r'ejecuci[oó]n|obra|montaje', s, re.IGNORECASE):
            return "05. Partidas y Tareas (Obra)"
        if re.search(r'cierre|entrega final|punch list', s, re.IGNORECASE):
            return "08. Observaciones & Entrega Final"
        return s

    df_f['Fase'] = df_f['Fase'].apply(_migrar_nombre_fase)

    # 3. Re-indexar orden por proyecto
    dfs_proy = []
    for proy_k, grp in df_f.groupby('Proyecto', sort=False):
        grp_sorted = grp.sort_values(by='Orden').copy()
        grp_sorted['Orden'] = list(range(1, len(grp_sorted) + 1))
        dfs_proy.append(grp_sorted)

    if dfs_proy:
        st.session_state.fases = pd.concat(dfs_proy, ignore_index=True)
    else:
        st.session_state.fases = df_f


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
    if widget_key not in st.session_state or base_key not in st.session_state:
        return

    try:
        edits = st.session_state.get(widget_key)
        if not edits or not isinstance(edits, dict):
            return
        df = st.session_state.get(base_key)
        if df is None or not isinstance(df, pd.DataFrame):
            return

        df_new = df.copy()

        # 1. Aplicar celdas editadas
        for idx, cols in edits.get("edited_rows", {}).items():
            row_idx = int(idx)
            for col, val in cols.items():
                if col in df_new.columns and df_new[col].dtype != object and isinstance(val, (str, datetime.date, datetime.datetime)):
                    df_new[col] = df_new[col].astype(object)
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
                df_new[id_col] = ""
            df_new[id_col] = df_new[id_col].astype(object)
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

        # Recalcular Presupuesto automáticamente en tasks si cambian Metrado o Valor_Unitario
        if master_state_key == 'tasks' and 'Metrado' in df_new.columns and 'Valor_Unitario' in df_new.columns and 'Presupuesto' in df_new.columns:
            for idx, cols in edits.get("edited_rows", {}).items():
                r_idx = int(idx)
                if r_idx in df_new.index and ('Metrado' in cols or 'Valor_Unitario' in cols) and 'Presupuesto' not in cols:
                    df_new.at[r_idx, 'Presupuesto'] = round(
                        float(df_new.at[r_idx, 'Metrado'] or 0.0) * float(df_new.at[r_idx, 'Valor_Unitario'] or 0.0), 2
                    )
            for i, row in df_new.iterrows():
                p_est = float(row.get('Presupuesto') or 0.0)
                met = float(row.get('Metrado') or 0.0)
                v_unit = float(row.get('Valor_Unitario') or 0.0)
                if p_est == 0.0 and met > 0 and v_unit > 0:
                    df_new.at[i, 'Presupuesto'] = round(met * v_unit, 2)

        # Normalizar Supervisado y defaults en tasks
        if master_state_key == 'tasks':
            if 'Supervisado' in df_new.columns:
                df_new['Supervisado'] = df_new['Supervisado'].apply(_normalizar_supervisado)
            if 'Moneda' in df_new.columns:
                df_new['Moneda'] = df_new['Moneda'].fillna("Soles").replace("", "Soles").replace("None", "Soles")
            if 'Unidad' in df_new.columns:
                df_new['Unidad'] = df_new['Unidad'].fillna("glb").replace("", "glb").replace("None", "glb")
            if 'Metrado' in df_new.columns:
                df_new['Metrado'] = pd.to_numeric(df_new['Metrado'], errors='coerce').fillna(1.0)
            if 'Valor_Unitario' in df_new.columns:
                df_new['Valor_Unitario'] = pd.to_numeric(df_new['Valor_Unitario'], errors='coerce').fillna(0.0)

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

            if master_state_key == 'tasks':
                for k in list(st.session_state.keys()):
                    if str(k).startswith("base_df_ppto_"):
                        del st.session_state[k]

        # 7. Incrementar contador de widget para forzar clave nueva y evitar duplicaciones
        c_key = f"c_{base_key}"
        st.session_state[c_key] = st.session_state.get(c_key, 0) + 1
    except Exception:
        return
