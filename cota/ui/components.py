"""
Componentes visuales reutilizables para COTA APP (tarjetas de métricas, cabeceras, badges y notas).
"""

import html as html_lib
import json
import re
import streamlit as st
import streamlit.components.v1 as components
from cota.utils import get_image_base64


def render_sidebar_branding(logo_path=None, subtitle="PROJECT & DESIGN MANAGEMENT"):
    """Renderiza el logo de COTA en la parte superior izquierda de la barra lateral con subtítulo e indicador de color del Estudio."""
    from cota.utils import obtener_marca_estudio

    marca = obtener_marca_estudio()
    cota_logo_src = get_image_base64(logo_path or "logo/Logo Full.png")
    studio_nom = marca.get("studio_name", "")
    brand_col = marca.get("brand_color", "#C85A32")

    studio_badge_html = ""
    if studio_nom:
        studio_esc = html_lib.escape(studio_nom)
        studio_badge_html = (
            f"<div style='margin-top:6px; display:inline-flex; align-items:center; gap:6px; "
            f"font-size:10.5px; font-weight:700; color:#262320; background:rgba(255,255,255,0.65); "
            f"padding:2px 8px; border-radius:10px; border:1px solid #DFD9CE;'>"
            f"<span style='width:8px; height:8px; border-radius:50%; background:{brand_col}; display:inline-block;'></span>"
            f"<span>{studio_esc}</span>"
            f"</div>"
        )

    st.markdown(
        f"""
        <div style='margin-bottom: 14px; padding-bottom: 12px; border-bottom: 1px solid #DFD9CE; text-align: center;'>
            <div style='display:flex; justify-content:center; align-items:center; margin-bottom:6px;'>
                <img src='{cota_logo_src}' alt='COTA' style='width: 155px; max-width: 82%; height: auto; object-fit: contain; mix-blend-mode: multiply;' />
            </div>
            <div style='font-family: "JetBrains Mono", monospace; font-size: 9px; font-weight: 700; color: #6E665E; letter-spacing: 0.14em; text-transform: uppercase;'>
                {subtitle}
            </div>
            {studio_badge_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_configurador_marca_estudio():
    """Renderiza en la barra lateral un panel desplegable para personalizar color, nombre y logo del Estudio (Branch)."""
    from cota.config import DEFAULT_BRAND_COLOR
    from cota.utils import guardar_marca_estudio, obtener_marca_estudio

    marca = obtener_marca_estudio()
    with st.expander("🎨 Marca y Logo del Estudio", expanded=False):
        st.caption(
            "Personaliza el nombre, el color representativo del Estudio y el logo para los archivos exportados (Excel / PDF)."
        )
        nom_actual = marca.get("studio_name", "")
        color_actual = marca.get("brand_color", DEFAULT_BRAND_COLOR)

        nuevo_nom = st.text_input(
            "Nombre del Estudio",
            value=nom_actual,
            placeholder="",
            key="cfg_studio_name_input",
        )

        color_elegido = st.color_picker(
            "Color del Estudio",
            value=color_actual,
            key="cfg_brand_color_picker",
        )

        logo_up = st.file_uploader(
            "Importar Logo del Estudio (PNG / JPG / SVG)",
            type=["png", "jpg", "jpeg", "svg"],
            key="cfg_brand_logo_uploader",
            help="Este logo se incrustará en las exportaciones de Presupuesto, Control de Pagos y Actas.",
        )

        c_b1, c_b2 = st.columns(2)
        if c_b1.button("💾 Guardar", key="btn_save_studio_brand", type="primary", use_container_width=True):
            up_bytes = logo_up.getvalue() if logo_up is not None else None
            up_name = logo_up.name if logo_up is not None else None
            guardar_marca_estudio(
                studio_name=nuevo_nom,
                brand_color=color_elegido,
                uploaded_logo_bytes=up_bytes,
                uploaded_logo_name=up_name,
            )
            st.toast("✅ Marca y logo del estudio actualizados.", icon="🎨")
            st.rerun()

        if c_b2.button("↺ Restaurar", key="btn_reset_studio_brand", use_container_width=True):
            guardar_marca_estudio(
                studio_name="",
                brand_color=DEFAULT_BRAND_COLOR,
                reset_logo=True,
            )
            st.toast("Marca restaurada a valores originales de COTA.", icon="↺")
            st.rerun()


def render_header(app_title, app_subtitle, logo_path=None, studio_name=""):
    """Renderiza el encabezado principal con el logo de COTA a todo lo alto a la izquierda y el nombre del Studio a la derecha."""
    from cota.utils import obtener_marca_estudio

    marca = obtener_marca_estudio()
    logo_src = get_image_base64(logo_path or "logo/Logo Full.png")
    img_html = f'<img src="{logo_src}" class="header-logo" alt="COTA Logo" />'

    raw_studio = str(studio_name or marca.get("studio_name", "") or "").strip()
    clean_title = str(app_title or "").strip()
    if not raw_studio and "//" in clean_title:
        raw_studio = clean_title.split("//", 1)[1].strip()

    if raw_studio:
        studio_esc = html_lib.escape(raw_studio)
        right_block_html = f"""
        <div class="header-divider"></div>
        <div class="header-title-box">
            <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                <span class="header-title">{studio_esc}</span>
            </div>
        </div>
        """
    else:
        right_block_html = ""

    st.markdown(
        f"""
        <div class="header-container">
            {img_html}
            {right_block_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(title, value, subtitle="", accent_color=None):
    """Renderiza una tarjeta de métrica con estética arquitectónica cálida y altura uniforme."""
    border_style = f"border-top: 3px solid {accent_color};" if accent_color else ""
    st.markdown(
        f"""
        <div class="metric-card" style="{border_style}">
            <div class="metric-label" title="{title}">{title}</div>
            <div class="metric-value" title="{value}">{value}</div>
            <div class="metric-sub" title="{subtitle}">{subtitle if subtitle else '&nbsp;'}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_grid(cards):
    """
    Renderiza una fila de tarjetas KPI perfectamente alineadas y con el mismo alto/ancho.
    cards: lista de dicts con llaves {'title', 'value', 'subtitle', 'accent_color'(opcional)}
    """
    if not cards:
        return
    items_html = []
    for c in cards:
        t = c.get("title", "")
        v = c.get("value", "")
        s = c.get("subtitle", "") or "&nbsp;"
        acc = c.get("accent_color")
        b_style = f' style="border-top: 3px solid {acc};"' if acc else ""
        items_html.append(
            f'<div class="metric-card"{b_style}>'
            f'<div class="metric-label" title="{t}">{t}</div>'
            f'<div class="metric-value" title="{v}">{v}</div>'
            f'<div class="metric-sub">{s}</div>'
            f'</div>'
        )
    grid_html = f'<div class="cota-kpi-grid">{"".join(items_html)}</div>'
    st.markdown(grid_html, unsafe_allow_html=True)


def render_section_header(icon, title):
    """Renderiza un separador de sección estilizado."""
    st.markdown(
        f"""
        <div class="cota-section-header">
            <span>{icon}</span> {title}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_notas_proyecto(proy_name, key_suffix, guardar_fn):
    """
    Renderiza el módulo de Notas del Proyecto estilo Chat interactivo:
    - Cada mensaje tiene un menú de 3 puntitos (⋮) con las opciones: Responder, Editar, Borrar.
    - Responder cita el mensaje original sobre el cuadro de texto y dentro de la burbuja enviada.
    - Editar permite modificar el texto del mensaje directamente en línea.
    - Borrar elimina únicamente ese mensaje desde el menú de 3 puntitos.
    - Soporta envío instantáneo (optimistic UI) y persistencia compatible con Notas en la base de datos.
    """
    from cota.state import (
        agregar_nota_chat_proyecto,
        editar_nota_chat_proyecto,
        eliminar_nota_chat_proyecto,
        obtener_notas_chat_proyecto,
    )

    safe_id = re.sub(r"[^a-zA-Z0-9_]", "_", f"{proy_name}_{key_suffix}")
    bridge_key = f"_cota_chat_bridge_{safe_id}"
    bridge_label = f"COTA_CHAT_BRIDGE_{safe_id}"

    socios_disp = st.session_state.get("lista_socios", ["Socio 1", "Socio 2"])
    if not socios_disp:
        socios_disp = ["Socio 1"]

    def _on_chat_bridge():
        raw_payload = st.session_state.get(bridge_key, "")
        if not raw_payload:
            return
        try:
            payload = json.loads(raw_payload)
        except Exception:
            return
        if not isinstance(payload, dict):
            return

        action = payload.get("action")
        changed = False
        if action == "send":
            socio = str(payload.get("socio") or socios_disp[0]).strip()
            texto = str(payload.get("texto") or "").strip()
            reply_to = payload.get("reply_to")
            if texto:
                st.session_state["socio_activo"] = socio
                agregar_nota_chat_proyecto(proy_name, socio, texto, reply_to=reply_to)
                changed = True
        elif action == "edit":
            idx = payload.get("idx")
            nuevo_texto = str(payload.get("texto") or "").strip()
            if idx is not None and nuevo_texto:
                changed = editar_nota_chat_proyecto(proy_name, int(idx), nuevo_texto)
        elif action == "delete":
            idx = payload.get("idx")
            if idx is not None:
                changed = eliminar_nota_chat_proyecto(proy_name, int(idx))

        if changed:
            guardar_fn()

    # Ocultar el input puente de Streamlit y definir estilos del chat
    st.markdown(
        f"""
        <style>
        div.st-key-{bridge_key} {{
            position: fixed !important;
            left: -9999px !important;
            top: -9999px !important;
            width: 1px !important;
            height: 1px !important;
            opacity: 0 !important;
            overflow: hidden !important;
            pointer-events: none !important;
            margin: 0 !important;
            padding: 0 !important;
        }}
        .cota-chat-container {{
            background: #FFFFFF;
            border: 1px solid #DFD9CE;
            border-radius: 12px;
            padding: 12px;
            box-shadow: 0 2px 8px rgba(38, 35, 32, 0.04);
        }}
        .cota-chat-messages {{
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-height: 360px;
            overflow-y: auto;
            padding: 2px 4px 8px 2px;
        }}
        .cota-chat-bubble {{
            position: relative;
            background: #FAF8F5;
            border: 1px solid #DFD9CE;
            border-left: 4px solid #C85A32;
            border-radius: 10px;
            padding: 8px 12px 10px 12px;
            transition: background-color 0.2s ease, box-shadow 0.2s ease;
        }}
        .cota-chat-bubble:hover {{
            background: #F7F3EC;
            box-shadow: 0 2px 6px rgba(38, 35, 32, 0.06);
        }}
        .cota-chat-bubble.cota-chat-highlight {{
            background: #FDECE6 !important;
            box-shadow: 0 0 0 2px #C85A32 !important;
        }}
        .cota-chat-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 4px;
            gap: 8px;
        }}
        .cota-chat-author {{
            color: #C85A32;
            font-weight: 700;
            font-size: 12.5px;
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }}
        .cota-chat-meta {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        .cota-chat-time {{
            color: #8C8278;
            font-family: monospace;
            font-size: 11px;
        }}
        .cota-chat-edited {{
            color: #8C8278;
            font-size: 10.5px;
            font-style: italic;
        }}
        .cota-chat-dots-btn {{
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 24px;
            height: 24px;
            border-radius: 6px;
            color: #6E665E;
            font-size: 16px;
            font-weight: 800;
            line-height: 1;
            user-select: none;
            transition: background 0.15s ease, color 0.15s ease;
        }}
        .cota-chat-dots-btn:hover {{
            background: rgba(200, 90, 50, 0.14);
            color: #C85A32;
        }}
        .cota-chat-quote {{
            background: #EFECE6;
            border-left: 3px solid #C85A32;
            border-radius: 6px;
            padding: 5px 9px;
            margin-bottom: 6px;
            cursor: pointer;
            transition: background 0.15s ease;
        }}
        .cota-chat-quote:hover {{
            background: #E6E1D8;
        }}
        .cota-chat-quote-author {{
            color: #C85A32;
            font-weight: 700;
            font-size: 11px;
            margin-bottom: 1px;
        }}
        .cota-chat-quote-text {{
            color: #5A534A;
            font-size: 11.5px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 100%;
        }}
        .cota-chat-text {{
            color: #262320;
            font-size: 13px;
            line-height: 1.48;
            white-space: pre-wrap;
            word-break: break-word;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.text_input(
        bridge_label,
        key=bridge_key,
        label_visibility="collapsed",
        on_change=_on_chat_bridge,
    )

    notas_chat = obtener_notas_chat_proyecto(proy_name)
    soc_act = st.session_state.get("socio_activo", socios_disp[0])
    if soc_act not in socios_disp:
        soc_act = socios_disp[0]

    # Construir burbujas de mensajes
    bubbles_html = []
    for idx_msg, msg in enumerate(notas_chat):
        msg_id_esc = html_lib.escape(str(msg.get("id", f"msg_{idx_msg}")), quote=True)
        socio_esc = html_lib.escape(str(msg.get("socio", "Socio")), quote=True)
        fecha_esc = html_lib.escape(str(msg.get("fecha", "")), quote=True)
        texto_raw = str(msg.get("texto", ""))
        texto_esc = html_lib.escape(texto_raw, quote=True)
        editado_html = (
            "<span class='cota-chat-edited'>(editado)</span>"
            if msg.get("editado")
            else ""
        )

        quote_html = ""
        rep = msg.get("reply_to")
        if isinstance(rep, dict) and str(rep.get("texto", "")).strip():
            rep_id_esc = html_lib.escape(str(rep.get("id", "")), quote=True)
            rep_soc_esc = html_lib.escape(str(rep.get("socio", "Socio")), quote=True)
            rep_txt_esc = html_lib.escape(str(rep.get("texto", "")), quote=True)
            quote_html = (
                f"<div class='cota-chat-quote' data-target-id='{rep_id_esc}' title='Ver mensaje original'>"
                f"<div class='cota-chat-quote-author'>↩️ {rep_soc_esc}</div>"
                f"<div class='cota-chat-quote-text'>{rep_txt_esc}</div>"
                f"</div>"
            )

        bubbles_html.append(
            f"<div class='cota-chat-bubble' data-msg-idx='{idx_msg}' data-msg-id='{msg_id_esc}' "
            f"data-msg-socio='{socio_esc}' data-msg-texto='{texto_esc}'>"
            f"<div class='cota-chat-header'>"
            f"<span class='cota-chat-author'>👤 {socio_esc}</span>"
            f"<span class='cota-chat-meta'>"
            f"{editado_html}"
            f"<span class='cota-chat-time'>{fecha_esc}</span>"
            f"<span class='cota-chat-dots-btn' data-msg-idx='{idx_msg}' title='Opciones del mensaje (Responder, Editar, Borrar)'>⋮</span>"
            f"</span>"
            f"</div>"
            f"{quote_html}"
            f"<div class='cota-chat-text'>{texto_esc}</div>"
            f"</div>"
        )

    empty_html = (
        "<div class='cota-chat-empty' style='color:#8C8278; font-size:12.5px; padding:10px 6px; text-align:center;'>"
        "💬 Aún no hay notas en este proyecto. Escribe el primer mensaje abajo."
        "</div>"
        if not bubbles_html
        else ""
    )

    chat_wrap_html = (
        f"<div id='cota_chat_wrap_{safe_id}' class='cota-chat-container'>"
        f"<div id='cota_chat_list_{safe_id}' class='cota-chat-messages'>"
        f"{''.join(bubbles_html)}{empty_html}"
        f"</div>"
        f"<div id='cota_chat_composer_{safe_id}' style='margin-top:8px; border-top:1px solid #EFECE6; padding-top:10px;'></div>"
        f"</div>"
    )
    st.markdown(chat_wrap_html, unsafe_allow_html=True)

    socios_json = json.dumps(socios_disp, ensure_ascii=False)
    soc_act_json = json.dumps(soc_act, ensure_ascii=False)
    bridge_label_json = json.dumps(bridge_label)
    safe_id_json = json.dumps(safe_id)

    js_controller = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="margin:0;padding:0;overflow:hidden;background:transparent;">
    <script>
    (function() {{
        const parentDoc = window.parent.document;
        const parentWin = window.parent;
        const safeId = {safe_id_json};
        const bridgeLabel = {bridge_label_json};
        const sociosList = {socios_json};
        const defaultSocio = {soc_act_json};

        if (!parentWin.__cotaChatSocio) {{
            parentWin.__cotaChatSocio = defaultSocio;
        }}

        function sendBridgePayload(payloadObj) {{
            try {{
                payloadObj.ts = Date.now() + Math.floor(Math.random() * 1000);
                const payloadStr = JSON.stringify(payloadObj);
                const inputEl = parentDoc.querySelector('input[aria-label=' + JSON.stringify(bridgeLabel) + ']');
                if (!inputEl) return false;
                const proto = parentWin.HTMLInputElement.prototype;
                const nativeSetter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
                if (nativeSetter) {{
                    nativeSetter.call(inputEl, payloadStr);
                }} else {{
                    inputEl.value = payloadStr;
                }}
                const tracker = inputEl._valueTracker;
                if (tracker) {{
                    tracker.setValue('');
                }}
                inputEl.dispatchEvent(new Event('input', {{ bubbles: true }}));
                inputEl.dispatchEvent(new Event('change', {{ bubbles: true }}));
                inputEl.focus({{ preventScroll: true }});
                inputEl.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }}));
                inputEl.blur();
                return true;
            }} catch (err) {{
                console.error('Error en puente de chat:', err);
                return false;
            }}
        }}

        // Crear o recuperar menú flotante de 3 puntitos en parentDoc.body
        const MENU_ID = 'cota-chat-floating-menu';
        function getFloatingMenu() {{
            let menu = parentDoc.getElementById(MENU_ID);
            if (!menu) {{
                menu = parentDoc.createElement('div');
                menu.id = MENU_ID;
                menu.style.cssText = [
                    'position: fixed',
                    'z-index: 2147483647',
                    'display: none',
                    'background: #FFFFFF',
                    'border: 1px solid #DFD9CE',
                    'border-radius: 9px',
                    'box-shadow: 0 8px 24px rgba(38, 35, 32, 0.16)',
                    'padding: 4px',
                    'min-width: 155px',
                    'font-family: "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, sans-serif',
                    'user-select: none'
                ].join(';');
                parentDoc.body.appendChild(menu);

                parentDoc.addEventListener('click', function(ev) {{
                    if (menu.style.display !== 'none' && !menu.contains(ev.target) && !ev.target.closest('.cota-chat-dots-btn')) {{
                        menu.style.display = 'none';
                    }}
                }}, true);
            }}
            return menu;
        }}

        function escapeHtml(str) {{
            return String(str || '')
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }}

        function initChatWidget() {{
            const wrap = parentDoc.getElementById('cota_chat_wrap_' + safeId);
            const listEl = parentDoc.getElementById('cota_chat_list_' + safeId);
            const compEl = parentDoc.getElementById('cota_chat_composer_' + safeId);
            if (!wrap || !listEl || !compEl) return false;

            // Auto-scroll al final de la conversación
            listEl.scrollTop = listEl.scrollHeight;

            let activeReply = null;

            // Construir el compositor de chat si aún no está montado
            if (!compEl.dataset.cotaMounted) {{
                compEl.dataset.cotaMounted = '1';
                const currentSocio = sociosList.includes(parentWin.__cotaChatSocio) ? parentWin.__cotaChatSocio : defaultSocio;
                const optionsHtml = sociosList.map(s =>
                    '<option value="' + escapeHtml(s) + '"' + (s === currentSocio ? ' selected' : '') + '>' + escapeHtml(s) + '</option>'
                ).join('');

                compEl.innerHTML = [
                    '<div class="cota-reply-banner" style="display:none; background:#F0ECE1; border-left:3px solid #C85A32; border-radius:7px; padding:6px 10px; margin-bottom:8px; align-items:center; justify-content:space-between; gap:8px;">',
                        '<div style="overflow:hidden; flex:1;">',
                            '<div class="cota-reply-banner-author" style="color:#C85A32; font-weight:700; font-size:11.5px;"></div>',
                            '<div class="cota-reply-banner-text" style="color:#5A534A; font-size:12px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;"></div>',
                        '</div>',
                        '<span class="cota-reply-cancel" title="Cancelar respuesta" style="cursor:pointer; color:#6E665E; font-weight:800; font-size:14px; padding:2px 6px; border-radius:4px;">✕</span>',
                    '</div>',
                    '<div style="display:flex; gap:8px; align-items:flex-end; flex-wrap:wrap;">',
                        '<div style="flex:0 0 140px;">',
                            '<label style="display:block; font-size:11px; font-weight:600; color:#6E665E; margin-bottom:3px;">Socio:</label>',
                            '<select class="cota-chat-socio-sel" style="width:100%; height:38px; border:1px solid #DFD9CE; border-radius:8px; background:#FAF8F5; color:#262320; font-size:13px; font-weight:600; padding:0 8px; outline:none; cursor:pointer;">',
                                optionsHtml,
                            '</select>',
                        '</div>',
                        '<div style="flex:1 1 220px; position:relative;">',
                            '<label style="display:block; font-size:11px; font-weight:600; color:#6E665E; margin-bottom:3px;">Mensaje / Nota:</label>',
                            '<textarea class="cota-chat-input" rows="2" placeholder="Escribe un mensaje... (Enter para enviar, Shift+Enter nueva línea)" style="width:100%; box-sizing:border-box; border:1px solid #DFD9CE; border-radius:8px; background:#FAF8F5; color:#262320; font-family:inherit; font-size:13px; padding:8px 10px; resize:vertical; min-height:38px; max-height:110px; outline:none; line-height:1.4;"></textarea>',
                        '</div>',
                        '<button type="button" class="cota-chat-send-btn" style="height:38px; background:#C85A32; color:#FFFFFF; border:none; border-radius:8px; padding:0 16px; font-weight:700; font-size:12.5px; cursor:pointer; display:inline-flex; align-items:center; gap:6px; box-shadow:0 2px 5px rgba(200,90,50,0.25); transition:background 0.15s ease;">',
                            '<span>💬 ENVIAR</span>',
                        '</button>',
                    '</div>'
                ].join('');

                const selSocio = compEl.querySelector('.cota-chat-socio-sel');
                const txtInput = compEl.querySelector('.cota-chat-input');
                const btnSend = compEl.querySelector('.cota-chat-send-btn');
                const replyBanner = compEl.querySelector('.cota-reply-banner');
                const replyAuthor = compEl.querySelector('.cota-reply-banner-author');
                const replyText = compEl.querySelector('.cota-reply-banner-text');
                const replyCancel = compEl.querySelector('.cota-reply-cancel');

                selSocio.addEventListener('change', function() {{
                    parentWin.__cotaChatSocio = selSocio.value;
                }});

                txtInput.addEventListener('focus', function() {{
                    txtInput.style.borderColor = '#C85A32';
                    txtInput.style.background = '#FFFFFF';
                }});
                txtInput.addEventListener('blur', function() {{
                    txtInput.style.borderColor = '#DFD9CE';
                    txtInput.style.background = '#FAF8F5';
                }});

                function clearReply() {{
                    activeReply = null;
                    replyBanner.style.display = 'none';
                }}

                replyCancel.addEventListener('click', clearReply);

                compEl._setReply = function(msgObj) {{
                    activeReply = msgObj;
                    replyAuthor.textContent = '↩️ Respondiendo a ' + msgObj.socio;
                    replyText.textContent = msgObj.texto;
                    replyBanner.style.display = 'flex';
                    txtInput.focus();
                }};

                function triggerSend() {{
                    const rawText = (txtInput.value || '').trim();
                    if (!rawText) return;
                    const chosenSocio = selSocio.value || defaultSocio;
                    parentWin.__cotaChatSocio = chosenSocio;

                    // Agregar burbuja de forma optimista en el DOM (0ms)
                    const emptyMsg = listEl.querySelector('.cota-chat-empty');
                    if (emptyMsg) emptyMsg.remove();

                    const now = new Date();
                    const pad = n => String(n).padStart(2, '0');
                    const fechaStr = pad(now.getDate()) + '/' + pad(now.getMonth() + 1) + '/' + now.getFullYear() + ' ' + pad(now.getHours()) + ':' + pad(now.getMinutes());
                    const newIdx = listEl.querySelectorAll('.cota-chat-bubble').length;
                    const tempId = 'msg_' + Date.now();

                    let quoteBlock = '';
                    let replyPayload = null;
                    if (activeReply) {{
                        replyPayload = {{
                            id: activeReply.id,
                            socio: activeReply.socio,
                            texto: activeReply.texto
                        }};
                        quoteBlock = '<div class="cota-chat-quote" data-target-id="' + escapeHtml(activeReply.id) + '">' +
                            '<div class="cota-chat-quote-author">↩️ ' + escapeHtml(activeReply.socio) + '</div>' +
                            '<div class="cota-chat-quote-text">' + escapeHtml(activeReply.texto) + '</div>' +
                        '</div>';
                    }}

                    const bubble = parentDoc.createElement('div');
                    bubble.className = 'cota-chat-bubble';
                    bubble.setAttribute('data-msg-idx', String(newIdx));
                    bubble.setAttribute('data-msg-id', tempId);
                    bubble.setAttribute('data-msg-socio', chosenSocio);
                    bubble.setAttribute('data-msg-texto', rawText);
                    bubble.innerHTML = [
                        '<div class="cota-chat-header">',
                            '<span class="cota-chat-author">👤 ' + escapeHtml(chosenSocio) + '</span>',
                            '<span class="cota-chat-meta">',
                                '<span class="cota-chat-time">' + fechaStr + '</span>',
                                '<span class="cota-chat-dots-btn" data-msg-idx="' + newIdx + '" title="Opciones del mensaje">⋮</span>',
                            '</span>',
                        '</div>',
                        quoteBlock,
                        '<div class="cota-chat-text">' + escapeHtml(rawText) + '</div>'
                    ].join('');
                    listEl.appendChild(bubble);
                    listEl.scrollTop = listEl.scrollHeight;

                    txtInput.value = '';
                    clearReply();

                    sendBridgePayload({{
                        action: 'send',
                        socio: chosenSocio,
                        texto: rawText,
                        reply_to: replyPayload
                    }});
                }}

                btnSend.addEventListener('click', triggerSend);
                txtInput.addEventListener('keydown', function(ke) {{
                    if (ke.key === 'Enter' && !ke.shiftKey) {{
                        ke.preventDefault();
                        triggerSend();
                    }} else if (ke.key === 'Escape' && activeReply) {{
                        clearReply();
                    }}
                }});
            }}

            // Edición en línea de una burbuja de mensaje
            function startInlineEdit(bubble) {{
                if (!bubble || bubble.classList.contains('cota-editing')) return;
                const textEl = bubble.querySelector('.cota-chat-text');
                if (!textEl) return;
                const idx = parseInt(bubble.getAttribute('data-msg-idx') || '0', 10);
                const curText = bubble.getAttribute('data-msg-texto') || textEl.textContent || '';
                bubble.classList.add('cota-editing');

                const editWrap = parentDoc.createElement('div');
                editWrap.style.cssText = 'margin-top:4px; display:flex; flex-direction:column; gap:6px;';
                editWrap.innerHTML = [
                    '<textarea class="cota-inline-edit-area" rows="2" style="width:100%; box-sizing:border-box; border:1.5px solid #C85A32; border-radius:7px; padding:6px 8px; font-family:inherit; font-size:13px; color:#262320; background:#FFFFFF; outline:none; resize:vertical;"></textarea>',
                    '<div style="display:flex; justify-content:flex-end; gap:6px;">',
                        '<button type="button" class="cota-edit-cancel" style="background:#EFECE6; color:#4A453F; border:1px solid #DFD9CE; border-radius:6px; padding:4px 10px; font-size:11.5px; font-weight:600; cursor:pointer;">Cancelar (Esc)</button>',
                        '<button type="button" class="cota-edit-save" style="background:#C85A32; color:#FFFFFF; border:none; border-radius:6px; padding:4px 12px; font-size:11.5px; font-weight:700; cursor:pointer;">💾 Guardar (Enter)</button>',
                    '</div>'
                ].join('');

                textEl.style.display = 'none';
                bubble.appendChild(editWrap);

                const area = editWrap.querySelector('.cota-inline-edit-area');
                const btnCancel = editWrap.querySelector('.cota-edit-cancel');
                const btnSave = editWrap.querySelector('.cota-edit-save');
                area.value = curText;
                area.focus();
                area.setSelectionRange(area.value.length, area.value.length);

                function closeEdit() {{
                    bubble.classList.remove('cota-editing');
                    editWrap.remove();
                    textEl.style.display = '';
                }}

                function saveEdit() {{
                    const newTxt = (area.value || '').trim();
                    if (!newTxt || newTxt === curText) {{
                        closeEdit();
                        return;
                    }}
                    bubble.setAttribute('data-msg-texto', newTxt);
                    textEl.textContent = newTxt;
                    const metaEl = bubble.querySelector('.cota-chat-meta');
                    if (metaEl && !metaEl.querySelector('.cota-chat-edited')) {{
                        const edSpan = parentDoc.createElement('span');
                        edSpan.className = 'cota-chat-edited';
                        edSpan.textContent = '(editado)';
                        metaEl.insertBefore(edSpan, metaEl.firstChild);
                    }}
                    closeEdit();
                    sendBridgePayload({{
                        action: 'edit',
                        idx: idx,
                        texto: newTxt
                    }});
                }}

                btnCancel.addEventListener('click', closeEdit);
                btnSave.addEventListener('click', saveEdit);
                area.addEventListener('keydown', function(ke) {{
                    if (ke.key === 'Enter' && !ke.shiftKey) {{
                        ke.preventDefault();
                        saveEdit();
                    }} else if (ke.key === 'Escape') {{
                        ke.preventDefault();
                        closeEdit();
                    }}
                }});
            }}

            // Delegación de eventos en la lista de mensajes (menú de 3 puntos y clic en citas)
            if (!listEl.dataset.cotaEventsBound) {{
                listEl.dataset.cotaEventsBound = '1';

                listEl.addEventListener('click', function(ev) {{
                    const dotsBtn = ev.target.closest('.cota-chat-dots-btn');
                    if (dotsBtn) {{
                        ev.preventDefault();
                        ev.stopPropagation();
                        const bubble = dotsBtn.closest('.cota-chat-bubble');
                        if (!bubble) return;

                        const idx = parseInt(bubble.getAttribute('data-msg-idx') || '0', 10);
                        const msgId = bubble.getAttribute('data-msg-id') || ('msg_' + idx);
                        const socio = bubble.getAttribute('data-msg-socio') || 'Socio';
                        const texto = bubble.getAttribute('data-msg-texto') || '';

                        const menu = getFloatingMenu();
                        const itemStyle = 'display:flex; align-items:center; gap:8px; padding:7px 12px; font-size:12.5px; font-weight:600; color:#262320; border-radius:6px; cursor:pointer; transition:background 0.12s ease;';
                        menu.innerHTML = [
                            '<div class="cota-menu-opt" data-opt="reply" style="' + itemStyle + '"><span>↩️</span><span>Responder</span></div>',
                            '<div class="cota-menu-opt" data-opt="edit" style="' + itemStyle + '"><span>✏️</span><span>Editar</span></div>',
                            '<div style="height:1px; background:#EFECE6; margin:3px 4px;"></div>',
                            '<div class="cota-menu-opt" data-opt="delete" style="' + itemStyle + ' color:#C93B2B;"><span>🗑️</span><span>Borrar</span></div>'
                        ].join('');

                        menu.querySelectorAll('.cota-menu-opt').forEach(optEl => {{
                            const isDel = optEl.getAttribute('data-opt') === 'delete';
                            optEl.addEventListener('mouseenter', () => {{
                                optEl.style.background = isDel ? '#FDF2F2' : '#FAF8F5';
                            }});
                            optEl.addEventListener('mouseleave', () => {{
                                optEl.style.background = 'transparent';
                            }});
                            optEl.addEventListener('click', function(oe) {{
                                oe.preventDefault();
                                oe.stopPropagation();
                                menu.style.display = 'none';
                                const act = optEl.getAttribute('data-opt');
                                if (act === 'reply') {{
                                    if (typeof compEl._setReply === 'function') {{
                                        compEl._setReply({{ id: msgId, idx: idx, socio: socio, texto: texto }});
                                    }}
                                }} else if (act === 'edit') {{
                                    startInlineEdit(bubble);
                                }} else if (act === 'delete') {{
                                    bubble.style.opacity = '0.35';
                                    bubble.remove();
                                    sendBridgePayload({{
                                        action: 'delete',
                                        idx: idx
                                    }});
                                }}
                            }});
                        }});

                        menu.style.display = 'block';
                        const rect = dotsBtn.getBoundingClientRect();
                        const menuRect = menu.getBoundingClientRect();
                        let leftPos = rect.right - menuRect.width;
                        let topPos = rect.bottom + 4;
                        if (leftPos < 8) leftPos = 8;
                        if (topPos + menuRect.height > parentWin.innerHeight - 8) {{
                            topPos = rect.top - menuRect.height - 4;
                        }}
                        menu.style.left = leftPos + 'px';
                        menu.style.top = topPos + 'px';
                        return;
                    }}

                    const quoteEl = ev.target.closest('.cota-chat-quote');
                    if (quoteEl) {{
                        const targetId = quoteEl.getAttribute('data-target-id');
                        if (targetId) {{
                            const targetBubble = listEl.querySelector('.cota-chat-bubble[data-msg-id="' + targetId + '"]');
                            if (targetBubble) {{
                                targetBubble.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                                targetBubble.classList.add('cota-chat-highlight');
                                setTimeout(() => targetBubble.classList.remove('cota-chat-highlight'), 1400);
                            }}
                        }}
                    }}
                }});
            }}

            return true;
        }}

        if (!initChatWidget()) {{
            let tries = 0;
            const t = setInterval(() => {{
                tries++;
                if (initChatWidget() || tries > 25) clearInterval(t);
            }}, 120);
        }}
    }})();
    </script>
    </body>
    </html>
    """
    components.html(js_controller, height=0, scrolling=False)
