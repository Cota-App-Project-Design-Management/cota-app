"""
Estilos visuales, temas y CSS para COTA APP.
Estética oscura, técnica, minimalista estilo Palantir.
"""

def get_app_css():
    """Retorna el bloque CSS inyectable en Streamlit."""
    return """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap');
    
    :root {
        --custom-bg: #070B14;
        --card-bg: #0d1424;
        --card-bg-hover: #111b30;
        --border-color: #1e293b;
        --text-muted: #cbd5e1;
        --text-secondary: #94a3b8;
        --text-color: #ffffff;
        --accent-cyan: #00E5FF;
        --btn-bg-start: #070B14;
        --btn-bg-end: #0d1424;
        --card-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        --login-bg: rgba(10, 15, 28, 0.90);
        --login-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
    
    @media (prefers-color-scheme: light) {
        :root {
            --custom-bg: #ffffff;
            --card-bg: #f8fafc;
            --card-bg-hover: #f1f5f9;
            --border-color: #cbd5e1;
            --text-muted: #475569;
            --text-secondary: #64748b;
            --text-color: #0f172a;
            --accent-cyan: #0891b2;
            --btn-bg-start: #ffffff;
            --btn-bg-end: #f1f5f9;
            --card-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            --login-bg: rgba(248, 250, 252, 0.95);
            --login-shadow: 0 10px 30px rgba(0,0,0,0.08);
        }
    }
    
    html, body { 
        font-size: 13px !important; 
        font-family: 'Outfit', 'Inter', -apple-system, sans-serif !important; 
        background-color: var(--custom-bg) !important; 
    }
    
    /* Tipografía nítida en selectores */
    div[role="listbox"] ul li, 
    div[role="listbox"] [role="option"], 
    div[role="listbox"] div,
    ul[role="listbox"] li,
    div[data-baseweb="select"] div {
        font-family: 'Inter', sans-serif !important;
        font-weight: 500 !important;
        font-size: 13px !important;
    }
    
    /* Header corporativo */
    .header-container { 
        display: flex; 
        align-items: center; 
        padding: 20px 0 22px 0; 
        gap: 18px; 
        border-bottom: 1px solid var(--border-color); 
        margin-bottom: 22px; 
    }
    
    .header-logo { 
        height: 52px; 
        width: auto; 
        object-fit: contain; 
    }
    
    .header-divider { 
        width: 1px; 
        height: 44px; 
        background-color: var(--border-color); 
        margin: 0 8px; 
    }
    
    .header-title-box { 
        display: flex; 
        flex-direction: column; 
        justify-content: center;
    }
    
    .header-title { 
        color: var(--text-color) !important; 
        font-size: 28px !important; 
        font-weight: 800; 
        letter-spacing: -0.5px; 
        margin: 0; 
        line-height: 1.1; 
    }
    
    .header-subtitle { 
        color: var(--accent-cyan); 
        font-family: 'Courier New', monospace; 
        font-size: 11px; 
        letter-spacing: 3px; 
        font-weight: 700; 
        margin-top: 4px;
        text-transform: uppercase;
    }
    
    /* Tarjetas métricas ejecutivas */
    .metric-card { 
        background-color: var(--card-bg) !important; 
        padding: 16px 14px; 
        border-radius: 6px; 
        text-align: center; 
        border-top: 3px solid var(--accent-cyan) !important; 
        border: 1px solid var(--border-color) !important; 
        transition: all 0.25s ease-in-out;
        box-shadow: var(--card-shadow) !important;
    }
    
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 18px rgba(0, 229, 255, 0.12) !important;
        border-color: var(--accent-cyan);
    }
    
    .metric-card h4 { 
        margin-bottom: 6px; 
        color: var(--text-secondary) !important; 
        font-weight: 600; 
        font-size: 12px; 
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .metric-card h2 { 
        margin-top: 0; 
        margin-bottom: 4px; 
        font-size: 24px; 
        font-weight: 700;
        color: var(--text-color) !important; 
        font-family: 'Outfit', sans-serif;
    }
    
    .metric-card small {
        font-size: 11px;
        color: var(--text-secondary);
        display: block;
    }
    
    /* Barra de estado técnica */
    .cota-status-header {
        font-family: 'Courier New', monospace !important;
        font-weight: bold !important;
        letter-spacing: 1px !important;
        margin-top: 20px !important;
        margin-bottom: 12px !important;
        border-bottom: 1px solid var(--border-color) !important;
        padding-bottom: 6px !important;
        display: flex !important;
        align-items: center !important;
        font-size: 13px !important;
    }
    
    .cota-status-header-bar {
        width: 4px !important;
        height: 14px !important;
        display: inline-block !important;
        margin-right: 8px !important;
    }
    
    .cota-section-header {
        color: var(--accent-cyan) !important;
        font-family: 'Courier New', monospace !important;
        font-weight: bold !important;
        font-size: 12px !important;
        text-transform: uppercase !important;
        margin-top: 20px !important;
        margin-bottom: 10px !important;
        border-bottom: 1px solid var(--border-color) !important;
        padding-bottom: 5px !important;
        letter-spacing: 1px !important;
        display: flex !important;
        align-items: center !important;
    }
    
    .cota-badge-container {
        display: flex !important;
        gap: 8px !important;
        font-family: 'Courier New', monospace !important;
        font-size: 11px !important;
        align-items: center !important;
        justify-content: flex-end !important;
        height: 100% !important;
    }
    
    .cota-badge {
        padding: 5px 10px !important;
        border-radius: 3px !important;
        font-weight: 700 !important;
        border: 1px solid transparent !important;
        white-space: nowrap !important;
    }
    
    .cota-badge-pactado {
        background-color: var(--card-bg) !important;
        color: var(--text-muted) !important;
        border-color: var(--border-color) !important;
    }
    
    .cota-badge-pagado {
        background-color: rgba(0, 229, 255, 0.08) !important;
        color: var(--accent-cyan) !important;
        border-color: rgba(0, 229, 255, 0.3) !important;
    }
    
    .cota-badge-saldo-ok {
        background-color: rgba(16, 185, 129, 0.08) !important;
        color: #10b981 !important;
        border-color: rgba(16, 185, 129, 0.3) !important;
    }
    
    .cota-badge-saldo-error {
        background-color: rgba(239, 68, 68, 0.08) !important;
        color: #ef4444 !important;
        border-color: rgba(239, 68, 68, 0.3) !important;
    }
    
    /* Login Card */
    .login-card {
        background: var(--login-bg) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 10px;
        padding: 32px 28px;
        box-shadow: var(--login-shadow) !important;
        text-align: center;
        font-family: 'Outfit', sans-serif;
    }
    
    .login-title {
        color: var(--text-color) !important;
        font-weight: 800;
        letter-spacing: 1.5px;
        margin-bottom: 4px;
        font-size: 22px;
        margin-top: 0;
    }
    
    .login-subtitle {
        color: var(--accent-cyan);
        font-size: 11px;
        font-family: 'Courier New', monospace;
        font-weight: 700;
        letter-spacing: 2.5px;
        margin-bottom: 14px;
        text-transform: uppercase;
    }
    
    .login-access {
        color: var(--text-secondary) !important;
        font-size: 11px;
        letter-spacing: 2px;
        margin-bottom: 6px;
    }
    
    /* Botones primarios y secundarios */
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #FF1744 0%, #D50000 100%) !important;
        color: #ffffff !important;
        border: 1px solid #FF1744 !important;
        border-radius: 4px !important;
        padding: 7px 16px !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: 0.8px !important;
        transition: all 0.2s ease !important;
    }
    
    .stButton>button[kind="primary"]:hover {
        background: linear-gradient(135deg, #FF5252 0%, #FF1744 100%) !important;
        border-color: #FF5252 !important;
        box-shadow: 0 0 14px rgba(255, 23, 68, 0.45) !important;
        transform: scale(1.01);
    }
    
    .stButton>button[kind="secondary"], .stButton>button:not([kind="primary"]) {
        background: linear-gradient(135deg, var(--btn-bg-start) 0%, var(--btn-bg-end) 100%) !important;
        color: var(--text-muted) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 4px !important;
        padding: 6px 14px !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }
    
    .stButton>button[kind="secondary"]:hover, .stButton>button:not([kind="primary"]):hover {
        border-color: var(--accent-cyan) !important;
        color: var(--accent-cyan) !important;
        box-shadow: 0 0 10px rgba(0, 229, 255, 0.2) !important;
    }
    
    /* Calendario Técnico */
    .calendar-container { 
        display: grid; 
        grid-template-columns: repeat(7, 1fr); 
        gap: 6px; 
        margin-top: 18px; 
    }
    
    .calendar-header-day { 
        text-align: center; 
        font-weight: bold; 
        color: var(--accent-cyan); 
        padding: 8px 0; 
        border-bottom: 1px solid var(--border-color); 
        font-family: monospace; 
        text-transform: uppercase; 
        font-size: 11px;
    }
    
    .calendar-cell { 
        min-height: 105px; 
        border: 1px solid var(--border-color); 
        border-radius: 4px; 
        padding: 6px; 
        background-color: var(--card-bg); 
        transition: border-color 0.2s ease; 
    }
    
    .calendar-cell:hover { 
        border-color: var(--accent-cyan); 
    }
    
    .calendar-cell.today { 
        border-color: var(--accent-cyan); 
        background-color: rgba(0, 229, 255, 0.05); 
    }
    
    .calendar-cell-date {
        font-family: monospace;
        font-weight: 700;
        font-size: 11px;
        color: var(--text-secondary);
        margin-bottom: 4px;
    }
    
    .cal-task-item { 
        font-size: 10px; 
        padding: 3px 5px; 
        margin-bottom: 3px; 
        border-radius: 2px; 
        font-weight: 600; 
        position: relative !important; 
        cursor: pointer !important; 
    }
    
    .calendar-legend {
        display: flex !important;
        flex-wrap: wrap !important;
        justify-content: center !important;
        gap: 14px !important;
        margin-top: 20px !important;
        padding: 12px !important;
        background: var(--card-bg) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 6px !important;
    }
    
    .calendar-legend-item {
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
        font-family: monospace !important;
        font-size: 11px !important;
        color: var(--text-secondary) !important;
    }
    
    .calendar-legend-color {
        width: 10px !important;
        height: 10px !important;
        border-radius: 2px !important;
    }
    </style>
    """
