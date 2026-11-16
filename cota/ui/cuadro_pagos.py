"""
Componentes interactivos y ventanas flotantes del Cuadro de Pagos Semanales:
- Ventana flotante al seleccionar celda ('Ingresar nuevo pago' + pagos de la celda/semana).
- Modal 'Registro de Pago' (Contratista, Tipo de Pago, Fecha, Monto) con buscador integrado.
- Modal de pagos realizados por semana y panel resumen en Streamlit ('a quién hacer los pagos').
"""

import html as html_lib
import pandas as pd
import streamlit as st

from cota.cotizacion import (
    _extraer_contratista_de_notas,
    _formatear_fecha_ddmmyyyy,
    _normalizar_col_pago_name,
    _normalizar_detalle_pagos_celda,
    etiqueta_export_columna_pago,
    obtener_pagos_semana,
    resumen_contratistas_semana,
)
from cota.utils import safe_float, safe_str


def build_cell_payments_badge_and_tooltip(
    fila_d: dict, c_s: str, pref_m: str, v_num: float
) -> tuple[str, str, str, list[dict], str]:
    """
    Construye el HTML interno, el indicador visual de esquina y el texto tooltip de una celda semanal,
    combinando los pagos registrados (`Pagos_Detalle`) y las notas manuales (`Notas_Pagos`).
    """
    pd_map = fila_d.get("Pagos_Detalle", {}) if isinstance(fila_d.get("Pagos_Detalle"), dict) else {}
    pagos_celda = _normalizar_detalle_pagos_celda(pd_map.get(c_s, []), c_s)
    np_dict = fila_d.get("Notas_Pagos", {}) if isinstance(fila_d.get("Notas_Pagos"), dict) else {}
    nota_manual = safe_str(np_dict.get(c_s, "")).strip()

    is_zero = abs(v_num) < 0.005
    val_str = "" if is_zero else f"{pref_m}{v_num:,.2f}"

    tooltip_lines = []
    for p in pagos_celda:
        con_txt = p.get("contratista") or "Sin contratista"
        f_txt = _formatear_fecha_ddmmyyyy(p.get("fecha", ""))
        m_txt = f"{pref_m}{safe_float(p.get('monto', 0.0), 0.0):,.2f}"
        tooltip_lines.append(f"{con_txt} · {p.get('tipo', '')} ({f_txt}): {m_txt}")
    if nota_manual:
        tooltip_lines.append(f"Nota: {nota_manual}")
    tooltip_txt = "\n".join(tooltip_lines)

    count_badge = ""
    if len(pagos_celda) > 1:
        count_badge = (
            f"<span class='cota-cell-multi-badge' "
            f"title='{len(pagos_celda)} pagos registrados (suma)'>{len(pagos_celda)}</span>"
        )

    if count_badge or nota_manual:
        disp_val = val_str if val_str else "<span style='color:#C85A32; font-size:11px;'>💬</span>"
        disp_inner = f"{count_badge}{disp_val}"
    else:
        disp_inner = val_str

    corner_dot = ""
    if pagos_celda or nota_manual:
        cor_color = "#C85A32" if nota_manual else "#4A7C59"
        corner_dot = (
            f"<span style='position:absolute; top:0; right:0; width:0; height:0; "
            f"border-top:7px solid {cor_color}; border-left:7px solid transparent;'></span>"
        )

    default_contra = _extraer_contratista_de_notas(fila_d.get("Notas", ""))
    return disp_inner, corner_dot, tooltip_txt, pagos_celda, default_contra


def resolver_semana_activa_cuadro(proy_name: str, data_cuadro: dict, cols_pago: list[str]) -> str:
    """
    Determina la semana activa sincronizada para la vista de 'Pagos realizados esa semana'
    y para el bloque resumen en Excel/PDF.
    """
    opciones = list(cols_pago) + ["ALL"]
    sel_key = f"sel_sem_resumen_{proy_name}"

    cur_widget = safe_str(st.session_state.get(sel_key, "")).strip()
    if cur_widget in opciones:
        return cur_widget

    sem_guardada = safe_str(data_cuadro.get("semana_activa", "")).strip()
    if sem_guardada == "ALL":
        return "ALL"
    if sem_guardada:
        norm_g = _normalizar_col_pago_name(sem_guardada, cols_pago)
        if norm_g in cols_pago:
            return norm_g

    for c_pp in data_cuadro.get("cols_por_pagar", []):
        if c_pp in cols_pago and obtener_pagos_semana(data_cuadro, c_pp):
            return c_pp

    con_pagos = [c for c in cols_pago if obtener_pagos_semana(data_cuadro, c)]
    if con_pagos:
        return con_pagos[-1]

    return cols_pago[0] if cols_pago else "ALL"


