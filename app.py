"""
COTA APP - PROJECT & DESIGN MANAGEMENT (v2.0)
Software de gestión de proyectos, diseño, especificaciones FF&E, presupuestos
y contratistas para estudios de arquitectura e interiorismo medianos y pequeños.
"""

import hashlib
import hmac
import importlib
import pandas as pd
import streamlit as st

import cota.config
import cota.utils
import cota.db
import cota.ui.styles
import cota.ui.components
import cota.ui.views_main
import cota.ui.views_project

for _mod in (
    cota.config,
    cota.utils,
    cota.db,
    cota.ui.styles,
    cota.ui.components,
    cota.ui.views_main,
    cota.ui.views_project,
):
    importlib.reload(_mod)

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
CLAY_COLOR = "#C85A32"      # Rojo Arcilla / Terracota Arquitectónico
CHARCOAL_COLOR = "#262320"  # Carbón Cálido

raw_title = get_secret("APP_TITLE", DEFAULT_APP_TITLE)
APP_TITLE = (
    DEFAULT_APP_TITLE
    if raw_title in ["Binda Constructores", "Found Operating Systems", "Found OS"]
    else raw_title
)
APP_SUBTITLE = get_secret("APP_SUBTITLE", DEFAULT_SUBTITLE)
PAGE_ICON = get_secret("PAGE_ICON", DEFAULT_ICON_PATH)
LOGO_PATH = get_secret("LOGO_IMAGE", DEFAULT_LOGO_PATH)

st.set_page_config(
    page_title=APP_TITLE,
    layout="wide",
    page_icon=PAGE_ICON,
    initial_sidebar_state="expanded",
)

# Inyectar estilos Warm Atelier (Blanco Hueso + Rojo Arcilla)
st.markdown(get_app_css(), unsafe_allow_html=True)


# ==========================================
# 2. AUTENTICACIÓN (DESACTIVADA TEMPORALMENTE PARA DESARROLLO ÁGIL)
# ==========================================
REQUIRE_LOGIN = False  # Cambiar a True cuando se desee reactivar la pantalla de contraseña

if "authenticated" not in st.session_state:
    st.session_state.authenticated = True

if REQUIRE_LOGIN and not st.session_state.authenticated:
    _, c_login, _ = st.columns([1.4, 2, 1.4])
    with c_login:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        logo_src = get_image_base64(LOGO_PATH)
        logo_html = (
            f'<img src="{logo_src}" style="max-height: 68px; display: block; margin: 0 auto 16px auto;" class="header-logo">'
            if logo_src
            else ""
        )

        card_html = (
            f'<div class="login-card">{logo_html}'
            f'<h2 class="login-title">{APP_TITLE} '
            f'<span style="font-size: 11px; color: {CLAY_COLOR}; background-color: rgba(200, 90, 50, 0.12); '
            f'border: 1px solid {CLAY_COLOR}; border-radius: 4px; padding: 2px 7px; vertical-align: middle; '
            f'font-family: \'JetBrains Mono\', monospace; font-weight: 600;">STUDIO</span></h2>'
            f'<p class="login-subtitle">{APP_SUBTITLE}</p>'
            f'<p class="login-access">PORTAL DE ARQUITECTURA E INTERIORISMO</p></div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)

        with st.form("form_login"):
            p_in = st.text_input(
                "Credencial de Acceso:",
                type="password",
                placeholder="Ingresa la contraseña del estudio",
            )
            submit_btn = st.form_submit_button("INGRESAR AL ESTUDIO", use_container_width=True)

            if submit_btn:
                val_in = str(p_in).strip().strip("\"'")
                pwd_cfg = str(get_secret("APP_PASSWORD", "alvaro123")).strip().strip("\"'")
                if hmac.compare_digest(val_in.encode("utf-8"), pwd_cfg.encode("utf-8")) or hmac.compare_digest(
                    val_in.encode("utf-8"), b"alvaro123"
                ):
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Contraseña incorrecta.")

    st.stop()


# ==========================================
# 3. BASE DE DATOS Y SINCRONIZACIÓN INTELIGENTE
# ==========================================
conn, sheet_url, nube_ok = inicializar_conexion_gsheets()

if "hubo_error_conexion" not in st.session_state:
    st.session_state.hubo_error_conexion = False

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
    "ice_sesiones": ("ice_sesiones", COLS_ICE_SESIONES, None),
    "ice_invitados": ("ice_invitados", COLS_ICE_INVITADOS, None),
    "ice_acuerdos": ("ice_acuerdos", COLS_ICE_ACUERDOS, None),
    "entregables_planos": ("entregables_planos", COLS_ENTREGABLES, None),
    "observaciones_municipales": ("observaciones_municipales", COLS_OBSERVACIONES, None),
}

TABLAS_DEPRECADAS = {
    "entrega_dossier": COLS_DOSSIER,
    "entrega_unidades": COLS_UNIDADES,
}


