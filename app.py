"""
COTA APP - PROJECT & DESIGN MANAGEMENT (v2.0)
Software de gestión de proyectos, diseño, especificaciones FF&E, presupuestos
y contratistas para estudios de arquitectura e interiorismo medianos y pequeños.
"""

import hashlib
import hmac
import pandas as pd
import streamlit as st

from cota.config import (
    DEFAULT_APP_TITLE,
    DEFAULT_ICON_PATH,
    DEFAULT_LOGO_PATH,
    DEFAULT_SUBTITLE,
    get_secret,
)
from cota.db import (
    COLS_COBROS,
    COLS_DOSSIER,
    COLS_ENTREGABLES,
    COLS_FASES,
    COLS_GG,
    COLS_HIST,
    COLS_ICE_ACUERDOS,
    COLS_ICE_INVITADOS,
    COLS_ICE_SESIONES,
    COLS_INGRESOS,
    COLS_MAESTRO,
    COLS_MAT,
    COLS_OBSERVACIONES,
    COLS_P_INFO,
    COLS_PAGOS,
    COLS_PROY,
    COLS_PUNCH,
    COLS_TASKS,
    COLS_TODO,
    COLS_UNIDADES,
    cargar_tabla,
    clear_base_dfs,
    guardar_tabla,
    inicializar_conexion_gsheets,
)
from cota.ui.components import render_header
from cota.ui.styles import get_app_css
from cota.ui.views_main import render_main_view
from cota.ui.views_project import render_proyecto_view
from cota.utils import get_image_base64, to_bool


# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
# ==========================================
ACCENT_COLOR = "#D96B43"  # Rojo tipo arcilla - Identidad Cota App

APP_TITLE = get_secret("APP_TITLE", DEFAULT_APP_TITLE)
APP_SUBTITLE = get_secret("APP_SUBTITLE", DEFAULT_SUBTITLE)
PAGE_ICON = get_secret("PAGE_ICON", DEFAULT_ICON_PATH)
LOGO_PATH = get_secret("LOGO_IMAGE", DEFAULT_LOGO_PATH)

st.set_page_config(
    page_title=APP_TITLE,
    layout="wide",
    page_icon=PAGE_ICON,
    initial_sidebar_state="expanded",
)

st.markdown(get_app_css(), unsafe_allow_html=True)


# ==========================================
# 2. AUTENTICACIÓN SEGURA (SIN BACKDOORS)
# ==========================================
def obtener_password_secreto() -> str:
    """Obtiene la contraseña configurada en Secrets (raíz o bloque gsheets)."""
    pwd = str(get_secret("APP_PASSWORD", "")).strip().strip("\"'")
    if not pwd:
        try:
            conn_secrets = get_secret("connections", {})
            pwd = str(conn_secrets.get("gsheets", {}).get("APP_PASSWORD", "")).strip().strip("\"'")
        except Exception:
            pwd = ""
    return pwd


password_configurado = obtener_password_secreto()