def render_pagos_realizados_por_semana_panel(
    proy_name: str, data_cuadro: dict, cols_pago: list[str], sem_activa: str
):
    """
    Muestra debajo del Cuadro de Pagos el detalle de los pagos realizados en la semana seleccionada
    y el resumen agrupado de a quién hacer los pagos (solo Contratista y Monto).
    """
    lbl_sem = "Todas las semanas" if sem_activa == "ALL" else etiqueta_export_columna_pago(sem_activa)
    pagos_sem = obtener_pagos_semana(data_cuadro, sem_activa)
    res_con = resumen_contratistas_semana(data_cuadro, sem_activa)

    st.markdown(
        f"<div style='margin-top:6px; margin-bottom:6px; display:flex; align-items:center; gap:8px;'>"
        f"<span style='font-size:14px; font-weight:800; color:#262320;'>📅 PAGOS REALIZADOS — {html_lib.escape(lbl_sem.upper())}</span>"
        f"<span style='font-size:11.5px; color:#6E665E; background:#FAF8F5; border:1px solid #DFD9CE; border-radius:99px; padding:2px 9px;'>{len(pagos_sem)} pago(s)</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    col_det, col_res = st.columns([6.2, 3.8])
    with col_det:
        with st.container(border=True):
            st.markdown(f"**📋 Detalle de pagos realizados ({lbl_sem})**")
            if pagos_sem:
                rows_det = []
                for p in pagos_sem:
                    row_d = {
                        "Partida": p["partida"],
                        "Contratista": p["contratista"] or "Sin contratista",
                        "Tipo de Pago": p["tipo"],
                        "Fecha": p["fecha_fmt"],
                        "Monto": f"{p['pref']}{p['monto']:,.2f}",
                    }
                    if sem_activa == "ALL":
                        row_d = {"Semana": p["semana_label"], **row_d}
                    rows_det.append(row_d)
                st.dataframe(pd.DataFrame(rows_det), use_container_width=True, hide_index=True)
            else:
                st.caption(f"No hay pagos detallados registrados en {lbl_sem}. Haz clic en cualquier celda de semana arriba para ingresar pagos.")

    with col_res:
        with st.container(border=True):
            st.markdown(f"**💸 A quién hacer los pagos — {lbl_sem}**")
            st.caption("Resumen incluido al exportar (solo Contratista y Monto).")
            if res_con:
                rows_r = [
                    {
                        "Contratista": r["contratista"],
                        "Monto": f"{r['pref']}{r['monto']:,.2f}",
                    }
                    for r in res_con
                ]
                st.dataframe(pd.DataFrame(rows_r), use_container_width=True, hide_index=True)
                monedas_u = {r["moneda"] for r in res_con}
                if len(monedas_u) == 1:
                    tot_w = sum(r["monto"] for r in res_con)
                    pref_u = res_con[0]["pref"]
                    st.markdown(
                        f"<div style='text-align:right; font-size:13px; font-weight:800; color:#262320; padding-top:4px;'>"
                        f"Total {html_lib.escape(lbl_sem)}: <span style='color:#C85A32;'>{pref_u}{tot_w:,.2f}</span></div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("Sin pagos asignados a contratistas en esta semana.")


def build_pagos_floating_ui_js() -> str:
    """
    Retorna el código JavaScript modular que gestiona:
    1. Ventana flotante inicial al hacer clic en una celda ('Ingresar nuevo pago' + pagos de la celda y semana).
    2. Ventana flotante 'Registro de Pago' (Contratista y Tipo de Pago con buscador, Fecha, Monto).
    3. Ventana flotante al seleccionar una semana en cabecera ('Pagos realizados esa semana' + 'A quién pagar').
    """
    return r"""
        const colLabels = payload.colLabels || {};
        const colExportLabels = payload.colExportLabels || {};
        const contractorsMaster = Array.isArray(payload.contractors) ? payload.contractors : [];
        const paymentTypes = Array.isArray(payload.paymentTypes) ? payload.paymentTypes : ['Adelanto', 'Valorización', 'Liquidación'];
        let allPayments = Array.isArray(payload.payments) ? payload.payments.slice() : [];
        const todayIso = payload.todayIso || new Date().toISOString().slice(0, 10);

        function escHtml(val) {
            return String(val == null ? '' : val)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        function fmtIsoToDisplay(isoStr) {
            const s = String(isoStr || '').trim();
            const m = s.match(/^(\d{4})-(\d{2})-(\d{2})$/);
            if (m) return m[3] + '/' + m[2] + '/' + m[1];
            return s || '';
        }

        function getOverlayHost() {
            const fsEl = parentDoc.fullscreenElement;
            return fsEl || parentDoc.body;
        }

        function ensureFloatingStyles() {
            let stEl = parentDoc.getElementById('cota_pagos_floating_styles');
            if (!stEl) {
                stEl = parentDoc.createElement('style');
                stEl.id = 'cota_pagos_floating_styles';
                parentDoc.head.appendChild(stEl);
            }
            stEl.textContent = `
                .cota-cell-multi-badge {
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    min-width: 15px;
                    height: 15px;
                    padding: 0 4px;
                    margin-right: 5px;
                    border-radius: 99px;
                    background: #EFECE6;
                    border: 1px solid #C8BFA8;
                    color: #262320;
                    font-size: 9.5px;
                    font-weight: 800;
                    vertical-align: middle;
                }
                th.cota-week-hdr-clickable {
                    cursor: pointer !important;
                    transition: filter 0.12s ease;
                }
                th.cota-week-hdr-clickable:hover {
                    filter: brightness(1.06);
                }
                .cota-pp-pill-btn {
                    display: inline-block;
                    margin-top: 3px;
                    padding: 1px 6px;
                    border-radius: 99px;
                    font-size: 9.5px;
                    font-weight: 800;
                    cursor: pointer;
                    border: 1px solid rgba(255,255,255,0.45);
                    background: rgba(38,35,32,0.22);
                    color: #FAF8F5;
                    transition: background 0.12s ease;
                }
                .cota-pp-pill-btn.is-pp {
                    background: #FFE066;
                    color: #262320;
                    border-color: #262320;
                }
                .cota-pp-pill-btn:hover {
                    opacity: 0.9;
                }
                #cota_pagos_cell_popover {
                    position: fixed;
                    z-index: 2147483644;
                    width: 400px;
                    max-width: calc(100vw - 20px);
                    max-height: calc(100vh - 24px);
                    background: #FFFFFF;
                    border: 1px solid #D0C9BD;
                    border-radius: 12px;
                    box-shadow: 0 18px 44px rgba(38, 35, 32, 0.28);
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    color: #262320;
                    display: flex;
                    flex-direction: column;
                    overflow: hidden;
                }
                .cota-pop-hdr {
                    background: #262320;
                    color: #FFFFFF;
                    padding: 10px 14px;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 8px;
                }
                .cota-pop-close {
                    background: rgba(255,255,255,0.14);
                    color: #FFFFFF;
                    border: none;
                    border-radius: 6px;
                    width: 24px;
                    height: 24px;
                    cursor: pointer;
                    font-size: 13px;
                    font-weight: 700;
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                }
                .cota-pop-close:hover {
                    background: rgba(255,255,255,0.28);
                }
                .cota-pop-body {
                    padding: 12px 14px;
                    overflow-y: auto;
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                }
                .cota-btn-new-pago-card {
                    width: 100%;
                    text-align: left;
                    background: #FFF6EE;
                    border: 1.5px dashed #C85A32;
                    border-radius: 9px;
                    padding: 10px 12px;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 10px;
                    transition: background 0.14s ease, transform 0.1s ease;
                }
                .cota-btn-new-pago-card:hover {
                    background: #FDECE0;
                    border-style: solid;
                }
                .cota-pago-item-row {
                    border: 1px solid #E6E0D6;
                    background: #FAF8F5;
                    border-radius: 8px;
                    padding: 8px 10px;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 8px;
                }
                .cota-pago-tipo-badge {
                    display: inline-block;
                    padding: 1px 7px;
                    border-radius: 99px;
                    font-size: 10.5px;
                    font-weight: 700;
                }
                .cota-tipo-adelanto { background: #FDF1EC; color: #C85A32; border: 1px solid #E9BFA9; }
                .cota-tipo-valorizacion { background: #EEF6F0; color: #3D6B4A; border: 1px solid #B7D6BF; }
                .cota-tipo-liquidacion { background: #FEF7EC; color: #9E6B2D; border: 1px solid #E5CBA3; }
                .cota-icon-mini-btn {
                    border: 1px solid #DFD9CE;
                    background: #FFFFFF;
                    border-radius: 5px;
                    padding: 3px 6px;
                    cursor: pointer;
                    font-size: 11px;
                }
                .cota-icon-mini-btn:hover { background: #F0ECE4; }
                .cota-icon-mini-btn.del:hover { background: #FDECEA; border-color: #E5A9A4; }

                .cota-modal-backdrop {
                    position: fixed;
                    inset: 0;
                    z-index: 2147483645;
                    background: rgba(38, 35, 32, 0.45);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 16px;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                }
                .cota-registro-card {
                    width: 440px;
                    max-width: 100%;
                    background: #FFFFFF;
                    border-radius: 12px;
                    border: 1px solid #C8BFA8;
                    box-shadow: 0 24px 56px rgba(38, 35, 32, 0.36);
                    overflow: visible;
                    color: #262320;
                }
                .cota-semana-card {
                    width: 720px;
                    max-width: 100%;
                    max-height: 88vh;
                    background: #FFFFFF;
                    border-radius: 12px;
                    border: 1px solid #C8BFA8;
                    box-shadow: 0 24px 56px rgba(38, 35, 32, 0.36);
                    display: flex;
                    flex-direction: column;
                    overflow: hidden;
                    color: #262320;
                }
                .cota-reg-table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 4px;
                }
                .cota-reg-table th, .cota-reg-table td {
                    border: 1px solid #262320;
                    padding: 8px 10px;
                    font-size: 13px;
                    vertical-align: middle;
                }
                .cota-reg-label-cell {
                    width: 132px;
                    font-weight: 800;
                    color: #262320;
                    background: #FAF8F5;
                    text-align: left;
                }
                .cota-reg-field-cell {
                    position: relative;
                    background: #FFFFFF;
                }
                .cota-dd-trigger {
                    width: 100%;
                    box-sizing: border-box;
                    background: #E8EAED;
                    border: 1.5px solid transparent;
                    border-radius: 99px;
                    padding: 5px 12px;
                    font-size: 13px;
                    font-weight: 600;
                    color: #262320;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 8px;
                    cursor: pointer;
                    text-align: left;
                }
                .cota-dd-trigger.is-open, .cota-dd-trigger:focus {
                    border-color: #1A73E8;
                    background: #FFFFFF;
                    outline: none;
                }
                .cota-dd-menu {
                    position: absolute;
                    left: 0;
                    right: 0;
                    top: calc(100% + 4px);
                    z-index: 2147483647;
                    background: #FFFFFF;
                    border: 1px solid #D0C9BD;
                    border-radius: 10px;
                    box-shadow: 0 12px 30px rgba(38, 35, 32, 0.25);
                    overflow: hidden;
                }
                .cota-dd-search-wrap {
                    display: flex;
                    align-items: center;
                    gap: 7px;
                    padding: 7px 10px;
                    border-bottom: 1px solid #E6E0D6;
                    background: #FFFFFF;
                }
                .cota-dd-search-inp {
                    width: 100%;
                    border: none;
                    outline: none;
                    font-size: 13px;
                    color: #262320;
                    background: transparent;
                }
                .cota-dd-list {
                    max-height: 195px;
                    overflow-y: auto;
                    padding: 8px 10px;
                    display: flex;
                    flex-direction: column;
                    gap: 6px;
                }
                .cota-dd-pill-opt {
                    align-self: flex-start;
                    background: #EAEAEA;
                    color: #262320;
                    border: 1px solid transparent;
                    border-radius: 99px;
                    padding: 4px 12px;
                    font-size: 12.5px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: background 0.12s ease;
                    max-width: 100%;
                    text-align: left;
                }
                .cota-dd-pill-opt:hover {
                    background: #FCEAE2;
                    border-color: #C85A32;
                }
                .cota-dd-pill-opt.selected {
                    background: #C85A32;
                    color: #FFFFFF;
                }
                .cota-reg-input {
                    width: 100%;
                    box-sizing: border-box;
                    border: 1px solid #D0C9BD;
                    border-radius: 6px;
                    padding: 6px 9px;
                    font-size: 13px;
                    font-weight: 600;
                    color: #262320;
                    font-family: inherit;
                }
                .cota-reg-input:focus {
                    outline: none;
                    border-color: #C85A32;
                }
            `;
        }

        function tipoBadgeClass(tipo) {
            const s = String(tipo || '').toLowerCase();
            if (s.indexOf('adelant') >= 0) return 'cota-tipo-adelanto';
            if (s.indexOf('liquid') >= 0) return 'cota-tipo-liquidacion';
            return 'cota-tipo-valorizacion';
        }

        function getCellPaymentsFromTd(cell) {
            if (!cell) return [];
            try {
                const raw = cell.getAttribute('data-cota-payments-json') || '[]';
                const parsed = JSON.parse(raw);
                return Array.isArray(parsed) ? parsed : [];
            } catch (e) {
                return [];
            }
        }

        function getWeekPayments(colField) {
            return allPayments.filter(p => String(p.semana || '').toUpperCase() === String(colField || '').toUpperCase());
        }

        function aggregateByContractor(pagosList) {
            const orden = [];
            const map = {};
            const monSets = {};
            pagosList.forEach(p => {
                const con = (p.contratista || '').trim() || 'Sin contratista asignado';
                const mon = p.moneda || 'Soles';
                const pref = mon === 'Dólares' ? '$ ' : 'S/ ';
                const k = con + '||' + mon;
                monSets[con] = monSets[con] || {};
                monSets[con][mon] = true;
                if (!map[k]) {
                    map[k] = { contratista: con, moneda: mon, pref: pref, monto: 0 };
                    orden.push(k);
                }
                map[k].monto = Math.round((map[k].monto + (Number(p.monto) || 0)) * 100) / 100;
            });
            return orden.map(k => {
                const it = map[k];
                const cntM = Object.keys(monSets[it.contratista] || {}).length;
                return {
                    contratista: cntM > 1 ? (it.contratista + (it.moneda === 'Dólares' ? ' (USD)' : ' (S/)')) : it.contratista,
                    moneda: it.moneda,
                    pref: it.pref,
                    monto: it.monto
                };
            }).filter(it => it.monto > 0);
        }

        function getAllContractorOptions(defaultContra) {
            const seen = {};
            const out = [];
            function addOne(name, tag) {
                const n = String(name || '').trim();
                if (!n) return;
                const low = n.toLowerCase();
                if (seen[low]) return;
                seen[low] = true;
                out.push({ name: n, tag: tag || '' });
            }
            if (defaultContra) addOne(defaultContra, '★');
            contractorsMaster.forEach(c => addOne(c, ''));
            allPayments.forEach(p => addOne(p.contratista, ''));
            return out;
        }

        function closeCellPopover() {
            const el = parentDoc.getElementById('cota_pagos_cell_popover');
            if (el) el.remove();
        }

        function closeRegistroModal() {
            const el = parentDoc.getElementById('cota_pagos_registro_modal');
            if (el) el.remove();
        }

        function closeSemanaModal() {
            const el = parentDoc.getElementById('cota_pagos_semana_modal');
            if (el) el.remove();
        }

        function closeAllPagosPopups() {
            closeRegistroModal();
            closeCellPopover();
            closeSemanaModal();
        }

        function updateCellDomAfterMutation(cell, fsWrap, newPaymentsList) {
            if (!cell) return;
            const pref = cell.getAttribute('data-pref') || 'S/ ';
            const sumVal = Math.round(newPaymentsList.reduce((acc, p) => acc + (Number(p.monto) || 0), 0) * 100) / 100;
            cell.setAttribute('data-cota-payments-json', JSON.stringify(newPaymentsList));
            cell.setAttribute('data-raw-val', String(sumVal));
            const dispTxt = fmtMoney(sumVal, pref, true);
            const badgeHtml = newPaymentsList.length > 1
                ? '<span class="cota-cell-multi-badge">' + newPaymentsList.length + '</span>'
                : '';
            const notaManual = (cell.getAttribute('data-cota-note-manual') || '').trim();
            const lines = newPaymentsList.map(p => (p.contratista || 'Sin contratista') + ' · ' + p.tipo + ' (' + fmtIsoToDisplay(p.fecha) + '): ' + fmtMoney(p.monto, pref, false));
            if (notaManual) lines.push('Nota: ' + notaManual);
            if (lines.length > 0) {
                cell.setAttribute('data-cota-note-text', lines.join('\n'));
                cell.setAttribute('data-cota-note-monto', fmtMoney(sumVal, pref, false));
            } else {
                cell.removeAttribute('data-cota-note-text');
            }
            const corColor = notaManual ? '#C85A32' : '#4A7C59';
            const cornerHtml = (newPaymentsList.length > 0 || notaManual)
                ? '<span style="position:absolute; top:0; right:0; width:0; height:0; border-top:7px solid ' + corColor + '; border-left:7px solid transparent;"></span>'
                : '';
            cell.innerHTML = badgeHtml + dispTxt + cornerHtml;
            recalculateTableDOM(fsWrap);
        }

        function renderPagosTableRowsHtml(pagosList, showPartidaCol) {
            if (!pagosList || pagosList.length === 0) {
                return '<div style="font-size:12px; color:#7A7267; padding:8px 4px;">No hay pagos registrados en esta semana.</div>';
            }
            return pagosList.map(p => {
                const pref = p.pref || (p.moneda === 'Dólares' ? '$' : 'S/ ');
                const partHtml = showPartidaCol
                    ? '<div style="font-size:11px; color:#6E665E; font-weight:600; margin-bottom:2px;">' + escHtml(p.partida || '') + '</div>'
                    : '';
                return `
                    <div class="cota-pago-item-row">
                        <div style="min-width:0; flex:1;">
                            ${partHtml}
                            <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
                                <span style="font-weight:700; font-size:12.5px; color:#262320;">${escHtml(p.contratista || 'Sin contratista')}</span>
                                <span class="cota-pago-tipo-badge ${tipoBadgeClass(p.tipo)}">${escHtml(p.tipo || 'Valorización')}</span>
                            </div>
                            <div style="font-size:11px; color:#6E665E; margin-top:2px;">📅 ${escHtml(fmtIsoToDisplay(p.fecha))}</div>
                        </div>
                        <div style="display:flex; align-items:center; gap:6px;">
                            <span style="font-weight:800; font-size:12.5px; color:#262320; font-variant-numeric:tabular-nums;">${escHtml(fmtMoney(p.monto, pref, false))}</span>
                            <button type="button" class="cota-icon-mini-btn" data-cota-edit-pid="${escHtml(p.id)}" data-cota-r-type="${escHtml(p.row_type || 'contratista')}" data-cota-r-idx="${escHtml(p.row_idx != null ? p.row_idx : 0)}" data-cota-col="${escHtml(p.semana || '')}" title="Editar pago">✏️</button>
                            <button type="button" class="cota-icon-mini-btn del" data-cota-del-pid="${escHtml(p.id)}" data-cota-r-type="${escHtml(p.row_type || 'contratista')}" data-cota-r-idx="${escHtml(p.row_idx != null ? p.row_idx : 0)}" data-cota-col="${escHtml(p.semana || '')}" title="Eliminar pago">🗑️</button>
                        </div>
                    </div>
                `;
            }).join('');
        }

        function openRegistroPagoModal(opts) {
            closeRegistroModal();
            hideTooltip();
            const cell = opts.cell;
            const fsWrap = opts.fsWrap;
            const rType = opts.rowType || 'contratista';
            const rIdx = parseInt(opts.rowIdx || '0', 10);
            const colField = opts.colField || '';
            const partidaLabel = opts.partidaLabel || '';
            const semLabel = colExportLabels[colField] || colLabels[colField] || colField;
            const pref = opts.pref || (cell ? (cell.getAttribute('data-pref') || 'S/ ') : 'S/ ');
            const isEdit = !!opts.editPayment;
            const isReplaceLegacy = !!opts.replaceLegacy;
            const existingP = opts.editPayment || {};
            const defaultContra = opts.defaultContra || (cell ? (cell.getAttribute('data-cota-default-contractor') || '') : '');

            let selContratista = existingP.contratista || '';
            let selTipo = existingP.tipo || '';
            const initFecha = existingP.fecha || todayIso;
            const initMonto = opts.initialMonto != null ? String(opts.initialMonto) : (existingP.monto ? String(existingP.monto) : '');

            const modal = parentDoc.createElement('div');
            modal.id = 'cota_pagos_registro_modal';
            modal.className = 'cota-modal-backdrop';
            modal.innerHTML = `
                <div class="cota-registro-card">
                    <div class="cota-pop-hdr" style="background:#C85A32; border-radius:11px 11px 0 0;">
                        <div>
                            <div style="font-size:15px; font-weight:800;">${isEdit ? 'Editar Registro de Pago' : 'Registro de Pago'}</div>
                            <div style="font-size:11.5px; color:#FAF8F5; opacity:0.95;">${escHtml(partidaLabel)} &nbsp;·&nbsp; ${escHtml(semLabel)}</div>
                        </div>
                        <button type="button" class="cota-pop-close" data-cota-reg-close="1" title="Cerrar">✕</button>
                    </div>
                    <div style="padding:14px 16px;">
                        <table class="cota-reg-table">
                            <tbody>
                                <tr>
                                    <td class="cota-reg-label-cell">Contratista:</td>
                                    <td class="cota-reg-field-cell">
                                        <button type="button" class="cota-dd-trigger" id="cota_reg_contra_btn">
                                            <span id="cota_reg_contra_val" style="color:${selContratista ? '#262320' : '#6E665E'};">${escHtml(selContratista || 'Seleccionar contratista...')}</span>
                                            <span>▾</span>
                                        </button>
                                        <div class="cota-dd-menu" id="cota_reg_contra_menu" style="display:none;">
                                            <div class="cota-dd-search-wrap">
                                                <span>🔍</span>
                                                <input type="text" class="cota-dd-search-inp" id="cota_reg_contra_search" placeholder="Buscar o escribir contratista..." />
                                            </div>
                                            <div class="cota-dd-list" id="cota_reg_contra_list"></div>
                                        </div>
                                    </td>
                                </tr>
                                <tr>
                                    <td class="cota-reg-label-cell">Tipo de Pago:</td>
                                    <td class="cota-reg-field-cell">
                                        <button type="button" class="cota-dd-trigger" id="cota_reg_tipo_btn">
                                            <span id="cota_reg_tipo_val" style="color:${selTipo ? '#262320' : '#6E665E'};">${escHtml(selTipo || 'Seleccionar tipo...')}</span>
                                            <span>▾</span>
                                        </button>
                                        <div class="cota-dd-menu" id="cota_reg_tipo_menu" style="display:none;">
                                            <div class="cota-dd-search-wrap">
                                                <span>🔍</span>
                                                <input type="text" class="cota-dd-search-inp" id="cota_reg_tipo_search" placeholder="Filtrar tipo..." />
                                            </div>
                                            <div class="cota-dd-list" id="cota_reg_tipo_list"></div>
                                        </div>
                                    </td>
                                </tr>
                                <tr>
                                    <td class="cota-reg-label-cell">Fecha:</td>
                                    <td class="cota-reg-field-cell">
                                        <input type="date" class="cota-reg-input" id="cota_reg_fecha_inp" value="${escHtml(initFecha)}" />
                                    </td>
                                </tr>
                                <tr>
                                    <td class="cota-reg-label-cell">Monto (${escHtml(pref.trim())}):</td>
                                    <td class="cota-reg-field-cell">
                                        <input type="number" step="0.01" min="0" class="cota-reg-input" id="cota_reg_monto_inp" value="${escHtml(initMonto)}" placeholder="0.00" style="text-align:right; font-variant-numeric:tabular-nums;" />
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                        <div id="cota_reg_err_msg" style="display:none; margin-top:9px; padding:7px 10px; border-radius:6px; background:#FDECEA; color:#B42318; font-size:12px; font-weight:700;"></div>
                        <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:14px;">
                            <button type="button" data-cota-reg-close="1" style="background:#FAF8F5; color:#262320; border:1px solid #D0C9BD; border-radius:7px; padding:7px 14px; font-size:12.5px; font-weight:700; cursor:pointer;">Cancelar</button>
                            <button type="button" id="cota_reg_save_btn" style="background:#C85A32; color:#FFFFFF; border:none; border-radius:7px; padding:7px 16px; font-size:12.5px; font-weight:800; cursor:pointer;">💾 Guardar Pago</button>
                        </div>
                    </div>
                </div>
            `;

            getOverlayHost().appendChild(modal);

            const contraBtn = modal.querySelector('#cota_reg_contra_btn');
            const contraMenu = modal.querySelector('#cota_reg_contra_menu');
            const contraSearch = modal.querySelector('#cota_reg_contra_search');
            const contraList = modal.querySelector('#cota_reg_contra_list');
            const contraValSpan = modal.querySelector('#cota_reg_contra_val');

            const tipoBtn = modal.querySelector('#cota_reg_tipo_btn');
            const tipoMenu = modal.querySelector('#cota_reg_tipo_menu');
            const tipoSearch = modal.querySelector('#cota_reg_tipo_search');
            const tipoList = modal.querySelector('#cota_reg_tipo_list');
            const tipoValSpan = modal.querySelector('#cota_reg_tipo_val');

            const fechaInp = modal.querySelector('#cota_reg_fecha_inp');
            const montoInp = modal.querySelector('#cota_reg_monto_inp');
            const errBox = modal.querySelector('#cota_reg_err_msg');
            const saveBtn = modal.querySelector('#cota_reg_save_btn');

            function renderContraOptions(q) {
                const ql = String(q || '').trim().toLowerCase();
                const allOpts = getAllContractorOptions(defaultContra);
                const filtered = allOpts.filter(o => !ql || o.name.toLowerCase().indexOf(ql) >= 0);
                let html = filtered.map(o => {
                    const isSel = selContratista && selContratista.toLowerCase() === o.name.toLowerCase();
                    const lbl = (o.tag ? o.tag + ' ' : '') + o.name;
                    return '<button type="button" class="cota-dd-pill-opt' + (isSel ? ' selected' : '') + '" data-pick-contra="' + escHtml(o.name) + '">' + escHtml(lbl) + '</button>';
                }).join('');
                const exactExists = allOpts.some(o => o.name.toLowerCase() === ql);
                if (ql && !exactExists) {
                    const typedRaw = String(q || '').trim();
                    html += '<button type="button" class="cota-dd-pill-opt" style="background:#FFF6EE; border-color:#C85A32; color:#C85A32;" data-pick-contra="' + escHtml(typedRaw) + '">➕ Usar "' + escHtml(typedRaw) + '"</button>';
                }
                if (!html) {
                    html = '<span style="font-size:12px; color:#7A7267;">Escribe un nombre arriba para usarlo.</span>';
                }
                contraList.innerHTML = html;
            }

            function renderTipoOptions(q) {
                const ql = String(q || '').trim().toLowerCase();
                const filtered = paymentTypes.filter(t => !ql || t.toLowerCase().indexOf(ql) >= 0);
                tipoList.innerHTML = filtered.map(t => {
                    const isSel = selTipo === t;
                    return '<button type="button" class="cota-dd-pill-opt' + (isSel ? ' selected' : '') + '" data-pick-tipo="' + escHtml(t) + '">' + escHtml(t) + '</button>';
                }).join('') || '<span style="font-size:12px; color:#7A7267;">Sin coincidencias</span>';
            }

            function toggleMenu(menuEl, btnEl, otherMenuEl, otherBtnEl, searchEl, renderFn) {
                const willOpen = menuEl.style.display === 'none';
                otherMenuEl.style.display = 'none';
                otherBtnEl.classList.remove('is-open');
                if (willOpen) {
                    renderFn(searchEl.value);
                    menuEl.style.display = 'block';
                    btnEl.classList.add('is-open');
                    setTimeout(() => { searchEl.focus(); }, 20);
                } else {
                    menuEl.style.display = 'none';
                    btnEl.classList.remove('is-open');
                }
            }

            contraBtn.addEventListener('click', function(ev) {
                ev.stopPropagation();
                toggleMenu(contraMenu, contraBtn, tipoMenu, tipoBtn, contraSearch, renderContraOptions);
            });
            tipoBtn.addEventListener('click', function(ev) {
                ev.stopPropagation();
                toggleMenu(tipoMenu, tipoBtn, contraMenu, contraBtn, tipoSearch, renderTipoOptions);
            });
            contraSearch.addEventListener('input', function() { renderContraOptions(contraSearch.value); });
            tipoSearch.addEventListener('input', function() { renderTipoOptions(tipoSearch.value); });

            contraList.addEventListener('click', function(ev) {
                const b = ev.target.closest('[data-pick-contra]');
                if (!b) return;
                selContratista = b.getAttribute('data-pick-contra') || '';
                contraValSpan.textContent = selContratista;
                contraValSpan.style.color = '#262320';
                contraMenu.style.display = 'none';
                contraBtn.classList.remove('is-open');
                errBox.style.display = 'none';
            });

            tipoList.addEventListener('click', function(ev) {
                const b = ev.target.closest('[data-pick-tipo]');
                if (!b) return;
                selTipo = b.getAttribute('data-pick-tipo') || '';
                tipoValSpan.textContent = selTipo;
                tipoValSpan.style.color = '#262320';
                tipoMenu.style.display = 'none';
                tipoBtn.classList.remove('is-open');
                errBox.style.display = 'none';
            });

            modal.addEventListener('click', function(ev) {
                if (ev.target === modal || ev.target.closest('[data-cota-reg-close]')) {
                    closeRegistroModal();
                    return;
                }
                if (!ev.target.closest('.cota-reg-field-cell')) {
                    contraMenu.style.display = 'none';
                    contraBtn.classList.remove('is-open');
                    tipoMenu.style.display = 'none';
                    tipoBtn.classList.remove('is-open');
                }
            });

            function submitPago() {
                const fechaVal = (fechaInp.value || '').trim() || todayIso;
                const montoNum = Math.round((parseFloat(montoInp.value) || 0) * 100) / 100;
                if (!selContratista.trim()) {
                    errBox.textContent = '⚠️ Selecciona un contratista antes de guardar.';
                    errBox.style.display = 'block';
                    return;
                }
                if (!selTipo.trim()) {
                    errBox.textContent = '⚠️ Selecciona el tipo de pago (Adelanto, Valorización o Liquidación).';
                    errBox.style.display = 'block';
                    return;
                }
                if (montoNum <= 0) {
                    errBox.textContent = '⚠️ Ingresa un monto mayor a 0.';
                    errBox.style.display = 'block';
                    montoInp.focus();
                    return;
                }

                const newEntry = {
                    id: isEdit ? existingP.id : ('pg_' + Date.now() + '_' + Math.random().toString(16).slice(2, 6)),
                    contratista: selContratista.trim(),
                    tipo: selTipo.trim(),
                    fecha: fechaVal,
                    monto: montoNum,
                    nota: ''
                };

                if (cell) {
                    const curList = getCellPaymentsFromTd(cell);
                    let nextList;
                    if (isEdit) {
                        nextList = curList.map(p => (p.id === existingP.id ? newEntry : p));
                    } else if (isReplaceLegacy) {
                        nextList = [newEntry];
                    } else {
                        nextList = curList.concat([newEntry]);
                    }
                    updateCellDomAfterMutation(cell, fsWrap, nextList);
                }

                const monStr = pref.indexOf('$') >= 0 ? 'Dólares' : 'Soles';
                const flatEntry = Object.assign({
                    row_type: rType,
                    row_idx: rIdx,
                    partida: partidaLabel,
                    semana: colField,
                    moneda: monStr,
                    pref: pref
                }, newEntry);
                if (isEdit) {
                    allPayments = allPayments.map(p => (p.id === existingP.id ? flatEntry : p));
                } else {
                    allPayments.push(flatEntry);
                }

                const actionName = isEdit ? 'edit_payment' : (isReplaceLegacy ? 'replace_legacy_with_payment' : 'add_payment');
                const bridgeMsg = {
                    action: actionName,
                    row_type: rType,
                    row_idx: rIdx,
                    field: colField,
                    contratista: newEntry.contratista,
                    tipo: newEntry.tipo,
                    fecha: newEntry.fecha,
                    monto: newEntry.monto
                };
                if (isEdit) bridgeMsg.payment_id = existingP.id;

                closeAllPagosPopups();
                sendBridgePayload(bridgeMsg);
            }

            saveBtn.addEventListener('click', submitPago);
            montoInp.addEventListener('keydown', function(ke) {
                if (ke.key === 'Enter') {
                    ke.preventDefault();
                    submitPago();
                }
            });
        }

        function buildWeekSummaryInnerHtml(colField) {
            const semLabel = colExportLabels[colField] || colLabels[colField] || colField;
            const wkPagos = getWeekPayments(colField);
            const wkResumen = aggregateByContractor(wkPagos);

            let resHtml = '';
            if (wkResumen.length > 0) {
                resHtml = '<table style="width:100%; border-collapse:collapse; font-size:12px; margin-top:4px;">' +
                    '<thead><tr style="background:#EFECE6; color:#262320;">' +
                    '<th style="padding:5px 8px; text-align:left; border:1px solid #D0C9BD;">Contratista</th>' +
                    '<th style="padding:5px 8px; text-align:right; border:1px solid #D0C9BD;">Monto</th>' +
                    '</tr></thead><tbody>' +
                    wkResumen.map(it => (
                        '<tr><td style="padding:5px 8px; border:1px solid #E6E0D6; font-weight:600;">' + escHtml(it.contratista) + '</td>' +
                        '<td style="padding:5px 8px; border:1px solid #E6E0D6; text-align:right; font-weight:700; font-variant-numeric:tabular-nums;">' + escHtml(fmtMoney(it.monto, it.pref, false)) + '</td></tr>'
                    )).join('') +
                    '</tbody></table>';
            } else {
                resHtml = '<div style="font-size:12px; color:#7A7267; padding:4px 0;">Sin pagos registrados para contratistas en ' + escHtml(semLabel) + '.</div>';
            }

            return { semLabel, wkPagos, wkResumen, resHtml };
        }

        function openCellPopover(cell, fsWrap) {
            closeCellPopover();
            hideTooltip();

            const rType = cell.getAttribute('data-row-type') || 'contratista';
            const rIdx = parseInt(cell.getAttribute('data-row-idx') || '0', 10);
            const colField = cell.getAttribute('data-col-field') || '';
            const partidaLabel = cell.getAttribute('data-cota-note-partida') || '';
            const semShort = colLabels[colField] || cell.getAttribute('data-cota-note-semana') || colField;
            const semLabel = colExportLabels[colField] || semShort;
            const pref = cell.getAttribute('data-pref') || 'S/ ';
            const rawVal = parseFloat(cell.getAttribute('data-raw-val') || '0') || 0;
            const defaultContra = cell.getAttribute('data-cota-default-contractor') || '';

            const cellPagos = getCellPaymentsFromTd(cell).map(p => Object.assign({
                row_type: rType,
                row_idx: rIdx,
                semana: colField,
                pref: pref
            }, p));
            const sumCell = cellPagos.length > 0
                ? cellPagos.reduce((a, p) => a + (Number(p.monto) || 0), 0)
                : rawVal;

            const wkData = buildWeekSummaryInnerHtml(colField);

            let cellItemsHtml = '';
            if (cellPagos.length > 0) {
                cellItemsHtml = renderPagosTableRowsHtml(cellPagos, false);
            } else if (rawVal > 0.005) {
                cellItemsHtml = `
                    <div class="cota-pago-item-row" style="background:#FFFDF6;">
                        <div>
                            <div style="font-size:12px; font-weight:700; color:#262320;">Monto previo sin desglose</div>
                            <div style="font-size:11px; color:#6E665E;">${escHtml(fmtMoney(rawVal, pref, false))}</div>
                        </div>
                        <div style="display:flex; gap:5px;">
                            <button type="button" class="cota-icon-mini-btn" id="cota_pop_convert_legacy" title="Completar datos (contratista, tipo, fecha)">✏️ Completar</button>
                            <button type="button" class="cota-icon-mini-btn del" id="cota_pop_clear_legacy" title="Limpiar celda">🗑️</button>
                        </div>
                    </div>
                `;
            } else {
                cellItemsHtml = '<div style="font-size:12px; color:#7A7267; padding:2px 2px;">Sin pagos registrados aún en esta celda.</div>';
            }

            const pop = parentDoc.createElement('div');
            pop.id = 'cota_pagos_cell_popover';
            pop.innerHTML = `
                <div class="cota-pop-hdr">
                    <div style="min-width:0;">
                        <div style="font-size:13px; font-weight:800; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${escHtml(partidaLabel)}</div>
                        <div style="font-size:11px; color:#EFECE6; opacity:0.9;">${escHtml(semLabel)} &nbsp;·&nbsp; Total celda: <b>${escHtml(fmtMoney(sumCell, pref, false))}</b></div>
                    </div>
                    <button type="button" class="cota-pop-close" data-cota-pop-close="1" title="Cerrar">✕</button>
                </div>
                <div class="cota-pop-body">
                    <button type="button" class="cota-btn-new-pago-card" id="cota_pop_open_registro_btn">
                        <div>
                            <div style="font-size:13.5px; font-weight:800; color:#C85A32;">➕ Ingresar nuevo pago</div>
                            <div style="font-size:11px; color:#5A534A; margin-top:2px;">Contratista, tipo (Adelanto / Valorización / Liquidación), fecha y monto</div>
                        </div>
                        <span style="font-size:16px; color:#C85A32; font-weight:800;">→</span>
                    </button>

                    <div>
                        <div style="font-size:11px; font-weight:800; color:#6E665E; text-transform:uppercase; letter-spacing:0.4px; margin-bottom:5px;">Pagos en esta celda (${cellPagos.length})</div>
                        <div style="display:flex; flex-direction:column; gap:6px;">${cellItemsHtml}</div>
                    </div>

                    <div style="border-top:1px solid #E6E0D6; padding-top:8px;">
                        <div style="display:flex; align-items:center; justify-content:space-between; gap:6px;">
                            <span style="font-size:11.5px; font-weight:800; color:#262320;">📅 Pagos realizados en ${escHtml(semLabel)} (${wkData.wkPagos.length})</span>
                            <button type="button" id="cota_pop_open_week_btn" style="background:#FAF8F5; border:1px solid #D0C9BD; border-radius:6px; padding:3px 9px; font-size:11px; font-weight:700; color:#262320; cursor:pointer;">Ver semana completa</button>
                        </div>
                        ${wkData.resHtml}
                    </div>
                </div>
            `;

            getOverlayHost().appendChild(pop);

            // Posicionar cerca de la celda sin salirse de pantalla
            const rect = cell.getBoundingClientRect();
            const popW = Math.min(400, parentWin.innerWidth - 20);
            const popH = Math.min(pop.offsetHeight || 380, parentWin.innerHeight - 24);
            let leftPos = rect.left;
            if (leftPos + popW > parentWin.innerWidth - 10) {
                leftPos = Math.max(10, parentWin.innerWidth - popW - 10);
            }
            let topPos = rect.bottom + 6;
            if (topPos + popH > parentWin.innerHeight - 10) {
                topPos = Math.max(10, rect.top - popH - 6);
            }
            pop.style.left = leftPos + 'px';
            pop.style.top = topPos + 'px';

            pop.querySelector('[data-cota-pop-close]').addEventListener('click', closeCellPopover);
            pop.querySelector('#cota_pop_open_registro_btn').addEventListener('click', function() {
                openRegistroPagoModal({
                    cell, fsWrap, rowType: rType, rowIdx: rIdx, colField,
                    partidaLabel, pref, defaultContra
                });
            });
            pop.querySelector('#cota_pop_open_week_btn').addEventListener('click', function() {
                closeCellPopover();
                openSemanaPagosModal(colField, fsWrap);
            });

            const btnConv = pop.querySelector('#cota_pop_convert_legacy');
            if (btnConv) {
                btnConv.addEventListener('click', function() {
                    openRegistroPagoModal({
                        cell, fsWrap, rowType: rType, rowIdx: rIdx, colField,
                        partidaLabel, pref, defaultContra,
                        replaceLegacy: true, initialMonto: rawVal
                    });
                });
            }
            const btnClr = pop.querySelector('#cota_pop_clear_legacy');
            if (btnClr) {
                btnClr.addEventListener('click', function() {
                    updateCellDomAfterMutation(cell, fsWrap, []);
                    closeCellPopover();
                    sendBridgePayload({ action: 'clear_legacy_cell', row_type: rType, row_idx: rIdx, field: colField });
                });
            }

            pop.addEventListener('click', function(ev) {
                handleItemActionButtons(ev, fsWrap, cell);
            });
        }

        function openSemanaPagosModal(colField, fsWrap) {
            closeSemanaModal();
            hideTooltip();

            let activeWeek = colField || (colsPago[0] || 'ADELANTO 1');

            const modal = parentDoc.createElement('div');
            modal.id = 'cota_pagos_semana_modal';
            modal.className = 'cota-modal-backdrop';

            function renderBody() {
                const wkData = buildWeekSummaryInnerHtml(activeWeek);
                const isPp = (payload.colsPorPagar || []).indexOf(activeWeek) >= 0;
                const pillsHtml = colsPago.map(c => {
                    const actCls = c === activeWeek ? 'background:#C85A32; color:#FFFFFF; border-color:#C85A32;' : 'background:#FAF8F5; color:#262320; border-color:#D0C9BD;';
                    const cShort = colLabels[c] || c;
                    return '<button type="button" data-cota-switch-wk="' + escHtml(c) + '" style="border:1px solid; border-radius:99px; padding:4px 10px; font-size:11.5px; font-weight:700; cursor:pointer; ' + actCls + '">' + escHtml(cShort) + '</button>';
                }).join('');

                modal.innerHTML = `
                    <div class="cota-semana-card">
                        <div class="cota-pop-hdr" style="background:#C85A32;">
                            <div>
                                <div style="font-size:15px; font-weight:800;">📅 Pagos realizados — ${escHtml(wkData.semLabel)}</div>
                                <div style="font-size:11.5px; color:#FAF8F5;">Detalle por partida y resumen por contratista (a quién pagar)</div>
                            </div>
                            <button type="button" class="cota-pop-close" data-cota-wk-close="1" title="Cerrar">✕</button>
                        </div>
                        <div style="padding:12px 16px; overflow-y:auto; display:flex; flex-direction:column; gap:12px;">
                            <div style="display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:8px;">
                                <div style="display:flex; flex-wrap:wrap; gap:6px;">${pillsHtml}</div>
                                <button type="button" data-cota-wk-toggle-pp="${escHtml(activeWeek)}" style="background:${isPp ? '#FFE066' : '#FAF8F5'}; color:#262320; border:1px solid #D0C9BD; border-radius:6px; padding:5px 10px; font-size:11.5px; font-weight:700; cursor:pointer;">
                                    ${isPp ? '⏳ Por Pagar (clic para marcar Pagado)' : '🔴 Pagado (clic para marcar Por Pagar)'}
                                </button>
                            </div>
                            <div style="display:grid; grid-template-columns:1.35fr 1fr; gap:12px;">
                                <div style="border:1px solid #DFD9CE; border-radius:8px; padding:10px; background:#FFFFFF;">
                                    <div style="font-size:12px; font-weight:800; color:#262320; margin-bottom:6px;">📋 Pagos realizados (${wkData.wkPagos.length})</div>
                                    <div style="display:flex; flex-direction:column; gap:6px;">${renderPagosTableRowsHtml(wkData.wkPagos, true)}</div>
                                </div>
                                <div style="border:1px solid #DFD9CE; border-radius:8px; padding:10px; background:#FAF8F5;">
                                    <div style="font-size:12px; font-weight:800; color:#262320; margin-bottom:4px;">💸 A quién hacer los pagos</div>
                                    <div style="font-size:11px; color:#6E665E; margin-bottom:6px;">Solo contratista y monto (incluido al exportar)</div>
                                    ${wkData.resHtml}
                                </div>
                            </div>
                            <div style="display:flex; justify-content:flex-end; gap:8px;">
                                <button type="button" data-cota-wk-pin="${escHtml(activeWeek)}" style="background:#262320; color:#FFFFFF; border:none; border-radius:7px; padding:7px 14px; font-size:12px; font-weight:700; cursor:pointer;">📌 Seleccionar ${escHtml(wkData.semLabel)} y Cerrar</button>
                            </div>
                        </div>
                    </div>
                `;
            }

            renderBody();
            getOverlayHost().appendChild(modal);

            modal.addEventListener('click', function(ev) {
                if (ev.target === modal || ev.target.closest('[data-cota-wk-close]')) {
                    closeSemanaModal();
                    return;
                }
                const sw = ev.target.closest('[data-cota-switch-wk]');
                if (sw) {
                    activeWeek = sw.getAttribute('data-cota-switch-wk') || activeWeek;
                    renderBody();
                    return;
                }
                const pinBtn = ev.target.closest('[data-cota-wk-pin]');
                if (pinBtn) {
                    const wk = pinBtn.getAttribute('data-cota-wk-pin') || activeWeek;
                    closeSemanaModal();
                    sendBridgePayload({ action: 'select_week', col: wk });
                    return;
                }
                const tPp = ev.target.closest('[data-cota-wk-toggle-pp]');
                if (tPp) {
                    const wk = tPp.getAttribute('data-cota-wk-toggle-pp') || activeWeek;
                    closeSemanaModal();
                    sendBridgePayload({ action: 'toggle_por_pagar', col: wk });
                    return;
                }
                handleItemActionButtons(ev, fsWrap, null);
            });
        }

        function findCellDom(fsWrap, rType, rIdx, colField) {
            if (!fsWrap) return null;
            return fsWrap.querySelector(
                'td.cota-editable-cell[data-row-type="' + rType + '"][data-row-idx="' + rIdx + '"][data-col-field="' + colField + '"]'
            );
        }

        function handleItemActionButtons(ev, fsWrap, cellHint) {
            const editBtn = ev.target.closest('[data-cota-edit-pid]');
            if (editBtn) {
                const pid = editBtn.getAttribute('data-cota-edit-pid');
                const rType = editBtn.getAttribute('data-cota-r-type') || 'contratista';
                const rIdx = parseInt(editBtn.getAttribute('data-cota-r-idx') || '0', 10);
                const colField = editBtn.getAttribute('data-cota-col') || '';
                const targetCell = cellHint || findCellDom(fsWrap, rType, rIdx, colField);
                const pagosList = targetCell ? getCellPaymentsFromTd(targetCell) : allPayments.filter(p => p.row_type === rType && Number(p.row_idx) === rIdx && p.semana === colField);
                const foundP = pagosList.find(p => p.id === pid) || allPayments.find(p => p.id === pid);
                if (foundP) {
                    closeSemanaModal();
                    openRegistroPagoModal({
                        cell: targetCell,
                        fsWrap,
                        rowType: rType,
                        rowIdx: rIdx,
                        colField,
                        partidaLabel: (targetCell && targetCell.getAttribute('data-cota-note-partida')) || foundP.partida || '',
                        pref: (targetCell && targetCell.getAttribute('data-pref')) || foundP.pref || 'S/ ',
                        defaultContra: targetCell ? (targetCell.getAttribute('data-cota-default-contractor') || '') : '',
                        editPayment: foundP
                    });
                }
                return true;
            }
            const delBtn = ev.target.closest('[data-cota-del-pid]');
            if (delBtn) {
                const pid = delBtn.getAttribute('data-cota-del-pid');
                const rType = delBtn.getAttribute('data-cota-r-type') || 'contratista';
                const rIdx = parseInt(delBtn.getAttribute('data-cota-r-idx') || '0', 10);
                const colField = delBtn.getAttribute('data-cota-col') || '';
                const targetCell = cellHint || findCellDom(fsWrap, rType, rIdx, colField);
                if (targetCell) {
                    const nextList = getCellPaymentsFromTd(targetCell).filter(p => p.id !== pid);
                    updateCellDomAfterMutation(targetCell, fsWrap, nextList);
                }
                allPayments = allPayments.filter(p => p.id !== pid);
                closeAllPagosPopups();
                sendBridgePayload({
                    action: 'delete_payment',
                    row_type: rType,
                    row_idx: rIdx,
                    field: colField,
                    payment_id: pid
                });
                return true;
            }
            return false;
        }

        ensureFloatingStyles();
"""
