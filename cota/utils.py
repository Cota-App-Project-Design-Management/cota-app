"""
Utilidades auxiliares, formateo de datos, motor de fechas, parsing y sugerencias.
"""

import base64
import datetime
import io
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


def get_image_base64(path):
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


def analizar_tareas_proyecto(df_tasks: pd.DataFrame, proy_name: str, fecha_hoy: datetime.date | None = None) -> dict:
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

