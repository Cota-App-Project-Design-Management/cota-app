"""
Vista detallada de Proyecto (Fullscreen):
Resumen, Fases de Diseño, Presupuesto All-in-One, Entregables y Planos,
Ejecución de Obra, Cobros y Finanzas, Reuniones y Actas, y Punch List de Entrega.
"""

import datetime
import html as html_lib
import json
import re
import uuid
import altair as alt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from cota.config import (
    AMBIENTES_DEFAULT,
    ESPECIALIDADES_DEFAULT,
    ETAPAS_DISENO,
    PRIORIDADES_PUNCH,
    STATUS_COBROS,
    STATUS_FASES,
    STATUS_PROYECTOS,
    STATUS_PUNCH,
    STATUS_TASKS,
    TIPOS_COBRO,
    TIPOS_ENTREGABLE_DISENO,
    TIPOS_REUNION,
    UNIDADES_MEDIDA,
)
from cota.db import (
    COLS_COBROS,
    COLS_ENTREGABLES,
    COLS_FASES,
    COLS_PAGOS,
    COLS_PUNCH,
    agregar_pendiente_operativo,
    completar_pendiente_operativo,
    obtener_pendientes_operativos,
    COLS_TASKS,
    _normalizar_estado_diseno,
    _normalizar_supervisado,
    agregar_fase_banco,
    agregar_nota_chat_proyecto,
    clear_base_dfs,
    eliminar_nota_chat_proyecto,
    obtener_banco_fases,
    obtener_catalogo_estudio,
    obtener_notas_chat_proyecto,
    on_table_edit,
    registrar_cambio_diseno,
    sanitizar_fases_estudio,
    sembrar_fases_default,
    sincronizar_fases_proyecto,
)
import importlib
import cota.cotizacion
import cota.pdf
try:
    if (
        not hasattr(cota.cotizacion, "deshacer_presupuesto")
        or not hasattr(cota.cotizacion, "mover_partida_presupuesto")
        or not hasattr(cota.cotizacion, "aplicar_edicion_inline_cuadro_pagos")
        or not hasattr(cota.cotizacion, "agregar_partida_presupuesto")
        or not hasattr(cota.cotizacion, "eliminar_partida_presupuesto")
        or not hasattr(cota.cotizacion, "mover_tareas_seleccionadas_presupuesto")
        or not hasattr(cota.cotizacion, "eliminar_tareas_seleccionadas_presupuesto")
        or not hasattr(cota.cotizacion, "exportar_presupuesto_pdf")
        or not hasattr(cota.cotizacion, "resumen_contratistas_semana")
        or not hasattr(cota.cotizacion, "registrar_pago_en_fila_dict")
        or not hasattr(cota.cotizacion, "obtener_utilidades_gestion_pagadas_proyecto")
        or not hasattr(cota.cotizacion, "agregar_tarea_presupuesto")
        or not hasattr(cota.cotizacion, "obtener_notas_presupuesto_proyecto")
        or not hasattr(cota.cotizacion, "obtener_planificacion_presupuesto_proyecto")
    ):
        importlib.reload(cota.cotizacion)
    if not hasattr(cota.pdf, "generar_pdf_minuta"):
        importlib.reload(cota.pdf)
except Exception:
    pass
from cota.cotizacion import (
    agregar_partida_presupuesto,
    agregar_tarea_presupuesto,
    agregar_nota_presupuesto_proyecto,
    eliminar_nota_presupuesto_proyecto,
    eliminar_nota_predeterminada_presupuesto,
    guardar_nota_predeterminada_presupuesto,
    guardar_notas_presupuesto_proyecto,
    obtener_notas_predeterminadas_presupuesto,
    obtener_notas_presupuesto_proyecto,
    aplicar_cotizacion_planificada_a_presupuesto,
    guardar_estado_diseno_proyecto,
    guardar_planificacion_presupuesto_proyecto,
    obtener_estado_diseno_proyecto,
    obtener_planificacion_presupuesto_proyecto,
    resumen_planificacion_presupuesto,
    ajustar_cantidad_partidas_proyecto,
    ajustar_cantidad_tareas_partida,
    aplicar_cotizacion_a_proyecto,
    aplicar_edicion_inline_cuadro_pagos,
    aplicar_edicion_tabla_presupuesto_partida,
    asegurar_estructura_presupuesto_proyecto,
    calcular_resumen_cuadro_pagos_semanales,
    deshacer_presupuesto,
    eliminar_partida_presupuesto,
    eliminar_tareas_seleccionadas_presupuesto,
    establecer_estado_sincronizacion_presupuesto,
    etiqueta_corta_columna_pago,
    etiqueta_export_columna_pago,
    exportar_cuadro_pagos_semanales_excel,
    exportar_cuadro_pagos_semanales_pdf,
    exportar_presupuesto_pdf,
    exportar_proyecto_a_formato_venti,
    extraer_descripcion_tarea,
    generar_plantilla_cotizacion_venti,
    guardar_cuadro_pagos_semanales_proyecto,
    guardar_parametros_presupuesto_proyecto,
    guardar_valor_contrato_proyecto,
    integrar_presupuesto_con_gestion,
    guardar_snapshot_presupuesto,
    limpiar_nombre_partida,
    mover_partida_presupuesto,
    mover_tarea_presupuesto,
    mover_tareas_seleccionadas_presupuesto,
    obtener_columnas_pago_semanal,
    obtener_cuadro_pagos_semanales_proyecto,
    obtener_estado_sincronizacion_presupuesto,
    obtener_items_presupuesto_proyecto,
    obtener_pagado_por_partida_proyecto,
    obtener_parametros_presupuesto_proyecto,
    parsear_cotizacion_venti,
    parsear_cuadro_pagos_semanales,
    parsear_presupuesto_flexible,
    puede_deshacer_presupuesto,
    puede_rehacer_presupuesto,
    recalcular_totales_presupuesto_proyecto,
    redondear_arriba_10,
    redondear_arriba_100,
    rehacer_presupuesto,
    renombrar_partida_presupuesto,
    TIPOS_PAGO_CUADRO,
    _extraer_contratista_de_notas,
    obtener_contratistas_disponibles_proyecto,
    obtener_pagos_semana,
    obtener_utilidades_gestion_pagadas_proyecto,
    registrar_pago_en_fila_dict,
    reordenar_tareas_partida_por_indices,
)
from cota.pdf import generar_pdf_minuta
import cota.ui.cuadro_pagos
try:
    if not hasattr(cota.ui.cuadro_pagos, "build_pagos_floating_ui_js"):
        importlib.reload(cota.ui.cuadro_pagos)
except Exception:
    pass
from cota.ui.cuadro_pagos import (
    build_cell_payments_badge_and_tooltip,
    build_pagos_floating_ui_js,
    render_pagos_realizados_por_semana_panel,
    resolver_semana_activa_cuadro,
)
import cota.ui.components
try:
    if (
        not hasattr(cota.ui.components, "render_chat_notas_proyecto")
        or not hasattr(cota.ui.components, "render_alertas_cruce_contratistas")
    ):
        importlib.reload(cota.ui.components)
except Exception:
    pass
from cota.ui.components import render_alertas_cruce_contratistas, render_alertas_cruce_partida, render_chat_notas_proyecto, render_editor_valor_contrato, render_metric_card
from cota.utils import (
    analizar_tareas_proyecto,
    extraer_esp,
    extraer_texto_documento,
    format_currency,
    format_date,
    get_image_base64,
    parse_date,
    parse_resumen_meet,
    safe_float,
    safe_str,
    sugerir_contratista,
    to_bool,
)


def render_proyecto_view(proy_name):
    """Renderiza la vista completa de un proyecto seleccionado."""
    # Obtener datos del proyecto
    df_p = st.session_state.proyectos
    proy_matches = df_p[df_p['Nombre'] == proy_name]
    if proy_matches.empty:
        st.error(f"El proyecto '{proy_name}' no fue encontrado.")
        if st.button("⬅ Volver a Portafolio"):
            st.session_state.vista_actual = 'main'
            st.rerun()
        return

    proy_data = proy_matches.iloc[0]
    p_color = proy_data.get('Color', '#C85A32')
    if pd.isna(p_color) or not str(p_color).startswith('#') or str(p_color).upper() == '#00E5FF':
        p_color = '#C85A32'

    # Barra superior de navegación del proyecto
    col_back, col_title, col_stat = st.columns([1.6, 6, 2.4])
    with col_back:
        if st.button("⬅ PORTAFOLIO", use_container_width=True):
            st.session_state.vista_actual = 'main'
            st.session_state.proy_activo = None
            clear_base_dfs()
            st.rerun()

    with col_title:
        tipo_p = proy_data.get('Tipo_Proyecto', 'Diseño')
        cliente_p = proy_data.get('Cliente', '')
        cliente_txt = f"  //  CLIENTE: {cliente_p.upper()}" if cliente_p else ""
        st.markdown(
            f"<h3 style='color: {p_color} !important; margin: 0; font-size: 20px;'>"
            f"PROYECTO: {str(proy_name).upper()} <span style='font-size: 13px; color: #6E665E; font-weight: 500;'>({tipo_p}){cliente_txt}</span></h3>",
            unsafe_allow_html=True
        )

    with col_stat:
        est_curr = proy_data.get('Estado', '🟡 Planificación')
        st.markdown(
            f"<div style='text-align: right; font-family: monospace; font-weight: 600; font-size: 13px; padding-top: 6px; color: #262320;'>"
            f"ESTADO: {est_curr}</div>",
            unsafe_allow_html=True
        )

    st.divider()

    # Asegurar inicialización y sanitización de fases para este proyecto
    sanitizar_fases_estudio()
    if 'fases' not in st.session_state or st.session_state.fases.empty:
        st.session_state.fases = sembrar_fases_default(proy_name)
    else:
        fases_p = st.session_state.fases[st.session_state.fases['Proyecto'] == proy_name]
        if fases_p.empty:
            nuevas_f = sembrar_fases_default(proy_name)
            st.session_state.fases = pd.concat([st.session_state.fases, nuevas_f], ignore_index=True)

    # Tabs especializadas del proyecto
    t_resumen, t_diseno, t_presupuesto, t_obra, t_finanzas, t_actas, t_observaciones = st.tabs([
        "01. RESUMEN",
        "02. PLANIFICACIÓN",
        "03. PRESUPUESTO",
        "05. PARTIDAS Y TAREAS",
        "06. COBROS & FINANZAS",
        "07. REUNIONES & ACTAS",
        "08. OBSERVACIONES"
    ])

    with t_resumen:
        _render_tab_resumen(proy_name, proy_data)

    with t_diseno:
        _render_tab_fases(proy_name, proy_data)

    with t_presupuesto:
        _render_tab_presupuesto(proy_name, proy_data)

    with t_obra:
        _render_tab_obra(proy_name, proy_data)

    with t_finanzas:
        _render_tab_finanzas(proy_name, proy_data)

    with t_actas:
        _render_tab_actas(proy_name, proy_data)

    with t_observaciones:
        _render_tab_punch(proy_name, proy_data)


# ====================================================
# SUB-RENDERERS PARA CADA PESTAÑA
# ====================================================

def _render_tab_resumen(proy_name, proy_data):
    """Pestaña 1: Resumen ejecutivo y métricas globales del proyecto."""
    ppto_venta = safe_float(proy_data.get('Presupuesto', 0.0))
    hon_diseno = safe_float(proy_data.get('Honorarios_Diseno', 0.0))
    util_proy = safe_float(proy_data.get('Utilidades', 0.0))
    gg_ppto = safe_float(proy_data.get('GG_Presupuesto', 0.0))

    # Pagos a contratistas (incluye pagos del Cuadro de Pagos Semanales y pagos manuales por partida)
    pagados_por_part_res = obtener_pagado_por_partida_proyecto(proy_name)
    if pagados_por_part_res:
        total_pagado_maestros = float(sum(pagados_por_part_res.values()))
    else:
        df_pagos_p = st.session_state.pagos[st.session_state.pagos['Proyecto'] == proy_name]
        total_pagado_maestros = pd.to_numeric(df_pagos_p['Monto'], errors='coerce').sum() if not df_pagos_p.empty else 0.0

    # Costo directo pactado en partidas
    df_pinfo_p = st.session_state.p_info[st.session_state.p_info['Proyecto'] == proy_name] if 'p_info' in st.session_state else pd.DataFrame()
    total_casco_pactado = pd.to_numeric(df_pinfo_p['Monto_Pactado'], errors='coerce').sum() if not df_pinfo_p.empty else 0.0

    # Caja chica gastada
    df_gg_p = st.session_state.gg_log[st.session_state.gg_log['Proyecto'] == proy_name]
    caja_gastada = pd.to_numeric(df_gg_p['Monto'], errors='coerce').sum() if not df_gg_p.empty else 0.0
    caja_restante = gg_ppto - caja_gastada

    # Cobros al cliente
    df_cobros_p = st.session_state.cobros[st.session_state.cobros['Proyecto'] == proy_name] if 'cobros' in st.session_state else pd.DataFrame()
    total_cobrado_cliente = pd.to_numeric(df_cobros_p['Monto_Cobrado'], errors='coerce').sum() if not df_cobros_p.empty else 0.0

    # Avance en etapas de diseño
    fases_p = st.session_state.fases[st.session_state.fases['Proyecto'] == proy_name].sort_values(by='Orden')
    n_fases = len(fases_p)
    n_fases_ok = len(fases_p[fases_p['Aprobado_Cliente'].apply(to_bool) | (fases_p['Estado'].astype(str).str.contains('Aprob', case=False))])
    pct_fases = (n_fases_ok / n_fases * 100) if n_fases > 0 else 0.0

    # Analizar tareas operativas
    info_t = analizar_tareas_proyecto(st.session_state.get('tasks'), proy_name)
    pct_tareas = (info_t['completadas'] / info_t['total'] * 100) if info_t['total'] > 0 else 0.0

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        render_metric_card("Ppto. Total", format_currency(ppto_venta), f"Casco: {format_currency(total_casco_pactado)}")
    with c2:
        render_metric_card("Cobrado a Cliente", format_currency(total_cobrado_cliente), f"Saldo: {format_currency(max(0.0, ppto_venta - total_cobrado_cliente))}", border_color="#4A7C59", text_color="#4A7C59")
    with c3:
        render_metric_card("Pagos Contratistas", format_currency(total_pagado_maestros), "Ejecución de obra")
    with c4:
        util_ges_recibida = obtener_utilidades_gestion_pagadas_proyecto(proy_name)
        sub_util_res = f"Recibido: {format_currency(util_ges_recibida)} · Hon.: {format_currency(hon_diseno)}" if util_ges_recibida > 0 else f"Honorarios: {format_currency(hon_diseno)}"
        render_metric_card("Utilidades / Superv.", format_currency(util_proy), sub_util_res, border_color="#4A7C59", text_color="#4A7C59")
    with c5:
        col_caja = "#4A7C59" if caja_restante >= 0 else "#C93B2B"
        render_metric_card("Caja Chica Saldo", format_currency(caja_restante), f"Gastado: {format_currency(caja_gastada)}", border_color=col_caja, text_color=col_caja)
    with c6:
        render_metric_card("Avance de Tareas", f"{pct_tareas:.0f}%", f"{info_t['completadas']} de {info_t['total']} tareas completadas", border_color="#C85A32", text_color="#C85A32")

    st.divider()

    # Datos descriptivos, widget inteligente de tareas y estado de fases activas
    banco_fases_estudio = obtener_banco_fases()
    nombres_banco_all = [f["Fase"] for f in banco_fases_estudio]
    fases_activas_actuales = fases_p['Fase'].tolist() if not fases_p.empty else []

    col_d1, col_d2 = st.columns([1, 1.1])
    with col_d1:
        st.markdown("#### FICHA TÉCNICA DEL PROYECTO")
        c_ft_est, c_ft_ctr = st.columns(2)
        with c_ft_est:
            est_actual_res = safe_str(proy_data.get('Estado', STATUS_PROYECTOS[0])) or STATUS_PROYECTOS[0]
            if est_actual_res not in STATUS_PROYECTOS:
                est_actual_res = STATUS_PROYECTOS[0]
            k_est_res = f"sel_estado_proy_resumen_{proy_name}"
            if k_est_res not in st.session_state or st.session_state[k_est_res] != est_actual_res:
                st.session_state[k_est_res] = est_actual_res

            def _on_change_est_proy_res():
                nuevo_est_r = st.session_state.get(k_est_res, STATUS_PROYECTOS[0])
                m_ep_r = st.session_state.proyectos['Nombre'] == proy_name
                if m_ep_r.any():
                    st.session_state.proyectos.loc[m_ep_r, 'Estado'] = nuevo_est_r
                    clear_base_dfs()

            st.selectbox(
                "📌 Estado del Proyecto",
                options=STATUS_PROYECTOS,
                key=k_est_res,
                on_change=_on_change_est_proy_res,
            )
        with c_ft_ctr:
            render_editor_valor_contrato(
                proy_name,
                key_prefix="ft",
                other_prefix="sb",
                show_summary_box=False,
            )
        drive_link_val = safe_str(proy_data.get('Link_Drive', '')).strip()
        info_items = [
            ("Valor del Contrato", format_currency(ppto_venta)),
            ("Estado del Proyecto", safe_str(proy_data.get('Estado', STATUS_PROYECTOS[0])) or STATUS_PROYECTOS[0]),
            ("Líder de Diseño", proy_data.get('Encargado', 'N/A')),
            ("Cliente", proy_data.get('Cliente', 'N/A')),
            ("Tipología", proy_data.get('Tipo_Proyecto', 'Diseño Interior')),
            ("Ubicación", proy_data.get('Ubicación', 'N/A')),
            ("Carpeta / División", proy_data.get('Division', 'General')),
            ("Fecha Inicio", format_date(proy_data.get('Inicio'))),
            ("Fecha Estimada Entrega", format_date(proy_data.get('Fin'))),
            ("Tareas en Proceso", f"{info_t['en_proceso']} en proceso ({info_t['completadas']}/{info_t['total']} completadas)"),
            ("Presentación Drive", f"<a href='{drive_link_val}' target='_blank' style='color:#C85A32; font-weight:600;'>Abrir Drive ↗</a>" if drive_link_val else "Sin vincular"),
        ]
        rows_html = "".join(
            f"<div style='display:flex; justify-content:space-between; padding:8px 12px; border-bottom:1px solid #DFD9CE;'>"
            f"<span style='color:#6E665E; font-weight:500;'>{k}:</span>"
            f"<span style='color:#262320; font-weight:600;'>{v}</span></div>"
            for k, v in info_items
        )
        st.markdown(
            f"<div style='background:#FFFFFF; border:1px solid #DFD9CE; border-radius:10px; overflow:hidden; margin-bottom:14px;'>{rows_html}</div>",
            unsafe_allow_html=True
        )

        # Widget Inteligente de Tareas dentro del Resumen del Proyecto
        pills_html = "".join(
            f"<span style='background:#FFFFFF; border:1px solid #DFD9CE; border-radius:4px; padding:2px 8px; font-size:11px; color:#262320; font-weight:500;'>{pill}</span>"
            for pill in info_t.get("pills_extra", [])
        )
        pills_wrap = f"<div style='display:flex; flex-wrap:wrap; gap:6px; margin-top:6px;'>{pills_html}</div>" if pills_html else ""
        st.markdown(
            f"<div style='background:{info_t['widget_bg']}; border:1px solid #DFD9CE; border-left:4px solid {info_t['widget_color']}; border-radius:8px; padding:12px 14px; margin-bottom:14px;'>"
            f"<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;'>"
            f"<span style='font-size:11px; color:#6E665E; font-weight:700; text-transform:uppercase;'>⚡ MONITOR INTELIGENTE DE TAREAS</span>"
            f"<span style='font-family:monospace; font-size:10.5px; font-weight:700; color:{info_t['widget_color']}; background:#FFFFFF; border:1px solid {info_t['widget_color']}; border-radius:4px; padding:1px 7px;'>{info_t['widget_badge']}</span>"
            f"</div>"
            f"<div style='color:#262320; font-weight:700; font-size:13.5px;'>{info_t['widget_titulo']}</div>"
            f"<div style='color:#6E665E; font-size:12px; margin-top:2px;'>{info_t['widget_detalle']}</div>"
            f"{pills_wrap}"
            f"</div>",
            unsafe_allow_html=True
        )

        st.markdown("#### 💬 NOTAS")
        socios_disp = obtener_catalogo_estudio("socios") or ["Alvaro", "Socio 2", "Socio 3"]
        render_chat_notas_proyecto(proy_name, socios_disp, key_prefix="res")

    with col_d2:
        _render_panel_derecho_resumen(
            proy_name=proy_name,
            ppto_venta=ppto_venta,
            total_casco_pactado=total_casco_pactado,
            total_cobrado_cliente=total_cobrado_cliente,
            total_pagado_maestros=total_pagado_maestros,
            util_proy=util_proy,
            util_ges_recibida=util_ges_recibida,
            hon_diseno=hon_diseno,
            gg_ppto=gg_ppto,
            caja_gastada=caja_gastada,
            caja_restante=caja_restante,
            info_t=info_t,
            pct_tareas=pct_tareas,
            socios_disp=socios_disp,
        )
        return
        ch_f1, ch_f2 = st.columns([6.2, 3.8])
        with ch_f1:
            pass
        with ch_f2:
            with st.popover("Etapas", use_container_width=True):
                st.markdown("##### Activar / Desactivar Etapas de Diseño")
                st.caption("Selecciona del banco las etapas de diseño (Moodboard, Planos, 3D, Renders) que aplican a este proyecto.")
                with st.form(f"form_res_banco_fases_{proy_name}"):
                    opciones_res_f = list(dict.fromkeys(nombres_banco_all + fases_activas_actuales))
                    sel_res_f = st.multiselect(
                        "Etapas de diseño activas:",
                        options=opciones_res_f,
                        default=fases_activas_actuales,
                    )
                    nueva_f_res = st.text_input("➕ Nueva etapa de diseño (opcional):", placeholder="")
                    if st.form_submit_button("APLICAR ETAPAS DE DISEÑO", type="primary", use_container_width=True):
                        fases_aplicar = list(sel_res_f)
                        if nueva_f_res.strip():
                            nf = agregar_fase_banco(nueva_f_res.strip())
                            if nf["Fase"] not in fases_aplicar:
                                fases_aplicar.append(nf["Fase"])
                        sincronizar_fases_proyecto(proy_name, fases_aplicar)
                        st.success("Etapas de diseño actualizadas.")
                        st.rerun()

        if not fases_p.empty:
            fases_items = []
            for _, fr in fases_p.iterrows():
                est_f = _normalizar_estado_diseno(fr.get('Estado', '⚪ Pendiente'))
                aprob = to_bool(fr.get('Aprobado_Cliente', False)) or ('aprob' in est_f.lower())
                av_pct = int(safe_float(fr.get('Avance_Pct', 100 if aprob else 0)))
                cambios_n = int(safe_float(fr.get('Cambios_Realizados', 0)))
                ult_c_str = format_date(fr.get('Fecha_Ultimo_Cambio', ''))
                col_bar = "#4A7C59" if aprob else ("#C85A32" if av_pct > 0 else "#DFD9CE")
                badge_txt = "🟢 Aprobado" if aprob else est_f
                cambios_badge = (
                    f" · <span style='color:#C85A32; font-weight:700;'>🔄 {cambios_n} cambio(s){f' ({ult_c_str})' if ult_c_str else ''}</span>"
                    if cambios_n > 0
                    else ""
                )
                fases_items.append(
                    f"<div style='padding:7px 12px; border-bottom:1px solid #EFECE6;'>"
                    f"<div style='display:flex; justify-content:space-between; font-size:12.5px; margin-bottom:4px;'>"
                    f"<span style='color:#262320; font-weight:600;'>{fr.get('Fase', '')}</span>"
                    f"<span style='color:#6E665E; font-family:monospace; font-size:11.5px;'>{badge_txt} ({av_pct}%){cambios_badge}</span>"
                    f"</div>"
                    f"<div style='background:#EFECE6; border-radius:4px; height:5px; overflow:hidden;'>"
                    f"<div style='background:{col_bar}; width:{max(0, min(100, av_pct))}%; height:100%;'></div>"
                    f"</div></div>"
                )
            st.markdown(
                f"<div style='background:#FFFFFF; border:1px solid #DFD9CE; border-radius:10px; overflow:hidden;'>{''.join(fases_items)}</div>",
                unsafe_allow_html=True
            )
        else:
            pass


def _render_panel_derecho_resumen(
    proy_name: str,
    ppto_venta: float,
    total_casco_pactado: float,
    total_cobrado_cliente: float,
    total_pagado_maestros: float,
    util_proy: float,
    util_ges_recibida: float,
    hon_diseno: float,
    gg_ppto: float,
    caja_gastada: float,
    caja_restante: float,
    info_t: dict,
    pct_tareas: float,
    socios_disp: list[str],
):
    """Columna derecha de 01. RESUMEN: Resumen Económico, Estado de Tareas y Pendientes Diarios sincronizados con Control Operativo."""
    st.markdown("#### 💰 RESUMEN ECONÓMICO Y DE TAREAS")
    saldo_cobrar = max(0.0, ppto_venta - total_cobrado_cliente)
    pct_cobrado = min(100.0, max(0.0, (total_cobrado_cliente / ppto_venta * 100.0) if ppto_venta > 0 else 0.0))
    saldo_contratistas = total_casco_pactado - total_pagado_maestros
    col_caja_txt = "#4A7C59" if caja_restante >= 0 else "#C93B2B"
    col_saldo_con = "#262320" if saldo_contratistas >= 0 else "#C93B2B"

    df_t_proy = (
        st.session_state.tasks[st.session_state.tasks["Proyecto"] == proy_name]
        if "tasks" in st.session_state and isinstance(st.session_state.tasks, pd.DataFrame) and not st.session_state.tasks.empty
        else pd.DataFrame()
    )
    t_tot = int(info_t.get("total", 0))
    t_comp = int(info_t.get("completadas", 0))
    t_proc = int(info_t.get("en_proceso", 0))
    t_retr = 0
    if not df_t_proy.empty and "Estado" in df_t_proy.columns:
        t_retr = int(df_t_proy["Estado"].astype(str).str.contains(r"Retras|espera", case=False, na=False).sum())
    t_plan = max(0, t_tot - t_comp - t_proc - t_retr)
    retr_html = (
        f"<span style='color:#C93B2B;'>⚠️ Retraso/Espera: <b>{t_retr}</b></span>"
        if t_retr > 0
        else ""
    )

    eco_html = (
        "<div style='background:#FFFFFF; border:1px solid #DFD9CE; border-radius:10px; padding:12px 14px; margin-bottom:14px;'>"
        "  <div style='display:grid; grid-template-columns:1fr 1fr; gap:10px; font-size:12.5px; margin-bottom:10px;'>"
        "    <div style='background:#FAF8F5; border:1px solid #EFECE6; border-radius:8px; padding:8px 10px;'>"
        "      <div style='font-size:10.5px; color:#6E665E; text-transform:uppercase; font-weight:700;'>Cobranza Cliente</div>"
        f"      <div style='font-size:14px; font-weight:700; color:#4A7C59; font-family:monospace;'>{format_currency(total_cobrado_cliente)} <span style='font-size:11px; color:#6E665E; font-weight:500;'>({pct_cobrado:.0f}%)</span></div>"
        f"      <div style='font-size:11px; color:#6E665E;'>Por cobrar: {format_currency(saldo_cobrar)}</div>"
        "    </div>"
        "    <div style='background:#FAF8F5; border:1px solid #EFECE6; border-radius:8px; padding:8px 10px;'>"
        "      <div style='font-size:10.5px; color:#6E665E; text-transform:uppercase; font-weight:700;'>Pagos Contratistas</div>"
        f"      <div style='font-size:14px; font-weight:700; color:#262320; font-family:monospace;'>{format_currency(total_pagado_maestros)}</div>"
        f"      <div style='font-size:11px; color:{col_saldo_con};'>Saldo casco: {format_currency(saldo_contratistas)}</div>"
        "    </div>"
        "    <div style='background:#FAF8F5; border:1px solid #EFECE6; border-radius:8px; padding:8px 10px;'>"
        "      <div style='font-size:10.5px; color:#6E665E; text-transform:uppercase; font-weight:700;'>Utilidades / Gestión</div>"
        f"      <div style='font-size:14px; font-weight:700; color:#4A7C59; font-family:monospace;'>{format_currency(util_proy)}</div>"
        f"      <div style='font-size:11px; color:#6E665E;'>Recibido: {format_currency(util_ges_recibida)} · Hon.: {format_currency(hon_diseno)}</div>"
        "    </div>"
        "    <div style='background:#FAF8F5; border:1px solid #EFECE6; border-radius:8px; padding:8px 10px;'>"
        "      <div style='font-size:10.5px; color:#6E665E; text-transform:uppercase; font-weight:700;'>Caja Chica (GG)</div>"
        f"      <div style='font-size:14px; font-weight:700; color:{col_caja_txt}; font-family:monospace;'>{format_currency(caja_restante)}</div>"
        f"      <div style='font-size:11px; color:#6E665E;'>Gastado: {format_currency(caja_gastada)} de {format_currency(gg_ppto)}</div>"
        "    </div>"
        "  </div>"
        "  <div style='border-top:1px solid #EFECE6; padding-top:9px;'>"
        "    <div style='display:flex; justify-content:space-between; align-items:center; font-size:11.5px; margin-bottom:5px;'>"
        f"      <span style='font-weight:700; color:#262320;'>🔨 Tareas del Proyecto ({t_comp}/{t_tot} completadas)</span>"
        f"      <span style='font-family:monospace; font-weight:700; color:#C85A32;'>{pct_tareas:.0f}%</span>"
        "    </div>"
        "    <div style='background:#EFECE6; border-radius:4px; height:6px; overflow:hidden; margin-bottom:7px;'>"
        f"      <div style='background:#C85A32; width:{max(0.0, min(100.0, pct_tareas)):.1f}%; height:100%;'></div>"
        "    </div>"
        "    <div style='display:flex; flex-wrap:wrap; gap:10px; font-size:11.5px; color:#4A453E;'>"
        f"      <span>🔵 En proceso: <b>{t_proc}</b></span>"
        f"      <span>🟡 Planificadas: <b>{t_plan}</b></span>"
        f"      <span>✅ Listas: <b>{t_comp}</b></span>"
        f"      {retr_html}"
        "    </div>"
        "  </div>"
        "</div>"
    )
    st.markdown(eco_html, unsafe_allow_html=True)

    c_td_hdr, c_td_btn = st.columns([6.2, 3.8])
    with c_td_hdr:
        st.markdown("#### 📋 PENDIENTES DIARIOS")
        st.caption("Sincronizados con **Control Operativo** del estudio.")
    with c_td_btn:
        st.markdown("<div style='padding-top: 6px;'></div>", unsafe_allow_html=True)
        with st.popover("➕ NUEVO PENDIENTE", use_container_width=True):
            with st.form(f"form_res_new_todo_{proy_name}", clear_on_submit=True):
                idx_soc_def = socios_disp.index(st.session_state.get("socio_activo")) if st.session_state.get("socio_activo") in socios_disp else 0
                td_resp = st.selectbox("Responsable", socios_disp, index=idx_soc_def)
                td_cat = st.selectbox("Clasificación", ["Compras / FF&E", "Pagos", "Proveedores", "Coordinación Cliente", "Supervisión Obra"])
                td_txt = st.text_input("Detalle del Pendiente", placeholder="")
                if st.form_submit_button("AGREGAR PENDIENTE", type="primary", use_container_width=True) and td_txt and td_txt.strip():
                    agregar_pendiente_operativo(proy_name, td_cat, td_txt.strip(), td_resp)
                    st.rerun()

    df_todos_proy = obtener_pendientes_operativos(proy_name)
    if df_todos_proy.empty:
        st.info("No hay pendientes diarios activos para este proyecto. Los que agregues aquí o en Control Operativo aparecerán sincronizados.")
    else:
        for idx_td, r_td in df_todos_proy.iterrows():
            c_td_card, c_td_ok = st.columns([8.0, 2.0])
            cat_td = html_lib.escape(safe_str(r_td.get("Categoria", "Tarea")))
            tar_td = html_lib.escape(safe_str(r_td.get("Tarea", "")))
            resp_td = html_lib.escape(safe_str(r_td.get("Responsable", "")).upper())
            c_td_card.markdown(
                f"<div style='background:#FFFFFF; padding:8px 11px; border:1px solid #DFD9CE; border-left:3px solid #C85A32; border-radius:6px; margin-bottom:6px;'>"
                f"<b style='color:#6E665E; font-size:10.5px; text-transform:uppercase;'>[{cat_td}]</b> "
                f"<span style='color:#262320; font-size:12.5px; font-weight:500;'>{tar_td}</span><br>"
                f"<small style='color:#C85A32; font-family:monospace; font-weight:600;'>RESP: {resp_td}</small>"
                f"</div>",
                unsafe_allow_html=True,
            )
            if c_td_ok.button("✓ LISTO", key=f"res_todo_done_{proy_name}_{idx_td}_{r_td.get('ID', idx_td)}", use_container_width=True):
                completar_pendiente_operativo(idx_td)
                st.rerun()


def _contar_estados_diseno(fases_df: pd.DataFrame, df_ent_proy: pd.DataFrame) -> dict[str, dict[str, int]]:
    """Agrupa las etapas y entregables de diseño según su estado de avance y revisión."""
    resumen = {est: {"etapas": 0, "entregables": 0, "total": 0} for est in STATUS_FASES}
    if isinstance(fases_df, pd.DataFrame) and not fases_df.empty:
        for _, r_f in fases_df.iterrows():
            aprob_f = to_bool(r_f.get('Aprobado_Cliente', False)) or ('aprob' in str(r_f.get('Estado', '')).lower())
            est_eff = "🟢 Aprobado" if aprob_f else _normalizar_estado_diseno(r_f.get('Estado', '⚪ Pendiente'))
            if est_eff not in resumen:
                resumen[est_eff] = {"etapas": 0, "entregables": 0, "total": 0}
            resumen[est_eff]["etapas"] += 1
            resumen[est_eff]["total"] += 1
    if isinstance(df_ent_proy, pd.DataFrame) and not df_ent_proy.empty:
        for _, r_e in df_ent_proy.iterrows():
            est_e = _normalizar_estado_diseno(r_e.get('Estado', '⚪ Pendiente'))
            if est_e not in resumen:
                resumen[est_e] = {"etapas": 0, "entregables": 0, "total": 0}
            resumen[est_e]["entregables"] += 1
            resumen[est_e]["total"] += 1
    return resumen


def _render_tab_fases(proy_name, proy_data):
    """Pestaña 2: 02. PLANIFICACIÓN — Estado del Diseño con Checklist simple de Etapas + Planificación de Presupuesto y Comparativo de Cotizaciones por Partida."""
    st.markdown("### 🗂️ 02. PLANIFICACIÓN — DISEÑO Y COTIZACIONES DE PRESUPUESTO")
    st.caption(
        "Gestiona de forma simple el estado y checklist de etapas del diseño, y planifica las partidas del presupuesto "
        "comparando cotizaciones por contratista, monto total y estado (Entregado o Pendiente)."
    )

    # Preparar etapas de diseño del proyecto
    fases_df = st.session_state.fases[st.session_state.fases["Proyecto"] == proy_name].copy()
    for c_req in COLS_FASES:
        if c_req not in fases_df.columns:
            fases_df[c_req] = 0 if c_req in ("Orden", "Avance_Pct", "Cambios_Realizados") else (False if c_req == "Aprobado_Cliente" else "")
    fases_df["Estado"] = fases_df["Estado"].apply(_normalizar_estado_diseno)
    fases_df = fases_df.sort_values(by="Orden").reset_index(drop=True)
    fases_activas_actuales = fases_df["Fase"].tolist() if not fases_df.empty else []
    _ = _contar_estados_diseno(fases_df, pd.DataFrame())

    n_etapas_tot = len(fases_df)
    n_etapas_ok = int(
        (fases_df["Aprobado_Cliente"].apply(to_bool) | fases_df["Estado"].astype(str).str.contains("Aprob", case=False, na=False)).sum()
    ) if not fases_df.empty else 0
    pct_diseno = (n_etapas_ok / n_etapas_tot * 100.0) if n_etapas_tot > 0 else 0.0

    # ==========================================================
    # 1. SECCIÓN SIMPLE DE DISEÑO: ESTADO + CHECKLIST DE ETAPAS
    # ==========================================================
    with st.container(border=True):
        c_dis_top1, c_dis_top2, c_dis_top3 = st.columns([4.2, 3.2, 2.6])
        with c_dis_top1:
            st.markdown("#### 🎨 1. Estado del Diseño y Checklist de Etapas")
            st.caption(f"Marca las etapas completadas del diseño ({n_etapas_ok} de {n_etapas_tot} listas · {pct_diseno:.0f}%).")
        with c_dis_top2:
            est_dis_actual = obtener_estado_diseno_proyecto(proy_name)
            if est_dis_actual not in STATUS_FASES:
                est_dis_actual = STATUS_FASES[0]
            key_est_dis = f"sel_est_diseno_plan_{proy_name}"
            if key_est_dis not in st.session_state or st.session_state[key_est_dis] != est_dis_actual:
                st.session_state[key_est_dis] = est_dis_actual

            def _on_change_est_diseno():
                nuevo_e = st.session_state.get(key_est_dis, STATUS_FASES[0])
                guardar_estado_diseno_proyecto(proy_name, nuevo_e)

            st.selectbox(
                "Estado General del Diseño:",
                options=STATUS_FASES,
                key=key_est_dis,
                on_change=_on_change_est_diseno,
            )
        with c_dis_top3:
            st.markdown("<div style='padding-top: 24px;'></div>", unsafe_allow_html=True)
            banco_fases = obtener_banco_fases()
            nombres_banco = [f["Fase"] for f in banco_fases]
            todas_opciones_fases = list(dict.fromkeys(nombres_banco + fases_activas_actuales))
            with st.popover("⚙️ Configurar Etapas", use_container_width=True):
                with st.form(f"form_cfg_etapas_plan_{proy_name}"):
                    st.markdown("##### Etapas del Checklist de Diseño")
                    sel_fases = st.multiselect(
                        "Etapas activas en este proyecto:",
                        options=todas_opciones_fases,
                        default=fases_activas_actuales,
                    )
                    nueva_etapa_txt = st.text_input("➕ Agregar nueva etapa (opcional):", placeholder="Ej: Iluminación")
                    if st.form_submit_button("💾 Guardar Etapas", type="primary", use_container_width=True):
                        fases_final = list(sel_fases)
                        if nueva_etapa_txt.strip():
                            nf_added = agregar_fase_banco(nueva_etapa_txt.strip())
                            if nf_added["Fase"] not in fases_final:
                                fases_final.append(nf_added["Fase"])
                        sincronizar_fases_proyecto(proy_name, fases_final)
                        st.rerun()

        # Barra de progreso visual del checklist de diseño
        col_bar_d = "#4A7C59" if pct_diseno >= 100 else "#C85A32"
        st.markdown(
            f"<div style='background:#EFECE6; border-radius:6px; height:8px; overflow:hidden; margin:4px 0 12px 0;'>"
            f"<div style='background:{col_bar_d}; width:{max(0.0, min(100.0, pct_diseno)):.1f}%; height:100%; transition:width 0.2s ease;'></div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        if not fases_df.empty:
            cols_chk_dis = st.columns(2)
            for idx_r, r_f in fases_df.iterrows():
                f_id = safe_str(r_f.get("ID", ""))
                f_nom = safe_str(r_f.get("Fase", f"Etapa {idx_r + 1}"))
                checked_actual = bool(to_bool(r_f.get("Aprobado_Cliente", False)) or ("aprob" in str(r_f.get("Estado", "")).lower()))
                k_chk = f"chk_etapa_plan_{proy_name}_{f_id}_{idx_r}"
                if k_chk not in st.session_state or bool(st.session_state[k_chk]) != checked_actual:
                    st.session_state[k_chk] = checked_actual

                def _make_on_chk_fase(fase_id_val, fase_nom_val, key_c):
                    def _cb_chk():
                        nuevo_chk = bool(st.session_state.get(key_c, False))
                        m_f = st.session_state.fases["Proyecto"] == proy_name
                        if str(fase_id_val).strip():
                            m_f = m_f & (
                                (st.session_state.fases["ID"].astype(str) == str(fase_id_val))
                                | (st.session_state.fases["Fase"].astype(str) == str(fase_nom_val))
                            )
                        else:
                            m_f = m_f & (st.session_state.fases["Fase"].astype(str) == str(fase_nom_val))
                        if m_f.any():
                            st.session_state.fases.loc[m_f, "Aprobado_Cliente"] = nuevo_chk
                            st.session_state.fases.loc[m_f, "Estado"] = "🟢 Aprobado" if nuevo_chk else "⚪ Pendiente"
                            st.session_state.fases.loc[m_f, "Avance_Pct"] = 100 if nuevo_chk else 0
                            # Actualizar estado general del diseño automáticamente según el checklist
                            f_sub_p = st.session_state.fases[st.session_state.fases["Proyecto"] == proy_name]
                            ok_c = int((f_sub_p["Aprobado_Cliente"].apply(to_bool)).sum())
                            if ok_c >= len(f_sub_p) and len(f_sub_p) > 0:
                                guardar_estado_diseno_proyecto(proy_name, "🟢 Aprobado")
                            elif ok_c > 0:
                                guardar_estado_diseno_proyecto(proy_name, "🟡 En proceso")
                            else:
                                guardar_estado_diseno_proyecto(proy_name, "⚪ Pendiente")
                            clear_base_dfs()
                    return _cb_chk

                with cols_chk_dis[idx_r % 2]:
                    st.checkbox(
                        f"{f_nom}",
                        key=k_chk,
                        on_change=_make_on_chk_fase(f_id, f_nom, k_chk),
                    )
        else:
            st.info("No hay etapas configuradas en el checklist. Usa '⚙️ Configurar Etapas' para activarlas.")

    st.divider()

    # ==========================================================
    # 2. PLANIFICACIÓN DE PRESUPUESTO Y COMPARATIVO DE COTIZACIONES
    # ==========================================================
    plan_items = obtener_planificacion_presupuesto_proyecto(proy_name)
    res_plan = resumen_planificacion_presupuesto(plan_items)

    contratistas_disp = [""] + (
        st.session_state.maestro["ID_Contratista"].dropna().astype(str).unique().tolist()
        if "maestro" in st.session_state and not st.session_state.maestro.empty and "ID_Contratista" in st.session_state.maestro.columns
        else []
    )

    c_pl_hdr1, c_pl_hdr2, c_pl_hdr3 = st.columns([5.2, 2.4, 2.4])
    with c_pl_hdr1:
        st.markdown("#### 📐 2. Planificación de Presupuesto y Cotizaciones por Partida")
        st.caption(
            "Define las partidas que tendrá el presupuesto, cuántas cotizaciones solicitarás por partida, "
            "el contratista, el monto total y si ya fue **ENTREGADO** o sigue **Pendiente**."
        )
    with c_pl_hdr2:
        st.markdown("<div style='padding-top: 8px;'></div>", unsafe_allow_html=True)
        if st.button("➕ Agregar Partida a Cotizar", key=f"btn_add_part_plan_{proy_name}", type="primary", use_container_width=True):
            nuevo_num = len(plan_items) + 1
            plan_items.append({
                "id": f"pp_{nuevo_num}_{uuid.uuid4().hex[:4]}",
                "partida": f"{nuevo_num:02d}. Partida {nuevo_num}",
                "nombre_limpio": f"Partida {nuevo_num}",
                "num_cotizaciones": 2,
                "cotizacion_elegida": -1,
                "cotizaciones": [
                    {"contratista": "", "monto": 0.0, "entregado": False, "notas": ""},
                    {"contratista": "", "monto": 0.0, "entregado": False, "notas": ""},
                ],
            })
            guardar_planificacion_presupuesto_proyecto(proy_name, plan_items, sincronizar_partidas_ppto=False)
            st.rerun()
    with c_pl_hdr3:
        st.markdown("<div style='padding-top: 8px;'></div>", unsafe_allow_html=True)
        with st.popover("👷 Nuevo Contratista", use_container_width=True):
            with st.form(f"form_quick_contra_plan_{proy_name}", clear_on_submit=True):
                st.markdown("##### Registrar Contratista")
                nc_nom = st.text_input("Nombre del Contratista / Proveedor:")
                nc_esp = st.selectbox("Especialidad:", ESPECIALIDADES_DEFAULT)
                if st.form_submit_button("Guardar Contratista", type="primary", use_container_width=True) and nc_nom.strip():
                    nuevo_c_df = pd.DataFrame([{
                        "ID_Contratista": nc_nom.strip(),
                        "Especialidad": nc_esp,
                        "Ubicación_Base": "Lima",
                        "Notas": "",
                    }])
                    st.session_state.maestro = pd.concat([st.session_state.maestro, nuevo_c_df], ignore_index=True)
                    clear_base_dfs()
                    st.rerun()

    # 4 Tarjetas resumen de cotizaciones
    kp1, kp2, kp3, kp4 = st.columns(4)
    with kp1:
        render_metric_card(
            "Partidas Planificadas",
            f"{res_plan['total_partidas']} partidas",
            f"{res_plan['partidas_con_entrega']} con cotización recibida",
        )
    with kp2:
        render_metric_card(
            "Cotizaciones Entregadas",
            f"{res_plan['cotizaciones_entregadas']} de {res_plan['total_cotizaciones']}",
            "🟢 Ya recibidas",
            border_color="#4A7C59",
            text_color="#4A7C59",
        )
    with kp3:
        render_metric_card(
            "Cotizaciones Pendientes",
            f"{res_plan['cotizaciones_pendientes']}",
            "⏳ Faltan entregar",
            border_color="#D98A2B" if res_plan["cotizaciones_pendientes"] > 0 else "#4A7C59",
            text_color="#D98A2B" if res_plan["cotizaciones_pendientes"] > 0 else "#4A7C59",
        )
    with kp4:
        render_metric_card(
            "Presupuesto Comparado (Casco)",
            format_currency(res_plan["monto_estimado_optimo"]),
            "Suma de cotizaciones elegidas / mejores",
            border_color="#C85A32",
            text_color="#C85A32",
        )

    st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)

    # Renderizar cada Partida con sus N cotizaciones
    for idx_p0, item_p in enumerate(plan_items):
        idx_p1 = idx_p0 + 1
        p_nom_limpio = safe_str(item_p.get("nombre_limpio", limpiar_nombre_partida(item_p.get("partida", ""), idx_p1)))
        n_cots_p = int(item_p.get("num_cotizaciones", 2) or 1)
        cots_p = list(item_p.get("cotizaciones", []))
        elegida_idx = int(item_p.get("cotizacion_elegida", -1))

        entregadas_p = sum(1 for c in cots_p if c.get("entregado"))
        montos_validos = [
            (i_c, safe_float(c.get("monto", 0.0), 0.0), safe_str(c.get("contratista", "")))
            for i_c, c in enumerate(cots_p)
            if safe_float(c.get("monto", 0.0), 0.0) > 0
        ]
        mejor_cot_txt = "Sin cotización elegida"
        if 0 <= elegida_idx < len(cots_p):
            c_el = cots_p[elegida_idx]
            nom_el = safe_str(c_el.get("contratista", "")).strip() or f"Cotización #{elegida_idx + 1}"
            mejor_cot_txt = f"⭐ Elegida: {nom_el} ({format_currency(c_el.get('monto', 0.0))})"
        elif montos_validos:
            min_c = min(montos_validos, key=lambda x: x[1])
            mejor_cot_txt = f"💡 Más económica: {min_c[2] or f'Opción {min_c[0]+1}'} ({format_currency(min_c[1])})"
        else:
            mejor_cot_txt = "Sin montos aún"

        with st.container(border=True):
            cp_top1, cp_top2, cp_top3, cp_top4 = st.columns([4.2, 1.8, 3.0, 1.0])
            key_nom_plan = f"plan_pnom_{proy_name}_{idx_p0}"
            key_ncot_plan = f"plan_ncot_{proy_name}_{idx_p0}"
            if key_nom_plan not in st.session_state or st.session_state[key_nom_plan] != p_nom_limpio:
                st.session_state[key_nom_plan] = p_nom_limpio
            if key_ncot_plan not in st.session_state or int(st.session_state[key_ncot_plan]) != int(n_cots_p):
                st.session_state[key_ncot_plan] = int(n_cots_p)

            def _make_on_plan_header(i_p0, k_nom_pl, k_ncot_pl):
                def _cb_hdr():
                    curr_items = obtener_planificacion_presupuesto_proyecto(proy_name)
                    if 0 <= i_p0 < len(curr_items):
                        nuevo_nom_l = safe_str(st.session_state.get(k_nom_pl, "")).strip() or f"Partida {i_p0 + 1}"
                        curr_items[i_p0]["nombre_limpio"] = nuevo_nom_l
                        curr_items[i_p0]["partida"] = f"{i_p0 + 1:02d}. {nuevo_nom_l}"
                        curr_items[i_p0]["num_cotizaciones"] = int(st.session_state.get(k_ncot_pl, 2) or 1)
                        guardar_planificacion_presupuesto_proyecto(proy_name, curr_items, sincronizar_partidas_ppto=False)
                return _cb_hdr

            with cp_top1:
                st.text_input(
                    f"Partida {idx_p1} — Nombre de la Partida",
                    key=key_nom_plan,
                    on_change=_make_on_plan_header(idx_p0, key_nom_plan, key_ncot_plan),
                )
            with cp_top2:
                st.number_input(
                    "N° de Cotizaciones",
                    min_value=1,
                    max_value=15,
                    step=1,
                    key=key_ncot_plan,
                    on_change=_make_on_plan_header(idx_p0, key_nom_plan, key_ncot_plan),
                )
            with cp_top3:
                col_est_b = "#4A7C59" if entregadas_p == n_cots_p else ("#D98A2B" if entregadas_p > 0 else "#6E665E")
                st.markdown(
                    f"<div style='background:#FAF8F5; border:1px solid #DFD9CE; border-radius:8px; padding:7px 12px; margin-top:4px;'>"
                    f"<div style='font-size:11px; font-weight:700; color:{col_est_b}; text-transform:uppercase;'>"
                    f"📬 {entregadas_p}/{n_cots_p} Entregada(s) · {n_cots_p - entregadas_p} Pendiente(s)</div>"
                    f"<div style='font-size:12.5px; font-weight:700; color:#262320; margin-top:2px;'>{html_lib.escape(mejor_cot_txt)}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with cp_top4:
                st.markdown("<div style='padding-top: 26px;'></div>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"btn_del_plan_p_{proy_name}_{idx_p0}", disabled=(len(plan_items) <= 1), help="Eliminar partida del borrador", use_container_width=True):
                    plan_items.pop(idx_p0)
                    guardar_planificacion_presupuesto_proyecto(proy_name, plan_items, sincronizar_partidas_ppto=False)
                    prefijos_del = (
                        f"plan_pnom_{proy_name}_",
                        f"plan_ncot_{proy_name}_",
                        f"plan_cot_con_{proy_name}_",
                        f"plan_cot_mon_{proy_name}_",
                        f"plan_cot_ent_{proy_name}_",
                        f"plan_cot_eleg_{proy_name}_",
                    )
                    for k_st in list(st.session_state.keys()):
                        if str(k_st).startswith(prefijos_del):
                            del st.session_state[k_st]
                    st.rerun()

            def _sincronizar_fila_cot_widgets(curr_items, i_p0, i_c0, kc, km, ke):
                if 0 <= i_p0 < len(curr_items):
                    c_list = curr_items[i_p0].get("cotizaciones", [])
                    if 0 <= i_c0 < len(c_list):
                        if kc in st.session_state:
                            c_list[i_c0]["contratista"] = safe_str(st.session_state.get(kc, "")).strip()
                        if km in st.session_state:
                            c_list[i_c0]["monto"] = round(max(0.0, safe_float(st.session_state.get(km, 0.0), 0.0)), 2)
                        if ke in st.session_state:
                            c_list[i_c0]["entregado"] = bool(st.session_state.get(ke, False))

            # Filas de cotizaciones de esta partida
            for idx_c0, cot_it in enumerate(cots_p):
                idx_c1 = idx_c0 + 1
                es_ent = bool(cot_it.get("entregado", False))
                es_eleg = (elegida_idx == idx_c0)
                contra_val = safe_str(cot_it.get("contratista", "")).strip()
                opciones_c_row = list(dict.fromkeys(contratistas_disp + ([contra_val] if contra_val else [])))

                k_con = f"plan_cot_con_{proy_name}_{idx_p0}_{idx_c0}"
                k_mon = f"plan_cot_mon_{proy_name}_{idx_p0}_{idx_c0}"
                k_ent = f"plan_cot_ent_{proy_name}_{idx_p0}_{idx_c0}"
                k_elg = f"plan_cot_eleg_{proy_name}_{idx_p0}_{idx_c0}"

                contra_exp = contra_val if contra_val in opciones_c_row else ""
                monto_exp = float(safe_float(cot_it.get("monto", 0.0), 0.0))
                if k_con not in st.session_state or st.session_state[k_con] != contra_exp:
                    st.session_state[k_con] = contra_exp
                if k_mon not in st.session_state or abs(safe_float(st.session_state[k_mon], -1.0) - monto_exp) > 1e-6:
                    st.session_state[k_mon] = monto_exp
                if k_ent not in st.session_state or bool(st.session_state[k_ent]) != es_ent:
                    st.session_state[k_ent] = es_ent
                if k_elg not in st.session_state or bool(st.session_state[k_elg]) != es_eleg:
                    st.session_state[k_elg] = es_eleg

                def _make_on_cot_change(i_p0, i_c0, kc, km, ke):
                    def _cb_cot():
                        curr_items = obtener_planificacion_presupuesto_proyecto(proy_name)
                        _sincronizar_fila_cot_widgets(curr_items, i_p0, i_c0, kc, km, ke)
                        guardar_planificacion_presupuesto_proyecto(proy_name, curr_items, sincronizar_partidas_ppto=False)
                    return _cb_cot

                def _make_on_cot_eleg_change(i_p0, i_c0, kc, km, ke, k_eleg_w):
                    def _cb_eleg():
                        curr_items = obtener_planificacion_presupuesto_proyecto(proy_name)
                        _sincronizar_fila_cot_widgets(curr_items, i_p0, i_c0, kc, km, ke)
                        if 0 <= i_p0 < len(curr_items):
                            c_list = curr_items[i_p0].get("cotizaciones", [])
                            if 0 <= i_c0 < len(c_list):
                                marcar_eleg = bool(st.session_state.get(k_eleg_w, False))
                                if marcar_eleg:
                                    curr_items[i_p0]["cotizacion_elegida"] = int(i_c0)
                                elif int(curr_items[i_p0].get("cotizacion_elegida", -1)) == int(i_c0):
                                    curr_items[i_p0]["cotizacion_elegida"] = -1
                                guardar_planificacion_presupuesto_proyecto(proy_name, curr_items, sincronizar_partidas_ppto=False)
                                eleg_final = int(curr_items[i_p0].get("cotizacion_elegida", -1))
                                for j_c in range(len(c_list)):
                                    st.session_state[f"plan_cot_eleg_{proy_name}_{i_p0}_{j_c}"] = (j_c == eleg_final)
                    return _cb_eleg

                cc1, cc2, cc3, cc4, cc5 = st.columns([1.2, 3.2, 2.2, 1.7, 1.7])
                with cc1:
                    bg_tag = "#E8F5E9" if es_ent else "#FFF8E7"
                    col_tag = "#2E7D32" if es_ent else "#B76E00"
                    txt_tag = "🟢 ENTREGADO" if es_ent else "⏳ PENDIENTE"
                    st.markdown(
                        f"<div style='padding-top:6px;'>"
                        f"<span style='font-size:11.5px; font-weight:800; color:#262320;'>Cotización #{idx_c1}</span><br>"
                        f"<span style='display:inline-block; margin-top:2px; background:{bg_tag}; color:{col_tag}; font-size:10px; font-weight:800; padding:2px 7px; border-radius:99px;'>{txt_tag}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                with cc2:
                    st.selectbox(
                        f"Contratista #{idx_c1}",
                        options=opciones_c_row,
                        key=k_con,
                        on_change=_make_on_cot_change(idx_p0, idx_c0, k_con, k_mon, k_ent),
                        label_visibility="collapsed",
                    )
                with cc3:
                    st.number_input(
                        f"Monto S/ #{idx_c1}",
                        min_value=0.0,
                        step=0.01,
                        format="%.2f",
                        key=k_mon,
                        on_change=_make_on_cot_change(idx_p0, idx_c0, k_con, k_mon, k_ent),
                        label_visibility="collapsed",
                    )
                with cc4:
                    st.checkbox(
                        "Entregado",
                        key=k_ent,
                        on_change=_make_on_cot_change(idx_p0, idx_c0, k_con, k_mon, k_ent),
                    )
                with cc5:
                    st.checkbox(
                        "⭐ Elegida",
                        key=k_elg,
                        on_change=_make_on_cot_eleg_change(idx_p0, idx_c0, k_con, k_mon, k_ent, k_elg),
                        help="Marca esta cotización como la elegida (más indicada) en tu borrador comparativo",
                    )
    return
    """Pestaña 2: Gestión exclusiva del Diseño (02. Diseño) — Entregables por estado (pendiente, en proceso, en revisión, observado, aprobado), control de cambios y Drive vinculado."""
    st.markdown("### 🎨 02. DISEÑO — GESTIÓN DE ENTREGABLES (PLANOS, RENDERS Y 3D)")
    st.caption(
        "Gestión de entregables de diseño (Moodboard, Plano Preliminar, Modelado 3D, Renders y Planos Técnicos) "
        "según su estado (Pendiente, En proceso, En revisión cliente, Con cambios / Observado, Aprobado), historial de revisiones y enlace a Google Drive."
    )

    # 1. Conectar con la presentación / carpeta de diseño en Google Drive / Slides / Figma (manteniendo lo existente)
    drive_link = safe_str(proy_data.get('Link_Drive', '')).strip()
    c_drive1, c_drive2 = st.columns([6.8, 3.2])
    with c_drive1:
        if drive_link:
            st.markdown(
                f"<div style='background:#FAF8F5; border:1px solid #DFD9CE; border-left:4px solid #C85A32; border-radius:8px; padding:10px 14px; margin-bottom:12px; display:flex; align-items:center; justify-content:space-between;'>"
                f"<div><span style='font-size:11px; color:#6E665E; text-transform:uppercase; font-weight:700;'>📂 PRESENTACIÓN DE DISEÑO VINCULADA</span><br>"
                f"<a href='{drive_link}' target='_blank' style='color:#C85A32; font-weight:600; font-size:13px; text-decoration:none;'>{drive_link[:75]}{'...' if len(drive_link) > 75 else ''} ↗</a></div>"
                f"</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"<div style='background:#FAF8F5; border:1px dashed #DFD9CE; border-radius:8px; padding:10px 14px; margin-bottom:12px; color:#6E665E; font-size:12.5px;'>"
                f"ℹ️ <i>Aún no se ha vinculado la presentación o carpeta de Google Drive / Slides para este proyecto.</i>"
                f"</div>",
                unsafe_allow_html=True
            )
    with c_drive2:
        if drive_link:
            c_s1, c_s2 = st.columns([6.5, 3.5])
            with c_s1:
                st.link_button("🚀 ABRIR DRIVE ↗", drive_link, type="primary", use_container_width=True)
            with c_s2:
                with st.popover("✏️ EDITAR", use_container_width=True):
                    with st.form(f"f_edit_drive_{proy_name}"):
                        n_link = st.text_input("Enlace Drive / Slides:", value=drive_link)
                        if st.form_submit_button("GUARDAR", type="primary"):
                            if 'Link_Drive' not in st.session_state.proyectos.columns:
                                st.session_state.proyectos['Link_Drive'] = ""
                            st.session_state.proyectos['Link_Drive'] = st.session_state.proyectos['Link_Drive'].astype(object)
                            idx_matches = st.session_state.proyectos[st.session_state.proyectos['Nombre'] == proy_name].index
                            if not idx_matches.empty:
                                st.session_state.proyectos.loc[idx_matches, 'Link_Drive'] = n_link.strip()
                            clear_base_dfs()
                            st.rerun()
        else:
            with st.popover("🔗 CONECTAR DRIVE", use_container_width=True):
                with st.form(f"f_new_drive_{proy_name}"):
                    st.markdown("##### Presentación de Diseño en Drive")
                    st.caption("Pega el enlace de Google Drive, Google Slides o Figma del proyecto:")
                    n_link = st.text_input("URL:", placeholder="https://drive.google.com/...")
                    if st.form_submit_button("CONECTAR DRIVE", type="primary"):
                        if 'Link_Drive' not in st.session_state.proyectos.columns:
                            st.session_state.proyectos['Link_Drive'] = ""
                        st.session_state.proyectos['Link_Drive'] = st.session_state.proyectos['Link_Drive'].astype(object)
                        idx_matches = st.session_state.proyectos[st.session_state.proyectos['Nombre'] == proy_name].index
                        if not idx_matches.empty:
                            st.session_state.proyectos.loc[idx_matches, 'Link_Drive'] = n_link.strip()
                        clear_base_dfs()
                        st.rerun()

    # Preparar datos de etapas de diseño y bitácora de entregables / cambios por fecha
    fases_df = st.session_state.fases[st.session_state.fases['Proyecto'] == proy_name].copy()
    for c_req in COLS_FASES:
        if c_req not in fases_df.columns:
            fases_df[c_req] = 0 if c_req in ('Orden', 'Avance_Pct', 'Cambios_Realizados') else (False if c_req == 'Aprobado_Cliente' else "")
    fases_df['Estado'] = fases_df['Estado'].apply(_normalizar_estado_diseno)
    fases_df['Cambios_Realizados'] = pd.to_numeric(fases_df['Cambios_Realizados'], errors='coerce').fillna(0).astype(int)
    fases_df = fases_df.sort_values(by='Orden').reset_index(drop=True)
    fases_activas_actuales = fases_df['Fase'].tolist() if not fases_df.empty else []

    if 'entregables_planos' not in st.session_state or not isinstance(st.session_state.entregables_planos, pd.DataFrame):
        st.session_state.entregables_planos = pd.DataFrame(columns=COLS_ENTREGABLES)
    for c_ent in COLS_ENTREGABLES:
        if c_ent not in st.session_state.entregables_planos.columns:
            st.session_state.entregables_planos[c_ent] = 0 if c_ent == 'Nro_Cambios' else ""
    df_ent_proy = st.session_state.entregables_planos[st.session_state.entregables_planos['Proyecto'] == proy_name].copy()
    if not df_ent_proy.empty:
        df_ent_proy['Estado'] = df_ent_proy['Estado'].apply(_normalizar_estado_diseno)
        df_ent_proy['Nro_Cambios'] = pd.to_numeric(df_ent_proy['Nro_Cambios'], errors='coerce').fillna(0).astype(int)

    # 2. Métricas ejecutivas de Gestión del Diseño (Moodboard, Plano Preliminar, 3D/Renders y Conteo de Cambios)
    n_etapas_tot = len(fases_df)
    n_etapas_aprob = int(
        (fases_df['Aprobado_Cliente'].apply(to_bool) | fases_df['Estado'].astype(str).str.contains('Aprob', case=False, na=False)).sum()
    ) if not fases_df.empty else 0
    pct_diseno = (n_etapas_aprob / n_etapas_tot * 100.0) if n_etapas_tot > 0 else 0.0

    def _buscar_estado_etapa(patron: str) -> str:
        if fases_df.empty:
            return "Sin activar"
        m = fases_df[fases_df['Fase'].astype(str).str.contains(patron, case=False, na=False)]
        if m.empty:
            return "Sin activar"
        r0 = m.iloc[0]
        if to_bool(r0.get('Aprobado_Cliente', False)) or 'aprob' in str(r0.get('Estado', '')).lower():
            return "🟢 Aprobado"
        return str(r0.get('Estado', '⚪ Pendiente'))

    est_moodboard = _buscar_estado_etapa(r"moodboard|concepto")
    est_preliminar = _buscar_estado_etapa(r"preliminar|distribuci[oó]n|anteproyecto")
    est_3d_render = _buscar_estado_etapa(r"3d|render")

    cambios_en_fases = int(fases_df['Cambios_Realizados'].sum()) if not fases_df.empty else 0
    cambios_en_bitacora = int(df_ent_proy['Nro_Cambios'].sum()) if not df_ent_proy.empty else 0
    total_cambios_diseno = max(cambios_en_fases, cambios_en_bitacora)

    fechas_cambio_disp = []
    if not fases_df.empty:
        for fc in fases_df['Fecha_Ultimo_Cambio'].tolist():
            d_fc = parse_date(fc)
            if d_fc:
                fechas_cambio_disp.append(d_fc)
    if not df_ent_proy.empty:
        for fc in df_ent_proy['Fecha_Cambio'].tolist():
            d_fc = parse_date(fc)
            if d_fc:
                fechas_cambio_disp.append(d_fc)
    ult_fecha_cambio_str = max(fechas_cambio_disp).strftime("%d/%m/%Y") if fechas_cambio_disp else "Sin cambios"

    kd1, kd2, kd3, kd4 = st.columns(4)
    with kd1:
        render_metric_card(
            "Avance de Diseño",
            f"{pct_diseno:.0f}%",
            f"{n_etapas_aprob} de {n_etapas_tot} etapas aprobadas",
            border_color="#4A7C59" if pct_diseno >= 100 else "#C85A32",
            text_color="#4A7C59" if pct_diseno >= 100 else "#C85A32",
        )
    with kd2:
        est_mb_clean = est_moodboard.split(" ", 1)[-1] if " " in est_moodboard else est_moodboard
        render_metric_card(
            "Moodboard & Preliminar",
            est_mb_clean,
            f"Plano Preliminar: {est_preliminar}",
            border_color="#4A7C59" if "Aprobado" in est_moodboard and "Aprobado" in est_preliminar else "#D98A2B",
            text_color="#262320",
        )
    with kd3:
        tot_ent_p = len(df_ent_proy)
        aprob_ent_p = int(df_ent_proy['Estado'].astype(str).str.contains('Aprob', case=False, na=False).sum()) if not df_ent_proy.empty else 0
        est_3d_clean = est_3d_render.split(" ", 1)[-1] if " " in est_3d_render else est_3d_render
        render_metric_card(
            "Planos, Renders & 3D",
            est_3d_clean,
            f"{aprob_ent_p}/{tot_ent_p} entregables aprobados",
            border_color="#262320",
            text_color="#262320",
        )
    with kd4:
        render_metric_card(
            "Cambios Realizados",
            f"{total_cambios_diseno} cambio(s)",
            f"Último cambio: {ult_fecha_cambio_str}",
            border_color="#C85A32" if total_cambios_diseno > 0 else "#4A7C59",
            text_color="#C85A32" if total_cambios_diseno > 0 else "#4A7C59",
        )

    banco_fases = obtener_banco_fases()
    nombres_banco = [f["Fase"] for f in banco_fases]
    todas_opciones_fases = list(dict.fromkeys(nombres_banco + fases_activas_actuales))

    # 3. Banco de Etapas de Diseño: activar/desactivar por proyecto + agregar al banco
    with st.expander("🎨 CONFIGURAR ETAPAS DE DISEÑO — Activar / Desactivar o Crear Etapas", expanded=False):
        cb_left, cb_right = st.columns([6.5, 3.5])
        with cb_left:
            with st.form(f"form_tab_fases_banco_{proy_name}"):
                st.markdown("##### Selecciona las Etapas de Diseño del Proyecto")
                st.caption("Marca las etapas de diseño (Moodboard, Plano Preliminar, Modelado 3D, Renders, Planos) que aplican a este proyecto. Se conservarán los avances y cambios registrados.")
                checks_seleccionados = []
                cols_chk = st.columns(2)
                for idx_f, nom_f in enumerate(todas_opciones_fases):
                    col_c = cols_chk[idx_f % 2]
                    activo_actual = nom_f in fases_activas_actuales
                    if col_c.checkbox(nom_f, value=activo_actual, key=f"chk_bf_{proy_name}_{idx_f}"):
                        checks_seleccionados.append(nom_f)

                if st.form_submit_button("💾 ACTUALIZAR ETAPAS DE DISEÑO", type="primary", use_container_width=True):
                    sincronizar_fases_proyecto(proy_name, checks_seleccionados)
                    st.success(f"Etapas de diseño actualizadas ({len(checks_seleccionados)} activas en '{proy_name}').")
                    st.rerun()

        with cb_right:
            with st.form(f"form_nueva_fase_banco_{proy_name}", clear_on_submit=True):
                st.markdown("##### ➕ Nueva Etapa / Entregable")
                st.caption("Agrega una etapa o categoría de entregable al banco de diseño del estudio.")
                nf_nombre = st.text_input("Nombre del Entregable / Etapa", placeholder="")
                nf_etapa = st.selectbox("Categoría de Diseño", ETAPAS_DISENO)
                nf_activar = st.checkbox("Activar inmediatamente en este proyecto", value=True)
                if st.form_submit_button("AGREGAR AL BANCO DE DISEÑO", use_container_width=True) and nf_nombre.strip():
                    nueva_f = agregar_fase_banco(nf_nombre.strip(), etapa=nf_etapa)
                    if nf_activar:
                        nuevas_act = list(dict.fromkeys(fases_activas_actuales + [nueva_f["Fase"]]))
                        sincronizar_fases_proyecto(proy_name, nuevas_act)
                    st.success(f"Etapa '{nueva_f['Fase']}' añadida al Banco de Diseño.")
                    st.rerun()

    # 4. Tablero de Estados de Entregables (sin cronograma de hitos con fechas)
    resumen_est = _contar_estados_diseno(fases_df, df_ent_proy)
    estado_colors = {
        "⚪ Pendiente": "#9A9187",
        "🟡 En proceso": "#D98A2B",
        "🔵 En revisión cliente": "#3B82F6",
        "🟠 Con cambios / Observado": "#C85A32",
        "🟢 Aprobado": "#4A7C59",
    }
    cards_est_html = "".join(
        f"<div style='background:#FFFFFF; border:1px solid #DFD9CE; border-top:3px solid {estado_colors.get(est, '#6E665E')}; "
        f"border-radius:8px; padding:10px 12px;'>"
        f"<div style='font-size:11px; font-weight:700; color:#6E665E; text-transform:uppercase;'>{est}</div>"
        f"<div style='font-size:22px; font-weight:700; color:{estado_colors.get(est, '#262320')}; margin:2px 0;'>"
        f"{resumen_est.get(est, {}).get('total', 0)}</div>"
        f"<div style='font-size:11px; color:#6E665E;'>"
        f"{resumen_est.get(est, {}).get('etapas', 0)} etapa(s) · {resumen_est.get(est, {}).get('entregables', 0)} entregable(s)</div>"
        f"</div>"
        for est in STATUS_FASES
    )
    st.markdown(
        f"<div style='display:grid; grid-template-columns:repeat(auto-fit, minmax(150px, 1fr)); gap:10px; margin:8px 0 6px 0;'>"
        f"{cards_est_html}</div>",
        unsafe_allow_html=True,
    )

    st.divider()

    # 5. Tabla Editable de Etapas de Diseño (Moodboard, Plano Preliminar, 3D, Renders, Planos) + Conteo de Cambios
    st.markdown("#### 🎨 ETAPAS DE DISEÑO, ESTADOS Y APROBACIONES")
    st.caption(
        "Controla el estado de cada etapa de diseño (Pendiente, En proceso, En revisión cliente, Con cambios / Observado, Aprobado), "
        "su aprobación y el conteo de cambios realizados."
    )

    base_fases_key = f"base_df_fases_{proy_name}"
    counter_key = f"c_{base_fases_key}"
    c_val = st.session_state.get(counter_key, 0)
    w_key = f"ed_fases_{proy_name}_{c_val}"

    opciones_etapa_col = list(dict.fromkeys(ETAPAS_DISENO + [str(e) for e in fases_df['Etapa'].dropna().unique().tolist() if str(e).strip()]))

    display_fases = fases_df[[
        'ID', 'Orden', 'Fase', 'Etapa', 'Estado', 'Avance_Pct',
        'Cambios_Realizados', 'Fecha_Ultimo_Cambio',
        'Aprobado_Cliente', 'Responsable', 'Notas'
    ]].copy()
    display_fases['Fecha_Ultimo_Cambio'] = display_fases['Fecha_Ultimo_Cambio'].apply(lambda x: parse_date(x))
    display_fases['Avance_Pct'] = pd.to_numeric(display_fases['Avance_Pct'], errors='coerce').fillna(0).astype(int)
    display_fases['Cambios_Realizados'] = pd.to_numeric(display_fases['Cambios_Realizados'], errors='coerce').fillna(0).astype(int)
    display_fases['Aprobado_Cliente'] = display_fases['Aprobado_Cliente'].apply(to_bool)

    st.session_state[base_fases_key] = display_fases.copy()

    st.data_editor(
        st.session_state[base_fases_key],
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key=w_key,
        column_config={
            "ID": None,
            "Orden": st.column_config.NumberColumn("N°", width="small"),
            "Fase": st.column_config.TextColumn("Etapa de Diseño (Moodboard, Planos, 3D, Render)", width="large", required=True),
            "Etapa": st.column_config.SelectboxColumn("Categoría", options=opciones_etapa_col, width="small"),
            "Estado": st.column_config.SelectboxColumn("Estado", options=STATUS_FASES, width="medium"),
            "Avance_Pct": st.column_config.NumberColumn("Avance %", min_value=0, max_value=100, step=5, format="%d%%", width="small"),
            "Cambios_Realizados": st.column_config.NumberColumn("N° Cambios", min_value=0, max_value=100, step=1, format="%d", width="small", help="Cantidad de cambios realizados en esta etapa de diseño."),
            "Fecha_Ultimo_Cambio": st.column_config.DateColumn("Último Cambio", format="DD/MM/YYYY", width="small", help="Fecha en que se realizó el último cambio de esta etapa."),
            "Aprobado_Cliente": st.column_config.CheckboxColumn("Aprobado", width="small"),
            "Responsable": st.column_config.TextColumn("Responsable", width="small"),
            "Notas": st.column_config.TextColumn("Notas / Observaciones de Diseño", width="medium"),
        },
        on_change=on_table_edit,
        args=(
            base_fases_key,
            w_key,
            'fases',
            ['Proyecto'],
            [proy_name],
            ['Fecha_Ultimo_Cambio'],
            ['Fase', 'Etapa', 'Estado', 'Responsable', 'Notas'],
            ['Aprobado_Cliente'],
            ['Orden', 'Avance_Pct', 'Cambios_Realizados'],
            'ID'
        )
    )

    st.divider()

    # 6. Entregables de Diseño y Control de Revisiones: Planos, Renders, 3D y Moodboard
    c_bit_tit, c_bit_btn, c_bit_fil, c_bit_fil_est = st.columns([3.8, 2.4, 1.9, 1.9])
    with c_bit_tit:
        st.markdown("#### 📐 ENTREGABLES DE DISEÑO Y REVISIONES — PLANOS, RENDERS Y 3D")
        st.caption("Gestiona cada entregable (Moodboard, Plano Preliminar, Modelado 3D, Renders y Planos Técnicos) según su estado (Pendiente, En proceso, En revisión cliente, Con cambios / Observado, Aprobado), versión y control de cambios.")

    opciones_fases_select = fases_activas_actuales if fases_activas_actuales else [f["Fase"] for f in banco_fases]
    socios_disp_dis = obtener_catalogo_estudio("socios") or ["Alvaro", "Socio 1", "Socio 2"]

    with c_bit_btn:
        st.markdown("<div style='padding-top: 6px;'></div>", unsafe_allow_html=True)
        with st.popover("➕ NUEVO ENTREGABLE / REVISIÓN", use_container_width=True):
            with st.form(f"f_new_cambio_diseno_{proy_name}", clear_on_submit=True):
                st.markdown("##### Registrar Entregable o Revisión de Diseño")
                cd_fase = st.selectbox("Etapa de Diseño vinculada", opciones_fases_select)
                cd_tipo = st.selectbox("Tipo (Plano / Render / 3D / Moodboard)", TIPOS_ENTREGABLE_DISENO)
                cd_nom = st.text_input("Entregable (Plano / Vista 3D / Ambiente)", placeholder="")
                col_c1, col_c2 = st.columns(2)
                cd_est = col_c1.selectbox("Estado", STATUS_FASES, index=0)
                cd_resp = col_c2.selectbox("Responsable", socios_disp_dis)
                col_c3, col_c4 = st.columns(2)
                cd_ncambios = col_c3.number_input("N° de Cambios", min_value=0, max_value=50, value=0, step=1)
                cd_fecha = col_c4.date_input("Fecha de Registro / Revisión", value=datetime.date.today())
                cd_det = st.text_area("Observaciones / Detalle de Revisión", height=72, placeholder="")
                cd_link = st.text_input("Enlace a Plano / Render en Drive (opcional)", placeholder="https://drive.google.com/...")

                if st.form_submit_button("GUARDAR ENTREGABLE", type="primary", use_container_width=True):
                    if not cd_nom.strip():
                        st.error("Indica el nombre del plano, render, vista 3D o ambiente.")
                    else:
                        registrar_cambio_diseno(
                            proy_name=proy_name,
                            fase_diseno=cd_fase,
                            tipo_entregable=cd_tipo,
                            nombre_entregable=cd_nom.strip(),
                            fecha_cambio=cd_fecha,
                            detalle_cambio=cd_det.strip(),
                            estado=cd_est,
                            responsable=cd_resp,
                            nro_cambios=int(cd_ncambios),
                            link=cd_link.strip(),
                        )
                        st.success("Entregable guardado y estado de diseño actualizado.")
                        st.rerun()

    with c_bit_fil:
        filtro_cat_ent = st.selectbox(
            "Filtrar por tipo:",
            options=["🌐 Todos (Planos, 3D, Renders, Moodboard)"] + TIPOS_ENTREGABLE_DISENO,
            index=0,
            key=f"fil_tipo_diseno_{proy_name}",
        )

    with c_bit_fil_est:
        filtro_est_ent = st.selectbox(
            "Filtrar por estado:",
            options=["🌐 Todos los estados"] + STATUS_FASES,
            index=0,
            key=f"fil_est_diseno_{proy_name}",
        )

    # Resumen visual de conteo de cambios agrupados por fecha y por etapa (solo items con cambios > 0)
    fechas_resumen = {}
    if not df_ent_proy.empty:
        for _, r_e in df_ent_proy.iterrows():
            f_str = format_date(r_e.get('Fecha_Cambio') or r_e.get('Fecha_Limite'), default="Sin fecha")
            n_c = int(safe_float(r_e.get('Nro_Cambios', 0), 0))
            if n_c <= 0:
                continue
            nom_e = safe_str(r_e.get('Nombre_Entregable', 'Diseño'))
            entry = fechas_resumen.setdefault(f_str, {"cambios": 0, "items": []})
            entry["cambios"] += n_c
            if nom_e and nom_e not in entry["items"]:
                entry["items"].append(nom_e)
    elif not fases_df.empty:
        for _, r_f in fases_df[fases_df['Cambios_Realizados'] > 0].iterrows():
            f_str = format_date(r_f.get('Fecha_Ultimo_Cambio'), default="Fecha reciente")
            n_c = int(r_f.get('Cambios_Realizados', 0))
            nom_f = safe_str(r_f.get('Fase', ''))
            entry = fechas_resumen.setdefault(f_str, {"cambios": 0, "items": []})
            entry["cambios"] += n_c
            if nom_f and nom_f not in entry["items"]:
                entry["items"].append(nom_f)

    if fechas_resumen:
        pills_fechas_html = "".join(
            f"<div style='background:#FAF8F5; border:1px solid #DFD9CE; border-left:3px solid #C85A32; border-radius:6px; padding:6px 10px; font-size:12px;'>"
            f"<b style='color:#C85A32; font-family:monospace;'>📅 {f_k}: {info_f['cambios']} cambio(s)</b><br>"
            f"<span style='color:#6E665E; font-size:11.5px;'>{', '.join(info_f['items'][:3])}{'...' if len(info_f['items']) > 3 else ''}</span>"
            f"</div>"
            for f_k, info_f in list(fechas_resumen.items())[:8]
        )
        st.markdown(
            f"<div style='display:flex; flex-wrap:wrap; gap:8px; margin-bottom:12px;'>{pills_fechas_html}</div>",
            unsafe_allow_html=True,
        )

    df_ent_view = df_ent_proy.copy()
    if not df_ent_view.empty and not str(filtro_cat_ent).startswith("🌐"):
        df_ent_view = df_ent_view[df_ent_view['Especialidad'].astype(str) == filtro_cat_ent].copy()
    if not df_ent_view.empty and not str(filtro_est_ent).startswith("🌐"):
        df_ent_view = df_ent_view[df_ent_view['Estado'].astype(str) == filtro_est_ent].copy()

    opciones_esp_ent = list(dict.fromkeys(
        TIPOS_ENTREGABLE_DISENO
        + ESPECIALIDADES_DEFAULT
        + ([str(x) for x in df_ent_proy['Especialidad'].dropna().unique().tolist() if str(x).strip()] if not df_ent_proy.empty else [])
    ))
    opciones_fase_ent = list(dict.fromkeys(
        opciones_fases_select
        + ([str(x) for x in df_ent_proy['Fase'].dropna().unique().tolist() if str(x).strip()] if not df_ent_proy.empty else [])
    ))

    cols_ent_editor = [
        'ID', 'Fase', 'Especialidad', 'Nombre_Entregable',
        'Estado', 'Revision', 'Nro_Cambios', 'Fecha_Cambio',
        'Detalle_Cambio', 'Responsable', 'Link'
    ]
    display_ent = (
        df_ent_view[cols_ent_editor].copy()
        if not df_ent_view.empty
        else pd.DataFrame(columns=cols_ent_editor)
    )
    display_ent['Fecha_Cambio'] = display_ent['Fecha_Cambio'].apply(lambda x: parse_date(x))
    display_ent['Nro_Cambios'] = pd.to_numeric(display_ent['Nro_Cambios'], errors='coerce').fillna(0).astype(int)

    base_ent_key = f"base_df_ent_{proy_name}"
    c_ent_key = f"c_{base_ent_key}"
    c_ent_val = st.session_state.get(c_ent_key, 0)
    w_ent_key = f"ed_ent_{proy_name}_{c_ent_val}"

    st.session_state[base_ent_key] = display_ent.copy()

    st.data_editor(
        st.session_state[base_ent_key],
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key=w_ent_key,
        column_config={
            "ID": None,
            "Fase": st.column_config.SelectboxColumn("Etapa de Diseño", options=opciones_fase_ent, width="medium"),
            "Especialidad": st.column_config.SelectboxColumn("Tipo (Plano / Render / 3D)", options=opciones_esp_ent, width="medium"),
            "Nombre_Entregable": st.column_config.TextColumn("Entregable (Plano / Vista / Ambiente)", width="medium", required=True),
            "Estado": st.column_config.SelectboxColumn("Estado", options=STATUS_FASES, width="medium"),
            "Revision": st.column_config.TextColumn("Versión / Rev.", width="small"),
            "Nro_Cambios": st.column_config.NumberColumn("N° Cambios", min_value=0, max_value=100, step=1, format="%d", width="small"),
            "Fecha_Cambio": st.column_config.DateColumn("Última Revisión", format="DD/MM/YYYY", width="small"),
            "Detalle_Cambio": st.column_config.TextColumn("Observaciones / Detalle de Revisión", width="large"),
            "Responsable": st.column_config.TextColumn("Responsable", width="small"),
            "Link": st.column_config.LinkColumn("Link Drive / Archivo", width="small"),
        },
        on_change=on_table_edit,
        args=(
            base_ent_key,
            w_ent_key,
            'entregables_planos',
            ['Proyecto'],
            [proy_name],
            ['Fecha_Cambio'],
            ['Fase', 'Especialidad', 'Nombre_Entregable', 'Revision', 'Estado', 'Detalle_Cambio', 'Responsable', 'Link'],
            None,
            ['Nro_Cambios'],
            'ID'
        )
    )


def _render_table_dnd_controller(
    proy_name: str,
    idx_p: int,
    p_nom_completo: str,
    rows_ed: list,
    c_ppto_key: str,
    c_ppto_val: int,
):
    """
    Controlador invisible de Drag-and-Drop que conecta directamente con la tabla del presupuesto (03. PRESUPUESTO).
    Permite reordenar las tareas haciendo click sostenido directamente sobre el símbolo ⠿ (o la columna Ítem)
    de la tabla, mostrando la fila flotante y la guía de inserción en tiempo real.
    """
    safe_proy_id = re.sub(r"[^a-zA-Z0-9_]", "_", proy_name)
    bridge_label = f"dnd_bridge_{safe_proy_id}_{idx_p}"
    bridge_key = f"dnd_in_{safe_proy_id}_{idx_p}"

    def _on_dnd_change():
        raw_val = safe_str(st.session_state.get(bridge_key, "")).strip()
        if not raw_val:
            return
        orden_part = raw_val.split("|")[0].strip()
        try:
            nuevos_indices = [int(x.strip()) for x in orden_part.split(",") if x.strip() != ""]
        except ValueError:
            return
        if reordenar_tareas_partida_por_indices(proy_name, idx_p, p_nom_completo, nuevos_indices):
            st.session_state[c_ppto_key] = st.session_state.get(c_ppto_key, c_ppto_val) + 1
        st.session_state[bridge_key] = ""

    st.markdown(
        """
        <style>
        div[data-testid="stTextInput"]:has(input[aria-label^="dnd_bridge_"]) {
            position: absolute !important;
            width: 1px !important;
            height: 1px !important;
            opacity: 0 !important;
            overflow: hidden !important;
            pointer-events: none !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.text_input(
        bridge_label,
        key=bridge_key,
        label_visibility="collapsed",
        on_change=_on_dnd_change,
    )

    rows_meta_json = json.dumps([
        {
            "item": safe_str(r.get("Item", f"{idx_p}.{i_r+1:02d}")),
            "desc": safe_str(r.get("Descripcion", "")).strip(),
        }
        for i_r, r in enumerate(rows_ed)
    ])
    bridge_label_js = json.dumps(bridge_label)
    proy_name_js = json.dumps(proy_name)
    safe_proy_js = json.dumps(safe_proy_id)
    n_rows = len(rows_ed)

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="margin:0; padding:0; overflow:hidden; background:transparent;">
    <script>
    (function() {{
        const parentDoc = window.parent.document;
        const partIdx = {int(idx_p)};
        const proyName = {proy_name_js};
        const safeProy = {safe_proy_js};
        const nRows = {int(n_rows)};
        const rowsMeta = {rows_meta_json};
        const bridgeLabel = {bridge_label_js};

        function initDnd() {{
            const anchor = parentDoc.getElementById('anchor_ppto_' + safeProy + '_' + partIdx) || parentDoc.getElementById('anchor_ppto_' + proyName + '_' + partIdx);
            if (!anchor) return false;
            let container = anchor.parentElement;
            while (container && !container.querySelector('div[data-testid="stDataEditor"]')) {{
                container = container.parentElement;
            }}
            if (!container) return false;
            const editorWrap = container.querySelector('div[data-testid="stDataEditor"]') || container.querySelector('div[data-testid="stDataFrame"]');
            if (!editorWrap) return false;

            const instanceKey = partIdx + '_' + nRows;
            if (editorWrap.dataset.cotaDndInitialized === instanceKey) {{
                return true;
            }}
            editorWrap.dataset.cotaDndInitialized = instanceKey;

            let isDragging = false;
            let dragSrcIdx = -1;
            let ghostPill = null;
            let dropLine = null;

            function getOffsets() {{
                const canvas = editorWrap.querySelector('canvas');
                return canvas ? canvas.getBoundingClientRect() : editorWrap.getBoundingClientRect();
            }}

            function getTargetDropIdx(clientY, rect) {{
                const relY = clientY - rect.top - 36;
                let target = Math.round(relY / 35);
                return Math.max(0, Math.min(nRows, target));
            }}

            editorWrap.addEventListener('pointermove', function(e) {{
                if (isDragging) return;
                const rect = getOffsets();
                const relX = e.clientX - rect.left;
                const relY = e.clientY - rect.top;
                if (relX >= 0 && relX <= 75 && relY >= 36 && relY <= 36 + nRows * 35) {{
                    editorWrap.style.cursor = 'grab';
                }} else {{
                    editorWrap.style.cursor = '';
                }}
            }});

            function startDrag(e) {{
                if (e.button !== 0) return;
                const rect = getOffsets();
                const relX = e.clientX - rect.left;
                const relY = e.clientY - rect.top;

                if (relX >= 0 && relX <= 75 && relY >= 36 && relY <= 36 + nRows * 35) {{
                    const srcIdx = Math.floor((relY - 36) / 35);
                    if (srcIdx < 0 || srcIdx >= nRows) return;

                    isDragging = true;
                    dragSrcIdx = srcIdx;
                    e.preventDefault();
                    e.stopPropagation();

                    ghostPill = parentDoc.createElement('div');
                    ghostPill.style.cssText = 'position:fixed; z-index:9999999; pointer-events:none; background:#C85A32; color:#FFFFFF; font-family:-apple-system,BlinkMacSystemFont,sans-serif; font-size:12px; font-weight:700; padding:6px 14px; border-radius:6px; box-shadow:0 6px 20px rgba(200,90,50,0.40); transform:translate(-50%, -50%); display:flex; align-items:center; gap:8px; white-space:nowrap;';
                    const meta = rowsMeta[srcIdx] || {{ item: partIdx + '.' + String(srcIdx + 1).padStart(2, '0'), desc: '' }};
                    ghostPill.innerHTML = '<span style="font-size:14px;">⠿</span> <span style="background:rgba(255,255,255,0.25); padding:1px 5px; border-radius:3px;">' + meta.item + '</span> <span>' + (meta.desc || 'Tarea') + '</span>';
                    ghostPill.style.left = e.clientX + 'px';
                    ghostPill.style.top = e.clientY + 'px';
                    parentDoc.body.appendChild(ghostPill);

                    dropLine = parentDoc.createElement('div');
                    dropLine.style.cssText = 'position:fixed; z-index:9999998; pointer-events:none; height:3px; background:#C85A32; border-radius:2px; box-shadow:0 0 8px rgba(200,90,50,0.6); transition:top 0.05s ease;';
                    dropLine.style.left = rect.left + 'px';
                    dropLine.style.width = rect.width + 'px';
                    dropLine.style.top = (rect.top + 36 + srcIdx * 35) + 'px';
                    parentDoc.body.appendChild(dropLine);

                    parentDoc.body.style.userSelect = 'none';
                    editorWrap.style.cursor = 'grabbing';

                    function onMove(mEv) {{
                        if (!isDragging) return;
                        if (ghostPill) {{
                            ghostPill.style.left = mEv.clientX + 'px';
                            ghostPill.style.top = mEv.clientY + 'px';
                        }}
                        if (dropLine) {{
                            const curR = getOffsets();
                            const tgt = getTargetDropIdx(mEv.clientY, curR);
                            dropLine.style.left = curR.left + 'px';
                            dropLine.style.width = curR.width + 'px';
                            dropLine.style.top = (curR.top + 36 + tgt * 35) + 'px';
                        }}
                    }}

                    function onUp(uEv) {{
                        if (!isDragging) return;
                        isDragging = false;
                        editorWrap.style.cursor = '';
                        parentDoc.body.style.userSelect = '';

                        const curR = getOffsets();
                        const targetIdx = getTargetDropIdx(uEv.clientY, curR);

                        if (ghostPill && ghostPill.parentNode) ghostPill.parentNode.removeChild(ghostPill);
                        if (dropLine && dropLine.parentNode) dropLine.parentNode.removeChild(dropLine);
                        ghostPill = null;
                        dropLine = null;

                        parentDoc.removeEventListener('pointermove', onMove);
                        parentDoc.removeEventListener('pointerup', onUp);
                        parentDoc.removeEventListener('pointercancel', onUp);

                        if (targetIdx !== dragSrcIdx && targetIdx !== dragSrcIdx + 1) {{
                            let newIndices = Array.from({{length: nRows}}, (_, i) => i);
                            newIndices.splice(dragSrcIdx, 1);
                            let insertAt = (targetIdx > dragSrcIdx) ? (targetIdx - 1) : targetIdx;
                            insertAt = Math.max(0, Math.min(newIndices.length, insertAt));
                            newIndices.splice(insertAt, 0, dragSrcIdx);

                            const payload = newIndices.join(',') + '|' + Date.now();
                            try {{
                                const inputEl = parentDoc.querySelector('input[aria-label=' + JSON.stringify(bridgeLabel) + ']');
                                if (inputEl) {{
                                    const proto = window.parent.HTMLInputElement.prototype;
                                    const nativeSetter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
                                    if (nativeSetter) {{
                                        nativeSetter.call(inputEl, payload);
                                    }} else {{
                                        inputEl.value = payload;
                                    }}
                                    const tracker = inputEl._valueTracker;
                                    if (tracker) {{
                                        tracker.setValue('');
                                    }}
                                    inputEl.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                    inputEl.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    inputEl.focus();
                                    inputEl.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }}));
                                    inputEl.blur();
                                }}
                            }} catch (err) {{
                                console.error('Error enviando orden DND:', err);
                            }}
                        }}
                    }}

                    parentDoc.addEventListener('pointermove', onMove);
                    parentDoc.addEventListener('pointerup', onUp);
                    parentDoc.addEventListener('pointercancel', onUp);
                }}
            }}

            editorWrap.addEventListener('pointerdown', startDrag, true);
            editorWrap.addEventListener('mousedown', startDrag, true);

            return true;
        }}

        if (!initDnd()) {{
            let attempts = 0;
            const timer = setInterval(() => {{
                attempts++;
                if (initDnd() || attempts > 25) {{
                    clearInterval(timer);
                }}
            }}, 150);
        }}
    }})();
    </script>
    </body>
    </html>
    """
    components.html(html_code, height=0, scrolling=False)


def _render_obra_date_range_controller(
    proy_name: str,
    idx_p_1b: int,
    p_nom: str,
    df_tasks_p: pd.DataFrame,
    proy_inicio,
    counter_key: str,
):
    """
    Controlador invisible que integra el selector de rango de fechas (Inicio -> Fin en un solo
    calendario con resaltado continuo de días) directamente al hacer clic en Inicio o Fin dentro
    de la tabla st.data_editor de 05. PARTIDAS Y TAREAS.
    """
    if df_tasks_p is None or df_tasks_p.empty:
        return

    safe_proy_id = re.sub(r"[^a-zA-Z0-9_]", "_", str(proy_name or ""))
    bridge_label = f"OBRA_DATE_BRIDGE_{safe_proy_id}_{idx_p_1b}"
    bridge_key = f"obra_date_bridge_in_{safe_proy_id}_{idx_p_1b}"
    last_ts_key = f"_last_obra_date_ts_{safe_proy_id}_{idx_p_1b}"

    def _parse_iso_o_fecha(val):
        s_v = safe_str(val).strip()
        if not s_v:
            return None
        try:
            return datetime.date.fromisoformat(s_v[:10])
        except Exception:
            return parse_date(s_v)

    def _on_obra_range_bridge():
        raw_val = safe_str(st.session_state.get(bridge_key, "")).strip()
        if not raw_val:
            return
        try:
            msg = json.loads(raw_val)
        except Exception:
            st.session_state[bridge_key] = ""
            return
        ts_val = msg.get("ts")
        if ts_val is not None and st.session_state.get(last_ts_key) == ts_val:
            st.session_state[bridge_key] = ""
            return
        if ts_val is not None:
            st.session_state[last_ts_key] = ts_val

        action = safe_str(msg.get("action", "set_range")).strip()
        try:
            row_idx = int(msg.get("row_idx", -1))
        except Exception:
            row_idx = -1

        mask_t_cb = (
            (st.session_state.tasks["Proyecto"] == proy_name)
            & (st.session_state.tasks["Partida"] == p_nom)
        )
        indices_p_global = st.session_state.tasks[mask_t_cb].index.tolist()
        if 0 <= row_idx < len(indices_p_global):
            g_idx = indices_p_global[row_idx]
            if action == "clear_range":
                st.session_state.tasks.at[g_idx, "Inicio"] = ""
                st.session_state.tasks.at[g_idx, "Fin"] = ""
            elif action == "set_range":
                d_ini = _parse_iso_o_fecha(msg.get("inicio"))
                d_fin = _parse_iso_o_fecha(msg.get("fin")) or d_ini
                if d_ini is not None:
                    if d_fin is None or d_fin < d_ini:
                        d_fin = d_ini
                    st.session_state.tasks.at[g_idx, "Inicio"] = d_ini.strftime("%d/%m/%Y")
                    st.session_state.tasks.at[g_idx, "Fin"] = d_fin.strftime("%d/%m/%Y")
            st.session_state[counter_key] = int(st.session_state.get(counter_key, 0)) + 1
            clear_base_dfs()
        st.session_state[bridge_key] = ""

    st.text_input(
        bridge_label,
        key=bridge_key,
        label_visibility="collapsed",
        on_change=_on_obra_range_bridge,
    )

    default_anchor = parse_date(proy_inicio) or datetime.date.today()
    today_iso = datetime.date.today().strftime("%Y-%m-%d")
    tasks_meta = []
    for i_t, (_, r_t) in enumerate(df_tasks_p.iterrows()):
        d_i = parse_date(r_t.get("Inicio"))
        d_f = parse_date(r_t.get("Fin"))
        if d_i is not None and (d_f is None or d_f < d_i):
            d_f = d_i
        cod_item = safe_str(r_t.get("Codigo_Item", f"{idx_p_1b}.{i_t+1:02d}")).strip()
        desc_t = extraer_descripcion_tarea(r_t.get("Tarea", ""), cod_item)
        tasks_meta.append({
            "rowIdx": i_t,
            "code": cod_item,
            "label": desc_t,
            "inicio": d_i.strftime("%Y-%m-%d") if d_i else "",
            "fin": d_f.strftime("%Y-%m-%d") if d_f else "",
        })

    import time
    payload_str = json.dumps({
        "safeId": safe_proy_id,
        "partIdx": int(idx_p_1b),
        "anchorId": f"anchor_obra_tasks_{safe_proy_id}_{idx_p_1b}",
        "bridgeLabel": bridge_label,
        "defaultIso": default_anchor.strftime("%Y-%m-%d"),
        "todayIso": today_iso,
        "tasks": tasks_meta,
        "nonce": time.time(),
    }).replace("</", "<" + chr(92) + "/")

    html_template = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0; padding:0; overflow:hidden; background:transparent;">
<script>
(function() {
    const payload = __PAYLOAD_JSON__;
    const parentWin = window.parent;
    const parentDoc = parentWin.document;
    const ctrlKey = payload.safeId + '_' + payload.partIdx;
    const bridgeLabel = payload.bridgeLabel;
    const tasksMeta = payload.tasks || [];

    parentWin.__cotaObraDateControllers = parentWin.__cotaObraDateControllers || {};
    if (parentWin.__cotaObraDateControllers[ctrlKey] && typeof parentWin.__cotaObraDateControllers[ctrlKey].cleanup === 'function') {
        try { parentWin.__cotaObraDateControllers[ctrlKey].cleanup(); } catch (e) {}
    }

    function ensureCalStyles() {
        let stEl = parentDoc.getElementById('cota_obra_range_cal_styles');
        if (!stEl) {
            stEl = parentDoc.createElement('style');
            stEl.id = 'cota_obra_range_cal_styles';
            parentDoc.head.appendChild(stEl);
        }
        stEl.textContent = `
            #cota_obra_range_cal_popup {
                position: fixed;
                z-index: 2147483647;
                width: 286px;
                background: #FFFFFF;
                border: 1px solid #DFD7CC;
                border-radius: 12px;
                box-shadow: 0 14px 36px rgba(38, 35, 32, 0.22), 0 2px 8px rgba(38, 35, 32, 0.08);
                padding: 12px 12px 10px 12px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                color: #262320;
                user-select: none;
                box-sizing: border-box;
            }
            .cota-cal-task-hdr {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 6px;
                padding-bottom: 8px;
                margin-bottom: 8px;
                border-bottom: 1px solid #EFEAE2;
            }
            .cota-cal-task-title {
                font-size: 11.5px;
                font-weight: 700;
                color: #262320;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                flex: 1 1 auto;
            }
            .cota-cal-close-btn {
                border: none;
                background: transparent;
                color: #8C8275;
                cursor: pointer;
                font-size: 14px;
                line-height: 1;
                padding: 2px 5px;
                border-radius: 5px;
            }
            .cota-cal-close-btn:hover {
                background: #F4EFE8;
                color: #262320;
            }
            .cota-cal-nav {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 8px;
                gap: 4px;
            }
            .cota-cal-nav-btn {
                width: 28px;
                height: 28px;
                border: none;
                background: transparent;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 700;
                color: #5A5248;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .cota-cal-nav-btn:hover {
                background: #F4EFE8;
                color: #C85A32;
            }
            .cota-cal-sel-wrap {
                display: flex;
                align-items: center;
                gap: 4px;
            }
            .cota-cal-sel {
                border: 1px solid transparent;
                background: #FAF8F5;
                color: #262320;
                font-size: 13px;
                font-weight: 700;
                padding: 3px 6px;
                border-radius: 6px;
                cursor: pointer;
                outline: none;
            }
            .cota-cal-sel:hover, .cota-cal-sel:focus {
                border-color: #DFD7CC;
                background: #FFFFFF;
            }
            .cota-cal-wkdays {
                display: grid;
                grid-template-columns: repeat(7, 1fr);
                text-align: center;
                font-size: 11px;
                font-weight: 700;
                color: #8C8275;
                margin-bottom: 4px;
            }
            .cota-cal-wkdays > div {
                padding: 3px 0;
            }
            .cota-cal-grid {
                display: grid;
                grid-template-columns: repeat(7, 1fr);
                row-gap: 2px;
                column-gap: 0;
            }
            .cota-cal-cell {
                position: relative;
                height: 32px;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                padding: 0;
                margin: 0;
                border: none;
                background: transparent;
            }
            .cota-cal-band {
                position: absolute;
                top: 2px;
                bottom: 2px;
                left: 0;
                right: 0;
                pointer-events: none;
                background: transparent;
            }
            .cota-cal-num {
                position: relative;
                z-index: 2;
                width: 28px;
                height: 28px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 12.5px;
                font-weight: 500;
                color: #262320;
                transition: background 0.1s ease, color 0.1s ease;
            }
            .cota-cal-cell.is-muted .cota-cal-num {
                color: #BCB3A7;
            }
            .cota-cal-cell.is-today .cota-cal-num {
                box-shadow: inset 0 -2px 0 #C85A32;
                font-weight: 700;
            }
            .cota-cal-cell:hover .cota-cal-num {
                background: rgba(200, 90, 50, 0.14);
            }
            .cota-cal-cell.in-range .cota-cal-band {
                background: rgba(200, 90, 50, 0.16);
            }
            .cota-cal-cell.in-range .cota-cal-num {
                color: #9A3B1B;
                font-weight: 700;
            }
            .cota-cal-cell.range-start .cota-cal-band {
                left: 50%;
                right: 0;
                background: rgba(200, 90, 50, 0.16);
            }
            .cota-cal-cell.range-end .cota-cal-band {
                left: 0;
                right: 50%;
                background: rgba(200, 90, 50, 0.16);
            }
            .cota-cal-cell.range-single .cota-cal-band {
                background: transparent;
            }
            .cota-cal-cell.range-start .cota-cal-num,
            .cota-cal-cell.range-end .cota-cal-num,
            .cota-cal-cell.range-single .cota-cal-num {
                background: #C85A32 !important;
                color: #FFFFFF !important;
                font-weight: 700;
                box-shadow: 0 2px 6px rgba(200, 90, 50, 0.35);
            }
            .cota-cal-footer {
                margin-top: 9px;
                padding-top: 8px;
                border-top: 1px solid #EFEAE2;
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 6px;
            }
            .cota-cal-status {
                font-size: 11px;
                font-weight: 600;
                color: #7B7166;
                flex: 1 1 auto;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            .cota-cal-status strong {
                color: #C85A32;
            }
            .cota-cal-actions {
                display: flex;
                align-items: center;
                gap: 4px;
            }
            .cota-cal-mini-btn {
                border: 1px solid #DFD7CC;
                background: #FAF8F5;
                color: #5A5248;
                font-size: 10.5px;
                font-weight: 600;
                padding: 3px 7px;
                border-radius: 5px;
                cursor: pointer;
            }
            .cota-cal-mini-btn:hover {
                border-color: #C85A32;
                color: #C85A32;
                background: #FFF6EE;
            }
        `;
    }

    function findBridgeInput() {
        let inp = parentDoc.querySelector('input[aria-label="' + bridgeLabel + '"]');
        if (inp) return inp;
        const inputs = parentDoc.querySelectorAll('div[data-testid="stTextInput"] input');
        for (let i = 0; i < inputs.length; i++) {
            const el = inputs[i];
            if ((el.getAttribute('aria-label') || '').indexOf(bridgeLabel) >= 0) return el;
        }
        return null;
    }

    function sendBridgePayload(obj) {
        const inp = findBridgeInput();
        if (!inp) return;
        const valStr = JSON.stringify(Object.assign({ ts: Date.now() }, obj));
        const winProto = (parentWin.HTMLInputElement || window.HTMLInputElement).prototype;
        const nativeSetter = Object.getOwnPropertyDescriptor(winProto, 'value').set;
        const tracker = inp._valueTracker;
        if (tracker) tracker.setValue('');
        nativeSetter.call(inp, valStr);
        inp.dispatchEvent(new Event('input', { bubbles: true }));
        inp.dispatchEvent(new Event('change', { bubbles: true }));
        try { inp.focus({ preventScroll: true }); } catch (e) {}
        inp.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }));
        inp.blur();
    }

    function parseIso(s) {
        if (!s || typeof s !== 'string') return null;
        const m = s.match(/^(\\d{4})-(\\d{2})-(\\d{2})$/);
        if (!m) return null;
        return { y: parseInt(m[1], 10), m: parseInt(m[2], 10) - 1, d: parseInt(m[3], 10) };
    }
    function fmtIso(y, m, d) {
        return y + '-' + String(m + 1).padStart(2, '0') + '-' + String(d).padStart(2, '0');
    }
    function fmtShort(iso) {
        if (!iso) return '—';
        const p = iso.split('-');
        return p[2] + '/' + p[1] + '/' + p[0];
    }
    function diffDays(isoA, isoB) {
        const a = parseIso(isoA), b = parseIso(isoB);
        if (!a || !b) return 0;
        return Math.round((Date.UTC(b.y, b.m, b.d) - Date.UTC(a.y, a.m, a.d)) / 86400000);
    }

    const MONTHS_ES = [
        'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
    ];

    let openState = null;

    function closePopup() {
        const old = parentDoc.getElementById('cota_obra_range_cal_popup');
        if (old && old.parentNode) old.parentNode.removeChild(old);
        openState = null;
    }

    function dismissGlidePortal() {
        const portal = parentDoc.getElementById('portal');
        if (!portal) return;
        const portalInp = portal.querySelector('input, .gdg-input');
        if (portalInp) {
            try {
                portalInp.dispatchEvent(new KeyboardEvent('keydown', {
                    key: 'Escape', code: 'Escape', keyCode: 27, which: 27, bubbles: true
                }));
                portalInp.blur();
            } catch (e) {}
        }
    }

    function openRangePopup(rowIdx, clickX, clickY) {
        const meta = tasksMeta[rowIdx];
        if (!meta) return;
        ensureCalStyles();
        closePopup();

        const initIso = meta.inicio || payload.defaultIso || payload.todayIso;
        const initParsed = parseIso(initIso) || parseIso(payload.todayIso);

        openState = {
            ownerKey: ctrlKey,
            rowIdx: rowIdx,
            viewYear: initParsed.y,
            viewMonth: initParsed.m,
            savedStart: meta.inicio || '',
            savedEnd: meta.fin || meta.inicio || '',
            picking: false,
            pickStart: '',
            hoverIso: '',
        };

        const popup = parentDoc.createElement('div');
        popup.id = 'cota_obra_range_cal_popup';
        popup.dataset.ownerKey = ctrlKey;

        const popW = 286;
        const popH = 342;
        let left = Math.round(clickX - popW / 2);
        left = Math.max(12, Math.min(parentWin.innerWidth - popW - 12, left));
        let top = Math.round(clickY + 14);
        if (top + popH > parentWin.innerHeight - 12) {
            top = Math.max(12, Math.round(clickY - popH - 14));
        }
        top = Math.max(12, Math.min(parentWin.innerHeight - popH - 12, top));
        popup.style.left = left + 'px';
        popup.style.top = top + 'px';

        const hdr = parentDoc.createElement('div');
        hdr.className = 'cota-cal-task-hdr';
        const titleEl = parentDoc.createElement('div');
        titleEl.className = 'cota-cal-task-title';
        titleEl.textContent = (meta.code ? meta.code + ' — ' : '') + (meta.label || 'Tarea');
        titleEl.title = titleEl.textContent;
        const closeBtn = parentDoc.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'cota-cal-close-btn';
        closeBtn.textContent = '✕';
        closeBtn.addEventListener('click', function(ev) {
            ev.stopPropagation();
            closePopup();
        });
        hdr.appendChild(titleEl);
        hdr.appendChild(closeBtn);
        popup.appendChild(hdr);

        const nav = parentDoc.createElement('div');
        nav.className = 'cota-cal-nav';
        const prevBtn = parentDoc.createElement('button');
        prevBtn.type = 'button';
        prevBtn.className = 'cota-cal-nav-btn';
        prevBtn.textContent = '←';

        const selWrap = parentDoc.createElement('div');
        selWrap.className = 'cota-cal-sel-wrap';
        const selMonth = parentDoc.createElement('select');
        selMonth.className = 'cota-cal-sel';
        MONTHS_ES.forEach(function(mName, mIdx) {
            const opt = parentDoc.createElement('option');
            opt.value = String(mIdx);
            opt.textContent = mName;
            selMonth.appendChild(opt);
        });
        const selYear = parentDoc.createElement('select');
        selYear.className = 'cota-cal-sel';
        const todayParsed = parseIso(payload.todayIso) || initParsed;
        const minY = Math.min(initParsed.y - 3, todayParsed.y - 2);
        const maxY = Math.max(initParsed.y + 5, todayParsed.y + 5);
        for (let yVal = minY; yVal <= maxY; yVal++) {
            const opt = parentDoc.createElement('option');
            opt.value = String(yVal);
            opt.textContent = String(yVal);
            selYear.appendChild(opt);
        }
        selWrap.appendChild(selMonth);
        selWrap.appendChild(selYear);

        const nextBtn = parentDoc.createElement('button');
        nextBtn.type = 'button';
        nextBtn.className = 'cota-cal-nav-btn';
        nextBtn.textContent = '→';

        nav.appendChild(prevBtn);
        nav.appendChild(selWrap);
        nav.appendChild(nextBtn);
        popup.appendChild(nav);

        const wkRow = parentDoc.createElement('div');
        wkRow.className = 'cota-cal-wkdays';
        ['D', 'L', 'M', 'M', 'J', 'V', 'S'].forEach(function(w) {
            const d = parentDoc.createElement('div');
            d.textContent = w;
            wkRow.appendChild(d);
        });
        popup.appendChild(wkRow);

        const gridEl = parentDoc.createElement('div');
        gridEl.className = 'cota-cal-grid';
        popup.appendChild(gridEl);

        const footer = parentDoc.createElement('div');
        footer.className = 'cota-cal-footer';
        const statusEl = parentDoc.createElement('div');
        statusEl.className = 'cota-cal-status';
        const actionsEl = parentDoc.createElement('div');
        actionsEl.className = 'cota-cal-actions';

        const todayBtn = parentDoc.createElement('button');
        todayBtn.type = 'button';
        todayBtn.className = 'cota-cal-mini-btn';
        todayBtn.textContent = 'Hoy';
        todayBtn.addEventListener('click', function(ev) {
            ev.stopPropagation();
            const tp = parseIso(payload.todayIso);
            if (tp && openState) {
                openState.viewYear = tp.y;
                openState.viewMonth = tp.m;
                renderMonth();
            }
        });

        const clearBtn = parentDoc.createElement('button');
        clearBtn.type = 'button';
        clearBtn.className = 'cota-cal-mini-btn';
        clearBtn.textContent = 'Limpiar';
        clearBtn.addEventListener('click', function(ev) {
            ev.stopPropagation();
            const rIdx = openState ? openState.rowIdx : rowIdx;
            closePopup();
            sendBridgePayload({ action: 'clear_range', row_idx: rIdx });
        });

        actionsEl.appendChild(todayBtn);
        actionsEl.appendChild(clearBtn);
        footer.appendChild(statusEl);
        footer.appendChild(actionsEl);
        popup.appendChild(footer);

        function updateHighlightOnly() {
            if (!openState) return;
            let effStart = '';
            let effEnd = '';
            if (openState.picking && openState.pickStart) {
                const anchorEnd = openState.hoverIso || openState.pickStart;
                if (anchorEnd < openState.pickStart) {
                    effStart = anchorEnd;
                    effEnd = openState.pickStart;
                } else {
                    effStart = openState.pickStart;
                    effEnd = anchorEnd;
                }
                const days = diffDays(effStart, effEnd) + 1;
                statusEl.innerHTML = '<strong>' + fmtShort(effStart) + ' → ' + fmtShort(effEnd) + '</strong> (' + days + 'd)';
            } else if (openState.savedStart) {
                effStart = openState.savedStart;
                effEnd = openState.savedEnd || openState.savedStart;
                const days = diffDays(effStart, effEnd) + 1;
                statusEl.textContent = fmtShort(effStart) + ' → ' + fmtShort(effEnd) + ' (' + days + 'd)';
            } else {
                statusEl.textContent = 'Clic 1: Inicio · Clic 2: Fin';
            }

            const cells = gridEl.children;
            for (let i = 0; i < cells.length; i++) {
                const cell = cells[i];
                const iso = cell.dataset.iso;
                cell.classList.remove('in-range', 'range-start', 'range-end', 'range-single');
                if (effStart && effEnd) {
                    if (effStart === effEnd && iso === effStart) {
                        cell.classList.add('range-single');
                    } else if (iso === effStart) {
                        cell.classList.add('range-start');
                    } else if (iso === effEnd) {
                        cell.classList.add('range-end');
                    } else if (iso > effStart && iso < effEnd) {
                        cell.classList.add('in-range');
                    }
                }
            }
        }

        function onDayClick(iso) {
            if (!openState) return;
            if (!openState.picking) {
                openState.picking = true;
                openState.pickStart = iso;
                openState.hoverIso = iso;
                updateHighlightOnly();
            } else {
                const d1 = openState.pickStart;
                const d2 = iso;
                const inicio = d1 <= d2 ? d1 : d2;
                const fin = d1 <= d2 ? d2 : d1;
                const rIdx = openState.rowIdx;
                openState.picking = false;
                openState.savedStart = inicio;
                openState.savedEnd = fin;
                updateHighlightOnly();
                setTimeout(function() {
                    closePopup();
                    sendBridgePayload({
                        action: 'set_range',
                        row_idx: rIdx,
                        inicio: inicio,
                        fin: fin
                    });
                }, 60);
            }
        }

        function renderMonth() {
            if (!openState) return;
            selMonth.value = String(openState.viewMonth);
            selYear.value = String(openState.viewYear);
            gridEl.innerHTML = '';

            const firstDow = new Date(openState.viewYear, openState.viewMonth, 1).getDay();
            for (let slot = 0; slot < 42; slot++) {
                const dayOffset = slot - firstDow + 1;
                const dtObj = new Date(openState.viewYear, openState.viewMonth, dayOffset);
                const y = dtObj.getFullYear();
                const m = dtObj.getMonth();
                const d = dtObj.getDate();
                const iso = fmtIso(y, m, d);

                const btn = parentDoc.createElement('button');
                btn.type = 'button';
                btn.className = 'cota-cal-cell';
                btn.dataset.iso = iso;
                if (m !== openState.viewMonth) btn.classList.add('is-muted');
                if (iso === payload.todayIso) btn.classList.add('is-today');

                const band = parentDoc.createElement('span');
                band.className = 'cota-cal-band';
                const num = parentDoc.createElement('span');
                num.className = 'cota-cal-num';
                num.textContent = String(d);

                btn.appendChild(band);
                btn.appendChild(num);

                btn.addEventListener('mouseenter', function() {
                    if (openState && openState.picking && openState.hoverIso !== iso) {
                        openState.hoverIso = iso;
                        updateHighlightOnly();
                    }
                });
                btn.addEventListener('click', function(ev) {
                    ev.stopPropagation();
                    onDayClick(iso);
                });
                gridEl.appendChild(btn);
            }
            updateHighlightOnly();
        }

        prevBtn.addEventListener('click', function(ev) {
            ev.stopPropagation();
            if (!openState) return;
            openState.viewMonth -= 1;
            if (openState.viewMonth < 0) {
                openState.viewMonth = 11;
                openState.viewYear -= 1;
            }
            renderMonth();
        });
        nextBtn.addEventListener('click', function(ev) {
            ev.stopPropagation();
            if (!openState) return;
            openState.viewMonth += 1;
            if (openState.viewMonth > 11) {
                openState.viewMonth = 0;
                openState.viewYear += 1;
            }
            renderMonth();
        });
        selMonth.addEventListener('change', function(ev) {
            ev.stopPropagation();
            if (!openState) return;
            openState.viewMonth = parseInt(selMonth.value, 10);
            renderMonth();
        });
        selYear.addEventListener('change', function(ev) {
            ev.stopPropagation();
            if (!openState) return;
            openState.viewYear = parseInt(selYear.value, 10);
            renderMonth();
        });

        popup.addEventListener('mousedown', function(ev) { ev.stopPropagation(); });
        popup.addEventListener('pointerdown', function(ev) { ev.stopPropagation(); });
        popup.addEventListener('click', function(ev) { ev.stopPropagation(); });

        renderMonth();
        parentDoc.body.appendChild(popup);
    }

    function getSelectedCellInfo(editorWrap) {
        const selCell =
            editorWrap.querySelector('tbody td[aria-selected="true"], [role="gridcell"][aria-selected="true"]') ||
            editorWrap.querySelector('tbody td:focus, [role="gridcell"]:focus') ||
            editorWrap.querySelector('tbody td[tabindex="0"], [role="gridcell"][tabindex="0"]');
        if (!selCell) return null;

        let colName = '';
        const ariaCol = selCell.getAttribute('aria-colindex');
        if (ariaCol) {
            const th = editorWrap.querySelector(
                'thead th[aria-colindex="' + ariaCol + '"], [role="columnheader"][aria-colindex="' + ariaCol + '"]'
            );
            if (th) colName = (th.textContent || '').replace(/\\s+/g, ' ').trim().toLowerCase();
        }
        if (!colName && selCell.parentElement) {
            const cells = Array.from(selCell.parentElement.children);
            const cIdx = cells.indexOf(selCell);
            const ths = Array.from(editorWrap.querySelectorAll('thead th, [role="columnheader"]'));
            if (cIdx >= 0 && cIdx < ths.length) {
                colName = (ths[cIdx].textContent || '').replace(/\\s+/g, ' ').trim().toLowerCase();
            }
        }

        const tr = selCell.closest('tr, [role="row"]');
        if (!tr) return null;
        let rowIdx = -1;
        const ariaRow = parseInt(tr.getAttribute('aria-rowindex') || '', 10);
        if (!isNaN(ariaRow)) {
            const hdrRow = editorWrap.querySelector('thead tr, [role="row"][aria-rowindex="1"]');
            const hdrAria = hdrRow ? parseInt(hdrRow.getAttribute('aria-rowindex') || '1', 10) : 1;
            rowIdx = ariaRow - hdrAria - 1;
        }
        if (rowIdx < 0 && tr.parentElement) {
            rowIdx = Array.from(tr.parentElement.children).indexOf(tr);
        }
        return { colName: colName, rowIdx: rowIdx };
    }

    function findEditorWrap() {
        const anchor = parentDoc.getElementById(payload.anchorId);
        if (!anchor) return null;
        let block = anchor.closest('[data-testid="stElementContainer"], [data-testid="element-container"], .element-container') || anchor.parentElement;
        let sib = block ? block.nextElementSibling : null;
        let hops = 0;
        while (sib && hops < 5) {
            if (sib.matches && sib.matches('div[data-testid="stDataEditor"]')) return sib;
            const nested = sib.querySelector ? sib.querySelector('div[data-testid="stDataEditor"]') : null;
            if (nested) return nested;
            sib = sib.nextElementSibling;
            hops++;
        }
        let p = anchor.parentElement;
        while (p && !p.querySelector('div[data-testid="stDataEditor"]')) {
            p = p.parentElement;
        }
        return p ? p.querySelector('div[data-testid="stDataEditor"]') : null;
    }

    function handleGridInteraction(ev, editorWrap) {
        if (ev.button && ev.button !== 0) return;
        if (ev.target && ev.target.closest && ev.target.closest('[data-testid="stElementToolbar"], button, input, select, a')) {
            return;
        }
        const canvas = editorWrap.querySelector('canvas');
        if (canvas) {
            const rect = canvas.getBoundingClientRect();
            if (ev.clientX < rect.left || ev.clientX > rect.right - 12 || ev.clientY < rect.top + 36 || ev.clientY > rect.bottom - 8) {
                closePopup();
                return;
            }
        }
        const cx = ev.clientX;
        const cy = ev.clientY;
        setTimeout(function() {
            const info = getSelectedCellInfo(editorWrap);
            if (!info) {
                closePopup();
                return;
            }
            if ((info.colName === 'inicio' || info.colName === 'fin') && info.rowIdx >= 0 && info.rowIdx < tasksMeta.length) {
                dismissGlidePortal();
                openRangePopup(info.rowIdx, cx, cy);
                setTimeout(dismissGlidePortal, 70);
            } else {
                closePopup();
            }
        }, 55);
    }

    function initController() {
        const editorWrap = findEditorWrap();
        if (!editorWrap) return false;

        function onClick(ev) {
            handleGridInteraction(ev, editorWrap);
        }
        function onDblClick(ev) {
            const info = getSelectedCellInfo(editorWrap);
            if (info && (info.colName === 'inicio' || info.colName === 'fin') && info.rowIdx >= 0 && info.rowIdx < tasksMeta.length) {
                dismissGlidePortal();
                setTimeout(dismissGlidePortal, 60);
            }
        }
        function onDocMouseDown(ev) {
            const popup = parentDoc.getElementById('cota_obra_range_cal_popup');
            if (!popup) return;
            if (popup.contains(ev.target)) return;
            if (editorWrap.contains(ev.target)) return;
            closePopup();
        }
        function onDocKeyDown(ev) {
            if (ev.key === 'Escape') {
                closePopup();
            }
        }

        editorWrap.addEventListener('click', onClick, true);
        editorWrap.addEventListener('dblclick', onDblClick, true);
        parentDoc.addEventListener('mousedown', onDocMouseDown, true);
        parentDoc.addEventListener('keydown', onDocKeyDown, true);

        parentWin.__cotaObraDateControllers[ctrlKey] = {
            cleanup: function() {
                editorWrap.removeEventListener('click', onClick, true);
                editorWrap.removeEventListener('dblclick', onDblClick, true);
                parentDoc.removeEventListener('mousedown', onDocMouseDown, true);
                parentDoc.removeEventListener('keydown', onDocKeyDown, true);
                const popup = parentDoc.getElementById('cota_obra_range_cal_popup');
                if (popup && popup.dataset.ownerKey === ctrlKey) {
                    closePopup();
                }
            }
        };
        return true;
    }

    if (!initController()) {
        let attempts = 0;
        const timer = setInterval(function() {
            attempts++;
            if (initController() || attempts > 25) {
                clearInterval(timer);
            }
        }, 150);
    }
})();
</script>
</body>
</html>
"""
    html_code = html_template.replace("__PAYLOAD_JSON__", payload_str)
    components.html(html_code, height=0, scrolling=False)


def _render_barra_sync_presupuesto(proy_name: str, sync_gestion_act: bool, totales: dict):
    """Control opcional para mantener 03. PRESUPUESTO independiente o integrarlo sin pérdida hacia 05 y 06."""
    items_p = obtener_items_presupuesto_proyecto(proy_name, tc=totales.get("tc", 3.42))
    n_p = len(items_p)
    n_t = sum(len(it.get("tareas", []) or []) for it in items_p)

    df_t_all = st.session_state.get("tasks", pd.DataFrame())
    df_t_obra = (
        df_t_all[df_t_all["Proyecto"] == proy_name]
        if isinstance(df_t_all, pd.DataFrame) and not df_t_all.empty and "Proyecto" in df_t_all.columns
        else pd.DataFrame()
    )
    n_t_obra = len(df_t_obra)
    n_en_avance = 0
    if not df_t_obra.empty and "Estado" in df_t_obra.columns:
        n_en_avance = int(df_t_obra["Estado"].astype(str).apply(lambda x: x.strip() not in ("", "🟡 Planificado")).sum())

    with st.container(border=True):
        c_sw, c_act = st.columns([6.7, 3.3])
        with c_sw:
            k_sw = f"tog_sync_ppto_gestion_{proy_name}"
            if k_sw not in st.session_state or bool(st.session_state[k_sw]) != bool(sync_gestion_act):
                st.session_state[k_sw] = bool(sync_gestion_act)

            def _on_toggle_sync():
                nuevo_estado = bool(st.session_state.get(k_sw, False))
                res_s = establecer_estado_sincronizacion_presupuesto(proy_name, nuevo_estado, aplicar_integracion=nuevo_estado)
                integ = res_s.get("integracion") or {}
                if nuevo_estado:
                    st.toast(
                        f"🔗 Sincronización activada (+{integ.get('partidas_agregadas', 0)} partidas, "
                        f"+{integ.get('tareas_agregadas', 0)} tareas; {integ.get('avances_conservados', 0)} avances conservados).",
                        icon="🔗",
                    )
                else:
                    st.toast("🔒 Modo independiente activado: tus avances en 05 y pagos en 06 quedan protegidos.", icon="🔒")

            st.toggle(
                "🔗 Sincronizar cambios automáticamente con Gestión (05. Partidas/Tareas y 06. Cuadro de Pagos)",
                key=k_sw,
                on_change=_on_toggle_sync,
                help="Si está desactivado, 03. Presupuesto actualiza el contrato y finanzas de forma independiente sin modificar el avance de procesos ni los pagos.",
            )
            if sync_gestion_act:
                st.caption(
                    f"🔗 Modo integrado activo · Presupuesto ({n_p} part., {n_t} tar.) ↔ Gestión ({n_t_obra} tareas, {n_en_avance} con avance conservado)."
                )
            else:
                st.caption(
                    f"🔒 Modo independiente · Editar o importar aquí actualiza Finanzas sin borrar tus {n_en_avance} tarea(s) avanzadas en 05 ni pagos en 06."
                )

        with c_act:
            st.markdown("<div style='padding-top: 4px;'></div>", unsafe_allow_html=True)
            with st.popover("🔄 Integrar Partidas con Gestión", use_container_width=True):
                st.markdown("##### 🔗 Integración No Destructiva Presupuesto → Gestión")
                st.caption(
                    "Combina por nombre/código: **conserva estados** (*En Proceso / Completado*), "
                    "**fechas**, **contratistas** y **pagos registrados**; actualiza montos y agrega solo lo nuevo."
                )
                st.markdown(
                    f"- **En 03. Presupuesto:** `{n_p}` partida(s) · `{n_t}` tarea(s) · Casco `{format_currency(totales.get('subtotal_casco', 0.0))}`\n"
                    f"- **En 05. Partidas y Tareas:** `{n_t_obra}` tarea(s) (`{n_en_avance}` con avance/estado activo)"
                )
                inc_obra = st.checkbox(
                    "Integrar en 05. Partidas y Tareas (conservar avances)",
                    value=True,
                    key=f"chk_int_obra_{proy_name}",
                )
                inc_pagos = st.checkbox(
                    "Sincronizar montos en 06. Cuadro de Pagos (conservar pagos)",
                    value=True,
                    key=f"chk_int_pagos_{proy_name}",
                )
                if st.button(
                    "✅ INTEGRAR AHORA (CONSERVAR AVANCES)",
                    type="primary",
                    use_container_width=True,
                    disabled=(not inc_obra and not inc_pagos),
                    key=f"btn_exec_integ_ppto_{proy_name}",
                ):
                    r_int = integrar_presupuesto_con_gestion(proy_name, incluir_obra=inc_obra, incluir_pagos=inc_pagos)
                    st.toast(
                        f"✅ Integrado: +{r_int['partidas_agregadas']} part. nuevas, "
                        f"{r_int['tareas_actualizadas']} tar. actualizadas, +{r_int['tareas_agregadas']} nuevas "
                        f"({r_int['avances_conservados']} avances conservados).",
                        icon="✅",
                    )
                    st.rerun()


def _render_tab_presupuesto(proy_name, proy_data):
    """
    Pestaña 3: Constructor y Editor de Presupuesto All-in-One dentro de COTA.
    Permite definir dinámicamente la cantidad de Partidas (1, 2, 3, 4...), sus nombres,
    y la cantidad de Tareas por cada Partida (1.01, 1.02, 1.03...), reordenarlas verticalmente,
    asignar Especialidad y Contratista (uso interno), o importar presupuestos de tablas / Excel / CSV.
    """
    sync_gestion_act = obtener_estado_sincronizacion_presupuesto(proy_name)
    st.session_state[f"_ppto_indep_ui_{proy_name}"] = not sync_gestion_act
    asegurar_estructura_presupuesto_proyecto(proy_name, n_partidas_default=3, n_tareas_default=3, solo_presupuesto=(not sync_gestion_act))
    if "proyectos" in st.session_state and not st.session_state.proyectos.empty:
        m_p_sync = st.session_state.proyectos["Nombre"] == proy_name
        if m_p_sync.any():
            idx_p_sync = st.session_state.proyectos[m_p_sync].index[0]
            _pend_cfg = st.session_state.pop(f"_pending_sync_ppto_cfg_{proy_name}", None)
            if isinstance(_pend_cfg, dict):
                for _k_suf, _v_soles in _pend_cfg.items():
                    if _k_suf in ("util", "gg"):
                        st.session_state[f"cfg_modo_{_k_suf}_{proy_name}"] = "monto"
                        st.session_state[f"cfg_{_k_suf}_monto_{proy_name}"] = float(safe_float(_v_soles, 0.0))
                        st.session_state.pop(f"cfg_{_k_suf}_pct_{proy_name}", None)
            if f"cfg_gg_pct_{proy_name}" in st.session_state and st.session_state.get(f"cfg_modo_gg_{proy_name}", "pct") == "pct":
                st.session_state.proyectos.at[idx_p_sync, "GG_Pct"] = float(safe_float(st.session_state.get(f"cfg_gg_pct_{proy_name}"), 2.0))
            if f"cfg_util_pct_{proy_name}" in st.session_state and st.session_state.get(f"cfg_modo_util_{proy_name}", "pct") == "pct":
                st.session_state.proyectos.at[idx_p_sync, "Utilidades_Pct"] = float(safe_float(st.session_state.get(f"cfg_util_pct_{proy_name}"), 15.0))
    totales = recalcular_totales_presupuesto_proyecto(proy_name, sincronizar_pactado=sync_gestion_act)
    params = obtener_parametros_presupuesto_proyecto(proy_name)

    items_ppto = obtener_items_presupuesto_proyecto(proy_name, tc=totales.get("tc", 3.42))

    safe_fn_p = "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in proy_name).strip("_") or "Proyecto"
    col_tit_p, col_undo, col_imp_top, col_exp_x, col_exp_pdf = st.columns([3.7, 1.6, 1.7, 1.5, 1.5])
    with col_tit_p:
        st.markdown("### 📐 PRESUPUESTO Y COTIZACIÓN DEL PROYECTO")
        if sync_gestion_act:
            st.caption(
                "Define partidas, tareas, metrados y precios unitarios en tiempo real. "
                "Sincronización opcional **activada** hacia **05. PARTIDAS Y TAREAS** y **06. COBROS & FINANZAS** (conservando avances)."
            )
        else:
            st.caption(
                "Define partidas, tareas, metrados y precios unitarios de forma independiente para actualizar el contrato y Finanzas "
                "sin alterar tus avances en **05. PARTIDAS Y TAREAS** ni pagos en **06. COBROS & FINANZAS**."
            )
        if totales.get("contrato_manual") and safe_float(totales.get("total_calculado_partidas", 0.0), 0.0) > 0.0:
            c_cm_msg, c_cm_btn = st.columns([3.2, 1.8])
            with c_cm_msg:
                st.caption(
                    f"💼 Contrato fijado manualmente en **{format_currency(totales.get('presupuesto_total', 0.0))}** "
                    f"(calculado por partidas: {format_currency(totales.get('total_calculado_partidas', 0.0))})."
                )
            with c_cm_btn:
                if st.button("🔄 Usar calculado", key=f"btn_reset_contrato_calc_{proy_name}", use_container_width=True):
                    guardar_valor_contrato_proyecto(
                        proy_name,
                        safe_float(totales.get("total_calculado_partidas", 0.0), 0.0),
                        manual=False,
                    )
                    recalcular_totales_presupuesto_proyecto(proy_name)
                    st.rerun()
    with col_undo:
        st.markdown("<div style='padding-top: 8px;'></div>", unsafe_allow_html=True)
        cu1, cu2 = st.columns(2)
        with cu1:
            can_undo = puede_deshacer_presupuesto(proy_name)
            if st.button("↩️ Deshacer", key=f"btn_undo_ppto_{proy_name}", disabled=not can_undo, help="Deshacer último cambio en el presupuesto (como en Excel)", use_container_width=True):
                if deshacer_presupuesto(proy_name):
                    st.toast("↩️ Cambio deshecho", icon="↩️")
                    st.rerun()
        with cu2:
            can_redo = puede_rehacer_presupuesto(proy_name)
            if st.button("↪️ Rehacer", key=f"btn_redo_ppto_{proy_name}", disabled=not can_redo, help="Rehacer cambio deshecho", use_container_width=True):
                if rehacer_presupuesto(proy_name):
                    st.toast("↪️ Cambio rehecho", icon="↪️")
                    st.rerun()
    with col_imp_top:
        st.markdown("<div style='padding-top: 8px;'></div>", unsafe_allow_html=True)
        if st.button("📥 IMPORTAR PRESUPUESTO", key=f"btn_toggle_imp_ppto_{proy_name}", use_container_width=True):
            st.session_state[f"show_imp_ppto_{proy_name}"] = not st.session_state.get(f"show_imp_ppto_{proy_name}", False)
    with col_exp_x:
        st.markdown("<div style='padding-top: 8px;'></div>", unsafe_allow_html=True)
        xlsx_export_bytes = exportar_proyecto_a_formato_venti(proy_name)
        st.download_button(
            "📥 EXCEL (.XLSX)",
            data=xlsx_export_bytes,
            file_name=f"Presupuesto_{safe_fn_p}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
            key=f"btn_exp_excel_top_{proy_name}",
        )
    with col_exp_pdf:
        st.markdown("<div style='padding-top: 8px;'></div>", unsafe_allow_html=True)
        pdf_export_bytes = exportar_presupuesto_pdf(proy_name)
        st.download_button(
            "📄 PDF (.PDF)",
            data=pdf_export_bytes,
            file_name=f"Presupuesto_{safe_fn_p}.pdf",
            mime="application/pdf",
            use_container_width=True,
            key=f"btn_exp_pdf_top_{proy_name}",
        )

    # Control de sincronización opcional Presupuesto <-> Gestión (05 y 06)
    _render_barra_sync_presupuesto(proy_name, sync_gestion_act, totales)

    # Panel Importador Inteligente de Presupuesto
    if st.session_state.get(f"show_imp_ppto_{proy_name}", False):
        with st.container(border=True):
            ci_1, ci_2 = st.columns([8.5, 1.5])
            with ci_1:
                st.markdown("##### 📥 Importar Presupuesto")
                st.caption(
                    "Pega directamente una tabla de presupuesto (con columnas como *Partida, Tarea / Sub-partida, Unidad, Metraje, Valor Unitario, Valor Parcial*) "
                    "o sube un archivo `.xlsx` / `.csv`. El sistema la transformará automáticamente al formato oficial de COTA."
                )
            with ci_2:
                if st.button("✖ Cerrar", key=f"btn_close_imp_ppto_{proy_name}", use_container_width=True):
                    st.session_state[f"show_imp_ppto_{proy_name}"] = False
                    st.rerun()

            fuente_imp = st.radio(
                "Método de importación:",
                options=["texto", "archivo"],
                format_func=lambda x: "📋 Pegar Tabla" if x == "texto" else "📁 Subir archivo (.xlsx / .xls / .csv)",
                horizontal=True,
                key=f"rad_fuente_ppto_{proy_name}",
            )

            parsed_imp = None
            if fuente_imp == "texto":
                txt_spark = st.text_area(
                    "Pega aquí la tabla del presupuesto:",
                    height=165,
                    placeholder=(
                        "| Item | Partida / Tarea | Unidad | Metraje | V. Unitario | Valor Parcial |\n"
                        "|---|---|---|---|---|---|\n"
                        "| 1 | OBRAS PROVISIONALES Y DEMOLICIÓN | | | | |\n"
                        "| 1.01 | Desmontaje y eliminación de desmonte | glb | 1.00 | 1800.00 | 1800.00 |\n"
                        "| 1.02 | Protección de áreas comunes | m2 | 45.00 | 25.00 | 1125.00 |\n"
                        "| 2 | PISOS Y REVESTIMIENTOS | | | | |\n"
                        "| 2.01 | Instalación de piso porcelanato | m2 | 60.00 | 95.00 | 5700.00 |"
                    ),
                    key=f"txt_spark_in_{proy_name}",
                )
                if txt_spark and txt_spark.strip():
                    parsed_imp = parsear_presupuesto_flexible(txt_spark, tc_default=float(params["tc"]))
            else:
                up_f_ppto = st.file_uploader(
                    "Selecciona el archivo (.xlsx, .xls, .csv):",
                    type=["xlsx", "xls", "csv"],
                    key=f"up_f_ppto_in_{proy_name}",
                )
                if up_f_ppto is not None:
                    parsed_imp = parsear_presupuesto_flexible(up_f_ppto, tc_default=float(params["tc"]))

            if parsed_imp is not None and parsed_imp.get("partidas"):
                n_p_det = len(parsed_imp["partidas"])
                n_t_det = sum(len(p.get("tareas", [])) for p in parsed_imp["partidas"])
                st.markdown("---")
                es_modo_reemplazar = (st.session_state.get(f"rad_modo_imp_ppto_{proy_name}", "reemplazar") == "reemplazar")
                if es_modo_reemplazar:
                    st.markdown("###### ⚙️ Ajustar Parámetros de Gastos Generales y Utilidades")
                c_imp_g1, c_imp_g2, c_imp_g3, c_imp_g4 = (st.columns([1.3, 1.3, 1.1, 1.0]) if es_modo_reemplazar else (None, None, None, None))
                if not es_modo_reemplazar:
                    m_gg_imp_calc = 0.0
                    pct_gg_imp_calc = float(params.get("gg_pct", 2.0))
                    modo_gg_imp_tab = str(params.get("modo_gg", "pct"))
                    monto_fijo_gg_tab = float(params.get("monto_fijo_gg", 0.0))
                    m_util_imp_calc = 0.0
                    pct_util_imp_calc = float(params.get("utilidades_pct", 15.0))
                    modo_util_imp_tab = str(params.get("modo_util", "pct"))
                    monto_fijo_util_tab = float(params.get("monto_fijo_util", 0.0))
                    in_tc_tab = float(params.get("tc", 3.42))
                    in_igv_tab = bool(params.get("incluir_igv", False))
                if es_modo_reemplazar:
                  with c_imp_g1:
                    modo_gg_imp_tab = st.radio(
                        "Gastos Generales:",
                        options=["pct", "monto"],
                        format_func=lambda x: "% Casco" if x == "pct" else "Monto Fijo (S/)",
                        horizontal=True,
                        key=f"rad_modo_gg_imp_tab_{proy_name}",
                    )
                    if modo_gg_imp_tab == "pct":
                        in_gg_pct = st.number_input("% GG", value=float(parsed_imp.get("gg_pct", 2.0)), min_value=0.0, max_value=100.0, step=0.5, format="%.1f", key=f"in_gg_pct_tab_{proy_name}")
                        m_gg_imp_calc = redondear_arriba_10(parsed_imp["subtotal_casco"] * (in_gg_pct / 100.0))
                        pct_gg_imp_calc = round(float(in_gg_pct), 2)
                        monto_fijo_gg_tab = 0.0
                    else:
                        in_gg_monto = st.number_input("Monto GG (S/)", value=float(parsed_imp.get("gg_monto", 0.0)), min_value=0.0, step=10.0, format="%.2f", key=f"in_gg_monto_tab_{proy_name}")
                        m_gg_imp_calc = redondear_arriba_10(in_gg_monto)
                        pct_gg_imp_calc = round((m_gg_imp_calc / parsed_imp["subtotal_casco"] * 100.0) if parsed_imp["subtotal_casco"] > 0 else 0.0, 2)
                        monto_fijo_gg_tab = m_gg_imp_calc
                if es_modo_reemplazar:
                  with c_imp_g2:
                    modo_util_imp_tab = st.radio(
                        "Gestión y Supervisión:",
                        options=["pct", "monto"],
                        format_func=lambda x: "% Casco" if x == "pct" else "Monto Fijo (S/)",
                        horizontal=True,
                        key=f"rad_modo_util_imp_tab_{proy_name}",
                    )
                    if modo_util_imp_tab == "pct":
                        in_util_pct = st.number_input("% Util.", value=float(parsed_imp.get("utilidades_pct", 15.0)), min_value=0.0, max_value=100.0, step=0.5, format="%.1f", key=f"in_util_pct_tab_{proy_name}")
                        m_util_imp_calc = redondear_arriba_100(parsed_imp["subtotal_casco"] * (in_util_pct / 100.0))
                        pct_util_imp_calc = round(float(in_util_pct), 2)
                        monto_fijo_util_tab = 0.0
                    else:
                        in_util_monto = st.number_input("Monto Util. (S/)", value=float(parsed_imp.get("utilidades_monto", 0.0)), min_value=0.0, step=100.0, format="%.2f", key=f"in_util_monto_tab_{proy_name}")
                        m_util_imp_calc = redondear_arriba_100(in_util_monto)
                        pct_util_imp_calc = round((m_util_imp_calc / parsed_imp["subtotal_casco"] * 100.0) if parsed_imp["subtotal_casco"] > 0 else 0.0, 2)
                        monto_fijo_util_tab = m_util_imp_calc
                if es_modo_reemplazar:
                  with c_imp_g3:
                    in_tc_tab = st.number_input("TC", value=float(parsed_imp.get("tc", params["tc"])), min_value=1.0, max_value=10.0, step=0.01, format="%.2f", key=f"in_tc_tab_{proy_name}")
                if es_modo_reemplazar:
                  with c_imp_g4:
                    st.markdown("<div style='padding-top: 26px;'></div>", unsafe_allow_html=True)
                    in_igv_tab = st.checkbox("IGV (18%)", value=bool(parsed_imp.get("igv_pct", 0.0) > 0 or parsed_imp.get("incluir_igv", False)), key=f"in_igv_tab_{proy_name}")

                # Recalcular valores ajustados
                parsed_imp["modo_gg"] = modo_gg_imp_tab
                parsed_imp["monto_fijo_gg"] = monto_fijo_gg_tab
                parsed_imp["gg_monto"] = m_gg_imp_calc
                parsed_imp["gg_pct"] = pct_gg_imp_calc

                parsed_imp["modo_util"] = modo_util_imp_tab
                parsed_imp["monto_fijo_util"] = monto_fijo_util_tab
                parsed_imp["utilidades_monto"] = m_util_imp_calc
                parsed_imp["utilidades_pct"] = pct_util_imp_calc

                parsed_imp["tc"] = in_tc_tab
                base_imp_tab = parsed_imp["subtotal_casco"] + m_gg_imp_calc + m_util_imp_calc
                parsed_imp["igv_monto"] = round(base_imp_tab * 0.18, 2) if in_igv_tab else 0.0
                parsed_imp["igv_pct"] = 18.0 if in_igv_tab else 0.0
                parsed_imp["incluir_igv"] = in_igv_tab
                parsed_imp["presupuesto_total"] = round(base_imp_tab + parsed_imp["igv_monto"], 2)
                parsed_imp["presupuesto_dolares"] = round(parsed_imp["presupuesto_total"] / in_tc_tab, 2) if in_tc_tab > 0 else 0.0

                st.markdown(
                    f"**✅ Presupuesto detectado:** `{n_p_det}` Partida(s) · `{n_t_det}` Tarea(s) · "
                    f"Sub Total Casco: `{format_currency(parsed_imp['subtotal_casco'])}`" +
                    (f" · Gastos Generales: `{format_currency(parsed_imp['gg_monto'])}` ({parsed_imp['gg_pct']:g}%) · " if es_modo_reemplazar else "") +
                    (f"Gestión/Utilidades: `{format_currency(parsed_imp['utilidades_monto'])}` ({parsed_imp['utilidades_pct']:g}%) · " if es_modo_reemplazar else "") +
                    (f"**TOTAL: `{format_currency(parsed_imp['presupuesto_total'])}`**" if es_modo_reemplazar else "")
                )
                modo_aplicar = st.radio(
                    "Modo de carga:",
                    options=["reemplazar", "agregar"],
                    format_func=lambda x: "🔄 Reemplazar el presupuesto actual del proyecto" if x == "reemplazar" else "➕ Agregar a las partidas actuales",
                    horizontal=True,
                    key=f"rad_modo_imp_ppto_{proy_name}",
                )
                sincronizar_en_import = st.checkbox(
                    "🔗 Integrar también con Gestión (05. Partidas/Tareas y 06. Cuadro de Pagos, conservando avances)",
                    value=sync_gestion_act,
                    key=f"chk_sync_imp_ppto_{proy_name}",
                    help="Desmarcado = actualiza solo 03. Presupuesto y las finanzas del proyecto sin modificar lo avanzado en procesos ni los pagos.",
                )
                if st.button("✅ TRANSFORMAR Y CARGAR EN EL PRESUPUESTO", type="primary", use_container_width=True, key=f"btn_apply_spark_{proy_name}"):
                    res_imp = aplicar_cotizacion_a_proyecto(
                        proy_name=proy_name,
                        parsed_data=parsed_imp,
                        modo=modo_aplicar,
                        actualizar_ficha=(modo_aplicar == "reemplazar"),
                        incluir_partidas_vacias=True,
                        solo_presupuesto=(not sincronizar_en_import),
                    )
                    st.session_state[f"show_imp_ppto_{proy_name}"] = False
                    st.success(f"Presupuesto cargado con éxito: {res_imp['partidas_importadas']} partidas y {res_imp['tareas_importadas']} tareas.")
                    st.rerun()

    # Panel de Configuración Global del Presupuesto (incluye Honorarios de Diseño, % o Monto Exacto con redondeo)
    with st.container(border=True):
        st.markdown("##### ⚙️ Configuración de Presupuesto")
        c_cfg1, c_cfg2, c_cfg3, c_cfg4, c_cfg_hon, c_cfg5 = st.columns([1.5, 1.2, 2.1, 2.1, 1.6, 1.1])

        key_tc = f"cfg_tc_ppto_{proy_name}"
        key_modo_gg = f"cfg_modo_gg_{proy_name}"
        key_gg_pct = f"cfg_gg_pct_{proy_name}"
        key_gg_monto = f"cfg_gg_monto_{proy_name}"
        key_modo_util = f"cfg_modo_util_{proy_name}"
        key_util_pct = f"cfg_util_pct_{proy_name}"
        key_util_monto = f"cfg_util_monto_{proy_name}"
        key_hon = f"cfg_hon_diseno_{proy_name}"
        key_igv = f"cfg_igv_chk_{proy_name}"

        hon_actual = safe_float(proy_data.get("Honorarios_Diseno", 0.0), 0.0)

        def _on_change_params_ppto():
            modo_gg_val = st.session_state.get(key_modo_gg, params.get("modo_gg", "pct"))
            gg_pct_val = safe_float(st.session_state.get(key_gg_pct, params["gg_pct"]), 2.0)
            gg_monto_val = safe_float(st.session_state.get(key_gg_monto, params.get("monto_fijo_gg", 0.0)), 0.0)

            modo_util_val = st.session_state.get(key_modo_util, params.get("modo_util", "pct"))
            util_pct_val = safe_float(st.session_state.get(key_util_pct, params["utilidades_pct"]), 15.0)
            util_monto_val = safe_float(st.session_state.get(key_util_monto, params.get("monto_fijo_util", 0.0)), 0.0)

            guardar_parametros_presupuesto_proyecto(
                proy_name=proy_name,
                tc=safe_float(st.session_state.get(key_tc, params["tc"]), 3.42),
                gg_pct=gg_pct_val,
                utilidades_pct=util_pct_val,
                incluir_igv=bool(st.session_state.get(key_igv, params["incluir_igv"])),
                modo_gg=modo_gg_val,
                monto_fijo_gg=gg_monto_val,
                modo_util=modo_util_val,
                monto_fijo_util=util_monto_val,
            )
            if key_hon in st.session_state and "proyectos" in st.session_state and not st.session_state.proyectos.empty:
                st.session_state.proyectos["Honorarios_Diseno"] = pd.to_numeric(
                    st.session_state.proyectos.get("Honorarios_Diseno", 0.0), errors="coerce"
                ).fillna(0.0).astype(float)
                idx_p_m = st.session_state.proyectos[st.session_state.proyectos["Nombre"] == proy_name].index
                if not idx_p_m.empty:
                    st.session_state.proyectos.loc[idx_p_m, "Honorarios_Diseno"] = float(safe_float(st.session_state.get(key_hon, 0.0), 0.0))

        with c_cfg1:
            st.markdown("<div style='padding-top: 27px;'></div>", unsafe_allow_html=True)
            if st.button(
                "➕ Agregar Partida",
                key=f"btn_add_partida_{proy_name}",
                use_container_width=True,
                help="Agrega una nueva partida principal al presupuesto con sus tareas iniciales.",
            ):
                agregar_partida_presupuesto(proy_name, n_tareas_default=3, ambito="presupuesto")
                st.rerun()
        with c_cfg2:
            st.number_input(
                "Tipo de Cambio",
                min_value=1.0,
                max_value=10.0,
                value=float(params["tc"]),
                step=0.01,
                format="%.2f",
                key=key_tc,
                on_change=_on_change_params_ppto,
            )
        with c_cfg3:
            st.radio(
                "Gastos Generales:",
                options=["pct", "monto"],
                index=0 if params.get("modo_gg", "pct") == "pct" else 1,
                format_func=lambda x: "% Casco" if x == "pct" else "Monto Fijo (S/)",
                horizontal=True,
                key=key_modo_gg,
                on_change=_on_change_params_ppto,
            )
            if st.session_state.get(key_modo_gg, params.get("modo_gg", "pct")) == "pct":
                st.number_input(
                    "% Gastos Gen.",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(params["gg_pct"]),
                    step=0.5,
                    format="%.1f",
                    key=key_gg_pct,
                    on_change=_on_change_params_ppto,
                    help="Calcula % del Casco y redondea hacia arriba al múltiplo de 10.",
                )
            else:
                st.number_input(
                    "Monto GG (S/.)",
                    min_value=0.0,
                    value=float(params.get("monto_fijo_gg", totales.get("gg_monto", 0.0))),
                    step=10.0,
                    format="%.2f",
                    key=key_gg_monto,
                    on_change=_on_change_params_ppto,
                    help="Monto exacto de Gastos Generales (redondeo hacia arriba al 10).",
                )
        with c_cfg4:
            st.radio(
                "Gestión y Supervisión:",
                options=["pct", "monto"],
                index=0 if params.get("modo_util", "pct") == "pct" else 1,
                format_func=lambda x: "% Casco" if x == "pct" else "Monto Fijo (S/)",
                horizontal=True,
                key=key_modo_util,
                on_change=_on_change_params_ppto,
            )
            if st.session_state.get(key_modo_util, params.get("modo_util", "pct")) == "pct":
                st.number_input(
                    "% Gestión / Util.",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(params["utilidades_pct"]),
                    step=0.5,
                    format="%.1f",
                    key=key_util_pct,
                    on_change=_on_change_params_ppto,
                    help="Calcula % del Casco y redondea hacia arriba al múltiplo de 100.",
                )
            else:
                st.number_input(
                    "Monto Util. (S/.)",
                    min_value=0.0,
                    value=float(params.get("monto_fijo_util", totales.get("utilidades_monto", 0.0))),
                    step=100.0,
                    format="%.2f",
                    key=key_util_monto,
                    on_change=_on_change_params_ppto,
                    help="Monto exacto de Utilidades (redondeo hacia arriba al 100).",
                )
        with c_cfg_hon:
            st.markdown("<div style='padding-top: 24px;'></div>", unsafe_allow_html=True)
            st.number_input(
                "Honorarios Diseño (S/)",
                min_value=0.0,
                value=float(hon_actual),
                step=100.0,
                format="%.2f",
                key=key_hon,
                on_change=_on_change_params_ppto,
                help="Honorarios de diseño del proyecto (se reflejan en el Resumen y Finanzas).",
            )
        with c_cfg5:
            st.markdown("<div style='padding-top: 50px;'></div>", unsafe_allow_html=True)
            st.checkbox(
                "IGV (18%)",
                value=bool(params["incluir_igv"]),
                key=key_igv,
                on_change=_on_change_params_ppto,
                help="Si marcas la casilla se aplica 18% de IGV; si no, queda en 0%.",
            )

    # Recargar métricas actualizadas
    totales = recalcular_totales_presupuesto_proyecto(proy_name, sincronizar_pactado=sync_gestion_act)
    items_ppto = obtener_items_presupuesto_proyecto(proy_name, tc=totales.get("tc", 3.42))
    n_parts_ppto = len(items_ppto)
    total_tareas_proy = sum(len(it.get("tareas", []) or []) for it in items_ppto)

    unidades_cat = obtener_catalogo_estudio("unidades") or UNIDADES_MEDIDA
    especialidades_cat = list(dict.fromkeys([""] + (obtener_catalogo_estudio("especialidades") or ESPECIALIDADES_DEFAULT) + extraer_esp(st.session_state.maestro)))
    contratistas_cat = [""] + (st.session_state.maestro["ID_Contratista"].dropna().unique().tolist() if "maestro" in st.session_state and not st.session_state.maestro.empty else [])

    # 5 Tarjetas de Resumen del Presupuesto en Vivo
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        render_metric_card(
            "Sub Total (Casco)",
            format_currency(totales["subtotal_casco"]),
            f"{n_parts_ppto} partidas · {total_tareas_proy} tareas",
        )
    with k2:
        render_metric_card(
            f"Gastos Generales ({totales['gg_pct']:g}%)",
            format_currency(totales["gg_monto"]),
            "Sincronizado con Caja Chica / GG" if sync_gestion_act else "Presupuesto del proyecto (GG)",
            border_color="#C85A32",
            text_color="#C85A32",
        )
    with k3:
        render_metric_card(
            f"Gestión / Superv. ({totales['utilidades_pct']:g}%)",
            format_currency(totales["utilidades_monto"]),
            "Sincronizado con Utilidades" if sync_gestion_act else "Presupuesto del proyecto (Utilidades)",
            border_color="#4A7C59",
            text_color="#4A7C59",
        )
    with k4:
        igv_lbl = "18%" if totales["incluir_igv"] else "0%"
        render_metric_card(
            f"IGV ({igv_lbl})",
            format_currency(totales["igv_monto"]),
            "Impuesto General a las Ventas",
            border_color="#6E665E",
            text_color="#6E665E",
        )
    with k5:
        render_metric_card(
            "TOTAL PRESUPUESTO",
            format_currency(totales["presupuesto_total"]),
            f"USD {totales['presupuesto_dolares']:,.2f} (TC: {totales['tc']:.2f})",
            border_color="#262320",
            text_color="#262320",
        )

    st.divider()

    # Iterar cada Partida (1, 2, 3, 4...) y su tabla editable de Tareas (1.01, 1.02, 1.03...)
    resumen_rows = []
    subtotal_casco_val = totales["subtotal_casco"]

    for idx_p, part_item in enumerate(items_ppto, start=1):
        p_nom_completo = safe_str(part_item.get("nombre", f"Partida {idx_p}"))
        p_nom_limpio = limpiar_nombre_partida(p_nom_completo, idx_p)

        tareas_list_p = part_item.get("tareas", []) or []
        n_tareas_p = max(1, len(tareas_list_p))

        sub_partida = totales["subtotales_por_partida"].get(p_nom_completo, safe_float(part_item.get("monto_pactado", 0.0), 0.0))
        mix_partida = (sub_partida / subtotal_casco_val * 100.0) if subtotal_casco_val > 0 else 0.0

        resumen_rows.append({
            "Ítem": str(idx_p),
            "Descripción": p_nom_limpio,
            "Moneda": "Soles",
            "Factor": "",
            "Importe_Fmt": format_currency(sub_partida),
            "Mix": f"{mix_partida:.1f}%",
            "Tipo_Fila": "partida",
        })

        with st.container(border=True):
            base_ppto_key = f"base_df_ppto_{proy_name}_{idx_p}"
            c_ppto_key = f"c_{base_ppto_key}"
            c_ppto_val = st.session_state.get(c_ppto_key, 0)
            w_ppto_key = f"ed_ppto_{proy_name}_{idx_p}_{c_ppto_val}"
            sel_saved_key = f"sel_saved_ppto_{proy_name}_{idx_p}"
            sel_ver_key = f"sel_ver_ppto_{proy_name}_{idx_p}"

            # Cabecera de la Partida: Nombre editable + N° de Tareas editable + Sub Total, Mix, Mover y Eliminar Partida
            cp_nom, cp_cnt, cp_sub, cp_mix, cp_mv = st.columns([3.1, 1.5, 1.6, 1.0, 2.8])

            key_pnom = f"ppto_pnom_{proy_name}_{idx_p}"
            key_ntasks = f"ppto_ntasks_{proy_name}_{idx_p}"

            # Sincronizar el widget de N° de Tareas con la cantidad real de filas de esta partida
            st.session_state[key_ntasks] = int(n_tareas_p)
            st.session_state[key_pnom] = p_nom_limpio

            def _make_on_rename(p_idx_1b, curr_full, k_nom):
                def _cb():
                    nuevo_val = st.session_state.get(k_nom, "")
                    renombrar_partida_presupuesto(proy_name, p_idx_1b, curr_full, nuevo_val, ambito="presupuesto")
                return _cb

            def _make_on_cant_tasks(p_idx_1b, curr_full, k_cnt, k_base, k_c):
                def _cb():
                    nueva_c = st.session_state.get(k_cnt, 1)
                    ajustar_cantidad_tareas_partida(proy_name, p_idx_1b, curr_full, int(nueva_c), ambito="presupuesto")
                    if k_base in st.session_state:
                        del st.session_state[k_base]
                    st.session_state[k_c] = st.session_state.get(k_c, 0) + 1
                return _cb

            with cp_nom:
                st.text_input(
                    f"Partida {idx_p} — Nombre de la Partida",
                    key=key_pnom,
                    on_change=_make_on_rename(idx_p, p_nom_completo, key_pnom),
                    placeholder="",
                )
            with cp_cnt:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                if st.button("➕ Agregar Tarea", key=f"btn_add_task_ppto_{proy_name}_{idx_p}", use_container_width=True):
                    agregar_tarea_presupuesto(proy_name, idx_p, p_nom_completo, ambito="presupuesto")
                    if base_ppto_key in st.session_state:
                        del st.session_state[base_ppto_key]
                    st.session_state[c_ppto_key] = st.session_state.get(c_ppto_key, 0) + 1
                    st.rerun()
            if False:
                st.number_input(
                    f"N° de Tareas ({idx_p}.01, {idx_p}.02...)",
                    min_value=1,
                    max_value=100,
                    step=1,
                    key=key_ntasks,
                    on_change=_make_on_cant_tasks(idx_p, p_nom_completo, key_ntasks, base_ppto_key, c_ppto_key),
                )
            with cp_sub:
                st.markdown(
                    f"<div style='background:#FAF8F5; border:1px solid #DFD9CE; border-radius:8px; padding:8px 12px; margin-top:4px; text-align:right;'>"
                    f"<div style='font-size:11px; color:#6E665E; font-weight:600; text-transform:uppercase;'>Sub Total Partida {idx_p}</div>"
                    f"<div style='font-size:16px; color:#262320; font-weight:700; font-family:monospace;'>{format_currency(sub_partida)}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with cp_mix:
                st.markdown(
                    f"<div style='background:#EFECE6; border:1px solid #DFD9CE; border-radius:8px; padding:8px 12px; margin-top:4px; text-align:center;'>"
                    f"<div style='font-size:11px; color:#6E665E; font-weight:600; text-transform:uppercase;'>Mix</div>"
                    f"<div style='font-size:16px; color:#C85A32; font-weight:700; font-family:monospace;'>{mix_partida:.1f}%</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with cp_mv:
                st.markdown("<div style='padding-top: 26px;'></div>", unsafe_allow_html=True)
                c_ord, c_u, c_d, c_del = st.columns([1.2, 0.9, 0.9, 1.8])
                with c_ord:
                    key_ord_p = f"sel_ord_ppto_{proy_name}_{idx_p}"
                    st.session_state[key_ord_p] = int(idx_p)
                    def _make_on_ord_p(p_curr, k_ord):
                        def _cb_ord():
                            nueva_pos = int(st.session_state.get(k_ord, p_curr))
                            if nueva_pos != p_curr:
                                mover_partida_presupuesto(proy_name, p_curr, nueva_pos, ambito="presupuesto")
                        return _cb_ord
                    st.selectbox(
                        "Orden",
                        options=list(range(1, n_parts_ppto + 1)),
                        format_func=lambda x: f"N° {x}",
                        key=key_ord_p,
                        on_change=_make_on_ord_p(idx_p, key_ord_p),
                        label_visibility="collapsed",
                        help="Seleccionar el número de orden de esta partida",
                    )
                with c_u:
                    if st.button("⬆", key=f"btn_mv_up_p_{proy_name}_{idx_p}", disabled=(idx_p == 1), help="Subir Partida completa", use_container_width=True):
                        mover_partida_presupuesto(proy_name, idx_p, "subir", ambito="presupuesto")
                        st.rerun()
                with c_d:
                    if st.button("⬇", key=f"btn_mv_dn_p_{proy_name}_{idx_p}", disabled=(idx_p == n_parts_ppto), help="Bajar Partida completa", use_container_width=True):
                        mover_partida_presupuesto(proy_name, idx_p, "bajar", ambito="presupuesto")
                        st.rerun()
                with c_del:
                    with st.popover("🗑️ Eliminar", use_container_width=True):
                        if n_parts_ppto <= 1:
                            st.info("El presupuesto debe conservar al menos 1 partida.")
                        else:
                            st.warning(f"¿Eliminar **Partida {idx_p}: {p_nom_limpio}** y sus {len(tareas_list_p)} tarea(s)?")
                            if st.button(
                                "CONFIRMAR",
                                key=f"btn_del_p_{proy_name}_{idx_p}",
                                type="primary",
                                use_container_width=True,
                            ):
                                eliminar_partida_presupuesto(proy_name, idx_p, p_nom_completo, ambito="presupuesto")
                                st.rerun()

            # Construir DataFrame editable para las tareas de esta partida (incluye Especialidad y Contratista para uso interno)
            rows_ed = []
            for pos_t, t_r in enumerate(tareas_list_p, start=1):
                cod_item = f"{idx_p}.{pos_t:02d}"
                desc_t = extraer_descripcion_tarea(t_r.get("descripcion", t_r.get("Tarea", "")), cod_item)
                mon_t = safe_str(t_r.get("moneda", t_r.get("Moneda", "Soles"))) or "Soles"
                if mon_t not in ["Soles", "Dólares"]:
                    mon_t = "Soles"
                und_t = safe_str(t_r.get("unidad", t_r.get("Unidad", "glb"))) or "glb"
                if und_t not in unidades_cat:
                    unidades_cat.append(und_t)
                met_t = float(safe_float(t_r.get("metrado", t_r.get("Metrado", 1.0)), 1.0))
                if met_t <= 0:
                    met_t = 1.0
                vu_t = float(safe_float(t_r.get("valor_unitario", t_r.get("Valor_Unitario", 0.0)), 0.0))
                vp_t = float(safe_float(t_r.get("presupuesto", t_r.get("Presupuesto", 0.0)), 0.0))
                esp_t = safe_str(t_r.get("especialidad", t_r.get("Especialidad", ""))).strip()
                if esp_t == "Ninguna":
                    esp_t = ""
                if esp_t and esp_t not in especialidades_cat:
                    especialidades_cat.append(esp_t)
                con_t = safe_str(t_r.get("contratista", t_r.get("Contratista", ""))).strip()
                if con_t and con_t not in contratistas_cat:
                    contratistas_cat.append(con_t)

                rows_ed.append({
                    "Sel": False,
                    "Item": str(cod_item),
                    "Descripcion": str(desc_t),
                    "Especialidad": str(esp_t),
                    "Contratista": str(con_t),
                    "Moneda": str(mon_t),
                    "Unidad": str(und_t),
                    "Metrado": float(met_t),
                    "Valor_Unitario": float(vu_t),
                    "Valor_Parcial": float(vp_t),
                })

            df_ed_p = pd.DataFrame(rows_ed)
            for c_num in ["Metrado", "Valor_Unitario", "Valor_Parcial"]:
                if c_num in df_ed_p.columns:
                    df_ed_p[c_num] = pd.to_numeric(df_ed_p[c_num], errors="coerce").fillna(0.0).astype(float)

            prev_base = st.session_state.get(base_ppto_key)
            if (
                st.session_state.get(sel_ver_key) == c_ppto_val
                and isinstance(prev_base, pd.DataFrame)
                and len(prev_base) == len(df_ed_p)
                and "Sel" in prev_base.columns
            ):
                base_sel = [bool(v) for v in prev_base["Sel"].tolist()]
            else:
                saved_sel = {int(i) for i in st.session_state.get(sel_saved_key, []) if 0 <= int(i) < len(df_ed_p)}
                base_sel = [i in saved_sel for i in range(len(df_ed_p))]
                st.session_state[sel_ver_key] = c_ppto_val

            df_ed_p["Sel"] = pd.Series(base_sel, index=df_ed_p.index, dtype=bool)
            st.session_state[base_ppto_key] = df_ed_p.copy()

            eff_sel = list(base_sel)
            ed_state = st.session_state.get(w_ppto_key)
            if isinstance(ed_state, dict):
                for r_s, ch in ed_state.get("edited_rows", {}).items():
                    try:
                        r_idx = int(r_s)
                        if 0 <= r_idx < len(eff_sel) and isinstance(ch, dict) and "Sel" in ch:
                            eff_sel[r_idx] = bool(ch["Sel"])
                    except (TypeError, ValueError):
                        pass
            selected_indices = [i for i, checked in enumerate(eff_sel) if checked]

            if rows_ed and len(selected_indices) > 0:
              with st.container(border=True):
                n_sel_t = len(selected_indices)
                sel_set_t = set(selected_indices)
                can_move_up_t = (
                    n_sel_t > 0
                    and len(rows_ed) > 1
                    and any((i - 1) >= 0 and (i - 1) not in sel_set_t for i in selected_indices)
                )
                can_move_dn_t = (
                    n_sel_t > 0
                    and len(rows_ed) > 1
                    and any((i + 1) < len(rows_ed) and (i + 1) not in sel_set_t for i in selected_indices)
                )

                col_act_info, col_act_u, col_act_d, col_act_del, col_act_cls = st.columns([4.4, 1.5, 1.5, 1.6, 1.0])
                with col_act_info:
                    lbl_sel = (
                        f"☑ {n_sel_t} tarea(s) seleccionada(s)"
                        if n_sel_t > 0
                        else "☐ Marca casillas (☑) en las tareas para moverlas o borrarlas"
                    )
                    color_sel = "#C85A32" if n_sel_t > 0 else "#6E665E"
                    st.markdown(
                        f"<div class='cota-floating-task-window' style='font-size:12.5px; font-weight:700; color:{color_sel}; padding-top:6px;'>🛠️ Acciones de Tarea · {lbl_sel}</div>",
                        unsafe_allow_html=True,
                    )
                with col_act_cls:
                    if st.button("✖", key=f"btn_cls_t_{proy_name}_{idx_p}", use_container_width=True, help="Deseleccionar y cerrar ventana flotante"):
                        st.session_state[sel_saved_key] = []
                        if base_ppto_key in st.session_state:
                            del st.session_state[base_ppto_key]
                        st.session_state[c_ppto_key] = c_ppto_val + 1
                        st.rerun()
                with col_act_u:
                    if st.button(
                        "⬆ Subir",
                        key=f"btn_up_t_{proy_name}_{idx_p}",
                        disabled=not can_move_up_t,
                        use_container_width=True,
                        help="Sube la(s) tarea(s) seleccionada(s) una posición",
                    ):
                        movido, nuevos_idx = mover_tareas_seleccionadas_presupuesto(
                            proy_name, idx_p, p_nom_completo, selected_indices, "subir", ambito="presupuesto"
                        )
                        if movido:
                            st.session_state[sel_saved_key] = nuevos_idx
                            if base_ppto_key in st.session_state:
                                del st.session_state[base_ppto_key]
                            st.session_state[c_ppto_key] = c_ppto_val + 1
                            st.rerun()
                with col_act_d:
                    if st.button(
                        "⬇ Bajar",
                        key=f"btn_dn_t_{proy_name}_{idx_p}",
                        disabled=not can_move_dn_t,
                        use_container_width=True,
                        help="Baja la(s) tarea(s) seleccionada(s) una posición",
                    ):
                        movido, nuevos_idx = mover_tareas_seleccionadas_presupuesto(
                            proy_name, idx_p, p_nom_completo, selected_indices, "bajar", ambito="presupuesto"
                        )
                        if movido:
                            st.session_state[sel_saved_key] = nuevos_idx
                            if base_ppto_key in st.session_state:
                                del st.session_state[base_ppto_key]
                            st.session_state[c_ppto_key] = c_ppto_val + 1
                            st.rerun()
                with col_act_del:
                    if st.button(
                        "🗑️ Borrar",
                        key=f"btn_del_t_{proy_name}_{idx_p}",
                        disabled=(n_sel_t == 0),
                        use_container_width=True,
                        help="Elimina la(s) tarea(s) seleccionada(s) y renumera las restantes",
                    ):
                        if eliminar_tareas_seleccionadas_presupuesto(
                            proy_name, idx_p, p_nom_completo, selected_indices, ambito="presupuesto"
                        ):
                            st.session_state[sel_saved_key] = []
                            if base_ppto_key in st.session_state:
                                del st.session_state[base_ppto_key]
                            st.session_state[c_ppto_key] = c_ppto_val + 1
                            st.rerun()

            st.data_editor(
                st.session_state[base_ppto_key],
                use_container_width=True,
                hide_index=True,
                num_rows="fixed",
                disabled=["Item", "Valor_Parcial"],
                column_order=[
                    "Sel",
                    "Item",
                    "Descripcion",
                    "Especialidad",
                    "Contratista",
                    "Moneda",
                    "Unidad",
                    "Metrado",
                    "Valor_Unitario",
                    "Valor_Parcial",
                ],
                key=w_ppto_key,
                column_config={
                    "Sel": st.column_config.CheckboxColumn(
                        "☑",
                        default=False,
                        width=48,
                        help="Selecciona una o varias tareas para moverlas o borrarlas",
                    ),
                    "Item": st.column_config.TextColumn("Ítem", width="small", disabled=True),
                    "Descripcion": st.column_config.TextColumn("Descripción de la Tarea / Sub-partida", width="large"),
                    "Especialidad": st.column_config.SelectboxColumn(
                        "Especialidad 🔒",
                        options=especialidades_cat,
                        width="small",
                        help="Uso interno (conecta con 05. Partidas y 06. Pagos). No se exporta al Excel del cliente.",
                    ),
                    "Contratista": st.column_config.SelectboxColumn(
                        "Contratista 🔒",
                        options=contratistas_cat,
                        width="small",
                        help="Uso interno (conecta con 05. Partidas y 06. Pagos). No se exporta al Excel del cliente.",
                    ),
                    "Moneda": st.column_config.SelectboxColumn("Moneda", options=["Soles", "Dólares"], width="small", required=True),
                    "Unidad": st.column_config.SelectboxColumn("Unidad", options=unidades_cat, width="small", required=True),
                    "Metrado": st.column_config.NumberColumn("Metrado", min_value=0.01, step=0.01, format="%.2f", width="small", required=True),
                    "Valor_Unitario": st.column_config.NumberColumn("Valor Unitario", min_value=0.0, step=0.01, format="%.2f", width="medium", required=True),
                    "Valor_Parcial": st.column_config.NumberColumn("Valor Parcial (S/.)", format="S/ %.2f", width="medium"),
                },
                on_change=aplicar_edicion_tabla_presupuesto_partida,
                args=(
                    base_ppto_key,
                    w_ppto_key,
                    proy_name,
                    idx_p,
                    p_nom_completo,
                    "presupuesto",
                ),
            )

            st.caption("🔒 *Especialidad y Contratista son internos (no se exportan al cliente).*")

    # Cuadro Resumen de Cierre del Presupuesto + Exportación a Excel
    st.divider()
    st.markdown("#### 📊 CUADRO DE CIERRE DEL PRESUPUESTO")
    st.caption("Resumen ejecutivo alineado al 100% con las partidas, gastos generales, gestión/supervisión, IGV y tipo de cambio configurados arriba.")

    resumen_rows.extend([
        {
            "Ítem": "",
            "Descripción": "SUB TOTAL (Costo Directo / Casco)",
            "Moneda": "Soles",
            "Factor": "",
            "Importe_Fmt": format_currency(totales["subtotal_casco"]),
            "Mix": "100.0%" if totales["subtotal_casco"] > 0 else "0.0%",
            "Tipo_Fila": "subtotal",
        },
        {
            "Ítem": "",
            "Descripción": "Gastos Generales",
            "Moneda": "Soles",
            "Factor": (f"Monto fijo" if totales.get("modo_gg") == "monto" else f"{totales['gg_pct']:g}%"),
            "Importe_Fmt": format_currency(totales["gg_monto"]),
            "Mix": f"{totales['gg_pct']:.1f}%" if totales["subtotal_casco"] > 0 else "",
            "Tipo_Fila": "cargo",
        },
        {
            "Ítem": "",
            "Descripción": "Gestión y Supervisión de Obras (Utilidades)",
            "Moneda": "Soles",
            "Factor": (f"Monto fijo" if totales.get("modo_util") == "monto" else f"{totales['utilidades_pct']:g}%"),
            "Importe_Fmt": format_currency(totales["utilidades_monto"]),
            "Mix": f"{totales['utilidades_pct']:.1f}%" if totales["subtotal_casco"] > 0 else "",
            "Tipo_Fila": "cargo",
        },
        {
            "Ítem": "",
            "Descripción": "IGV (Impuesto General a las Ventas)",
            "Moneda": "Soles",
            "Factor": "18%" if totales["incluir_igv"] else "0%",
            "Importe_Fmt": format_currency(totales["igv_monto"]),
            "Mix": "",
            "Tipo_Fila": "cargo",
        },
        {
            "Ítem": "",
            "Descripción": "TOTAL PRESUPUESTO (SOLES)",
            "Moneda": "Soles",
            "Factor": "",
            "Importe_Fmt": format_currency(totales["presupuesto_total"]),
            "Mix": f"{(totales['presupuesto_total'] / totales['subtotal_casco'] * 100.0):.1f}%" if totales["subtotal_casco"] > 0 else "0.0%",
            "Tipo_Fila": "total_soles",
        },
        {
            "Ítem": "",
            "Descripción": "TOTAL PRESUPUESTO (DÓLARES USD)",
            "Moneda": "Dólares",
            "Factor": f"TC: {totales['tc']:.2f}",
            "Importe_Fmt": f"US$ {totales['presupuesto_dolares']:,.2f}",
            "Mix": "",
            "Tipo_Fila": "total_usd",
        },
    ])

    trs_cierre_html = []
    for r_c in resumen_rows:
        t_fila = r_c.get("Tipo_Fila", "partida")
        if t_fila == "subtotal":
            row_style = "background:#EFECE6; font-weight:700; border-top:2px solid #262320; border-bottom:1px solid #DFD9CE; color:#262320;"
        elif t_fila == "total_soles":
            row_style = "background:#262320; color:#FFFFFF; font-weight:700; font-size:14px; border-top:2px solid #262320;"
        elif t_fila == "total_usd":
            row_style = "background:#FAF8F5; color:#C85A32; font-weight:700; font-size:13.5px; border-top:1px solid #DFD9CE;"
        elif t_fila == "cargo":
            row_style = "background:#FAF8F5; color:#4A453F; border-bottom:1px solid #EFECE6;"
        else:
            row_style = "background:#FFFFFF; color:#262320; border-bottom:1px solid #EFECE6;"

        imp_color = "#FFFFFF" if t_fila == "total_soles" else ("#C85A32" if t_fila == "total_usd" else "#262320")
        trs_cierre_html.append(
            f"<tr style='{row_style}'>"
            f"<td style='padding:9px 12px; text-align:center; font-family:monospace; width:60px;'>{r_c['Ítem']}</td>"
            f"<td style='padding:9px 12px; text-align:left;'>{r_c['Descripción']}</td>"
            f"<td style='padding:9px 12px; text-align:center; width:95px;'>{r_c['Moneda']}</td>"
            f"<td style='padding:9px 12px; text-align:center; font-family:monospace; width:100px;'>{r_c['Factor']}</td>"
            f"<td style='padding:9px 14px; text-align:right; font-family:monospace; font-weight:700; color:{imp_color}; width:170px;'>{r_c['Importe_Fmt']}</td>"
            f"<td style='padding:9px 12px; text-align:right; font-family:monospace; width:90px;'>{r_c['Mix']}</td>"
            f"</tr>"
        )

    tabla_cierre_html = (
        "<div style='border:1px solid #DFD9CE; border-radius:10px; overflow:hidden; margin-bottom:16px; box-shadow:0 2px 6px rgba(38,35,32,0.04);'>"
        "<table style='width:100%; border-collapse:collapse; font-size:13px;'>"
        "<thead>"
        "<tr style='background:#F0ECE1; color:#6E665E; text-transform:uppercase; font-size:11px; letter-spacing:0.5px; border-bottom:2px solid #DFD9CE;'>"
        "<th style='padding:10px 12px; text-align:center;'>Ítem</th>"
        "<th style='padding:10px 12px; text-align:left;'>Concepto / Partida</th>"
        "<th style='padding:10px 12px; text-align:center;'>Moneda</th>"
        "<th style='padding:10px 12px; text-align:center;'>% / TC</th>"
        "<th style='padding:10px 14px; text-align:right;'>Importe</th>"
        "<th style='padding:10px 12px; text-align:right;'>Mix (%)</th>"
        "</tr>"
        "</thead>"
        f"<tbody>{''.join(trs_cierre_html)}</tbody>"
        "</table>"
        "</div>"
    )
    st.markdown(tabla_cierre_html, unsafe_allow_html=True)

    # Módulo de Notas y Condiciones debajo del Presupuesto (Personalizadas + Predeterminados)
    notas_ppto_activas = obtener_notas_presupuesto_proyecto(proy_name)
    presets_notas_ppto = obtener_notas_predeterminadas_presupuesto()

    if notas_ppto_activas:
        items_notas_html = "".join(
            f"<li style='margin-bottom:4px; color:#262320; font-size:13px; line-height:1.45;'>{html_lib.escape(n_txt)}</li>"
            for n_txt in notas_ppto_activas
        )
        st.markdown(
            f"<div style='background:#FAF8F5; border:1px solid #DFD9CE; border-left:4px solid #C85A32; border-radius:9px; padding:12px 16px; margin-top:-4px; margin-bottom:14px;'>"
            f"<div style='font-size:11.5px; font-weight:800; color:#262320; text-transform:uppercase; letter-spacing:0.4px; margin-bottom:6px;'>📌 NOTAS Y CONDICIONES DEL PRESUPUESTO</div>"
            f"<ul style='margin:0; padding-left:18px;'>{items_notas_html}</ul>"
            f"</div>",
            unsafe_allow_html=True,
        )

    with st.expander("📝 NOTAS DEL PRESUPUESTO — Escribir nota personalizada o usar predeterminados", expanded=True):
        c_np_left, c_np_right = st.columns([5.4, 4.6])
        rst_np_cnt = st.session_state.get(f"rst_np_in_{proy_name}", 0)
        with c_np_left:
            st.markdown("###### ✍️ Agregar Nota Personalizada")
            nueva_nota_txt = st.text_input(
                "Escribe la nota para este presupuesto:",
                placeholder="Ej: El metraje se ajustará al real en obra.",
                key=f"in_nueva_nota_ppto_{proy_name}_{rst_np_cnt}",
            )
            b_np1, b_np2 = st.columns([1.0, 1.35])
            with b_np1:
                if st.button("➕ Agregar al Presupuesto", key=f"btn_add_np_{proy_name}", use_container_width=True, type="primary"):
                    if nueva_nota_txt and nueva_nota_txt.strip():
                        agregar_nota_presupuesto_proyecto(proy_name, nueva_nota_txt.strip(), guardar_como_predeterminado=False)
                        st.session_state[f"rst_np_in_{proy_name}"] = rst_np_cnt + 1
                        st.rerun()
            with b_np2:
                if st.button("⭐ Agregar y Guardar Predeterminado", key=f"btn_add_save_np_{proy_name}", use_container_width=True):
                    if nueva_nota_txt and nueva_nota_txt.strip():
                        agregar_nota_presupuesto_proyecto(proy_name, nueva_nota_txt.strip(), guardar_como_predeterminado=True)
                        st.session_state[f"rst_np_in_{proy_name}"] = rst_np_cnt + 1
                        st.rerun()

            if notas_ppto_activas:
                st.markdown("<div style='margin-top:8px; font-size:12px; font-weight:700; color:#6E665E;'>Notas activas en este presupuesto:</div>", unsafe_allow_html=True)
                for i_na, txt_na in enumerate(notas_ppto_activas):
                    cn_txt, cn_del = st.columns([8.8, 1.2])
                    with cn_txt:
                        st.markdown(f"<div style='font-size:12.5px; color:#262320; padding:4px 0;'>• {html_lib.escape(txt_na)}</div>", unsafe_allow_html=True)
                    with cn_del:
                        if st.button("🗑️", key=f"btn_del_np_act_{proy_name}_{i_na}", help="Quitar esta nota del presupuesto", use_container_width=True):
                            eliminar_nota_presupuesto_proyecto(proy_name, i_na)
                            st.rerun()

        with c_np_right:
            st.markdown("###### ⭐ Notas Predeterminadas Guardadas")
            st.caption("Haz clic en **➕ Usar** para insertar una nota predeterminada en este presupuesto.")
            activas_low = {x.lower() for x in notas_ppto_activas}
            for i_pr, txt_pr in enumerate(presets_notas_ppto):
                ya_esta = txt_pr.lower() in activas_low
                cp_txt, cp_use, cp_rm = st.columns([6.8, 2.0, 1.2])
                with cp_txt:
                    st.markdown(f"<div style='font-size:12px; color:#262320; padding:4px 0;'>• {html_lib.escape(txt_pr)}</div>", unsafe_allow_html=True)
                with cp_use:
                    if st.button(
                        "✅ En uso" if ya_esta else "➕ Usar",
                        key=f"btn_use_preset_np_{proy_name}_{i_pr}",
                        disabled=ya_esta,
                        use_container_width=True,
                    ):
                        agregar_nota_presupuesto_proyecto(proy_name, txt_pr, guardar_como_predeterminado=False)
                        st.rerun()
                with cp_rm:
                    if st.button("🗑️", key=f"btn_rm_preset_np_{proy_name}_{i_pr}", help="Eliminar de predeterminados", use_container_width=True):
                        eliminar_nota_predeterminada_presupuesto(txt_pr)
                        st.rerun()

    col_bot_exp1, col_bot_exp2, col_bot_exp3 = st.columns([3.3, 3.2, 3.5])
    with col_bot_exp1:
        st.download_button(
            "📥 EXPORTAR PRESUPUESTO A EXCEL (.XLSX) PARA EL CLIENTE",
            data=xlsx_export_bytes,
            file_name=f"Presupuesto_{safe_fn_p}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
            key=f"btn_exp_excel_bot_{proy_name}",
        )
    with col_bot_exp2:
        st.download_button(
            "📄 EXPORTAR PRESUPUESTO A PDF (.PDF)",
            data=pdf_export_bytes,
            file_name=f"Presupuesto_{safe_fn_p}.pdf",
            mime="application/pdf",
            use_container_width=True,
            key=f"btn_exp_pdf_bot_{proy_name}",
        )
    with col_bot_exp3:
        st.info("✅ **Sincronizado en tiempo real:** Las partidas, tareas, contratistas y montos están conectados con **05. PARTIDAS Y TAREAS** y **06. COBROS & FINANZAS**.")


def _render_tab_entregables(proy_name, proy_data):
    """Pestaña 4: Control de Planos, 3D Renders y Entregables Técnicos."""
    st.markdown("### 📋 ENTREGABLES, PLANOS Y REVISIONES")
    st.caption("Seguimiento del paquete de planos técnicos, modelos 3D y especificaciones del proyecto.")

    col_btn1, _ = st.columns([3, 7])
    with col_btn1:
        with st.popover("➕ REGISTRAR NUEVO ENTREGABLE", use_container_width=True):
            with st.form(f"f_new_ent_{proy_name}", clear_on_submit=True):
                e_esp = st.selectbox("Especialidad", ESPECIALIDADES_DEFAULT)
                e_nom = st.text_input("Nombre del Plano / Documento", placeholder="")
                col_r1, col_r2 = st.columns(2)
                e_rev = col_r1.text_input("Revisión", value="Rev 0")
                e_est = col_r2.selectbox("Estado", ["En desarrollo", "En revisión", "Aprobado", "Observado"])
                col_f1, col_f2 = st.columns(2)
                e_flim = col_f1.date_input("Fecha Límite", value=datetime.date.today())
                e_resp = col_f2.text_input("Responsable")
                e_link = st.text_input("Enlace a Drive / Dropbox / PDF")

                if st.form_submit_button("CREAR ENTREGABLE") and e_nom:
                    n_row = pd.DataFrame([{
                        'ID': f"ENT_{int(datetime.datetime.now().timestamp())}_{uuid.uuid4().hex[:6]}",
                        'Proyecto': proy_name,
                        'Especialidad': e_esp,
                        'Nombre_Entregable': e_nom,
                        'Revision': e_rev,
                        'Estado': e_est,
                        'Fecha_Limite': e_flim.strftime("%d/%m/%Y"),
                        'Responsable': e_resp,
                        'Fase': "Expediente Técnico",
                        'Link': e_link
                    }])
                    st.session_state.entregables_planos = pd.concat([st.session_state.entregables_planos, n_row[COLS_ENTREGABLES]], ignore_index=True)
                    clear_base_dfs()
                    st.rerun()

    df_ent = st.session_state.entregables_planos[st.session_state.entregables_planos['Proyecto'] == proy_name].copy()

    tot_ent = len(df_ent)
    n_aprob = len(df_ent[df_ent['Estado'] == 'Aprobado']) if not df_ent.empty else 0
    n_rev = len(df_ent[df_ent['Estado'].isin(['En desarrollo', 'En revisión'])]) if not df_ent.empty else 0
    n_obs = len(df_ent[df_ent['Estado'] == 'Observado']) if not df_ent.empty else 0

    ek1, ek2, ek3, ek4 = st.columns(4)
    with ek1:
        render_metric_card("Total Entregables", str(tot_ent), "Expediente del proyecto")
    with ek2:
        render_metric_card("Aprobados", str(n_aprob), f"{(n_aprob/tot_ent*100 if tot_ent>0 else 0):.0f}% validado", border_color="#4A7C59", text_color="#4A7C59")
    with ek3:
        render_metric_card("En Desarrollo / Rev.", str(n_rev), "En producción técnica", border_color="#D98A2B", text_color="#D98A2B")
    with ek4:
        render_metric_card("Observados", str(n_obs), "Requieren levantamiento", border_color="#C93B2B", text_color="#C93B2B")

    st.divider()

    base_ent_key = f"base_df_ent_{proy_name}"
    counter_key = f"c_{base_ent_key}"
    c_val = st.session_state.get(counter_key, 0)
    w_key = f"ed_ent_{proy_name}_{c_val}"

    display_ent = df_ent[['ID', 'Especialidad', 'Nombre_Entregable', 'Revision', 'Estado', 'Fecha_Limite', 'Responsable', 'Link']].copy() if not df_ent.empty else pd.DataFrame(columns=['ID', 'Especialidad', 'Nombre_Entregable', 'Revision', 'Estado', 'Fecha_Limite', 'Responsable', 'Link'])
    display_ent['Fecha_Limite'] = display_ent['Fecha_Limite'].apply(lambda x: parse_date(x))

    if base_ent_key not in st.session_state:
        st.session_state[base_ent_key] = display_ent.copy()

    st.data_editor(
        st.session_state[base_ent_key],
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key=w_key,
        column_config={
            "ID": None,
            "Especialidad": st.column_config.SelectboxColumn("Especialidad", options=ESPECIALIDADES_DEFAULT),
            "Nombre_Entregable": st.column_config.TextColumn("Entregable / Código de Plano", width="large", required=True),
            "Revision": st.column_config.TextColumn("Revisión", width="small"),
            "Estado": st.column_config.SelectboxColumn("Estado", options=["En desarrollo", "En revisión", "Aprobado", "Observado"]),
            "Fecha_Limite": st.column_config.DateColumn("Fecha Límite", format="DD/MM/YYYY"),
            "Responsable": st.column_config.TextColumn("Responsable"),
            "Link": st.column_config.LinkColumn("Enlace de Descarga / Nube")
        },
        on_change=on_table_edit,
        args=(
            base_ent_key,
            w_key,
            'entregables_planos',
            ['Proyecto'],
            [proy_name],
            ['Fecha_Limite'],
            ['Especialidad', 'Nombre_Entregable', 'Revision', 'Estado', 'Responsable', 'Link'],
            None,
            None,
            'ID'
        )
    )


def _render_tab_obra(proy_name, proy_data):
    """Pestaña 5: Partidas y Tareas (Sincronizada con 03. Presupuesto, con Cronograma Gantt y Rango Rápido de Fechas)."""
    st.markdown("### 🏗️ 05. PARTIDAS Y TAREAS")
    st.markdown(
        """
        <style>
        div[data-testid="stTextInput"]:has(input[aria-label^="OBRA_DATE_BRIDGE_"]) {
            position: absolute !important;
            width: 1px !important;
            height: 1px !important;
            opacity: 0 !important;
            overflow: hidden !important;
            pointer-events: none !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        "Control operativo de contratistas, cronograma Gantt de obra y supervisión por partida. "
        "Las partidas y tareas mantienen exactamente el mismo orden que en **03. PRESUPUESTO**."
    )

    col_ap1, col_ap2, col_ap3 = st.columns([2.8, 3.4, 3.8])
    with col_ap1:
        with st.popover("➕ AGREGAR PARTIDA DE OBRA", use_container_width=True):
            with st.form(f"f_new_part_{proy_name}", clear_on_submit=True):
                n_pa = st.text_input("Código / Nombre de Partida")
                n_pac = st.number_input("Presupuesto Pactado Contratista (S/)", value=0.0)
                if st.form_submit_button("CREAR PARTIDA") and n_pa:
                    st.session_state.partidas = pd.concat([st.session_state.partidas, pd.DataFrame([{'Proyecto': proy_name, 'Nombre_Partida': n_pa}])], ignore_index=True)
                    st.session_state.p_info = pd.concat([st.session_state.p_info, pd.DataFrame([{'Proyecto': proy_name, 'Nombre_Partida': n_pa, 'Monto_Pactado': float(n_pac)}])], ignore_index=True)
                    clear_base_dfs()
                    st.rerun()

    with col_ap2:
        if st.button("🔄 SINCRONIZAR CON 03. PRESUPUESTO", key=f"btn_sync_obra_ppto_{proy_name}", use_container_width=True, help="Integra las partidas y montos de 03. Presupuesto aquí sin borrar tus estados En Proceso / Completado ni fechas."):
            res_int_o = integrar_presupuesto_con_gestion(proy_name, incluir_obra=True, incluir_pagos=False)
            clear_base_dfs()
            st.toast(
                f"✅ Integrado con 03. Presupuesto: +{res_int_o['partidas_agregadas']} part., "
                f"+{res_int_o['tareas_agregadas']} tar. ({res_int_o['avances_conservados']} avances conservados).",
                icon="✅",
            )
            st.rerun()

    # Ordenar las partidas estrictamente por su prefijo numérico (1., 2., 3...) para mantener el orden de 03. Presupuesto
    parts_proy = st.session_state.partidas[st.session_state.partidas['Proyecto'] == proy_name].copy()
    if parts_proy.empty:
        st.info("No hay partidas registradas para este proyecto. Configura tus partidas en **03. PRESUPUESTO** o crea una arriba.")
        return

    def _orden_partida_num(nom_p: str) -> tuple:
        s_p = str(nom_p or "").strip()
        import re as _re
        m_p = _re.match(r"^(\d+)", s_p)
        if m_p:
            return (0, int(m_p.group(1)), s_p)
        return (1, 999999, s_p)

    parts_proy["_sort_key"] = parts_proy["Nombre_Partida"].apply(_orden_partida_num)
    parts_proy = parts_proy.sort_values(by="_sort_key", kind="mergesort").drop(columns=["_sort_key"])

    # Cronograma Gantt Interactivo de Tareas (Inicio a Fin y Estados)
    df_all_t_proy = st.session_state.tasks[st.session_state.tasks["Proyecto"] == proy_name].copy() if "tasks" in st.session_state else pd.DataFrame()
    with col_ap3:
        if not df_all_t_proy.empty:
            sin_fecha_mask = df_all_t_proy["Inicio"].apply(lambda x: parse_date(x) is None) | df_all_t_proy["Fin"].apply(lambda x: parse_date(x) is None)
            n_sin_fecha = int(sin_fecha_mask.sum())
            if n_sin_fecha > 0:
                if st.button(f"📅 Auto-asignar fechas a {n_sin_fecha} tarea(s) para el Gantt", key=f"btn_autofechas_{proy_name}", use_container_width=True):
                    f_base = parse_date(proy_data.get("Inicio")) or datetime.date.today()
                    offset_d = 0
                    for idx_t_g in df_all_t_proy.index:
                        d_i_cur = parse_date(st.session_state.tasks.at[idx_t_g, "Inicio"])
                        d_f_cur = parse_date(st.session_state.tasks.at[idx_t_g, "Fin"])
                        if d_i_cur is None:
                            d_i_cur = f_base + datetime.timedelta(days=offset_d)
                            st.session_state.tasks.at[idx_t_g, "Inicio"] = d_i_cur.strftime("%d/%m/%Y")
                            offset_d += 3
                        if d_f_cur is None or d_f_cur < d_i_cur:
                            d_f_cur = d_i_cur + datetime.timedelta(days=4)
                            st.session_state.tasks.at[idx_t_g, "Fin"] = d_f_cur.strftime("%d/%m/%Y")
                    clear_base_dfs()
                    st.rerun()


    with st.expander("📊 CRONOGRAMA GANTT POR PARTIDA Y TAREAS (INICIO → FIN Y ESTADOS)", expanded=False):
        if not df_all_t_proy.empty:
            df_gantt_raw = df_all_t_proy.copy()
            df_gantt_raw["Inicio_DT"] = df_gantt_raw["Inicio"].apply(lambda x: pd.to_datetime(parse_date(x)))
            df_gantt_raw["Fin_DT"] = df_gantt_raw["Fin"].apply(lambda x: pd.to_datetime(parse_date(x)))
            df_gantt_raw = df_gantt_raw.dropna(subset=["Inicio_DT", "Fin_DT"]).copy()

            if not df_gantt_raw.empty:
                mask_eq = df_gantt_raw["Inicio_DT"].dt.date == df_gantt_raw["Fin_DT"].dt.date
                df_gantt_raw.loc[mask_eq, "Fin_DT"] = df_gantt_raw["Fin_DT"] + datetime.timedelta(days=1)
                df_gantt_raw["Duracion_Dias"] = (df_gantt_raw["Fin_DT"] - df_gantt_raw["Inicio_DT"]).dt.days.clip(lower=1)

                paleta_partidas = [
                    "#C85A32",
                    "#2B6CB0",
                    "#4A7C59",
                    "#D98A2B",
                    "#7B4B94",
                    "#1D7874",
                    "#9C4221",
                    "#4C51BF",
                ]
                orden_partidas_lista = parts_proy["Nombre_Partida"].dropna().astype(str).tolist()
                for p_ex in df_gantt_raw["Partida"].dropna().astype(str).unique().tolist():
                    if p_ex not in orden_partidas_lista:
                        orden_partidas_lista.append(p_ex)

                mapa_color_partida = {
                    p_n: paleta_partidas[i_c % len(paleta_partidas)]
                    for i_c, p_n in enumerate(orden_partidas_lista)
                }

                filas_gantt_estructuradas = []
                separadores_y = []
                chips_leyenda_partidas = []
                orden_row = 0

                for i_part_g, p_nom_g in enumerate(orden_partidas_lista, start=1):
                    df_p_sub = df_gantt_raw[df_gantt_raw["Partida"].astype(str) == p_nom_g].copy()
                    if df_p_sub.empty:
                        continue

                    color_p = mapa_color_partida.get(p_nom_g, "#C85A32")
                    p_limpio_g = limpiar_nombre_partida(p_nom_g, i_part_g)
                    p_grupo_lbl = f"P{i_part_g}: {p_limpio_g}"

                    ini_min_p = df_p_sub["Inicio_DT"].min()
                    fin_max_p = df_p_sub["Fin_DT"].max()
                    dur_total_p = max(1, int((fin_max_p - ini_min_p).days))
                    etiqueta_cabecera = f"■ PARTIDA {i_part_g}: {p_limpio_g.upper()}"[:56]

                    if orden_row > 0:
                        separadores_y.append(etiqueta_cabecera)

                    chips_leyenda_partidas.append(
                        f"<span style='display:inline-flex; align-items:center; gap:6px; background:#FFFFFF; border:1px solid #DFD9CE; "
                        f"border-left:5px solid {color_p}; border-radius:6px; padding:4px 10px; font-size:12px; font-weight:600; color:#262320;'>"
                        f"<span style='width:10px; height:10px; border-radius:2px; background:{color_p}; display:inline-block;'></span>"
                        f"{html_lib.escape(f'{i_part_g}. {p_limpio_g}')} "
                        f"<span style='font-size:11px; color:#6E665E; font-weight:500;'>({len(df_p_sub)} tarea{'s' if len(df_p_sub) != 1 else ''})</span>"
                        f"</span>"
                    )

                    # Barra resumen de toda la Partida
                    filas_gantt_estructuradas.append({
                        "Orden_Gantt": orden_row,
                        "Etiqueta_Y": etiqueta_cabecera,
                        "Partida_Grupo": p_grupo_lbl,
                        "Partida": p_nom_g,
                        "Tarea": f"RESUMEN {p_nom_g}",
                        "Contratista": "—",
                        "Estado": "Resumen de Partida",
                        "Inicio": ini_min_p.strftime("%d/%m/%Y"),
                        "Fin": fin_max_p.strftime("%d/%m/%Y"),
                        "Inicio_DT": ini_min_p,
                        "Fin_DT": fin_max_p,
                        "Duracion_Dias": dur_total_p,
                        "Es_Cabecera": True,
                        "Opacidad": 1.0,
                        "Texto_Barra": f"● {ini_min_p.strftime('%d/%m')} → {fin_max_p.strftime('%d/%m')} ({dur_total_p}d total)",
                    })
                    orden_row += 1

                    # Barras de cada Tarea perteneciente a esta Partida
                    for pos_sub_t, (_, r_gt) in enumerate(df_p_sub.iterrows(), start=1):
                        cod_g = safe_str(r_gt.get("Codigo_Item", "")).strip() or f"{i_part_g}.{pos_sub_t:02d}"
                        desc_g = extraer_descripcion_tarea(r_gt.get("Tarea", ""), cod_g)
                        est_g = safe_str(r_gt.get("Estado", "⏳ Planificado")).strip() or "⏳ Planificado"
                        icono_est = est_g.split(" ")[0] if " " in est_g else "•"
                        etiqueta_t = f"   ↳ {cod_g} {desc_g}"[:54]
                        # Evitar colisión si dos tareas tienen exactamente el mismo nombre
                        while any(f_prev["Etiqueta_Y"] == etiqueta_t for f_prev in filas_gantt_estructuradas):
                            etiqueta_t = etiqueta_t + " "

                        ini_t_dt = r_gt["Inicio_DT"]
                        fin_t_dt = r_gt["Fin_DT"]
                        dur_t_d = int(r_gt["Duracion_Dias"])
                        contra_g = safe_str(r_gt.get("Contratista", "")).strip() or "Sin asignar"

                        filas_gantt_estructuradas.append({
                            "Orden_Gantt": orden_row,
                            "Etiqueta_Y": etiqueta_t,
                            "Partida_Grupo": p_grupo_lbl,
                            "Partida": p_nom_g,
                            "Tarea": f"{cod_g} - {desc_g}",
                            "Contratista": contra_g,
                            "Estado": est_g,
                            "Inicio": ini_t_dt.strftime("%d/%m/%Y"),
                            "Fin": fin_t_dt.strftime("%d/%m/%Y"),
                            "Inicio_DT": ini_t_dt,
                            "Fin_DT": fin_t_dt,
                            "Duracion_Dias": dur_t_d,
                            "Es_Cabecera": False,
                            "Opacidad": 0.78,
                            "Texto_Barra": f"{est_g} · {ini_t_dt.strftime('%d/%m')}→{fin_t_dt.strftime('%d/%m')} ({dur_t_d}d)",
                        })
                        orden_row += 1

                # Leyenda clara en HTML (Partidas por Color + Estados de Ejecución)
                html_leyenda_gantt = (
                    "<div style='background:#FAF8F5; border:1px solid #DFD9CE; border-radius:10px; padding:10px 14px; margin-bottom:10px;'>"
                    "  <div style='display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:10px; margin-bottom:8px;'>"
                    "    <div style='font-size:11.5px; font-weight:700; color:#262320; text-transform:uppercase; letter-spacing:0.4px;'>"
                    "      🎨 Leyenda de Partidas (Color por Partida):"
                    "    </div>"
                    "    <div style='display:flex; flex-wrap:wrap; align-items:center; gap:10px; font-size:11.5px; color:#4A453E; background:#EFECE6; padding:4px 10px; border-radius:6px;'>"
                    "      <span><b>Estados en barra:</b></span>"
                    "      <span>⏳ Planificado</span>"
                    "      <span>🔨 En Proceso</span>"
                    "      <span>✅ Completado</span>"
                    "      <span>⚠️ Retrasado</span>"
                    "      <span style='color:#6E665E;'>|</span>"
                    "      <span><b>■</b> Barra intensa = Duración total de la Partida</span>"
                    "      <span><b>↳</b> Barra clara = Tarea individual</span>"
                    "    </div>"
                    "  </div>"
                    f"  <div style='display:flex; flex-wrap:wrap; gap:8px;'>{''.join(chips_leyenda_partidas)}</div>"
                    "</div>"
                )
                st.markdown(html_leyenda_gantt, unsafe_allow_html=True)

                df_gantt_plot = pd.DataFrame(filas_gantt_estructuradas)
                dominio_grupos = list(dict.fromkeys(df_gantt_plot["Partida_Grupo"].tolist()))
                rango_colores = [
                    mapa_color_partida.get(
                        df_gantt_plot[df_gantt_plot["Partida_Grupo"] == g]["Partida"].iloc[0],
                        "#C85A32",
                    )
                    for g in dominio_grupos
                ]
                escala_color_partidas = alt.Scale(domain=dominio_grupos, range=rango_colores)
                orden_etiquetas_y = df_gantt_plot.sort_values("Orden_Gantt")["Etiqueta_Y"].tolist()

                alto_gantt = max(250, min(820, len(df_gantt_plot) * 30 + 55))

                base_chart = alt.Chart(df_gantt_plot).encode(
                    y=alt.Y(
                        "Etiqueta_Y:N",
                        sort=orden_etiquetas_y,
                        title="",
                        axis=alt.Axis(
                            labelColor="#262320",
                            labelFontSize=11.5,
                            labelFontWeight="bold",
                            labelLimit=310,
                            tickColor="#DFD9CE",
                            domainColor="#DFD9CE",
                        ),
                    )
                )

                barras_gantt = base_chart.mark_bar(cornerRadius=4, height=18).encode(
                    x=alt.X(
                        "Inicio_DT:T",
                        title="Línea de Tiempo (Inicio → Fin)",
                        axis=alt.Axis(
                            grid=True,
                            gridColor="#EAE5DC",
                            domainColor="#DFD9CE",
                            labelColor="#262320",
                            titleColor="#262320",
                            format="%d/%m",
                        ),
                    ),
                    x2="Fin_DT:T",
                    color=alt.Color("Partida_Grupo:N", scale=escala_color_partidas, legend=None),
                    opacity=alt.Opacity("Opacidad:Q", legend=None),
                    tooltip=[
                        alt.Tooltip("Partida:N", title="Partida"),
                        alt.Tooltip("Tarea:N", title="Tarea / Resumen"),
                        alt.Tooltip("Estado:N", title="Estado"),
                        alt.Tooltip("Contratista:N", title="Contratista"),
                        alt.Tooltip("Inicio:N", title="Fecha Inicio"),
                        alt.Tooltip("Fin:N", title="Fecha Fin"),
                        alt.Tooltip("Duracion_Dias:Q", title="Duración (días)"),
                    ],
                )

                textos_gantt = base_chart.mark_text(
                    align="left",
                    baseline="middle",
                    dx=6,
                    fontSize=10.5,
                    fontWeight="bold",
                    color="#262320",
                ).encode(
                    x="Fin_DT:T",
                    text="Texto_Barra:N",
                )

                layers_gantt = [barras_gantt, textos_gantt]
                if separadores_y:
                    df_sep = pd.DataFrame({"Etiqueta_Y": separadores_y})
                    reglas_sep = (
                        alt.Chart(df_sep)
                        .mark_rule(strokeDash=[5, 4], color="#C8BFA8", strokeWidth=1.5)
                        .encode(y=alt.Y("Etiqueta_Y:N", sort=orden_etiquetas_y))
                    )
                    layers_gantt.insert(0, reglas_sep)

                chart_gantt_final = (
                    alt.layer(*layers_gantt)
                    .properties(height=alto_gantt)
                    .configure_view(strokeOpacity=0)
                )
                st.altair_chart(chart_gantt_final, use_container_width=True)
            else:
                st.caption("💡 Asigna fechas de **Inicio** y **Fin** a las tareas abajo (o usa el botón **📅 Auto-asignar fechas**) para visualizar las barras en el Cronograma Gantt.")
        else:
            st.caption("No hay tareas registradas en este proyecto.")

    especialidades_obra = list(dict.fromkeys([""] + (obtener_catalogo_estudio("especialidades") or ESPECIALIDADES_DEFAULT) + extraer_esp(st.session_state.maestro)))
    contratistas_obra = [""] + (st.session_state.maestro['ID_Contratista'].dropna().unique().tolist() if not st.session_state.maestro.empty else [])

    # Mapa de montos pagados por Partida (sincronizado con 06. Cuadro de Pagos Semanales + Pagos directos)
    pagados_por_partida_map = obtener_pagado_por_partida_proyecto(proy_name)

    # Iterar partidas en el orden exacto del presupuesto
    for pos_part_0b, (idx_part, part_r) in enumerate(parts_proy.iterrows()):
        idx_p_1b = pos_part_0b + 1
        p_nom = part_r['Nombre_Partida']
        st.markdown(f"<div class='cota-section-header'><span>■</span> PARTIDA // {p_nom.upper()}</div>", unsafe_allow_html=True)

        df_pactado = st.session_state.p_info[(st.session_state.p_info['Proyecto'] == proy_name) & (st.session_state.p_info['Nombre_Partida'] == p_nom)]
        monto_pactado = float(df_pactado['Monto_Pactado'].iloc[0]) if not df_pactado.empty else 0.0

        monto_pagado = float(pagados_por_partida_map.get(p_nom, 0.0))
        saldo = monto_pactado - monto_pagado

        col_ord_up, col_ord_dn, col_ord_sel, col_b1, col_b2, col_b3, col_b4, col_sug, col_b5 = st.columns([0.5, 0.5, 1.0, 1.3, 1.4, 1.55, 1.25, 1.35, 3.65])
        with col_ord_up:
            if st.button("⬆", key=f"btn_obra_up_p_{proy_name}_{idx_p_1b}", disabled=(idx_p_1b == 1), help="Subir Partida", use_container_width=True):
                mover_partida_presupuesto(proy_name, idx_p_1b, "subir", ambito="gestion")
                st.rerun()
        with col_ord_dn:
            if st.button("⬇", key=f"btn_obra_dn_p_{proy_name}_{idx_p_1b}", disabled=(idx_p_1b == len(parts_proy)), help="Bajar Partida", use_container_width=True):
                mover_partida_presupuesto(proy_name, idx_p_1b, "bajar", ambito="gestion")
                st.rerun()
        with col_ord_sel:
            key_ord_obra = f"sel_ord_obra_{proy_name}_{idx_p_1b}"
            st.session_state[key_ord_obra] = int(idx_p_1b)
            def _make_on_ord_obra(p_curr_o, k_ord_o):
                def _cb_ord_o():
                    nueva_pos_o = int(st.session_state.get(k_ord_o, p_curr_o))
                    if nueva_pos_o != p_curr_o:
                        mover_partida_presupuesto(proy_name, p_curr_o, nueva_pos_o, ambito="gestion")
                return _cb_ord_o
            st.selectbox(
                "Orden Partida",
                options=list(range(1, len(parts_proy) + 1)),
                format_func=lambda x: f"N° {x}",
                key=key_ord_obra,
                on_change=_make_on_ord_obra(idx_p_1b, key_ord_obra),
                label_visibility="collapsed",
                help="Seleccionar el número de orden de esta partida",
            )

        with col_b1:
            with st.popover("✏️ RENOMBRAR"):
                with st.form(f"ren_{proy_name}_{p_nom}_{idx_part}"):
                    nuevo_nombre = st.text_input("Nuevo Nombre", value=p_nom)
                    if st.form_submit_button("GUARDAR") and nuevo_nombre and nuevo_nombre != p_nom:
                        renombrar_partida_presupuesto(proy_name, idx_p_1b, p_nom, nuevo_nombre, ambito="gestion")
                        st.rerun()

        with col_b2:
            with st.popover("PRESUPUESTO"):
                with st.form(f"pact_{proy_name}_{p_nom}_{idx_part}"):
                    n_pac = st.number_input("Pactado (S/)", value=monto_pactado)
                    if st.form_submit_button("FIJAR"):
                        if df_pactado.empty:
                            st.session_state.p_info = pd.concat([st.session_state.p_info, pd.DataFrame([{'Proyecto': proy_name, 'Nombre_Partida': p_nom, 'Monto_Pactado': float(n_pac)}])], ignore_index=True)
                        else:
                            st.session_state.p_info.loc[df_pactado.index, 'Monto_Pactado'] = float(n_pac)
                        clear_base_dfs()
                        st.rerun()

        with col_b3:
            with st.popover("INGRESAR PAGO"):
                with st.form(f"pago_{proy_name}_{p_nom}_{idx_part}"):
                    p_contra = st.selectbox("Contratista", st.session_state.maestro['ID_Contratista'].tolist() if not st.session_state.maestro.empty else ["Sin contratistas"])
                    p_fecha = st.date_input("Fecha", value=datetime.date.today())
                    p_monto = st.number_input("Monto (S/)", value=0.0)
                    p_tipo = st.selectbox("Tipo", ["Adelanto", "Valorización", "Liquidación", "Adicional", "Otros"])
                    p_notas = st.text_input("Notas")
                    if st.form_submit_button("PAGAR") and p_monto > 0:
                        n_pago = pd.DataFrame([{
                            'ID': f"PAG_{int(datetime.datetime.now().timestamp())}_{uuid.uuid4().hex[:6]}",
                            'Proyecto': proy_name,
                            'Partida': p_nom,
                            'Contratista': p_contra,
                            'Fecha': p_fecha.strftime("%d/%m/%Y"),
                            'Monto': float(p_monto),
                            'Tipo': p_tipo,
                            'Notas': p_notas
                        }])
                        st.session_state.pagos = pd.concat([st.session_state.pagos, n_pago[COLS_PAGOS]], ignore_index=True)
                        clear_base_dfs()
                        st.rerun()

        with col_b4:
            with st.popover("🗑️ ELIMINAR"):
                st.warning(f"¿Eliminar la partida '{p_nom}' y sus tareas?")
                if st.button("CONFIRMAR", key=f"del_part_{proy_name}_{p_nom}_{idx_part}", type="primary"):
                    st.session_state.partidas = st.session_state.partidas.drop(idx_part)
                    st.session_state.tasks = st.session_state.tasks[~((st.session_state.tasks['Proyecto'] == proy_name) & (st.session_state.tasks['Partida'] == p_nom))]
                    st.session_state.p_info = st.session_state.p_info[~((st.session_state.p_info['Proyecto'] == proy_name) & (st.session_state.p_info['Nombre_Partida'] == p_nom))]
                    recalcular_totales_presupuesto_proyecto(proy_name, sincronizar_pactado=False)
                    clear_base_dfs()
                    st.rerun()

        # Editor de tareas de la partida
        mask_t = (st.session_state.tasks['Proyecto'] == proy_name) & (st.session_state.tasks['Partida'] == p_nom)
        df_tasks_p = st.session_state.tasks[mask_t].copy().reset_index(drop=True)
        ppto_tareas_sum = pd.to_numeric(df_tasks_p['Presupuesto'], errors='coerce').fillna(0.0).sum() if not df_tasks_p.empty and 'Presupuesto' in df_tasks_p.columns else 0.0

        with col_b5:
            cls_s = 'cota-badge-saldo-ok' if saldo >= 0 else 'cota-badge-saldo-error'
            badge_tareas_html = (
                f"<span class='cota-badge cota-badge-pactado' style='background:#FAF8F5; border-color:#C85A32; color:#C85A32;'>PPTO. TAREAS: {format_currency(ppto_tareas_sum)}</span>"
                if ppto_tareas_sum > 0
                else ""
            )
            html_badges = (
                f"<div class='cota-badge-container'>"
                f"{badge_tareas_html}"
                f"<span class='cota-badge cota-badge-pactado'>PACTADO: {format_currency(monto_pactado)}</span>"
                f"<span class='cota-badge cota-badge-pagado'>PAGADO: {format_currency(monto_pagado)}</span>"
                f"<span class='cota-badge {cls_s}'>SALDO: {format_currency(saldo)}</span>"
                f"</div>"
            )
            st.markdown(html_badges, unsafe_allow_html=True)

        base_t_key = f"base_df_tasks_{proy_name}_{p_nom}"
        counter_key = f"c_{base_t_key}"
        c_val = st.session_state.get(counter_key, 0)
        w_key = f"t_{proy_name}_{p_nom}_{c_val}"

        cols_task_ed = [
            'Codigo_Item', 'Tarea', 'Moneda', 'Unidad', 'Metrado', 'Valor_Unitario', 'Presupuesto',
            'Especialidad', 'Contratista', 'Estado', 'Supervisado', 'Inicio', 'Fin',
            'Causa_Cumplimiento', 'Dependencia', 'Permitir_Cruce', 'Notas'
        ]
        for c_req in cols_task_ed:
            if c_req not in df_tasks_p.columns:
                if c_req in ['Metrado', 'Valor_Unitario', 'Presupuesto']:
                    df_tasks_p[c_req] = 0.0
                elif c_req == 'Moneda':
                    df_tasks_p[c_req] = "Soles"
                elif c_req == 'Supervisado':
                    df_tasks_p[c_req] = "No"
                else:
                    df_tasks_p[c_req] = ""

        for esp_v in df_tasks_p['Especialidad'].dropna().unique().tolist():
            if safe_str(esp_v) and safe_str(esp_v) not in especialidades_obra:
                especialidades_obra.append(safe_str(esp_v))
        for con_v in df_tasks_p['Contratista'].dropna().unique().tolist():
            if safe_str(con_v) and safe_str(con_v) not in contratistas_obra:
                contratistas_obra.append(safe_str(con_v))

        display_t = df_tasks_p[cols_task_ed].copy() if not df_tasks_p.empty else pd.DataFrame(columns=cols_task_ed)
        display_t['Inicio'] = display_t['Inicio'].apply(lambda x: parse_date(x))
        display_t['Fin'] = display_t['Fin'].apply(lambda x: parse_date(x))
        display_t['Metrado'] = pd.to_numeric(display_t['Metrado'], errors='coerce').fillna(0.0).astype(float)
        display_t['Valor_Unitario'] = pd.to_numeric(display_t['Valor_Unitario'], errors='coerce').fillna(0.0).astype(float)
        display_t['Presupuesto'] = pd.to_numeric(display_t['Presupuesto'], errors='coerce').fillna(0.0).astype(float)
        if 'Supervisado' in display_t.columns:
            display_t['Supervisado'] = display_t['Supervisado'].apply(_normalizar_supervisado)

        display_t['Permitir_Cruce'] = display_t['Permitir_Cruce'].apply(to_bool) if 'Permitir_Cruce' in display_t.columns else False
        st.session_state[base_t_key] = display_t.copy()

        with col_sug:
            with st.popover("🔍 SUGERIR"):
                if st.button("Buscar disponibles", key=f"sug_{proy_name}_{p_nom}_{idx_part}", use_container_width=True, help="Sugerir contratista disponible para esta partida"):
                    encontrado_sug = False
                    for _, row_s in st.session_state[base_t_key].iterrows():
                        if pd.notna(row_s.get('Especialidad')) and str(row_s.get('Especialidad')).strip() not in ["Ninguna", ""]:
                            sug = sugerir_contratista(
                                row_s['Especialidad'],
                                proy_data.get('Ubicación', 'Lima'),
                                row_s.get('Inicio'),
                                row_s.get('Fin'),
                                st.session_state.maestro,
                                st.session_state.tasks,
                                st.session_state.df_historial,
                            )
                            if sug:
                                encontrado_sug = True
                                st.info(f"**{row_s.get('Tarea')}**: {sug}")
                    if not encontrado_sug:
                        st.caption("Asigna una especialidad a las tareas para sugerir contratistas.")

        safe_proy_id_obra = re.sub(r"[^a-zA-Z0-9_]", "_", str(proy_name or ""))
        st.markdown(f"<div id='anchor_obra_tasks_{safe_proy_id_obra}_{idx_p_1b}'></div>", unsafe_allow_html=True)

        st.data_editor(
            st.session_state[base_t_key],
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            key=w_key,
            column_order=[
                "Codigo_Item",
                "Tarea",
                "Especialidad",
                "Contratista",
                "Estado",
                "Supervisado",
                "Permitir_Cruce",
                "Inicio",
                "Fin",
                "Notas",
            ],
            column_config={
                "Codigo_Item": st.column_config.TextColumn("Ítem", width="small"),
                "Tarea": st.column_config.TextColumn("Tarea / Actividad", width="large", required=True),
                "Moneda": None,
                "Unidad": None,
                "Metrado": None,
                "Valor_Unitario": None,
                "Presupuesto": None,
                "Especialidad": st.column_config.SelectboxColumn("Especialidad", options=especialidades_obra),
                "Contratista": st.column_config.SelectboxColumn("Contratista", options=contratistas_obra),
                "Estado": st.column_config.SelectboxColumn("Estado", options=STATUS_TASKS),
                "Supervisado": st.column_config.SelectboxColumn("Supervisado ✓", options=["No", "Sí"], default="No", width="small"),
                "Permitir_Cruce": st.column_config.CheckboxColumn("Permitir cruce", default=False, width="small", help="Autoriza que este contratista tenga tareas simultáneas en la misma fecha en distintos proyectos o tareas"),
                "Inicio": st.column_config.DateColumn("Inicio", format="DD/MM/YYYY"),
                "Fin": st.column_config.DateColumn("Fin", format="DD/MM/YYYY"),
                "Notas": st.column_config.TextColumn("Notas")
            },
            on_change=on_table_edit,
            args=(
                base_t_key,
                w_key,
                'tasks',
                ['Proyecto', 'Partida'],
                [proy_name, p_nom],
                ['Inicio', 'Fin'],
                ['Codigo_Item', 'Tarea', 'Moneda', 'Unidad', 'Especialidad', 'Contratista', 'Estado', 'Supervisado', 'Causa_Cumplimiento', 'Dependencia', 'Notas'],
                None,
                ['Metrado', 'Valor_Unitario', 'Presupuesto'],
                None
            )
        )

        render_alertas_cruce_partida(proy_name, p_nom)
        _render_obra_date_range_controller(
            proy_name,
            idx_p_1b,
            p_nom,
            df_tasks_p,
            proy_data.get("Inicio"),
            counter_key,
        )
        continue  # Rango integrado directo en la tabla; bloque inferior omitido
        if not df_tasks_p.empty:
            opciones_t_obra = [
                (i_t, f"{safe_str(r_t.get('Codigo_Item', f'{idx_p_1b}.{i_t+1:02d}'))} — {extraer_descripcion_tarea(r_t.get('Tarea', ''), r_t.get('Codigo_Item', ''))}")
                for i_t, (_, r_t) in enumerate(df_tasks_p.iterrows())
            ]
            cr_t, cr_cal, cr_btn, cr_sug = st.columns([3.8, 3.2, 1.6, 1.4])
            with cr_t:
                idx_t_sel_obra = st.selectbox(
                    "Tarea seleccionada:",
                    options=[o[0] for o in opciones_t_obra],
                    format_func=lambda x: dict(opciones_t_obra).get(x, ""),
                    # (legacy selector removido)
                    label_visibility="collapsed",
                )
            fila_t_sel = df_tasks_p.iloc[idx_t_sel_obra]
            d_ini_sel = parse_date(fila_t_sel.get("Inicio")) or parse_date(proy_data.get("Inicio")) or datetime.date.today()
            d_fin_sel = parse_date(fila_t_sel.get("Fin")) or (d_ini_sel + datetime.timedelta(days=3))
            if d_fin_sel < d_ini_sel:
                d_fin_sel = d_ini_sel

            with cr_cal:
                rango_fechas_sel = st.date_input(
                    "📅 Inicio → Fin (mismo calendario):",
                    value=(d_ini_sel, d_fin_sel),
                    format="DD/MM/YYYY",
                    # (legacy rango removido)
                    label_visibility="collapsed",
                    help="Selecciona la fecha de Inicio y ahí mismo la fecha de Fin; el calendario resaltará todos los días que durará la tarea.",
                )
            with cr_btn:
                dur_txt = ""
                if isinstance(rango_fechas_sel, (tuple, list)) and len(rango_fechas_sel) == 2:
                    dias_dur = (rango_fechas_sel[1] - rango_fechas_sel[0]).days + 1
                    dur_txt = f" ({dias_dur}d)"
                if False:
                    if isinstance(rango_fechas_sel, (tuple, list)) and len(rango_fechas_sel) >= 1:
                        f_i_new = rango_fechas_sel[0]
                        f_f_new = rango_fechas_sel[1] if len(rango_fechas_sel) > 1 else f_i_new
                        indices_p_global = st.session_state.tasks[mask_t].index.tolist()
                        if idx_t_sel_obra < len(indices_p_global):
                            g_idx = indices_p_global[idx_t_sel_obra]
                            st.session_state.tasks.at[g_idx, "Inicio"] = f_i_new.strftime("%d/%m/%Y")
                            st.session_state.tasks.at[g_idx, "Fin"] = f_f_new.strftime("%d/%m/%Y")
                            st.session_state[counter_key] = c_val + 1
                            st.rerun()
            with cr_sug:
                if False:
                    for _, row_s in st.session_state[base_t_key].iterrows():
                        if pd.notna(row_s.get('Especialidad')) and str(row_s.get('Especialidad')).strip() not in ["Ninguna", ""]:
                            sug = sugerir_contratista(
                                row_s['Especialidad'],
                                proy_data.get('Ubicación', 'Lima'),
                                row_s.get('Inicio'),
                                row_s.get('Fin'),
                                st.session_state.maestro,
                                st.session_state.tasks,
                                st.session_state.df_historial
                            )
                            if sug:
                                st.info(f"**{row_s.get('Tarea')}**: {sug}")


def _render_pagos_tooltip_controller(proy_name: str, safe_proy_id: str, data_cuadro: dict, cols_pago: list[str]):
    """Inyecta el controlador interactivo del Cuadro de Pagos: edición en vivo dentro del cuadro con colores (normal y Pantalla Completa), recálculo instantáneo y tooltips flotantes."""
    tc_val = float(data_cuadro.get("tc", 3.60) or 3.60)
    if tc_val <= 0:
        tc_val = 3.60
    cols_por_pagar = list(data_cuadro.get("cols_por_pagar", []))
    contratistas_disp = obtener_contratistas_disponibles_proyecto(proy_name, data_cuadro)
    pagos_todos = obtener_pagos_semana(data_cuadro, "ALL")
    col_labels = {c: etiqueta_corta_columna_pago(c) for c in cols_pago}
    col_export_labels = {c: etiqueta_export_columna_pago(c) for c in cols_pago}
    floating_ui_js = build_pagos_floating_ui_js()

    import time
    payload_json = json.dumps({
        "safeId": safe_proy_id,
        "bridgeLabel": f"PAGOS_BRIDGE_{safe_proy_id}",
        "colLabels": col_labels,
        "colExportLabels": col_export_labels,
        "contractors": contratistas_disp,
        "paymentTypes": list(TIPOS_PAGO_CUADRO),
        "payments": pagos_todos,
        "todayIso": datetime.date.today().strftime("%Y-%m-%d"),
        "colsPago": cols_pago,
        "colsPorPagar": cols_por_pagar,
        "tc": tc_val,
        "renderNonce": time.time(),
    })

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="margin:0; padding:0; overflow:hidden; background:transparent;">
    <script>
    (function() {{
        const payload = {payload_json.replace("</", "<" + chr(92) + "/")};
        const parentWin = window.parent;
        const parentDoc = parentWin.document;
        const safeId = payload.safeId;
        const bridgeLabel = payload.bridgeLabel;
        const colsPago = payload.colsPago;
        let tc = payload.tc || 3.60;

        parentWin.__cotaPagosFsState = parentWin.__cotaPagosFsState || {{}};
        parentWin.__cotaPagosControllers = parentWin.__cotaPagosControllers || {{}};

        if (parentWin.__cotaPagosControllers[safeId] && typeof parentWin.__cotaPagosControllers[safeId].cleanup === 'function') {{
            try {{
                parentWin.__cotaPagosControllers[safeId].cleanup();
            }} catch (e) {{}}
        }}

        function ensureInteractiveStyles() {{
            let stEl = parentDoc.getElementById('cota_pagos_fs_styles');
            if (!stEl) {{
                stEl = parentDoc.createElement('style');
                stEl.id = 'cota_pagos_fs_styles';
                parentDoc.head.appendChild(stEl);
            }}
            stEl.textContent = `
                .cota-pagos-fs-active {{
                    position: fixed !important;
                    inset: 0 !important;
                    top: 0 !important;
                    left: 0 !important;
                    right: 0 !important;
                    bottom: 0 !important;
                    width: 100vw !important;
                    height: 100vh !important;
                    max-width: 100vw !important;
                    max-height: 100vh !important;
                    z-index: 2147483640 !important;
                    background: #FAF8F5 !important;
                    padding: 16px 24px !important;
                    margin: 0 !important;
                    border-radius: 0 !important;
                    overflow: hidden !important;
                    box-sizing: border-box !important;
                    box-shadow: none !important;
                    display: flex !important;
                    flex-direction: column !important;
                }}
                .cota-pagos-fs-active .cota-pagos-scroll-area {{
                    flex: 1 1 auto !important;
                    max-height: calc(100vh - 85px) !important;
                    overflow: auto !important;
                }}
                .cota-pagos-fs-active table {{
                    font-size: 13.5px !important;
                }}
                .cota-pagos-fs-active th, .cota-pagos-fs-active td {{
                    padding: 8px 11px !important;
                }}
                td.cota-editable-cell {{
                    cursor: pointer !important;
                    transition: background 0.1s ease, box-shadow 0.1s ease;
                }}
                td.cota-editable-cell:hover {{
                    background: #FFF6EE !important;
                    box-shadow: inset 0 0 0 1.5px rgba(200, 90, 50, 0.55) !important;
                }}
                td.cota-cell-editing {{
                    padding: 2px 4px !important;
                    background: #FFFFFF !important;
                    box-shadow: inset 0 0 0 2px #C85A32 !important;
                }}
                .cota-inline-input {{
                    width: 100%;
                    box-sizing: border-box;
                    border: none;
                    outline: none;
                    background: transparent;
                    font-family: inherit;
                    font-size: inherit;
                    font-weight: 700;
                    color: #262320;
                    padding: 4px 4px;
                }}
                .cota-row-del-btn {{
                    opacity: 0.25;
                    transition: opacity 0.15s ease, color 0.15s ease;
                    cursor: pointer;
                    border: none;
                    background: transparent;
                    color: #9E9589;
                    font-size: 13px;
                    padding: 2px 5px;
                    border-radius: 4px;
                }}
                tr:hover .cota-row-del-btn {{
                    opacity: 1;
                }}
                .cota-row-del-btn:hover {{
                    background: #FDECEA;
                    color: #D92B2B;
                }}
            `;
        }}

        if (!parentWin.__cotaSafeDomPatched) {{
            parentWin.__cotaSafeDomPatched = true;
            const origRemoveChild = parentWin.Node.prototype.removeChild;
            parentWin.Node.prototype.removeChild = function(child) {{
                if (child && child.parentNode !== this) return child;
                return origRemoveChild.apply(this, arguments);
            }};
            const origInsertBefore = parentWin.Node.prototype.insertBefore;
            parentWin.Node.prototype.insertBefore = function(newNode, referenceNode) {{
                if (referenceNode && referenceNode.parentNode !== this) return this.appendChild(newNode);
                return origInsertBefore.apply(this, arguments);
            }};
        }}

        function findBridgeInput() {{
            let inp = parentDoc.querySelector('input[aria-label="' + bridgeLabel + '"]');
            if (inp) return inp;
            const inputs = parentDoc.querySelectorAll('div[data-testid="stTextInput"] input');
            for (let i = 0; i < inputs.length; i++) {{
                const el = inputs[i];
                if ((el.getAttribute('aria-label') || '').indexOf(bridgeLabel) >= 0) return el;
                const container = el.closest('div[data-testid="stTextInput"]');
                if (container && (container.textContent || '').indexOf(bridgeLabel) >= 0) return el;
            }}
            return null;
        }}

        function sendBridgePayload(obj) {{
            const inp = findBridgeInput();
            if (!inp) {{
                console.warn('[Cota Pagos] Bridge input no encontrado para', bridgeLabel);
                return;
            }}
            const valStr = JSON.stringify(Object.assign({{ ts: Date.now() }}, obj));
            const winProto = (parentWin.HTMLInputElement || window.HTMLInputElement).prototype;
            const nativeSetter = Object.getOwnPropertyDescriptor(winProto, 'value').set;
            const tracker = inp._valueTracker;
            if (tracker) tracker.setValue('');
            nativeSetter.call(inp, valStr);
            inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
            inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
            try {{ inp.focus({{ preventScroll: true }}); }} catch (e) {{}}
            inp.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }}));
            inp.blur();
        }}

        function fmtMoney(val, pref, blankZero) {{
            const v = Number(val) || 0;
            if (blankZero && Math.abs(v) < 0.005) return '';
            return pref + v.toLocaleString('en-US', {{ minimumFractionDigits: 2, maximumFractionDigits: 2 }});
        }}

        function getOrCreateTooltip() {{
            let tt = parentDoc.getElementById('cota_payment_tooltip_box');
            if (!tt) {{
                tt = parentDoc.createElement('div');
                tt.id = 'cota_payment_tooltip_box';
                tt.style.cssText = 'position:fixed; z-index:2147483647; pointer-events:none; background:#262320; color:#FFFFFF; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; padding:10px 14px; border-radius:8px; box-shadow:0 10px 28px rgba(38,35,32,0.45); border:1px solid rgba(255,255,255,0.18); max-width:340px; display:none; opacity:0; transition:opacity 0.12s ease;';
                parentDoc.body.appendChild(tt);
            }}
            const fsEl = parentDoc.fullscreenElement;
            if (fsEl && tt.parentElement !== fsEl) {{
                fsEl.appendChild(tt);
            }} else if (!fsEl && tt.parentElement !== parentDoc.body) {{
                parentDoc.body.appendChild(tt);
            }}
            return tt;
        }}

        function showTooltipContent(e, partida, semana, monto, nota) {{
            if (!nota) return;
            const tooltip = getOrCreateTooltip();
            tooltip.innerHTML = `
                <div style="display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:6px; border-bottom:1px solid rgba(255,255,255,0.18); padding-bottom:5px;">
                    <span style="background:#C85A32; color:#FFFFFF; font-size:10px; font-weight:800; text-transform:uppercase; padding:2px 7px; border-radius:4px; letter-spacing:0.5px;">💳 DETALLE DE PAGO</span>
                    <span style="font-size:11.5px; font-weight:700; color:#EFECE6;">${{semana}}</span>
                </div>
                <div style="font-size:13px; font-weight:700; color:#FFFFFF; margin-bottom:2px;">${{partida}}</div>
                <div style="font-size:11.5px; font-weight:700; color:#78C288; background:rgba(74,124,89,0.25); display:inline-block; padding:2px 6px; border-radius:4px; margin-bottom:7px;">Monto: ${{monto}}</div>
                <div style="font-size:12px; color:#EFECE6; line-height:1.45; border-left:3px solid #C85A32; padding-left:8px; margin-top:2px;">${{escHtml(nota).replace(/\\n/g, '<br>')}}</div>
            `;
            tooltip.style.display = 'block';
            tooltip.style.opacity = '1';

            let posX = e.clientX + 16;
            let posY = e.clientY + 16;
            if (posX + 350 > parentWin.innerWidth) {{
                posX = Math.max(10, e.clientX - 355);
            }}
            if (posY + 140 > parentWin.innerHeight) {{
                posY = Math.max(10, e.clientY - 130);
            }}
            tooltip.style.left = posX + 'px';
            tooltip.style.top = posY + 'px';
        }}

        function hideTooltip() {{
            const tt = parentDoc.getElementById('cota_payment_tooltip_box');
            if (tt) {{
                tt.style.display = 'none';
                tt.style.opacity = '0';
            }}
        }}

        function recalculateTableDOM(fsWrap) {{
            if (!fsWrap) return;
            const rows = fsWrap.querySelectorAll('tr[data-row-type]');
            let subTotal = 0;
            let subPagado = 0;
            let subSaldo = 0;
            const subSem = {{}};
            colsPago.forEach(c => {{ subSem[c] = 0; }});

            let gesTotal = 0, gesPagado = 0, gesSaldo = 0;
            const gesSem = {{}};
            let ggTotal = 0, ggPagado = 0, ggSaldo = 0;
            const ggSem = {{}};
            colsPago.forEach(c => {{ gesSem[c] = 0; ggSem[c] = 0; }});

            rows.forEach(tr => {{
                const rType = tr.getAttribute('data-row-type');
                if (rType !== 'contratista' && rType !== 'gestion' && rType !== 'gg') return;
                const monCell = tr.querySelector('td[data-col-field="Moneda"]');
                const monTxt = monCell ? (monCell.getAttribute('data-raw-val') || monCell.textContent || 'Soles') : 'Soles';
                const isUsd = monTxt.toLowerCase().indexOf('dolar') >= 0 || monTxt.toLowerCase().indexOf('dólar') >= 0;
                const pref = isUsd ? '$' : 'S/ ';

                const totCell = tr.querySelector('td[data-col-field="TOTAL"]');
                const totVal = totCell ? (parseFloat(totCell.getAttribute('data-raw-val')) || 0) : 0;

                let rPagado = 0;
                colsPago.forEach(cName => {{
                    const cCell = tr.querySelector('td[data-col-field="' + cName + '"]');
                    if (!cCell) return;
                    const v = parseFloat(cCell.getAttribute('data-raw-val')) || 0;
                    const isPp = cCell.getAttribute('data-is-pp') === '1';
                    if (!isPp) {{
                        rPagado += v;
                    }}
                    if (rType === 'contratista') {{
                        subSem[cName] = (subSem[cName] || 0) + v;
                    }} else if (rType === 'gestion') {{
                        gesSem[cName] = v;
                    }} else if (rType === 'gg') {{
                        ggSem[cName] = v;
                    }}
                }});

                const rSaldo = totVal - rPagado;
                const pagCell = tr.querySelector('td[data-calc-role="row-pagado"]');
                const salCell = tr.querySelector('td[data-calc-role="row-saldo"]');
                if (pagCell) pagCell.textContent = fmtMoney(rPagado, pref, false);
                if (salCell) salCell.textContent = fmtMoney(rSaldo, pref, false);

                if (rType === 'contratista') {{
                    subTotal += totVal;
                    subPagado += rPagado;
                    subSaldo += rSaldo;
                }} else if (rType === 'gestion') {{
                    gesTotal = totVal;
                    gesPagado = rPagado;
                    gesSaldo = rSaldo;
                }} else if (rType === 'gg') {{
                    ggTotal = totVal;
                    ggPagado = rPagado;
                    ggSaldo = rSaldo;
                }}
            }});

            // Actualizar fila SUB TOTAL
            const trSub = fsWrap.querySelector('tr[data-summary-row="subtotal"]');
            if (trSub) {{
                const cTot = trSub.querySelector('td[data-sum-col="TOTAL"]');
                if (cTot) cTot.textContent = fmtMoney(subTotal, 'S/ ', false);
                colsPago.forEach(cName => {{
                    const cS = trSub.querySelector('td[data-sum-col="' + cName + '"]');
                    if (cS) cS.textContent = fmtMoney(subSem[cName] || 0, 'S/ ', false);
                }});
                const cPag = trSub.querySelector('td[data-sum-col="PAGADO"]');
                if (cPag) cPag.textContent = fmtMoney(subPagado, 'S/ ', false);
                const cSal = trSub.querySelector('td[data-sum-col="SALDO"]');
                if (cSal) cSal.textContent = fmtMoney(subSaldo, 'S/ ', false);
            }}

            // Actualizar filas TOTAL Soles y Dólares
            const totSolesTotal = subTotal + gesTotal + ggTotal;
            const totSolesPagado = subPagado + gesPagado + ggPagado;
            const totSolesSaldo = subSaldo + gesSaldo + ggSaldo;

            const trTotSoles = fsWrap.querySelector('tr[data-summary-row="total_soles"]');
            const trTotUsd = fsWrap.querySelector('tr[data-summary-row="total_usd"]');

            if (trTotSoles) {{
                const cTot = trTotSoles.querySelector('td[data-sum-col="TOTAL"]');
                if (cTot) cTot.textContent = fmtMoney(totSolesTotal, 'S/ ', false);
                colsPago.forEach(cName => {{
                    const vCol = (subSem[cName] || 0) + (gesSem[cName] || 0) + (ggSem[cName] || 0);
                    const cS = trTotSoles.querySelector('td[data-sum-col="' + cName + '"]');
                    if (cS) cS.textContent = fmtMoney(vCol, 'S/ ', false);
                }});
                const cPag = trTotSoles.querySelector('td[data-sum-col="PAGADO"]');
                if (cPag) cPag.textContent = fmtMoney(totSolesPagado, 'S/ ', false);
                const cSal = trTotSoles.querySelector('td[data-sum-col="SALDO"]');
                if (cSal) cSal.textContent = fmtMoney(totSolesSaldo, 'S/ ', false);
            }}

            if (trTotUsd && tc > 0) {{
                const cTot = trTotUsd.querySelector('td[data-sum-col="TOTAL"]');
                if (cTot) cTot.textContent = fmtMoney(totSolesTotal / tc, '$', false);
                colsPago.forEach(cName => {{
                    const vCol = (subSem[cName] || 0) + (gesSem[cName] || 0) + (ggSem[cName] || 0);
                    const cS = trTotUsd.querySelector('td[data-sum-col="' + cName + '"]');
                    if (cS) cS.textContent = fmtMoney(vCol / tc, '$', false);
                }});
                const cPag = trTotUsd.querySelector('td[data-sum-col="PAGADO"]');
                if (cPag) cPag.textContent = fmtMoney(totSolesPagado / tc, '$', false);
                const cSal = trTotUsd.querySelector('td[data-sum-col="SALDO"]');
                if (cSal) cSal.textContent = fmtMoney(totSolesSaldo / tc, '$', false);
            }}
        }}

        function renderAmountCellInner(cell, rawVal, notaTxt) {{
            const pref = cell.getAttribute('data-pref') || 'S/ ';
            const isTotal = cell.getAttribute('data-col-field') === 'TOTAL';
            const isPp = cell.getAttribute('data-is-pp') === '1';
            const numV = parseFloat(rawVal) || 0;
            cell.setAttribute('data-raw-val', String(numV));

            const dispTxt = fmtMoney(numV, pref, !isTotal);
            cell.style.color = isTotal ? '#262320' : (isPp ? '#262320' : '#D92B2B');

            if (notaTxt && !isTotal) {{
                cell.setAttribute('data-cota-note-text', notaTxt);
                cell.setAttribute('data-cota-note-monto', fmtMoney(numV, pref, false));
                cell.style.background = '#FFFDF9';
                const innerVal = dispTxt ? dispTxt : '<span style="color:#C85A32; font-size:11px;">💬</span>';
                cell.innerHTML = innerVal + '<span style="position:absolute; top:0; right:0; width:0; height:0; border-top:8px solid #C85A32; border-left:8px solid transparent;"></span>';
            }} else {{
                cell.removeAttribute('data-cota-note-text');
                cell.style.background = '';
                cell.textContent = dispTxt;
            }}
        }}

        {floating_ui_js}

        const iconExpand = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle; margin-right:5px;"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>';
        const iconCollapse = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle; margin-right:5px;"><path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3"/></svg>';

        function updateFsButtonState(btn, isFs) {{
            if (!btn) return; const desiredState = isFs ? '1' : '0'; if (btn.getAttribute('data-fs-state') === desiredState) return; btn.setAttribute('data-fs-state', desiredState);
            if (isFs) {{
                btn.innerHTML = iconCollapse + '<span>Salir de Pantalla Completa (ESC)</span>';
                btn.style.background = '#262320';
            }} else {{
                btn.innerHTML = iconExpand + '<span>Pantalla Completa</span>';
                btn.style.background = 'rgba(38, 35, 32, 0.28)';
            }}
        }}

        function syncFsState() {{
            const fsWrap = parentDoc.getElementById('cota_cuadro_pagos_fs_wrap_' + safeId);
            const btnFs = parentDoc.getElementById('btn_fs_pagos_' + safeId);
            if (!fsWrap) return;
            const isFs = !!parentWin.__cotaPagosFsState[safeId];
            if (isFs) {{
                if (!fsWrap.classList.contains('cota-pagos-fs-active')) {{
                    fsWrap.classList.add('cota-pagos-fs-active');
                }}
                parentDoc.body.style.overflow = 'hidden';
                updateFsButtonState(btnFs, true);
            }} else {{
                if (fsWrap.classList.contains('cota-pagos-fs-active')) {{
                    fsWrap.classList.remove('cota-pagos-fs-active');
                }}
                parentDoc.body.style.overflow = '';
                updateFsButtonState(btnFs, false);
            }}
        }}

        function toggleFs() {{
            const fsWrap = parentDoc.getElementById('cota_cuadro_pagos_fs_wrap_' + safeId);
            if (!fsWrap) return;
            const isFsNow = !fsWrap.classList.contains('cota-pagos-fs-active');
            parentWin.__cotaPagosFsState[safeId] = isFsNow;
            syncFsState();
        }}

        function commitAnyActiveEdit(fsWrap) {{
            if (!fsWrap) return;
            const editingCells = fsWrap.querySelectorAll('.cota-cell-editing');
            editingCells.forEach(c => {{
                if (typeof c._cotaCommit === 'function') {{
                    c._cotaCommit();
                }}
            }});
        }}

        function startCellEditing(cell, fsWrap) {{
            if (cell.classList.contains('cota-cell-editing')) return;
            commitAnyActiveEdit(fsWrap);
            closeCellPopover();
            hideTooltip();

            const rType = cell.getAttribute('data-row-type');
            const rIdx = parseInt(cell.getAttribute('data-row-idx') || '0', 10);
            const colField = cell.getAttribute('data-col-field');

            // Caso 1: Columna Moneda (alternar Soles / Dólares con selector directo)
            if (colField === 'Moneda') {{
                const curMon = (cell.getAttribute('data-raw-val') || 'Soles').trim();
                const nextMon = curMon === 'Dólares' ? 'Soles' : 'Dólares';
                cell.setAttribute('data-raw-val', nextMon);
                cell.textContent = nextMon;
                const tr = cell.closest('tr');
                if (tr) {{
                    const newPref = nextMon === 'Dólares' ? '$' : 'S/ ';
                    tr.querySelectorAll('td[data-pref]').forEach(tdP => {{
                        tdP.setAttribute('data-pref', newPref);
                        if (!tdP) return;
                        // Rerun de Streamlit actualiza formato de moneda sin mutar el DOM de React
                    }});
                }}
                recalculateTableDOM(fsWrap);
                sendBridgePayload({{
                    action: 'edit_cells',
                    edits: [{{ row_type: rType, row_idx: rIdx, field: 'Moneda', value: nextMon }}]
                }});
                return;
            }}

            // Caso 2: Columna Descripción + Contratista/Nota
            if (colField === 'Descripcion') {{
                const curDesc = cell.getAttribute('data-raw-desc') || '';
                const curNotas = cell.getAttribute('data-raw-notas') || '';
                const origHtml = cell.innerHTML;
                cell.classList.add('cota-cell-editing');
                cell.innerHTML = '<div style="display:flex; flex-direction:column; gap:4px; padding:3px;">' +
                    '<input type="text" class="cota-inline-input inp-desc" value="' + curDesc.replace(/"/g, '&quot;') + '" placeholder="Partida / Especialidad" style="border-bottom:1px solid #DFD9CE; font-weight:700; font-size:12px;" />' +
                    '<input type="text" class="cota-inline-input inp-notas" value="' + curNotas.replace(/"/g, '&quot;') + '" placeholder="Contratista / Nota (ej. Contratista: Juan)" style="font-weight:500; font-size:11px; color:#5A534A;" />' +
                '</div>';
                const inpD = cell.querySelector('.inp-desc');
                const inpN = cell.querySelector('.inp-notas');
                inpD.focus();
                inpD.select();

                let committed = false;
                function commitDesc() {{
                    if (committed) return;
                    committed = true;
                    cell._cotaCommit = null;
                    const newD = (inpD.value || '').trim() || curDesc;
                    const newN = (inpN.value || '').trim();
                    cell.classList.remove('cota-cell-editing');
                    cell.setAttribute('data-raw-desc', newD);
                    cell.setAttribute('data-raw-notas', newN);
                    cell.innerHTML = origHtml;
                    const titleSpan = cell.querySelector('.cota-desc-title');
                    if (titleSpan) titleSpan.textContent = newD;
                    const noteSpan = cell.querySelector('.cota-desc-sub');
                    if (noteSpan) {{
                        noteSpan.textContent = newN;
                        noteSpan.style.display = newN ? 'block' : 'none';
                    }}
                    if (newD !== curDesc || newN !== curNotas) {{
                        sendBridgePayload({{
                            action: 'edit_cells',
                            edits: [
                                {{ row_type: rType, row_idx: rIdx, field: 'Descripcion', value: newD }},
                                {{ row_type: rType, row_idx: rIdx, field: 'Notas', value: newN }}
                            ]
                        }});
                    }}
                }}
                cell._cotaCommit = commitDesc;

                cell.addEventListener('focusout', function onFo(ev) {{
                    if (cell.contains(ev.relatedTarget)) return;
                    cell.removeEventListener('focusout', onFo);
                    commitDesc();
                }});

                [inpD, inpN].forEach(inpEl => {{
                    inpEl.addEventListener('keydown', function(ke) {{
                        if (ke.key === 'Enter') {{
                            ke.preventDefault();
                            commitDesc();
                        }} else if (ke.key === 'Escape') {{
                            ke.preventDefault();
                            committed = true;
                            cell._cotaCommit = null;
                            cell.classList.remove('cota-cell-editing');
                            cell.innerHTML = origHtml;
                        }}
                    }});
                }});
                return;
            }}

            // Caso 3: Celda de Monto (TOTAL o Semana de Pago ADELANTO 1, S1, S2...)
            const curVal = parseFloat(cell.getAttribute('data-raw-val')) || 0;
            const curNote = cell.getAttribute('data-cota-note-text') || '';
            const isPaymentCol = colField !== 'TOTAL';
            if (isPaymentCol) {{
                openCellPopover(cell, fsWrap);
                return;
            }}

            cell.classList.add('cota-cell-editing');
            const initStr = curVal !== 0 ? String(curVal) : '';

            if (isPaymentCol) {{
                cell.innerHTML = '<div style="display:flex; flex-direction:column; gap:3px; min-width:110px;">' +
                    '<input type="text" inputmode="decimal" class="cota-inline-input inp-monto" value="' + initStr + '" placeholder="0.00" style="text-align:right;" />' +
                    '<input type="text" class="cota-inline-input inp-nota-pago" value="' + curNote.replace(/"/g, '&quot;') + '" placeholder="💬 Nota opcional..." style="font-size:10.5px; font-weight:500; color:#6E665E; border-top:1px dashed #DFD9CE; padding-top:2px; text-align:left;" />' +
                '</div>';
            }} else {{
                cell.innerHTML = '<input type="text" inputmode="decimal" class="cota-inline-input inp-monto" value="' + initStr + '" placeholder="0.00" style="text-align:right;" />';
            }}

            const inpM = cell.querySelector('.inp-monto');
            const inpNP = cell.querySelector('.inp-nota-pago');
            inpM.focus();
            inpM.select();

            let committedM = false;
            function commitMonto(moveDir) {{
                if (committedM) return;
                committedM = true;
                cell._cotaCommit = null;
                const rawTyped = (inpM.value || '').replace(/,/g, '').replace(/[^0-9.\\-]/g, '');
                const newNum = Math.max(0, Math.round((parseFloat(rawTyped) || 0) * 100) / 100);
                const newNota = inpNP ? (inpNP.value || '').trim() : curNote;

                cell.classList.remove('cota-cell-editing');
                renderAmountCellInner(cell, newNum, newNota);
                recalculateTableDOM(fsWrap);

                if (Math.abs(newNum - curVal) > 0.001 || newNota !== curNote) {{
                    const edPayload = {{
                        row_type: rType,
                        row_idx: rIdx,
                        field: colField,
                        value: newNum
                    }};
                    if (isPaymentCol) {{
                        edPayload.nota_pago = newNota;
                    }}
                    sendBridgePayload({{
                        action: 'edit_cells',
                        edits: [edPayload]
                    }});
                }}

                if (moveDir !== 0) {{
                    const editableCells = Array.from(fsWrap.querySelectorAll('td.cota-editable-cell'));
                    const curIndex = editableCells.indexOf(cell);
                    const nextCell = editableCells[curIndex + moveDir];
                    if (nextCell && nextCell.getAttribute('data-col-field') !== 'Moneda') {{
                        setTimeout(() => startCellEditing(nextCell, fsWrap), 30);
                    }}
                }}
            }}
            cell._cotaCommit = () => commitMonto(0);

            cell.addEventListener('focusout', function onFoM(ev) {{
                if (cell.contains(ev.relatedTarget)) return;
                cell.removeEventListener('focusout', onFoM);
                commitMonto(0);
            }});

            [inpM, inpNP].filter(Boolean).forEach(elInp => {{
                elInp.addEventListener('keydown', function(ke) {{
                    if (ke.key === 'Enter') {{
                        ke.preventDefault();
                        commitMonto(0);
                    }} else if (ke.key === 'Tab') {{
                        if (elInp === inpM && inpNP && !ke.shiftKey && ke.altKey) {{
                            return;
                        }}
                        ke.preventDefault();
                        commitMonto(ke.shiftKey ? -1 : 1);
                    }} else if (ke.key === 'Escape') {{
                        ke.preventDefault();
                        committedM = true;
                        cell._cotaCommit = null;
                        cell.classList.remove('cota-cell-editing');
                        renderAmountCellInner(cell, curVal, curNote);
                    }}
                }});
            }});
        }}

        // Manejador Delegado en parentDoc: captura clicks incluso tras cualquier re-render de Streamlit
        function onDocClick(ev) {{
            const wrapId = 'cota_cuadro_pagos_fs_wrap_' + safeId;
            const fsWrap = parentDoc.getElementById(wrapId);
            if (!fsWrap) return;

            // 1. Botón de Pantalla Completa
            const btnFs = ev.target.closest('#btn_fs_pagos_' + safeId);
            if (btnFs) {{
                ev.preventDefault();
                ev.stopPropagation();
                toggleFs();
                return;
            }}

            if (
                ev.target.closest('#cota_pagos_registro_modal')
                || ev.target.closest('#cota_pagos_semana_modal')
                || ev.target.closest('#cota_pagos_cell_popover')
            ) {{
                return;
            }}
            if (!fsWrap.contains(ev.target)) {{
                closeCellPopover();
                return;
            }}

            // 2. Botón para agregar fila
            const btnAdd = ev.target.closest('[data-cota-action="add-row"]');
            if (btnAdd) {{
                ev.preventDefault();
                ev.stopPropagation();
                sendBridgePayload({{ action: 'add_row', Descripcion: 'NUEVA PARTIDA / CONTRATISTA', Moneda: 'Soles', TOTAL: 0 }});
                return;
            }}

            // 3. Botón para eliminar fila
            const btnDel = ev.target.closest('[data-cota-action="del-row"]');
            if (btnDel) {{
                ev.preventDefault();
                ev.stopPropagation();
                const rIdx = parseInt(btnDel.getAttribute('data-row-idx') || '-1', 10);
                if (rIdx >= 0) {{
                    sendBridgePayload({{ action: 'delete_row', row_idx: rIdx }});
                }}
                return;
            }}

            // 4. Cabeceras de semanas: Por Pagar
            const thPp = ev.target.closest('[data-cota-toggle-pp-pill]') || ev.target.closest('th[data-cota-toggle-pp]');
            if (thPp) {{
                ev.preventDefault();
                ev.stopPropagation();
                const colName = thPp.getAttribute('data-cota-toggle-pp-pill') || thPp.getAttribute('data-cota-toggle-pp');
                if (colName) {{
                    sendBridgePayload({{ action: 'toggle_por_pagar', col: colName }});
                }}
                return;
            }}

            // 4b. Clic en columna de semana -> abrir ventana de Pagos realizados esa semana
            const thWeek = ev.target.closest('th[data-cota-week-header]');
            if (thWeek) {{
                ev.preventDefault();
                ev.stopPropagation();
                closeCellPopover();
                const colWk = thWeek.getAttribute('data-cota-week-header');
                if (colWk) {{
                    openSemanaPagosModal(colWk, fsWrap);
                }}
                return;
            }}

            // 5. Celdas editables
            const cell = ev.target.closest('td.cota-editable-cell');
            if (cell && !cell.classList.contains('cota-cell-editing')) {{
                startCellEditing(cell, fsWrap);
                return;
            }}
        }}

        function onDocKeyDown(ev) {{
            if (ev.key === 'Escape') {{
                const fsWrap = parentDoc.getElementById('cota_cuadro_pagos_fs_wrap_' + safeId);
                if (!fsWrap) return;
                if (parentDoc.getElementById('cota_pagos_registro_modal')) {{
                    closeRegistroModal();
                    return;
                }}
                if (parentDoc.getElementById('cota_pagos_semana_modal')) {{
                    closeSemanaModal();
                    return;
                }}
                if (parentDoc.getElementById('cota_pagos_cell_popover')) {{
                    closeCellPopover();
                    return;
                }}
                if (fsWrap.querySelector('.cota-cell-editing')) return;
                if (fsWrap.classList.contains('cota-pagos-fs-active')) {{
                    parentWin.__cotaPagosFsState[safeId] = false;
                    syncFsState();
                }}
            }}
        }}

        function onDocPointerMove(e) {{
            const wrapId = 'cota_cuadro_pagos_fs_wrap_' + safeId;
            const fsWrap = parentDoc.getElementById(wrapId);
            if (!fsWrap) return;
            const cell = e.target.closest('td[data-cota-note-text]');
            if (cell && fsWrap.contains(cell) && !cell.classList.contains('cota-cell-editing')) {{
                showTooltipContent(
                    e,
                    cell.getAttribute('data-cota-note-partida') || '',
                    cell.getAttribute('data-cota-note-semana') || '',
                    cell.getAttribute('data-cota-note-monto') || '',
                    cell.getAttribute('data-cota-note-text') || ''
                );
            }} else {{
                hideTooltip();
            }}
        }}

        parentDoc.addEventListener('click', onDocClick, true);
        parentDoc.addEventListener('keydown', onDocKeyDown, true);
        parentDoc.addEventListener('pointermove', onDocPointerMove, true);

        const observer = new (parentWin.MutationObserver || window.MutationObserver)(function() {{
            syncFsState();
        }});
        try {{
            // observer.observe deshabilitado para evitar bucle infinito de MutationObserver
        }} catch (e) {{}}

        parentWin.__cotaPagosControllers[safeId] = {{
            cleanup: function() {{
                try {{
                    closeAllPagosPopups();
                    parentDoc.removeEventListener('click', onDocClick, true);
                    parentDoc.removeEventListener('keydown', onDocKeyDown, true);
                    parentDoc.removeEventListener('pointermove', onDocPointerMove, true);
                    observer.disconnect();
                }} catch (e) {{}}
            }}
        }};

        ensureInteractiveStyles();
        try {{
            const fsWrapHeal = parentDoc.getElementById('cota_cuadro_pagos_fs_wrap_' + safeId);
            if (fsWrapHeal) {{
                fsWrapHeal.querySelectorAll('td.cota-editable-cell').forEach(td => {{
                    if (!td.querySelector('.cota-cell-total-txt')) return;
                    Array.from(td.childNodes).forEach(node => {{
                        if (node.nodeType === 3 && (node.nodeValue || '').trim() !== '') {{
                            if (node.parentNode === td) td.removeChild(node);
                        }} else if (node.nodeType === 1 && node.tagName === 'SPAN') {{
                            if (!node.classList.contains('cota-cell-total-txt') && !node.classList.contains('cota-cell-corner-dot')) {{
                                if (node.parentNode === td) td.removeChild(node);
                            }}
                        }}
                    }});
                }});
            }}
        }} catch (e) {{}}
        syncFsState();
    }})();
    </script>
    </body>
    </html>
    """
    components.html(html_code, height=0)


def _render_cuadro_pagos_semanales(proy_name: str, proy_data: dict):
    """Renderiza el Cuadro de Pagos Semanales por Partida / Contratista y su exportación a Excel y PDF para el cliente."""
    cliente_str = safe_str(proy_data.get("Cliente", "")).strip() or "Sin cliente asignado"
    data_cuadro = obtener_cuadro_pagos_semanales_proyecto(proy_name)

    num_sem_actual = int(data_cuadro.get("num_semanas", 5) or 5)
    tc_actual = float(data_cuadro.get("tc", 3.60) or 3.60)
    cols_pago = obtener_columnas_pago_semanal(num_sem_actual)
    cols_por_pagar_actual = [c for c in data_cuadro.get("cols_por_pagar", []) if c in cols_pago]

    safe_proy_id = re.sub(r"[^a-zA-Z0-9_]", "_", proy_name)
    st.markdown(f"<div id='anchor_pagos_{safe_proy_id}'></div>", unsafe_allow_html=True)

    bridge_key = f"pagos_inline_bridge_{proy_name}"
    if bridge_key in st.session_state and st.session_state[bridge_key]:
        aplicar_edicion_inline_cuadro_pagos(proy_name, st.session_state[bridge_key])
        st.session_state[bridge_key] = ""
        data_cuadro = obtener_cuadro_pagos_semanales_proyecto(proy_name)

    # Barra de configuración superior
    c_cfg1, c_cfg2, c_cfg3 = st.columns([1.5, 1.3, 4.2])
    nuevo_num_sem = num_sem_actual
    with c_cfg1:
        st.markdown("<div style='padding-top: 27px;'></div>", unsafe_allow_html=True)
        if st.button(
            "➕ Agregar Semana",
            key=f"btn_add_sem_pagos_{proy_name}",
            disabled=(num_sem_actual >= 30),
            use_container_width=True,
            help=f"Agrega Semana {num_sem_actual + 1} al cuadro de pagos (actual: {num_sem_actual} semana(s)).",
        ):
            nuevo_num_sem = min(30, num_sem_actual + 1)
            data_cuadro["num_semanas"] = nuevo_num_sem
            guardar_cuadro_pagos_semanales_proyecto(proy_name, data_cuadro)
            st.session_state.pop(f"base_df_pagos_cont_{proy_name}", None)
            st.session_state.pop(f"base_df_pagos_ges_{proy_name}", None)
            st.rerun()
    with c_cfg2:
        nuevo_tc = float(
            st.number_input(
                "TC (S/ por USD)",
                min_value=0.10,
                max_value=20.00,
                value=round(tc_actual, 2),
                step=0.05,
                format="%.2f",
                key=f"tc_pagos_{proy_name}",
            )
        )
    with c_cfg3:
        cols_opciones = obtener_columnas_pago_semanal(nuevo_num_sem)
        default_pp = [c for c in cols_por_pagar_actual if c in cols_opciones]
        nuevas_por_pagar = st.multiselect(
            "⏳ Semanas / Columnas en estado 'Por Pagar' (no suman a PAGADO hasta desmarcarse):",
            options=cols_opciones,
            default=default_pp,
            format_func=etiqueta_corta_columna_pago,
            key=f"por_pagar_cols_{proy_name}",
        )

    # Si cambió la configuración superior, actualizar y persistir
    if (
        nuevo_num_sem != num_sem_actual
        or abs(nuevo_tc - tc_actual) > 1e-4
        or set(nuevas_por_pagar) != set(cols_por_pagar_actual)
    ):
        data_cuadro["num_semanas"] = nuevo_num_sem
        data_cuadro["tc"] = round(nuevo_tc, 2)
        data_cuadro["cols_por_pagar"] = list(nuevas_por_pagar)
        guardar_cuadro_pagos_semanales_proyecto(proy_name, data_cuadro)
        st.session_state.pop(f"base_df_pagos_cont_{proy_name}", None)
        st.session_state.pop(f"base_df_pagos_ges_{proy_name}", None)
        data_cuadro = obtener_cuadro_pagos_semanales_proyecto(proy_name)
        cols_pago = obtener_columnas_pago_semanal(nuevo_num_sem)
        cols_por_pagar_actual = list(nuevas_por_pagar)

    # Botonera de sincronización, importación y exportación (Excel + PDF con Semana 1, Semana 2...)
    b_act1, b_act2, b_act3, b_act4 = st.columns([2.4, 2.1, 2.2, 1.8])
    with b_act1:
        if st.button(
            "🔄 Sincronizar con 03. Presupuesto",
            key=f"btn_sync_pagos_{proy_name}",
            use_container_width=True,
            help="Trae o actualiza las partidas y montos totales desde la pestaña 03. Presupuesto sin perder los pagos semanales registrados.",
        ):
            data_cuadro = obtener_cuadro_pagos_semanales_proyecto(proy_name, sincronizar_partidas=True, fuente="presupuesto")
            st.session_state.pop(f"base_df_pagos_cont_{proy_name}", None)
            st.session_state.pop(f"base_df_pagos_ges_{proy_name}", None)
            st.rerun()

    with b_act2:
        with st.popover("📤 Importar Cuadro (Excel / CSV)", use_container_width=True):
            st.caption("Sube un archivo `.xlsx` o `.csv` con el cuadro de pagos semanales.")
            up_pagos = st.file_uploader(
                "Archivo de Pagos Semanales",
                type=["xlsx", "xls", "csv"],
                key=f"up_pagos_sem_{proy_name}",
            )
            if up_pagos is not None:
                if st.button("✅ Cargar al Proyecto", key=f"btn_apply_up_pagos_{proy_name}", type="primary", use_container_width=True):
                    parsed_p = parsear_cuadro_pagos_semanales(up_pagos, tc_default=nuevo_tc)
                    if parsed_p and parsed_p.get("filas_contratistas"):
                        guardar_cuadro_pagos_semanales_proyecto(proy_name, parsed_p)
                        st.session_state.pop(f"base_df_pagos_cont_{proy_name}", None)
                        st.session_state.pop(f"base_df_pagos_ges_{proy_name}", None)
                        st.session_state.pop(f"num_sem_pagos_{proy_name}", None)
                        st.session_state.pop(f"tc_pagos_{proy_name}", None)
                        st.session_state.pop(f"por_pagar_cols_{proy_name}", None)
                        st.success("Cuadro de pagos semanales importado correctamente.")
                        st.rerun()
                    else:
                        st.error("No se detectó la estructura del cuadro de pagos en el archivo.")

    safe_fn = "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in proy_name).strip("_") or "Proyecto"
    sem_activa_ui = resolver_semana_activa_cuadro(proy_name, data_cuadro, cols_pago)
    data_cuadro_export = dict(data_cuadro)
    data_cuadro_export["semana_resumen"] = sem_activa_ui
    with b_act3:
        xlsx_bytes = exportar_cuadro_pagos_semanales_excel(proy_name, data_cuadro_export)
        st.download_button(
            label="📥 EXPORTAR EXCEL (.XLSX)",
            data=xlsx_bytes,
            file_name=f"Control_Pagos_Semanales_{safe_fn}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"dl_xlsx_pagos_{proy_name}",
            type="primary",
            use_container_width=True,
        )

    with b_act4:
        pdf_bytes = exportar_cuadro_pagos_semanales_pdf(proy_name, data_cuadro_export)
        st.download_button(
            label="📄 EXPORTAR PDF (.PDF)",
            data=pdf_bytes,
            file_name=f"Control_Pagos_Semanales_{safe_fn}.pdf",
            mime="application/pdf",
            key=f"dl_pdf_pagos_{proy_name}",
            use_container_width=True,
        )

    res_calc = calcular_resumen_cuadro_pagos_semanales(data_cuadro)
    tot_soles = res_calc["total_soles"]
    tot_usd = res_calc["total_dolares"]
    sub_cont = res_calc["sub_total"]

    # Tarjetas KPI del Cuadro de Pagos Semanales
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_metric_card(
            "Total General (Soles)",
            format_currency(tot_soles["TOTAL"]),
            f"USD $ {tot_usd['TOTAL']:,.2f} · Contratistas: {format_currency(sub_cont['TOTAL'])}",
        )
    with k2:
        pct_pag = (tot_soles["PAGADO"] / tot_soles["TOTAL"] * 100.0) if tot_soles["TOTAL"] > 0 else 0.0
        render_metric_card(
            "Total Pagado",
            format_currency(tot_soles["PAGADO"]),
            f"USD $ {tot_usd['PAGADO']:,.2f} ({pct_pag:.1f}% desembolsado)" + (f" · Gestión rec.: {format_currency(safe_float(res_calc.get('fila_gestion', {}).get('PAGADO', 0.0), 0.0))}" if safe_float(res_calc.get("fila_gestion", {}).get("PAGADO", 0.0), 0.0) > 0 else ""),
            border_color="#4A7C59",
            text_color="#4A7C59",
        )
    with k3:
        lbl_pp = ", ".join(etiqueta_corta_columna_pago(c) for c in cols_por_pagar_actual) if cols_por_pagar_actual else "Ninguna semana marcada"
        render_metric_card(
            "Programado 'Por Pagar'",
            format_currency(tot_soles["POR_PAGAR"]),
            f"USD $ {tot_usd['POR_PAGAR']:,.2f} · {lbl_pp}",
            border_color="#D98A2B",
            text_color="#D98A2B",
        )
    with k4:
        render_metric_card(
            "Saldo Pendiente Total",
            format_currency(tot_soles["SALDO"]),
            f"USD $ {tot_usd['SALDO']:,.2f} (Total - Pagado)",
            border_color="#C85A32",
            text_color="#C85A32",
        )

    # Construcción de opciones de Partidas y contadores de estado
    partidas_proy_list = (
        st.session_state.partidas[st.session_state.partidas["Proyecto"] == proy_name]["Nombre_Partida"].dropna().astype(str).tolist()
        if "partidas" in st.session_state and not st.session_state.partidas.empty
        else []
    )
    opciones_partida_cont = [""] + list(dict.fromkeys(partidas_proy_list))
    for r_fc in res_calc.get("filas_contratistas", []):
        p_fc = safe_str(r_fc.get("Partida", "")).strip()
        if p_fc and p_fc not in opciones_partida_cont:
            opciones_partida_cont.append(p_fc)

    base_cont_key = f"base_df_pagos_cont_{proy_name}"
    cnt_cont_key = f"c_{base_cont_key}"
    c_cont_val = st.session_state.get(cnt_cont_key, 0)
    w_cont_key = f"ed_pagos_cont_{proy_name}_{c_cont_val}"

    base_ges_key = f"base_df_pagos_ges_{proy_name}"
    cnt_ges_key = f"c_{base_ges_key}"
    c_ges_val = st.session_state.get(cnt_ges_key, 0)
    w_ges_key = f"ed_pagos_ges_{proy_name}_{c_ges_val}"

    # Barra de herramientas rápidas sobre el Cuadro de Pagos
    opciones_filas_np = []
    mapa_filas_np = {}
    for i_fc, f_c_item in enumerate(data_cuadro.get("filas_contratistas", [])):
        lbl_f = f"👷 {i_fc + 1}. {safe_str(f_c_item.get('Descripcion', '')) or safe_str(f_c_item.get('Partida', ''))}"
        opciones_filas_np.append(lbl_f)
        mapa_filas_np[lbl_f] = ("contratista", i_fc, f_c_item)

    lbl_f_ges = "📐 Gestión y supervisión de obras"
    opciones_filas_np.append(lbl_f_ges)
    mapa_filas_np[lbl_f_ges] = ("gestion", 0, data_cuadro.get("fila_gestion", {}))

    lbl_f_gg = "📐 Gastos Generales"
    opciones_filas_np.append(lbl_f_gg)
    mapa_filas_np[lbl_f_gg] = ("gg", 0, data_cuadro.get("fila_gg", {}))

    total_notas_reg = sum(len(f.get("Notas_Pagos", {})) for f in data_cuadro.get("filas_contratistas", []))
    total_notas_reg += len(data_cuadro.get("fila_gestion", {}).get("Notas_Pagos", {}))
    total_notas_reg += len(data_cuadro.get("fila_gg", {}).get("Notas_Pagos", {}))
    btn_lbl_notas = f"💬 Notas de Pagos ({total_notas_reg})" if total_notas_reg > 0 else "💬 Notas de Pagos"

    tb_col1, tb_col2, tb_col3 = st.columns([3.4, 3.2, 3.4])
    with tb_col1:
        with st.popover("➕ Ingresar Nuevo Pago", use_container_width=True):
            st.markdown("##### 💳 Registro de Pago")
            st.caption("Ingresa rápidamente un monto de pago (y su nota opcional) para cualquier contratista o semana.")
            fila_qp_lbl = st.selectbox(
                "Partida / Contratista / Concepto:",
                options=opciones_filas_np,
                key=f"sel_fila_qp_{proy_name}",
            )
            tipo_qp, idx_qp, obj_qp = mapa_filas_np[fila_qp_lbl]
            col_qp_sel = st.selectbox(
                "Semana / Columna de Pago:",
                options=cols_pago,
                format_func=etiqueta_corta_columna_pago,
                key=f"sel_col_qp_{proy_name}",
            )
            def_con_qp = _extraer_contratista_de_notas(obj_qp.get("Notas", ""))
            contratistas_qp_list = obtener_contratistas_disponibles_proyecto(proy_name, data_cuadro)
            opts_con_qp = list(dict.fromkeys(([def_con_qp] if def_con_qp else []) + contratistas_qp_list + ["+ Escribir otro contratista..."]))
            con_qp_sel = st.selectbox(
                "Contratista:",
                options=opts_con_qp,
                key=f"sel_con_qp_{proy_name}_{fila_qp_lbl}",
            )
            if con_qp_sel == "+ Escribir otro contratista...":
                con_qp_final = st.text_input("Nombre del Contratista:", key=f"txt_con_qp_{proy_name}").strip()
            else:
                con_qp_final = safe_str(con_qp_sel).strip()
            c_tp_f1, c_tp_f2 = st.columns(2)
            with c_tp_f1:
                tipo_qp_pago = st.selectbox(
                    "Tipo de Pago:",
                    options=TIPOS_PAGO_CUADRO,
                    index=0 if "ADELANTO" in col_qp_sel else 1,
                    key=f"sel_tipo_qp_{proy_name}_{col_qp_sel}",
                )
            with c_tp_f2:
                fecha_qp_sel = st.date_input("Fecha:", value=datetime.date.today(), key=f"dt_qp_{proy_name}")
            val_qp_actual = 0.0
            qp_cnt_key = f"qp_reset_{proy_name}"
            qp_cnt_val = int(st.session_state.get(qp_cnt_key, 0) or 0)
            nota_qp_actual = (obj_qp.get("Notas_Pagos", {}) or {}).get(col_qp_sel, "") if isinstance(obj_qp.get("Notas_Pagos"), dict) else ""
            nuevo_monto_qp = st.number_input(
                f"Monto para {etiqueta_corta_columna_pago(col_qp_sel)}:",
                min_value=0.0,
                value=float(val_qp_actual),
                step=100.0,
                format="%.2f",
                key=f"num_qp_{proy_name}_{fila_qp_lbl}_{col_qp_sel}_{qp_cnt_val}",
            )
            nueva_nota_qp = st.text_input(
                "Nota del pago (opcional, visible al pasar el mouse):",
                value=nota_qp_actual,
                placeholder="",
                key=f"txt_qp_{proy_name}_{fila_qp_lbl}_{col_qp_sel}_{qp_cnt_val}",
            )
            if st.button("💾 Guardar Pago", key=f"btn_save_qp_{proy_name}", type="primary", use_container_width=True) and nuevo_monto_qp > 0 and con_qp_final:
                d_cur_qp = obtener_cuadro_pagos_semanales_proyecto(proy_name)
                if tipo_qp == "contratista":
                    fc_list = list(d_cur_qp.get("filas_contratistas", []))
                    if idx_qp < len(fc_list):
                        registrar_pago_en_fila_dict(fc_list[idx_qp], col_qp_sel, con_qp_final, tipo_qp_pago, fecha_qp_sel, nuevo_monto_qp, nota=nueva_nota_qp)
                        np_d = dict(fc_list[idx_qp].get("Notas_Pagos", {}))
                        if nueva_nota_qp.strip():
                            np_d[col_qp_sel] = nueva_nota_qp.strip()
                        else:
                            np_d.pop(col_qp_sel, None)
                        fc_list[idx_qp]["Notas_Pagos"] = np_d
                        d_cur_qp["filas_contratistas"] = fc_list
                elif tipo_qp == "gestion":
                    fg_d = dict(d_cur_qp.get("fila_gestion", {}))
                    registrar_pago_en_fila_dict(fg_d, col_qp_sel, con_qp_final, tipo_qp_pago, fecha_qp_sel, nuevo_monto_qp, nota=nueva_nota_qp)
                    np_d = dict(fg_d.get("Notas_Pagos", {}))
                    if nueva_nota_qp.strip():
                        np_d[col_qp_sel] = nueva_nota_qp.strip()
                    else:
                        np_d.pop(col_qp_sel, None)
                    fg_d["Notas_Pagos"] = np_d
                    d_cur_qp["fila_gestion"] = fg_d
                elif tipo_qp == "gg":
                    fgg_d = dict(d_cur_qp.get("fila_gg", {}))
                    registrar_pago_en_fila_dict(fgg_d, col_qp_sel, con_qp_final, tipo_qp_pago, fecha_qp_sel, nuevo_monto_qp, nota=nueva_nota_qp)
                    np_d = dict(fgg_d.get("Notas_Pagos", {}))
                    if nueva_nota_qp.strip():
                        np_d[col_qp_sel] = nueva_nota_qp.strip()
                    else:
                        np_d.pop(col_qp_sel, None)
                    fgg_d["Notas_Pagos"] = np_d
                    d_cur_qp["fila_gg"] = fgg_d
                d_cur_qp["semana_activa"] = col_qp_sel
                st.session_state[f"sel_sem_resumen_{proy_name}"] = col_qp_sel
                guardar_cuadro_pagos_semanales_proyecto(proy_name, d_cur_qp)
                st.session_state[qp_cnt_key] = qp_cnt_val + 1
                st.session_state[cnt_cont_key] = st.session_state.get(cnt_cont_key, 0) + 1
                st.session_state[cnt_ges_key] = st.session_state.get(cnt_ges_key, 0) + 1
                st.rerun()

    with tb_col2:
        with st.popover(btn_lbl_notas, use_container_width=True):
            st.markdown("##### 💬 Notas y Detalle de Pagos")
            st.caption("Registra notas o motivos sobre cualquier desembolso (Adelanto o S1, S2...). Al pasar el mouse sobre el pago en el cuadro, la nota aparecerá flotando.")

            fila_sel_lbl = st.selectbox(
                "Concepto / Fila:",
                options=opciones_filas_np,
                key=f"sel_fila_np_{proy_name}",
            )
            tipo_f_sel, idx_f_sel, obj_f_sel = mapa_filas_np[fila_sel_lbl]
            mon_sel = safe_str(obj_f_sel.get("Moneda", "Soles"))
            pref_sel = "US$ " if "dólar" in mon_sel.lower() or "dolar" in mon_sel.lower() else "S/ "

            def _fmt_col_np(c_n):
                m_val = safe_float(obj_f_sel.get(c_n, 0.0), 0.0)
                np_dict_curr = obj_f_sel.get("Notas_Pagos", {})
                has_badge = " [✓ Tiene Nota]" if (isinstance(np_dict_curr, dict) and c_n in np_dict_curr and np_dict_curr[c_n]) else ""
                return f"{etiqueta_corta_columna_pago(c_n)} ({pref_sel}{m_val:,.2f}){has_badge}"

            col_sel_pago = st.selectbox(
                "Semana / Desembolso:",
                options=cols_pago,
                format_func=_fmt_col_np,
                key=f"sel_col_pago_np_{proy_name}",
            )

            np_dict_f = obj_f_sel.get("Notas_Pagos", {})
            nota_existente = np_dict_f.get(col_sel_pago, "") if isinstance(np_dict_f, dict) else ""

            txt_nota_input = st.text_area(
                f"Detalle / Motivo del pago ({etiqueta_corta_columna_pago(col_sel_pago)}):",
                value=nota_existente,
                placeholder="",
                key=f"txt_nota_p_{proy_name}_{fila_sel_lbl}_{col_sel_pago}",
                height=90,
            )

            c_btn_n1, c_btn_n2 = st.columns(2)
            with c_btn_n1:
                if st.button("💾 Guardar Nota", key=f"btn_save_np_{proy_name}", type="primary", use_container_width=True):
                    d_cur_np = obtener_cuadro_pagos_semanales_proyecto(proy_name)
                    if tipo_f_sel == "contratista":
                        filas_c_np = list(d_cur_np.get("filas_contratistas", []))
                        if idx_f_sel < len(filas_c_np):
                            cur_np = dict(filas_c_np[idx_f_sel].get("Notas_Pagos", {}))
                            if txt_nota_input.strip():
                                cur_np[col_sel_pago] = txt_nota_input.strip()
                            else:
                                cur_np.pop(col_sel_pago, None)
                            filas_c_np[idx_f_sel]["Notas_Pagos"] = cur_np
                            d_cur_np["filas_contratistas"] = filas_c_np
                    elif tipo_f_sel == "gestion":
                        fg_np = dict(d_cur_np.get("fila_gestion", {}))
                        cur_np = dict(fg_np.get("Notas_Pagos", {}))
                        if txt_nota_input.strip():
                            cur_np[col_sel_pago] = txt_nota_input.strip()
                        else:
                            cur_np.pop(col_sel_pago, None)
                        fg_np["Notas_Pagos"] = cur_np
                        d_cur_np["fila_gestion"] = fg_np
                    elif tipo_f_sel == "gg":
                        fgg_np = dict(d_cur_np.get("fila_gg", {}))
                        cur_np = dict(fgg_np.get("Notas_Pagos", {}))
                        if txt_nota_input.strip():
                            cur_np[col_sel_pago] = txt_nota_input.strip()
                        else:
                            cur_np.pop(col_sel_pago, None)
                        fgg_np["Notas_Pagos"] = cur_np
                        d_cur_np["fila_gg"] = fgg_np

                    guardar_cuadro_pagos_semanales_proyecto(proy_name, d_cur_np)
                    st.session_state[cnt_cont_key] = st.session_state.get(cnt_cont_key, 0) + 1
                    st.session_state[cnt_ges_key] = st.session_state.get(cnt_ges_key, 0) + 1
                    st.rerun()

            with c_btn_n2:
                if nota_existente:
                    if st.button("🗑️ Borrar Nota", key=f"btn_del_np_{proy_name}", use_container_width=True):
                        d_cur_np = obtener_cuadro_pagos_semanales_proyecto(proy_name)
                        if tipo_f_sel == "contratista":
                            filas_c_np = list(d_cur_np.get("filas_contratistas", []))
                            if idx_f_sel < len(filas_c_np):
                                cur_np = dict(filas_c_np[idx_f_sel].get("Notas_Pagos", {}))
                                cur_np.pop(col_sel_pago, None)
                                filas_c_np[idx_f_sel]["Notas_Pagos"] = cur_np
                                d_cur_np["filas_contratistas"] = filas_c_np
                        elif tipo_f_sel == "gestion":
                            fg_np = dict(d_cur_np.get("fila_gestion", {}))
                            cur_np = dict(fg_np.get("Notas_Pagos", {}))
                            cur_np.pop(col_sel_pago, None)
                            fg_np["Notas_Pagos"] = cur_np
                            d_cur_np["fila_gestion"] = fg_np
                        elif tipo_f_sel == "gg":
                            fgg_np = dict(d_cur_np.get("fila_gg", {}))
                            cur_np = dict(fgg_np.get("Notas_Pagos", {}))
                            cur_np.pop(col_sel_pago, None)
                            fgg_np["Notas_Pagos"] = cur_np
                            d_cur_np["fila_gg"] = fgg_np

                        guardar_cuadro_pagos_semanales_proyecto(proy_name, d_cur_np)
                        st.session_state[cnt_cont_key] = st.session_state.get(cnt_cont_key, 0) + 1
                        st.session_state[cnt_ges_key] = st.session_state.get(cnt_ges_key, 0) + 1
                        st.rerun()

            todas_np_pop = []
            for i_fc, f_c_item in enumerate(data_cuadro.get("filas_contratistas", [])):
                desc_f = safe_str(f_c_item.get("Descripcion", "")) or safe_str(f_c_item.get("Partida", f"Fila {i_fc+1}"))
                for col_k, txt_k in f_c_item.get("Notas_Pagos", {}).items():
                    if txt_k:
                        todas_np_pop.append((desc_f, etiqueta_corta_columna_pago(col_k), txt_k))
            for desc_g, obj_g in [("Gestión y supervisión de obras", data_cuadro.get("fila_gestion", {})), ("Gastos Generales", data_cuadro.get("fila_gg", {}))]:
                for col_k, txt_k in obj_g.get("Notas_Pagos", {}).items():
                    if txt_k:
                        todas_np_pop.append((desc_g, etiqueta_corta_columna_pago(col_k), txt_k))

            if todas_np_pop:
                st.divider()
                st.markdown(f"**Notas registradas ({len(todas_np_pop)}):**")
                for f_nom, sem_k, txt_k in todas_np_pop:
                    st.caption(f"• **{f_nom}** ({sem_k}): *\"{txt_k}\"*")

    with tb_col3:
        with st.popover("➕ Agregar Contratista / Sub-partida", use_container_width=True):
            st.caption("Agrega otra fila asociada a una misma Partida.")
            with st.form(f"frm_add_sub_cont_{proy_name}", clear_on_submit=True):
                part_sel_new = st.selectbox(
                    "Partida Asociada:",
                    options=partidas_proy_list if partidas_proy_list else ["General"],
                )
                contratistas_sug_list = (
                    st.session_state.maestro["ID_Contratista"].dropna().astype(str).tolist()
                    if "maestro" in st.session_state and not st.session_state.maestro.empty
                    else []
                )
                desc_sub_new = st.text_input(
                    "Contratista / Especialidad:",
                    placeholder="",
                )
                contra_ref = st.selectbox(
                    "O elegir Contratista de Base de Datos (opcional):",
                    options=["(Escribir arriba)"] + contratistas_sug_list,
                )
                c_m1, c_m2 = st.columns(2)
                with c_m1:
                    mon_sub_new = st.selectbox("Moneda:", ["Soles", "Dólares"])
                with c_m2:
                    tot_sub_new = st.number_input("Total Pactado:", min_value=0.0, value=0.0, step=100.0)
                if st.form_submit_button("➕ AGREGAR FILA A LA PARTIDA", type="primary", use_container_width=True):
                    etiqueta_final = desc_sub_new.strip()
                    if contra_ref != "(Escribir arriba)":
                        etiqueta_final = f"{etiqueta_final} ({contra_ref})" if etiqueta_final else contra_ref
                    if not etiqueta_final:
                        etiqueta_final = f"{part_sel_new} — Sub-contratista"
                    d_cur_add = obtener_cuadro_pagos_semanales_proyecto(proy_name)
                    nueva_fila_c = {
                        "Partida": part_sel_new,
                        "Descripcion": etiqueta_final,
                        "Moneda": mon_sub_new,
                        "TOTAL": float(tot_sub_new),
                        "Notas": "",
                    }
                    for c_s in cols_pago:
                        nueva_fila_c[c_s] = 0.0
                    filas_act = list(d_cur_add.get("filas_contratistas", []))
                    insert_pos = len(filas_act)
                    for idx_f, f_ex in enumerate(filas_act):
                        if safe_str(f_ex.get("Partida", "")).strip() == part_sel_new:
                            insert_pos = idx_f + 1
                    filas_act.insert(insert_pos, nueva_fila_c)
                    d_cur_add["filas_contratistas"] = filas_act
                    guardar_cuadro_pagos_semanales_proyecto(proy_name, d_cur_add)
                    st.session_state[cnt_cont_key] = c_cont_val + 1
                    st.rerun()

    # =========================================================================
    # 1. CUADRO PRINCIPAL EDITABLE CON COLORES ARCILLA Y ROJO (Normal + Pantalla Completa)
    # =========================================================================
    # Puente oculto para persistir ediciones hechas directamente sobre las celdas del cuadro coloreado
    bridge_key = f"pagos_inline_bridge_{proy_name}"

    def _on_inline_pagos_bridge_change(p_name: str, b_key: str):
        raw_val = st.session_state.get(b_key, "")
        if raw_val:
            aplicar_edicion_inline_cuadro_pagos(p_name, raw_val)
            st.session_state[b_key] = ""

    st.markdown(
        f"""
        <style>
        div[data-testid="stTextInput"]:has(input[aria-label="PAGOS_BRIDGE_{safe_proy_id}"]) {{
            position: absolute !important;
            width: 1px !important;
            height: 1px !important;
            overflow: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
            margin: 0 !important;
            padding: 0 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.text_input(
        f"PAGOS_BRIDGE_{safe_proy_id}",
        key=bridge_key,
        label_visibility="collapsed",
        on_change=_on_inline_pagos_bridge_change,
        args=(proy_name, bridge_key),
    )

    border_grid = "1px solid #B8B0A4"
    border_clay = "1px solid rgba(255,255,255,0.22)"

    cnt_pagos_sem = {c: len(obtener_pagos_semana(data_cuadro, c)) for c in cols_pago}
    ths_semanas_list = []
    for c_s in cols_pago:
        lbl_short = html_lib.escape(etiqueta_corta_columna_pago(c_s))
        esc_col_attr = html_lib.escape(c_s, quote=True)
        n_p_wk = cnt_pagos_sem.get(c_s, 0)
        wk_cnt_tag = f" <span style='font-size:9.5px; background:rgba(255,255,255,0.22); border-radius:99px; padding:0 5px;'>{n_p_wk}</span>" if n_p_wk > 0 else ""
        if c_s in cols_por_pagar_actual:
            ths_semanas_list.append(
                f"<th class='cota-week-hdr-clickable' data-cota-week-header='{esc_col_attr}' title='Haz clic para ver pagos realizados en {lbl_short}' "
                f"style='padding:7px 9px; text-align:center; border:{border_clay}; min-width:86px; cursor:pointer;'>"
                f"<div>{lbl_short}{wk_cnt_tag}</div>"
                f"<div><span class='cota-pp-pill-btn is-pp' data-cota-toggle-pp-pill='{esc_col_attr}' title='Clic para marcar como Pagado (Rojo)'>⏳ Por Pagar</span></div>"
                f"</th>"
            )
        else:
            ths_semanas_list.append(
                f"<th class='cota-week-hdr-clickable' data-cota-week-header='{esc_col_attr}' title='Haz clic para ver pagos realizados en {lbl_short}' "
                f"style='padding:7px 9px; text-align:center; border:{border_clay}; min-width:82px; cursor:pointer;'><div>{lbl_short}{wk_cnt_tag}</div><div><span class='cota-pp-pill-btn' data-cota-toggle-pp-pill='{esc_col_attr}' title='Clic para marcar {lbl_short} como Por Pagar'>⏳</span></div></th>"
            )
    ths_semanas_html = "".join(ths_semanas_list)

    def _build_payment_cells_html(fila_d: dict, pref_m: str, part_label: str, r_type: str, r_idx: int) -> str:
        np_dict_r = fila_d.get("Notas_Pagos", {}) if isinstance(fila_d.get("Notas_Pagos"), dict) else {}
        tds = []
        esc_part = html_lib.escape(part_label, quote=True)
        esc_pref = html_lib.escape(pref_m, quote=True)
        for c_s in cols_pago:
            v_num = safe_float(fila_d.get(c_s, 0.0), 0.0)
            is_zero = abs(v_num) < 0.005
            is_pp = c_s in cols_por_pagar_actual
            # Pagos realizados de semanas pasadas en ROJO (#D92B2B); semanas "Por Pagar" en negro/carbón (#262320)
            color_txt = "#262320" if is_pp else "#D92B2B"
            val_str = "" if is_zero else f"{pref_m}{v_num:,.2f}"
            nota_manual_txt = safe_str(np_dict_r.get(c_s, "")).strip()
            disp_inner_c, corner_dot_c, tooltip_full_c, pagos_celda_c, def_con_c = build_cell_payments_badge_and_tooltip(
                fila_d, c_s, pref_m, v_num
            )
            esc_pay_json = html_lib.escape(json.dumps(pagos_celda_c, ensure_ascii=False), quote=True).replace("\r\n", "&#10;").replace("\r", "&#10;").replace("\n", "&#10;")
            esc_def_con = html_lib.escape(def_con_c, quote=True)
            esc_nota_man = html_lib.escape(nota_manual_txt, quote=True).replace("\r\n", "&#10;").replace("\r", "&#10;").replace("\n", "&#10;")
            nota_txt = tooltip_full_c
            esc_sem_short = html_lib.escape(etiqueta_corta_columna_pago(c_s), quote=True)
            esc_col_f = html_lib.escape(c_s, quote=True)
            esc_mon = html_lib.escape(f"{pref_m}{v_num:,.2f}", quote=True)

            if nota_txt:
                esc_not = html_lib.escape(nota_txt, quote=True).replace("\r\n", "&#10;").replace("\r", "&#10;").replace("\n", "&#10;")
                disp_inner = disp_inner_c
                tds.append(
                    f"<td class='cota-editable-cell' data-row-type='{r_type}' data-row-idx='{r_idx}' "
                    f"data-col-field='{esc_col_f}' data-raw-val='{v_num:.2f}' data-is-pp='{'1' if is_pp else '0'}' data-pref='{esc_pref}' "
                    f"data-cota-note-partida='{esc_part}' data-cota-note-semana='{esc_sem_short}' "
                    f"data-cota-note-monto='{esc_mon}' data-cota-note-text='{esc_not}' data-cota-payments-json='{esc_pay_json}' data-cota-default-contractor='{esc_def_con}' data-cota-note-manual='{esc_nota_man}' "
                    f"style='position:relative; padding:6px 9px; text-align:right; border:{border_grid}; color:{color_txt}; font-weight:600; font-variant-numeric:tabular-nums; background:#FFFDF9;'>"
                    f"<span class='cota-cell-total-txt' style='color:inherit;'>{disp_inner}</span>"
                    f"{corner_dot_c}"
                    f"</td>"
                )
            else:
                tds.append(
                    f"<td class='cota-editable-cell' data-row-type='{r_type}' data-row-idx='{r_idx}' "
                    f"data-col-field='{esc_col_f}' data-raw-val='{v_num:.2f}' data-is-pp='{'1' if is_pp else '0'}' data-pref='{esc_pref}' "
                    f"data-cota-note-partida='{esc_part}' data-cota-note-semana='{esc_sem_short}' "
                    f"data-cota-payments-json='{esc_pay_json}' data-cota-default-contractor='{esc_def_con}' "
                    f"style='position:relative; padding:6px 9px; text-align:right; border:{border_grid}; color:{color_txt}; font-weight:600; font-variant-numeric:tabular-nums;'><span class='cota-cell-total-txt' style='color:inherit;'>{val_str}</span></td>"
                )
        return "".join(tds)

    trs_body = []
    # Fila de sección: TRABAJOS CONTRATISTAS (con botón directo para agregar fila)
    empty_sem_section = "".join(f"<td style='padding:6px 9px; border:{border_grid};'></td>" for _ in cols_pago)
    trs_body.append(
        f"<tr style='background:#FFFFFF;'>"
        f"<td style='padding:7px 12px; text-align:left; border:{border_grid}; position:sticky; left:0; background:#FFFFFF; z-index:1;'>"
        f"<div style='display:flex; justify-content:space-between; align-items:center; gap:8px;'>"
        f"<span style='font-weight:800; color:#262320; text-decoration:underline;'>TRABAJOS CONTRATISTAS</span>"
        f"<button type='button' data-cota-action='add-row' title='Agregar otra fila de contratista en este cuadro' "
        f"style='background:#FAF8F5; color:#C85A32; border:1px solid #DFD9CE; border-radius:5px; padding:2px 8px; font-size:11px; font-weight:700; cursor:pointer;'>+ Fila</button>"
        f"</div>"
        f"</td>"
        f"<td style='padding:6px 8px; border:{border_grid};'></td>"
        f"<td style='padding:6px 9px; border:{border_grid};'></td>"
        f"{empty_sem_section}"
        f"<td style='padding:6px 9px; border:{border_grid};'></td>"
        f"<td style='padding:6px 9px; border:{border_grid};'></td>"
        f"</tr>"
    )

    # Filas de Contratistas / Partidas (100% editables en el mismo cuadro)
    n_filas_c = len(res_calc["filas_contratistas"])
    for idx_fc, f_c in enumerate(res_calc["filas_contratistas"]):
        part_s = safe_str(f_c.get("Partida", "")).strip()
        desc_s = safe_str(f_c.get("Descripcion", "")).strip()
        lbl_row = f"{part_s} — {desc_s}" if (part_s and desc_s and part_s.upper() not in desc_s.upper()) else (desc_s or part_s)
        nota_gral = safe_str(f_c.get("Notas", "")).strip()
        mon_c = safe_str(f_c.get("Moneda", "Soles"))
        es_usd_c = "dólar" in mon_c.lower() or "dolar" in mon_c.lower()
        pref_c = "$" if es_usd_c else "S/ "
        tot_c_val = safe_float(f_c.get("TOTAL", 0.0), 0.0)

        del_btn_html = (
            f"<button type='button' class='cota-row-del-btn' data-cota-action='del-row' data-row-idx='{idx_fc}' title='Eliminar esta fila'>✕</button>"
            if n_filas_c > 1
            else ""
        )
        sub_nota_disp = "block" if nota_gral else "none"
        sub_nota_html = (
            f"<span class='cota-desc-sub' style='display:{sub_nota_disp}; font-size:10.5px; color:#7A7267; font-weight:500; margin-top:1px;'>{html_lib.escape(nota_gral)}</span>"
        )
        tds_sem_c = _build_payment_cells_html(f_c, pref_c, lbl_row, "contratista", idx_fc)
        esc_raw_desc = html_lib.escape(lbl_row, quote=True)
        esc_raw_notas = html_lib.escape(nota_gral, quote=True)
        esc_mon_c = html_lib.escape(mon_c, quote=True)
        esc_pref_c = html_lib.escape(pref_c, quote=True)

        trs_body.append(
            f"<tr data-row-type='contratista' data-row-idx='{idx_fc}' style='background:#FFFFFF; color:#262320;'>"
            f"<td class='cota-editable-cell' data-row-type='contratista' data-row-idx='{idx_fc}' data-col-field='Descripcion' "
            f"data-raw-desc='{esc_raw_desc}' data-raw-notas='{esc_raw_notas}' title='Haz clic para editar nombre o contratista' "
            f"style='padding:6px 12px; text-align:left; border:{border_grid}; font-weight:500; position:sticky; left:0; background:#FFFFFF; z-index:1;'>"
            f"<div style='display:flex; justify-content:space-between; align-items:flex-start; gap:6px;'>"
            f"<div><span class='cota-desc-title'>{html_lib.escape(lbl_row)}</span>{sub_nota_html}</div>"
            f"{del_btn_html}"
            f"</div>"
            f"</td>"
            f"<td class='cota-editable-cell' data-row-type='contratista' data-row-idx='{idx_fc}' data-col-field='Moneda' data-raw-val='{esc_mon_c}' "
            f"title='Haz clic para alternar Soles / Dólares' style='padding:6px 8px; text-align:center; border:{border_grid};'>{html_lib.escape(mon_c)}</td>"
            f"<td class='cota-editable-cell' data-row-type='contratista' data-row-idx='{idx_fc}' data-col-field='TOTAL' data-raw-val='{tot_c_val:.2f}' data-pref='{esc_pref_c}' "
            f"title='Haz clic para editar el monto TOTAL pactado' style='padding:6px 9px; text-align:right; border:{border_grid}; font-variant-numeric:tabular-nums;'>{pref_c}{tot_c_val:,.2f}</td>"
            f"{tds_sem_c}"
            f"<td data-calc-role='row-pagado' style='padding:6px 9px; text-align:right; border:{border_grid}; font-variant-numeric:tabular-nums;'>{pref_c}{safe_float(f_c.get('PAGADO', 0.0)):,.2f}</td>"
            f"<td data-calc-role='row-saldo' style='padding:6px 9px; text-align:right; border:{border_grid}; font-variant-numeric:tabular-nums;'>{pref_c}{safe_float(f_c.get('SALDO', 0.0)):,.2f}</td>"
            f"</tr>"
        )

    # Fila SUB TOTAL (Color Arcilla Cota #C85A32 + Texto Blanco)
    tds_sub_sem = "".join(
        f"<td data-sum-col='{html_lib.escape(c_s, quote=True)}' style='padding:7px 9px; text-align:right; border:{border_clay}; font-weight:700; font-variant-numeric:tabular-nums;'>S/ {safe_float(sub_cont.get(c_s, 0.0)):,.2f}</td>"
        for c_s in cols_pago
    )
    trs_body.append(
        f"<tr data-summary-row='subtotal' style='background:#C85A32; color:#FFFFFF; font-weight:700;'>"
        f"<td style='padding:7px 12px; text-align:center; border:{border_clay}; font-weight:800; position:sticky; left:0; background:#C85A32; z-index:1;'>SUB TOTAL</td>"
        f"<td style='padding:7px 8px; text-align:center; border:{border_clay};'></td>"
        f"<td data-sum-col='TOTAL' style='padding:7px 9px; text-align:right; border:{border_clay}; font-weight:800; font-variant-numeric:tabular-nums;'>S/ {safe_float(sub_cont.get('TOTAL', 0.0)):,.2f}</td>"
        f"{tds_sub_sem}"
        f"<td data-sum-col='PAGADO' style='padding:7px 9px; text-align:right; border:{border_clay}; font-weight:800; font-variant-numeric:tabular-nums;'>S/ {safe_float(sub_cont.get('PAGADO', 0.0)):,.2f}</td>"
        f"<td data-sum-col='SALDO' style='padding:7px 9px; text-align:right; border:{border_clay}; font-weight:800; font-variant-numeric:tabular-nums;'>S/ {safe_float(sub_cont.get('SALDO', 0.0)):,.2f}</td>"
        f"</tr>"
    )

    # Filas Gestión y supervisión de obras & Gastos Generales (también editables directamente en el cuadro)
    for r_type_cargo, nom_cargo, fila_cargo in [
        ("gestion", "Gestión y supervisión de obras", res_calc["fila_gestion"]),
        ("gg", "Gastos Generales", res_calc["fila_gg"]),
    ]:
        mon_g = safe_str(fila_cargo.get("Moneda", "Soles"))
        es_usd_g = "dólar" in mon_g.lower() or "dolar" in mon_g.lower()
        pref_g = "$" if es_usd_g else "S/ "
        tot_g_val = safe_float(fila_cargo.get("TOTAL", 0.0), 0.0)
        esc_mon_g = html_lib.escape(mon_g, quote=True)
        esc_pref_g = html_lib.escape(pref_g, quote=True)

        tds_sem_g = _build_payment_cells_html(fila_cargo, pref_g, nom_cargo, r_type_cargo, 0)
        trs_body.append(
            f"<tr data-row-type='{r_type_cargo}' data-row-idx='0' style='background:#FFFFFF; color:#262320;'>"
            f"<td style='padding:6px 12px; text-align:left; border:{border_grid}; font-weight:500; position:sticky; left:0; background:#FFFFFF; z-index:1;'>{html_lib.escape(nom_cargo)}</td>"
            f"<td class='cota-editable-cell' data-row-type='{r_type_cargo}' data-row-idx='0' data-col-field='Moneda' data-raw-val='{esc_mon_g}' "
            f"title='Haz clic para alternar Soles / Dólares' style='padding:6px 8px; text-align:center; border:{border_grid};'>{html_lib.escape(mon_g)}</td>"
            f"<td class='cota-editable-cell' data-row-type='{r_type_cargo}' data-row-idx='0' data-col-field='TOTAL' data-raw-val='{tot_g_val:.2f}' data-pref='{esc_pref_g}' "
            f"title='Haz clic para editar el monto TOTAL' style='padding:6px 9px; text-align:right; border:{border_grid}; font-variant-numeric:tabular-nums;'>{pref_g}{tot_g_val:,.2f}</td>"
            f"{tds_sem_g}"
            f"<td data-calc-role='row-pagado' style='padding:6px 9px; text-align:right; border:{border_grid}; font-variant-numeric:tabular-nums;'>{pref_g}{safe_float(fila_cargo.get('PAGADO', 0.0)):,.2f}</td>"
            f"<td data-calc-role='row-saldo' style='padding:6px 9px; text-align:right; border:{border_grid}; font-variant-numeric:tabular-nums;'>{pref_g}{safe_float(fila_cargo.get('SALDO', 0.0)):,.2f}</td>"
            f"</tr>"
        )

    # Filas TOTAL (Soles y Dólares) en Color Arcilla Cota #C85A32 con celda PAGADO resaltada en amarillo (#FFE066)
    for sum_key, lbl_tot, mon_tot, pref_t, d_tot in [
        ("total_soles", "TOTAL", "Soles", "S/ ", tot_soles),
        ("total_usd", "", "Dólares", "$", tot_usd),
    ]:
        tds_tot_sem = "".join(
            f"<td data-sum-col='{html_lib.escape(c_s, quote=True)}' style='padding:7px 9px; text-align:right; border:{border_clay}; font-weight:700; font-variant-numeric:tabular-nums;'>{pref_t}{safe_float(d_tot.get(c_s, 0.0)):,.2f}</td>"
            for c_s in cols_pago
        )
        trs_body.append(
            f"<tr data-summary-row='{sum_key}' style='background:#C85A32; color:#FFFFFF; font-weight:700;'>"
            f"<td style='padding:7px 12px; text-align:center; border:{border_clay}; font-weight:800; position:sticky; left:0; background:#C85A32; z-index:1;'>{lbl_tot}</td>"
            f"<td style='padding:7px 8px; text-align:center; border:{border_clay}; font-weight:700;'>{mon_tot}</td>"
            f"<td data-sum-col='TOTAL' style='padding:7px 9px; text-align:right; border:{border_clay}; font-weight:800; font-variant-numeric:tabular-nums;'>{pref_t}{safe_float(d_tot.get('TOTAL', 0.0)):,.2f}</td>"
            f"{tds_tot_sem}"
            f"<td data-sum-col='PAGADO' style='padding:7px 9px; text-align:right; border:1px solid #262320; background:#FFE066; color:#262320; font-weight:800; font-variant-numeric:tabular-nums;'>{pref_t}{safe_float(d_tot.get('PAGADO', 0.0)):,.2f}</td>"
            f"<td data-sum-col='SALDO' style='padding:7px 9px; text-align:right; border:{border_clay}; font-weight:800; font-variant-numeric:tabular-nums;'>{pref_t}{safe_float(d_tot.get('SALDO', 0.0)):,.2f}</td>"
            f"</tr>"
        )

    esc_proy_banner = html_lib.escape(proy_name)
    esc_cli_banner = html_lib.escape(cliente_str)
    html_cuadro_unificado = (
        f"<div id='cota_cuadro_pagos_fs_wrap_{safe_proy_id}' style='border:1px solid #B8B0A4; border-radius:10px; overflow:hidden; margin-top:6px; margin-bottom:14px; box-shadow:0 4px 14px rgba(38,35,32,0.08); background:#FFFFFF;'>"
        f"<div style='background:#C85A32; color:#FFFFFF; padding:11px 16px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; border-bottom:2px solid #A84622;'>"
        f"<div>"
        f"<div style='font-size:15.5px; font-weight:800; letter-spacing:0.2px;'>Proyecto {esc_proy_banner}</div>"
        f"<div style='font-size:12.5px; color:#FAF8F5; opacity:0.95;'>Cliente: {esc_cli_banner} &nbsp;·&nbsp; TC: S/ {tc_actual:.2f}</div>"
        f"</div>"
        f"<div style='display:flex; align-items:center; gap:10px; flex-wrap:wrap;'>"
        f"<span style='font-size:11px; color:#FAF8F5; background:rgba(38,35,32,0.18); padding:4px 9px; border-radius:5px;'>💳 Clic en celda para registrar pagos &nbsp;·&nbsp; 📅 Clic en semana para ver pagos &nbsp;·&nbsp; 🔴 Rojo = Pagado</span>"
        f"<button id='btn_fs_pagos_{safe_proy_id}' type='button' title='Ver y editar Cuadro en Pantalla Completa (como en YouTube / Excel)' "
        f"style='background:rgba(38,35,32,0.28); color:#FFFFFF; border:1px solid rgba(255,255,255,0.45); border-radius:6px; padding:6px 12px; font-size:12px; font-weight:700; cursor:pointer; display:inline-flex; align-items:center; transition:background 0.15s ease;'>"
        f"<svg width='15' height='15' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round' style='vertical-align:middle; margin-right:5px;'><path d='M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3'/></svg>"
        f"<span>Pantalla Completa</span>"
        f"</button>"
        f"</div>"
        f"</div>"
        f"<div class='cota-pagos-scroll-area' style='overflow-x:auto; width:100%;'>"
        f"<table style='width:100%; border-collapse:collapse; font-size:12.5px; white-space:nowrap; font-family:-apple-system,BlinkMacSystemFont,\"Segoe UI\",Roboto,sans-serif;'>"
        f"<thead>"
        f"<tr style='background:#C85A32; color:#FFFFFF; font-size:12px; font-weight:700;'>"
        f"<th style='padding:8px 12px; text-align:left; border:{border_clay}; min-width:210px; position:sticky; left:0; background:#C85A32; z-index:2;'>Descripción</th>"
        f"<th style='padding:8px 8px; text-align:center; border:{border_clay}; min-width:66px;'>Moneda</th>"
        f"<th style='padding:8px 9px; text-align:center; border:{border_clay}; min-width:95px;'>TOTAL</th>"
        f"{ths_semanas_html}"
        f"<th style='padding:8px 9px; text-align:center; border:{border_clay}; min-width:95px;'>PAGADO</th>"
        f"<th style='padding:8px 9px; text-align:center; border:{border_clay}; min-width:95px;'>SALDO</th>"
        f"</tr>"
        f"</thead>"
        f"<tbody>{''.join(trs_body)}</tbody>"
        f"</table>"
        f"</div>"
        f"</div>"
    )
    st.markdown(html_cuadro_unificado, unsafe_allow_html=True)

    opciones_sem_panel = list(cols_pago) + ["ALL"]
    sel_sem_key_ui = f"sel_sem_resumen_{proy_name}"
    if sel_sem_key_ui not in st.session_state or st.session_state[sel_sem_key_ui] not in opciones_sem_panel:
        st.session_state[sel_sem_key_ui] = sem_activa_ui

    def _on_sem_panel_change():
        new_w = safe_str(st.session_state.get(sel_sem_key_ui, "")).strip()
        if new_w:
            d_upd = obtener_cuadro_pagos_semanales_proyecto(proy_name)
            d_upd["semana_activa"] = new_w
            guardar_cuadro_pagos_semanales_proyecto(proy_name, d_upd)

    sem_sel_panel = st.radio(
        "📅 Selecciona una semana para ver sus pagos realizados (y el resumen incluido al exportar):",
        options=opciones_sem_panel,
        format_func=lambda c: "Todas las semanas" if c == "ALL" else etiqueta_export_columna_pago(c),
        horizontal=True,
        key=sel_sem_key_ui,
        on_change=_on_sem_panel_change,
    )
    render_pagos_realizados_por_semana_panel(proy_name, data_cuadro, cols_pago, sem_sel_panel)

    # 2. Sección de Notas Registradas (Expander visible con tarjetas para acceso directo)
    todas_las_notas = []
    for idx_f, f_item in enumerate(data_cuadro.get("filas_contratistas", [])):
        nom = safe_str(f_item.get("Descripcion", "")) or safe_str(f_item.get("Partida", f"Partida {idx_f+1}"))
        mon = safe_str(f_item.get("Moneda", "Soles"))
        pref = "US$ " if "dólar" in mon.lower() or "dolar" in mon.lower() else "S/ "
        for c_sem, txt_n in f_item.get("Notas_Pagos", {}).items():
            if txt_n:
                monto_val = safe_float(f_item.get(c_sem, 0.0), 0.0)
                todas_las_notas.append({
                    "fila": nom,
                    "semana": etiqueta_corta_columna_pago(c_sem),
                    "monto": f"{pref}{monto_val:,.2f}",
                    "nota": txt_n,
                })
    for obj_g, nom_g in [(data_cuadro.get("fila_gestion", {}), "Gestión y supervisión de obras"), (data_cuadro.get("fila_gg", {}), "Gastos Generales")]:
        mon = safe_str(obj_g.get("Moneda", "Soles"))
        pref = "US$ " if "dólar" in mon.lower() or "dolar" in mon.lower() else "S/ "
        for c_sem, txt_n in obj_g.get("Notas_Pagos", {}).items():
            if txt_n:
                monto_val = safe_float(obj_g.get(c_sem, 0.0), 0.0)
                todas_las_notas.append({
                    "fila": nom_g,
                    "semana": etiqueta_corta_columna_pago(c_sem),
                    "monto": f"{pref}{monto_val:,.2f}",
                    "nota": txt_n,
                })

    if todas_las_notas:
        with st.expander(f"📝 Notas Registradas en Pagos ({len(todas_las_notas)})", expanded=False):
            st.caption("Pasa el mouse sobre cualquier celda con marca naranja en el cuadro de arriba para ver su nota flotante, o haz clic directamente en la celda para editarla.")
            n_cols_card = min(3, len(todas_las_notas))
            c_cards = st.columns(n_cols_card)
            for idx_nc, n_card in enumerate(todas_las_notas):
                with c_cards[idx_nc % n_cols_card]:
                    esc_part = html_lib.escape(n_card['fila'])
                    esc_sem = html_lib.escape(n_card['semana'])
                    esc_monto = html_lib.escape(n_card['monto'])
                    esc_body = html_lib.escape(n_card['nota'])
                    st.markdown(
                        f"<div style='background:#FAF8F5; border-left:4px solid #C85A32; border-radius:6px; padding:9px 12px; margin-bottom:8px; box-shadow:0 1px 3px rgba(0,0,0,0.04);'>"
                        f"<div style='display:flex; justify-content:space-between; align-items:center;'><span style='font-size:10.5px; font-weight:800; color:#C85A32; text-transform:uppercase;'>💬 {esc_sem}</span><span style='font-size:11px; font-weight:700; color:#4A7C59;'>{esc_monto}</span></div>"
                        f"<div style='font-size:12.5px; font-weight:700; color:#262320; margin-top:3px;'>{esc_part}</div>"
                        f"<div style='font-size:12px; color:#494541; margin-top:4px; font-style:italic; line-height:1.3;'>\"{esc_body}\"</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

    # Inyectar el controlador de edición en vivo, Pantalla Completa y tooltips flotantes
    _render_pagos_tooltip_controller(proy_name, safe_proy_id, data_cuadro, cols_pago)


def _render_tab_finanzas(proy_name, proy_data):
    """Pestaña 6: Cuadro de Pagos Semanales por Partida/Contratista, Hitos de Cobro al Cliente y Caja Chica."""
    st.markdown("### 💰 COBROS, PAGOS SEMANALES Y FINANZAS")
    st.caption("Control de pagos semanales por partida/contratista (exportable a Excel para el cliente), hitos de cobro y caja chica.")

    # 1. Cuadro de Pagos Semanales por Partida / Contratista
    _render_cuadro_pagos_semanales(proy_name, proy_data)

    st.divider()
    st.markdown("#### 🧾 HITOS DE COBRO CONTRACTUAL AL CLIENTE")

    # Inicializar cobros si no existe
    if 'cobros' not in st.session_state:
        st.session_state.cobros = pd.DataFrame(columns=COLS_COBROS)

    df_cobros_p = st.session_state.cobros[st.session_state.cobros['Proyecto'] == proy_name].copy()

    col_btn1, _ = st.columns([3, 7])
    with col_btn1:
        with st.popover("➕ REGISTRAR HITO DE COBRO", use_container_width=True):
            with st.form(f"f_new_cobro_{proy_name}", clear_on_submit=True):
                c_hito = st.text_input("Hito / Concepto de Cobro", placeholder="")
                c_tipo = st.selectbox("Tipo de Concepto", TIPOS_COBRO)
                c_monto = st.number_input("Monto Pactado (S/)", value=0.0)
                c_venc = st.date_input("Fecha de Vencimiento", value=datetime.date.today())
                c_est = st.selectbox("Estado", STATUS_COBROS)

                if st.form_submit_button("REGISTRAR HITO") and c_hito:
                    n_cobro = pd.DataFrame([{
                        'ID': f"COB_{int(datetime.datetime.now().timestamp())}_{uuid.uuid4().hex[:6]}",
                        'Proyecto': proy_name,
                        'Hito': c_hito,
                        'Tipo': c_tipo,
                        'Monto_Pactado': c_monto,
                        'Fecha_Vencimiento': c_venc.strftime("%d/%m/%Y"),
                        'Monto_Cobrado': c_monto if c_est == "🟢 Cobrado" else 0.0,
                        'Fecha_Cobro': c_venc.strftime("%d/%m/%Y") if c_est == "🟢 Cobrado" else "",
                        'Estado': c_est,
                        'Notas': ""
                    }])
                    st.session_state.cobros = pd.concat([st.session_state.cobros, n_cobro[COLS_COBROS]], ignore_index=True)
                    clear_base_dfs()
                    st.rerun()

    # Métricas de cobros
    tot_pactado_cobro = pd.to_numeric(df_cobros_p['Monto_Pactado'], errors='coerce').sum() if not df_cobros_p.empty else 0.0
    tot_cobrado = pd.to_numeric(df_cobros_p['Monto_Cobrado'], errors='coerce').sum() if not df_cobros_p.empty else 0.0
    saldo_cobrar = tot_pactado_cobro - tot_cobrado

    m1, m2, m3 = st.columns(3)
    with m1:
        render_metric_card("Total Hitos Contractuales", format_currency(tot_pactado_cobro), "Facturación pactada")
    with m2:
        render_metric_card("Total Cobrado", format_currency(tot_cobrado), f"Efectivo percibido ({(tot_cobrado/tot_pactado_cobro*100 if tot_pactado_cobro>0 else 0):.0f}%)", border_color="#4A7C59", text_color="#4A7C59")
    with m3:
        render_metric_card("Saldo por Cobrar", format_currency(saldo_cobrar), "Pendiente de cobro", border_color="#C85A32", text_color="#C85A32")

    st.divider()

    # Editor de Cobros
    base_cob_key = f"base_df_cobros_{proy_name}"
    counter_key = f"c_{base_cob_key}"
    c_val = st.session_state.get(counter_key, 0)
    w_key = f"ed_cobros_{proy_name}_{c_val}"

    display_cob = df_cobros_p[['ID', 'Hito', 'Tipo', 'Monto_Pactado', 'Fecha_Vencimiento', 'Monto_Cobrado', 'Fecha_Cobro', 'Estado', 'Notas']].copy() if not df_cobros_p.empty else pd.DataFrame(columns=['ID', 'Hito', 'Tipo', 'Monto_Pactado', 'Fecha_Vencimiento', 'Monto_Cobrado', 'Fecha_Cobro', 'Estado', 'Notas'])
    display_cob['Fecha_Vencimiento'] = display_cob['Fecha_Vencimiento'].apply(lambda x: parse_date(x))
    display_cob['Fecha_Cobro'] = display_cob['Fecha_Cobro'].apply(lambda x: parse_date(x))
    display_cob['Monto_Pactado'] = pd.to_numeric(display_cob['Monto_Pactado'], errors='coerce').fillna(0.0)
    display_cob['Monto_Cobrado'] = pd.to_numeric(display_cob['Monto_Cobrado'], errors='coerce').fillna(0.0)

    if base_cob_key not in st.session_state:
        st.session_state[base_cob_key] = display_cob.copy()

    st.data_editor(
        st.session_state[base_cob_key],
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key=w_key,
        column_config={
            "ID": None,
            "Hito": st.column_config.TextColumn("Hito / Detalle de Cobro", width="large", required=True),
            "Tipo": st.column_config.SelectboxColumn("Tipo", options=TIPOS_COBRO),
            "Monto_Pactado": st.column_config.NumberColumn("Monto Pactado", format="S/ %.2f"),
            "Fecha_Vencimiento": st.column_config.DateColumn("Vencimiento", format="DD/MM/YYYY"),
            "Monto_Cobrado": st.column_config.NumberColumn("Monto Cobrado", format="S/ %.2f"),
            "Fecha_Cobro": st.column_config.DateColumn("Fecha Cobro", format="DD/MM/YYYY"),
            "Estado": st.column_config.SelectboxColumn("Estado", options=STATUS_COBROS),
            "Notas": st.column_config.TextColumn("Notas / N° Factura")
        },
        on_change=on_table_edit,
        args=(
            base_cob_key,
            w_key,
            'cobros',
            ['Proyecto'],
            [proy_name],
            ['Fecha_Vencimiento', 'Fecha_Cobro'],
            ['Hito', 'Tipo', 'Estado', 'Notas'],
            None,
            ['Monto_Pactado', 'Monto_Cobrado'],
            'ID'
        )
    )

    # Caja Chica de Obra
    st.divider()
    st.markdown("#### CAJA CHICA Y GASTOS OPERATIVOS DEL PROYECTO")
    df_gg_p = st.session_state.gg_log[st.session_state.gg_log['Proyecto'] == proy_name].copy()

    with st.form(f"form_gg_quick_{proy_name}", clear_on_submit=True):
        cg1, cg2, cg3 = st.columns([5, 2, 2])
        n_conc = cg1.text_input("Concepto de Gasto")
        n_monto_gg = cg2.number_input("Monto (S/)", value=0.0)
        if cg3.form_submit_button("REGISTRAR GASTO") and n_conc and n_monto_gg > 0:
            n_row = pd.DataFrame([{
                'Proyecto': proy_name,
                'Fecha': datetime.date.today().strftime("%d/%m/%Y"),
                'Responsable': proy_data.get('Encargado', ''),
                'Concepto': n_conc,
                'Monto': n_monto_gg
            }])
            st.session_state.gg_log = pd.concat([st.session_state.gg_log, n_row], ignore_index=True)
            clear_base_dfs()
            st.rerun()

    if not df_gg_p.empty:
        st.dataframe(df_gg_p[['Fecha', 'Concepto', 'Monto']], use_container_width=True, hide_index=True)


def _render_tab_actas(proy_name, proy_data):
    """Pestaña 7: Actas de Reunión, Asistentes, Acuerdos y Exportación PDF."""
    st.markdown("### 📝 REUNIONES Y ACTAS DE COORDINACIÓN")
    st.caption("Registro de minutas con clientes, especialistas y contratistas. Exportación formal a PDF.")

    proj_sessions = st.session_state.ice_sesiones[st.session_state.ice_sesiones['Proyecto'] == proy_name].copy()

    col_s1, col_s2 = st.columns([2.5, 4.5])

    with col_s1:
        with st.popover("➕ NUEVA ACTA DE REUNIÓN", use_container_width=True):
            tab_meet, tab_man = st.tabs(["📄 IMPORTAR NOTAS", "✍️ REGISTRO MANUAL"])

            with tab_meet:
                st.caption("Pega las notas de Google Meet / transcripción para estructurar asistentes y acuerdos automáticamente.")
                f_doc = st.file_uploader("Archivo (.txt, .docx, .pdf, .md)", type=['txt', 'docx', 'pdf', 'md'], key=f"f_meet_{proy_name}")
                t_doc = st.text_area("O pega el texto aquí:", height=120, key=f"t_meet_{proy_name}")

                if st.button("PROCESAR NOTAS Y CREAR ACTA", type="primary", use_container_width=True, key=f"btn_pmeet_{proy_name}"):
                    txt = extraer_texto_documento(f_doc) if f_doc else (t_doc or "")
                    if txt.strip():
                        data = parse_resumen_meet(txt, proy_name, len(proj_sessions))
                        new_id = f"SES_{int(datetime.datetime.now().timestamp())}_{uuid.uuid4().hex[:6]}"

                        # Crear sesión
                        n_ses = pd.DataFrame([{
                            'ID_Sesion': new_id,
                            'Proyecto': proy_name,
                            'Nombre_Sesion': data['nombre_sesion'],
                            'Tipo_Reunion': data.get('tipo_reunion', 'Con Cliente'),
                            'Etapa': data['etapa'],
                            'Fecha_Prog': data['fecha_prog'],
                            'Fecha_Real': data['fecha_real'],
                            'Hora': data['hora'],
                            'Organizador': data['organizador'],
                            'Lider': data['lider']
                        }])
                        st.session_state.ice_sesiones = pd.concat([st.session_state.ice_sesiones, n_ses], ignore_index=True)

                        # Crear asistentes
                        inv_rows = [{'ID_Sesion': new_id, 'Nombre': i['nombre'], 'Empresa': i['empresa'], 'Cargo': i['cargo'], 'Asistencia': i['asistencia']} for i in data.get('invitados', [])]
                        if inv_rows:
                            st.session_state.ice_invitados = pd.concat([st.session_state.ice_invitados, pd.DataFrame(inv_rows)], ignore_index=True)

                        # Crear acuerdos
                        acu_rows = [{'ID_Sesion': new_id, 'Descripcion': a['descripcion'], 'Responsable': a['responsable'], 'Acuerdo': a['acuerdo']} for a in data.get('acuerdos', [])]
                        if acu_rows:
                            st.session_state.ice_acuerdos = pd.concat([st.session_state.ice_acuerdos, pd.DataFrame(acu_rows)], ignore_index=True)

                        st.session_state[f"sel_sesion_{proy_name}"] = new_id
                        clear_base_dfs()
                        st.success("Acta creada exitosamente.")
                        st.rerun()

            with tab_man:
                with st.form(f"form_man_ses_{proy_name}", clear_on_submit=True):
                    num_acta = len(proj_sessions) + 1
                    n_nom_acta = st.text_input("Título de la Reunión", value=f"Acta de Coordinación N° 0{num_acta} - {proy_name}")
                    n_tipo_acta = st.selectbox("Tipo de Reunión", TIPOS_REUNION)
                    n_etp = st.text_input("Fase / Etapa", value="Diseño")
                    col_f1, col_f2 = st.columns(2)
                    n_fp = col_f1.date_input("Fecha", value=datetime.date.today())
                    n_hora = col_f2.text_input("Hora", value="10:00 a. m.")
                    n_org = st.text_input("Organizador", value=proy_data.get('Encargado', 'Estudio'))

                    if st.form_submit_button("CREAR ACTA") and n_nom_acta:
                        new_id = f"SES_{int(datetime.datetime.now().timestamp())}_{uuid.uuid4().hex[:6]}"
                        n_ses = pd.DataFrame([{
                            'ID_Sesion': new_id,
                            'Proyecto': proy_name,
                            'Nombre_Sesion': n_nom_acta,
                            'Tipo_Reunion': n_tipo_acta,
                            'Etapa': n_etp,
                            'Fecha_Prog': n_fp.strftime("%d/%m/%Y"),
                            'Fecha_Real': n_fp.strftime("%d/%m/%Y"),
                            'Hora': n_hora,
                            'Organizador': n_org,
                            'Lider': n_org
                        }])
                        st.session_state.ice_sesiones = pd.concat([st.session_state.ice_sesiones, n_ses], ignore_index=True)
                        st.session_state[f"sel_sesion_{proy_name}"] = new_id
                        clear_base_dfs()
                        st.rerun()

        if proj_sessions.empty:
            st.info("Sin actas registradas.")
            return

        session_opts = proj_sessions.set_index('ID_Sesion')['Nombre_Sesion'].to_dict()
        def_id = st.session_state.get(f"sel_sesion_{proy_name}")
        sel_idx = list(session_opts.keys()).index(def_id) if def_id in session_opts else 0

        sel_id = st.selectbox(
            "Seleccionar Acta:",
            options=list(session_opts.keys()),
            format_func=lambda x: session_opts[x],
            index=sel_idx,
            key=f"sb_ses_{proy_name}"
        )
        st.session_state[f"sel_sesion_{proy_name}"] = sel_id

    with col_s2:
        if sel_id:
            r_ses = proj_sessions[proj_sessions['ID_Sesion'] == sel_id].iloc[0]
            html_acta = (
                f"<div style='background-color: #FFFFFF; border: 1px solid #DFD9CE; border-left: 4px solid #C85A32; border-radius: 6px; padding: 14px;'>"
                f"<div style='color: #C85A32; font-weight: 700; font-size: 15px; margin-bottom: 6px;'>{r_ses['Nombre_Sesion']}</div>"
                f"<div style='display: grid; grid-template-columns: repeat(3, 1fr); font-size: 12px; color: #262320; gap: 8px;'>"
                f"<div><b style='color:#6E665E;'>Fecha:</b> {r_ses['Fecha_Real']}</div>"
                f"<div><b style='color:#6E665E;'>Hora:</b> {r_ses['Hora']}</div>"
                f"<div><b style='color:#6E665E;'>Tipo:</b> {r_ses.get('Tipo_Reunion', 'Coordinación')}</div>"
                f"<div><b style='color:#6E665E;'>Organizador:</b> {r_ses['Organizador']}</div>"
                f"<div><b style='color:#6E665E;'>Fase:</b> {r_ses['Etapa']}</div>"
                f"</div>"
                f"</div>"
            )
            st.markdown(html_acta, unsafe_allow_html=True)

    if sel_id:
        st.divider()

        # 1. Asistentes
        st.markdown("#### 👥 PARTICIPANTES Y ASISTENCIA")
        df_inv = st.session_state.ice_invitados[st.session_state.ice_invitados['ID_Sesion'] == sel_id].copy()

        base_inv_key = f"base_df_inv_{sel_id}"
        counter_key = f"c_{base_inv_key}"
        c_val = st.session_state.get(counter_key, 0)
        w_key = f"ed_inv_{sel_id}_{c_val}"

        display_inv = df_inv[['Nombre', 'Empresa', 'Cargo', 'Asistencia']].copy() if not df_inv.empty else pd.DataFrame(columns=['Nombre', 'Empresa', 'Cargo', 'Asistencia'])

        if base_inv_key not in st.session_state:
            st.session_state[base_inv_key] = display_inv.copy()

        upd_inv = st.data_editor(
            st.session_state[base_inv_key],
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            key=w_key,
            column_config={
                "Nombre": st.column_config.TextColumn("Nombre", required=True),
                "Empresa": st.column_config.TextColumn("Empresa / Especialidad"),
                "Cargo": st.column_config.TextColumn("Cargo / Rol"),
                "Asistencia": st.column_config.SelectboxColumn("Asistencia", options=["Asistió", "Faltó", "Tarde", "Licencia"])
            },
            on_change=on_table_edit,
            args=(
                base_inv_key,
                w_key,
                'ice_invitados',
                ['ID_Sesion'],
                [sel_id],
                None,
                ['Nombre', 'Empresa', 'Cargo', 'Asistencia'],
                None,
                None,
                None
            )
        )

        st.divider()

        # 2. Acuerdos y Compromisos
        st.markdown("#### 📋 ACUERDOS Y PRÓXIMOS PASOS")
        df_acu = st.session_state.ice_acuerdos[st.session_state.ice_acuerdos['ID_Sesion'] == sel_id].copy()

        base_acu_key = f"base_df_acu_{sel_id}"
        counter_key = f"c_{base_acu_key}"
        c_val = st.session_state.get(counter_key, 0)
        w_key = f"ed_acu_{sel_id}_{c_val}"

        display_acu = df_acu[['Descripcion', 'Responsable', 'Acuerdo']].copy() if not df_acu.empty else pd.DataFrame(columns=['Descripcion', 'Responsable', 'Acuerdo'])

        if base_acu_key not in st.session_state:
            st.session_state[base_acu_key] = display_acu.copy()

        upd_acu = st.data_editor(
            st.session_state[base_acu_key],
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            key=w_key,
            column_config={
                "Descripcion": st.column_config.TextColumn("Tema / Entregable", width="large", required=True),
                "Responsable": st.column_config.TextColumn("Responsable"),
                "Acuerdo": st.column_config.TextColumn("Acuerdo / Acción Acordada", width="large", required=True)
            },
            on_change=on_table_edit,
            args=(
                base_acu_key,
                w_key,
                'ice_acuerdos',
                ['ID_Sesion'],
                [sel_id],
                None,
                ['Descripcion', 'Responsable', 'Acuerdo'],
                None,
                None,
                None
            )
        )

        # Exportación y acciones
        st.divider()
        cb1, cb2, _ = st.columns([2.5, 2.5, 5])
        with cb1:
            try:
                pdf_bytes = generar_pdf_minuta(r_ses, upd_inv, upd_acu)
                st.download_button(
                    label="📥 EXPORTAR ACTA A PDF",
                    data=pdf_bytes,
                    file_name=f"{r_ses['Nombre_Sesion'].replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Error al generar PDF: {str(e)}")

        with cb2:
            if st.button("🗑️ ELIMINAR ACTA", key=f"del_acta_{sel_id}", type="secondary", use_container_width=True):
                st.session_state.ice_sesiones = st.session_state.ice_sesiones[st.session_state.ice_sesiones['ID_Sesion'] != sel_id]
                st.session_state.ice_invitados = st.session_state.ice_invitados[st.session_state.ice_invitados['ID_Sesion'] != sel_id]
                st.session_state.ice_acuerdos = st.session_state.ice_acuerdos[st.session_state.ice_acuerdos['ID_Sesion'] != sel_id]
                clear_base_dfs()
                st.rerun()


def _render_tab_punch(proy_name, proy_data):
    """Pestaña 8: Observaciones y Control de Calidad para Entrega."""
    st.markdown("### 🔍 08. OBSERVACIONES Y CONTROL DE CALIDAD")
    st.caption("Control de observaciones técnicas, detalles finales y levantamiento de pendientes antes de la entrega al cliente.")

    if 'pendientes_entrega' not in st.session_state:
        st.session_state.pendientes_entrega = pd.DataFrame(columns=COLS_PUNCH)

    df_punch = st.session_state.pendientes_entrega[st.session_state.pendientes_entrega['Proyecto'] == proy_name].copy()

    col_btn1, _ = st.columns([3, 7])
    with col_btn1:
        with st.popover("➕ AGREGAR OBSERVACIÓN", use_container_width=True):
            with st.form(f"f_new_punch_{proy_name}", clear_on_submit=True):
                p_amb = st.selectbox("Ambiente", AMBIENTES_DEFAULT)
                p_elem = st.text_input("Elemento")
                p_desc = st.text_area("Descripción de la Observación", placeholder="")
                col_r1, col_r2 = st.columns(2)
                p_resp = col_r1.text_input("Responsable (Contratista / Proveedor)")
                p_prio = col_r2.selectbox("Prioridad", PRIORIDADES_PUNCH, index=1)
                p_est = st.selectbox("Estado", STATUS_PUNCH)

                if st.form_submit_button("REGISTRAR OBSERVACIÓN") and p_desc:
                    n_row = pd.DataFrame([{
                        'ID': f"PUN_{int(datetime.datetime.now().timestamp())}_{uuid.uuid4().hex[:6]}",
                        'Proyecto': proy_name,
                        'Ambiente': p_amb,
                        'Elemento': p_elem,
                        'Descripcion': p_desc,
                        'Responsable': p_resp,
                        'Prioridad': p_prio,
                        'Estado': p_est,
                        'Fecha_Deteccion': datetime.date.today().strftime("%d/%m/%Y"),
                        'Fecha_Solucion': "",
                        'Notas': ""
                    }])
                    st.session_state.pendientes_entrega = pd.concat([st.session_state.pendientes_entrega, n_row[COLS_PUNCH]], ignore_index=True)
                    clear_base_dfs()
                    st.rerun()

    # Métricas del Punch List
    tot_punch = len(df_punch)
    tot_pend = len(df_punch[df_punch['Estado'] == '🔴 Pendiente'])
    tot_corr = len(df_punch[df_punch['Estado'] == '🟡 En Corrección'])
    tot_subs = len(df_punch[df_punch['Estado'] == '🟢 Subsanado'])

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        render_metric_card("Total Observaciones", str(tot_punch), "Detalles detectados")
    with m2:
        render_metric_card("Pendientes", str(tot_pend), "Por corregir", border_color="#C93B2B", text_color="#C93B2B")
    with m3:
        render_metric_card("En Corrección", str(tot_corr), "En atención", border_color="#D98A2B", text_color="#D98A2B")
    with m4:
        render_metric_card("Subsanados", str(tot_subs), f"{(tot_subs/tot_punch*100 if tot_punch>0 else 100):.0f}% resuelto", border_color="#4A7C59", text_color="#4A7C59")

    st.divider()

    # Editor de Punch List
    base_pun_key = f"base_df_punch_{proy_name}"
    counter_key = f"c_{base_pun_key}"
    c_val = st.session_state.get(counter_key, 0)
    w_key = f"ed_punch_{proy_name}_{c_val}"

    display_pun = df_punch[['ID', 'Ambiente', 'Elemento', 'Descripcion', 'Responsable', 'Prioridad', 'Estado', 'Fecha_Deteccion', 'Fecha_Solucion', 'Notas']].copy() if not df_punch.empty else pd.DataFrame(columns=['ID', 'Ambiente', 'Elemento', 'Descripcion', 'Responsable', 'Prioridad', 'Estado', 'Fecha_Deteccion', 'Fecha_Solucion', 'Notas'])
    display_pun['Fecha_Deteccion'] = display_pun['Fecha_Deteccion'].apply(lambda x: parse_date(x))
    display_pun['Fecha_Solucion'] = display_pun['Fecha_Solucion'].apply(lambda x: parse_date(x))

    if base_pun_key not in st.session_state:
        st.session_state[base_pun_key] = display_pun.copy()

    st.data_editor(
        st.session_state[base_pun_key],
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key=w_key,
        column_config={
            "ID": None,
            "Ambiente": st.column_config.SelectboxColumn("Ambiente", options=AMBIENTES_DEFAULT),
            "Elemento": st.column_config.TextColumn("Elemento"),
            "Descripcion": st.column_config.TextColumn("Descripción del Detalle", width="large", required=True),
            "Responsable": st.column_config.TextColumn("Responsable"),
            "Prioridad": st.column_config.SelectboxColumn("Prioridad", options=PRIORIDADES_PUNCH),
            "Estado": st.column_config.SelectboxColumn("Estado", options=STATUS_PUNCH),
            "Fecha_Deteccion": st.column_config.DateColumn("Detección", format="DD/MM/YYYY"),
            "Fecha_Solucion": st.column_config.DateColumn("Subsanación", format="DD/MM/YYYY"),
            "Notas": st.column_config.TextColumn("Notas")
        },
        on_change=on_table_edit,
        args=(
            base_pun_key,
            w_key,
            'pendientes_entrega',
            ['Proyecto'],
            [proy_name],
            ['Fecha_Deteccion', 'Fecha_Solucion'],
            ['Ambiente', 'Elemento', 'Descripcion', 'Responsable', 'Prioridad', 'Estado', 'Notas'],
            None,
            None,
            'ID'
        )
    )

