"""
Vista Principal del Portafolio y Operaciones del Estudio:
Portafolio de Proyectos, Directorio de Contratistas, Finanzas Globales,
Control Operativo Diario, Calendario Técnico y Archivo Histórico.
Estética: Warm Architectural Atelier (#F7F4EF, #C85A32, #262320, #4A7C59, #D98A2B).
"""

import calendar
import datetime
import re
import altair as alt
import pandas as pd
import streamlit as st

from cota.config import (
    ESPECIALIDADES_DEFAULT,
    STATUS_PROYECTOS,
    STATUS_TASKS,
    TIPOS_PROYECTO,
    UNIDADES_MEDIDA,
)
from cota.db import (
    COLS_MAESTRO,
    COLS_PROY,
    agregar_fase_banco,
    agregar_item_catalogo_estudio,
    agregar_nota_chat_proyecto,
    clear_base_dfs,
    eliminar_item_catalogo_estudio,
    eliminar_nota_chat_proyecto,
    get_proyectos_activos,
    get_proyectos_archivados,
    guardar_tabla,
    obtener_banco_fases,
    obtener_catalogo_estudio,
    obtener_notas_chat_proyecto,
    purgar_proyecto_cascada,
    renombrar_proyecto,
    sembrar_fases_default,
    sincronizar_fases_proyecto,
)
import importlib
import cota.cotizacion
try:
    if not hasattr(cota.cotizacion, "obtener_utilidades_recibidas_estudio"):
        importlib.reload(cota.cotizacion)
except Exception:
    pass
from cota.cotizacion import obtener_utilidades_recibidas_estudio
import cota.ui.components
try:
    if not hasattr(cota.ui.components, "render_chat_notas_proyecto"):
        importlib.reload(cota.ui.components)
except Exception:
    pass
from cota.ui.components import render_chat_notas_proyecto, render_metric_card, render_metric_row
from cota.utils import (
    analizar_tareas_proyecto,
    calcular_rating,
    format_currency,
    format_date,
    get_now,
    parse_date,
    safe_float,
    safe_str,
    to_bool,
)


def render_main_view(conn, sheet_url, nube_ok, lista_socios):
    """Renderiza la vista principal cuando no hay un proyecto abierto individualmente."""
    now_dt = get_now()
    fecha_hoy = now_dt.date()
    df_hoy = pd.DataFrame({'Hoy': [pd.to_datetime(fecha_hoy)], 'Etiqueta': ['DIA ACTUAL']})

    # Asegurar columnas requeridas en proyectos
    for col in ['Nombre', 'Encargado', 'Ubicación', 'Estado', 'Inicio', 'Fin', 'Color', 'Cliente', 'Presupuesto', 'Archivado', 'Division', 'Tipo_Proyecto']:
        if col not in st.session_state.proyectos.columns:
            st.session_state.proyectos[col] = "General" if col == 'Division' else ""

    st.session_state.proyectos['Division'] = st.session_state.proyectos['Division'].fillna("General").replace("", "General")

    exist_divs = sorted(list(set([d for d in st.session_state.proyectos['Division'].dropna().unique().tolist() if d])))
    if not exist_divs:
        exist_divs = ["General"]
    elif "General" not in exist_divs:
        exist_divs.insert(0, "General")

    exist_ubis = obtener_catalogo_estudio("ubicaciones")
    if not exist_ubis:
        exist_ubis = ["Lima", "Miraflores", "San Isidro", "Barranco", "Surco", "La Molina"]

    socios_cat = obtener_catalogo_estudio("socios")
    if socios_cat:
        lista_socios = socios_cat

    # Tabs principales
    t_proy, t_con, t_fin, t_ope, t_cal, t_arc = st.tabs([
        "PROYECTOS",
        "BASE DE DATOS",
        "FINANZAS",
        "CONTROL OPERATIVO",
        "CALENDARIO",
        "ARCHIVO"
    ])

    with t_proy:
        _render_tab_portafolio(exist_divs, exist_ubis, lista_socios, fecha_hoy)

    with t_con:
        _render_tab_contratistas(fecha_hoy, df_hoy)

    with t_fin:
        _render_tab_finanzas_estudio(fecha_hoy)

    with t_ope:
        _render_tab_operativo_diario(lista_socios, fecha_hoy, conn, sheet_url, nube_ok)

    with t_cal:
        _render_tab_calendario(fecha_hoy)

    with t_arc:
        _render_tab_archivo()


# ====================================================
# SUB-RENDERERS PARA CADA SECCIÓN PRINCIPAL
# ====================================================

def _proy_tiene_anio(row, anio_str: str) -> bool:
    """Verifica si el año especificado coincide con las fechas de Inicio o Fin del proyecto."""
    if not anio_str or str(anio_str).startswith("🌐"):
        return True
    try:
        target_year = int(anio_str)
    except (ValueError, TypeError):
        return True

    d_ini = parse_date(row.get('Inicio')) if hasattr(row, 'get') else None
    d_fin = parse_date(row.get('Fin')) if hasattr(row, 'get') else None

    if d_ini is not None and d_ini.year == target_year:
        return True
    if d_fin is not None and d_fin.year == target_year:
        return True
    if d_ini is not None and d_fin is not None and d_ini.year <= target_year <= d_fin.year:
        return True
    return False


def _generar_barra_avance(pct: int, length: int = 10) -> str:
    """Genera una barra gráfica de progreso unicode con porcentaje."""
    p_val = max(0, min(100, int(pct)))
    filled = int(round(length * p_val / 100))
    bar = "█" * filled + "░" * (length - filled)
    return f"{bar} {p_val}%"


