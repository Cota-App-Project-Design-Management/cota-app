"""
Vista detallada de Proyecto (Fullscreen):
Resumen, Fases de Diseño, Presupuesto All-in-One, Entregables y Planos,
Ejecución de Obra, Cobros y Finanzas, Reuniones y Actas, y Punch List de Entrega.
"""

import datetime
import uuid
import altair as alt
import pandas as pd
import streamlit as st

from cota.config import (
    AMBIENTES_DEFAULT,
    ESPECIALIDADES_DEFAULT,
    PRIORIDADES_PUNCH,
    STATUS_COBROS,
    STATUS_FASES,
    STATUS_PUNCH,
    STATUS_TASKS,
    TIPOS_COBRO,
    TIPOS_REUNION,
    UNIDADES_MEDIDA,
)
from cota.db import (
    COLS_COBROS,
    COLS_ENTREGABLES,
    COLS_FASES,
    COLS_PAGOS,
    COLS_PUNCH,
    COLS_TASKS,
    _normalizar_supervisado,
    agregar_fase_banco,
    clear_base_dfs,
    obtener_banco_fases,
    on_table_edit,
    sanitizar_fases_estudio,
    sembrar_fases_default,
    sincronizar_fases_proyecto,
)
from cota.cotizacion import (
    ajustar_cantidad_partidas_proyecto,
    ajustar_cantidad_tareas_partida,
    aplicar_cotizacion_a_proyecto,
    aplicar_edicion_tabla_presupuesto_partida,
    asegurar_estructura_presupuesto_proyecto,
    calcular_resumen_cuadro_pagos_semanales,
    exportar_cuadro_pagos_semanales_excel,
    exportar_proyecto_a_formato_venti,
    extraer_descripcion_tarea,
    generar_plantilla_cotizacion_venti,
    guardar_cuadro_pagos_semanales_proyecto,
    guardar_parametros_presupuesto_proyecto,
    limpiar_nombre_partida,
    obtener_columnas_pago_semanal,
    obtener_cuadro_pagos_semanales_proyecto,
    obtener_parametros_presupuesto_proyecto,
    parsear_cotizacion_venti,
    parsear_cuadro_pagos_semanales,
    recalcular_totales_presupuesto_proyecto,
    renombrar_partida_presupuesto,
)
from cota.pdf import generar_pdf_minuta
from cota.ui.components import render_metric_card
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
        st.session_state.fases = sembrar_fases_default(proy_name, proy_data.get('Inicio'))
    else:
        fases_p = st.session_state.fases[st.session_state.fases['Proyecto'] == proy_name]
        if fases_p.empty:
            nuevas_f = sembrar_fases_default(proy_name, proy_data.get('Inicio'))
            st.session_state.fases = pd.concat([st.session_state.fases, nuevas_f], ignore_index=True)

    # Tabs especializadas del proyecto
    t_resumen, t_diseno, t_presupuesto, t_obra, t_finanzas, t_actas, t_observaciones = st.tabs([
        "01. RESUMEN",
        "02. DISEÑO",
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

    # Pagos a contratistas
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

    # Avance en fases
    fases_p = st.session_state.fases[st.session_state.fases['Proyecto'] == proy_name].sort_values(by='Orden')
    n_fases = len(fases_p)
    n_fases_ok = len(fases_p[fases_p['Aprobado_Cliente'].apply(to_bool) | (fases_p['Estado'].astype(str).str.contains('Aprobada', case=False))])
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
        render_metric_card("Utilidades / Superv.", format_currency(util_proy), f"Honorarios: {format_currency(hon_diseno)}", border_color="#4A7C59", text_color="#4A7C59")
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
        drive_link_val = safe_str(proy_data.get('Link_Drive', '')).strip()
        info_items = [
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

        st.markdown("#### BRIEF Y OBJETIVOS DE DISEÑO")
        notas_p = str(proy_data.get('Notas', '')).strip()
        if notas_p and notas_p.lower() not in ['nan', 'none']:
            st.markdown(
                f"<div style='background:#FAF8F5; border:1px solid #DFD9CE; border-left:4px solid #C85A32; border-radius:8px; padding:12px 16px; color:#262320; font-size:13.5px; line-height:1.6;'>{notas_p}</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown("<p style='color:#8C8277; font-style:italic;'>Sin notas registradas en el brief de este proyecto.</p>", unsafe_allow_html=True)

    with col_d2:
        ch_f1, ch_f2 = st.columns([6.2, 3.8])
        with ch_f1:
            st.markdown(f"#### ESTADO DE LAS FASES ({n_fases} ACTIVAS)")
        with ch_f2:
            with st.popover("🗂️ BANCO DE FASES", use_container_width=True):
                st.markdown("##### Activar / Desactivar Fases")
                st.caption("Selecciona del banco las fases que aplican a las características de este proyecto.")
                with st.form(f"form_res_banco_fases_{proy_name}"):
                    opciones_res_f = list(dict.fromkeys(nombres_banco_all + fases_activas_actuales))
                    sel_res_f = st.multiselect(
                        "Fases activas en este proyecto:",
                        options=opciones_res_f,
                        default=fases_activas_actuales,
                    )
                    nueva_f_res = st.text_input("➕ Nueva fase al Banco (opcional):", placeholder="ej. 09. Licencias Municipales")
                    if st.form_submit_button("APLICAR FASES", type="primary", use_container_width=True):
                        fases_aplicar = list(sel_res_f)
                        if nueva_f_res.strip():
                            nf = agregar_fase_banco(nueva_f_res.strip())
                            if nf["Fase"] not in fases_aplicar:
                                fases_aplicar.append(nf["Fase"])
                        sincronizar_fases_proyecto(proy_name, fases_aplicar, proy_data.get('Inicio'))
                        st.success("Fases del proyecto actualizadas.")
                        st.rerun()

        if not fases_p.empty:
            fases_items = []
            for _, fr in fases_p.iterrows():
                est_f = str(fr.get('Estado', '⚪ No iniciada'))
                aprob = to_bool(fr.get('Aprobado_Cliente', False)) or ('Aprobada' in est_f)
                av_pct = int(safe_float(fr.get('Avance_Pct', 100 if aprob else 0)))
                col_bar = "#4A7C59" if aprob else ("#C85A32" if av_pct > 0 else "#DFD9CE")
                badge_txt = "✓ Aprobada" if aprob else est_f
                fases_items.append(
                    f"<div style='padding:7px 12px; border-bottom:1px solid #EFECE6;'>"
                    f"<div style='display:flex; justify-content:space-between; font-size:12.5px; margin-bottom:4px;'>"
                    f"<span style='color:#262320; font-weight:600;'>{fr.get('Fase', '')}</span>"
                    f"<span style='color:#6E665E; font-family:monospace; font-size:11.5px;'>{badge_txt} ({av_pct}%)</span>"
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
            st.info("No hay fases activas para este proyecto. Usa el botón '🗂️ BANCO DE FASES' para activar las que correspondan.")


def _render_tab_fases(proy_name, proy_data):
    """Pestaña 2: Diseño, Banco de Fases configurable, cronograma y presentación en Drive."""
    st.markdown("### 🎨 02. DISEÑO Y PRESENTACIÓN DEL PROYECTO")
    st.caption("Fases del ciclo de diseño del proyecto, cronograma Gantt y conexión directa con la presentación en Google Drive / Slides.")

    # Conectar con la presentación de diseño en Google Drive / Slides / Figma
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

    fases_df = st.session_state.fases[st.session_state.fases['Proyecto'] == proy_name].copy()
    fases_df = fases_df.sort_values(by='Orden')
    fases_activas_actuales = fases_df['Fase'].tolist() if not fases_df.empty else []

    banco_fases = obtener_banco_fases()
    nombres_banco = [f["Fase"] for f in banco_fases]
    todas_opciones_fases = list(dict.fromkeys(nombres_banco + fases_activas_actuales))

    # Banco de Fases del Estudio: activar/desactivar por proyecto + agregar al banco
    with st.expander("🗂️ BANCO DE FASES — Activar / Desactivar Fases para este Proyecto", expanded=False):
        cb_left, cb_right = st.columns([6.5, 3.5])
        with cb_left:
            with st.form(f"form_tab_fases_banco_{proy_name}"):
                st.markdown("##### Selecciona las Fases Activas del Proyecto")
                st.caption("Marca únicamente las fases que aplican a este proyecto. Los datos de avance de las fases que ya estaban activas se conservarán.")
                checks_seleccionados = []
                cols_chk = st.columns(2)
                for idx_f, nom_f in enumerate(todas_opciones_fases):
                    col_c = cols_chk[idx_f % 2]
                    activo_actual = nom_f in fases_activas_actuales
                    if col_c.checkbox(nom_f, value=activo_actual, key=f"chk_bf_{proy_name}_{idx_f}"):
                        checks_seleccionados.append(nom_f)

                if st.form_submit_button("💾 ACTUALIZAR FASES ACTIVAS DEL PROYECTO", type="primary", use_container_width=True):
                    sincronizar_fases_proyecto(proy_name, checks_seleccionados, proy_data.get('Inicio'))
                    st.success(f"Fases actualizadas ({len(checks_seleccionados)} fases activas en '{proy_name}').")
                    st.rerun()

        with cb_right:
            with st.form(f"form_nueva_fase_banco_{proy_name}", clear_on_submit=True):
                st.markdown("##### ➕ Agregar Fase al Banco")
                st.caption("Crea una nueva fase en el catálogo del estudio.")
                nf_nombre = st.text_input("Nombre de la Fase", placeholder="ej. 09. Licencias Municipales")
                nf_etapa = st.selectbox("Etapa", ["Conceptual", "Diseño", "Documentación", "Adquisiciones", "Construcción", "Cierre"])
                nf_dias = st.number_input("Duración estimada (días)", min_value=1, max_value=365, value=10)
                nf_activar = st.checkbox("Activar inmediatamente en este proyecto", value=True)
                if st.form_submit_button("AGREGAR AL BANCO", use_container_width=True) and nf_nombre.strip():
                    nueva_f = agregar_fase_banco(nf_nombre.strip(), etapa=nf_etapa, dias=int(nf_dias))
                    if nf_activar:
                        nuevas_act = list(dict.fromkeys(fases_activas_actuales + [nueva_f["Fase"]]))
                        sincronizar_fases_proyecto(proy_name, nuevas_act, proy_data.get('Inicio'))
                    st.success(f"Fase '{nueva_f['Fase']}' añadida al Banco de Fases.")
                    st.rerun()

    # Gantt interactivo de Fases
    df_chart = fases_df.copy()
    df_chart['Inicio_DT'] = df_chart['Inicio'].apply(lambda x: pd.to_datetime(parse_date(x)))
    df_chart['Fin_DT'] = df_chart['Fin'].apply(lambda x: pd.to_datetime(parse_date(x)))
    df_chart = df_chart.dropna(subset=['Inicio_DT', 'Fin_DT'])

    if not df_chart.empty:
        mask_same = df_chart['Inicio_DT'].dt.date == df_chart['Fin_DT'].dt.date
        df_chart.loc[mask_same, 'Fin_DT'] = df_chart['Fin_DT'] + datetime.timedelta(days=1)

        color_scale = alt.Scale(
            domain=STATUS_FASES,
            range=['#9A9187', '#D98A2B', '#C85A32', '#4A7C59']
        )

        chart_fases = alt.Chart(df_chart).mark_bar(cornerRadius=4, height=18).encode(
            x=alt.X('Inicio_DT:T', title='Cronograma de Diseño', axis=alt.Axis(gridColor='#DFD9CE', domainColor='#DFD9CE', labelColor='#6E665E', titleColor='#262320', format='%d %b')),
            x2='Fin_DT:T',
            y=alt.Y('Fase:N', sort=alt.SortField(field='Orden', order='ascending'), title='', axis=alt.Axis(labelColor='#262320', labelFontWeight='bold', labelLimit=240)),
            color=alt.Color('Estado:N', scale=color_scale, legend=alt.Legend(title="Estado de Fase", orient="top", labelColor='#262320', titleColor='#6E665E')),
            tooltip=['Fase', 'Etapa', 'Estado', 'Responsable', alt.Tooltip('Avance_Pct:Q', title='Avance %')]
        ).properties(height=290).configure_view(strokeOpacity=0).configure_axis(grid=True)

        st.altair_chart(chart_fases, use_container_width=True)

    st.divider()
    st.markdown("#### EDITOR DE FASES ACTIVAS Y APROBACIÓN DEL CLIENTE")

    base_fases_key = f"base_df_fases_{proy_name}"
    counter_key = f"c_{base_fases_key}"
    c_val = st.session_state.get(counter_key, 0)
    w_key = f"ed_fases_{proy_name}_{c_val}"

    display_fases = fases_df[['ID', 'Orden', 'Fase', 'Etapa', 'Inicio', 'Fin', 'Estado', 'Avance_Pct', 'Responsable', 'Aprobado_Cliente', 'Notas']].copy()
    display_fases['Inicio'] = display_fases['Inicio'].apply(lambda x: parse_date(x))
    display_fases['Fin'] = display_fases['Fin'].apply(lambda x: parse_date(x))
    display_fases['Avance_Pct'] = pd.to_numeric(display_fases['Avance_Pct'], errors='coerce').fillna(0).astype(int)
    display_fases['Aprobado_Cliente'] = display_fases['Aprobado_Cliente'].apply(to_bool)

    if base_fases_key not in st.session_state:
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
            "Fase": st.column_config.TextColumn("Fase de Diseño", width="large", required=True),
            "Etapa": st.column_config.SelectboxColumn("Etapa", options=["Conceptual", "Diseño", "Documentación", "Adquisiciones", "Construcción", "Cierre"]),
            "Inicio": st.column_config.DateColumn("Inicio", format="DD/MM/YYYY"),
            "Fin": st.column_config.DateColumn("Fin", format="DD/MM/YYYY"),
            "Estado": st.column_config.SelectboxColumn("Estado", options=STATUS_FASES),
            "Avance_Pct": st.column_config.ProgressColumn("Avance %", min_value=0, max_value=100, format="%d%%"),
            "Aprobado_Cliente": st.column_config.CheckboxColumn("Aprobado Cliente"),
            "Responsable": st.column_config.TextColumn("Responsable"),
            "Notas": st.column_config.TextColumn("Notas / Entregable Clave")
        },
        on_change=on_table_edit,
        args=(
            base_fases_key,
            w_key,
            'fases',
            ['Proyecto'],
            [proy_name],
            ['Inicio', 'Fin'],
            ['Fase', 'Etapa', 'Estado', 'Responsable', 'Notas'],
            ['Aprobado_Cliente'],
            ['Orden', 'Avance_Pct'],
            'ID'
        )
    )


def _render_tab_presupuesto(proy_name, proy_data):
    """
    Pestaña 3: Constructor y Editor de Presupuesto All-in-One dentro de COTA.
    Permite definir dinámicamente la cantidad de Partidas (1, 2, 3, 4...), sus nombres,
    y la cantidad de Tareas por cada Partida (1.01, 1.02, 1.03...), editándolas constantemente.
    Se sincroniza automáticamente con 05. EJECUCIÓN & PARTIDAS y permite exportar a Excel (.xlsx).
    """
    asegurar_estructura_presupuesto_proyecto(proy_name, n_partidas_default=3, n_tareas_default=3)
    totales = recalcular_totales_presupuesto_proyecto(proy_name)
    params = obtener_parametros_presupuesto_proyecto(proy_name)

    parts_proy = st.session_state.partidas[st.session_state.partidas["Proyecto"] == proy_name].reset_index(drop=True)
    n_partidas_actual = max(1, len(parts_proy))

    col_tit_p, col_exp_p = st.columns([6.8, 3.2])
    with col_tit_p:
        st.markdown("### 📐 PRESUPUESTO Y COTIZACIÓN DEL PROYECTO")
        st.caption(
            "Define la cantidad de partidas y tareas, edita nombres, metrados y precios unitarios en tiempo real. "
            "Todas las partidas y tareas se sincronizan automáticamente con **05. EJECUCIÓN & PARTIDAS**."
        )
    with col_exp_p:
        st.markdown("<div style='padding-top: 8px;'></div>", unsafe_allow_html=True)
        xlsx_export_bytes = exportar_proyecto_a_formato_venti(proy_name)
        st.download_button(
            "📥 EXPORTAR PRESUPUESTO A EXCEL (.XLSX)",
            data=xlsx_export_bytes,
            file_name=f"Presupuesto_{proy_name.replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
            key=f"btn_exp_excel_top_{proy_name}",
        )

    # Panel de Configuración Global del Presupuesto
    with st.container(border=True):
        st.markdown("##### ⚙️ Configuración de Estructura y Parámetros Financieros")
        c_cfg1, c_cfg2, c_cfg3, c_cfg4, c_cfg5 = st.columns([1.8, 1.8, 2.0, 2.2, 2.2])

        key_n_part = f"cfg_n_partidas_{proy_name}"
        key_tc = f"cfg_tc_ppto_{proy_name}"
        key_gg = f"cfg_gg_pct_{proy_name}"
        key_util = f"cfg_util_pct_{proy_name}"
        key_igv = f"cfg_igv_chk_{proy_name}"

        def _on_change_cant_partidas():
            nueva_cant = st.session_state.get(key_n_part, n_partidas_actual)
            ajustar_cantidad_partidas_proyecto(proy_name, int(nueva_cant), n_tareas_default=3)

        def _on_change_params_ppto():
            guardar_parametros_presupuesto_proyecto(
                proy_name=proy_name,
                tc=safe_float(st.session_state.get(key_tc, params["tc"]), 3.42),
                gg_pct=safe_float(st.session_state.get(key_gg, params["gg_pct"]), 2.0),
                utilidades_pct=safe_float(st.session_state.get(key_util, params["utilidades_pct"]), 15.0),
                incluir_igv=bool(st.session_state.get(key_igv, params["incluir_igv"])),
            )

        with c_cfg1:
            st.number_input(
                "Cantidad de Partidas",
                min_value=1,
                max_value=40,
                value=n_partidas_actual,
                step=1,
                key=key_n_part,
                on_change=_on_change_cant_partidas,
                help="Indica cuántas partidas principales (1, 2, 3, 4...) tendrá el presupuesto.",
            )
        with c_cfg2:
            st.number_input(
                "Tipo de Cambio (TC)",
                min_value=1.0,
                max_value=10.0,
                value=float(params["tc"]),
                step=0.01,
                format="%.2f",
                key=key_tc,
                on_change=_on_change_params_ppto,
            )
        with c_cfg3:
            st.number_input(
                "% Gastos Generales",
                min_value=0.0,
                max_value=100.0,
                value=float(params["gg_pct"]),
                step=0.5,
                format="%.1f",
                key=key_gg,
                on_change=_on_change_params_ppto,
            )
        with c_cfg4:
            st.number_input(
                "% Gestión y Supervisión",
                min_value=0.0,
                max_value=100.0,
                value=float(params["utilidades_pct"]),
                step=0.5,
                format="%.1f",
                key=key_util,
                on_change=_on_change_params_ppto,
            )
        with c_cfg5:
            st.markdown("<div style='padding-top: 26px;'></div>", unsafe_allow_html=True)
            st.checkbox(
                "Aplicar IGV (18%)",
                value=bool(params["incluir_igv"]),
                key=key_igv,
                on_change=_on_change_params_ppto,
                help="Si marcas la casilla se aplica 18% de IGV; si no, queda en 0%.",
            )

    # Recargar métricas actualizadas
    totales = recalcular_totales_presupuesto_proyecto(proy_name)
    parts_proy = st.session_state.partidas[st.session_state.partidas["Proyecto"] == proy_name].reset_index(drop=True)
    total_tareas_proy = len(st.session_state.tasks[st.session_state.tasks["Proyecto"] == proy_name])

    # 5 Tarjetas de Resumen del Presupuesto en Vivo
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        render_metric_card(
            "Sub Total (Casco)",
            format_currency(totales["subtotal_casco"]),
            f"{len(parts_proy)} partidas · {total_tareas_proy} tareas",
        )
    with k2:
        render_metric_card(
            f"Gastos Generales ({totales['gg_pct']:g}%)",
            format_currency(totales["gg_monto"]),
            "Sincronizado con Caja Chica / GG",
            border_color="#C85A32",
            text_color="#C85A32",
        )
    with k3:
        render_metric_card(
            f"Gestión / Superv. ({totales['utilidades_pct']:g}%)",
            format_currency(totales["utilidades_monto"]),
            "Sincronizado con Utilidades",
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

    for idx_zero, part_row in parts_proy.iterrows():
        idx_p = idx_zero + 1
        p_nom_completo = safe_str(part_row["Nombre_Partida"])
        p_nom_limpio = limpiar_nombre_partida(p_nom_completo, idx_p)

        mask_t_p = (st.session_state.tasks["Proyecto"] == proy_name) & (st.session_state.tasks["Partida"] == p_nom_completo)
        df_t_p = st.session_state.tasks[mask_t_p].copy().reset_index(drop=True)
        n_tareas_p = max(1, len(df_t_p))

        sub_partida = totales["subtotales_por_partida"].get(p_nom_completo, 0.0)
        mix_partida = (sub_partida / subtotal_casco_val * 100.0) if subtotal_casco_val > 0 else 0.0

        resumen_rows.append({
            "Ítem": str(idx_p),
            "Descripción": p_nom_limpio,
            "Moneda": "Soles",
            "Porcentaje / Factor": "",
            "Monto (S/.)": sub_partida,
            "Mix (%)": f"{mix_partida:.1f}%",
        })

        with st.container(border=True):
            # Cabecera de la Partida: Nombre editable + N° de Tareas editable + Sub Total y Mix
            cp_nom, cp_cnt, cp_sub, cp_mix = st.columns([4.4, 2.0, 2.1, 1.5])

            key_pnom = f"ppto_pnom_{proy_name}_{idx_p}"
            key_ntasks = f"ppto_ntasks_{proy_name}_{idx_p}"

            def _make_on_rename(p_idx_1b, curr_full, k_nom):
                def _cb():
                    nuevo_val = st.session_state.get(k_nom, "")
                    renombrar_partida_presupuesto(proy_name, p_idx_1b, curr_full, nuevo_val)
                return _cb

            def _make_on_cant_tasks(p_idx_1b, curr_full, k_cnt):
                def _cb():
                    nueva_c = st.session_state.get(k_cnt, 1)
                    ajustar_cantidad_tareas_partida(proy_name, p_idx_1b, curr_full, int(nueva_c))
                return _cb

            with cp_nom:
                st.text_input(
                    f"Partida {idx_p} — Nombre de la Partida",
                    value=p_nom_limpio,
                    key=key_pnom,
                    on_change=_make_on_rename(idx_p, p_nom_completo, key_pnom),
                    placeholder=f"ej. Obras Civiles, Carpintería, Inst. Eléctricas...",
                )
            with cp_cnt:
                st.number_input(
                    f"N° de Tareas ({idx_p}.01, {idx_p}.02...)",
                    min_value=1,
                    max_value=100,
                    value=n_tareas_p,
                    step=1,
                    key=key_ntasks,
                    on_change=_make_on_cant_tasks(idx_p, p_nom_completo, key_ntasks),
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

            # Construir DataFrame editable para las tareas de esta partida
            rows_ed = []
            for pos_t, (_, t_r) in enumerate(df_t_p.iterrows(), start=1):
                cod_item = f"{idx_p}.{pos_t:02d}"
                desc_t = extraer_descripcion_tarea(t_r.get("Tarea", ""), cod_item)
                mon_t = safe_str(t_r.get("Moneda", "Soles")) or "Soles"
                if mon_t not in ["Soles", "Dólares"]:
                    mon_t = "Soles"
                und_t = safe_str(t_r.get("Unidad", "glb")) or "glb"
                met_t = safe_float(t_r.get("Metrado", 1.0), 1.0)
                if met_t <= 0:
                    met_t = 1.0
                vu_t = safe_float(t_r.get("Valor_Unitario", 0.0), 0.0)
                vp_t = safe_float(t_r.get("Presupuesto", 0.0), 0.0)

                rows_ed.append({
                    "Item": cod_item,
                    "Descripcion": desc_t,
                    "Moneda": mon_t,
                    "Unidad": und_t,
                    "Metrado": met_t,
                    "Valor_Unitario": vu_t,
                    "Valor_Parcial": vp_t,
                })

            df_ed_p = pd.DataFrame(rows_ed)

            base_ppto_key = f"base_df_ppto_{proy_name}_{idx_p}_{n_tareas_p}"
            c_ppto_key = f"c_{base_ppto_key}"
            c_ppto_val = st.session_state.get(c_ppto_key, 0)
            w_ppto_key = f"ed_ppto_{proy_name}_{idx_p}_{n_tareas_p}_{c_ppto_val}"

            if base_ppto_key not in st.session_state:
                st.session_state[base_ppto_key] = df_ed_p.copy()

            st.data_editor(
                st.session_state[base_ppto_key],
                use_container_width=True,
                hide_index=True,
                num_rows="fixed",
                disabled=["Item", "Valor_Parcial"],
                key=w_ppto_key,
                column_config={
                    "Item": st.column_config.TextColumn("Ítem", width="small"),
                    "Descripcion": st.column_config.TextColumn("Descripción de la Tarea / Sub-partida", width="large"),
                    "Moneda": st.column_config.SelectboxColumn("Moneda", options=["Soles", "Dólares"], width="small", required=True),
                    "Unidad": st.column_config.SelectboxColumn("Unidad", options=UNIDADES_MEDIDA, width="small", required=True),
                    "Metrado": st.column_config.NumberColumn("Metrado", min_value=0.01, step=1.0, format="%.2f", width="small", required=True),
                    "Valor_Unitario": st.column_config.NumberColumn("Valor Unitario", min_value=0.0, step=10.0, format="%.2f", width="medium", required=True),
                    "Valor_Parcial": st.column_config.NumberColumn("Valor Parcial (S/.)", format="S/ %.2f", width="medium"),
                },
                on_change=aplicar_edicion_tabla_presupuesto_partida,
                args=(
                    base_ppto_key,
                    w_ppto_key,
                    proy_name,
                    idx_p,
                    p_nom_completo,
                ),
            )

    # Cuadro Resumen de Cierre del Presupuesto + Exportación a Excel
    st.divider()
    st.markdown("#### 📊 CUADRO DE CIERRE DEL PRESUPUESTO")

    resumen_rows.extend([
        {
            "Ítem": "",
            "Descripción": "SUB TOTAL (Casco)",
            "Moneda": "Soles",
            "Porcentaje / Factor": "",
            "Monto (S/.)": totales["subtotal_casco"],
            "Mix (%)": "100.0%" if totales["subtotal_casco"] > 0 else "0.0%",
        },
        {
            "Ítem": "",
            "Descripción": "Gastos generales",
            "Moneda": "Soles",
            "Porcentaje / Factor": f"{totales['gg_pct']:g}%",
            "Monto (S/.)": totales["gg_monto"],
            "Mix (%)": "",
        },
        {
            "Ítem": "",
            "Descripción": "Gestión y supervisión de obras",
            "Moneda": "Soles",
            "Porcentaje / Factor": f"{totales['utilidades_pct']:g}%",
            "Monto (S/.)": totales["utilidades_monto"],
            "Mix (%)": "",
        },
        {
            "Ítem": "",
            "Descripción": "IGV",
            "Moneda": "Soles",
            "Porcentaje / Factor": "18%" if totales["incluir_igv"] else "0%",
            "Monto (S/.)": totales["igv_monto"],
            "Mix (%)": "",
        },
        {
            "Ítem": "",
            "Descripción": "TOTAL (Soles)",
            "Moneda": "Soles",
            "Porcentaje / Factor": "",
            "Monto (S/.)": totales["presupuesto_total"],
            "Mix (%)": f"{(totales['presupuesto_total'] / totales['subtotal_casco'] * 100.0):.1f}%" if totales["subtotal_casco"] > 0 else "0.0%",
        },
        {
            "Ítem": "",
            "Descripción": "TOTAL (USD)",
            "Moneda": "Dólares",
            "Porcentaje / Factor": f"TC: {totales['tc']:.2f}",
            "Monto (S/.)": totales["presupuesto_dolares"],
            "Mix (%)": "",
        },
    ])

    df_resumen_cierre = pd.DataFrame(resumen_rows)
    st.dataframe(
        df_resumen_cierre,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Ítem": st.column_config.TextColumn("Ítem", width="small"),
            "Descripción": st.column_config.TextColumn("Concepto / Partida", width="large"),
            "Moneda": st.column_config.TextColumn("Moneda", width="small"),
            "Porcentaje / Factor": st.column_config.TextColumn("% / TC", width="small"),
            "Monto (S/.)": st.column_config.NumberColumn("Importe", format="%.2f", width="medium"),
            "Mix (%)": st.column_config.TextColumn("Mix", width="small"),
        },
    )

    col_bot_exp1, col_bot_exp2 = st.columns([5, 5])
    with col_bot_exp1:
        st.download_button(
            "📥 EXPORTAR PRESUPUESTO A EXCEL (.XLSX) PARA COMPARTIR CON CLIENTE",
            data=xlsx_export_bytes,
            file_name=f"Presupuesto_{proy_name.replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
            key=f"btn_exp_excel_bot_{proy_name}",
        )
    with col_bot_exp2:
        st.info("✅ **Sincronizado en tiempo real:** Todas las partidas y tareas de este presupuesto están listas en **05. EJECUCIÓN & PARTIDAS**.")


def _render_tab_entregables(proy_name, proy_data):
    """Pestaña 4: Control de Planos, 3D Renders y Entregables Técnicos."""
    st.markdown("### 📋 ENTREGABLES, PLANOS Y REVISIONES")
    st.caption("Seguimiento del paquete de planos técnicos, modelos 3D y especificaciones del proyecto.")

    col_btn1, _ = st.columns([3, 7])
    with col_btn1:
        with st.popover("➕ REGISTRAR NUEVO ENTREGABLE", use_container_width=True):
            with st.form(f"f_new_ent_{proy_name}", clear_on_submit=True):
                e_esp = st.selectbox("Especialidad", ESPECIALIDADES_DEFAULT)
                e_nom = st.text_input("Nombre del Plano / Documento", placeholder="ej. A-01 Plano de Distribución y Mobiliario")
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
    """Pestaña 5: Partidas y Tareas (Sincronizada con 03. Presupuesto)."""
    st.markdown("### 🏗️ PARTIDAS Y TAREAS")
    st.caption(
        "Control operativo de contratistas, cronograma de obra y pagos por partida. "
        "Las partidas, tareas (1.01, 1.02...) y sus presupuestos provienen automáticamente de **03. PRESUPUESTO**."
    )

    col_ap1, col_ap2, _ = st.columns([2.8, 3.2, 4.0])
    with col_ap1:
        with st.popover("➕ AGREGAR PARTIDA DE OBRA", use_container_width=True):
            with st.form(f"f_new_part_{proy_name}", clear_on_submit=True):
                n_pa = st.text_input("Código / Nombre de Partida (ej. 5. Instalaciones Especiales)")
                n_pac = st.number_input("Presupuesto Pactado Contratista (S/)", value=0.0)
                if st.form_submit_button("CREAR PARTIDA") and n_pa:
                    st.session_state.partidas = pd.concat([st.session_state.partidas, pd.DataFrame([{'Proyecto': proy_name, 'Nombre_Partida': n_pa}])], ignore_index=True)
                    st.session_state.p_info = pd.concat([st.session_state.p_info, pd.DataFrame([{'Proyecto': proy_name, 'Nombre_Partida': n_pa, 'Monto_Pactado': n_pac}])], ignore_index=True)
                    clear_base_dfs()
                    st.rerun()

    with col_ap2:
        if st.button("🔄 SINCRONIZAR MONTOS CON 03. PRESUPUESTO", key=f"btn_sync_obra_ppto_{proy_name}", use_container_width=True):
            recalcular_totales_presupuesto_proyecto(proy_name, sincronizar_pactado=True)
            clear_base_dfs()
            st.rerun()

    parts_proy = st.session_state.partidas[st.session_state.partidas['Proyecto'] == proy_name]
    if parts_proy.empty:
        st.info("No hay partidas registradas para este proyecto. Configura tus partidas en **03. PRESUPUESTO** o crea una arriba.")
        return

    # Iterar partidas
    for idx_part, part_r in parts_proy.iterrows():
        p_nom = part_r['Nombre_Partida']
        st.markdown(f"<div class='cota-section-header'><span>■</span> PARTIDA // {p_nom.upper()}</div>", unsafe_allow_html=True)

        df_pactado = st.session_state.p_info[(st.session_state.p_info['Proyecto'] == proy_name) & (st.session_state.p_info['Nombre_Partida'] == p_nom)]
        monto_pactado = float(df_pactado['Monto_Pactado'].iloc[0]) if not df_pactado.empty else 0.0

        df_pagos_part = st.session_state.pagos[(st.session_state.pagos['Proyecto'] == proy_name) & (st.session_state.pagos['Partida'] == p_nom)]
        monto_pagado = pd.to_numeric(df_pagos_part['Monto'], errors='coerce').sum() if not df_pagos_part.empty else 0.0
        saldo = monto_pactado - monto_pagado

        col_b1, col_b2, col_b3, col_b4, col_b5 = st.columns([1.5, 1.8, 1.8, 1.5, 5.4])

        with col_b1:
            with st.popover("✏️ RENOMBRAR"):
                with st.form(f"ren_{proy_name}_{p_nom}_{idx_part}"):
                    nuevo_nombre = st.text_input("Nuevo Nombre", value=p_nom)
                    if st.form_submit_button("GUARDAR") and nuevo_nombre and nuevo_nombre != p_nom:
                        renombrar_partida_presupuesto(proy_name, p_nom, nuevo_nombre)
                        st.rerun()

        with col_b2:
            with st.popover("PRESUPUESTO"):
                with st.form(f"pact_{proy_name}_{p_nom}_{idx_part}"):
                    n_pac = st.number_input("Pactado (S/)", value=monto_pactado)
                    if st.form_submit_button("FIJAR"):
                        if df_pactado.empty:
                            st.session_state.p_info = pd.concat([st.session_state.p_info, pd.DataFrame([{'Proyecto': proy_name, 'Nombre_Partida': p_nom, 'Monto_Pactado': n_pac}])], ignore_index=True)
                        else:
                            st.session_state.p_info.loc[df_pactado.index, 'Monto_Pactado'] = n_pac
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
                            'Monto': p_monto,
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

        base_t_key = f"base_df_tasks_{proy_name}_{p_nom}_{idx_part}"
        counter_key = f"c_{base_t_key}"
        c_val = st.session_state.get(counter_key, 0)
        w_key = f"t_{proy_name}_{p_nom}_{idx_part}_{c_val}"

        cols_task_ed = [
            'Codigo_Item', 'Tarea', 'Moneda', 'Unidad', 'Metrado', 'Valor_Unitario', 'Presupuesto',
            'Especialidad', 'Contratista', 'Estado', 'Supervisado', 'Inicio', 'Fin',
            'Causa_Cumplimiento', 'Dependencia', 'Notas'
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

        display_t = df_tasks_p[cols_task_ed].copy() if not df_tasks_p.empty else pd.DataFrame(columns=cols_task_ed)
        display_t['Inicio'] = display_t['Inicio'].apply(lambda x: parse_date(x))
        display_t['Fin'] = display_t['Fin'].apply(lambda x: parse_date(x))
        display_t['Metrado'] = pd.to_numeric(display_t['Metrado'], errors='coerce').fillna(0.0)
        display_t['Valor_Unitario'] = pd.to_numeric(display_t['Valor_Unitario'], errors='coerce').fillna(0.0)
        display_t['Presupuesto'] = pd.to_numeric(display_t['Presupuesto'], errors='coerce').fillna(0.0)
        if 'Supervisado' in display_t.columns:
            display_t['Supervisado'] = display_t['Supervisado'].apply(_normalizar_supervisado)

        if base_t_key not in st.session_state:
            st.session_state[base_t_key] = display_t.copy()

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
                "Especialidad": st.column_config.SelectboxColumn("Especialidad", options=extraer_esp(st.session_state.maestro)),
                "Contratista": st.column_config.SelectboxColumn("Contratista", options=st.session_state.maestro['ID_Contratista'].tolist() if not st.session_state.maestro.empty else []),
                "Estado": st.column_config.SelectboxColumn("Estado", options=STATUS_TASKS),
                "Supervisado": st.column_config.SelectboxColumn("Supervisado ✓", options=["No", "Sí"], default="No", width="small"),
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

        # Botón para sugerir contratistas
        if st.button("🔍 Sugerir contratista disponible", key=f"sug_{proy_name}_{p_nom}_{idx_part}"):
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


def _render_cuadro_pagos_semanales(proy_name: str, proy_data: dict):
    """Renderiza el Cuadro de Pagos Semanales por Partida / Contratista y su exportación a Excel para el cliente."""
    cliente_str = safe_str(proy_data.get("Cliente", "")).strip() or "Sin cliente asignado"
    data_cuadro = obtener_cuadro_pagos_semanales_proyecto(proy_name)

    num_sem_actual = int(data_cuadro.get("num_semanas", 5) or 5)
    tc_actual = float(data_cuadro.get("tc", 3.60) or 3.60)
    cols_pago = obtener_columnas_pago_semanal(num_sem_actual)
    cols_por_pagar_actual = [c for c in data_cuadro.get("cols_por_pagar", []) if c in cols_pago]

    st.markdown("#### 📊 CUADRO DE PAGOS SEMANALES POR PARTIDA / CONTRATISTA")
    st.caption(
        f"**Proyecto:** {proy_name}  ·  **Cliente:** {cliente_str}  ·  "
        "Control semanal de adelantos y valorizaciones por contratista/partida, listo para exportar a Excel para el cliente."
    )

    # Barra de configuración y acciones
    c_cfg1, c_cfg2, c_cfg3 = st.columns([1.4, 1.4, 4.2])
    with c_cfg1:
        nuevo_num_sem = int(
            st.number_input(
                "N° de Semanas",
                min_value=1,
                max_value=30,
                value=num_sem_actual,
                step=1,
                key=f"num_sem_pagos_{proy_name}",
            )
        )
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

    # Botonera de sincronización, importación y exportación Excel
    b_act1, b_act2, b_act3 = st.columns([2.6, 2.4, 3.0])
    with b_act1:
        if st.button(
            "🔄 Sincronizar Partidas con 03. Presupuesto",
            key=f"btn_sync_pagos_{proy_name}",
            use_container_width=True,
            help="Trae o actualiza las partidas y montos totales desde la pestaña 03. Presupuesto sin perder los pagos semanales registrados.",
        ):
            data_cuadro = obtener_cuadro_pagos_semanales_proyecto(proy_name, sincronizar_partidas=True)
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

    with b_act3:
        xlsx_bytes = exportar_cuadro_pagos_semanales_excel(proy_name, data_cuadro)
        safe_fn = "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in proy_name).strip("_") or "Proyecto"
        st.download_button(
            label="📥 EXPORTAR EXCEL PARA CLIENTE (.XLSX)",
            data=xlsx_bytes,
            file_name=f"Control_Pagos_Semanales_{safe_fn}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"dl_xlsx_pagos_{proy_name}",
            type="primary",
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
            f"USD $ {tot_usd['PAGADO']:,.2f} ({pct_pag:.1f}% desembolsado)",
            border_color="#4A7C59",
            text_color="#4A7C59",
        )
    with k3:
        lbl_pp = ", ".join(cols_por_pagar_actual) if cols_por_pagar_actual else "Ninguna semana marcada"
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

    # Construcción de columnas del editor
    ordered_cols = ["Descripcion", "Moneda", "TOTAL"] + cols_pago + ["PAGADO", "SALDO", "Notas"]

    col_cfg_common = {
        "Descripcion": st.column_config.TextColumn("Descripción / Partida", width="medium", required=True),
        "Moneda": st.column_config.SelectboxColumn("Moneda", options=["Soles", "Dólares"], default="Soles", width="small"),
        "TOTAL": st.column_config.NumberColumn("TOTAL", format="%.2f", width="small"),
    }
    for c_sem in cols_pago:
        is_pp = c_sem in cols_por_pagar_actual
        header_lbl = f"⏳ {c_sem} (Por Pagar)" if is_pp else c_sem
        col_cfg_common[c_sem] = st.column_config.NumberColumn(
            header_lbl,
            format="%.2f",
            width="small",
            help="Marcada como 'Por Pagar' (no suma a PAGADO)" if is_pp else "Columna pagada (suma a PAGADO)",
        )
    col_cfg_common["PAGADO"] = st.column_config.NumberColumn("PAGADO ✓", format="%.2f", width="small", disabled=True)
    col_cfg_common["SALDO"] = st.column_config.NumberColumn("SALDO", format="%.2f", width="small", disabled=True)
    col_cfg_common["Notas"] = st.column_config.TextColumn("Notas", width="medium")

    # 1. Editor de TRABAJOS CONTRATISTAS
    st.markdown("##### 👷 TRABAJOS CONTRATISTAS")
    df_cont_view = pd.DataFrame(res_calc["filas_contratistas"])
    if df_cont_view.empty:
        df_cont_view = pd.DataFrame(columns=ordered_cols)
    else:
        for c_o in ordered_cols:
            if c_o not in df_cont_view.columns:
                df_cont_view[c_o] = "" if c_o in ("Descripcion", "Moneda", "Notas") else 0.0
        df_cont_view = df_cont_view[ordered_cols].copy()

    base_cont_key = f"base_df_pagos_cont_{proy_name}"
    cnt_cont_key = f"c_{base_cont_key}"
    c_cont_val = st.session_state.get(cnt_cont_key, 0)
    w_cont_key = f"ed_pagos_cont_{proy_name}_{c_cont_val}"

    st.session_state[base_cont_key] = df_cont_view.copy()

    def _on_edit_pagos_cont(b_key, w_key, p_name):
        if w_key not in st.session_state or b_key not in st.session_state:
            return
        state_ed = st.session_state[w_key]
        df_b = st.session_state[b_key].copy()
        for r_idx_str, changes in state_ed.get("edited_rows", {}).items():
            r_idx = int(r_idx_str)
            if r_idx < len(df_b):
                for col_k, val_k in changes.items():
                    if col_k in df_b.columns and df_b[col_k].dtype != object and isinstance(val_k, str):
                        df_b[col_k] = df_b[col_k].astype(object)
                    df_b.at[r_idx, col_k] = val_k
        for del_idx in sorted(state_ed.get("deleted_rows", []), reverse=True):
            if del_idx < len(df_b):
                df_b = df_b.drop(df_b.index[del_idx]).reset_index(drop=True)
        for add_r in state_ed.get("added_rows", []):
            new_r = {c: ("" if c in ("Descripcion", "Notas") else ("Soles" if c == "Moneda" else 0.0)) for c in df_b.columns}
            new_r.update(add_r)
            if not str(new_r.get("Descripcion", "")).strip():
                new_r["Descripcion"] = f"NUEVA PARTIDA {len(df_b) + 1}"
            df_b = pd.concat([df_b, pd.DataFrame([new_r])], ignore_index=True)

        d_cur = obtener_cuadro_pagos_semanales_proyecto(p_name)
        d_cur["filas_contratistas"] = df_b.to_dict(orient="records")
        guardar_cuadro_pagos_semanales_proyecto(p_name, d_cur)
        st.session_state[cnt_cont_key] = st.session_state.get(cnt_cont_key, 0) + 1

    st.data_editor(
        st.session_state[base_cont_key],
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key=w_cont_key,
        column_config=col_cfg_common,
        on_change=_on_edit_pagos_cont,
        args=(base_cont_key, w_cont_key, proy_name),
    )

    # 2. Editor de GESTIÓN Y GASTOS GENERALES
    st.markdown("##### 📐 GESTIÓN, SUPERVISIÓN Y GASTOS GENERALES")
    df_ges_view = pd.DataFrame([res_calc["fila_gestion"], res_calc["fila_gg"]])[ordered_cols].copy()

    base_ges_key = f"base_df_pagos_ges_{proy_name}"
    cnt_ges_key = f"c_{base_ges_key}"
    c_ges_val = st.session_state.get(cnt_ges_key, 0)
    w_ges_key = f"ed_pagos_ges_{proy_name}_{c_ges_val}"

    st.session_state[base_ges_key] = df_ges_view.copy()

    col_cfg_ges = dict(col_cfg_common)
    col_cfg_ges["Descripcion"] = st.column_config.TextColumn("Concepto", width="medium", disabled=True)

    def _on_edit_pagos_ges(b_key, w_key, p_name):
        if w_key not in st.session_state or b_key not in st.session_state:
            return
        state_ed = st.session_state[w_key]
        df_b = st.session_state[b_key].copy()
        for r_idx_str, changes in state_ed.get("edited_rows", {}).items():
            r_idx = int(r_idx_str)
            if r_idx < len(df_b):
                for col_k, val_k in changes.items():
                    if col_k in df_b.columns and df_b[col_k].dtype != object and isinstance(val_k, str):
                        df_b[col_k] = df_b[col_k].astype(object)
                    df_b.at[r_idx, col_k] = val_k

        d_cur = obtener_cuadro_pagos_semanales_proyecto(p_name)
        if len(df_b) >= 1:
            d_cur["fila_gestion"] = df_b.iloc[0].to_dict()
        if len(df_b) >= 2:
            d_cur["fila_gg"] = df_b.iloc[1].to_dict()
        guardar_cuadro_pagos_semanales_proyecto(p_name, d_cur)
        st.session_state[cnt_ges_key] = st.session_state.get(cnt_ges_key, 0) + 1

    st.data_editor(
        st.session_state[base_ges_key],
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key=w_ges_key,
        column_config=col_cfg_ges,
        on_change=_on_edit_pagos_ges,
        args=(base_ges_key, w_ges_key, proy_name),
    )

    # 3. Tabla de Resumen de Cierre (SUB TOTAL, Gestión, Gastos Generales, TOTAL Soles, Dólares)
    st.markdown("##### 📋 RESUMEN DE CIERRE (SUB TOTAL · TOTAL SOLES · DÓLARES)")
    filas_cierre = [
        res_calc["sub_total"],
        res_calc["fila_gestion"],
        res_calc["fila_gg"],
        res_calc["total_soles"],
        res_calc["total_dolares"],
    ]
    df_cierre = pd.DataFrame(filas_cierre)[ordered_cols].copy()
    col_cfg_cierre = dict(col_cfg_common)
    col_cfg_cierre["Descripcion"] = st.column_config.TextColumn("Resumen", width="medium")
    col_cfg_cierre["Moneda"] = st.column_config.TextColumn("Moneda", width="small")
    st.dataframe(
        df_cierre,
        use_container_width=True,
        hide_index=True,
        column_config=col_cfg_cierre,
    )


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
                c_hito = st.text_input("Hito / Concepto de Cobro", placeholder="ej. Anticipo 30% - Firma de Contrato")
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
        n_conc = cg1.text_input("Concepto de Gasto (ej. Taxis, materiales menores, ferretería)")
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
                p_elem = st.text_input("Elemento (ej. Zócalo, Puerta Principal, Pintura Techo)")
                p_desc = st.text_area("Descripción de la Observación", placeholder="ej. Retocar masillado y pintura en esquina superior derecha")
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

