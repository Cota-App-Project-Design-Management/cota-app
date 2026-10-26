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
from cota.cotizacion import (
    aplicar_cotizacion_a_proyecto,
    generar_plantilla_cotizacion_venti,
    parsear_cotizacion_venti,
    parsear_presupuesto_flexible,
)
from cota.ui.components import render_metric_card, render_metric_row
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

    # 2. Barra de herramientas: Nuevo Proyecto + Cotización / Importar Presupuesto + Buscador
    col_new, col_cot, col_search = st.columns([2.6, 2.8, 4.6])
    banco_fases_estudio = obtener_banco_fases()
    nombres_banco_all = [f["Fase"] for f in banco_fases_estudio]
    nombres_banco_def = [f["Fase"] for f in banco_fases_estudio if f.get("Por_Defecto", True)]

    tipos_cat = obtener_catalogo_estudio("tipos_proyecto") or TIPOS_PROYECTO

    with col_new:
        with st.popover("➕ NUEVO PROYECTO DE DISEÑO", use_container_width=True):
            with st.form("form_nuevo_proy", clear_on_submit=True):
                pn = st.text_input("Nombre / Código del Proyecto (Único)", placeholder="ej. Casa Las Casuarinas").strip()
                sel_div = st.selectbox("Carpeta / Cliente", exist_divs + ["+ Crear Nueva Carpeta"])
                p_div = st.text_input("Nombre de Nueva Carpeta") if sel_div == "+ Crear Nueva Carpeta" else sel_div
                sel_ubi = st.selectbox("Ubicación", exist_ubis + ["+ Agregar Ubicación"])
                p_ubi_new = st.text_input("Nueva Ubicación (si elegiste '+ Agregar Ubicación')", placeholder="ej. Chacarilla, Surco").strip()
                p_ubi = p_ubi_new if (sel_ubi == "+ Agregar Ubicación" and p_ubi_new) else (exist_ubis[0] if sel_ubi == "+ Agregar Ubicación" else sel_ubi)
                pe = st.selectbox("Líder de Proyecto", lista_socios)
                ps = st.selectbox("Estado Inicial", STATUS_PROYECTOS)
                p_tipo = st.selectbox("Tipo de Proyecto", tipos_cat)
                p_cliente = st.text_input("Nombre del Cliente", placeholder="ej. Familia Gómez")
                p_color = st.color_picker("Color Identificador", value="#C85A32")

                st.markdown("##### Fases Activas del Proyecto (Banco de Fases)")
                fases_sel_nuevo = st.multiselect(
                    "Selecciona las fases que aplican a este proyecto:",
                    options=[f for f in nombres_banco_all if "ff&e" not in f.lower() and "ffe" not in f.lower()],
                    default=[f for f in nombres_banco_def if "ff&e" not in f.lower() and "ffe" not in f.lower()],
                )
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
                        fases_a_sembrar = [f for f in (fases_sel_nuevo if fases_sel_nuevo else nombres_banco_def) if "ff&e" not in f.lower() and "ffe" not in f.lower()]
                        nuevas_fases = sembrar_fases_default(pn, fecha_hoy, fases_seleccionadas=fases_a_sembrar)
                        if 'fases' not in st.session_state or st.session_state.fases.empty:
                            st.session_state.fases = nuevas_fases
                        else:
                            st.session_state.fases = pd.concat([st.session_state.fases, nuevas_fases], ignore_index=True)

                        clear_base_dfs()
                        st.success(f"Proyecto '{pn}' creado exitosamente con {len(fases_a_sembrar)} fase(s) activa(s).")
                        st.rerun()

    with col_cot:
        if st.button("📄 COTIZACIÓN / IMPORTAR PPTO.", use_container_width=True, key="btn_open_cot_portafolio"):
            st.session_state["show_cot_portafolio"] = not st.session_state.get("show_cot_portafolio", False)

    with col_search:
        search_q = st.text_input(
            "Buscar proyecto o cliente:",
            placeholder="🔍 Filtrar por nombre de proyecto, cliente, tipo o ubicación...",
            label_visibility="collapsed"
        )

    # Panel desplegable en Portafolio: Plantilla de Cotización e Importador Inteligente
    if st.session_state.get("show_cot_portafolio", False):
        with st.container(border=True):
            ch_c1, ch_c2 = st.columns([8.5, 1.5])
            with ch_c1:
                st.markdown("#### 📄 FORMATO DE COTIZACIÓN E IMPORTADOR DE PRESUPUESTO")
                st.caption("Descarga la plantilla oficial de cotización para que el cliente o el estudio la llene, e impórtala directamente a un proyecto para cargar automáticamente Partidas, Tareas, Presupuestos asignados, Gastos Generales y Utilidades.")
            with ch_c2:
                if st.button("✖ Cerrar", key="btn_close_cot_portafolio", use_container_width=True):
                    st.session_state["show_cot_portafolio"] = False
                    st.rerun()

            col_dl_p, col_imp_p = st.columns([1, 1.4])
            with col_dl_p:
                st.markdown("##### 1. Descargar Plantilla de Cotización")
                dl_p_nom = st.text_input("Nombre del Proyecto (opcional para cabecera)", placeholder="ej. Proyecto Galeon 129", key="dl_p_nom_port")
                dl_c_nom = st.text_input("Cliente (opcional para cabecera)", placeholder="ej. Nano Salazar", key="dl_c_nom_port")

                c_p1, c_p2, c_p3 = st.columns(3)
                with c_p1:
                    dl_tc = st.number_input("Tipo de Cambio (TC)", value=3.42, step=0.01, format="%.2f", key="dl_tc_port")
                with c_p2:
                    dl_gg_pct = st.number_input("% Gastos Generales", value=2.0, min_value=0.0, max_value=100.0, step=0.5, format="%.1f", key="dl_gg_pct_port")
                with c_p3:
                    dl_ges_pct = st.number_input("% Gestión y Superv.", value=15.0, min_value=0.0, max_value=100.0, step=0.5, format="%.1f", key="dl_ges_pct_port")

                dl_igv = st.checkbox("Incluir IGV (18%)", value=False, help="Si se marca, la plantilla aplicará 18% de IGV; si no, quedará en 0%.", key="dl_igv_port")

                xlsx_template_bytes = generar_plantilla_cotizacion_venti(
                    proyecto=dl_p_nom,
                    cliente=dl_c_nom,
                    tc=dl_tc,
                    gg_pct=dl_gg_pct / 100.0,
                    gestion_pct=dl_ges_pct / 100.0,
                    incluir_igv=dl_igv,
                )
                fname_clean = dl_p_nom.strip().replace(" ", "_") if dl_p_nom.strip() else "COTA"
                st.download_button(
                    "📥 DESCARGAR FORMATO COTIZACIÓN (.XLSX)",
                    data=xlsx_template_bytes,
                    file_name=f"Formato_Cotizacion_{fname_clean}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    use_container_width=True,
                    key="btn_dl_template_portafolio",
                )

            with col_imp_p:
                st.markdown("##### 2. Importar Presupuesto (Excel / CSV / Gemini Spark)")
                modo_imp_port = st.radio(
                    "Fuente del presupuesto:",
                    options=["archivo", "texto"],
                    format_func=lambda x: "📁 Subir archivo (.xlsx / .csv)" if x == "archivo" else "🤖 Pegar tabla de Gemini Spark / Excel / Markdown",
                    horizontal=True,
                    key="rad_fuente_imp_port",
                )
                parsed_p = None
                if modo_imp_port == "archivo":
                    up_port_file = st.file_uploader(
                        "Sube el archivo de presupuesto llenado:",
                        type=["xlsx", "xls", "csv"],
                        key="up_cot_file_portafolio",
                    )
                    if up_port_file is not None:
                        parsed_p = parsear_presupuesto_flexible(up_port_file)
                else:
                    txt_spark_port = st.text_area(
                        "Pega aquí la tabla generada en Gemini Spark, Excel o CSV (con Partidas, Tareas, Unidad, Metraje, V. Unitario, Valor Parcial):",
                        height=150,
                        placeholder="| Item | Descripción | Unidad | Metraje | V. Unitario | Valor Parcial |\n|---|---|---|---|---|---|\n| 1.0 | OBRAS PROVISIONALES | | | | |\n| 1.01 | Desmontaje y limpieza | glb | 1 | 1500 | 1500 |",
                        key="txt_spark_portafolio",
                    )
                    if txt_spark_port and txt_spark_port.strip():
                        parsed_p = parsear_presupuesto_flexible(txt_spark_port)

                if parsed_p is not None and parsed_p.get("partidas"):
                    st.markdown(
                        f"**Resumen detectado:** Sub Total Casco: `{format_currency(parsed_p['subtotal_casco'])}` · "
                        f"Gastos Generales ({parsed_p['gg_pct']:g}%): `{format_currency(parsed_p['gg_monto'])}` · "
                        f"Gestión/Utilidades ({parsed_p['utilidades_pct']:g}%): `{format_currency(parsed_p['utilidades_monto'])}` · "
                        f"**TOTAL: `{format_currency(parsed_p['presupuesto_total'])}`**"
                    )

                    destino_opt = st.radio(
                        "Destino de la importación:",
                        options=["existente", "nuevo"] if nombres_act else ["nuevo"],
                        format_func=lambda x: "🔄 Importar en un proyecto existente" if x == "existente" else "➕ Crear un proyecto nuevo con este presupuesto",
                        horizontal=True,
                        key="rad_dest_imp_port",
                    )

                    if destino_opt == "existente" and nombres_act:
                        proy_dest = st.selectbox("Selecciona el Proyecto:", nombres_act, key="sel_proy_dest_port")
                    else:
                        proy_dest = st.text_input(
                            "Nombre del Nuevo Proyecto:",
                            value=parsed_p.get("proyecto") or "",
                            placeholder="ej. Proyecto Galeon 129",
                            key="txt_new_proy_dest_port",
                        ).strip()
                        cli_dest = st.text_input(
                            "Cliente:",
                            value=parsed_p.get("cliente") or "",
                            key="txt_new_cli_dest_port",
                        ).strip()

                    # Permitir nombrar las partidas detectadas antes de importar
                    nombres_ov_port = {}
                    for p_it in parsed_p["partidas"]:
                        p_c = p_it["codigo"]
                        nombres_ov_port[p_c] = st.text_input(
                            f"Partida {p_c} ({format_currency(p_it['monto_pactado'])} · {len(p_it['tareas'])} tareas):",
                            value=p_it["nombre_completo"],
                            key=f"port_pnom_{p_c}",
                        )

                    todas_vac_p = all(
                        (not p["tareas"] and p["monto_pactado"] == 0)
                        for p in parsed_p["partidas"]
                    ) if parsed_p["partidas"] else True

                    if st.button("✅ IMPORTAR PRESUPUESTO AHORA", type="primary", use_container_width=True, key="btn_exec_imp_port"):
                        if not proy_dest:
                            st.error("Indica el nombre del proyecto para importar el presupuesto.")
                        else:
                            if destino_opt == "nuevo" or proy_dest not in st.session_state.proyectos["Nombre"].tolist():
                                n_proy_dict = {
                                    "Nombre": proy_dest,
                                    "Encargado": lista_socios[0] if lista_socios else "Alvaro",
                                    "Ubicación": "Lima",
                                    "Estado": STATUS_PROYECTOS[0],
                                    "Inicio": parsed_p.get("fecha") or fecha_hoy.strftime("%Y-%m-%d"),
                                    "Fin": (fecha_hoy + datetime.timedelta(days=90)).strftime("%Y-%m-%d"),
                                    "Color": "#C85A32",
                                    "Presupuesto": parsed_p["presupuesto_total"],
                                    "Utilidades": parsed_p["utilidades_monto"],
                                    "GG_Presupuesto": parsed_p["gg_monto"],
                                    "Archivado": False,
                                    "Metodologia": "Diseño Interior",
                                    "Division": "General",
                                    "Tipo_Proyecto": TIPOS_PROYECTO[0],
                                    "Num_Pisos": 0,
                                    "Num_Sotanos": 0,
                                    "Presupuesto_FFE": 0.0,
                                    "Honorarios_Diseno": 0.0,
                                    "Cliente": cli_dest if destino_opt == "nuevo" else parsed_p.get("cliente", ""),
                                    "Notas": "",
                                    "TC_Presupuesto": parsed_p.get("tc", 3.42),
                                    "GG_Pct": parsed_p.get("gg_pct", 2.0),
                                    "Utilidades_Pct": parsed_p.get("utilidades_pct", 15.0),
                                    "Incluir_IGV": parsed_p.get("incluir_igv", False),
                                }
                                for col in COLS_PROY:
                                    if col not in n_proy_dict:
                                        n_proy_dict[col] = False if col in ['Archivado', 'Incluir_IGV'] else 0.0
                                n_proy_df = pd.DataFrame([n_proy_dict])
                                st.session_state.proyectos = pd.concat([st.session_state.proyectos, n_proy_df[COLS_PROY]], ignore_index=True)
                                nuevas_f = sembrar_fases_default(proy_dest, fecha_hoy, fases_seleccionadas=nombres_banco_def)
                                if "fases" not in st.session_state or st.session_state.fases.empty:
                                    st.session_state.fases = nuevas_f
                                else:
                                    st.session_state.fases = pd.concat([st.session_state.fases, nuevas_f], ignore_index=True)

                            res_p = aplicar_cotizacion_a_proyecto(
                                proy_name=proy_dest,
                                parsed_data=parsed_p,
                                modo="reemplazar",
                                actualizar_ficha=True,
                                nombres_partidas_override=nombres_ov_port,
                                incluir_partidas_vacias=todas_vac_p,
                            )
                            st.session_state["show_cot_portafolio"] = False
                            st.session_state.proy_activo = proy_dest
                            st.session_state.vista_actual = "proyecto"
                            st.success(
                                f"Presupuesto importado en '{proy_dest}': {res_p['partidas_importadas']} partidas y {res_p['tareas_importadas']} tareas."
                            )
                            st.rerun()

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

                    # Calcular avance de fases activas
                    pct_avance = 0
                    fase_actual_str = "Sin fases activas"
                    fases_activas_proy = []
                    if 'fases' in st.session_state and not st.session_state.fases.empty:
                        f_p = st.session_state.fases[st.session_state.fases['Proyecto'] == p_nom].sort_values(by='Orden')
                        if not f_p.empty:
                            fases_activas_proy = f_p['Fase'].tolist()
                            ok_cnt = len(f_p[f_p['Aprobado_Cliente'].apply(to_bool) | (f_p['Estado'].astype(str).str.contains('Aprobada', case=False))])
                            pct_avance = int(ok_cnt / len(f_p) * 100)
                            en_curso = f_p[~(f_p['Aprobado_Cliente'].apply(to_bool) | (f_p['Estado'].astype(str).str.contains('Aprobada', case=False)))]
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
                            f"<div><span style='color:#6E665E; font-size:11px; text-transform:uppercase;'>Fase Actual</span><br><b style='color:#C85A32;'>{fase_actual_str}</b></div>"
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
                                    n_ubi_new = st.text_input("Nueva Ubicación (opcional)", placeholder="ej. San Borja").strip()
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
                            with st.popover("🗂️ FASES DEL PROYECTO", use_container_width=True):
                                st.markdown("##### Banco de Fases")
                                st.caption("Activa o desactiva las fases que corresponden a las características de este proyecto.")
                                with st.form(f"f_banco_fases_card_{ukey}"):
                                    opciones_f_card = list(dict.fromkeys(nombres_banco_all + fases_activas_proy))
                                    sel_f_card = st.multiselect(
                                        "Fases activas:",
                                        options=opciones_f_card,
                                        default=fases_activas_proy if fases_activas_proy else nombres_banco_def,
                                    )
                                    nueva_f_card = st.text_input("➕ Crear nueva fase en el banco (opcional):", placeholder="ej. 09. Licencias Municipales")
                                    if st.form_submit_button("GUARDAR FASES DEL PROYECTO", type="primary", use_container_width=True):
                                        fases_finales = list(sel_f_card)
                                        if nueva_f_card.strip():
                                            nf_obj = agregar_fase_banco(nueva_f_card.strip())
                                            if nf_obj["Fase"] not in fases_finales:
                                                fases_finales.append(nf_obj["Fase"])
                                        sincronizar_fases_proyecto(p_nom, fases_finales, proy.get('Inicio'))
                                        st.success("Fases del proyecto actualizadas.")
                                        st.rerun()

                        with c_btn3:
                            notas_chat_card = obtener_notas_chat_proyecto(p_nom)
                            with st.popover(f"💬 NOTAS ({len(notas_chat_card)})", use_container_width=True):
                                st.markdown(f"##### 💬 Notas del Proyecto: {p_nom}")
                                if notas_chat_card:
                                    for msg in notas_chat_card[-6:]:
                                        st.markdown(
                                            f"<div style='background:#FAF8F5; border:1px solid #DFD9CE; border-left:3px solid #C85A32; border-radius:6px; padding:6px 10px; margin-bottom:6px; font-size:12px;'>"
                                            f"<b style='color:#C85A32;'>{msg['socio']}</b> <span style='color:#8C8278; font-size:10.5px;'>· {msg['fecha']}</span><br>"
                                            f"<span style='color:#262320;'>{msg['texto']}</span></div>",
                                            unsafe_allow_html=True,
                                        )
                                else:
                                    st.caption("Aún no hay notas registradas en este proyecto.")
                                with st.form(f"f_notes_m_{ukey}", clear_on_submit=True):
                                    socio_def = st.session_state.get("socio_activo", lista_socios[0] if lista_socios else "Alvaro")
                                    idx_soc = lista_socios.index(socio_def) if socio_def in lista_socios else 0
                                    soc_nota = st.selectbox("Socio", lista_socios, index=idx_soc, key=f"soc_n_card_{ukey}")
                                    c_notas = st.text_area("Escribir nueva nota...", height=80, placeholder="Escribe un acuerdo, comentario o pendiente...")
                                    if st.form_submit_button("ENVIAR NOTA", type="primary", use_container_width=True):
                                        if c_notas and c_notas.strip():
                                            agregar_nota_chat_proyecto(p_nom, soc_nota, c_notas.strip())
                                            st.success("Nota publicada.")
                                            st.rerun()

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
                    nc_nom = st.text_input("Nombre / Empresa Especialista", placeholder="ej. Carpintería Hnos. Silva").strip()
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

            n_rep = st.text_input(f"Añadir evaluación sobre {c_sel}:", placeholder="ej. Cumplió entrega de carpintería antes de fecha pactada...", key="txt_rep_c")
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
                nueva_ubi = st.text_input("➕ Nueva Ubicación / Distrito:", placeholder="ej. San Borja, Asia, Punta Hermosa...")
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
                nueva_esp = st.text_input("➕ Nueva Especialidad:", placeholder="ej. Paisajismo, Domótica, Acústica...")
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
            st.caption("Unidades disponibles al armar partidas y tareas en `03. Presupuesto` (ej. glb, m2, ml, und, pto).")
            with st.form("form_add_uni_bd", clear_on_submit=True):
                nueva_uni = st.text_input("➕ Nueva Unidad de Medida:", placeholder="ej. pza, jgo, mes...")
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
                nuevo_soc = st.text_input("➕ Nuevo Socio / Encargado:", placeholder="ej. Camila")
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
                nuevo_tip = st.text_input("➕ Nuevo Tipo de Proyecto:", placeholder="ej. Hotel / Hospitality")
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