def _render_tab_portafolio(exist_divs, exist_ubis, lista_socios, fecha_hoy):
    """Portafolio de proyectos activos con KPIs ejecutivos filtrables por proyecto, carpetas y estados."""
    p_vis_all = get_proyectos_activos(st.session_state.proyectos)
    nombres_act = p_vis_all['Nombre'].tolist()

    # 1. Filtros del Resumen Ejecutivo en 3 columnas: Proyecto, Año y Ubicación
    OPCION_TODOS_PROY = "🌐 Todos los Proyectos Activos (Resumen Estudio)"
    opciones_filtro_proy = [OPCION_TODOS_PROY] + nombres_act

    anios_set = set()
    for _, r_p in p_vis_all.iterrows():
        d_i = parse_date(r_p.get('Inicio'))
        if d_i:
            anios_set.add(str(d_i.year))
        d_f = parse_date(r_p.get('Fin'))
        if d_f:
            anios_set.add(str(d_f.year))
    if not anios_set:
        anios_set.add(str(fecha_hoy.year))
    anios_disponibles = sorted(list(anios_set), reverse=True)

    OPCION_TODOS_ANIOS = "🌐 Todos los Años"
    opciones_filtro_anio = [OPCION_TODOS_ANIOS] + anios_disponibles

    OPCION_TODAS_UBIS = "🌐 Todas las Ubicaciones"
    ubis_en_proy = sorted(list(set([safe_str(u) for u in p_vis_all['Ubicación'].dropna().unique().tolist() if safe_str(u)])))
    if not ubis_en_proy:
        ubis_en_proy = [u for u in exist_ubis if u]
    opciones_filtro_ubi = [OPCION_TODAS_UBIS] + ubis_en_proy

    col_f_proy, col_f_anio, col_f_ubi = st.columns([4.2, 2.9, 2.9])
    with col_f_proy:
        proy_kpi_sel = st.selectbox(
            "🎯 Filtrar Resumen Ejecutivo por Proyecto:",
            options=opciones_filtro_proy,
            index=0,
            key="filtro_kpi_proyecto"
        )
    with col_f_anio:
        anio_kpi_sel = st.selectbox(
            "📅 Filtrar por Año:",
            options=opciones_filtro_anio,
            index=0,
            key="filtro_kpi_anio"
        )
    with col_f_ubi:
        ubi_kpi_sel = st.selectbox(
            "📍 Filtrar por Ubicación:",
            options=opciones_filtro_ubi,
            index=0,
            key="filtro_kpi_ubicacion"
        )

    es_proy_unico = (proy_kpi_sel != OPCION_TODOS_PROY) and (proy_kpi_sel in nombres_act)

    # Subconjunto de proyectos aplicando los 3 filtros combinados
    p_kpi_df = p_vis_all.copy()
    if es_proy_unico:
        p_kpi_df = p_kpi_df[p_kpi_df['Nombre'] == proy_kpi_sel]
    if anio_kpi_sel != OPCION_TODOS_ANIOS:
        p_kpi_df = p_kpi_df[p_kpi_df.apply(lambda r: _proy_tiene_anio(r, anio_kpi_sel), axis=1)]
    if ubi_kpi_sel != OPCION_TODAS_UBIS:
        p_kpi_df = p_kpi_df[p_kpi_df['Ubicación'].astype(str) == ubi_kpi_sel]

    nombres_kpi = p_kpi_df['Nombre'].tolist()

    # 1.A Cartera y Gastos
    n_plan = len(p_kpi_df[p_kpi_df['Estado'].astype(str).str.contains('Planificación', case=False, na=False)])
    n_en_proc = len(p_kpi_df[p_kpi_df['Estado'].astype(str).str.contains('Proceso', case=False, na=False)])
    n_activos = n_plan + n_en_proc
    tot_cartera = sum(safe_float(v) for v in p_kpi_df.get('Presupuesto', []))

    gastado_pagos = 0.0
    if 'pagos' in st.session_state and not st.session_state.pagos.empty and 'Proyecto' in st.session_state.pagos.columns:
        df_pag_k = st.session_state.pagos[st.session_state.pagos['Proyecto'].isin(nombres_kpi)]
        gastado_pagos = pd.to_numeric(df_pag_k.get('Monto', 0), errors='coerce').sum()
    gastado_gg = 0.0
    if 'gg_log' in st.session_state and not st.session_state.gg_log.empty and 'Proyecto' in st.session_state.gg_log.columns:
        df_gg_k = st.session_state.gg_log[st.session_state.gg_log['Proyecto'].isin(nombres_kpi)]
        gastado_gg = pd.to_numeric(df_gg_k.get('Monto', 0), errors='coerce').sum()
    tot_ejecutado = gastado_pagos + gastado_gg

    # 1.B Avance Operativo de Tareas (completadas / totales)
    tot_tareas_kpi = 0
    comp_tareas_kpi = 0
    if 'tasks' in st.session_state and not st.session_state.tasks.empty and 'Proyecto' in st.session_state.tasks.columns:
        df_t_kpi = st.session_state.tasks[st.session_state.tasks['Proyecto'].isin(nombres_kpi)]
        tot_tareas_kpi = len(df_t_kpi)
        if tot_tareas_kpi > 0 and 'Estado' in df_t_kpi.columns:
            comp_tareas_kpi = int(df_t_kpi['Estado'].astype(str).str.contains('Completado', case=False, na=False).sum())
    prom_avance = (comp_tareas_kpi / tot_tareas_kpi * 100.0) if tot_tareas_kpi > 0 else 0.0

    # 1.C Partidas y Tareas del Presupuesto
    num_partidas_kpi = 0
    num_tareas_kpi = 0
    monto_partidas_kpi = 0.0
    if 'partidas' in st.session_state and not st.session_state.partidas.empty and 'Proyecto' in st.session_state.partidas.columns:
        num_partidas_kpi = len(st.session_state.partidas[st.session_state.partidas['Proyecto'].isin(nombres_kpi)])
    if 'tasks' in st.session_state and not st.session_state.tasks.empty and 'Proyecto' in st.session_state.tasks.columns:
        num_tareas_kpi = len(st.session_state.tasks[st.session_state.tasks['Proyecto'].isin(nombres_kpi)])
    if 'p_info' in st.session_state and not st.session_state.p_info.empty and 'Proyecto' in st.session_state.p_info.columns:
        df_pi_act = st.session_state.p_info[st.session_state.p_info['Proyecto'].isin(nombres_kpi)]
        monto_partidas_kpi = float(pd.to_numeric(df_pi_act.get('Monto_Pactado', 0), errors='coerce').fillna(0.0).sum())

    # 1.D Hitos por Cobrar
    cobros_pend = 0
    cobros_tot_items = 0
    monto_pactado_cobros = 0.0
    monto_cobrado_cobros = 0.0
    if 'cobros' in st.session_state and not st.session_state.cobros.empty and 'Proyecto' in st.session_state.cobros.columns:
        df_c_act = st.session_state.cobros[st.session_state.cobros['Proyecto'].isin(nombres_kpi)].copy()
        cobros_tot_items = len(df_c_act)
        if not df_c_act.empty:
            monto_pactado_cobros = float(pd.to_numeric(df_c_act.get('Monto_Pactado', 0), errors='coerce').fillna(0.0).sum())
            monto_cobrado_cobros = float(pd.to_numeric(df_c_act.get('Monto_Cobrado', 0), errors='coerce').fillna(0.0).sum())
            if 'Estado' in df_c_act.columns:
                cobros_pend = int((~df_c_act['Estado'].astype(str).str.contains('Cobrado', case=False, na=False)).sum())
    saldo_hitos_cobrar = max(0.0, monto_pactado_cobros - monto_cobrado_cobros)

    # Renderizado simétrico de los 5 Widgets Ejecutivos mediante CSS Grid (.cota-kpi-grid)
    if es_proy_unico and not p_kpi_df.empty:
        r_p = p_kpi_df.iloc[0]
        est_str = safe_str(r_p.get('Estado', 'En Proceso')).split(" ", 1)[-1]
        cli_k = safe_str(r_p.get('Cliente', 'Sin cliente'))
        card_1 = {
            "title": "Proyecto / Estado",
            "value": est_str,
            "subtitle": f"{cli_k} · {safe_str(r_p.get('Tipo_Proyecto', 'Diseño'))}",
        }
    else:
        card_1 = {
            "title": "Proyectos Activos",
            "value": str(n_activos),
            "subtitle": f"{n_en_proc} en proceso · {n_plan} en planificación",
        }

    sub_cartera = (
        f"Ejecutado: {format_currency(tot_ejecutado)}"
        if tot_ejecutado > 0
        else "Presupuesto total contratado"
    )
    sub_avance = (
        f"{comp_tareas_kpi} de {tot_tareas_kpi} tareas completadas"
        if tot_tareas_kpi > 0
        else "Sin tareas registradas"
    )
    val_ppto_part = format_currency(monto_partidas_kpi) if monto_partidas_kpi > 0 else f"{num_partidas_kpi} partidas"
    sub_ppto_part = f"{num_partidas_kpi} partida(s) · {num_tareas_kpi} tarea(s) en ppto."

    col_cob = "#C85A32" if (cobros_pend > 0 or saldo_hitos_cobrar > 0) else "#4A7C59"
    val_cob = format_currency(saldo_hitos_cobrar) if monto_pactado_cobros > 0 else str(cobros_pend)
    sub_cob = f"{cobros_pend}/{cobros_tot_items} hitos pend. · Cobrado: {format_currency(monto_cobrado_cobros)}"

    render_metric_row([
        card_1,
        {"title": "Resumen Cartera", "value": format_currency(tot_cartera), "subtitle": sub_cartera},
        {"title": "Avance de Tareas", "value": f"{prom_avance:.0f}%", "subtitle": sub_avance, "border_color": "#4A7C59", "text_color": "#4A7C59"},
        {"title": "Presupuesto Casco", "value": val_ppto_part, "subtitle": sub_ppto_part, "border_color": "#D98A2B", "text_color": "#D98A2B"},
        {"title": "Hitos por Cobrar", "value": val_cob, "subtitle": sub_cob, "border_color": col_cob, "text_color": col_cob},
    ])

    # Detalle rápido desplegable cuando se filtra un proyecto específico
    if es_proy_unico:
        col_det_exp, col_det_btn = st.columns([7.8, 2.2])
        with col_det_exp:
            with st.expander(f"📋 Ver detalle de Hitos de Cobro y Partidas de Presupuesto de '{proy_kpi_sel}'", expanded=False):
                cd1, cd2 = st.columns(2)
                with cd1:
                    st.markdown("##### 💰 Hitos de Cobro del Proyecto")
                    df_c_det = st.session_state.cobros[st.session_state.cobros['Proyecto'] == proy_kpi_sel] if 'cobros' in st.session_state else pd.DataFrame()
                    if not df_c_det.empty:
                        st.dataframe(
                            df_c_det[['Hito', 'Monto_Pactado', 'Monto_Cobrado', 'Fecha_Vencimiento', 'Estado']],
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.caption("Sin hitos de cobro registrados para este proyecto.")
                with cd2:
                    st.markdown("##### 📐 Partidas de Presupuesto del Proyecto")
                    df_pi_det = st.session_state.p_info[st.session_state.p_info['Proyecto'] == proy_kpi_sel] if 'p_info' in st.session_state else pd.DataFrame()
                    if not df_pi_det.empty:
                        st.dataframe(
                            df_pi_det[['Nombre_Partida', 'Monto_Pactado']].rename(columns={'Nombre_Partida': 'Partida', 'Monto_Pactado': 'Sub Total (S/)'}),
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.caption("Sin partidas de presupuesto registradas para este proyecto.")
        with col_det_btn:
            st.markdown("<div style='padding-top: 5px;'></div>", unsafe_allow_html=True)
            if st.button(f"📂 ABRIR {proy_kpi_sel.upper()} →", key="btn_open_kpi_proy", type="primary", use_container_width=True):
                st.session_state.proy_activo = proy_kpi_sel
                st.session_state.vista_actual = 'proyecto'
                clear_base_dfs()
                st.rerun()

    st.divider()

    # 2. Barra de herramientas: Nuevo Proyecto + Buscador
    col_new, col_search = st.columns([2.8, 7.2])
    tipos_cat = obtener_catalogo_estudio("tipos_proyecto") or TIPOS_PROYECTO

    with col_new:
        with st.popover("➕ NUEVO PROYECTO", use_container_width=True):
            with st.form("form_nuevo_proy", clear_on_submit=True):
                pn = st.text_input("Nombre / Código del Proyecto (Único)", placeholder="").strip()
                sel_div = st.selectbox("Carpeta / Cliente", exist_divs + ["+ Crear Nueva Carpeta"])
                p_div = st.text_input("Nombre de Nueva Carpeta") if sel_div == "+ Crear Nueva Carpeta" else sel_div
                sel_ubi = st.selectbox("Ubicación", exist_ubis + ["+ Agregar Ubicación"])
                p_ubi_new = st.text_input("Nueva Ubicación (si elegiste '+ Agregar Ubicación')", placeholder="").strip()
                p_ubi = p_ubi_new if (sel_ubi == "+ Agregar Ubicación" and p_ubi_new) else (exist_ubis[0] if sel_ubi == "+ Agregar Ubicación" else sel_ubi)
                pe = st.selectbox("Líder de Proyecto", lista_socios, index=(lista_socios.index(st.session_state.get("socio_activo")) if st.session_state.get("socio_activo") in lista_socios else 0))
                ps = st.selectbox("Estado Inicial", STATUS_PROYECTOS)
                p_tipo = st.selectbox("Tipo de Proyecto", tipos_cat)
                p_cliente = st.text_input("Nombre del Cliente", placeholder="")
                p_color = st.color_picker("Color Identificador", value="#C85A32")

                st.caption("💡 El presupuesto total, utilidades, gastos generales y honorarios se definen directamente en la pestaña **03. PRESUPUESTO** del proyecto.")

                if st.form_submit_button("CREAR PROYECTO", type="primary", use_container_width=True):
                    if not pn:
                        st.error("El nombre del proyecto es obligatorio.")
                    elif pn in st.session_state.proyectos['Nombre'].tolist():
                        st.error(f"Ya existe un proyecto con el nombre '{pn}'. Elige un nombre único.")
                    else:
                        if p_ubi_new:
                            agregar_item_catalogo_estudio("ubicaciones", p_ubi_new)
                            p_ubi = p_ubi_new
                        n_p_dict = {
                            'Nombre': pn,
                            'Encargado': pe,
                            'Ubicación': p_ubi,
                            'Estado': ps,
                            'Inicio': fecha_hoy.strftime('%Y-%m-%d'),
                            'Fin': (fecha_hoy + datetime.timedelta(days=90)).strftime('%Y-%m-%d'),
                            'Color': p_color,
                            'Cliente': p_cliente,
                            'Presupuesto': 0.0,
                            'Utilidades': 0.0,
                            'GG_Presupuesto': 0.0,
                            'Archivado': False,
                            'Metodologia': 'Diseño Interior',
                            'Division': p_div,
                            'Tipo_Proyecto': p_tipo,
                            'Num_Pisos': 0,
                            'Num_Sotanos': 0,
                            'Presupuesto_FFE': 0.0,
                            'Honorarios_Diseno': 0.0,
                            'Notas': '',
                            'TC_Presupuesto': 3.42,
                            'GG_Pct': 2.0,
                            'Utilidades_Pct': 15.0,
                            'Incluir_IGV': False,
                        }
                        for col in COLS_PROY:
                            if col not in n_p_dict:
                                n_p_dict[col] = False if col in ['Archivado', 'Incluir_IGV'] else (0.0 if 'Ppto' in col or 'Pct' in col or col in ['Presupuesto', 'Utilidades', 'GG_Presupuesto', 'Presupuesto_FFE', 'Honorarios_Diseno'] else "")
                        n_p = pd.DataFrame([n_p_dict])
                        st.session_state.proyectos = pd.concat([st.session_state.proyectos, n_p[COLS_PROY]], ignore_index=True)

                        # Sembrar fases seleccionadas del Banco de Fases (sin FF&E)
                        fases_a_sembrar = [
                            f["Fase"]
                            for f in obtener_banco_fases()
                            if f.get("Por_Defecto", True) and "ff&e" not in f["Fase"].lower() and "ffe" not in f["Fase"].lower()
                        ]
                        nuevas_fases = sembrar_fases_default(pn, fases_seleccionadas=fases_a_sembrar)
                        if 'fases' not in st.session_state or st.session_state.fases.empty:
                            st.session_state.fases = nuevas_fases
                        else:
                            st.session_state.fases = pd.concat([st.session_state.fases, nuevas_fases], ignore_index=True)

                        clear_base_dfs()
                        st.success(f"Proyecto '{pn}' creado exitosamente.")
                        st.rerun()

    with col_search:
        search_q = st.text_input(
            "Buscar proyecto o cliente:",
            placeholder="🔍 Filtrar por nombre de proyecto, cliente, tipo o ubicación...",
            label_visibility="collapsed"
        )

    p_vis = p_kpi_df.copy()

    if search_q:
        sq = search_q.lower()
        p_vis = p_vis[
            p_vis['Nombre'].astype(str).str.lower().str.contains(sq, na=False) |
            p_vis['Cliente'].astype(str).str.lower().str.contains(sq, na=False) |
            p_vis['Ubicación'].astype(str).str.lower().str.contains(sq, na=False) |
            p_vis['Tipo_Proyecto'].astype(str).str.lower().str.contains(sq, na=False)
        ]

    divisiones = sorted(list(set([d for d in p_vis['Division'].dropna().unique().tolist() if d])))

    # Pestañas de carpetas: la primera muestra TODOS los proyectos activos juntos
    tab_labels = [f"🗂️ TODOS LOS PROYECTOS ({len(p_vis)})"] + [
        f"📁 {d.upper()} ({len(p_vis[p_vis['Division'] == d])})" for d in divisiones
    ]
    tab_keys = ["__ALL__"] + divisiones
    tabs_div = st.tabs(tab_labels)

    for t_div, d_key in zip(tabs_div, tab_keys):
        with t_div:
            p_div = p_vis if d_key == "__ALL__" else p_vis[p_vis['Division'] == d_key]
            if p_div.empty:
                st.info("No hay proyectos activos que coincidan con este filtro.")
                continue

            indices_mostrados = set()

            for est in STATUS_PROYECTOS:
                est_clean = est.split(" ", 1)[-1] if " " in est else est
                p_est = p_div[p_div['Estado'].astype(str).str.contains(est_clean, case=False, na=False)]

                if p_est.empty:
                    continue

                indices_mostrados.update(p_est.index.tolist())
                col_st = "#D98A2B" if "Planificación" in est else ("#4A7C59" if "Completado" in est else "#C85A32")

                state_key = f"est_open_{est_clean}"
                if state_key not in st.session_state:
                    st.session_state[state_key] = True
                is_open = st.session_state[state_key]

                flecha = "▲" if is_open else "▼"
                label_header = f"{flecha}   ESTADO: {est.upper()} ({len(p_est)})"

                d_slug = re.sub(r'[^a-zA-Z0-9_]', '_', str(d_key))
                est_slug = est_clean.replace(" ", "_").replace("ó", "o").replace("í", "i").replace("á", "a")
                btn_key = f"btn_est_{d_slug}_{est_slug}"

                c_est_col, _ = st.columns([1.25, 4.75])
                with c_est_col:
                    if st.button(label_header, key=btn_key, use_container_width=True, help="Click para ocultar o desplegar esta sección"):
                        st.session_state[state_key] = not is_open
                        st.rerun()

                if not is_open:
                    continue

                for idx_p, proy in p_est.iterrows():
                    p_nom = proy['Nombre']
                    ukey = f"{d_key}_{idx_p}"

                    # Calcular avance de etapas de diseño activas
                    pct_avance = 0
                    fase_actual_str = "Sin etapas de diseño"
                    fases_activas_proy = []
                    if 'fases' in st.session_state and not st.session_state.fases.empty:
                        f_p = st.session_state.fases[st.session_state.fases['Proyecto'] == p_nom].sort_values(by='Orden')
                        if not f_p.empty:
                            fases_activas_proy = f_p['Fase'].tolist()
                            ok_cnt = len(f_p[f_p['Aprobado_Cliente'].apply(to_bool) | (f_p['Estado'].astype(str).str.contains('Aprob', case=False))])
                            pct_avance = int(ok_cnt / len(f_p) * 100)
                            en_curso = f_p[~(f_p['Aprobado_Cliente'].apply(to_bool) | (f_p['Estado'].astype(str).str.contains('Aprob', case=False)))]
                            fase_actual_str = en_curso.iloc[0]['Fase'] if not en_curso.empty else f_p.iloc[-1]['Fase']

                    # Analizar tareas en proceso y widget inteligente de alertas (Foto 2)
                    info_t = analizar_tareas_proyecto(st.session_state.get('tasks'), p_nom, fecha_hoy)

                    # % de avance basado exclusivamente en tareas (completadas / totales)
                    pct_avance_tareas = int((info_t['completadas'] / info_t['total']) * 100) if info_t['total'] > 0 else 0

                    cli_val = safe_str(proy.get('Cliente', ''))
                    cli_str = f" · Cliente: {cli_val}" if cli_val else ""
                    div_val = safe_str(proy.get('Division', 'General'))
                    tipo_val = safe_str(proy.get('Tipo_Proyecto', 'Diseño'))
                    barra_avance = _generar_barra_avance(pct_avance_tareas, 10)
                    tit_expander = f"🏛️ **{p_nom.upper()}**{cli_str}  ·  📁 {div_val} · {tipo_val}  ·  Líder: {proy.get('Encargado', 'N/A')}  `{barra_avance}`"

                    with st.expander(tit_expander, expanded=es_proy_unico):
                        ppto_p = safe_float(proy.get('Presupuesto', 0))
                        hon_p = safe_float(proy.get('Honorarios_Diseno', 0))
                        ubi_p = safe_str(proy.get('Ubicación', 'Lima'))
                        ini_p = format_date(proy.get('Inicio'))
                        fin_p = format_date(proy.get('Fin'))

                        pills_html = "".join(
                            f"<span style='background:#FFFFFF; border:1px solid #DFD9CE; border-radius:4px; padding:2px 8px; font-size:11px; color:#262320; font-weight:500;'>{pill}</span>"
                            for pill in info_t.get("pills_extra", [])
                        )
                        pills_wrap = f"<div style='display:flex; flex-wrap:wrap; gap:6px; margin-top:4px;'>{pills_html}</div>" if pills_html else ""

                        # Ficha resumen ejecutiva del proyecto con conteo de tareas en proceso y widget inteligente
                        summary_html = (
                            f"<div style='border-left: 4px solid {col_st}; background: #FAF8F5; border: 1px solid #DFD9CE; border-left-width: 4px; border-left-color: {col_st}; border-radius: 8px; padding: 14px 16px; margin-bottom: 14px;'>"
                            f"<div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(145px, 1fr)); gap: 12px; font-size: 12.5px;'>"
                            f"<div><span style='color:#6E665E; font-size:11px; text-transform:uppercase;'>Ubicación</span><br><b style='color:#262320;'>{ubi_p}</b></div>"
                            f"<div><span style='color:#6E665E; font-size:11px; text-transform:uppercase;'>Cronograma</span><br><b style='color:#262320;'>{ini_p} → {fin_p}</b></div>"
                            f"<div><span style='color:#6E665E; font-size:11px; text-transform:uppercase;'>Estado de Proyecto</span><br><b style='color:{col_st};'>{safe_str(proy.get('Estado', '')) or est}</b></div>"
                            f"<div><span style='color:#6E665E; font-size:11px; text-transform:uppercase;'>Tareas en Proceso</span><br><b style='color:#262320; font-family:monospace;'>{info_t['en_proceso']} en proceso</b> <span style='color:#6E665E; font-size:11px;'>({info_t['completadas']}/{info_t['total']} listas)</span></div>"
                            f"<div><span style='color:#6E665E; font-size:11px; text-transform:uppercase;'>Ppto. Contrato</span><br><b style='color:#262320; font-family:monospace;'>{format_currency(ppto_p)}</b></div>"
                            f"<div><span style='color:#6E665E; font-size:11px; text-transform:uppercase;'>Honorarios Diseño</span><br><b style='color:#4A7C59; font-family:monospace;'>{format_currency(hon_p)}</b></div>"
                            f"</div>"
                            f"<div style='margin-top: 10px; background: #EFECE6; border-radius: 4px; height: 6px; overflow: hidden;'>"
                            f"<div style='background: {col_st}; width: {pct_avance_tareas}%; height: 100%;'></div>"
                            f"</div>"
                            f"<div style='margin-top: 10px; background: {info_t['widget_bg']}; border: 1px solid #DFD9CE; border-left: 3px solid {info_t['widget_color']}; border-radius: 6px; padding: 8px 12px; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 8px;'>"
                            f"<div>"
                            f"<span style='font-family:monospace; font-size:10.5px; font-weight:700; color:{info_t['widget_color']}; background:#FFFFFF; border:1px solid {info_t['widget_color']}; border-radius:4px; padding:1px 6px; margin-right:8px;'>{info_t['widget_badge']}</span>"
                            f"<b style='color:#262320; font-size:12.5px;'>{info_t['widget_titulo']}</b> "
                            f"<span style='color:#6E665E; font-size:12px;'>— {info_t['widget_detalle']}</span>"
                            f"</div>"
                            f"{pills_wrap}"
                            f"</div>"
                            f"</div>"
                        )
                        st.markdown(summary_html, unsafe_allow_html=True)

                        c_btn1, c_btn2, c_btn_fases, c_btn3, c_btn4 = st.columns([2.5, 2, 2.2, 2, 2])

                        with c_btn1:
                            if st.button("ABRIR PROYECTO →", key=f"open_proy_{ukey}", type="primary", use_container_width=True):
                                st.session_state.proy_activo = p_nom
                                st.session_state.vista_actual = 'proyecto'
                                clear_base_dfs()
                                st.rerun()

                        with c_btn2:
                            with st.popover("⚙️ EDITAR FICHA", use_container_width=True):
                                with st.form(f"edit_params_{ukey}"):
                                    n_nom = st.text_input("Nombre", value=p_nom)
                                    n_cli = st.text_input("Cliente", value=safe_str(proy.get('Cliente', '')))
                                    n_div = st.selectbox("Carpeta", exist_divs, index=exist_divs.index(proy.get('Division', 'General')) if proy.get('Division', 'General') in exist_divs else 0)
                                    opciones_ubi_ed = exist_ubis + ["+ Agregar Ubicación"]
                                    idx_ubi_ed = exist_ubis.index(proy.get('Ubicación', 'Lima')) if proy.get('Ubicación', 'Lima') in exist_ubis else 0
                                    n_ubi_sel = st.selectbox("Ubicación", opciones_ubi_ed, index=idx_ubi_ed)
                                    n_ubi_new = st.text_input("Nueva Ubicación (opcional)", placeholder="").strip()
                                    n_est = st.selectbox("Estado", STATUS_PROYECTOS, index=STATUS_PROYECTOS.index(proy.get('Estado')) if proy.get('Estado') in STATUS_PROYECTOS else 0)
                                    n_tipo = st.selectbox("Tipo", tipos_cat, index=tipos_cat.index(proy.get('Tipo_Proyecto')) if proy.get('Tipo_Proyecto') in tipos_cat else 0)
                                    col_d1, col_d2 = st.columns(2)
                                    d_i = col_d1.date_input("Inicio", value=parse_date(proy.get('Inicio')) or fecha_hoy)
                                    d_f = col_d2.date_input("Fin", value=parse_date(proy.get('Fin')) or fecha_hoy)
                                    n_drive = st.text_input("Presentación Drive / Slides (URL)", value=safe_str(proy.get('Link_Drive', '')))
                                    st.caption("💡 El presupuesto total, utilidades, gastos generales y honorarios se administran en **03. PRESUPUESTO**.")

                                    if st.form_submit_button("ACTUALIZAR DATOS"):
                                        if n_nom != p_nom:
                                             renombrar_proyecto(p_nom, n_nom)
                                        if n_ubi_new:
                                            agregar_item_catalogo_estudio("ubicaciones", n_ubi_new)
                                            n_ubi_final = n_ubi_new
                                        else:
                                            n_ubi_final = proy.get('Ubicación', 'Lima') if n_ubi_sel == "+ Agregar Ubicación" else n_ubi_sel

                                        st.session_state.proyectos.at[idx_p, 'Nombre'] = n_nom
                                        st.session_state.proyectos.at[idx_p, 'Cliente'] = n_cli
                                        st.session_state.proyectos.at[idx_p, 'Division'] = n_div
                                        st.session_state.proyectos.at[idx_p, 'Ubicación'] = n_ubi_final
                                        st.session_state.proyectos.at[idx_p, 'Estado'] = n_est
                                        st.session_state.proyectos.at[idx_p, 'Tipo_Proyecto'] = n_tipo
                                        st.session_state.proyectos.at[idx_p, 'Inicio'] = d_i.strftime('%Y-%m-%d')
                                        st.session_state.proyectos.at[idx_p, 'Fin'] = d_f.strftime('%Y-%m-%d')
                                        st.session_state.proyectos.at[idx_p, 'Link_Drive'] = n_drive.strip()
                                        clear_base_dfs()
                                        st.success("Datos actualizados correctamente.")
                                        st.rerun()


                        with c_btn_fases:
                            with st.popover("📌 ESTADO DE PROYECTO", use_container_width=True):
                                est_actual_card = safe_str(proy.get("Estado", "")) or est
                                st.markdown("##### 📌 Estado del Proyecto")
                                st.caption(f"Actual: **{est_actual_card}**")
                                for idx_opt_e, est_opt in enumerate(STATUS_PROYECTOS):
                                    es_act_est = (est_opt == est_actual_card)
                                    lbl_opt = f"{'✅ ' if es_act_est else ''}{est_opt}"
                                    if st.button(
                                        lbl_opt,
                                        key=f"btn_quick_est_{ukey}_{idx_opt_e}",
                                        type="primary" if es_act_est else "secondary",
                                        use_container_width=True,
                                        disabled=es_act_est,
                                    ):
                                        st.session_state.proyectos.at[idx_p, "Estado"] = est_opt
                                        clear_base_dfs()
                                        st.rerun()




                        with c_btn3:
                            notas_chat_card = obtener_notas_chat_proyecto(p_nom)
                            with st.popover(f"💬 NOTAS ({len(notas_chat_card)})", use_container_width=True):
                                st.markdown(f"##### 💬 Notas del Proyecto: {p_nom}")
                                render_chat_notas_proyecto(p_nom, lista_socios, key_prefix=f"card_{ukey}")

                        with c_btn4:
                            if st.button("📦 ARCHIVAR", key=f"arch_{ukey}", use_container_width=True):
                                st.session_state.proyectos.at[idx_p, 'Archivado'] = True
                                clear_base_dfs()
                                st.rerun()


def _render_tab_contratistas(fecha_hoy, df_hoy):
    """Base de Datos Maestra del Estudio: Contratistas, Ubicaciones, Especialidades, Socios, Unidades y Tipologías."""
    st.markdown("### 🗄️ BASE DE DATOS DEL ESTUDIO")
    st.caption("Administra contratistas, ubicaciones, especialidades, socios, unidades de medida y tipologías para armar presupuestos y proyectos.")

    sub_con, sub_ubi, sub_esp, sub_soc = st.tabs([
        "👷 Contratistas y Proveedores",
        "📍 Ubicaciones",
        "🛠️ Especialidades y Unidades",
        "👥 Socios y Tipologías",
    ])

    especialidades_cat = obtener_catalogo_estudio("especialidades")
    ubicaciones_cat = obtener_catalogo_estudio("ubicaciones")
    unidades_cat = obtener_catalogo_estudio("unidades")
    socios_cat = obtener_catalogo_estudio("socios")
    tipos_cat = obtener_catalogo_estudio("tipos_proyecto")

    with sub_con:
        c_tit, c_add = st.columns([7, 3])
        with c_tit:
            st.markdown("#### 🛠️ DIRECTORIO DE CONTRATISTAS, PROVEEDORES Y ESPECIALISTAS")
            st.caption("Evaluación histórica de desempeño, carga de trabajo actual y bitácora de obra.")
        with c_add:
            with st.popover("➕ REGISTRAR CONTRATISTA", use_container_width=True):
                with st.form("form_nuevo_contratista", clear_on_submit=True):
                    nc_nom = st.text_input("Nombre / Empresa Especialista", placeholder="").strip()
                    nc_esp = st.selectbox("Especialidad Principal", especialidades_cat)
                    nc_ubi = st.selectbox("Distrito / Ubicación Base", ubicaciones_cat if ubicaciones_cat else ["Lima"])
                    nc_not = st.text_area("Datos de Contacto / Observaciones Iniciales", placeholder="Teléfono, correo, RUC o referencias")
                    if st.form_submit_button("GUARDAR EN DIRECTORIO", type="primary", use_container_width=True):
                        if not nc_nom:
                            st.error("El nombre del contratista es obligatorio.")
                        elif not st.session_state.maestro.empty and nc_nom in st.session_state.maestro['ID_Contratista'].tolist():
                            st.error("Este contratista ya está registrado.")
                        else:
                            n_row = pd.DataFrame([{
                                'ID_Contratista': nc_nom,
                                'Especialidad': nc_esp,
                                'Ubicación_Base': nc_ubi,
                                'Notas': f"[+] {nc_not}" if nc_not else ""
                            }])
                            st.session_state.maestro = pd.concat([st.session_state.maestro, n_row[COLS_MAESTRO]], ignore_index=True)
                            clear_base_dfs()
                            st.success(f"Contratista '{nc_nom}' registrado.")
                            st.rerun()

        df_tasks_act = st.session_state.tasks.copy()
        df_tasks_act['Inicio_DT'] = df_tasks_act['Inicio'].apply(lambda x: pd.to_datetime(parse_date(x)))
        df_tasks_act['Fin_DT'] = df_tasks_act['Fin'].apply(lambda x: pd.to_datetime(parse_date(x)))
        df_tasks_act = df_tasks_act.dropna(subset=['Inicio_DT', 'Fin_DT'])

        estado_din = {}
        carga_din = {}

        for _, m_row in st.session_state.maestro.iterrows():
            n_c = m_row['ID_Contratista']
            t_c = df_tasks_act[df_tasks_act['Contratista'] == n_c]
            en_obra = t_c[(t_c['Inicio_DT'].dt.date <= fecha_hoy) & (t_c['Fin_DT'].dt.date >= fecha_hoy)]
            if not en_obra.empty:
                fecha_hasta = en_obra['Fin_DT'].max().date()
                estado_din[n_c] = f"🔵 En Obra Hoy (hasta {fecha_hasta.strftime('%d/%m/%Y')})"
            else:
                estado_din[n_c] = "🟢 Disponible"

            t_7d = t_c[(t_c['Inicio_DT'].dt.date <= fecha_hoy + datetime.timedelta(days=7)) & (t_c['Fin_DT'].dt.date >= fecha_hoy)]
            frentes = t_7d['Proyecto'].nunique()
            carga_din[n_c] = "Libre" if frentes == 0 else ("Carga Óptima (1 Obra)" if frentes == 1 else f"Alta Carga ({frentes} Obras)")

        df_m = st.session_state.maestro.copy()
        df_m['Estatus'] = df_m['ID_Contratista'].map(estado_din).fillna("🟢 Disponible")
        df_m['Carga_Trabajo'] = df_m['ID_Contratista'].map(carga_din).fillna("Libre")
        df_m['Rating'] = [calcular_rating(n, st.session_state.df_historial, st.session_state.tasks, st.session_state.maestro) for n in df_m['ID_Contratista']]

        st.dataframe(
            df_m[['ID_Contratista', 'Especialidad', 'Ubicación_Base', 'Estatus', 'Carga_Trabajo', 'Rating', 'Notas']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "ID_Contratista": st.column_config.TextColumn("Nombre / Empresa", width="medium"),
                "Especialidad": st.column_config.TextColumn("Especialidad"),
                "Ubicación_Base": st.column_config.TextColumn("Ubicación Base"),
                "Estatus": st.column_config.TextColumn("Estatus Hoy", width="medium"),
                "Carga_Trabajo": st.column_config.TextColumn("Disponibilidad (7 Días)"),
                "Rating": st.column_config.NumberColumn("Rating (1-5 ⭐)", format="%d ⭐"),
                "Notas": st.column_config.TextColumn("Observaciones / Historial")
            }
        )

        st.divider()

        # Bitácora de incidencias y reportes
        st.markdown("#### BITÁCORA TÉCNICA DE DESEMPEÑO")
        if not df_m.empty:
            c_sel = st.selectbox("Seleccionar Contratista / Proveedor:", df_m['ID_Contratista'].tolist(), key="sb_bitacora_m")
            idx_c = st.session_state.maestro[st.session_state.maestro['ID_Contratista'] == c_sel].index[0]
            notas_c = st.session_state.maestro.at[idx_c, 'Notas']

            with st.container(border=True):
                if notas_c and str(notas_c).strip():
                    html_n = (
                        str(notas_c)
                        .replace("[+]", "<span style='color:#4A7C59; font-weight:700;'>[+ MÉRITO]</span>")
                        .replace("[-]", "<span style='color:#C93B2B; font-weight:700;'>[- INCIDENCIA]</span>")
                    )
                    st.markdown(f"<div style='font-family:monospace; font-size:12.5px; color:#262320; line-height:1.6;'>{html_n}</div>", unsafe_allow_html=True)
                else:
                    st.info("Sin reportes registrados en la bitácora para este especialista.")

            n_rep = st.text_input(f"Añadir evaluación sobre {c_sel}:", placeholder="", key="txt_rep_c")
            col_r1, col_r2, _ = st.columns([2.5, 2.5, 5])

            if col_r1.button("👍 MÉRITO POSITIVO (+)", use_container_width=True) and n_rep:
                n_line = f"**[{fecha_hoy.strftime('%d/%m/%Y')}]** [+] {n_rep}"
                st.session_state.maestro.at[idx_c, 'Notas'] = f"{notas_c}\n<br>{n_line}" if notas_c and str(notas_c).strip() else n_line
                st.rerun()

            if col_r2.button("⚠️ INCIDENCIA NEGATIVA (-)", use_container_width=True) and n_rep:
                n_line = f"**[{fecha_hoy.strftime('%d/%m/%Y')}]** [-] {n_rep}"
                st.session_state.maestro.at[idx_c, 'Notas'] = f"{notas_c}\n<br>{n_line}" if notas_c and str(notas_c).strip() else n_line
                st.rerun()

    with sub_ubi:
        st.markdown("#### 📍 CATÁLOGO DE UBICACIONES Y DISTRITOS")
        st.caption("Agrega o elimina ubicaciones para asignarlas rápidamente al crear proyectos, contratistas o presupuestos.")
        c_u1, c_u2 = st.columns([1, 1.5])
        with c_u1:
            with st.form("form_add_ubicacion_bd", clear_on_submit=True):
                nueva_ubi = st.text_input("➕ Nueva Ubicación / Distrito:", placeholder="")
                if st.form_submit_button("AGREGAR UBICACIÓN", type="primary", use_container_width=True):
                    if nueva_ubi and nueva_ubi.strip():
                        agregar_item_catalogo_estudio("ubicaciones", nueva_ubi.strip())
                        st.success(f"Ubicación '{nueva_ubi.strip()}' agregada a la Base de Datos.")
                        st.rerun()
            if ubicaciones_cat:
                with st.form("form_del_ubicacion_bd"):
                    ubi_del = st.selectbox("🗑️ Eliminar Ubicación de la lista:", ubicaciones_cat)
                    if st.form_submit_button("ELIMINAR UBICACIÓN", use_container_width=True):
                        eliminar_item_catalogo_estudio("ubicaciones", ubi_del)
                        st.rerun()
        with c_u2:
            df_ubis = pd.DataFrame({"N°": range(1, len(ubicaciones_cat) + 1), "Ubicación / Distrito": ubicaciones_cat})
            st.dataframe(df_ubis, use_container_width=True, hide_index=True)

    with sub_esp:
        col_esp_bd, col_uni_bd = st.columns(2)
        with col_esp_bd:
            st.markdown("#### 🛠️ ESPECIALIDADES DE OBRA Y PRESUPUESTO")
            st.caption("Se utilizan en el Directorio de Contratistas, en `03. Presupuesto` y en `05. Partidas y Tareas`.")
            with st.form("form_add_esp_bd", clear_on_submit=True):
                nueva_esp = st.text_input("➕ Nueva Especialidad:", placeholder="")
                if st.form_submit_button("AGREGAR ESPECIALIDAD", type="primary", use_container_width=True):
                    if nueva_esp and nueva_esp.strip():
                        agregar_item_catalogo_estudio("especialidades", nueva_esp.strip())
                        st.success(f"Especialidad '{nueva_esp.strip()}' agregada.")
                        st.rerun()
            if especialidades_cat:
                with st.form("form_del_esp_bd"):
                    esp_del = st.selectbox("🗑️ Eliminar Especialidad:", especialidades_cat)
                    if st.form_submit_button("ELIMINAR ESPECIALIDAD", use_container_width=True):
                        eliminar_item_catalogo_estudio("especialidades", esp_del)
                        st.rerun()
            st.dataframe(pd.DataFrame({"Especialidad": especialidades_cat}), use_container_width=True, hide_index=True)

        with col_uni_bd:
            st.markdown("#### 📏 UNIDADES DE MEDIDA (PRESUPUESTO)")
            st.caption("Unidades disponibles al armar partidas y tareas en `03. Presupuesto`.")
            with st.form("form_add_uni_bd", clear_on_submit=True):
                nueva_uni = st.text_input("➕ Nueva Unidad de Medida:", placeholder="")
                if st.form_submit_button("AGREGAR UNIDAD", type="primary", use_container_width=True):
                    if nueva_uni and nueva_uni.strip():
                        agregar_item_catalogo_estudio("unidades", nueva_uni.strip())
                        st.success(f"Unidad '{nueva_uni.strip()}' agregada.")
                        st.rerun()
            if unidades_cat:
                with st.form("form_del_uni_bd"):
                    uni_del = st.selectbox("🗑️ Eliminar Unidad:", unidades_cat)
                    if st.form_submit_button("ELIMINAR UNIDAD", use_container_width=True):
                        eliminar_item_catalogo_estudio("unidades", uni_del)
                        st.rerun()
            st.dataframe(pd.DataFrame({"Unidad": unidades_cat}), use_container_width=True, hide_index=True)

    with sub_soc:
        col_soc_bd, col_tip_bd = st.columns(2)
        with col_soc_bd:
            st.markdown("#### 👥 SOCIOS Y LÍDERES DE PROYECTO")
            st.caption("Socios y encargados disponibles para liderar proyectos, dejar notas y registrar control operativo.")
            with st.form("form_add_soc_bd", clear_on_submit=True):
                nuevo_soc = st.text_input("➕ Nuevo Socio / Encargado:", placeholder="")
                if st.form_submit_button("AGREGAR SOCIO", type="primary", use_container_width=True):
                    if nuevo_soc and nuevo_soc.strip():
                        agregar_item_catalogo_estudio("socios", nuevo_soc.strip())
                        st.success(f"Socio '{nuevo_soc.strip()}' agregado.")
                        st.rerun()
            if socios_cat:
                with st.form("form_del_soc_bd"):
                    soc_del = st.selectbox("🗑️ Eliminar Socio:", socios_cat)
                    if st.form_submit_button("ELIMINAR SOCIO", use_container_width=True):
                        eliminar_item_catalogo_estudio("socios", soc_del)
                        st.rerun()
            st.dataframe(pd.DataFrame({"Socio / Encargado": socios_cat}), use_container_width=True, hide_index=True)

        with col_tip_bd:
            st.markdown("#### 🏛️ TIPOLOGÍAS DE PROYECTO")
            st.caption("Tipos de proyecto disponibles al crear o editar una ficha de proyecto.")
            with st.form("form_add_tip_bd", clear_on_submit=True):
                nuevo_tip = st.text_input("➕ Nuevo Tipo de Proyecto:", placeholder="")
                if st.form_submit_button("AGREGAR TIPO DE PROYECTO", type="primary", use_container_width=True):
                    if nuevo_tip and nuevo_tip.strip():
                        agregar_item_catalogo_estudio("tipos_proyecto", nuevo_tip.strip())
                        st.success(f"Tipo '{nuevo_tip.strip()}' agregado.")
                        st.rerun()
            if tipos_cat:
                with st.form("form_del_tip_bd"):
                    tip_del = st.selectbox("🗑️ Eliminar Tipo de Proyecto:", tipos_cat)
                    if st.form_submit_button("ELIMINAR TIPO", use_container_width=True):
                        eliminar_item_catalogo_estudio("tipos_proyecto", tip_del)
                        st.rerun()
            st.dataframe(pd.DataFrame({"Tipo de Proyecto": tipos_cat}), use_container_width=True, hide_index=True)


FINANZAS_KPIS_CONFIG = [
    {"id": "ventas", "label": "Ventas (Total Contratos)", "color": "#262320", "default": True},
    {"id": "utilidades", "label": "Utilidades Proyectadas", "color": "#4A7C59", "default": True},
    {"id": "gg_ppto", "label": "Gastos Generales (GG)", "color": "#D98A2B", "default": True},
    {"id": "util_recibidas", "label": "Utilidades Recibidas", "color": "#C85A32", "default": True},
    {"id": "gg_cobrados", "label": "GG Cobrados", "color": "#B58445", "default": False},
    {"id": "util_mas_gg", "label": "Util. Recibidas + GG Cobrados", "color": "#9A4322", "default": False},
    {"id": "caja_ejecutada", "label": "Caja Chica Ejecutada", "color": "#C93B2B", "default": False},
    {"id": "cobrado_clientes", "label": "Cobrado a Clientes", "color": "#2E6F8E", "default": False},
    {"id": "egresos_obra", "label": "Pagos Obra + FF&E", "color": "#6E665E", "default": False},
    {"id": "honorarios", "label": "Honorarios de Diseño", "color": "#7A638E", "default": False},
]
_FINANZAS_KPI_MAP = {k["label"]: k for k in FINANZAS_KPIS_CONFIG}


def es_estado_proyecto_aprobado_finanzas(estado) -> bool:
    """Retorna True solo para proyectos aprobados ('En Proceso' o 'Completado')."""
    est = safe_str(estado).strip().lower()
    if not est or "planif" in est:
        return False
    return ("proceso" in est) or ("completad" in est) or ("aprobad" in est)


def filtrar_proyectos_aprobados_finanzas(df_proyectos: pd.DataFrame) -> pd.DataFrame:
    """Filtra el DataFrame conservando únicamente proyectos aprobados (En Proceso y Completado)."""
    if df_proyectos is None or df_proyectos.empty:
        return pd.DataFrame(columns=COLS_PROY)
    if "Estado" not in df_proyectos.columns:
        return df_proyectos.copy()
    mask_ok = df_proyectos["Estado"].apply(es_estado_proyecto_aprobado_finanzas)
    return df_proyectos[mask_ok].copy()


def asignar_anio_proyecto(row, label_sin_fecha: str = "Sin fecha") -> str:
    """Determina el año financiero único de un proyecto priorizando Inicio y luego Fin."""
    if row is None or not hasattr(row, "get"):
        return label_sin_fecha
    d_ini = parse_date(row.get("Inicio"))
    if d_ini is not None:
        return str(d_ini.year)
    d_fin = parse_date(row.get("Fin"))
    if d_fin is not None:
        return str(d_fin.year)
    return label_sin_fecha


def _ordenar_anios_financieros(anios_iter) -> list[str]:
    """Ordena años cronológicamente dejando cualquier etiqueta sin año al final."""
    unicos = {str(a).strip() for a in anios_iter if str(a).strip()}
    numericos = sorted((a for a in unicos if a.isdigit()), key=int)
    otros = sorted(a for a in unicos if not a.isdigit())
    return numericos + otros


def _mapa_sumas_por_proyecto(df: pd.DataFrame, col_monto: str, col_proy: str = "Proyecto") -> dict[str, float]:
    """Agrupa montos numéricos por nombre de proyecto de forma segura."""
    if df is None or df.empty or col_proy not in df.columns or col_monto not in df.columns:
        return {}
    s_num = pd.to_numeric(df[col_monto], errors="coerce").fillna(0.0)
    grouped = s_num.groupby(df[col_proy].fillna("").astype(str)).sum()
    return {str(k): float(v) for k, v in grouped.items()}


def calcular_datos_finanzas_estudio(
    df_proyectos: pd.DataFrame,
    df_cob: pd.DataFrame,
    df_pag: pd.DataFrame,
    df_gg: pd.DataFrame,
    df_mat: pd.DataFrame,
    df_ing: pd.DataFrame,
    util_rec_info: dict,
    anios_filtro=None,
    fecha_ref=None,
) -> dict:
    """Consolida métricas financieras por proyecto y por año para la pestaña FINANZAS."""
    df_p = (
        df_proyectos.copy()
        if isinstance(df_proyectos, pd.DataFrame) and not df_proyectos.empty
        else pd.DataFrame(columns=COLS_PROY)
    )
    df_p = filtrar_proyectos_aprobados_finanzas(df_p)
    nombres_base = [safe_str(n) for n in df_p["Nombre"].tolist()] if "Nombre" in df_p.columns else []
    nombres_set = set(nombres_base)

    cob_map = _mapa_sumas_por_proyecto(df_cob, "Monto_Cobrado")
    pag_map = _mapa_sumas_por_proyecto(df_pag, "Monto")
    gg_map = _mapa_sumas_por_proyecto(df_gg, "Monto")
    mat_map = _mapa_sumas_por_proyecto(df_mat, "Costo_Real")

    ing_util_map: dict[str, float] = {}
    ing_gg_map: dict[str, float] = {}
    ing_otros_map: dict[str, float] = {}
    gen_util_anio: dict[str, float] = {}
    gen_gg_anio: dict[str, float] = {}

    if isinstance(df_ing, pd.DataFrame) and not df_ing.empty and "Monto" in df_ing.columns:
        valid_proys = nombres_set | {"General"}
        df_ing_sub = (
            df_ing[df_ing["Proyecto"].isin(valid_proys)].reset_index(drop=True)
            if "Proyecto" in df_ing.columns
            else df_ing.reset_index(drop=True)
        )
        if not df_ing_sub.empty:
            cat_s = df_ing_sub["Categoria"].astype(str) if "Categoria" in df_ing_sub.columns else pd.Series("", index=df_ing_sub.index)
            montos_s = pd.to_numeric(df_ing_sub["Monto"], errors="coerce").fillna(0.0)
            is_u_arr = cat_s.str.contains("Utilidad|Honorario", case=False, na=False)
            is_g_arr = cat_s.str.contains("Gasto|Caja|GG", case=False, na=False)
            for idx_i, r_ing in df_ing_sub.iterrows():
                m_val = float(montos_s.loc[idx_i])
                p_ing = safe_str(r_ing.get("Proyecto", "General")) or "General"
                is_u = bool(is_u_arr.loc[idx_i])
                is_g = bool(is_g_arr.loc[idx_i]) and not is_u
                if p_ing in nombres_set:
                    if is_u:
                        ing_util_map[p_ing] = round(ing_util_map.get(p_ing, 0.0) + m_val, 2)
                    elif is_g:
                        ing_gg_map[p_ing] = round(ing_gg_map.get(p_ing, 0.0) + m_val, 2)
                    else:
                        ing_otros_map[p_ing] = round(ing_otros_map.get(p_ing, 0.0) + m_val, 2)
                elif p_ing == "General":
                    d_ing = parse_date(r_ing.get("Fecha"))
                    yr_gen = str(d_ing.year) if d_ing is not None else (str(fecha_ref.year) if fecha_ref is not None else "Sin fecha")
                    if is_u:
                        gen_util_anio[yr_gen] = round(gen_util_anio.get(yr_gen, 0.0) + m_val, 2)
                    elif is_g:
                        gen_gg_anio[yr_gen] = round(gen_gg_anio.get(yr_gen, 0.0) + m_val, 2)

    raw_util_sum = sum(safe_float(u) for u in df_p.get("Utilidades", []))
    raw_ventas_sum = sum(safe_float(v) for v in df_p.get("Presupuesto", []))
    usar_fallback_20 = (raw_util_sum == 0.0 and raw_ventas_sum > 0.0)
    por_proy_rec = util_rec_info.get("por_proyecto", {}) if isinstance(util_rec_info, dict) else {}

    proy_records = []
    for _, pr in df_p.iterrows():
        p_name = safe_str(pr.get("Nombre", ""))
        anio_p = asignar_anio_proyecto(pr)
        ppto_p = round(safe_float(pr.get("Presupuesto", 0.0)), 2)
        hon_p = round(safe_float(pr.get("Honorarios_Diseno", 0.0)), 2)
        util_p = round(safe_float(pr.get("Utilidades", 0.0)), 2)
        modo_u = safe_str(pr.get("Modo_Utilidades", "")).strip().lower()
        if usar_fallback_20 and util_p == 0.0 and ppto_p > 0 and modo_u not in ("exacto", "monto", "fijo"):
            util_p = round(ppto_p * 0.20, 2)
        gg_ppto_p = round(safe_float(pr.get("GG_Presupuesto", 0.0)), 2)
        caja_p = round(gg_map.get(p_name, 0.0), 2)
        cob_p = round(cob_map.get(p_name, 0.0), 2)
        pag_p = round(pag_map.get(p_name, 0.0), 2)
        ffe_p = round(mat_map.get(p_name, 0.0), 2)
        egresos_p = round(pag_p + caja_p + ffe_p, 2)

        ges_pag_p = round(float(por_proy_rec.get(p_name, {}).get("gestion_pagado", 0.0)), 2)
        util_rec_p = round(ges_pag_p + ing_util_map.get(p_name, 0.0), 2)
        gg_cob_p = round(ing_gg_map.get(p_name, 0.0), 2)
        util_mas_gg_p = round(util_rec_p + gg_cob_p, 2)
        u_ej_tabla_p = round(util_mas_gg_p + ing_otros_map.get(p_name, 0.0), 2)

        proy_records.append({
            "Proyecto": p_name,
            "Estado": safe_str(pr.get("Estado", "")),
            "Cliente": safe_str(pr.get("Cliente", "")),
            "Año": anio_p,
            "ventas": ppto_p,
            "utilidades": util_p,
            "gg_ppto": gg_ppto_p,
            "util_recibidas": util_rec_p,
            "gg_cobrados": gg_cob_p,
            "util_mas_gg": util_mas_gg_p,
            "u_ej_tabla": u_ej_tabla_p,
            "caja_ejecutada": caja_p,
            "cobrado_clientes": cob_p,
            "egresos_obra": egresos_p,
            "honorarios": hon_p,
        })

    anios_disponibles = _ordenar_anios_financieros(
        [r["Año"] for r in proy_records] + list(gen_util_anio.keys()) + list(gen_gg_anio.keys())
    )
    if anios_filtro is None:
        anios_activos = list(anios_disponibles)
    else:
        filtro_set = {str(a) for a in anios_filtro}
        anios_activos = [a for a in anios_disponibles if a in filtro_set]

    anios_act_set = set(anios_activos)
    recs_filtrados = [r for r in proy_records if r["Año"] in anios_act_set]

    por_anio_acc: dict[str, dict] = {}
    for yr in anios_activos:
        por_anio_acc[yr] = {
            "Año": yr,
            "Proyectos": 0,
            **{k["id"]: 0.0 for k in FINANZAS_KPIS_CONFIG},
        }
        por_anio_acc[yr]["util_recibidas"] = round(gen_util_anio.get(yr, 0.0), 2)
        por_anio_acc[yr]["gg_cobrados"] = round(gen_gg_anio.get(yr, 0.0), 2)
        por_anio_acc[yr]["util_mas_gg"] = round(
            por_anio_acc[yr]["util_recibidas"] + por_anio_acc[yr]["gg_cobrados"], 2
        )

    for rec in recs_filtrados:
        acc = por_anio_acc[rec["Año"]]
        acc["Proyectos"] += 1
        for k_cfg in FINANZAS_KPIS_CONFIG:
            kid = k_cfg["id"]
            acc[kid] = round(acc[kid] + float(rec[kid]), 2)

    resumen_anual = []
    for yr in anios_activos:
        row_y = por_anio_acc[yr]
        v_y = row_y["ventas"]
        row_y["margen_pct"] = round((row_y["utilidades"] / v_y * 100.0) if v_y > 0 else 0.0, 1)
        resumen_anual.append(row_y)

    tot_ventas = round(sum(r["ventas"] for r in resumen_anual), 2)
    tot_hon = round(sum(r["honorarios"] for r in resumen_anual), 2)
    tot_utilidades = round(sum(r["utilidades"] for r in resumen_anual), 2)
    tot_caja_ppto = round(sum(r["gg_ppto"] for r in resumen_anual), 2)
    tot_caja_gastada = round(sum(r["caja_ejecutada"] for r in resumen_anual), 2)
    saldo_caja = round(tot_caja_ppto - tot_caja_gastada, 2)
    pct_caja = (tot_caja_gastada / tot_caja_ppto * 100.0) if tot_caja_ppto > 0 else 0.0
    pct_util_contratos = (tot_utilidades / tot_ventas * 100.0) if tot_ventas > 0 else 0.0
    util_ejecutadas = round(sum(r["util_recibidas"] for r in resumen_anual), 2)
    gg_cobrados = round(sum(r["gg_cobrados"] for r in resumen_anual), 2)
    tot_util_ejec_mas_gg = round(util_ejecutadas + gg_cobrados, 2)
    tot_cobrado = round(sum(r["cobrado_clientes"] for r in resumen_anual), 2)
    tot_egresos = round(sum(r["egresos_obra"] for r in resumen_anual), 2)

    rows_fin = [
        {
            "Proyecto": r["Proyecto"],
            "Estado": r.get("Estado", ""),
            "Año": r["Año"],
            "Cliente": r["Cliente"],
            "Total Contrato": format_currency(r["ventas"]),
            "Utilidades": format_currency(r["utilidades"]),
            "GG (Ppto.)": format_currency(r["gg_ppto"]),
            "Caja Chica (Ejec. / Ppto.)": f"{format_currency(r['caja_ejecutada'])} / {format_currency(r['gg_ppto'])}",
            "Util. Ejec. + GG Cobrados": format_currency(r["u_ej_tabla"]),
            "Cobrado Cliente": format_currency(r["cobrado_clientes"]),
            "Pagos Obra + FF&E": format_currency(r["egresos_obra"]),
        }
        for r in recs_filtrados
    ]

    return {
        "anios_disponibles": anios_disponibles,
        "anios_activos": anios_activos,
        "kpis_globales": {
            "num_proyectos": len(recs_filtrados),
            "tot_ventas": tot_ventas,
            "tot_hon": tot_hon,
            "tot_utilidades": tot_utilidades,
            "pct_util_contratos": pct_util_contratos,
            "tot_caja_ppto": tot_caja_ppto,
            "tot_caja_gastada": tot_caja_gastada,
            "saldo_caja": saldo_caja,
            "pct_caja": pct_caja,
            "util_ejecutadas": util_ejecutadas,
            "gg_cobrados": gg_cobrados,
            "tot_util_ejec_mas_gg": tot_util_ejec_mas_gg,
            "tot_cobrado": tot_cobrado,
            "tot_egresos": tot_egresos,
        },
        "resumen_anual": resumen_anual,
        "proy_records": recs_filtrados,
        "rows_fin": rows_fin,
    }


def _render_finanzas_chart_y_resumen(fin_data: dict, kpis_sel: list[str], vista_graf: str):
    """Renderiza el gráfico comparativo (Anual por defecto o Por Proyecto) y la tabla consolidada anual."""
    anios_act = fin_data["anios_activos"]
    resumen_anual = fin_data["resumen_anual"]
    proy_recs = fin_data["proy_records"]

    if not anios_act:
        st.info("Selecciona al menos un año en el filtro superior para visualizar las métricas.")
        return
    if not kpis_sel:
        st.info("Selecciona al menos un KPI en el filtro superior para visualizar el gráfico.")
        return

    kpis_validos = [k for k in kpis_sel if k in _FINANZAS_KPI_MAP]
    if not kpis_validos:
        st.info("Selecciona al menos un KPI válido para visualizar el gráfico.")
        return
    colores_sel = [_FINANZAS_KPI_MAP[k]["color"] for k in kpis_validos]

    if vista_graf == "🏗️ Por Proyecto":
        st.markdown("#### COMPARATIVA FINANCIERA POR PROYECTO")
        chart_rows = []
        for rec in proy_recs:
            for k_lbl in kpis_validos:
                kid = _FINANZAS_KPI_MAP[k_lbl]["id"]
                chart_rows.append({
                    "Proyecto": rec["Proyecto"],
                    "Año": rec["Año"],
                    "KPI": k_lbl,
                    "Monto": rec[kid],
                })
        if not chart_rows:
            st.info("No hay proyectos en los años seleccionados.")
            return
        df_ch_p = pd.DataFrame(chart_rows)
        chart_p = alt.Chart(df_ch_p).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X("Proyecto:N", title=None, axis=alt.Axis(labelAngle=-15, labelColor="#262320", labelFontWeight="bold")),
            y=alt.Y("Monto:Q", title="Monto (S/)", axis=alt.Axis(gridColor="#DFD9CE", labelColor="#6E665E")),
            xOffset=alt.XOffset("KPI:N", sort=kpis_validos),
            color=alt.Color(
                "KPI:N",
                scale=alt.Scale(domain=kpis_validos, range=colores_sel),
                legend=alt.Legend(title="Indicador Financiero", orient="top", labelColor="#262320", titleColor="#6E665E"),
            ),
            tooltip=["Proyecto", "Año", "KPI", alt.Tooltip("Monto:Q", title="Monto (S/)", format=",.2f")],
        ).properties(height=310).configure_view(strokeOpacity=0)
        st.altair_chart(chart_p, use_container_width=True)
        return

    st.markdown("#### COMPARATIVA FINANCIERA ANUAL")
    st.caption("Evolución anual según los años y KPIs seleccionados (cada proyecto se asigna al año de su fecha de Inicio o Fin).")

    chart_rows_a = []
    for r_y in resumen_anual:
        v_y = r_y["ventas"]
        for k_lbl in kpis_validos:
            kid = _FINANZAS_KPI_MAP[k_lbl]["id"]
            m_val = r_y[kid]
            pct_v = round((m_val / v_y * 100.0) if v_y > 0 else 0.0, 1)
            chart_rows_a.append({
                "Año": r_y["Año"],
                "Proyectos": r_y["Proyectos"],
                "KPI": k_lbl,
                "Monto": m_val,
                "Pct_Ventas": f"{pct_v:.1f}%",
            })

    df_ch_a = pd.DataFrame(chart_rows_a)
    chart_anual = alt.Chart(df_ch_a).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
        x=alt.X("Año:N", title=None, sort=anios_act, axis=alt.Axis(labelAngle=0, labelColor="#262320", labelFontWeight="bold", labelFontSize=13)),
        y=alt.Y("Monto:Q", title="Monto (S/)", axis=alt.Axis(gridColor="#DFD9CE", labelColor="#6E665E")),
        xOffset=alt.XOffset("KPI:N", sort=kpis_validos),
        color=alt.Color(
            "KPI:N",
            scale=alt.Scale(domain=kpis_validos, range=colores_sel),
            legend=alt.Legend(title="KPI Financiero", orient="top", labelColor="#262320", titleColor="#6E665E"),
        ),
        tooltip=[
            alt.Tooltip("Año:N", title="Año"),
            alt.Tooltip("Proyectos:Q", title="Proyectos"),
            alt.Tooltip("KPI:N", title="KPI"),
            alt.Tooltip("Monto:Q", title="Monto (S/)", format=",.2f"),
            alt.Tooltip("Pct_Ventas:N", title="% s/ Ventas"),
        ],
    ).properties(height=320).configure_view(strokeOpacity=0)
    st.altair_chart(chart_anual, use_container_width=True)

    rows_anual_disp = []
    for r_y in resumen_anual:
        fila_t = {"Año": r_y["Año"], "Proyectos": r_y["Proyectos"]}
        for k_lbl in kpis_validos:
            kid = _FINANZAS_KPI_MAP[k_lbl]["id"]
            fila_t[k_lbl] = format_currency(r_y[kid])
        fila_t["Margen Util. %"] = f"{r_y['margen_pct']:.1f}%"
        rows_anual_disp.append(fila_t)

    if len(resumen_anual) > 1:
        tot_v_sel = sum(r["ventas"] for r in resumen_anual)
        tot_u_sel = sum(r["utilidades"] for r in resumen_anual)
        margen_tot = (tot_u_sel / tot_v_sel * 100.0) if tot_v_sel > 0 else 0.0
        fila_tot = {"Año": "TOTAL SELECCIONADO", "Proyectos": sum(r["Proyectos"] for r in resumen_anual)}
        for k_lbl in kpis_validos:
            kid = _FINANZAS_KPI_MAP[k_lbl]["id"]
            fila_tot[k_lbl] = format_currency(sum(r[kid] for r in resumen_anual))
        fila_tot["Margen Util. %"] = f"{margen_tot:.1f}%"
        rows_anual_disp.append(fila_tot)

    st.markdown("##### 📋 RESUMEN ANUAL CONSOLIDADO")
    st.dataframe(pd.DataFrame(rows_anual_disp), use_container_width=True, hide_index=True)


