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
            --card-bg: #FFFFFF;
            --border-color: #DFD9CE;
            --clay-primary: #C85A32;
            --clay-hover: #A94622;
            --clay-soft: rgba(200, 90, 50, 0.10);
            --clay-border: rgba(200, 90, 50, 0.30);
            --text-charcoal: #262320;
            --text-taupe: #6E665E;
            --text-muted: #8C8277;
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

        /* 3. ENCABEZADO CORPORATIVO DEL ESTUDIO */
        .header-container {
            display: flex;
            align-items: center;
            gap: 16px;
            background-color: var(--bg-white);
            border: 1px solid var(--border-sand);
            border-left: 5px solid var(--clay-primary);
            border-radius: 12px;
            padding: 16px 24px;
            margin-bottom: 22px;
            box-shadow: 0 4px 16px rgba(38, 35, 32, 0.04);
        }

        .header-logo {
            max-height: 46px;
            width: auto;
            object-fit: contain;
        }

        .header-divider {
            width: 1px;
            height: 36px;
            background-color: var(--border-sand);
        }

        .header-title-box {
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .header-title {
            font-size: 21px !important;
            font-weight: 700 !important;
            color: var(--text-charcoal) !important;
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1.2 !important;
            letter-spacing: 0.02em !important;
        }

        .header-subtitle {
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 11px !important;
            font-weight: 500 !important;
            color: var(--text-taupe) !important;
            letter-spacing: 0.14em !important;
            text-transform: uppercase;
            margin-top: 3px;
        }

        /* 4. TARJETA DE LOGIN EDITORIAL */
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

        /* 5. TARJETAS DE MÉTRICAS Y KPIs (.metric-card, .cota-kpi-grid y stMetric) */
        .cota-kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 14px;
            width: 100%;
            align-items: stretch;
            margin-bottom: 12px;
        }

        .metric-card {
            background-color: var(--bg-white);
            border: 1px solid var(--border-sand);
            border-top: 3px solid var(--clay-primary);
            border-radius: 10px;
            padding: 14px 16px;
            box-shadow: 0 3px 12px rgba(38, 35, 32, 0.03);
            margin-bottom: 10px;
            height: 118px;
            min-height: 118px;
            max-height: 118px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            box-sizing: border-box;
            overflow: hidden;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }

        .cota-kpi-grid .metric-card {
            margin-bottom: 0;
        }

        .metric-card:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(38, 35, 32, 0.06);
        }

        .metric-card .metric-label,
        .metric-card h4 {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            font-size: 11px !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.06em !important;
            color: var(--text-taupe) !important;
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1.2 !important;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .metric-card .metric-value,
        .metric-card h2 {
            font-family: 'JetBrains Mono', monospace !important;
            font-size: clamp(14.5px, 1.28vw, 19.5px) !important;
            font-weight: 700 !important;
            color: var(--text-charcoal) !important;
            margin: 4px 0 !important;
            padding: 0 !important;
            line-height: 1.25 !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }

        .metric-card .metric-sub,
        .metric-card small {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            font-size: 11px !important;
            color: var(--text-muted) !important;
            line-height: 1.28 !important;
            min-height: 28px;
            max-height: 28px;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            margin: 0 !important;
        }

        div[data-testid="stMetric"] {
            background-color: var(--bg-white) !important;
            border: 1px solid var(--border-sand) !important;
            border-left: 4px solid var(--clay-primary) !important;
            border-radius: 10px !important;
            padding: 16px 20px !important;
            box-shadow: 0 4px 14px rgba(38, 35, 32, 0.03) !important;
            min-height: 108px !important;
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
            font-size: clamp(16px, 1.4vw, 22px) !important;
            font-weight: 600 !important;
            white-space: nowrap !important;
        }

        /* 6. CABECERAS DE SECCIÓN Y BADGES DE OBRA */
        .cota-status-header {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 13px !important;
            font-weight: 700 !important;
            letter-spacing: 0.06em !important;
            text-transform: uppercase;
            margin: 14px 0 10px 0 !important;
        }

        .cota-status-header-bar {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 2px;
        }

        /* Cabeceras de Estado Plegables / Desplegables (Acordeón de Proyectos) */
        div[class*="st-key-btn_est_"] {
            margin-top: 16px !important;
            margin-bottom: 8px !important;
        }

        div[class*="st-key-btn_est_"] .stButton > button {
            display: flex !important;
            flex-direction: row !important;
            justify-content: flex-start !important;
            align-items: center !important;
            text-align: left !important;
            width: 100% !important;
            background-color: var(--bg-card) !important;
            border: 1px solid var(--border-sand) !important;
            border-left: 5px solid var(--clay-primary) !important;
            border-radius: 8px !important;
            padding: 9px 16px !important;
            min-height: 42px !important;
            box-shadow: 0 1px 4px rgba(38, 35, 32, 0.03) !important;
            cursor: pointer !important;
            transition: all 0.15s ease !important;
        }

        div[class*="st-key-btn_est_"] .stButton > button:hover {
            background-color: var(--bg-stone) !important;
            border-color: var(--clay-primary) !important;
            transform: none !important;
        }

        div[class*="st-key-btn_est_"] .stButton > button div[data-testid="stMarkdownContainer"] {
            text-align: left !important;
            width: 100% !important;
            display: flex !important;
            justify-content: flex-start !important;
        }

        div[class*="st-key-btn_est_"] .stButton > button p {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            font-size: 13.5px !important;
            font-weight: 700 !important;
            letter-spacing: 0.05em !important;
            color: var(--text-charcoal) !important;
            margin: 0 !important;
            padding: 0 !important;
            display: flex !important;
            align-items: center !important;
            gap: 10px !important;
            text-align: left !important;
        }

        div[class*="st-key-btn_est_"][class*="Planificaci"] .stButton > button {
            border-left-color: #D98A2B !important;
        }

        div[class*="st-key-btn_est_"][class*="Proceso"] .stButton > button {
            border-left-color: #C85A32 !important;
        }

        div[class*="st-key-btn_est_"][class*="Completado"] .stButton > button {
            border-left-color: #4A7C59 !important;
        }

        .cota-section-header {
            background-color: var(--bg-stone);
            border: 1px solid var(--border-sand);
            border-left: 4px solid var(--clay-primary);
            border-radius: 8px;
            padding: 10px 14px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
            font-weight: 600;
            color: var(--text-charcoal);
            margin: 18px 0 10px 0;
        }

        .cota-section-header span {
            color: var(--clay-primary);
            margin-right: 6px;
        }

        .cota-badge-container {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            align-items: center;
            justify-content: flex-end;
            padding-top: 4px;
        }

        .cota-badge {
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            font-weight: 600;
            padding: 5px 10px;
            border-radius: 6px;
            border: 1px solid var(--border-sand);
            background-color: var(--bg-white);
        }

        .cota-badge-pactado {
            color: var(--text-charcoal);
            background-color: var(--bg-stone);
        }

        .cota-badge-pagado {
            color: var(--clay-primary);
            border-color: var(--clay-border);
            background-color: var(--clay-soft);
        }

        .cota-badge-saldo-ok {
            color: var(--status-ok);
            border-color: rgba(74, 124, 89, 0.35);
            background-color: rgba(74, 124, 89, 0.10);
        }

        .cota-badge-saldo-error {
            color: var(--status-err);
            border-color: rgba(201, 59, 43, 0.35);
            background-color: rgba(201, 59, 43, 0.10);
        }

        /* 7. FORMULARIOS E INPUTS */
        div[data-testid="stForm"] {
            background-color: var(--bg-white) !important;
            border: 1px solid var(--border-sand) !important;
            border-radius: 12px !important;
            padding: 20px !important;
            box-shadow: 0 6px 20px rgba(38, 35, 32, 0.04) !important;
        }

        .stTextInput input, .stNumberInput input, .stTextArea textarea, .stDateInput input {
            background-color: var(--bg-bone) !important;
            color: var(--text-charcoal) !important;
            border: 1px solid var(--border-sand) !important;
            border-radius: 8px !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            min-height: 40px !important;
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
            min-height: 40px !important;
        }

        /* 8. BOTONES Y POPOVERS (ROJO ARCILLA Y SECUNDARIOS PIEDRA) */
        .stButton > button, .stFormSubmitButton > button, .stDownloadButton > button, div[data-testid="stPopover"] button {
            border-radius: 8px !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            font-weight: 600 !important;
            font-size: 13px !important;
            letter-spacing: 0.02em !important;
            padding: 0.45rem 0.9rem !important;
            min-height: 40px !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            transition: all 0.2s ease !important;
            border: 1px solid var(--border-sand) !important;
            background-color: var(--bg-white) !important;
            color: var(--text-charcoal) !important;
        }

        .stButton > button:hover, .stDownloadButton > button:hover, div[data-testid="stPopover"] button:hover {
            border-color: var(--clay-primary) !important;
            color: var(--clay-primary) !important;
            background-color: var(--bg-card) !important;
        }

        .stButton > button[kind="primary"], .stFormSubmitButton > button {
            background-color: var(--clay-primary) !important;
            color: #FFFFFF !important;
            border: 1px solid var(--clay-primary) !important;
            box-shadow: 0 4px 12px rgba(200, 90, 50, 0.18) !important;
        }

        .stButton > button[kind="primary"] *, .stFormSubmitButton > button * {
            color: #FFFFFF !important;
        }

        .stButton > button[kind="primary"]:hover, .stFormSubmitButton > button:hover {
            background-color: var(--clay-hover) !important;
            border-color: var(--clay-hover) !important;
            box-shadow: 0 6px 16px rgba(169, 70, 34, 0.25) !important;
        }

        /* 9. PESTAÑAS (TABS ARQUITECTÓNICOS) */
        .stTabs [data-baseweb="tab-list"] {
            gap: 6px;
            flex-wrap: wrap;
            background-color: var(--bg-stone);
            padding: 6px;
            border-radius: 10px;
            border: 1px solid var(--border-sand);
        }

        .stTabs [data-baseweb="tab"] {
            height: 36px;
            border-radius: 7px;
            padding: 0 12px;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            font-weight: 600;
            font-size: 12px;
            white-space: nowrap;
            color: var(--text-taupe) !important;
            background-color: transparent;
            border: none !important;
        }

        .stTabs [aria-selected="true"] {
            background-color: var(--bg-white) !important;
            color: var(--clay-primary) !important;
            font-weight: 700 !important;
            box-shadow: 0 2px 6px rgba(38, 35, 32, 0.08);
        }

        /* 10. EXPANDERS, TABLAS Y CONTENEDORES */
        div[data-testid="stExpander"] {
            background-color: var(--bg-white) !important;
            border: 1px solid var(--border-sand) !important;
            border-radius: 10px !important;
            box-shadow: 0 2px 8px rgba(38, 35, 32, 0.02) !important;
            margin-bottom: 8px !important;
        }

        div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] {
            border: 1px solid var(--border-sand) !important;
            border-radius: 10px !important;
            overflow: hidden !important;
            background-color: var(--bg-white) !important;
        }

        /* 11. CALENDARIO TÉCNICO MENSUAL */
        .calendar-container {
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 8px;
            margin-top: 14px;
        }

        .calendar-header-day {
            background-color: var(--bg-stone);
            border: 1px solid var(--border-sand);
            border-radius: 6px;
            padding: 8px;
            text-align: center;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            font-weight: 600;
            color: var(--text-taupe);
            letter-spacing: 0.08em;
        }

        .calendar-cell {
            background-color: var(--bg-white);
            border: 1px solid var(--border-sand);
            border-radius: 8px;
            min-height: 92px;
            padding: 8px;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .calendar-cell.today {
            border: 2px solid var(--clay-primary);
            background-color: var(--bg-card);
        }

        .calendar-cell-date {
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            font-weight: 600;
            color: var(--text-taupe);
            margin-bottom: 2px;
        }

        .calendar-cell.today .calendar-cell-date {
            color: var(--clay-primary);
            font-weight: 700;
        }

        .cal-task-item {
            font-size: 10.5px;
            font-weight: 500;
            padding: 3px 6px;
            border-radius: 4px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        hr {
            border-color: var(--border-sand) !important;
        }

        /* 12. TARJETA KPI CLICABLE (CAJA CHICA EN FINANZAS) */
        div[data-testid="stColumn"]:has(.st-key-btn_open_modulo_caja) div[data-testid="stVerticalBlock"] {
            position: relative !important;
            gap: 0px !important;
        }

        .st-key-btn_open_modulo_caja {
            position: absolute !important;
            top: 0 !important;
            left: 0 !important;
            right: 0 !important;
            width: 100% !important;
            height: 118px !important;
            z-index: 25 !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        .st-key-btn_open_modulo_caja div[data-testid="stButton"],
        .st-key-btn_open_modulo_caja button {
            width: 100% !important;
            height: 118px !important;
            min-height: 118px !important;
            max-height: 118px !important;
            opacity: 0 !important;
            cursor: pointer !important;
            margin: 0 !important;
            padding: 0 !important;
            border: none !important;
            background: transparent !important;
            box-shadow: none !important;
        }

        div[data-testid="stColumn"]:has(.st-key-btn_open_modulo_caja):hover .metric-card {
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 20px rgba(200, 90, 50, 0.14) !important;
            border-color: var(--clay-primary) !important;
        }
    </style>
    """