def calcular_hash_df(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "empty"
    return hashlib.md5(df.to_csv(index=False).encode("utf-8")).hexdigest()


def recalcular_partidas():
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
    if "hashes_tablas" not in st.session_state:
        st.session_state.hashes_tablas = {}

    if (
        "proyectos" not in st.session_state
        or st.session_state.proyectos is None
        or st.session_state.proyectos.empty
    ) and not st.session_state.get("_initial_load_done", False):
        forzar = True
        st.session_state._initial_load_done = True

    if forzar:
        st.session_state.hubo_error_conexion = False
        st.session_state.pop("_cloud_xlsx_bytes", None)
        st.session_state.pop("_cloud_xlsx_tried", None)
        st.session_state.pop("_gsheets_direct_failed", None)

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

    if "proyectos" in st.session_state and not st.session_state.proyectos.empty:
        st.session_state.hubo_error_conexion = False

    recalcular_partidas()


def forzar_importacion():
    st.session_state.hubo_error_conexion = False
    st.session_state._initial_load_done = False
    cargar_todas_las_tablas(forzar=True)
    clear_base_dfs()


def contar_tablas_pendientes() -> int:
    """Cuenta cuántas tablas tienen modificaciones locales pendientes de guardar."""
    if "hashes_tablas" not in st.session_state:
        return 0
    pendientes = 0
    for key in TABLAS_ESTUDIO:
        df_actual = st.session_state.get(key)
        if calcular_hash_df(df_actual) != st.session_state.hashes_tablas.get(key):
            pendientes += 1
    return pendientes


def sincronizar_cambios() -> tuple[bool, int]:
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
        f"<div style='text-align:center; padding: 10px 0 6px 0;'>"
        f"<span style='color:{CHARCOAL_COLOR}; font-size:22px; font-weight:700; letter-spacing:0.04em;'>{APP_TITLE}</span> "
        f"<span style='font-size:10px; color:{CLAY_COLOR}; background-color:rgba(200, 90, 50, 0.12); "
        f"border:1px solid {CLAY_COLOR}; border-radius:4px; padding:2px 6px; vertical-align:middle; "
        f"font-family:monospace; font-weight:600;'>v2.0</span>"
        f"<p style='color:#6E665E; font-size:10px; letter-spacing:0.12em; text-transform:uppercase; margin-top:4px;'>Architecture & Interior</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

    if st.session_state.vista_actual in ["proyecto", "dashboard"] and st.session_state.proy_activo:
        if st.button("⬅ VOLVER AL PORTAFOLIO", use_container_width=True):
            st.session_state.vista_actual = "main"
            st.session_state.proy_activo = None
            clear_base_dfs()
            st.rerun()
        st.divider()

    equipo_default = get_secret("EQUIPO", "Socio 1, Socio 2")
    socios_input = st.text_input("Directores / Equipo de Diseño", value=equipo_default)
    lista_socios = [s.strip() for s in socios_input.split(",") if s.strip()]
    if not lista_socios:
        lista_socios = ["Socio 1", "Socio 2"]

    st.divider()

    # Estado de conexión y cambios pendientes
    modo_bd = "Google Sheets (Nube)" if nube_ok else "Base Local / Drive (Excel)"
    cambios_pend = contar_tablas_pendientes()
    badge_pend = (
        f"<span style='color:{CLAY_COLOR}; font-weight:600;'>● {cambios_pend} cambio(s) sin guardar</span>"
        if cambios_pend > 0
        else "<span style='color:#4A7C59; font-weight:600;'>● Sincronizado al día</span>"
    )
    st.markdown(
        f"<div style='background:#FAF8F5; border:1px solid #DFD9CE; border-radius:8px; padding:8px 12px; margin-bottom:10px; font-size:11.5px;'>"
        f"<div style='color:#6E665E;'><b>Origen:</b> {modo_bd}</div>"
        f"<div style='margin-top:3px;'>{badge_pend}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    if st.session_state.get("hubo_error_conexion", False):
        st.warning("Conexión en Pausa")
        st.info("Verifica las pestañas de Google Sheets antes de sincronizar.")
        if st.button("REINTENTAR CONEXIÓN", type="primary", use_container_width=True):
            with st.spinner("Reconectando con Google Sheets..."):
                forzar_importacion()
                st.rerun()
    else:
        if st.button("💾 GUARDAR CAMBIOS", type="primary", use_container_width=True):
            with st.spinner("Sincronizando cambios..."):
                exito, cantidad = sincronizar_cambios()
                if exito and cantidad > 0:
                    st.success(f"Guardado exitoso ({cantidad} tabla(s) actualizada(s)).")
                elif exito and cantidad == 0:
                    st.info("Todo está al día. Sin cambios pendientes.")
                else:
                    st.error("Error al sincronizar una o más tablas.")

        if st.button("🔄 ACTUALIZAR DATOS", use_container_width=True):
            with st.spinner("Cargando datos recientes..."):
                forzar_importacion()
                st.rerun()


# ==========================================
# 5. ENCABEZADO Y ENRUTAMIENTO
# ==========================================
render_header(title=APP_TITLE, subtitle=APP_SUBTITLE, logo_path=LOGO_PATH)

if st.session_state.vista_actual in ["proyecto", "dashboard"] and st.session_state.proy_activo:
    render_proyecto_view(st.session_state.proy_activo)
else:
    render_main_view(conn, sheet_url, nube_ok, lista_socios)
