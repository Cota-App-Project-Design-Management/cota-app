import streamlit as st


def get_secret(key, default=None):
    """Obtiene un valor de st.secrets de forma segura sin lanzar StreamlitSecretNotFoundError."""
    try:
        val = st.secrets.get(key, default)
        return val if val is not None else default
    except Exception:
        return default


# Identidad y Branding
DEFAULT_APP_TITLE = "COTA APP"
DEFAULT_SUBTITLE = "PROJECT & DESIGN MANAGEMENT"
DEFAULT_LOGO_PATH = "Logo2.png"
DEFAULT_ICON_PATH = "icono.png"

# Moneda y Localización
DEFAULT_CURRENCY = "S/"
DEFAULT_TIMEZONE = "America/Lima"

# Catálogo de Estados de Proyecto
STATUS_PROYECTOS = ["🟡 Planificación", "🔵 En Proceso", "🟢 Completado"]

# Tipos de Proyecto especializados en Arquitectura e Interiorismo
TIPOS_PROYECTO = [
    "Interiorismo Residencial",
    "Interiorismo Comercial",
    "Arquitectura Residencial",
    "Remodelación / Ampliación",
    "Mobiliario a Medida",
    "Consultoría / Otro"
]

# Fases canónicas del ciclo de vida de un proyecto de diseño/arquitectura
FASES_CANONICAS = [
    {"Orden": 1, "Fase": "01. Levantamiento & Brief", "Etapa": "Conceptual", "Dias": 7},
    {"Orden": 2, "Fase": "02. Concepto & Moodboard", "Etapa": "Conceptual", "Dias": 10},
    {"Orden": 3, "Fase": "03. Anteproyecto / Distribución", "Etapa": "Diseño", "Dias": 14},
    {"Orden": 4, "Fase": "04. Desarrollo de Diseño & 3D", "Etapa": "Diseño", "Dias": 18},
    {"Orden": 5, "Fase": "05. Expediente Técnico & Planos", "Etapa": "Documentación", "Dias": 15},
    {"Orden": 6, "Fase": "06. Presupuesto & Compras (FF&E)", "Etapa": "Adquisiciones", "Dias": 10},
    {"Orden": 7, "Fase": "07. Ejecución / Obra / Montaje", "Etapa": "Construcción", "Dias": 30},
    {"Orden": 8, "Fase": "08. Cierre & Entrega Final", "Etapa": "Cierre", "Dias": 7},
]

STATUS_FASES = [
    "⚪ No iniciada",
    "🟡 En desarrollo",
    "🔵 En revisión cliente",
    "🟢 Aprobada cliente"
]

# Tareas de Obra / Ejecución
STATUS_TASKS = [
    "🟡 Planificado",
    "🔵 En Proceso",
    "⚪ En espera",
    "🟢 Completado a tiempo",
    "🔴 Completado con retraso"
]

# Ambientes estándar para Interiorismo y Arquitectura
AMBIENTES_DEFAULT = [
    "General / Toda la casa",
    "Sala / Estar",
    "Comedor",
    "Cocina",
    "Dormitorio Principal",
    "Dormitorio 2",
    "Dormitorio 3",
    "Baño Principal",
    "Baño Visitas",
    "Terraza / Balcón",
    "Oficina / Estudio",
    "Fachada / Exterior",
    "Recepción / Lobby"
]

# Categorías FF&E (Furniture, Fixtures & Equipment)
CATEGORIAS_FFE = [
    "Mobiliario Fijo (Carpintería)",
    "Mobiliario Suelto",
    "Iluminación",
    "Revestimientos y Acabados",
    "Grifería y Sanitarios",
    "Textiles y Cortinas",
    "Decoración y Arte",
    "Equipamiento / Electro",
    "Materiales de Obra",
    "Varios / Misceláneos"
]

STATUS_FFE = [
    "⚪ Propuesto",
    "🟡 En Cotización",
    "🔵 Aprobado Cliente",
    "🟣 En Producción",
    "🟠 En Despacho",
    "🟢 Instalado / Recibido"
]

# Cobros e Hitos Financieros hacia el Cliente
TIPOS_COBRO = [
    "Honorarios de Diseño",
    "Supervisión de Obra",
    "FF&E / Mobiliario",
    "Materiales",
    "Adicional Aprobado",
    "Liquidación Final"
]

STATUS_COBROS = [
    "🟡 Pendiente",
    "🟢 Cobrado",
    "🔴 Vencido"
]

# Punch List / Pendientes de Entrega
STATUS_PUNCH = [
    "🔴 Pendiente",
    "🟡 En Corrección",
    "🟢 Subsanado",
    "⚪ Descartado"
]

PRIORIDADES_PUNCH = ["Alta", "Media", "Baja"]

# Tipos de Reunión
TIPOS_REUNION = [
    "Con Cliente",
    "Con Contratistas",
    "Con Especialistas",
    "Interna de Equipo",
    "Supervisión en Obra"
]

# Unidades de medida
UNIDADES_MEDIDA = ["und", "m2", "m", "m3", "kg", "glb", "juego", "rollo", "bolsa"]

# Especialidades de Contratistas
ESPECIALIDADES_DEFAULT = [
    "Arquitectura",
    "Diseño Interior",
    "Carpintería / Madera",
    "Iluminación",
    "Inst. Eléctricas",
    "Inst. Sanitarias",
    "Pintura y Acabados",
    "Drywall / Tabiquería",
    "Cerrajería / Metal",
    "Vidriería / Mamparas",
    "Mármol / Cuarzo / Granito",
    "Climatización / Venti",
    "Equipamiento / Audio",
    "Albañilería General",
    "Otros"
]