def _render_tab_finanzas_estudio(fecha_hoy):
    """Consolidado de finanzas, utilidades, caja chica y rentabilidad del estudio."""
    df_p_act = get_proyectos_activos(st.session_state.proyectos)
    nombres_activos = df_p_act['Nombre'].tolist()

    # 1. Total Contratos y Honorarios
    tot_ventas = sum(safe_float(v) for v in df_p_act['Presupuesto'])
    tot_hon = sum(safe_float(h) for h in df_p_act.get('Honorarios_Diseno', []))

    # 2. Utilidades Proyectadas (Total de la columna Utilidades de proyectos activos)
    tot_utilidades = sum(safe_float(u) for u in df_p_act.get('Utilidades', []))
    if tot_utilidades == 0.0 and tot_ventas > 0:
        tot_utilidades = tot_ventas * 0.20

    # 3. Caja Chica Ejecutada vs Presupuesto Total para Caja Chica (GG_Presupuesto)
    tot_caja_ppto = sum(safe_float(g) for g in df_p_act.get('GG_Presupuesto', []))
    df_gg = st.session_state.gg_log if 'gg_log' in st.session_state else pd.DataFrame(columns=['Proyecto', 'Monto'])
    if not df_gg.empty and 'Proyecto' in df_gg.columns:
        df_gg = df_gg[df_gg['Proyecto'].isin(nombres_activos)]
    tot_caja_gastada = pd.to_numeric(df_gg['Monto'], errors='coerce').sum() if not df_gg.empty and 'Monto' in df_gg.columns else 0.0
    saldo_caja = tot_caja_ppto - tot_caja_gastada
    pct_caja = (tot_caja_gastada / tot_caja_ppto * 100.0) if tot_caja_ppto > 0 else 0.0

    # 4. Utilidades Ejecutadas + Gastos Generales Cobrados
    df_ing = st.session_state.ingresos_socios if 'ingresos_socios' in st.session_state else pd.DataFrame(columns=['Proyecto', 'Categoria', 'Monto'])
    if not df_ing.empty and 'Proyecto' in df_ing.columns:
        df_ing_act = df_ing[df_ing['Proyecto'].isin(nombres_activos + ['General'])].copy()
    else:
        df_ing_act = pd.DataFrame(columns=['Proyecto', 'Categoria', 'Monto'])

    if not df_ing_act.empty and 'Categoria' in df_ing_act.columns and 'Monto' in df_ing_act.columns:
        cat_s = df_ing_act['Categoria'].astype(str)
        mask_util = cat_s.str.contains('Utilidad|Honorario', case=False, na=False)
        mask_gg = cat_s.str.contains('Gasto|Caja|GG', case=False, na=False)
        util_ejecutadas = float(pd.to_numeric(df_ing_act.loc[mask_util, 'Monto'], errors='coerce').fillna(0.0).sum())
        gg_cobrados = float(pd.to_numeric(df_ing_act.loc[mask_gg, 'Monto'], errors='coerce').fillna(0.0).sum())
    else:
        util_ejecutadas = 0.0
        gg_cobrados = 0.0

    tot_util_ejec_mas_gg = util_ejecutadas + gg_cobrados

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
            {"title": "Presupuesto Caja Chica", "value": format_currency(tot_caja_ppto), "subtitle": "Fondo total asignado a proyectos"},
            {"title": "Caja Chica Ejecutada", "value": format_currency(tot_caja_gastada), "subtitle": f"{pct_caja:.1f}% del presupuesto ejecutado", "border_color": "#C85A32", "text_color": "#C85A32"},
            {"title": "Saldo Disponible Caja", "value": format_currency(saldo_caja), "subtitle": "Presupuesto restante por ejecutar", "border_color": "#4A7C59" if saldo_caja >= 0 else "#C93B2B", "text_color": "#4A7C59" if saldo_caja >= 0 else "#C93B2B"},
            {"title": "Gastos Generales Cobrados", "value": format_currency(gg_cobrados), "subtitle": "Ingresos aplicados a caja / GG", "border_color": "#4A7C59", "text_color": "#4A7C59"},
        ])

        if not df_gg.empty:
            st.markdown("#### 📋 Vista Previa de Movimientos de Caja Chica Registrados")
            st.dataframe(df_gg, use_container_width=True, hide_index=True)
        return

    st.markdown("### 📊 FINANZAS")
    st.caption("Control ejecutivo de contratos activos, utilidades proyectadas, ejecución de caja chica y utilidades + gastos generales cobrados.")

    # Cobrado a clientes y egresos adicionales para tablas y gráficos
    df_cob = st.session_state.cobros if 'cobros' in st.session_state else pd.DataFrame()
    if not df_cob.empty and 'Proyecto' in df_cob.columns:
        df_cob = df_cob[df_cob['Proyecto'].isin(nombres_activos)]

    df_pag = st.session_state.pagos if 'pagos' in st.session_state else pd.DataFrame(columns=['Proyecto', 'Monto'])
    if not df_pag.empty and 'Proyecto' in df_pag.columns:
        df_pag = df_pag[df_pag['Proyecto'].isin(nombres_activos)]

    df_mat = st.session_state.materiales if 'materiales' in st.session_state else pd.DataFrame(columns=['Proyecto', 'Costo_Real'])
    if not df_mat.empty and 'Proyecto' in df_mat.columns:
        df_mat = df_mat[df_mat['Proyecto'].isin(nombres_activos)]

    col_caja_card = "#C85A32" if tot_caja_gastada <= tot_caja_ppto else "#C93B2B"
    pct_util_contratos = (tot_utilidades / tot_ventas * 100.0) if tot_ventas > 0 else 0.0

    # Los 4 Widgets de Finanzas (Punto 1.2 - Foto 1) + Acceso directo a Caja Chica (Punto 1.3)
    cw1, cw2, cw3, cw4 = st.columns(4)
    with cw1:
        render_metric_card(
            "1. Total Contratos",
            format_currency(tot_ventas),
            f"{len(df_p_act)} proyectos · Honorarios: {format_currency(tot_hon)}",
        )
    with cw2:
        render_metric_card(
            "2. Utilidades",
            format_currency(tot_utilidades),
            f"Margen estimado: {pct_util_contratos:.0f}% sobre contratos",
            border_color="#4A7C59",
            text_color="#4A7C59",
        )
    with cw3:
        render_metric_card(
            "3. Caja Chica Ejecutada vs Caja Chica ↗",
            f"{format_currency(tot_caja_gastada)} / {format_currency(tot_caja_ppto)}",
            f"Ejecutado: {pct_caja:.1f}% · Saldo: {format_currency(saldo_caja)}",
            border_color=col_caja_card,
            text_color=col_caja_card,
        )
        if st.button("Abrir Caja Chica y Gastos Generales", key="btn_open_modulo_caja", use_container_width=True):
            st.session_state.modulo_caja_chica_abierto = True
            st.rerun()
    with cw4:
        render_metric_card(
            "4. Utilidades Ejecutadas + GG Cobrados",
            format_currency(tot_util_ejec_mas_gg),
            f"Util. Ejec.: {format_currency(util_ejecutadas)} · GG: {format_currency(gg_cobrados)}",
            border_color="#4A7C59",
            text_color="#4A7C59",
        )

    st.divider()

    if df_p_act.empty:
        st.info("No hay proyectos activos registrados.")
        return

    rows_fin = []
    chart_rows = []
    for _, pr in df_p_act.iterrows():
        p_name = pr['Nombre']
        ppto_p = safe_float(pr.get('Presupuesto', 0))
        util_p = safe_float(pr.get('Utilidades', 0))
        if util_p == 0.0 and ppto_p > 0:
            util_p = ppto_p * 0.20
        gg_ppto_p = safe_float(pr.get('GG_Presupuesto', 0))
        cob_p = pd.to_numeric(df_cob[df_cob['Proyecto'] == p_name]['Monto_Cobrado'], errors='coerce').sum() if not df_cob.empty and 'Proyecto' in df_cob.columns and 'Monto_Cobrado' in df_cob.columns else 0.0
        pag_p = pd.to_numeric(df_pag[df_pag['Proyecto'] == p_name]['Monto'], errors='coerce').sum() if not df_pag.empty and 'Proyecto' in df_pag.columns and 'Monto' in df_pag.columns else 0.0
        caja_p = pd.to_numeric(df_gg[df_gg['Proyecto'] == p_name]['Monto'], errors='coerce').sum() if not df_gg.empty and 'Proyecto' in df_gg.columns and 'Monto' in df_gg.columns else 0.0
        ffe_p = pd.to_numeric(df_mat[df_mat['Proyecto'] == p_name]['Costo_Real'], errors='coerce').sum() if not df_mat.empty and 'Proyecto' in df_mat.columns and 'Costo_Real' in df_mat.columns else 0.0
        egresos_p = pag_p + caja_p + ffe_p

        if not df_ing_act.empty:
            ing_p = df_ing_act[df_ing_act['Proyecto'] == p_name]
            u_ej_p = float(pd.to_numeric(ing_p['Monto'], errors='coerce').fillna(0.0).sum())
        else:
            u_ej_p = 0.0

        rows_fin.append({
            "Proyecto": p_name,
            "Cliente": safe_str(pr.get('Cliente', '')),
            "Total Contrato": format_currency(ppto_p),
            "Utilidades": format_currency(util_p),
            "Caja Chica (Ejec. / Ppto.)": f"{format_currency(caja_p)} / {format_currency(gg_ppto_p)}",
            "Util. Ejec. + GG Cobrados": format_currency(u_ej_p),
            "Cobrado Cliente": format_currency(cob_p),
            "Pagos Obra + FF&E": format_currency(egresos_p),
        })

        chart_rows.extend([
            {"Proyecto": p_name, "Categoría": "1. Total Contrato", "Monto": ppto_p},
            {"Proyecto": p_name, "Categoría": "2. Utilidades", "Monto": util_p},
            {"Proyecto": p_name, "Categoría": "3. Util. Ejecutadas + GG Cobrados", "Monto": u_ej_p},
        ])

    # Gráfico Comparativo por Proyecto
    if chart_rows:
        st.markdown("#### COMPARATIVA FINANCIERA POR PROYECTO")
        df_ch = pd.DataFrame(chart_rows)
        chart_fin = alt.Chart(df_ch).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X('Proyecto:N', title=None, axis=alt.Axis(labelAngle=0, labelColor='#262320', labelFontWeight='bold')),
            y=alt.Y('Monto:Q', title='Monto (S/)', axis=alt.Axis(gridColor='#DFD9CE', labelColor='#6E665E')),
            xOffset='Categoría:N',
            color=alt.Color(
                'Categoría:N',
                scale=alt.Scale(
                    domain=["1. Total Contrato", "2. Utilidades", "3. Util. Ejecutadas + GG Cobrados"],
                    range=['#262320', '#4A7C59', '#C85A32']
                ),
                legend=alt.Legend(title="Indicador Financiero", orient="top", labelColor='#262320', titleColor='#6E665E')
            ),
            tooltip=['Proyecto', 'Categoría', alt.Tooltip('Monto:Q', format=',.2f')]
        ).properties(height=280).configure_view(strokeOpacity=0)
        st.altair_chart(chart_fin, use_container_width=True)

    st.markdown("#### DETALLE FINANCIERO POR PROYECTO")
    if rows_fin:
        df_fin_disp = pd.DataFrame(rows_fin)
        st.dataframe(df_fin_disp, use_container_width=True, hide_index=True)

        csv_bytes = df_fin_disp.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 EXPORTAR REPORTE FINANCIERO A CSV",
            data=csv_bytes,
            file_name=f"finanzas_cota_{datetime.date.today().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )


def _render_tab_operativo_diario(lista_socios, fecha_hoy, conn, sheet_url, nube_ok):
    """Pestaña 4: Requerimientos diarios, obras activas hoy y próximos arranques."""
    co1, co2, co3 = st.columns([1.2, 1, 1])

    with co1:
        st.markdown("#### 📋 LOGÍSTICA DIARIA Y PENDIENTES")
        with st.popover("➕ NUEVO REQUERIMIENTO", use_container_width=True):
            with st.form("form_nuevo_todo", clear_on_submit=True):
                p_act = get_proyectos_activos(st.session_state.proyectos)['Nombre'].tolist()
                t_p = st.selectbox("Asignar a Proyecto", ["General"] + p_act)
                t_r = st.selectbox("Responsable", lista_socios)
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
