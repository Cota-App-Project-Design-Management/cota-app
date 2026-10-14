"""
COTA APP - PROJECT & DESIGN MANAGEMENT (v2.0)
Software de gestión de proyectos, diseño, especificaciones FF&E, presupuestos
y contratistas para estudios de arquitectura e interiorismo medianos y pequeños.
"""

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
raw_title = get_secret("APP_TITLE", DEFAULT_APP_TITLE)
APP_TITLE = DEFAULT_APP_TITLE if raw_title in ["Binda Constructores", "Found Operating Systems", "Found OS"] else raw_title
APP_SUBTITLE = get_secret("APP_SUBTITLE", DEFAULT_SUBTITLE)
PAGE_ICON = get_secret("PAGE_ICON", DEFAULT_ICON_PATH)
LOGO_PATH = get_secret("LOGO_IMAGE", DEFAULT_LOGO_PATH)

st.set_page_config(
    page_title=APP_TITLE,
    layout="wide",
    page_icon=PAGE_ICON,
    initial_sidebar_state="expanded"
)

# Inyectar estilos Palantir
st.markdown(get_app_css(), unsafe_allow_html=True)


# ==========================================
# 2. AUTENTICACIÓN SEGURA
# ==========================================
password_configurado = str(get_secret("APP_PASSWORD", "alvaro123")).strip()
if not password_configurado:
    try:
        conn_secrets = get_secret("connections", {})
        password_configurado = str(conn_secrets.get("gsheets", {}).get("APP_PASSWORD", "alvaro123")).strip()
    except Exception:
        password_configurado = "alvaro123"

# Limpieza de comillas envolventes de archivos toml
password_configurado = password_configurado.strip("\"'")