def _render_tab_finanzas_estudio(fecha_hoy):
    """Consolidado de finanzas anuales y por proyecto: ventas, utilidades, caja chica y cobros."""
    if "fin_incluir_archivados" not in st.session_state:
        st.session_state["fin_incluir_archivados"] = False
    incluir_arch = bool(st.session_state.get("fin_incluir_archivados", False))

    df_proy_all = st.session_state.get("proyectos", pd.DataFrame())
    df_p_act = get_proyectos_activos(df_proy_all)
    if incluir_arch and isinstance(df_proy_all, pd.DataFrame) and not df_proy_all.empty:
        df_p_base = df_proy_all.copy()
        for col in COLS_PROY:
            if col not in df_p_base.columns:
                df_p_base[col] = ""
    else:
        df_p_base = df_p_act

    df_p_base = filtrar_proyectos_aprobados_finanzas(df_p_base)
    nombres_base = (
        [safe_str(n) for n in df_p_base["Nombre"].tolist()]
        if not df_p_base.empty and "Nombre" in df_p_base.columns
        else []
    )

    df_gg_raw = st.session_state.gg_log if "gg_log" in st.session_state else pd.DataFrame(columns=["Proyecto", "Monto"])
    df_gg = (
        df_gg_raw[df_gg_raw["Proyecto"].isin(nombres_base)]
        if not df_gg_raw.empty and "Proyecto" in df_gg_raw.columns
        else pd.DataFrame(columns=["Proyecto", "Monto"])
    )

    df_ing_raw = (
        st.session_state.ingresos_socios
        if "ingresos_socios" in st.session_state
        else pd.DataFrame(columns=["Proyecto", "Categoria", "Monto"])
    )
    df_ing = (
        df_ing_raw[df_ing_raw["Proyecto"].isin(nombres_base + ["General"])].copy()
        if not df_ing_raw.empty and "Proyecto" in df_ing_raw.columns
        else pd.DataFrame(columns=["Proyecto", "Categoria", "Monto"])
    )

    df_cob_raw = st.session_state.cobros if "cobros" in st.session_state else pd.DataFrame()
    df_cob = (
        df_cob_raw[df_cob_raw["Proyecto"].isin(nombres_base)]
        if not df_cob_raw.empty and "Proyecto" in df_cob_raw.columns
        else pd.DataFrame()
    )

    df_pag_raw = st.session_state.pagos if "pagos" in st.session_state else pd.DataFrame(columns=["Proyecto", "Monto"])
    df_pag = (
        df_pag_raw[df_pag_raw["Proyecto"].isin(nombres_base)]
        if not df_pag_raw.empty and "Proyecto" in df_pag_raw.columns
        else pd.DataFrame(columns=["Proyecto", "Monto"])
    )

    df_mat_raw = st.session_state.materiales if "materiales" in st.session_state else pd.DataFrame(columns=["Proyecto", "Costo_Real"])
    df_mat = (
        df_mat_raw[df_mat_raw["Proyecto"].isin(nombres_base)]
        if not df_mat_raw.empty and "Proyecto" in df_mat_raw.columns
        else pd.DataFrame(columns=["Proyecto", "Costo_Real"])
    )

    util_rec_info = obtener_utilidades_recibidas_estudio(nombres_base)
    fin_base = calcular_datos_finanzas_estudio(
        df_p_base,
        df_cob,
        df_pag,
        df_gg,
        df_mat,
        df_ing,
        util_rec_info,
        anios_filtro=None,
        fecha_ref=fecha_hoy,
    )
    kg_all = fin_base["kpis_globales"]

    # Sub-módulo de Manejo de Caja Chica y Gastos Generales (Punto 1.3)
    if st.session_state.get("modulo_caja_chica_abierto", False):
        col_back_cc, col_tit_cc = st.columns([2.2, 7.8])
        with col_back_cc:
            if st.button("⬅ VOLVER A FINANZAS", key="btn_volver_finanzas", use_container_width=True):
                st.session_state.modulo_caja_chica_abierto = False
                st.rerun()
        with col_tit_cc:
            st.markdown("### 💼 MÓDULO DE MANEJO DE CAJA CHICA Y GASTOS GENERALES")

        st.markdown(
            "<div style='background:#FAF8F5; border:2px dashed #C85A32; border-radius:12px; padding:24px; text-align:center; margin:14px 0 20px 0;'>"
            "<span style='font-family:monospace; font-size:12px; font-weight:700; color:#C85A32; background:rgba(200,90,50,0.12); padding:4px 10px; border-radius:6px; border:1px solid #C85A32;'>🚀 PRÓXIMAMENTE</span>"
            "<h3 style='color:#262320; margin:12px 0 6px 0;'>Módulo de Manejo de Caja Chica y Gastos Generales</h3>"
            "<p style='color:#6E665E; font-size:14px; max-width:680px; margin:0 auto;'>"
            "Aquí podrás gestionar reposiciones de fondo fijo, rendiciones por proyecto, gastos generales de oficina y aprobaciones de caja chica. "
            "<b>Disponible muy pronto en la siguiente iteración.</b></p>"
            "</div>",
            unsafe_allow_html=True,
        )

        render_metric_row([
            {"title": "Presupuesto Caja Chica", "value": format_currency(kg_all["tot_caja_ppto"]), "subtitle": "Fondo total asignado a proyectos"},
            {"title": "Caja Chica Ejecutada", "value": format_currency(kg_all["tot_caja_gastada"]), "subtitle": f"{kg_all['pct_caja']:.1f}% del presupuesto ejecutado", "border_color": "#C85A32", "text_color": "#C85A32"},
            {"title": "Saldo Disponible Caja", "value": format_currency(kg_all["saldo_caja"]), "subtitle": "Presupuesto restante por ejecutar", "border_color": "#4A7C59" if kg_all["saldo_caja"] >= 0 else "#C93B2B", "text_color": "#4A7C59" if kg_all["saldo_caja"] >= 0 else "#C93B2B"},
            {"title": "Gastos Generales Cobrados", "value": format_currency(kg_all["gg_cobrados"]), "subtitle": "Ingresos aplicados a caja / GG", "border_color": "#4A7C59", "text_color": "#4A7C59"},
        ])

        if not df_gg.empty:
            st.markdown("#### 📋 Vista Previa de Movimientos de Caja Chica Registrados")
            st.dataframe(df_gg, use_container_width=True, hide_index=True)
        return

    st.markdown("### 📊 FINANZAS")
    st.caption("Control ejecutivo anual y por proyecto de proyectos aprobados (En Proceso y Completado): ventas, utilidades, gastos generales, caja chica y cobros.")

    anios_disp = fin_base["anios_disponibles"] or [str(fecha_hoy.year)]
    k_anios_key = "fin_filtro_anios"
    if k_anios_key in st.session_state:
        anios_prev = [a for a in st.session_state[k_anios_key] if a in anios_disp]
        if len(anios_prev) != len(st.session_state[k_anios_key]):
            st.session_state[k_anios_key] = anios_prev or list(anios_disp)

    kpi_opts = [k["label"] for k in FINANZAS_KPIS_CONFIG]
    kpi_defs = [k["label"] for k in FINANZAS_KPIS_CONFIG if k["default"]]
    k_kpis_key = "fin_filtro_kpis"
    if k_kpis_key in st.session_state:
        kpis_prev = [k for k in st.session_state[k_kpis_key] if k in kpi_opts]
        if len(kpis_prev) != len(st.session_state[k_kpis_key]):
            st.session_state[k_kpis_key] = kpis_prev or list(kpi_defs)

    cf1, cf2, cf3 = st.columns([3.0, 4.4, 2.6])
    with cf1:
        anios_sel = st.multiselect(
            "📅 Años a visualizar:",
            options=anios_disp,
            default=list(anios_disp),
            key=k_anios_key,
        )
    with cf2:
        kpis_sel = st.multiselect(
            "📊 KPIs en el gráfico:",
            options=kpi_opts,
            default=kpi_defs,
            key=k_kpis_key,
        )
    with cf3:
        vista_graf = st.radio(
            "Vista del gráfico:",
            options=["📅 Anual", "🏗️ Por Proyecto"],
            index=0,
            horizontal=True,
            key="fin_vista_grafico",
        )
        st.checkbox("Incluir proyectos archivados", key="fin_incluir_archivados")

    fin_filt = calcular_datos_finanzas_estudio(
        df_p_base,
        df_cob,
        df_pag,
        df_gg,
        df_mat,
        df_ing,
        util_rec_info,
        anios_filtro=anios_sel,
        fecha_ref=fecha_hoy,
    )
    kg = fin_filt["kpis_globales"]

    col_caja_card = "#C85A32" if kg["tot_caja_gastada"] <= kg["tot_caja_ppto"] else "#C93B2B"

    cw1, cw2, cw3, cw4 = st.columns(4)
    with cw1:
        render_metric_card(
            "1. Total Contratos",
            format_currency(kg["tot_ventas"]),
            f"{kg['num_proyectos']} proyectos · Honorarios: {format_currency(kg['tot_hon'])}",
        )
    with cw2:
        render_metric_card(
            "2. Utilidades",
            format_currency(kg["tot_utilidades"]),
            f"Margen est.: {kg['pct_util_contratos']:.0f}% · Recibidas: {format_currency(kg['util_ejecutadas'])}",
            border_color="#4A7C59",
            text_color="#4A7C59",
        )
    with cw3:
        render_metric_card(
            "3. Caja Chica Ejecutada vs Caja Chica ↗",
            f"{format_currency(kg['tot_caja_gastada'])} / {format_currency(kg['tot_caja_ppto'])}",
            f"Ejecutado: {kg['pct_caja']:.1f}% · Saldo: {format_currency(kg['saldo_caja'])}",
            border_color=col_caja_card,
            text_color=col_caja_card,
        )
        if st.button("Abrir Caja Chica y Gastos Generales", key="btn_open_modulo_caja", use_container_width=True):
            st.session_state.modulo_caja_chica_abierto = True
            st.rerun()
    with cw4:
        render_metric_card(
            "4. Utilidades Recibidas + GG Cobrados",
            format_currency(kg["tot_util_ejec_mas_gg"]),
            f"Util. Recibidas: {format_currency(kg['util_ejecutadas'])} · GG: {format_currency(kg['gg_cobrados'])}",
            border_color="#4A7C59",
            text_color="#4A7C59",
        )

    st.divider()

    if df_p_base.empty:
        st.info("No hay proyectos aprobados (En Proceso o Completado) registrados.")
        return

    _render_finanzas_chart_y_resumen(fin_filt, kpis_sel, vista_graf)

    st.markdown("#### DETALLE FINANCIERO POR PROYECTO")
    rows_fin = fin_filt["rows_fin"]
    if rows_fin:
        df_fin_disp = pd.DataFrame(rows_fin)
        st.dataframe(df_fin_disp, use_container_width=True, hide_index=True)

        csv_bytes = df_fin_disp.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 EXPORTAR REPORTE FINANCIERO A CSV",
            data=csv_bytes,
            file_name=f"finanzas_cota_{datetime.date.today().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.info("No hay proyectos dentro de los años seleccionados.")


