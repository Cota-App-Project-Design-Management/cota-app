"""
COTA APP - Sistema de Estilos Visuales (Warm Architectural Atelier)
Paleta: Blanco Hueso (#F7F4EF), Piedra Travertino (#EFECE6), Rojo Arcilla (#C85A32), Carbón Cálido (#262320).
"""


def get_app_css() -> str:
    """Retorna el bloque CSS completo con la identidad cálida para arquitectos y diseñadores."""
    return """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

        :root {
            --bg-bone: #F7F4EF;
            --bg-stone: #EFECE6;
            --bg-card: #FAF8F5;
            --bg-white: #FFFFFF;
            --clay-primary: #C85A32;
            --clay-hover: #A94622;
            --clay-soft: rgba(200, 90, 50, 0.10);
            --clay-border: rgba(200, 90, 50, 0.30);
            --text-charcoal: #262320;
            --text-taupe: #6E665E;
            --text-muted: #9A9187;
            --border-sand: #DFD9CE;
            --status-ok: #4A7C59;
            --status-warn: #D98A2B;
            --status-err: #C93B2B;
        }

        /* 1. FONDOS GENERALES Y TIPOGRAFÍA BASE */
        html, body, [class*="css"], .stApp {
            background-color: var(--bg-bone) !important;
            color: var(--text-charcoal) !important;
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        }

        h1, h2, h3, h4, h5, h6 {
            color: var(--text-charcoal) !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            font-weight: 600 !important;
            letter-spacing: -0.02em;
        }

        p, label, span, div {
            color: var(--text-charcoal);
        }

        /* 2. SIDEBAR (PIEDRA CALIZA CÁLIDA) */
        section[data-testid="stSidebar"] {
            background-color: var(--bg-stone) !important;
            border-right: 1px solid var(--border-sand) !important;
        }

        section[data-testid="stSidebar"] .stMarkdown h2 {
            color: var(--clay-primary) !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            letter-spacing: 0.04em;
            font-weight: 700 !important;
        }

        /* 3. TARJETA DE LOGIN EDITORIAL */
        .login-card {
            background-color: var(--bg-white);
            border: 1px solid var(--border-sand);
            border-top: 4px solid var(--clay-primary);
            border-radius: 12px;
            padding: 36px 32px 28px 32px;
            text-align: center;
            box-shadow: 0 12px 32px rgba(38, 35, 32, 0.06);
            margin-bottom: 18px;
        }

        .login-title {
            color: var(--text-charcoal) !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            font-size: 28px !important;
            font-weight: 700 !important;
            letter-spacing: 0.04em !important;
            margin-bottom: 6px !important;
        }

        .login-subtitle {
            color: var(--clay-primary) !important;
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 11px !important;
            font-weight: 500 !important;
            letter-spacing: 0.16em !important;
            text-transform: uppercase;
            margin-bottom: 18px !important;
        }

        .login-access {
            color: var(--text-taupe) !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            font-size: 12px !important;
            font-weight: 500;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            padding-top: 14px;
            border-top: 1px solid var(--border-sand);
            margin-bottom: 0 !important;
        }

        /* 4. FORMULARIOS E INPUTS */
        div[data-testid="stForm"] {
            background-color: var(--bg-white) !important;
            border: 1px solid var(--border-sand) !important;
            border-radius: 12px !important;
            padding: 24px !important;
            box-shadow: 0 6px 20px rgba(38, 35, 32, 0.04) !important;
        }

        .stTextInput input, .stNumberInput input, .stTextArea textarea, .stDateInput input {
            background-color: var(--bg-bone) !important;
            color: var(--text-charcoal) !important;
            border: 1px solid var(--border-sand) !important;
            border-radius: 8px !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            transition: all 0.2s ease;
        }

        .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
            border-color: var(--clay-primary) !important;
            background-color: var(--bg-white) !important;
            box-shadow: 0 0 0 3px var(--clay-soft) !important;
        }

        div[data-baseweb="select"] > div {
            background-color: var(--bg-bone) !important;
            color: var(--text-charcoal) !important;
            border: 1px solid var(--border-sand) !important;
            border-radius: 8px !important;
        }

        /* 5. BOTONES (ROJO ARCILLA Y SECUNDARIOS PIEDRA) */
        .stButton > button, .stFormSubmitButton > button {
            border-radius: 8px !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            font-weight: 600 !important;
            font-size: 13px !important;
            letter-spacing: 0.03em !important;
            padding: 0.55rem 1.1rem !important;
            transition: all 0.2s ease !important;
            border: 1px solid var(--border-sand) !important;
            background-color: var(--bg-white) !important;
            color: var(--text-charcoal) !important;
        }

        .stButton > button:hover {
            border-color: var(--clay-primary) !important;
            color: var(--clay-primary) !important;
            background-color: var(--bg-card) !important;
        }

        /* Botones Primarios e Ingreso */
        .stButton > button[kind="primary"], .stFormSubmitButton > button {
            background-color: var(--clay-primary) !important;
            color: #FFFFFF !important;
            border: 1px solid var(--clay-primary) !important;
            box-shadow: 0 4px 12px rgba(200, 90, 50, 0.20) !important;
        }

        .stButton > button[kind="primary"] *, .stFormSubmitButton > button * {
            color: #FFFFFF !important;
        }

        .stButton > button[kind="primary"]:hover, .stFormSubmitButton > button:hover {
            background-color: var(--clay-hover) !important;
            border-color: var(--clay-hover) !important;
            box-shadow: 0 6px 16px rgba(169, 70, 34, 0.28) !important;
        }

        /* 6. PESTAÑAS (TABS ARQUITECTÓNICOS) */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: var(--bg-stone);
            padding: 6px;
            border-radius: 10px;
            border: 1px solid var(--border-sand);
        }

        .stTabs [data-baseweb="tab"] {
            height: 38px;
            border-radius: 7px;
            padding: 0 16px;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            font-weight: 500;
            font-size: 13px;
            color: var(--text-taupe) !important;
            background-color: transparent;
            border: none !important;
        }

        .stTabs [aria-selected="true"] {
            background-color: var(--bg-white) !important;
            color: var(--clay-primary) !important;
            font-weight: 600 !important;
            box-shadow: 0 2px 6px rgba(38, 35, 32, 0.08);
        }

        /* 7. MÉTRICAS Y KPIs DE PROYECTO */
        div[data-testid="stMetric"] {
            background-color: var(--bg-white) !important;
            border: 1px solid var(--border-sand) !important;
            border-left: 4px solid var(--clay-primary) !important;
            border-radius: 10px !important;
            padding: 16px 20px !important;
            box-shadow: 0 4px 14px rgba(38, 35, 32, 0.03) !important;
        }

        div[data-testid="stMetricLabel"] p {
            color: var(--text-taupe) !important;
            font-size: 12px !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        div[data-testid="stMetricValue"] div {
            color: var(--text-charcoal) !important;
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 24px !important;
            font-weight: 600 !important;
        }

        /* 8. EXPANDERS, TABLAS Y CONTENEDORES */
        div[data-testid="stExpander"] {
            background-color: var(--bg-white) !important;
            border: 1px solid var(--border-sand) !important;
            border-radius: 10px !important;
            box-shadow: 0 2px 8px rgba(38, 35, 32, 0.02) !important;
        }

        div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] {
            border: 1px solid var(--border-sand) !important;
            border-radius: 10px !important;
            overflow: hidden !important;
            background-color: var(--bg-white) !important;
        }

        hr {
            border-color: var(--border-sand) !important;
        }
    </style>
    """