if password_configurado:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        _, c_login, _ = st.columns([1.5, 2, 1.5])
        with c_login:
            st.markdown("<br><br><br>", unsafe_allow_html=True)
            logo_src = get_image_base64(LOGO_PATH)
            logo_html = (
                f'<img src="{logo_src}" style="max-height: 70px; display: block; margin: 0 auto 15px auto;" class="header-logo">'
                if logo_src
                else ""
            )

            card_html = (
                f'<div class="login-card">{logo_html}'
                f'<h2 class="login-title">{APP_TITLE} '
                f'<span style="font-size: 11px; color: {ACCENT_COLOR}; background-color: rgba(217, 107, 67, 0.15); '
                f'border: 1px solid {ACCENT_COLOR}; border-radius: 4px; padding: 1px 6px; vertical-align: middle; font-family: monospace;">BETA</span></h2>'
                f'<p class="login-subtitle">{APP_SUBTITLE}</p>'
                f'<p class="login-access">ACCESO PRIVADO</p></div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)

            with st.form("form_login"):
                p_in = st.text_input(
                    "Contraseña de Acceso:",
                    type="password",
                    placeholder="Ingresa la clave del estudio",
                )
                submit_btn = st.form_submit_button("INGRESAR AL SISTEMA", use_container_width=True)

                if submit_btn:
                    val_in = str(p_in).strip().strip("\"'")
                    if hmac.compare_digest(val_in.encode("utf-8"), password_configurado.encode("utf-8")):
                        st.session_state.authenticated = True
                        st.rerun()
                    else:
                        st.error("Contraseña incorrecta. Verifica con la dirección del estudio.")

        st.stop()


# ==========================================
# 3. ESQUEMA DE BASE DE DATOS Y SINCRONIZACIÓN
# ==========================================
conn, sheet_url, nube_ok = inicializar_conexion_gsheets()

if "hubo_error_conexion" not in st.session_state:
    st.session_state.hubo_error_conexion = False

# Tablas activas propias de Cota App (Estudio de Arquitectura e Interiorismo)
# Formato: clave_session_state: (nombre_hoja_gsheets, columnas, columna_booleana_opcional)
TABLAS_ESTUDIO = {
    "proyectos": ("proyectos", COLS_PROY, "Archivado"),
    "tasks": ("tasks", COLS_TASKS, None),
    "maestro": ("maestro", COLS_MAESTRO, None),
    "df_historial": ("historial", COLS_HIST, None),
    "gg_log": ("gg_log", COLS_GG, None),
    "todo_list": ("logistica", COLS_TODO, "Check"),
    "pagos": ("pagos_maestros", COLS_PAGOS, None),
    "p_info": ("partidas_info", COLS_P_INFO, None),
    "ingresos_socios": ("ingresos_socios", COLS_INGRESOS, None),
    "materiales": ("materiales", COLS_MAT, None),
    "fases": ("fases", COLS_FASES, None),
    "cobros": ("cobros", COLS_COBROS, None),
    "pendientes_entrega": ("pendientes_entrega", COLS_PUNCH, None),
    "entregables_planos": ("entregables_planos", COLS_ENTREGABLES, None),
    "observaciones_municipales": ("observaciones_municipales", COLS_OBSERVACIONES, None),
}

# Tablas deprecadas (se mantienen vacías en RAM para compatibilidad hasta limpiar vistas)
TABLAS_DEPRECADAS = {
    "ice_sesiones": COLS_ICE_SESIONES,
    "ice_invitados": COLS_ICE_INVITADOS,
    "ice_acuerdos": COLS_ICE_ACUERDOS,
    "entrega_dossier": COLS_DOSSIER,
    "entrega_unidades": COLS_UNIDADES,
}


def calcular_hash_df(df: pd.DataFrame) -> str:
    """Genera un hash rápido del contenido del DataFrame para detectar cambios."""
    if df is None or df.empty:
        return "empty"
    return hashlib.md5(df.to_csv(index=False).encode("utf-8")).hexdigest()


def recalcular_partidas():
    """Actualiza el catálogo consolidado de partidas a partir de tasks y p_info."""
    partidas_list = []
    if "tasks" in st.session_state and not st.session_state.tasks.empty and "Partida" in st.session_state.tasks.columns:
        df_tasks_p = st.session_state.tasks[["Proyecto", "Partida"]].rename(columns={"Partida": "Nombre_Partida"})
        partidas_list.append(df_tasks_p)
    if "p_info" in st.session_state and not st.session_state.p_info.empty and "Nombre_Partida" in st.session_state.p_info.columns:
        df_pinfo_p = st.session_state.p_info[["Proyecto", "Nombre_Partida"]]
        partidas_list.append(df_pinfo_p)

    if partidas_list:
        st.session_state.partidas = (
            pd.concat(partidas_list, ignore_index=True).drop_duplicates().reset_index(drop=True)
        )
    else:
        st.session_state.partidas = pd.DataFrame(columns=["Proyecto", "Nombre_Partida"])


def cargar_todas_las_tablas(forzar: bool = False):
    """Carga las tablas de Cota App en session_state y guarda su huella inicial."""
    if "hashes_tablas" not in st.session_state:
        st.session_state.hashes_tablas = {}

    for key, (sheet_name, cols, bool_col) in TABLAS_ESTUDIO.items():
        if forzar or key not in st.session_state:
            df = cargar_tabla(conn, sheet_url, nube_ok, sheet_name, cols)
            if bool_col and bool_col in df.columns:
                df[bool_col] = df[bool_col].apply(to_bool)
            st.session_state[key] = df
            st.session_state.hashes_tablas[key] = calcular_hash_df(df)

    for key, cols in TABLAS_DEPRECADAS.items():
        if key not in st.session_state:
            st.session_state[key] = pd.DataFrame(columns=cols)

    recalcular_partidas()


def forzar_importacion():
    """Recarga todas las tablas desde Google Sheets y limpia cachés."""
    st.session_state.hubo_error_conexion = False
    cargar_todas_las_tablas(forzar=True)
    clear_base_dfs()


def sincronizar_cambios() -> tuple[bool, int]:
    """
    Guarda en Google Sheets únicamente las tablas que fueron modificadas en la sesión.
    Evita exceder la cuota de peticiones de Google API.
    """
    if "hashes_tablas" not in st.session_state:
        st.session_state.hashes_tablas = {}

    tablas_guardadas = 0
    errores = []

    for key, (sheet_name, _, _) in TABLAS_ESTUDIO.items():
        df_actual = st.session_state.get(key)
        hash_actual = calcular_hash_df(df_actual)
        hash_previo = st.session_state.hashes_tablas.get(key)

        if hash_actual != hash_previo:
            ok = guardar_tabla(conn, sheet_url, nube_ok, df_actual, sheet_name)
            if ok:
                st.session_state.hashes_tablas[key] = hash_actual
                tablas_guardadas += 1
            else:
                errores.append(sheet_name)

    recalcular_partidas()
    clear_base_dfs()
    return (len(errores) == 0, tablas_guardadas)


# Inicialización de datos y navegación
cargar_todas_las_tablas(forzar=False)

if "vista_actual" not in st.session_state:
    st.session_state.vista_actual = "main"
if "proy_activo" not in st.session_state:
    st.session_state.proy_activo = None


# ==========================================
# 4. SIDEBAR Y CONTROLES DEL ESTUDIO
# ==========================================
with st.sidebar:
    st.markdown(
        f"<h2 style='color:{ACCENT_COLOR}; font-family:monospace; text-align:center;'>{APP_TITLE} "
        f"<span style='font-size: 11px; color: {ACCENT_COLOR}; background-color: rgba(217, 107, 67, 0.15); "
        f"border: 1px solid {ACCENT_COLOR}; border-radius: 4px; padding: 1px 6px; vertical-align: middle; font-family: monospace;'>BETA</span></h2>",
        unsafe_allow_html=True,
    )

    # Configuración dinámica del equipo de diseño
    equipo_default = get_secret("EQUIPO", "Socio 1, Socio 2")
    socios_input = st.text_input("Directores / Equipo de Diseño", value=equipo_default)
    lista_socios = [s.strip() for s in socios_input.split(",") if s.strip()]
    if not lista_socios:
        lista_socios = ["Socio 1", "Socio 2"]

    st.divider()

    if st.session_state.get("hubo_error_conexion", False):
        st.warning("Conexión Bloqueada")
        st.info("Fallo de conexión o pestañas faltantes en Google Sheets. Sincronización en pausa.")
        if st.button("REINTENTAR CONEXIÓN", type="primary", use_container_width=True):
            with st.spinner("Reconectando con Google Sheets..."):
                forzar_importacion()
                st.rerun()
    else:
        if st.button("SINCRONIZAR DATOS", type="primary", use_container_width=True):
            with st.spinner("Sincronizando cambios con Google Sheets..."):
                exito, cantidad = sincronizar_cambios()
                if exito and cantidad > 0:
                    st.success(f"Sincronización completada ({cantidad} tabla(s) actualizada(s)).")
                elif exito and cantidad == 0:
                    st.info("No hay cambios pendientes por guardar.")
                else:
                    st.error("Error al sincronizar una o más tablas con Google Sheets.")

        if st.button("RECARGAR DESDE NUBE", use_container_width=True):
            with st.spinner("Actualizando datos desde Google Sheets..."):
                forzar_importacion()
                st.rerun()

        st.divider()
        if st.button("CERRAR SESIÓN", use_container_width=True):
            st.session_state.authenticated = False
            clear_base_dfs()
            st.rerun()


# ==========================================
# 5. ENCABEZADO Y ENRUTAMIENTO
# ==========================================
render_header(title=APP_TITLE, subtitle=APP_SUBTITLE, logo_path=LOGO_PATH)

if st.session_state.vista_actual in ["proyecto", "dashboard"] and st.session_state.proy_activo:
    render_proyecto_view(st.session_state.proy_activo)
else:
    render_main_view(conn, sheet_url, nube_ok, lista_socios)