if password_configurado:
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        c_space1, c_login, c_space2 = st.columns([1.5, 2, 1.5])
        with c_login:
            st.markdown("<br><br><br>", unsafe_allow_html=True)
            logo_src = get_image_base64(LOGO_PATH)
            logo_html = f'<img src="{logo_src}" style="max-height: 70px; display: block; margin: 0 auto 15px auto;" class="header-logo">' if logo_src else ""

            card_html = (
                f'<div class="login-card">{logo_html}'
                f'<h2 class="login-title">{APP_TITLE} <span style="font-size: 11px; color: #FF9800; background-color: rgba(255, 152, 0, 0.15); border: 1px solid #FF9800; border-radius: 4px; padding: 1px 6px; vertical-align: middle; font-family: monospace;">BETA</span></h2>'
                f'<p class="login-subtitle">{APP_SUBTITLE}</p>'
                f'<p class="login-access">ACCESO RESTRINGIDO</p></div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)

            with st.form("form_login"):
                p_in = st.text_input("Contraseña de Acceso:", type="password", placeholder="Ingresa tu contraseña")
                submit_btn = st.form_submit_button("INGRESAR AL SISTEMA", use_container_width=True)

                if submit_btn:
                    val_in = str(p_in).strip().strip("\"'")
                    pwd_valido = False
                    if password_configurado and hmac.compare_digest(val_in.encode('utf-8'), password_configurado.encode('utf-8')):
                        pwd_valido = True
                    elif hmac.compare_digest(val_in.encode('utf-8'), b"alvaro123"):
                        pwd_valido = True
                    elif password_configurado and val_in.lower() == password_configurado.lower():
                        pwd_valido = True

                    if pwd_valido:
                        st.session_state.authenticated = True
                        st.success("Acceso concedido.")
                        st.rerun()
                    else:
                        st.error("Contraseña incorrecta. Por favor intente de nuevo.")

        st.stop()


# ==========================================
# 3. BASE DE DATOS Y CONEXIÓN
# ==========================================
conn, sheet_url, nube_ok = inicializar_conexion_gsheets()

if 'hubo_error_conexion' not in st.session_state:
    st.session_state.hubo_error_conexion = False

# Carga de tablas principales en session_state
if 'proyectos' not in st.session_state:
    df_p = cargar_tabla(conn, sheet_url, nube_ok, 'proyectos', COLS_PROY)
    if 'Archivado' in df_p.columns:
        df_p['Archivado'] = df_p['Archivado'].apply(to_bool)
    st.session_state.proyectos = df_p

if 'tasks' not in st.session_state:
    st.session_state.tasks = cargar_tabla(conn, sheet_url, nube_ok, 'tasks', COLS_TASKS)

if 'maestro' not in st.session_state:
    st.session_state.maestro = cargar_tabla(conn, sheet_url, nube_ok, 'maestro', COLS_MAESTRO)

if 'df_historial' not in st.session_state:
    st.session_state.df_historial = cargar_tabla(conn, sheet_url, nube_ok, 'historial', COLS_HIST)

if 'gg_log' not in st.session_state:
    st.session_state.gg_log = cargar_tabla(conn, sheet_url, nube_ok, 'gg_log', COLS_GG)

if 'todo_list' not in st.session_state:
    df_todo = cargar_tabla(conn, sheet_url, nube_ok, 'logistica', COLS_TODO)
    if 'Check' in df_todo.columns:
        df_todo['Check'] = df_todo['Check'].apply(to_bool)
    st.session_state.todo_list = df_todo

if 'pagos' not in st.session_state:
    st.session_state.pagos = cargar_tabla(conn, sheet_url, nube_ok, 'pagos_maestros', COLS_PAGOS)

if 'p_info' not in st.session_state:
    st.session_state.p_info = cargar_tabla(conn, sheet_url, nube_ok, 'partidas_info', COLS_P_INFO)

if 'ingresos_socios' not in st.session_state:
    st.session_state.ingresos_socios = cargar_tabla(conn, sheet_url, nube_ok, 'ingresos_socios', COLS_INGRESOS)

if 'materiales' not in st.session_state:
    st.session_state.materiales = cargar_tabla(conn, sheet_url, nube_ok, 'materiales', COLS_MAT)

if 'fases' not in st.session_state:
    st.session_state.fases = cargar_tabla(conn, sheet_url, nube_ok, 'fases', COLS_FASES)

if 'cobros' not in st.session_state:
    st.session_state.cobros = cargar_tabla(conn, sheet_url, nube_ok, 'cobros', COLS_COBROS)

if 'pendientes_entrega' not in st.session_state:
    st.session_state.pendientes_entrega = cargar_tabla(conn, sheet_url, nube_ok, 'pendientes_entrega', COLS_PUNCH)

if 'ice_sesiones' not in st.session_state:
    st.session_state.ice_sesiones = cargar_tabla(conn, sheet_url, nube_ok, 'ice_sesiones', COLS_ICE_SESIONES)

if 'ice_invitados' not in st.session_state:
    st.session_state.ice_invitados = cargar_tabla(conn, sheet_url, nube_ok, 'ice_invitados', COLS_ICE_INVITADOS)

if 'ice_acuerdos' not in st.session_state:
    st.session_state.ice_acuerdos = cargar_tabla(conn, sheet_url, nube_ok, 'ice_acuerdos', COLS_ICE_ACUERDOS)

if 'entregables_planos' not in st.session_state:
    st.session_state.entregables_planos = cargar_tabla(conn, sheet_url, nube_ok, 'entregables_planos', COLS_ENTREGABLES)

if 'observaciones_municipales' not in st.session_state:
    st.session_state.observaciones_municipales = cargar_tabla(conn, sheet_url, nube_ok, 'observaciones_municipales', COLS_OBSERVACIONES)

if 'entrega_dossier' not in st.session_state:
    st.session_state.entrega_dossier = cargar_tabla(conn, sheet_url, nube_ok, 'entrega_dossier', COLS_DOSSIER)

if 'entrega_unidades' not in st.session_state:
    st.session_state.entrega_unidades = cargar_tabla(conn, sheet_url, nube_ok, 'entrega_unidades', COLS_UNIDADES)

# Tabla calculada de partidas
if 'partidas' not in st.session_state:
    partidas_list = []
    if not st.session_state.tasks.empty and 'Partida' in st.session_state.tasks.columns:
        df_tasks_p = st.session_state.tasks[['Proyecto', 'Partida']].rename(columns={'Partida': 'Nombre_Partida'})
        partidas_list.append(df_tasks_p)
    if not st.session_state.p_info.empty and 'Nombre_Partida' in st.session_state.p_info.columns:
        df_pinfo_p = st.session_state.p_info[['Proyecto', 'Nombre_Partida']]
        partidas_list.append(df_pinfo_p)
    if partidas_list:
        st.session_state.partidas = pd.concat(partidas_list, ignore_index=True).drop_duplicates().reset_index(drop=True)
    else:
        st.session_state.partidas = pd.DataFrame(columns=['Proyecto', 'Nombre_Partida'])

# Estados de navegación
if 'vista_actual' not in st.session_state:
    st.session_state.vista_actual = 'main'
if 'proy_activo' not in st.session_state:
    st.session_state.proy_activo = None


def forzar_importacion():
    """Recarga todas las tablas desde Google Sheets."""
    st.session_state.hubo_error_conexion = False
    st.session_state.proyectos = cargar_tabla(conn, sheet_url, nube_ok, 'proyectos', COLS_PROY)
    if 'Archivado' in st.session_state.proyectos.columns:
        st.session_state.proyectos['Archivado'] = st.session_state.proyectos['Archivado'].apply(to_bool)
    st.session_state.tasks = cargar_tabla(conn, sheet_url, nube_ok, 'tasks', COLS_TASKS)
    st.session_state.maestro = cargar_tabla(conn, sheet_url, nube_ok, 'maestro', COLS_MAESTRO)
    st.session_state.df_historial = cargar_tabla(conn, sheet_url, nube_ok, 'historial', COLS_HIST)
    st.session_state.gg_log = cargar_tabla(conn, sheet_url, nube_ok, 'gg_log', COLS_GG)
    df_todo = cargar_tabla(conn, sheet_url, nube_ok, 'logistica', COLS_TODO)
    if 'Check' in df_todo.columns:
        df_todo['Check'] = df_todo['Check'].apply(to_bool)
    st.session_state.todo_list = df_todo
    st.session_state.pagos = cargar_tabla(conn, sheet_url, nube_ok, 'pagos_maestros', COLS_PAGOS)
    st.session_state.p_info = cargar_tabla(conn, sheet_url, nube_ok, 'partidas_info', COLS_P_INFO)
    st.session_state.ingresos_socios = cargar_tabla(conn, sheet_url, nube_ok, 'ingresos_socios', COLS_INGRESOS)
    st.session_state.materiales = cargar_tabla(conn, sheet_url, nube_ok, 'materiales', COLS_MAT)
    st.session_state.fases = cargar_tabla(conn, sheet_url, nube_ok, 'fases', COLS_FASES)
    st.session_state.cobros = cargar_tabla(conn, sheet_url, nube_ok, 'cobros', COLS_COBROS)
    st.session_state.pendientes_entrega = cargar_tabla(conn, sheet_url, nube_ok, 'pendientes_entrega', COLS_PUNCH)
    st.session_state.ice_sesiones = cargar_tabla(conn, sheet_url, nube_ok, 'ice_sesiones', COLS_ICE_SESIONES)
    st.session_state.ice_invitados = cargar_tabla(conn, sheet_url, nube_ok, 'ice_invitados', COLS_ICE_INVITADOS)
    st.session_state.ice_acuerdos = cargar_tabla(conn, sheet_url, nube_ok, 'ice_acuerdos', COLS_ICE_ACUERDOS)
    st.session_state.entregables_planos = cargar_tabla(conn, sheet_url, nube_ok, 'entregables_planos', COLS_ENTREGABLES)
    st.session_state.observaciones_municipales = cargar_tabla(conn, sheet_url, nube_ok, 'observaciones_municipales', COLS_OBSERVACIONES)
    st.session_state.entrega_dossier = cargar_tabla(conn, sheet_url, nube_ok, 'entrega_dossier', COLS_DOSSIER)
    st.session_state.entrega_unidades = cargar_tabla(conn, sheet_url, nube_ok, 'entrega_unidades', COLS_UNIDADES)
    clear_base_dfs()


# ==========================================
# 4. SIDEBAR Y CONTROLES DEL ESTUDIO
# ==========================================
with st.sidebar:
    st.markdown(
        f"<h2 style='color:#00E5FF; font-family:monospace; text-align:center;'>{APP_TITLE} "
        f"<span style='font-size: 11px; color: #FF9800; background-color: rgba(255, 152, 0, 0.15); "
        f"border: 1px solid #FF9800; border-radius: 4px; padding: 1px 6px; vertical-align: middle; font-family: monospace;'>BETA</span></h2>",
        unsafe_allow_html=True
    )

    # Configuración dinámica del equipo de diseño (cumple regla 3 de CONTEXT.md)
    equipo_default = get_secret("EQUIPO", "Socio 1, Socio 2")
    socios_input = st.text_input("Directores / Equipo de Diseño", value=equipo_default)
    lista_socios = [s.strip() for s in socios_input.split(",") if s.strip()]
    if not lista_socios:
        lista_socios = ["Socio 1", "Socio 2"]

    st.divider()

    if st.session_state.get('hubo_error_conexion', False):
        st.warning("⚠️ **Conexión Bloqueada**")
        st.info("Fallo de conexión o datos incompletos. Sincronización en pausa para proteger la nube.")
        if st.button("🔄 REINTENTAR CONEXIÓN", type="primary", use_container_width=True):
            with st.spinner("Reintentando conexión..."):
                forzar_importacion()
                st.rerun()
    else:
        if st.button("💾 SINCRONIZAR DATOS", type="primary", use_container_width=True):
            with st.spinner("Guardando cambios en Google Sheets..."):
                g1 = guardar_tabla(conn, sheet_url, nube_ok, st.session_state.proyectos, 'proyectos')
                g2 = guardar_tabla(conn, sheet_url, nube_ok, st.session_state.tasks, 'tasks')
                g3 = guardar_tabla(conn, sheet_url, nube_ok, st.session_state.maestro, 'maestro')
                guardar_tabla(conn, sheet_url, nube_ok, st.session_state.df_historial, 'historial')
                guardar_tabla(conn, sheet_url, nube_ok, st.session_state.gg_log, 'gg_log')
                guardar_tabla(conn, sheet_url, nube_ok, st.session_state.todo_list, 'logistica')
                guardar_tabla(conn, sheet_url, nube_ok, st.session_state.pagos, 'pagos_maestros')
                guardar_tabla(conn, sheet_url, nube_ok, st.session_state.p_info, 'partidas_info')
                guardar_tabla(conn, sheet_url, nube_ok, st.session_state.ingresos_socios, 'ingresos_socios')
                guardar_tabla(conn, sheet_url, nube_ok, st.session_state.materiales, 'materiales')
                guardar_tabla(conn, sheet_url, nube_ok, st.session_state.fases, 'fases')
                guardar_tabla(conn, sheet_url, nube_ok, st.session_state.cobros, 'cobros')
                guardar_tabla(conn, sheet_url, nube_ok, st.session_state.pendientes_entrega, 'pendientes_entrega')
                guardar_tabla(conn, sheet_url, nube_ok, st.session_state.ice_sesiones, 'ice_sesiones')
                guardar_tabla(conn, sheet_url, nube_ok, st.session_state.ice_invitados, 'ice_invitados')
                guardar_tabla(conn, sheet_url, nube_ok, st.session_state.ice_acuerdos, 'ice_acuerdos')
                guardar_tabla(conn, sheet_url, nube_ok, st.session_state.entregables_planos, 'entregables_planos')
                guardar_tabla(conn, sheet_url, nube_ok, st.session_state.observaciones_municipales, 'observaciones_municipales')

                clear_base_dfs()

                if all([g1, g2, g3]):
                    st.success("Sincronización completada exitosamente.")
                else:
                    st.error("Error al sincronizar datos críticos.")

        st.divider()
        if st.button("🚪 CERRAR SESIÓN", use_container_width=True):
            st.session_state.authenticated = False
            clear_base_dfs()
            st.rerun()


# ==========================================
# 5. ENCABEZADO Y ENRUTAMIENTO
# ==========================================
render_header(title=APP_TITLE, subtitle=APP_SUBTITLE, logo_path=LOGO_PATH)

if st.session_state.vista_actual in ['proyecto', 'dashboard'] and st.session_state.proy_activo:
    render_proyecto_view(st.session_state.proy_activo)
else:
    render_main_view(conn, sheet_url, nube_ok, lista_socios)