def _render_tab_operativo_diario(lista_socios, fecha_hoy, conn, sheet_url, nube_ok):
    """Pestaña 4: Requerimientos diarios, obras activas hoy y próximos arranques."""
    co1, co2, co3 = st.columns([1.2, 1, 1])

    with co1:
        st.markdown("#### 📋 LOGÍSTICA DIARIA Y PENDIENTES")
        with st.popover("➕ NUEVO REQUERIMIENTO", use_container_width=True):
            with st.form("form_nuevo_todo", clear_on_submit=True):
                p_act = get_proyectos_activos(st.session_state.proyectos)['Nombre'].tolist()
                t_p = st.selectbox("Asignar a Proyecto", ["General"] + p_act)
                t_r = st.selectbox("Responsable", lista_socios, index=(lista_socios.index(st.session_state.get("socio_activo")) if st.session_state.get("socio_activo") in lista_socios else 0))
                t_cat = st.selectbox("Clasificación", ["Compras / FF&E", "Pagos", "Proveedores", "Coordinación Cliente", "Supervisión Obra"])
                t_txt = st.text_input("Detalle de Actividad")
                if st.form_submit_button("REGISTRAR ACTIVIDAD") and t_txt:
                    n_i = pd.DataFrame([{
                        'ID': datetime.datetime.now().timestamp(),
                        'Proyecto': t_p,
                        'Categoria': t_cat,
                        'Tarea': t_txt,
                        'Responsable': t_r,
                        'Check': False
                    }])
                    st.session_state.todo_list = pd.concat([st.session_state.todo_list, n_i], ignore_index=True)
                    clear_base_dfs()
                    st.rerun()

        pendientes_mostrados = 0
        for i, row in st.session_state.todo_list.iterrows():
            if not to_bool(row.get('Check', False)):
                pendientes_mostrados += 1
                ci, cb = st.columns([8, 2])
                ci.markdown(
                    f"<div style='background:#FFFFFF; padding:10px 12px; border:1px solid #DFD9CE; border-left:3px solid #C85A32; border-radius:6px; margin-bottom:6px;'>"
                    f"<b style='color:#6E665E; font-size:11px; text-transform:uppercase;'>[{row.get('Categoria', 'Tarea')}]</b> "
                    f"<span style='color:#262320; font-weight:500;'>{row.get('Tarea', '')}</span><br>"
                    f"<small style='color:#C85A32; font-family:monospace; font-weight:600;'>RESP: {row.get('Responsable', '').upper()}  |  PRY: {row.get('Proyecto', '')}</small></div>",
                    unsafe_allow_html=True
                )
                if cb.button("✓ LISTO", key=f"todo_done_{row.get('ID', i)}", use_container_width=True):
                    st.session_state.todo_list = st.session_state.todo_list.drop(i).reset_index(drop=True)
                    guardar_tabla(conn, sheet_url, nube_ok, st.session_state.todo_list, 'logistica')
                    st.rerun()

        if pendientes_mostrados == 0:
            st.info("No hay requerimientos pendientes en la agenda del estudio.")

    with co2:
        st.markdown("#### 🔨 EN EJECUCIÓN (HOY)")
        df_tasks_act = st.session_state.tasks.copy()
        df_tasks_act['Inicio_DT'] = df_tasks_act['Inicio'].apply(lambda x: pd.to_datetime(parse_date(x)))
        df_tasks_act['Fin_DT'] = df_tasks_act['Fin'].apply(lambda x: pd.to_datetime(parse_date(x)))
        df_tasks_act = df_tasks_act.dropna(subset=['Inicio_DT', 'Fin_DT'])

        if not df_tasks_act.empty:
            t_hoy = df_tasks_act[(df_tasks_act['Inicio_DT'].dt.date <= fecha_hoy) & (df_tasks_act['Fin_DT'].dt.date >= fecha_hoy)]
            if not t_hoy.empty:
                for p_n in t_hoy['Proyecto'].unique():
                    st.markdown(f"<div style='color:#C85A32; font-weight:700; font-size:12px; margin-top:10px; text-transform:uppercase;'>■ {p_n}</div>", unsafe_allow_html=True)
                    for _, t in t_hoy[t_hoy['Proyecto'] == p_n].iterrows():
                        st.markdown(
                            f"<div style='border-left: 3px solid #4A7C59; background:#FFFFFF; border:1px solid #DFD9CE; border-left-width:3px; border-left-color:#4A7C59; border-radius:6px; padding:8px 10px; margin-bottom:6px;'>"
                            f"<b style='color:#262320;'>{t.get('Tarea', '')}</b><br><small style='color:#6E665E;'>Especialista: {t.get('Contratista', 'Sin asignar')}</small></div>",
                            unsafe_allow_html=True
                        )
            else:
                st.info("No hay partidas de obra programadas para hoy.")
        else:
            st.info("Sin tareas registradas.")

    with co3:
        st.markdown("#### 📅 PRÓXIMOS ARRANQUES (7 DÍAS)")
        if not df_tasks_act.empty:
            lim_7d = fecha_hoy + datetime.timedelta(days=7)
            t_7 = df_tasks_act[(df_tasks_act['Inicio_DT'].dt.date > fecha_hoy) & (df_tasks_act['Inicio_DT'].dt.date <= lim_7d)].sort_values('Inicio_DT')
            if not t_7.empty:
                for p_n in t_7['Proyecto'].unique():
                    st.markdown(f"<div style='color:#D98A2B; font-weight:700; font-size:12px; margin-top:10px; text-transform:uppercase;'>■ {p_n}</div>", unsafe_allow_html=True)
                    for _, t in t_7[t_7['Proyecto'] == p_n].iterrows():
                        st.markdown(
                            f"<div style='border-left: 3px solid #D98A2B; background:#FFFFFF; border:1px solid #DFD9CE; border-left-width:3px; border-left-color:#D98A2B; border-radius:6px; padding:8px 10px; margin-bottom:6px;'>"
                            f"<b style='color:#262320;'>{t.get('Tarea', '')}</b><br><small style='color:#6E665E;'>Arranca: {t['Inicio_DT'].strftime('%d %b')}  |  CTR: {t.get('Contratista', 'Sin asignar')}</small></div>",
                            unsafe_allow_html=True
                        )
            else:
                st.info("Sin arranques en los próximos 7 días.")


