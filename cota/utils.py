"""
Utilidades auxiliares, formateo de datos, motor de fechas, parsing y sugerencias.
"""

import base64
import datetime
import io
import io
import os
import re
import unicodedata
from zoneinfo import ZoneInfo
import pandas as pd


def safe_float(val, default=0.0):
    """Convierte a float de forma segura, soportando formatos latinos (comas y puntos) y valores vacíos."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if s == '' or s.lower() in ['nan', 'none', 'null', '<na>']:
        return default
    try:
        return float(s)
    except ValueError:
        try:
            if ',' in s and '.' in s:
                if s.rfind(',') > s.rfind('.'):
                    s_clean = s.replace('.', '').replace(',', '.')
                else:
                    s_clean = s.replace(',', '')
                return float(s_clean)
            elif ',' in s:
                return float(s.replace(',', '.'))
            elif '.' in s:
                return float(s)
        except ValueError:
            return default
    return default


def safe_str(val, default=""):
    """Convierte cualquier valor a string limpio."""
    if val is None or pd.isna(val):
        return default
    s = str(val).strip()
    if s.lower() in ['nan', 'none', 'null', '<na>']:
        return default
    return s


def to_bool(val):
    """Convierte un valor de celda a booleano estricto."""
    if isinstance(val, bool):
        return val
    if val is None or pd.isna(val):
        return False
    s = str(val).strip().lower()
    return s in ['true', '1', 'verdadero', 't', 'y', 'yes', 'si', 's']


def get_now(tz_name="America/Lima"):
    """Retorna la fecha y hora actual en la zona horaria indicada sin usar utcnow() obsoleto."""
    try:
        tz = ZoneInfo(tz_name)
        return datetime.datetime.now(tz)
    except Exception:
        # Fallback para zona horaria estándar de Perú (UTC-5)
        offset = datetime.timezone(datetime.timedelta(hours=-5))
        return datetime.datetime.now(offset)


def parse_date(val, default=None):
    """
    Parsea una fecha de manera tolerante admitiendo formatos ISO (YYYY-MM-DD),
    latinos (DD/MM/YYYY o DD-MM-YYYY) o datetimes. Retorna un objeto datetime.date o default.
    """
    if val is None or pd.isna(val):
        return default
    if isinstance(val, datetime.date) and not isinstance(val, datetime.datetime):
        return val
    if isinstance(val, (datetime.datetime, pd.Timestamp)):
        return val.date()

    s = str(val).strip()
    if not s or s.lower() in ['nan', 'none', 'null', 'nat', '']:
        return default

    # Cortar componente horario si existe
    if ' ' in s:
        s = s.split(' ')[0].strip()
    if 'T' in s:
        s = s.split('T')[0].strip()

    # Intentar formatos comunes
    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%d/%m/%y",
        "%d-%m-%y"
    ]
    for fmt in formats:
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            continue

    # Fallback con pandas
    try:
        dt = pd.to_datetime(s, dayfirst=True, errors='coerce')
        if pd.notna(dt):
            return dt.date()
    except Exception:
        pass

    return default


def format_date(val, fmt="%d/%m/%Y", default=""):
    """Formatea una fecha a string de visualización."""
    d = parse_date(val)
    if d:
        return d.strftime(fmt)
    return default


def format_currency(val, symbol="S/"):
    """Formatea un monto como moneda con separador de miles y 2 decimales."""
    f = safe_float(val, 0.0)
    return f"{symbol} {f:,.2f}"


def limpiar_especialidad(texto):
    """Normaliza texto eliminando tildes y caracteres diacríticos."""
    if not texto or pd.isna(texto):
        return ""
    clean = ''.join(c for c in unicodedata.normalize('NFD', str(texto).strip()) if unicodedata.category(c) != 'Mn')
    return clean.capitalize()


def extraer_esp(df_maestro=None):
    """Extrae la lista única de especialidades registradas en el catálogo de maestros."""
    if df_maestro is None or df_maestro.empty or 'Especialidad' not in df_maestro.columns:
        return ["Ninguna", "Arquitectura", "Diseño Interior", "Carpintería / Madera", "Iluminación", "Inst. Eléctricas", "Inst. Sanitarias", "Pintura y Acabados", "Drywall / Tabiquería", "Albañilería"]
    raw = df_maestro['Especialidad'].dropna().astype(str).tolist()
    todas = set([limpiar_especialidad(sub) for e in raw for sub in e.split(',') if limpiar_especialidad(sub)])
    res = ["Ninguna"] + [e.replace("Albanileria", "Albañilería") for e in sorted(list(todas)) if e]
    return res


COTA_LOGO_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 360" width="1000" height="360">'
    '<path fill="#1F1B18" d="M 223.45 101.58 A 122 122 0 1 0 223.45 258.42 L 186.68 227.57 A 74 74 0 1 1 186.68 132.43 Z"/>'
    '<path fill="#BD4B28" fill-rule="evenodd" d="M 382 58 A 122 122 0 1 0 382 302 A 122 122 0 1 0 382 58 Z M 382 106 A 74 74 0 1 1 382 254 A 74 74 0 1 1 382 106 Z"/>'
    '<line x1="382" y1="2" x2="382" y2="358" stroke="#BD4B28" stroke-width="6.5"/>'
    '<line x1="216" y1="180" x2="548" y2="180" stroke="#BD4B28" stroke-width="6.5"/>'
    '<path fill="#1F1B18" d="M 530 63 H 730 V 109 H 654 V 297 H 606 V 109 H 530 Z"/>'
    '<path fill="#1F1B18" fill-rule="evenodd" d="M 838 63 H 884 L 988 297 H 936 L 914 244 H 808 L 786 297 H 734 Z M 861 120 L 824 204 H 898 Z"/>'
    '</svg>'
)


def get_image_base64(path):
    """Convierte una imagen local a Data URL base64 o retorna el logo oficial de COTA embebido."""
    if not path:
        b64_svg = base64.b64encode(COTA_LOGO_SVG.encode("utf-8")).decode("ascii")
        return f"data:image/svg+xml;base64,{b64_svg}"
    s_path = str(path).strip()
    if s_path.startswith("http://") or s_path.startswith("https://") or s_path.startswith("data:image/"):
        return s_path

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        s_path,
        os.path.join(repo_root, s_path),
        os.path.join(r"D:\cota-app", s_path),
        os.path.join(repo_root, "logo", "Logo Full.png"),
        os.path.join(repo_root, "logo", "Logo Full.jpg"),
        os.path.join(repo_root, "logo", "Logo Full.svg"),
        os.path.join(r"D:\cota-app", "logo", "Logo Full.png"),
        os.path.join(r"D:\cota-app", "logo", "Logo Full.jpg"),
    ]
    for cand in candidates:
        if cand and os.path.isfile(cand):
            try:
                with open(cand, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("ascii")
                    low = cand.lower()
                    if low.endswith(".svg"):
                        mime = "image/svg+xml"
                    elif low.endswith(".png"):
                        mime = "image/png"
                    else:
                        mime = "image/jpeg"
                    return f"data:{mime};base64,{b64}"
            except Exception:
                continue

    b64_svg = base64.b64encode(COTA_LOGO_SVG.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{b64_svg}"


def _unused_old_get_image(path):
    """Convierte una imagen local a Data URL base64 o retorna URLs externas intactas."""
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://"):
        return path
    try:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
            mime = "image/png" if path.lower().endswith(".png") else "image/jpeg"
            return f"data:{mime};base64,{b64}"
    except Exception:
        return None


def normalizar_hex_color(color_str: str, default: str = "#C85A32") -> str:
    """Normaliza un color hexadecimal al formato '#RRGGBB' en mayúsculas."""
    if not color_str or not isinstance(color_str, str):
        return default.upper()
    s = color_str.strip().lstrip("#").upper()
    if len(s) == 3 and all(c in "0123456789ABCDEF" for c in s):
        s = "".join(c * 2 for c in s)
    if len(s) == 6 and all(c in "0123456789ABCDEF" for c in s):
        return f"#{s}"
    return default.upper()


def hex_a_rgb(color_hex: str) -> tuple[int, int, int]:
    """Convierte un color '#RRGGBB' a una tupla (R, G, B)."""
    norm = normalizar_hex_color(color_hex).lstrip("#")
    return (int(norm[0:2], 16), int(norm[2:4], 16), int(norm[4:6], 16))


def oscurecer_hex_color(color_hex: str, factor: float = 0.82) -> str:
    """Oscurece un color '#RRGGBB' multiplicando sus canales por `factor`."""
    r, g, b = hex_a_rgb(color_hex)
    r2 = max(0, min(255, int(round(r * factor))))
    g2 = max(0, min(255, int(round(g * factor))))
    b2 = max(0, min(255, int(round(b * factor))))
    return f"#{r2:02X}{g2:02X}{b2:02X}"


def aclarar_hex_color(color_hex: str, mezcla_blanco: float = 0.90) -> str:
    """Aclara un color '#RRGGBB' mezclándolo con blanco para fondos suaves."""
    r, g, b = hex_a_rgb(color_hex)
    m = max(0.0, min(1.0, float(mezcla_blanco)))
    r2 = max(0, min(255, int(round(r * (1.0 - m) + 255 * m))))
    g2 = max(0, min(255, int(round(g * (1.0 - m) + 255 * m))))
    b2 = max(0, min(255, int(round(b * (1.0 - m) + 255 * m))))
    return f"#{r2:02X}{g2:02X}{b2:02X}"


def preparar_logo_png_bytes(source, max_height: int = 110) -> tuple:
    """
    Convierte una ruta de archivo, bytes o Data URI base64 en bytes PNG optimizados
    y retorna (png_bytes, (width, height)) listos para incrustar en Excel (openpyxl) y PDF (FPDF).
    """
    raw_bytes = None
    if isinstance(source, (bytes, bytearray)):
        raw_bytes = bytes(source)
    elif isinstance(source, str) and source.strip():
        s = source.strip()
        if s.startswith("data:image/"):
            if "svg+xml" in s:
                return None, None
            try:
                b64_part = s.split(",", 1)[1]
                raw_bytes = base64.b64decode(b64_part)
            except Exception:
                raw_bytes = None
        else:
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            for cand in [
                s,
                os.path.join(repo_root, s),
                os.path.join(repo_root, "Logo", os.path.basename(s)),
                os.path.join(repo_root, "logo", os.path.basename(s)),
                os.path.join(repo_root, "Logo", "Logo Full.png"),
                os.path.join(repo_root, "logo", "Logo Full.png"),
            ]:
                if cand and os.path.isfile(cand) and not cand.lower().endswith(".svg"):
                    try:
                        with open(cand, "rb") as f:
                            raw_bytes = f.read()
                        break
                    except Exception:
                        continue

    if not raw_bytes:
        return None, None

    try:
        from PIL import Image
        with Image.open(io.BytesIO(raw_bytes)) as im:
            im_rgba = im.convert("RGBA")
            w, h = im_rgba.size
            if h > max_height and h > 0:
                ratio = max_height / float(h)
                new_w = max(1, int(round(w * ratio)))
                new_h = max(1, int(round(h * ratio)))
                resamp = getattr(Image, "Resampling", Image).LANCZOS
                im_rgba = im_rgba.resize((new_w, new_h), resamp)
                w, h = im_rgba.size
            buf = io.BytesIO()
            im_rgba.save(buf, format="PNG", optimize=True)
            return buf.getvalue(), (w, h)
    except Exception:
        return None, None


def obtener_marca_estudio() -> dict:
    """
    Obtiene la configuración de marca del Estudio para el Branch actual (nombre, color de marca y logo).
    Prioriza sesión/config_estudio -> studio_branding.json del branch -> valores por defecto.
    """
    import json
    import streamlit as st
    from cota.config import (
        DEFAULT_BRAND_COLOR,
        DEFAULT_LOGO_PATH,
        DEFAULT_STUDIO_NAME,
        STUDIO_BRANDING_FILE,
        get_secret,
    )

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    branding_file = os.path.join(repo_root, STUDIO_BRANDING_FILE)

    data_file = {}
    if os.path.isfile(branding_file):
        try:
            with open(branding_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    data_file = loaded
        except Exception:
            data_file = {}

    sess_brand = {}
    try:
        if "studio_branding" in st.session_state and isinstance(st.session_state["studio_branding"], dict):
            sess_brand = dict(st.session_state["studio_branding"])
        elif "config_estudio" in st.session_state and isinstance(st.session_state["config_estudio"], pd.DataFrame):
            df_cfg = st.session_state["config_estudio"]
            if not df_cfg.empty and "Clave" in df_cfg.columns and "Valor" in df_cfg.columns:
                for k_cfg, k_dest in [
                    ("marca_studio_name", "studio_name"),
                    ("marca_brand_color", "brand_color"),
                    ("marca_logo_path", "logo_path"),
                    ("marca_logo_base64", "logo_base64"),
                ]:
                    m_r = df_cfg[df_cfg["Clave"].astype(str) == k_cfg]
                    if not m_r.empty:
                        v_s = safe_str(m_r.iloc[-1]["Valor"], "")
                        if v_s:
                            sess_brand[k_dest] = v_s
    except Exception:
        pass

    default_studio = get_secret("STUDIO_NAME", DEFAULT_STUDIO_NAME) or "LB Studio"
    studio_name = (
        safe_str(sess_brand.get("studio_name"))
        or safe_str(data_file.get("studio_name"))
        or default_studio
    )
    brand_color = normalizar_hex_color(
        safe_str(sess_brand.get("brand_color"))
        or safe_str(data_file.get("brand_color"))
        or get_secret("BRAND_COLOR", DEFAULT_BRAND_COLOR)
        or DEFAULT_BRAND_COLOR
    )
    logo_path = (
        safe_str(sess_brand.get("logo_path"))
        or safe_str(data_file.get("logo_path"))
        or get_secret("LOGO_IMAGE", DEFAULT_LOGO_PATH)
        or DEFAULT_LOGO_PATH
    )
    logo_b64_override = (
        safe_str(sess_brand.get("logo_base64"))
        or safe_str(data_file.get("logo_base64"))
    )

    if logo_b64_override and logo_b64_override.startswith("data:image/"):
        logo_base64 = logo_b64_override
        png_bytes, png_size = preparar_logo_png_bytes(logo_b64_override)
        if png_bytes is None:
            png_bytes, png_size = preparar_logo_png_bytes(logo_path)
    else:
        logo_base64 = get_image_base64(logo_path)
        png_bytes, png_size = preparar_logo_png_bytes(logo_path)

    brand_hex = brand_color.lstrip("#")
    brand_rgb = hex_a_rgb(brand_color)
    dark_color = oscurecer_hex_color(brand_color, 0.84)
    soft_color = aclarar_hex_color(brand_color, 0.90)
    border_soft = aclarar_hex_color(brand_color, 0.72)

    return {
        "studio_name": studio_name,
        "brand_color": brand_color,
        "brand_hex": brand_hex,
        "brand_rgb": brand_rgb,
        "brand_dark_color": dark_color,
        "brand_dark_hex": dark_color.lstrip("#"),
        "brand_dark_rgb": hex_a_rgb(dark_color),
        "brand_soft_color": soft_color,
        "brand_soft_hex": soft_color.lstrip("#"),
        "brand_border_color": border_soft,
        "logo_path": logo_path,
        "logo_base64": logo_base64,
        "logo_png_bytes": png_bytes,
        "logo_size": png_size,
    }


def guardar_marca_estudio(
    studio_name: str = None,
    brand_color: str = None,
    logo_bytes: bytes = None,
    logo_filename: str = None,
    reset_default: bool = False,
) -> dict:
    """
    Guarda la configuración de marca del Estudio (color, nombre y logo) tanto en el archivo
    del Branch (`studio_branding.json` + carpeta `Logo/`) como en `st.session_state`.
    """
    import json
    import streamlit as st
    from cota.config import (
        DEFAULT_BRAND_COLOR,
        STUDIO_BRANDING_FILE,
    )

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    branding_file = os.path.join(repo_root, STUDIO_BRANDING_FILE)
    logo_dir = os.path.join(repo_root, "Logo")
    if not os.path.isdir(logo_dir):
        logo_dir = os.path.join(repo_root, "logo")
    os.makedirs(logo_dir, exist_ok=True)

    if reset_default:
        nuevo_data = {
            "studio_name": "LB Studio",
            "brand_color": DEFAULT_BRAND_COLOR,
            "logo_path": "Logo/Logo Full.png",
            "logo_base64": "",
        }
    else:
        actual = obtener_marca_estudio()
        nom_final = safe_str(studio_name).strip() if studio_name is not None else actual["studio_name"]
        if not nom_final:
            nom_final = actual["studio_name"] or "LB Studio"
        col_final = normalizar_hex_color(brand_color, default=actual["brand_color"]) if brand_color is not None else actual["brand_color"]
        path_final = actual["logo_path"]
        b64_final = ""

        if os.path.isfile(branding_file):
            try:
                with open(branding_file, "r", encoding="utf-8") as f:
                    prev_d = json.load(f)
                    if isinstance(prev_d, dict):
                        b64_final = safe_str(prev_d.get("logo_base64", ""))
            except Exception:
                pass

        if logo_bytes is not None and len(logo_bytes) > 0:
            fn_low = safe_str(logo_filename, "studio_logo.png").lower()
            if fn_low.endswith(".svg"):
                dest_rel = "Logo/studio_logo.svg"
                dest_abs = os.path.join(repo_root, "Logo", "studio_logo.svg")
                try:
                    with open(dest_abs, "wb") as f:
                        f.write(logo_bytes)
                    path_final = dest_rel
                except Exception:
                    pass
                b64_str = base64.b64encode(logo_bytes).decode("ascii")
                b64_final = f"data:image/svg+xml;base64,{b64_str}"
            else:
                png_opt, _ = preparar_logo_png_bytes(logo_bytes, max_height=240)
                bytes_to_save = png_opt if png_opt else bytes(logo_bytes)
                dest_rel = "Logo/studio_logo.png"
                dest_abs = os.path.join(repo_root, "Logo", "studio_logo.png")
                try:
                    with open(dest_abs, "wb") as f:
                        f.write(bytes_to_save)
                    path_final = dest_rel
                except Exception:
                    pass
                b64_str = base64.b64encode(bytes_to_save).decode("ascii")
                b64_final = f"data:image/png;base64,{b64_str}"

        nuevo_data = {
            "studio_name": nom_final,
            "brand_color": col_final,
            "logo_path": path_final,
            "logo_base64": b64_final,
        }

    try:
        with open(branding_file, "w", encoding="utf-8") as f:
            json.dump(nuevo_data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    try:
        st.session_state["studio_branding"] = dict(nuevo_data)
        if "config_estudio" in st.session_state and isinstance(st.session_state["config_estudio"], pd.DataFrame):
            df_cfg = st.session_state["config_estudio"].copy()
            for k_c, v_c in [
                ("marca_studio_name", nuevo_data["studio_name"]),
                ("marca_brand_color", nuevo_data["brand_color"]),
                ("marca_logo_path", nuevo_data["logo_path"]),
                ("marca_logo_base64", nuevo_data.get("logo_base64", "")),
            ]:
                if not df_cfg.empty and "Clave" in df_cfg.columns:
                    df_cfg = df_cfg[df_cfg["Clave"].astype(str) != k_c]
                df_cfg = pd.concat(
                    [df_cfg, pd.DataFrame([{"Clave": k_c, "Valor": str(v_c)}])],
                    ignore_index=True,
                )
            st.session_state["config_estudio"] = df_cfg
    except Exception:
        pass

    return obtener_marca_estudio()


def _legacy_get_image(path):
    """Convierte una imagen local a Data URL base64 o retorna URLs externas intactas."""
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://"):
        return path
    try:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
            mime = "image/png" if path.lower().endswith(".png") else "image/jpeg"
            return f"data:{mime};base64,{b64}"
    except Exception:
        return None


def calcular_rating(nombre, df_historial=None, df_tasks=None, df_maestro=None):
    """Calcula el rating (1 a 5) de un contratista/maestro según su historial y bitácora."""
    base = 5.0
    penal_hist = 0
    penal_app = 0
    bonus_notas = 0.0

    if df_historial is not None and not df_historial.empty and 'ID_Contratista' in df_historial.columns:
        est_mask_h = df_historial['Estado'].astype(str).str.contains('retraso', case=False, na=False) if 'Estado' in df_historial.columns else pd.Series(False, index=df_historial.index)
        penal_hist = len(df_historial[
            (df_historial['ID_Contratista'] == nombre) &
            est_mask_h
        ])

    if df_tasks is not None and not df_tasks.empty and 'Contratista' in df_tasks.columns:
        culpable = df_tasks.get('Culpa_Contratista', pd.Series(False, index=df_tasks.index))
        est_mask_t = df_tasks['Estado'].astype(str).str.contains('retraso', case=False, na=False) if 'Estado' in df_tasks.columns else pd.Series(False, index=df_tasks.index)
        penal_app = len(df_tasks[
            (df_tasks['Contratista'] == nombre) &
            est_mask_t &
            (culpable.apply(to_bool) == True)
        ])

    if df_maestro is not None and not df_maestro.empty and 'ID_Contratista' in df_maestro.columns:
        notas = df_maestro.loc[df_maestro['ID_Contratista'] == nombre, 'Notas'].values
        notas_str = str(notas[0]) if len(notas) > 0 and pd.notna(notas[0]) else ""
        bonus_notas = (notas_str.count("[+]") * 0.5) - (notas_str.count("[-]") * 1.0)

    rating_final = base - (penal_hist + penal_app) + bonus_notas
    return max(1, min(5, int(round(rating_final))))


def sugerir_contratista(esp_req, ubi_proy, req_i, req_f, df_maestro, df_tasks, df_historial=None, app_title="COTA APP"):
    """
    Sugeridor inteligente de contratistas según especialidad requerida,
    disponibilidad en las fechas solicitadas, proximidad geográfica y rating histórico.
    """
    if not esp_req or esp_req in ["Ninguna", "", "None"]:
        return None
    if df_maestro is None or df_maestro.empty:
        return "No hay contratistas registrados en el sistema."

    maestro = df_maestro.copy()
    esp_req_limpia = limpiar_especialidad(esp_req)
    candidatos = maestro[
        maestro['Especialidad'].apply(lambda x: limpiar_especialidad(x)).str.contains(esp_req_limpia, case=False, na=False)
    ].copy()

    if candidatos.empty:
        return f"Aviso: Sin especialistas en '{esp_req}' registrados en la base."

    d_req_i = parse_date(req_i)
    d_req_f = parse_date(req_f)

    candidatos['Puntaje'] = 0.0

    if d_req_i and d_req_f and df_tasks is not None and not df_tasks.empty:
        for idx, r in candidatos.iterrows():
            c_n = r['ID_Contratista']
            t_c = df_tasks[(df_tasks['Contratista'] == c_n)]
            if 'Permitir_Cruce' in t_c.columns:
                t_c = t_c[~t_c['Permitir_Cruce'].apply(to_bool)]

            for _, t in t_c.iterrows():
                t_i = parse_date(t.get('Inicio'))
                t_f = parse_date(t.get('Fin'))
                if t_i and t_f and d_req_i <= t_f and t_i <= d_req_f:
                    candidatos.at[idx, 'Puntaje'] -= 1000.0
                    break

    # Filtrar especialistas ocupados en ese rango
    disponibles = candidatos[candidatos['Puntaje'] >= 0].copy()
    if disponibles.empty:
        return f"Aviso: Todos los especialistas en '{esp_req}' tienen tareas activas en ese rango de fechas."

    # Proximidad geográfica
    if 'Ubicación_Base' in disponibles.columns and ubi_proy:
        disponibles.loc[disponibles['Ubicación_Base'].astype(str).str.strip().str.lower() == str(ubi_proy).strip().lower(), 'Puntaje'] += 2.0

    # Rating
    disponibles['Estrellas'] = [calcular_rating(n, df_historial, df_tasks, df_maestro) for n in disponibles['ID_Contratista']]
    disponibles['Puntaje'] += disponibles['Estrellas']

    mejor = disponibles.sort_values(by='Puntaje', ascending=False).iloc[0]
    return f"Sugerencia {app_title}: {mejor['ID_Contratista']} (Rating: {mejor['Estrellas']}/5 estrellas)."


def extraer_texto_documento(uploaded_file):
    """Extrae texto de archivos .txt, .md, .docx, .pdf para actas y notas de reunión."""
    if uploaded_file is None:
        return ""
    name = uploaded_file.name.lower()
    try:
        if name.endswith(('.txt', '.md')):
            return uploaded_file.getvalue().decode('utf-8', errors='replace')
        elif name.endswith('.docx'):
            try:
                import docx
                doc = docx.Document(io.BytesIO(uploaded_file.getvalue()))
                full_text = []
                for p in doc.paragraphs:
                    if p.text.strip():
                        full_text.append(p.text)
                for t in doc.tables:
                    for row in t.rows:
                        row_text = [c.text.strip() for c in row.cells if c.text.strip()]
                        if row_text:
                            full_text.append(" | ".join(row_text))
                return "\n".join(full_text)
            except Exception:
                return uploaded_file.getvalue().decode('latin-1', errors='replace')
        elif name.endswith('.pdf'):
            try:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(uploaded_file.getvalue()))
                text_pages = []
                for page in reader.pages:
                    t = page.extract_text()
                    if t:
                        text_pages.append(t)
                return "\n\n".join(text_pages)
            except Exception:
                return ""
        else:
            return uploaded_file.getvalue().decode('utf-8', errors='replace')
    except Exception:
        return ""


def parse_resumen_meet(texto, proyecto, count=0):
    """
    Parser heurístico limpio y determinista para minutas y notas de reunión de Google Meet / transcripciones.
    Extrae organizador, fecha, hora, asistentes y compromisos sin dependencias externas ni alucinaciones.
    """
    lines = [l.strip() for l in str(texto).splitlines() if l.strip()]
    num_s = count + 1
    num_str = f"0{num_s}" if num_s < 10 else str(num_s)

    fecha_actual_str = datetime.date.today().strftime("%d/%m/%Y")

    # Extraer fecha
    m_fecha = re.search(r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})', texto)
    if m_fecha:
        d, m, y = m_fecha.groups()
        if len(y) == 2:
            y = "20" + y
        fecha_str = f"{int(d):02d}/{int(m):02d}/{y}"
    else:
        fecha_str = fecha_actual_str

    # Extraer hora
    m_hora = re.search(r'(\d{1,2}:\d{2}\s*(?:a\.?\s*m\.?|p\.?\s*m\.?|AM|PM)?)', texto, re.IGNORECASE)
    hora_str = m_hora.group(1) if m_hora else "10:00 a. m."

    invitados = []
    acuerdos = []

    modo = None
    for line in lines:
        l_lower = line.lower()
        if any(h in l_lower for h in ['asistentes', 'participantes', 'attendees', 'presentes']):
            modo = 'invitados'
            continue
        elif any(h in l_lower for h in ['próximos pasos', 'proximos pasos', 'action items', 'tareas', 'acuerdos', 'decisiones', 'compromisos']):
            modo = 'acuerdos'
            continue
        elif any(h in l_lower for h in ['resumen', 'overview', 'temas tratados', 'agenda']):
            modo = 'resumen'
            continue

        if modo == 'invitados':
            clean_l = re.sub(r'^[•\-\*\d\.\)]\s*', '', line).strip()
            if clean_l and not clean_l.endswith(':'):
                partes = clean_l.split('(')
                nom = partes[0].strip()
                rol = partes[1].replace(')', '').strip() if len(partes) > 1 else "Participante"
                if nom:
                    invitados.append({
                        "nombre": nom,
                        "empresa": "",
                        "cargo": rol,
                        "asistencia": "Asistió"
                    })
        elif modo == 'acuerdos':
            clean_l = re.sub(r'^[•\-\*\d\.\)]\s*', '', line).strip()
            if clean_l and not clean_l.endswith(':'):
                resp = "Equipo de Proyecto"
                act = clean_l
                if ':' in clean_l:
                    p = clean_l.split(':', 1)
                    if len(p[0].split()) <= 4:
                        resp = p[0].strip()
                        act = p[1].strip()
                elif '-' in clean_l and len(clean_l.split('-')[0].split()) <= 4:
                    p = clean_l.split('-', 1)
                    resp = p[0].strip()
                    act = p[1].strip()
                acuerdos.append({
                    "descripcion": "Acuerdo de coordinación",
                    "responsable": resp,
                    "acuerdo": act
                })

    if not invitados:
        invitados.append({
            "nombre": "Equipo del Estudio",
            "empresa": "Estudio",
            "cargo": "Arquitecto / Diseñador",
            "asistencia": "Asistió"
        })
    if not acuerdos:
        acuerdos.append({
            "descripcion": "Revisión general de avances",
            "responsable": "Equipo del Estudio",
            "acuerdo": "Avanzar entregables de la fase actual"
        })

    return {
        "nombre_sesion": f"Acta de Reunión N° {num_str} - {proyecto}",
        "tipo_reunion": "Con Cliente",
        "etapa": "Diseño",
        "fecha_prog": fecha_str,
        "fecha_real": fecha_str,
        "hora": hora_str,
        "organizador": invitados[0]["nombre"] if invitados else "Estudio",
        "lider": invitados[0]["nombre"] if invitados else "Líder de Proyecto",
        "invitados": invitados,
        "acuerdos": acuerdos,
        "resumen_ejecutivo": "Minuta registrada a partir de notas de reunión."
    }


def analizar_tareas_proyecto(df_tasks: pd.DataFrame, proy_name: str, fecha_hoy=None) -> dict:
    """
    Analiza las tareas de un proyecto y devuelve conteos operativos (total, en proceso, completadas)
    junto con un widget inteligente de alertas (tareas atrasadas, por terminar, por empezar o en curso).
    """
    hoy = parse_date(fecha_hoy) or get_now().date()
    res = {
        "total": 0,
        "en_proceso": 0,
        "completadas": 0,
        "planificadas": 0,
        "atrasadas": [],
        "por_terminar": [],
        "por_empezar": [],
        "en_curso_lista": [],
        "widget_badge": "⚪ SIN TAREAS",
        "widget_titulo": "Sin tareas registradas",
        "widget_detalle": "Agrega tareas en Ejecución & Partidas",
        "widget_color": "#6E665E",
        "widget_bg": "#F7F4EF",
        "pills_extra": [],
    }

    if df_tasks is None or df_tasks.empty or "Proyecto" not in df_tasks.columns:
        return res

    df_p = df_tasks[df_tasks["Proyecto"] == proy_name].copy()
    if df_p.empty:
        return res

    res["total"] = len(df_p)

    for _, r in df_p.iterrows():
        est = safe_str(r.get("Estado", ""))
        est_low = est.lower()
        tarea_nom = safe_str(r.get("Tarea", "Tarea sin nombre"))
        ctr_nom = safe_str(r.get("Contratista", "Sin asignar")) or "Sin asignar"
        ini_d = parse_date(r.get("Inicio"))
        fin_d = parse_date(r.get("Fin"))

        es_completada = "completado" in est_low
        es_proceso = ("proceso" in est_low) or (
            not es_completada and ini_d is not None and fin_d is not None and ini_d <= hoy <= fin_d
        )

        if es_completada:
            res["completadas"] += 1
            continue

        if "proceso" in est_low:
            res["en_proceso"] += 1
        elif es_proceso:
            res["en_proceso"] += 1
        else:
            res["planificadas"] += 1

        info_item = {
            "Tarea": tarea_nom,
            "Contratista": ctr_nom,
            "Inicio": ini_d,
            "Fin": fin_d,
            "Estado": est,
        }

        # 1. ¿Está atrasada? (No completada y fecha fin < hoy)
        if fin_d is not None and fin_d < hoy:
            dias_atr = (hoy - fin_d).days
            info_item["dias"] = dias_atr
            res["atrasadas"].append(info_item)
        # 2. ¿Está por terminar pronto? (Activa o en proceso y vence en los próximos 7 días)
        elif fin_d is not None and hoy <= fin_d <= (hoy + datetime.timedelta(days=7)) and (es_proceso or (ini_d and ini_d <= hoy)):
            dias_rest = (fin_d - hoy).days
            info_item["dias"] = dias_rest
            res["por_terminar"].append(info_item)
        # 3. ¿Está por empezar pronto? (Inicia hoy o en los próximos 14 días y aún no está en proceso)
        elif ini_d is not None and ini_d >= hoy and "proceso" not in est_low:
            dias_ini = (ini_d - hoy).days
            info_item["dias"] = dias_ini
            res["por_empezar"].append(info_item)
        elif es_proceso:
            res["en_curso_lista"].append(info_item)

    # Ordenar listas por urgencia
    res["atrasadas"].sort(key=lambda x: x.get("dias", 0), reverse=True)
    res["por_terminar"].sort(key=lambda x: x.get("dias", 999))
    res["por_empezar"].sort(key=lambda x: x.get("dias", 999))

    # Construir alerta principal y píldoras secundarias
    pills = []
    if res["atrasadas"]:
        top = res["atrasadas"][0]
        d_fin = top["Fin"].strftime("%d/%m/%Y") if top["Fin"] else ""
        res["widget_badge"] = f"🔴 ATRASADA ({len(res['atrasadas'])})" if len(res["atrasadas"]) > 1 else "🔴 TAREA ATRASADA"
        res["widget_titulo"] = top["Tarea"]
        res["widget_detalle"] = f"Venció hace {top['dias']} día(s) ({d_fin}) · {top['Contratista']}"
        res["widget_color"] = "#C93B2B"
        res["widget_bg"] = "rgba(201, 59, 43, 0.08)"
        if res["por_terminar"]:
            pt = res["por_terminar"][0]
            txt_d = "hoy" if pt["dias"] == 0 else f"en {pt['dias']}d"
            pills.append(f"🟠 Por terminar ({txt_d}): {pt['Tarea']}")
        if res["por_empezar"]:
            pe = res["por_empezar"][0]
            txt_d = "hoy" if pe["dias"] == 0 else f"en {pe['dias']}d"
            pills.append(f"🔵 Por empezar ({txt_d}): {pe['Tarea']}")
    elif res["por_terminar"]:
        top = res["por_terminar"][0]
        d_fin = top["Fin"].strftime("%d/%m/%Y") if top["Fin"] else ""
        cuando = "Vence HOY" if top["dias"] == 0 else f"Termina en {top['dias']} día(s)"
        res["widget_badge"] = "🟠 POR TERMINAR"
        res["widget_titulo"] = top["Tarea"]
        res["widget_detalle"] = f"{cuando} ({d_fin}) · {top['Contratista']}"
        res["widget_color"] = "#D98A2B"
        res["widget_bg"] = "rgba(217, 138, 43, 0.10)"
        if res["por_empezar"]:
            pe = res["por_empezar"][0]
            txt_d = "hoy" if pe["dias"] == 0 else f"en {pe['dias']}d"
            pills.append(f"🔵 Por empezar ({txt_d}): {pe['Tarea']}")
    elif res["por_empezar"]:
        top = res["por_empezar"][0]
        d_ini = top["Inicio"].strftime("%d/%m/%Y") if top["Inicio"] else ""
        cuando = "Inicia HOY" if top["dias"] == 0 else f"Inicia en {top['dias']} día(s)"
        res["widget_badge"] = "🔵 POR EMPEZAR"
        res["widget_titulo"] = top["Tarea"]
        res["widget_detalle"] = f"{cuando} ({d_ini}) · {top['Contratista']}"
        res["widget_color"] = "#2B6CB0"
        res["widget_bg"] = "rgba(43, 108, 176, 0.08)"
    elif res["en_curso_lista"]:
        top = res["en_curso_lista"][0]
        d_fin = f" (hasta {top['Fin'].strftime('%d/%m/%Y')})" if top["Fin"] else ""
        res["widget_badge"] = "🔵 EN EJECUCIÓN"
        res["widget_titulo"] = top["Tarea"]
        res["widget_detalle"] = f"En curso{d_fin} · {top['Contratista']}"
        res["widget_color"] = "#C85A32"
        res["widget_bg"] = "rgba(200, 90, 50, 0.08)"
    elif res["completadas"] == res["total"] and res["total"] > 0:
        res["widget_badge"] = "🟢 AL DÍA / COMPLETADO"
        res["widget_titulo"] = f"{res['completadas']} de {res['total']} tareas completadas"
        res["widget_detalle"] = "Todas las partidas registradas han concluido"
        res["widget_color"] = "#4A7C59"
        res["widget_bg"] = "rgba(74, 124, 89, 0.08)"

    res["pills_extra"] = pills[:2]
    return res



def normalizar_hex_color(color_str, default="#C85A32"):
    """Normaliza un string de color hexadecimal a formato '#RRGGBB'."""
    if not color_str:
        return default
    s = str(color_str).strip()
    if s.startswith("#"):
        s = s[1:]
    if len(s) == 3 and all(c in "0123456789abcdefABCDEF" for c in s):
        s = "".join(c * 2 for c in s)
    if len(s) == 6 and all(c in "0123456789abcdefABCDEF" for c in s):
        return f"#{s.upper()}"
    return default


def hex_a_rgb(color_str, default=(200, 90, 50)):
    """Convierte un color hexadecimal '#RRGGBB' a tupla RGB (r, g, b)."""
    hx = normalizar_hex_color(color_str, default="")
    if not hx:
        return default
    hx = hx.lstrip("#")
    return (int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16))


def oscurecer_hex_color(color_str, factor=0.82):
    """Oscurece un color hexadecimal multiplicando sus canales por factor (0..1)."""
    r, g, b = hex_a_rgb(color_str)
    r2 = max(0, min(255, int(round(r * factor))))
    g2 = max(0, min(255, int(round(g * factor))))
    b2 = max(0, min(255, int(round(b * factor))))
    return f"#{r2:02X}{g2:02X}{b2:02X}"


def aclarar_hex_color(color_str, factor=0.88):
    """Aclara un color hexadecimal mezclándolo hacia blanco según factor (0..1)."""
    r, g, b = hex_a_rgb(color_str)
    r2 = max(0, min(255, int(round(r + (255 - r) * factor))))
    g2 = max(0, min(255, int(round(g + (255 - g) * factor))))
    b2 = max(0, min(255, int(round(b + (255 - b) * factor))))
    return f"#{r2:02X}{g2:02X}{b2:02X}"


def preparar_logo_png_bytes(source=None, max_height=110):
    """
    Convierte una ruta de archivo, bytes o Data URL base64 de logo en bytes PNG
    optimizados para incrustar en Excel (openpyxl) y PDF (FPDF2).
    Retorna (png_bytes, (width, height)) o (None, (0, 0)).
    """
    import io
    try:
        from PIL import Image
    except Exception:
        return None, (0, 0)

    raw_bytes = None
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if isinstance(source, (bytes, bytearray)):
        raw_bytes = bytes(source)
    elif isinstance(source, str) and source.strip():
        s = source.strip()
        if s.startswith("data:image/"):
            try:
                header, b64_data = s.split(",", 1)
                if "svg+xml" not in header.lower():
                    raw_bytes = base64.b64decode(b64_data)
            except Exception:
                raw_bytes = None
        else:
            candidates = [
                s,
                os.path.join(repo_root, s),
                os.path.join(r"D:\cota-app", s),
            ]
            for cand in candidates:
                if cand and os.path.isfile(cand) and not cand.lower().endswith(".svg"):
                    try:
                        with open(cand, "rb") as f:
                            raw_bytes = f.read()
                        break
                    except Exception:
                        continue

    if not raw_bytes:
        for fallback_rel in ["Logo/studio_logo.png", "logo/studio_logo.png", "Logo/Logo Full.png", "logo/Logo Full.png"]:
            cand = os.path.join(repo_root, fallback_rel)
            if os.path.isfile(cand):
                try:
                    with open(cand, "rb") as f:
                        raw_bytes = f.read()
                    break
                except Exception:
                    continue

    if not raw_bytes:
        return None, (0, 0)

    try:
        with Image.open(io.BytesIO(raw_bytes)) as im:
            im = im.convert("RGBA")
            w, h = im.size
            if h > max_height and h > 0:
                ratio = max_height / float(h)
                w = max(1, int(round(w * ratio)))
                h = max_height
                im = im.resize((w, h), Image.Resampling.LANCZOS)
            out = io.BytesIO()
            im.save(out, format="PNG")
            return out.getvalue(), (w, h)
    except Exception:
        return None, (0, 0)


def obtener_marca_estudio():
    """
    Obtiene la configuración de marca del Estudio para el Branch actual.
    """
    import json
    import streamlit as st
    from cota.config import DEFAULT_BRAND_COLOR, DEFAULT_LOGO_PATH, STUDIO_BRANDING_FILE, get_secret

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    branding_file = os.path.join(repo_root, STUDIO_BRANDING_FILE)

    data_file = {}
    if os.path.isfile(branding_file):
        try:
            with open(branding_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    data_file = loaded
        except Exception:
            data_file = {}

    cfg_session = {}
    try:
        if "config_estudio" in st.session_state:
            df_cfg = st.session_state["config_estudio"]
            if isinstance(df_cfg, pd.DataFrame) and not df_cfg.empty and "Clave" in df_cfg.columns and "Valor" in df_cfg.columns:
                for _, r in df_cfg.iterrows():
                    k = str(r.get("Clave", "")).strip()
                    v = str(r.get("Valor", "")).strip()
                    if k and v and v.lower() != "nan":
                        cfg_session[k] = v
    except Exception:
        pass

    mem = {}
    try:
        if "studio_branding" in st.session_state and isinstance(st.session_state["studio_branding"], dict):
            mem = st.session_state["studio_branding"]
    except Exception:
        mem = {}

    sec_studio = str(
        get_secret("Studio Name", "")
        or get_secret("STUDIO_NAME", "")
        or get_secret("Studio_Name", "")
        or get_secret("studio_name", "")
        or ""
    ).strip()
    sec_color = str(get_secret("BRAND_COLOR", "") or "").strip()
    sec_logo = str(get_secret("LOGO_IMAGE", "") or "").strip()

    studio_name = (
        mem.get("studio_name")
        or cfg_session.get("studio_name")
        or data_file.get("studio_name")
        or sec_studio
        or ""
    )
    raw_color = (
        mem.get("brand_color")
        or cfg_session.get("brand_color")
        or data_file.get("brand_color")
        or sec_color
        or DEFAULT_BRAND_COLOR
    )
    brand_color = normalizar_hex_color(raw_color, DEFAULT_BRAND_COLOR)
    logo_path = (
        mem.get("logo_path")
        or cfg_session.get("logo_path")
        or data_file.get("logo_path")
        or sec_logo
        or DEFAULT_LOGO_PATH
    )
    logo_b64_override = mem.get("logo_base64") or cfg_session.get("logo_base64") or data_file.get("logo_base64") or ""

    if logo_b64_override and str(logo_b64_override).startswith("data:image/"):
        logo_base64 = str(logo_b64_override)
        png_bytes, logo_size = preparar_logo_png_bytes(logo_base64)
        if not png_bytes:
            png_bytes, logo_size = preparar_logo_png_bytes(logo_path)
    else:
        logo_base64 = get_image_base64(logo_path)
        png_bytes, logo_size = preparar_logo_png_bytes(logo_path)

    brand_dark_color = oscurecer_hex_color(brand_color, 0.84)
    brand_soft_color = aclarar_hex_color(brand_color, 0.90)

    return {
        "studio_name": str(studio_name).strip(),
        "brand_color": brand_color,
        "brand_hex": brand_color.lstrip("#"),
        "brand_rgb": hex_a_rgb(brand_color),
        "brand_dark_color": brand_dark_color,
        "brand_dark_hex": brand_dark_color.lstrip("#"),
        "brand_dark_rgb": hex_a_rgb(brand_dark_color),
        "brand_soft_color": brand_soft_color,
        "logo_path": logo_path,
        "logo_base64": logo_base64,
        "logo_png_bytes": png_bytes,
        "logo_size": logo_size,
    }


def guardar_marca_estudio(studio_name=None, brand_color=None, uploaded_logo_bytes=None, uploaded_logo_name=None, reset_logo=False):
    """
    Guarda la configuración de marca del Estudio en el Branch actual (`studio_branding.json`),
    guarda el archivo de logo importado en `Logo/studio_logo.png` (si se subió uno) y
    actualiza `st.session_state["studio_branding"]` y `st.session_state["config_estudio"]`.
    """
    import json
    import streamlit as st
    from cota.config import DEFAULT_BRAND_COLOR, DEFAULT_LOGO_PATH, STUDIO_BRANDING_FILE

    actual = obtener_marca_estudio()
    nuevo_nombre = str(studio_name).strip() if studio_name is not None else actual["studio_name"]
    nuevo_color = normalizar_hex_color(brand_color, actual["brand_color"] or DEFAULT_BRAND_COLOR) if brand_color is not None else actual["brand_color"]
    nuevo_logo_path = DEFAULT_LOGO_PATH if reset_logo else actual["logo_path"]
    nuevo_logo_b64 = ""

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logo_dir = os.path.join(repo_root, "Logo")
    os.makedirs(logo_dir, exist_ok=True)
    if reset_logo:
        for _tmp_logo in ("studio_logo.png", "studio_logo.svg"):
            _p = os.path.join(logo_dir, _tmp_logo)
            if os.path.isfile(_p):
                try:
                    os.remove(_p)
                except Exception:
                    pass

    if uploaded_logo_bytes:
        ext = os.path.splitext(str(uploaded_logo_name or "studio_logo.png"))[1].lower()
        if ext == ".svg":
            target_rel = "Logo/studio_logo.svg"
            target_abs = os.path.join(repo_root, target_rel)
            try:
                with open(target_abs, "wb") as f:
                    f.write(uploaded_logo_bytes)
                nuevo_logo_path = target_rel
                b64_str = base64.b64encode(uploaded_logo_bytes).decode("ascii")
                nuevo_logo_b64 = f"data:image/svg+xml;base64,{b64_str}"
            except Exception:
                pass
        else:
            png_bytes, _ = preparar_logo_png_bytes(uploaded_logo_bytes, max_height=240)
            save_bytes = png_bytes if png_bytes else uploaded_logo_bytes
            target_rel = "Logo/studio_logo.png"
            target_abs = os.path.join(repo_root, target_rel)
            try:
                with open(target_abs, "wb") as f:
                    f.write(save_bytes)
                nuevo_logo_path = target_rel
                b64_str = base64.b64encode(save_bytes).decode("ascii")
                nuevo_logo_b64 = f"data:image/png;base64,{b64_str}"
            except Exception:
                pass

    payload = {
        "studio_name": nuevo_nombre,
        "brand_color": nuevo_color,
        "logo_path": nuevo_logo_path,
    }
    if nuevo_logo_b64:
        payload["logo_base64"] = nuevo_logo_b64

    branding_file = os.path.join(repo_root, STUDIO_BRANDING_FILE)
    try:
        with open(branding_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    try:
        st.session_state["studio_branding"] = payload
        if "config_estudio" in st.session_state and isinstance(st.session_state["config_estudio"], pd.DataFrame):
            df_cfg = st.session_state["config_estudio"].copy()
            for k, v in [("studio_name", nuevo_nombre), ("brand_color", nuevo_color), ("logo_path", nuevo_logo_path)]:
                if not df_cfg.empty and "Clave" in df_cfg.columns and (df_cfg["Clave"] == k).any():
                    df_cfg.loc[df_cfg["Clave"] == k, "Valor"] = v
                else:
                    df_cfg = pd.concat([df_cfg, pd.DataFrame([{"Clave": k, "Valor": v}])], ignore_index=True)
            st.session_state["config_estudio"] = df_cfg
    except Exception:
        pass

    return obtener_marca_estudio()
