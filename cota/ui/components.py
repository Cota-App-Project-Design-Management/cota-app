"""
Componentes visuales reutilizables: Header, tarjetas métricas, badges y fragmentos.
"""

import streamlit as st
from cota.utils import get_image_base64


def render_header(title="COTA APP", subtitle="PROJECT & DESIGN MANAGEMENT", logo_path="Logo2.png", is_beta=True):
    """Renderiza el header principal corporativo."""
    logo_src = get_image_base64(logo_path)
    logo_html = f'<img src="{logo_src}" class="header-logo">' if logo_src else ""
    beta_badge = (
        "<span style='font-size: 11px; color: #FF9800; background-color: rgba(255, 152, 0, 0.15); "
        "border: 1px solid #FF9800; border-radius: 4px; padding: 1px 6px; margin-left: 8px; "
        "vertical-align: middle; font-family: monospace; font-weight: bold;'>BETA</span>"
        if is_beta else ""
    )
    st.markdown(f'''
        <div class="header-container">
            {logo_html}
            <div class="header-divider"></div>
            <div class="header-title-box">
                <h1 class="header-title">{title} {beta_badge}</h1>
                <div class="header-subtitle">{subtitle}</div>
            </div>
        </div>
    ''', unsafe_allow_html=True)


def render_metric_card(title, value, subtitle="", border_color=None, text_color=None):
    """Renderiza una tarjeta métrica con estilo glassmorphism."""
    b_style = f"border-top-color: {border_color} !important;" if border_color else ""
    t_style = f"color: {text_color} !important;" if text_color else ""
    sub_html = f"<small>{subtitle}</small>" if subtitle else ""
    card_html = f"""
    <div class='metric-card' style='{b_style}'>
        <h4>{title}</h4>
        <h2 style='{t_style}'>{value}</h2>
        {sub_html}
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def render_status_header(label, color="#00E5FF"):
    """Renderiza una cabecera de sección con semáforo/color de estado."""
    html = f"""
    <h4 class='cota-status-header' style='color: {color};'>
        <span class='cota-status-header-bar' style='background-color: {color};'></span>
        {label}
    </h4>
    """
    st.markdown(html, unsafe_allow_html=True)
