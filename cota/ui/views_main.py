"""
Vista Principal del Portafolio y Operaciones del Estudio:
Portafolio de Proyectos, Directorio de Contratistas, Finanzas Globales,
Control Operativo Diario, Calendario Técnico y Archivo Histórico.
Estética: Warm Architectural Atelier (#F7F4EF, #C85A32, #262320, #4A7C59, #D98A2B).
"""

import calendar
import datetime
import altair as alt
import pandas as pd
import streamlit as st

from cota.config import (
    ESPECIALIDADES_DEFAULT,
    STATUS_PROYECTOS,
    STATUS_TASKS,
    TIPOS_PROYECTO,
)
from cota.db import (
    COLS_MAESTRO,
    COLS_PROY,
    agregar_fase_banco,
    clear_base_dfs,
    get_proyectos_activos,
    get_proyectos_archivados,
    guardar_tabla,
    obtener_banco_fases,
    purgar_proyecto_cascada,
    renombrar_proyecto,
    sembrar_fases_default,
    sincronizar_fases_proyecto,
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

    exist_ubis = sorted(list(set([u for u in st.session_state.proyectos['Ubicación'].dropna().unique().tolist() if u])))
    if not exist_ubis:
        exist_ubis = ["Lima", "Miraflores", "San Isidro", "Barranco", "Surco", "La Molina"]

    # Tabs principales
    t_proy, t_con, t_fin, t_ope, t_cal, t_arc = st.tabs([
        "DISEÑO",
        "BASE CONTRATISTAS",
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

def _render_tab_portafolio(exist_divs, exist_ubis, lista_socios, fecha_hoy):
    """Portafolio de proyectos activos con KPIs ejecutivos filtrables por proyecto, carpetas y estados."""
    p_vis_all = get_proyectos_activos(st.session_state.proyectos)
    nombres_act = p_vis_all['Nombre'].tolist()

    # 1. Selector de Filtro por Proyecto para los Widgets de Resumen Ejecutivo
    OPCION_TODOS = "🌐 Todos los Proyectos Activos (Resumen Estudio)"
    opciones_filtro_proy = [OPCION_TODOS] + nombres_act

    col_f_kpi, col_f_action = st.columns([7, 3])
    with col_f_kpi:
        proy_kpi_sel = st.selectbox(
            "🎯 Filtrar Resumen Ejecutivo por Proyecto:",
            options=opciones_filtro_proy,
            index=0,
            key="filtro_kpi_proyecto"
        )
    es_proy_unico = (proy_kpi_sel != OPCION_TODOS) and (proy_kpi_sel in nombres_act)

    with col_f_action:
        if es_proy_unico:
            st.markdown("<div style='padding-top: 26px;'></div>", unsafe_allow_html=True)
            if st.button(f"📂 ABRIR {proy_kpi_sel.upper()} →", key="btn_open_kpi_proy", type="primary", use_container_width=True):
                st.session_state.proy_activo = proy_kpi_sel
                st.session_state.vista_actual = 'proyecto'
                clear_base_dfs()
                st.rerun()

    # Subconjunto de proyectos sobre el cual se calculan los KPIs
    p_kpi_df = p_vis_all[p_vis_all['Nombre'] == proy_kpi_sel].copy() if es_proy_unico else p_vis_all.copy()
    nombres_kpi = [proy_kpi_sel] if es_proy_unico else nombres_act

    # 1.A Cartera y Gastos
    n_activos = len(p_kpi_df)
    n_en_proc = len(p_kpi_df[p_kpi_df['Estado'].astype(str).str.contains('Proceso', case=False, na=False)])
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

    # 1.B Avance del Diseño (Fases)
    avances = []
    fases_ok_tot = 0
    fases_len_tot = 0
    fase_actual_kpi = "En curso"
    if 'fases' in st.session_state and not st.session_state.fases.empty:
        for p_n in nombres_kpi:
            fp = st.session_state.fases[st.session_state.fases['Proyecto'] == p_n].sort_values(by='Orden')
            if not fp.empty:
                mask_ok = fp['Aprobado_Cliente'].apply(to_bool) | (fp['Estado'].astype(str).str.contains('Aprobada', case=False, na=False))
                ok_c = int(mask_ok.sum())
                fases_ok_tot += ok_c
                fases_len_tot += len(fp)
                avances.append(ok_c / len(fp) * 100.0)
                if es_proy_unico:
                    pend_fp = fp[~mask_ok]
                    fase_actual_kpi = pend_fp.iloc[0]['Fase'] if not pend_fp.empty else "08. Cierre & Entrega Final"
    prom_avance = sum(avances) / len(avances) if avances else 0.0

    # 1.C FF&E (Por aprobar / Presupuesto FF&E)
    ffe_propuestos = 0
    ffe_total_items = 0
    monto_ffe_pend = 0.0
    monto_ffe_total = 0.0
    if 'materiales' in st.session_state and not st.session_state.materiales.empty and 'Proyecto' in st.session_state.materiales.columns:
        df_m_act = st.session_state.materiales[st.session_state.materiales['Proyecto'].isin(nombres_kpi)].copy()
        ffe_total_items = len(df_m_act)
        if not df_m_act.empty:
            df_m_act['Costo_Estimado'] = pd.to_numeric(df_m_act.get('Costo_Estimado', 0), errors='coerce').fillna(0.0)
            monto_ffe_total = float(df_m_act['Costo_Estimado'].sum())
            if 'Estado' in df_m_act.columns:
                mask_ffe_pend = df_m_act['Estado'].astype(str).str.contains('Propuesto|Cotizado', case=False, na=False)
                ffe_propuestos = int(mask_ffe_pend.sum())
                monto_ffe_pend = float(df_m_act.loc[mask_ffe_pend, 'Costo_Estimado'].sum())

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
            "subtitle": f"{n_en_proc} en ejecución actual",
        }

    sub_cartera = (
        f"Ejecutado: {format_currency(tot_ejecutado)}"
        if tot_ejecutado > 0
        else "Presupuesto total contratado"
    )
    sub_avance = (
        f"{fases_ok_tot}/{fases_len_tot} fases · {fase_actual_kpi}"
        if es_proy_unico and fases_len_tot > 0
        else f"{fases_ok_tot}/{fases_len_tot} fases aprobadas" if fases_len_tot > 0 else "Promedio de fases aprobadas"
    )
    col_ffe = "#D98A2B" if ffe_propuestos > 0 else "#4A7C59"
    val_ffe = format_currency(monto_ffe_pend) if monto_ffe_pend > 0 else f"{ffe_propuestos} ítems"
    sub_ffe = f"{ffe_propuestos}/{ffe_total_items} por aprobar · Total: {format_currency(monto_ffe_total)}"

    col_cob = "#C85A32" if (cobros_pend > 0 or saldo_hitos_cobrar > 0) else "#4A7C59"
    val_cob = format_currency(saldo_hitos_cobrar) if monto_pactado_cobros > 0 else str(cobros_pend)
    sub_cob = f"{cobros_pend}/{cobros_tot_items} hitos pend. · Cobrado: {format_currency(monto_cobrado_cobros)}"

    render_metric_row([
        card_1,
        {"title": "Resumen Cartera", "value": format_currency(tot_cartera), "subtitle": sub_cartera},
        {"title": "Avance Diseño", "value": f"{prom_avance:.0f}%", "subtitle": sub_avance, "border_color": "#4A7C59", "text_color": "#4A7C59"},
        {"title": "FF&E por Aprobar", "value": val_ffe, "subtitle": sub_ffe, "border_color": col_ffe, "text_color": col_ffe},
        {"title": "Hitos por Cobrar", "value": val_cob, "subtitle": sub_cob, "border_color": col_cob, "text_color": col_cob},
    ])

    # Detalle rápido desplegable cuando se filtra un proyecto específico
    if es_proy_unico:
        with st.expander(f"📋 Ver detalle de Hitos de Cobro y FF&E de '{proy_kpi_sel}'", expanded=False):
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
                st.markdown("##### 🛋️ Especificaciones FF&E del Proyecto")
                df_m_det = st.session_state.materiales[st.session_state.materiales['Proyecto'] == proy_kpi_sel] if 'materiales' in st.session_state else pd.DataFrame()
                if not df_m_det.empty:
                    st.dataframe(
                        df_m_det[['Ambiente', 'Material', 'Costo_Estimado', 'Estado']],
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.caption("Sin elementos FF&E registrados para este proyecto.")

    st.divider()

    # 2. Barra de herramientas: Nuevo Proyecto + Buscador (alineados simétricamente)
    col_new, col_search = st.columns([3, 7])
    banco_fases_estudio = obtener_banco_fases()
    nombres_banco_all = [f["Fase"] for f in banco_fases_estudio]
    nombres_banco_def = [f["Fase"] for f in banco_fases_estudio if f.get("Por_Defecto", True)]

    with col_new:
        with st.popover("➕ NUEVO PROYECTO DE DISEÑO", use_container_width=True):
            with st.form("form_nuevo_proy", clear_on_submit=True):
                pn = st.text_input("Nombre / Código del Proyecto (Único)", placeholder="ej. Casa Las Casuarinas").strip()
                sel_div = st.selectbox("Carpeta / Cliente", exist_divs + ["+ Crear Nueva Carpeta"])
                p_div = st.text_input("Nombre de Nueva Carpeta") if sel_div == "+ Crear Nueva Carpeta" else sel_div
                sel_ubi = st.selectbox("Ubicación", exist_ubis + ["+ Agregar Ubicación"])
                p_ubi = st.text_input("Nueva Ubicación") if sel_ubi == "+ Agregar Ubicación" else sel_ubi
                pe = st.selectbox("Líder de Proyecto", lista_socios)
                ps = st.selectbox("Estado Inicial", STATUS_PROYECTOS)
                p_tipo = st.selectbox("Tipo de Proyecto", TIPOS_PROYECTO)
                p_cliente = st.text_input("Nombre del Cliente", placeholder="ej. Familia Gómez")
                p_color = st.color_picker("Color Identificador", value="#C85A32")

                st.markdown("##### Fases Activas del Proyecto (Banco de Fases)")
                fases_sel_nuevo = st.multiselect(
                    "Selecciona las fases que aplican a este proyecto:",
                    options=nombres_banco_all,
                    default=nombres_banco_def,
                )

                st.markdown("##### Presupuestos Iniciales (Opcional)")
                col_m1, col_m2 = st.columns(2)
                p_presupuesto = col_m1.number_input("Ppto Total Venta (S/)", value=0.0)
                p_util = col_m2.number_input("Utilidades Proyectadas (S/)", value=0.0, help="Si se deja en 0, se calcula el 20% del contrato por defecto.")
                col_m3, col_m4 = st.columns(2)
                p_hon = col_m3.number_input("Honorarios Diseño (S/)", value=0.0)
                p_ffe = col_m4.number_input("Ppto FF&E / Muebles (S/)", value=0.0)
                p_gg = st.number_input("Ppto Caja Chica (S/)", value=0.0)

                if st.form_submit_button("CREAR PROYECTO", type="primary", use_container_width=True):
                    if not pn:
                        st.error("El nombre del proyecto es obligatorio.")
                    elif pn in st.session_state.proyectos['Nombre'].tolist():
                        st.error(f"Ya existe un proyecto con el nombre '{pn}'. Elige un nombre único.")
                    else:
                        util_final = p_util if p_util > 0 else (p_presupuesto * 0.20)
                        n_p = pd.DataFrame([{
                            'Nombre': pn,
                            'Encargado': pe,
                            'Ubicación': p_ubi,
                            'Estado': ps,
                            'Inicio': fecha_hoy.strftime('%Y-%m-%d'),
                            'Fin': (fecha_hoy + datetime.timedelta(days=90)).strftime('%Y-%m-%d'),
                            'Color': p_color,
                            'Presupuesto': p_presupuesto,
                            'Utilidades': util_final,
                            'GG_Presupuesto': p_gg,
                            'Archivado': False,
                            'Metodologia': 'Diseño Interior',
                            'Division': p_div,
                            'Tipo_Proyecto': p_tipo,
                            'Num_Pisos': 0,
                            'Num_Sotanos': 0,
                            'Presupuesto_FFE': p_ffe,
                            'Honorarios_Diseno': p_hon,
                            'Cliente': p_cliente
                        }])
                        st.session_state.proyectos = pd.concat([st.session_state.proyectos, n_p[COLS_PROY]], ignore_index=True)

                        # Sembrar fases seleccionadas del Banco de Fases
                        fases_a_sembrar = fases_sel_nuevo if fases_sel_nuevo else nombres_banco_def
                        nuevas_fases = sembrar_fases_default(pn, fecha_hoy, fases_seleccionadas=fases_a_sembrar)
                        if 'fases' not in st.session_state or st.session_state.fases.empty:
                            st.session_state.fases = nuevas_fases
                        else:
                            st.session_state.fases = pd.concat([st.session_state.fases, nuevas_fases], ignore_index=True)

                        clear_base_dfs()
                        st.success(f"Proyecto '{pn}' creado exitosamente con {len(fases_a_sembrar)} fase(s) activa(s).")
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
                st.markdown(
                    f"<h4 class='cota-status-header' style='color: {col_st} !important;'>"
                    f"<span class='cota-status-header-bar' style='background-color: {col_st};'></span>"
                    f"ESTADO: {est.upper()} ({len(p_est)})"
                    f"</h4>",
                    unsafe_allow_html=True
                )

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

                    cli_val = safe_str(proy.get('Cliente', ''))
                    cli_str = f" · Cliente: {cli_val}" if cli_val else ""
                    div_val = safe_str(proy.get('Division', 'General'))
                    tipo_val = safe_str(proy.get('Tipo_Proyecto', 'Diseño'))
                    tit_expander = f"🏛️ {p_nom.upper()}{cli_str}  |  📁 {div_val} · {tipo_val}  |  Líder: {proy.get('Encargado', 'N/A')}  |  Avance: {pct_avance}%"

                    with st.expander(tit_expander, expanded=es_proy_unico):
                        ppto_p = safe_float(proy.get('Presupuesto', 0))
                        hon_p = safe_float(proy.get('Honorarios_Diseno', 0))
                        ffe_p = safe_float(proy.get('Presupuesto_FFE', 0))
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
                            f"<div><span style='color:#6E665E; font-size:11px; text-transform:uppercase;'>Honorarios / FF&E</span><br><b style='color:#4A7C59; font-family:monospace;'>{format_currency(hon_p)} / {format_currency(ffe_p)}</b></div>"
                            f"</div>"
                            f"<div style='margin-top: 10px; background: #EFECE6; border-radius: 4px; height: 6px; overflow: hidden;'>"
                            f"<div style='background: {col_st}; width: {pct_avance}%; height: 100%;'></div>"
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
                                    n_ubi = st.selectbox("Ubicación", exist_ubis, index=exist_ubis.index(proy.get('Ubicación', 'Lima')) if proy.get('Ubicación', 'Lima') in exist_ubis else 0)
                                    n_est = st.selectbox("Estado", STATUS_PROYECTOS, index=STATUS_PROYECTOS.index(proy.get('Estado')) if proy.get('Estado') in STATUS_PROYECTOS else 0)
                                    n_tipo = st.selectbox("Tipo", TIPOS_PROYECTO, index=TIPOS_PROYECTO.index(proy.get('Tipo_Proyecto')) if proy.get('Tipo_Proyecto') in TIPOS_PROYECTO else 0)
                                    col_d1, col_d2 = st.columns(2)
                                    d_i = col_d1.date_input("Inicio", value=parse_date(proy.get('Inicio')) or fecha_hoy)
                                    d_f = col_d2.date_input("Fin", value=parse_date(proy.get('Fin')) or fecha_hoy)
                                    v_p = st.number_input("Ppto Total (S/)", value=safe_float(proy.get('Presupuesto', 0)))
                                    v_util = st.number_input("Utilidades Proyectadas (S/)", value=safe_float(proy.get('Utilidades', 0)))
                                    v_hon = st.number_input("Honorarios Diseño (S/)", value=safe_float(proy.get('Honorarios_Diseno', 0)))
                                    v_ffe = st.number_input("Ppto FF&E (S/)", value=safe_float(proy.get('Presupuesto_FFE', 0)))
                                    v_gg = st.number_input("Ppto Caja Chica (S/)", value=safe_float(proy.get('GG_Presupuesto', 0)))

                                    if st.form_submit_button("ACTUALIZAR DATOS"):
                                        if n_nom != p_nom:
                                            renombrar_proyecto(p_nom, n_nom)

                                        st.session_state.proyectos.at[idx_p, 'Nombre'] = n_nom
                                        st.session_state.proyectos.at[idx_p, 'Cliente'] = n_cli
                                        st.session_state.proyectos.at[idx_p, 'Division'] = n_div
                                        st.session_state.proyectos.at[idx_p, 'Ubicación'] = n_ubi
                                        st.session_state.proyectos.at[idx_p, 'Estado'] = n_est
                                        st.session_state.proyectos.at[idx_p, 'Tipo_Proyecto'] = n_tipo
                                        st.session_state.proyectos.at[idx_p, 'Inicio'] = d_i.strftime('%Y-%m-%d')
                                        st.session_state.proyectos.at[idx_p, 'Fin'] = d_f.strftime('%Y-%m-%d')
                                        st.session_state.proyectos.at[idx_p, 'Presupuesto'] = v_p
                                        st.session_state.proyectos.at[idx_p, 'Utilidades'] = v_util
                                        st.session_state.proyectos.at[idx_p, 'Honorarios_Diseno'] = v_hon
                                        st.session_state.proyectos.at[idx_p, 'Presupuesto_FFE'] = v_ffe
                                        st.session_state.proyectos.at[idx_p, 'GG_Presupuesto'] = v_gg
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
                            with st.popover("📝 BRIEF / NOTAS", use_container_width=True):
                                with st.form(f"f_notes_m_{ukey}"):
                                    c_notas = st.text_area("Notas / Brief del Cliente", value=safe_str(proy.get('Notas', '')), height=140)
                                    if st.form_submit_button("GUARDAR BRIEF"):
                                        st.session_state.proyectos.at[idx_p, 'Notas'] = c_notas
                                        st.success("Notas guardadas.")
                                        st.rerun()

                        with c_btn4:
                            if st.button("📦 ARCHIVAR", key=f"arch_{ukey}", use_container_width=True):
                                st.session_state.proyectos.at[idx_p, 'Archivado'] = True
                                clear_base_dfs()
                                st.rerun()


def _render_tab_contratistas(fecha_hoy, df_hoy):
    """Directorio de contratistas, proveedores y especialistas con rating y disponibilidad en tiempo real."""
    c_tit, c_add = st.columns([7, 3])
    with c_tit:
        st.markdown("### 🛠️ DIRECTORIO DE CONTRATISTAS, PROVEEDORES Y ESPECIALISTAS")
        st.caption("Evaluación histórica de desempeño, carga de trabajo actual y bitácora de obra.")
    with c_add:
        with st.popover("➕ REGISTRAR CONTRATISTA", use_container_width=True):
            with st.form("form_nuevo_contratista", clear_on_submit=True):
                nc_nom = st.text_input("Nombre / Empresa Especialista", placeholder="ej. Carpintería Hnos. Silva").strip()
                nc_esp = st.selectbox("Especialidad Principal", ESPECIALIDADES_DEFAULT + ["Mobiliario a Medida", "Mármol y Piedra", "Drywall y Pintura", "Instalaciones Eléctricas", "Sanitarias / Gasfitería", "Vidrios y Espejos", "Tapicería y Cortinas", "Otro"])
                nc_ubi = st.text_input("Distrito / Ubicación Base", value="Lima")
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
