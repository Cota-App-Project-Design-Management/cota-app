"""
Vista detallada de Proyecto (Fullscreen):
Resumen, Fases de Diseño, Especificaciones FF&E, Entregables y Planos,
Ejecución de Obra, Cobros y Finanzas, Reuniones y Actas, y Punch List de Entrega.
"""

import datetime
import uuid
import altair as alt
import pandas as pd
import streamlit as st

from cota.config import (
    AMBIENTES_DEFAULT,
    CATEGORIAS_FFE,
    ESPECIALIDADES_DEFAULT,
    PRIORIDADES_PUNCH,
    STATUS_COBROS,
    STATUS_FASES,
    STATUS_FFE,
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
    COLS_MAT,
    COLS_PAGOS,
    COLS_PUNCH,
    clear_base_dfs,
    on_table_edit,
    sembrar_fases_default,
)
from cota.pdf import generar_pdf_minuta
from cota.ui.components import render_metric_card
from cota.utils import (
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

    # Asegurar inicialización de fases para este proyecto
    if 'fases' not in st.session_state or st.session_state.fases.empty:
        st.session_state.fases = sembrar_fases_default(proy_name, proy_data.get('Inicio'))
    else:
        fases_p = st.session_state.fases[st.session_state.fases['Proyecto'] == proy_name]
        if fases_p.empty:
            nuevas_f = sembrar_fases_default(proy_name, proy_data.get('Inicio'))
            st.session_state.fases = pd.concat([st.session_state.fases, nuevas_f], ignore_index=True)

    # Tabs especializadas para diseño y arquitectura
    t_resumen, t_fases, t_ffe, t_planos, t_obra, t_finanzas, t_actas, t_punch = st.tabs([
        "01. RESUMEN",
        "02. FASES DE DISEÑO",
        "03. ESPECIFICACIONES FF&E",
        "04. ENTREGABLES & PLANOS",
        "05. EJECUCIÓN & PARTIDAS",
        "06. COBROS & FINANZAS",
        "07. REUNIONES & ACTAS",
        "08. PUNCH LIST"
    ])

    with t_resumen:
        _render_tab_resumen(proy_name, proy_data)

    with t_fases:
        _render_tab_fases(proy_name, proy_data)

    with t_ffe:
        _render_tab_ffe(proy_name, proy_data)

    with t_planos:
        _render_tab_entregables(proy_name, proy_data)

    with t_obra:
        _render_tab_obra(proy_name, proy_data)

    with t_finanzas:
        _render_tab_finanzas(proy_name, proy_data)

    with t_actas:
        _render_tab_actas(proy_name, proy_data)

    with t_punch:
        _render_tab_punch(proy_name, proy_data)


# ====================================================
# SUB-RENDERERS PARA CADA PESTAÑA
# ====================================================

def _render_tab_resumen(proy_name, proy_data):
    """Pestaña 1: Resumen ejecutivo y métricas globales del proyecto."""
    ppto_venta = safe_float(proy_data.get('Presupuesto', 0.0))
    hon_diseno = safe_float(proy_data.get('Honorarios_Diseno', 0.0))
    ppto_ffe = safe_float(proy_data.get('Presupuesto_FFE', 0.0))
    gg_ppto = safe_float(proy_data.get('GG_Presupuesto', 0.0))

    # Pagos a contratistas
    df_pagos_p = st.session_state.pagos[st.session_state.pagos['Proyecto'] == proy_name]
    total_pagado_maestros = pd.to_numeric(df_pagos_p['Monto'], errors='coerce').sum() if not df_pagos_p.empty else 0.0

    # FF&E real
    df_mat_p = st.session_state.materiales[st.session_state.materiales['Proyecto'] == proy_name]
    costo_real_ffe = pd.to_numeric(df_mat_p['Costo_Real'], errors='coerce').sum() if not df_mat_p.empty else 0.0

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

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        render_metric_card("Ppto. Total", format_currency(ppto_venta), f"Honorarios: {format_currency(hon_diseno)}")
    with c2:
        render_metric_card("Cobrado a Cliente", format_currency(total_cobrado_cliente), f"Saldo: {format_currency(max(0.0, ppto_venta - total_cobrado_cliente))}", border_color="#4A7C59", text_color="#4A7C59")
    with c3:
        render_metric_card("Pagos Contratistas", format_currency(total_pagado_maestros), "Ejecución de obra")
    with c4:
        render_metric_card("Compras FF&E", format_currency(costo_real_ffe), f"Meta: {format_currency(ppto_ffe)}")
    with c5:
        col_caja = "#4A7C59" if caja_restante >= 0 else "#C93B2B"
        render_metric_card("Caja Chica Saldo", format_currency(caja_restante), f"Gastado: {format_currency(caja_gastada)}", border_color=col_caja, text_color=col_caja)
    with c6:
        render_metric_card("Fases Aprobadas", f"{pct_fases:.0f}%", f"{n_fases_ok} de {n_fases} fases completadas", border_color="#C85A32", text_color="#C85A32")

    st.divider()

    # Datos descriptivos y estado de fases
    col_d1, col_d2 = st.columns([1, 1.1])
    with col_d1:
        st.markdown("#### FICHA TÉCNICA DEL PROYECTO")
        info_items = [
            ("Líder de Diseño", proy_data.get('Encargado', 'N/A')),
            ("Cliente", proy_data.get('Cliente', 'N/A')),
            ("Tipología", proy_data.get('Tipo_Proyecto', 'Diseño Interior')),
            ("Ubicación", proy_data.get('Ubicación', 'N/A')),
            ("Carpeta / División", proy_data.get('Division', 'General')),
            ("Fecha Inicio", format_date(proy_data.get('Inicio'))),
            ("Fecha Estimada Entrega", format_date(proy_data.get('Fin'))),
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
        st.markdown("#### ESTADO DE LAS 8 FASES DE DISEÑO")
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


def _render_tab_fases(proy_name, proy_data):
    """Pestaña 2: Fases de diseño y cronograma canónico."""
    st.markdown("### 📐 CICLO DE VIDA Y FASES DEL DISEÑO")
    st.caption("Estructura secuencial para estudios de interiores y arquitectura: desde el brief inicial hasta la entrega final.")

    fases_df = st.session_state.fases[st.session_state.fases['Proyecto'] == proy_name].copy()
    if fases_df.empty:
        st.session_state.fases = sembrar_fases_default(proy_name, proy_data.get('Inicio'))
        fases_df = st.session_state.fases[st.session_state.fases['Proyecto'] == proy_name].copy()

    fases_df = fases_df.sort_values(by='Orden')

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
    st.markdown("#### EDITOR DE FASES Y APROBACIÓN DEL CLIENTE")

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


def _render_tab_ffe(proy_name, proy_data):
    """Pestaña 3: Especificaciones FF&E (Mobiliario, Iluminación, Acabados por Ambiente)."""
    st.markdown("### 🛋️ ESPECIFICACIONES FF&E Y MATERIALES POR AMBIENTE")
    st.caption("Planilla de mobiliario fijo/suelto, luminarias, revestimientos, griferías y decoración.")

    df_mat_p = st.session_state.materiales[st.session_state.materiales['Proyecto'] == proy_name].copy()

    # Ambientes detectados
    ambientes_existentes = sorted(list(set(df_mat_p['Ambiente'].dropna().tolist() + AMBIENTES_DEFAULT)))
    if not ambientes_existentes:
        ambientes_existentes = AMBIENTES_DEFAULT

    # Filtro por ambiente
    col_f1, col_f2, col_act = st.columns([3, 3, 4])
    with col_f1:
        filtro_amb = st.selectbox("Filtrar por Ambiente:", ["Todos"] + ambientes_existentes, key=f"f_amb_{proy_name}")
    with col_f2:
        filtro_cat = st.selectbox("Filtrar por Categoría:", ["Todas"] + CATEGORIAS_FFE, key=f"f_cat_{proy_name}")

    with col_act:
        with st.popover("➕ AGREGAR ESPECIFICACIÓN RÁPIDA", use_container_width=True):
            with st.form(f"form_new_ffe_{proy_name}", clear_on_submit=True):
                n_amb = st.selectbox("Ambiente", ambientes_existentes)
                n_cat = st.selectbox("Categoría", CATEGORIAS_FFE)
                n_cod = st.text_input("Código / Tag (ej. MOB-01, LUM-04)")
                n_desc = st.text_input("Descripción del Elemento", placeholder="ej. Sofá 3 cuerpos tapizado en lino gris")
                col_c1, col_c2 = st.columns(2)
                n_cant = col_c1.number_input("Cantidad", value=1.0, min_value=0.1, step=1.0)
                n_und = col_c2.selectbox("Unidad", UNIDADES_MEDIDA)
                col_p1, col_p2 = st.columns(2)
                n_p_unit = col_p1.number_input("Precio Unit. Estimado (S/)", value=0.0)
                n_costo_real = col_p2.number_input("Costo Real (si ya se cotizó)", value=0.0)
                n_prov = st.text_input("Proveedor / Fabricante")
                n_est = st.selectbox("Estado Inicial", STATUS_FFE)
                n_link = st.text_input("Link de Referencia / Ficha Técnica (URL)")
                n_notas = st.text_input("Notas / Dimensiones / Acabado")

                if st.form_submit_button("REGISTRAR ESPECIFICACIÓN") and n_desc:
                    costo_est = n_cant * n_p_unit
                    nueva_fila = pd.DataFrame([{
                        'ID': f"FFE_{int(datetime.datetime.now().timestamp())}_{uuid.uuid4().hex[:6]}",
                        'Proyecto': proy_name,
                        'Ambiente': n_amb,
                        'Categoria': n_cat,
                        'Codigo_Ref': n_cod,
                        'Material': n_desc,
                        'Cantidad': n_cant,
                        'Unidad': n_und,
                        'Precio_Unit_Estimado': n_p_unit,
                        'Costo_Estimado': costo_est,
                        'Costo_Real': n_costo_real,
                        'Proveedor': n_prov,
                        'Estado': n_est,
                        'Link_Ref': n_link,
                        'Notas': n_notas
                    }])
                    st.session_state.materiales = pd.concat([st.session_state.materiales, nueva_fila[COLS_MAT]], ignore_index=True)
                    clear_base_dfs()
                    st.rerun()

    # Métricas del subconjunto de FF&E
    df_filtrado = df_mat_p.copy()
    ffe_group_cols = ['Proyecto']
    ffe_group_vals = [proy_name]
    if filtro_amb != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Ambiente'] == filtro_amb]
        ffe_group_cols.append('Ambiente')
        ffe_group_vals.append(filtro_amb)
    if filtro_cat != "Todas":
        df_filtrado = df_filtrado[df_filtrado['Categoria'] == filtro_cat]
        ffe_group_cols.append('Categoria')
        ffe_group_vals.append(filtro_cat)

    tot_est = pd.to_numeric(df_filtrado['Costo_Estimado'], errors='coerce').sum() if not df_filtrado.empty else 0.0
    tot_real = pd.to_numeric(df_filtrado['Costo_Real'], errors='coerce').sum() if not df_filtrado.empty else 0.0
    n_items = len(df_filtrado)
    n_aprobados = len(df_filtrado[df_filtrado['Estado'].isin(['🔵 Aprobado Cliente', '🟣 En Producción', '🟠 En Despacho', '🟢 Instalado / Recibido'])])

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        render_metric_card("Total Estimado", format_currency(tot_est), f"{n_items} elementos especificados")
    with m2:
        render_metric_card("Total Compra / Real", format_currency(tot_real), f"Diferencia: {format_currency(tot_est - tot_real)}", border_color="#C85A32")
    with m3:
        render_metric_card("Aprobados por Cliente", f"{n_aprobados} / {n_items}", f"{(n_aprobados/n_items*100 if n_items>0 else 0):.0f}% del catálogo", border_color="#4A7C59", text_color="#4A7C59")
    with m4:
        render_metric_card("Ambientes", str(df_mat_p['Ambiente'].nunique()), "Distribuidos en el proyecto", border_color="#6E665E")

    # Resumen por Ambiente si hay datos
    if not df_mat_p.empty:
        with st.expander("📊 Ver desglose de presupuesto FF&E por Ambiente", expanded=False):
            df_amb_sum = df_mat_p.copy()
            df_amb_sum['Costo_Estimado'] = pd.to_numeric(df_amb_sum['Costo_Estimado'], errors='coerce').fillna(0.0)
            df_amb_sum['Costo_Real'] = pd.to_numeric(df_amb_sum['Costo_Real'], errors='coerce').fillna(0.0)
            res_amb = df_amb_sum.groupby('Ambiente', as_index=False).agg(
                Items=('ID', 'count'),
                Presupuesto_Estimado=('Costo_Estimado', 'sum'),
                Costo_Real=('Costo_Real', 'sum')
            ).sort_values('Presupuesto_Estimado', ascending=False)
            res_amb['Diferencia'] = res_amb['Presupuesto_Estimado'] - res_amb['Costo_Real']
            st.dataframe(
                res_amb,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Ambiente": st.column_config.TextColumn("Ambiente"),
                    "Items": st.column_config.NumberColumn("Ítems", format="%d"),
                    "Presupuesto_Estimado": st.column_config.NumberColumn("Estimado", format="S/ %.2f"),
                    "Costo_Real": st.column_config.NumberColumn("Compra / Real", format="S/ %.2f"),
                    "Diferencia": st.column_config.NumberColumn("Saldo / Ahorro", format="S/ %.2f"),
                }
            )

    st.divider()

    # Editor interactivo de especificaciones
    base_ffe_key = f"base_df_ffe_{proy_name}_{filtro_amb}_{filtro_cat}"
    counter_key = f"c_{base_ffe_key}"
    c_val = st.session_state.get(counter_key, 0)
    w_key = f"ed_ffe_{proy_name}_{filtro_amb}_{filtro_cat}_{c_val}"

    display_cols = ['ID', 'Ambiente', 'Categoria', 'Codigo_Ref', 'Material', 'Cantidad', 'Unidad', 'Precio_Unit_Estimado', 'Costo_Estimado', 'Costo_Real', 'Proveedor', 'Estado', 'Link_Ref', 'Notas']
    for c in display_cols:
        if c not in df_filtrado.columns:
            df_filtrado[c] = ""

    display_df = df_filtrado[display_cols].copy()
    display_df['Cantidad'] = pd.to_numeric(display_df['Cantidad'], errors='coerce').fillna(1.0)
    display_df['Precio_Unit_Estimado'] = pd.to_numeric(display_df['Precio_Unit_Estimado'], errors='coerce').fillna(0.0)
    display_df['Costo_Estimado'] = pd.to_numeric(display_df['Costo_Estimado'], errors='coerce').fillna(0.0)
    display_df['Costo_Real'] = pd.to_numeric(display_df['Costo_Real'], errors='coerce').fillna(0.0)
    for c in ['Link_Ref', 'Material', 'Codigo_Ref', 'Proveedor', 'Notas', 'Estado', 'Ambiente', 'Categoria', 'Unidad']:
        if c in display_df.columns:
            display_df[c] = display_df[c].fillna("").astype(str).replace('nan', '').replace('None', '')

    if base_ffe_key not in st.session_state:
        st.session_state[base_ffe_key] = display_df.copy()

    st.data_editor(
        st.session_state[base_ffe_key],
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key=w_key,
        column_config={
            "ID": None,
            "Ambiente": st.column_config.SelectboxColumn("Ambiente", options=ambientes_existentes, required=True),
            "Categoria": st.column_config.SelectboxColumn("Categoría", options=CATEGORIAS_FFE, required=True),
            "Codigo_Ref": st.column_config.TextColumn("Tag", width="small"),
            "Material": st.column_config.TextColumn("Elemento / Especificación", width="large", required=True),
            "Cantidad": st.column_config.NumberColumn("Cant.", format="%.1f"),
            "Unidad": st.column_config.SelectboxColumn("Und.", options=UNIDADES_MEDIDA),
            "Precio_Unit_Estimado": st.column_config.NumberColumn("P. Unit Estimado", format="S/ %.2f"),
            "Costo_Estimado": st.column_config.NumberColumn("Costo Estimado", format="S/ %.2f"),
            "Costo_Real": st.column_config.NumberColumn("Costo Real", format="S/ %.2f"),
            "Proveedor": st.column_config.TextColumn("Proveedor / Tienda"),
            "Estado": st.column_config.SelectboxColumn("Estado", options=STATUS_FFE),
            "Link_Ref": st.column_config.LinkColumn("Enlace Ficha / Producto"),
            "Notas": st.column_config.TextColumn("Notas / Acabados")
        },
        on_change=on_table_edit,
        args=(
            base_ffe_key,
            w_key,
            'materiales',
            ffe_group_cols,
            ffe_group_vals,
            None,
            ['Ambiente', 'Categoria', 'Codigo_Ref', 'Material', 'Unidad', 'Proveedor', 'Estado', 'Link_Ref', 'Notas'],
            None,
            ['Cantidad', 'Precio_Unit_Estimado', 'Costo_Estimado', 'Costo_Real'],
            'ID'
        )
    )


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
    """Pestaña 5: Ejecución de Obra, Partidas y Tareas Técnicas."""
    st.markdown("### 🏗️ EJECUCIÓN DE OBRA Y PARTIDAS")
    st.caption("Control operativo de contratistas, tareas por sección y cronograma de obra.")

    # Agregar Partida
    col_ap1, _ = st.columns([3, 7])
    with col_ap1:
        with st.popover("➕ AGREGAR PARTIDA DE OBRA", use_container_width=True):
            with st.form(f"f_new_part_{proy_name}", clear_on_submit=True):
                n_pa = st.text_input("Código / Nombre de Partida (ej. 01. Demoliciones, 02. Carpintería Fija)")
                n_pac = st.number_input("Presupuesto Pactado Contratista (S/)", value=0.0)
                if st.form_submit_button("CREAR PARTIDA") and n_pa:
                    st.session_state.partidas = pd.concat([st.session_state.partidas, pd.DataFrame([{'Proyecto': proy_name, 'Nombre_Partida': n_pa}])], ignore_index=True)
                    st.session_state.p_info = pd.concat([st.session_state.p_info, pd.DataFrame([{'Proyecto': proy_name, 'Nombre_Partida': n_pa, 'Monto_Pactado': n_pac}])], ignore_index=True)
                    clear_base_dfs()
                    st.rerun()

    parts_proy = st.session_state.partidas[st.session_state.partidas['Proyecto'] == proy_name]
    if parts_proy.empty:
        st.info("No hay partidas registradas para este proyecto. Crea una partida arriba para comenzar.")
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
        col_s = '#4A7C59' if saldo >= 0 else '#C93B2B'

        col_b1, col_b2, col_b3, col_b4, col_b5 = st.columns([1.5, 1.8, 1.8, 1.5, 5.4])

        with col_b1:
            with st.popover("✏️ RENOMBRAR"):
                with st.form(f"ren_{proy_name}_{p_nom}_{idx_part}"):
                    nuevo_nombre = st.text_input("Nuevo Nombre", value=p_nom)
                    if st.form_submit_button("GUARDAR") and nuevo_nombre and nuevo_nombre != p_nom:
                        st.session_state.partidas.at[idx_part, 'Nombre_Partida'] = nuevo_nombre
                        st.session_state.p_info.loc[(st.session_state.p_info['Proyecto'] == proy_name) & (st.session_state.p_info['Nombre_Partida'] == p_nom), 'Nombre_Partida'] = nuevo_nombre
                        st.session_state.tasks.loc[(st.session_state.tasks['Proyecto'] == proy_name) & (st.session_state.tasks['Partida'] == p_nom), 'Partida'] = nuevo_nombre
                        st.session_state.pagos.loc[(st.session_state.pagos['Proyecto'] == proy_name) & (st.session_state.pagos['Partida'] == p_nom), 'Partida'] = nuevo_nombre
                        clear_base_dfs()
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
                    clear_base_dfs()
                    st.rerun()

        with col_b5:
            cls_s = 'cota-badge-saldo-ok' if saldo >= 0 else 'cota-badge-saldo-error'
            st.markdown(f"""
                <div class='cota-badge-container'>
                    <span class='cota-badge cota-badge-pactado'>PACTADO: {format_currency(monto_pactado)}</span>
                    <span class='cota-badge cota-badge-pagado'>PAGADO: {format_currency(monto_pagado)}</span>
                    <span class='cota-badge {cls_s}'>SALDO: {format_currency(saldo)}</span>
                </div>
            """, unsafe_allow_html=True)

        # Editor de tareas de la partida
        mask_t = (st.session_state.tasks['Proyecto'] == proy_name) & (st.session_state.tasks['Partida'] == p_nom)
        df_tasks_p = st.session_state.tasks[mask_t].copy().reset_index(drop=True)

        base_t_key = f"base_df_tasks_{proy_name}_{p_nom}_{idx_part}"
        counter_key = f"c_{base_t_key}"
        c_val = st.session_state.get(counter_key, 0)
        w_key = f"t_{proy_name}_{p_nom}_{idx_part}_{c_val}"

        display_t = df_tasks_p[['Tarea', 'Especialidad', 'Contratista', 'Estado', 'Inicio', 'Fin', 'Causa_Cumplimiento', 'Dependencia', 'Notas']].copy() if not df_tasks_p.empty else pd.DataFrame(columns=['Tarea', 'Especialidad', 'Contratista', 'Estado', 'Inicio', 'Fin', 'Causa_Cumplimiento', 'Dependencia', 'Notas'])
        display_t['Inicio'] = display_t['Inicio'].apply(lambda x: parse_date(x))
        display_t['Fin'] = display_t['Fin'].apply(lambda x: parse_date(x))

        if base_t_key not in st.session_state:
            st.session_state[base_t_key] = display_t.copy()

        st.data_editor(
            st.session_state[base_t_key],
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            key=w_key,
            column_config={
                "Tarea": st.column_config.TextColumn("Tarea / Actividad", width="large", required=True),
                "Especialidad": st.column_config.SelectboxColumn("Especialidad", options=extraer_esp(st.session_state.maestro)),
                "Contratista": st.column_config.SelectboxColumn("Contratista", options=st.session_state.maestro['ID_Contratista'].tolist() if not st.session_state.maestro.empty else []),
                "Estado": st.column_config.SelectboxColumn("Estado", options=STATUS_TASKS),
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
                ['Tarea', 'Especialidad', 'Contratista', 'Estado', 'Causa_Cumplimiento', 'Dependencia', 'Notas'],
                None,
                None,
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


def _render_tab_finanzas(proy_name, proy_data):
    """Pestaña 6: Hitos de Cobro al Cliente, Flujo de Caja y Caja Chica."""
    st.markdown("### 💰 PLAN DE COBROS AL CLIENTE Y FINANZAS")
    st.caption("Control de cuentas por cobrar, hitos contractuales y liquidación financiera del proyecto.")

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
            st.markdown(f"""
            <div style='background-color: #FFFFFF; border: 1px solid #DFD9CE; border-left: 4px solid #C85A32; border-radius: 6px; padding: 14px;'>
                <div style='color: #C85A32; font-weight: 700; font-size: 15px; margin-bottom: 6px;'>{r_ses['Nombre_Sesion']}</div>
                <div style='display: grid; grid-template-columns: repeat(3, 1fr); font-size: 12px; color: #262320; gap: 8px;'>
                    <div><b style='color:#6E665E;'>Fecha:</b> {r_ses['Fecha_Real']}</div>
                    <div><b style='color:#6E665E;'>Hora:</b> {r_ses['Hora']}</div>
                    <div><b style='color:#6E665E;'>Tipo:</b> {r_ses.get('Tipo_Reunion', 'Coordinación')}</div>
                    <div><b style='color:#6E665E;'>Organizador:</b> {r_ses['Organizador']}</div>
                    <div><b style='color:#6E665E;'>Fase:</b> {r_ses['Etapa']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

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
    """Pestaña 8: Punch List / Lista de Observaciones para Entrega."""
    st.markdown("### 🔍 PUNCH LIST Y PENDIENTES DE ENTREGA")
    st.caption("Inspección de detalles finales por ambiente antes de la entrega formal al cliente.")

    if 'pendientes_entrega' not in st.session_state:
        st.session_state.pendientes_entrega = pd.DataFrame(columns=COLS_PUNCH)

    df_punch = st.session_state.pendientes_entrega[st.session_state.pendientes_entrega['Proyecto'] == proy_name].copy()

    col_btn1, _ = st.columns([3, 7])
    with col_btn1:
        with st.popover("➕ AGREGAR OBSERVACIÓN / DETALLE", use_container_width=True):
            with st.form(f"f_new_punch_{proy_name}", clear_on_submit=True):
                p_amb = st.selectbox("Ambiente", AMBIENTES_DEFAULT)
                p_elem = st.text_input("Elemento (ej. Zócalo, Puerta Principal, Pintura Techo)")
                p_desc = st.text_area("Detalle / Observación", placeholder="ej. Retocar masillado y pintura en esquina superior derecha")
                col_r1, col_r2 = st.columns(2)
                p_resp = col_r1.text_input("Responsable (Contratista / Proveedor)")
                p_prio = col_r2.selectbox("Prioridad", PRIORIDADES_PUNCH, index=1)
                p_est = st.selectbox("Estado", STATUS_PUNCH)

                if st.form_submit_button("REGISTRAR PENDIENTE") and p_desc:
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