def _render_tab_calendario(fecha_hoy):
    """Pestaña 5: Calendario técnico mensual con visualización de obras y fases."""
    if 'cal_month_offset' not in st.session_state:
        st.session_state.cal_month_offset = 0

    c_n1, c_n2, c_n3 = st.columns([1, 2, 1])
    if c_n1.button("◀ MES ANTERIOR", use_container_width=True):
        st.session_state.cal_month_offset -= 1
        st.rerun()
    if c_n3.button("SIGUIENTE MES ▶", use_container_width=True):
        st.session_state.cal_month_offset += 1
        st.rerun()

    t_d = pd.to_datetime(fecha_hoy) + pd.DateOffset(months=st.session_state.cal_month_offset)
    meses_es = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    c_n2.markdown(f"<h3 style='text-align:center; color:#C85A32 !important; font-family:monospace; margin:0;'>{meses_es[t_d.month].upper()} {t_d.year}</h3>", unsafe_allow_html=True)

    cal = calendar.monthcalendar(t_d.year, t_d.month)
    p_c = {}
    for _, pr_r in st.session_state.proyectos.iterrows():
        raw_col = str(pr_r.get('Color', '#C85A32'))
        # Reemplazar cian neón antiguo por terracota cálido para legibilidad sobre fondo claro
        if raw_col.upper() in ['#00E5FF', 'NAN', 'NONE', '']:
            raw_col = '#C85A32'
        p_c[pr_r['Nombre']] = raw_col

    df_tasks_act = st.session_state.tasks.copy()
    df_tasks_act['Inicio_Date'] = df_tasks_act['Inicio'].apply(lambda x: parse_date(x))
    df_tasks_act['Fin_Date'] = df_tasks_act['Fin'].apply(lambda x: parse_date(x))
    df_tasks_act = df_tasks_act.dropna(subset=['Inicio_Date', 'Fin_Date'])

    h_c = "<div class='calendar-container'>"
    for d in ["LUN", "MAR", "MIE", "JUE", "VIE", "SAB", "DOM"]:
        h_c += f"<div class='calendar-header-day'>{d}</div>"

    for w in cal:
        for d in w:
            if d == 0:
                h_c += "<div class='calendar-cell' style='background:transparent; border:none;'></div>"
            else:
                c_dt = datetime.date(t_d.year, t_d.month, d)
                cls = "today" if c_dt == fecha_hoy else ""
                h_c += f"<div class='calendar-cell {cls}'><div class='calendar-cell-date'>{d}</div>"

                if not df_tasks_act.empty:
                    t_day = df_tasks_act[(df_tasks_act['Inicio_Date'] <= c_dt) & (df_tasks_act['Fin_Date'] >= c_dt)]
                    for _, t in t_day.iterrows():
                        prj = t.get('Proyecto', 'General')
                        col_p = p_c.get(prj, '#C85A32')
                        tarea_txt = f"{prj[:8]}: {t.get('Tarea', '')[:14]}"
                        h_c += f"<div class='cal-task-item' style='background:{col_p}1A; border-left: 3px solid {col_p}; color:#262320;'>{tarea_txt}</div>"

                h_c += "</div>"

    h_c += "</div>"
    st.markdown(h_c, unsafe_allow_html=True)


