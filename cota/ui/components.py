"""
Componentes visuales reutilizables: Header corporativo, tarjetas métricas, badges y fragmentos.
Estética: Warm Architectural Atelier (#F7F4EF, #C85A32, #262320).
"""

import streamlit as st
from cota.utils import get_image_base64


def render_header(title="COTA APP", subtitle="PROJECT & DESIGN MANAGEMENT", logo_path="Logo2.png", is_beta=True):
    """Renderiza el header principal corporativo del estudio."""
    logo_src = get_image_base64(logo_path)
    logo_html = f'<img src="{logo_src}" class="header-logo">' if logo_src else ""
    divider_html = '<div class="header-divider"></div>' if logo_src else ""
    beta_badge = (
        "<span style='font-size: 10px; color: #C85A32; background-color: rgba(200, 90, 50, 0.12); "
        "border: 1px solid rgba(200, 90, 50, 0.35); border-radius: 4px; padding: 2px 7px; margin-left: 8px; "
        "vertical-align: middle; font-family: monospace; font-weight: 600;'>STUDIO v2.0</span>"
        if is_beta else ""
    )
    html = (
        f'<div class="header-container">'
        f'{logo_html}'
        f'{divider_html}'
        f'<div class="header-title-box">'
        f'<h1 class="header-title">{title} {beta_badge}</h1>'
        f'<div class="header-subtitle">{subtitle}</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_metric_card(title, value, subtitle="", border_color=None, text_color=None):
    """Renderiza una tarjeta ejecutiva de métrica con estilo editorial cálido."""
    b_style = f"border-top-color: {border_color} !important;" if border_color else ""
    t_style = f"color: {text_color} !important;" if text_color else ""
    sub_html = f"<small>{subtitle}</small>" if subtitle else ""
    card_html = (
        f"<div class='metric-card' style='{b_style}'>"
        f"<h4>{title}</h4>"
        f"<h2 style='{t_style}'>{value}</h2>"
        f"{sub_html}"
        f"</div>"
    )
    st.markdown(card_html, unsafe_allow_html=True)


def render_status_header(label, color="#C85A32"):
    """Renderiza una cabecera de sección con indicador cromático de estado."""
    html = (
        f"<h4 class='cota-status-header' style='color: {color} !important;'>"
        f"<span class='cota-status-header-bar' style='background-color: {color};'></span>"
        f"{label}"
        f"</h4>"
    )
    st.markdown(html, unsafe_allow_html=True)