def _render_tab_archivo():
    """Pestaña 6: Archivo histórico con confirmación de purga."""
    st.markdown("### 🗄️ ARCHIVO HISTÓRICO DE PROYECTOS")
    st.caption("Proyectos completados o pausados. Puedes restaurarlos al portafolio activo o purgarlos con confirmación.")

    df_a = get_proyectos_archivados(st.session_state.proyectos)
    if df_a.empty:
        st.info("El archivo histórico está vacío.")
        return

    for idx, r in df_a.iterrows():
        p_name = r['Nombre']
        with st.container(border=True):
            ca1, ca2, ca3 = st.columns([6, 2, 2])
            ca1.markdown(f"**PROYECTO: {p_name}**  <small style='color:#6E665E;'>({r.get('Tipo_Proyecto', '')} · Cliente: {r.get('Cliente', 'N/A')})</small>", unsafe_allow_html=True)

            if ca2.button("↩ RESTAURAR", key=f"rest_{idx}", use_container_width=True):
                st.session_state.proyectos.at[idx, 'Archivado'] = False
                clear_base_dfs()
                st.rerun()

            with ca3:
                with st.popover("🗑️ PURGAR DEFINITIVAMENTE", use_container_width=True):
                    st.warning(f"¿Estás seguro de eliminar '{p_name}'? Se eliminarán todas sus tareas, pagos y entregables asociados.")
                    if st.button("CONFIRMAR PURGA", key=f"conf_purge_{idx}", type="primary", use_container_width=True):
                        purgar_proyecto_cascada(p_name)
                        clear_base_dfs()
                        st.success(f"Proyecto '{p_name}' purgado del sistema.")
                        st.rerun()
