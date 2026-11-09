# LB Studio // Base de Datos Inicial - COTA APP

Este directorio contiene la estructura y formato oficial de la base de datos de **COTA APP**, completamente limpia y vacía (sin proyectos de ejemplo ni datos de prueba de Cota App), lista para ser utilizada por **LB Studio** como el primer estudio de diseño en probar el sistema.

---

## 📁 Archivos Disponibles

1. **`BD_COTA_APP_PRUEBAS.xlsx`**: Archivo Excel con el nombre nativo estándar reconocido por la aplicación.
2. **`BD_LB_STUDIO.xlsx`**: Copia idéntica nombrada para el estudio.
3. **`tablas_csv/`**: Carpeta con los 20 esquemas en formato CSV independiente (con codificación UTF-8), útil para importar a Google Sheets, bases SQL u otros sistemas.

---

## 🗂️ Estructura de las 20 Tablas (Hojas)

| # | Hoja / Tabla | Descripción | Columnas Principales |
|---|---|---|---|
| 1 | **`proyectos`** | Registro maestro de proyectos de arquitectura e interiorismo | `Nombre`, `Cliente`, `Tipo_Proyecto`, `Encargado`, `Ubicación`, `Estado`, `Inicio`, `Fin`, `Presupuesto`, `Honorarios_Diseno`, etc. |
| 2 | **`tasks`** | Cronograma detallado de partidas constructivas y tareas de obra | `Proyecto`, `Partida`, `Tarea`, `Especialidad`, `Contratista`, `Estado`, `Inicio`, `Fin`, `Presupuesto`, etc. |
| 3 | **`maestro`** | Directorio global de contratistas y proveedores | `ID_Contratista`, `Especialidad`, `Ubicación_Base`, `Notas` |
| 4 | **`historial`** | Evaluaciones de desempeño de contratistas (1-5 estrellas) | `ID_Contratista`, `Estado`, `Responsable` |
| 5 | **`fases`** | Las etapas del flujo de diseño (Levantamiento, Moodboard, 3D, Renders, Planos) | `Proyecto`, `Orden`, `Fase`, `Etapa`, `Estado`, `Avance_Pct`, `Aprobado_Cliente` |
| 6 | **`materiales`** | Especificaciones FF&E (Mobiliario, Iluminación, Revestimientos, Griferías) | `Proyecto`, `Ambiente`, `Categoria`, `Material`, `Cantidad`, `Precio_Unit_Estimado`, `Costo_Real`, `Proveedor`, `Estado` |
| 7 | **`cobros`** | Hitos financieros y facturación al cliente | `Proyecto`, `Hito`, `Tipo`, `Monto_Pactado`, `Fecha_Vencimiento`, `Monto_Cobrado`, `Fecha_Cobro`, `Estado` |
| 8 | **`pagos_maestros`** | Registro de desembolsos a contratistas y proveedores por partida | `Proyecto`, `Partida`, `Contratista`, `Fecha`, `Monto`, `Tipo` |
| 9 | **`partidas_info`** | Resumen ejecutivo por partida de obra | `Proyecto`, `Nombre_Partida`, `Monto_Pactado`, `Contratista`, `Estado` |
| 10 | **`gg_log`** | Caja chica y gastos generales de obra / supervisión | `Proyecto`, `Fecha`, `Responsable`, `Concepto`, `Monto` |
| 11 | **`logistica`** | To-Do list y pendientes operativos del proyecto | `Proyecto`, `Categoria`, `Tarea`, `Responsable`, `Check` |
| 12 | **`ice_sesiones`** | Actas de reunión (con cliente, contratistas o equipo interno) | `ID_Sesion`, `Proyecto`, `Nombre_Sesion`, `Tipo_Reunion`, `Fecha_Prog`, `Lider` |
| 13 | **`ice_invitados`** | Asistencia a reuniones | `ID_Sesion`, `Nombre`, `Empresa`, `Cargo`, `Asistencia` |
| 14 | **`ice_acuerdos`** | Acuerdos y compromisos formalizados en reuniones | `ID_Sesion`, `Descripcion`, `Responsable`, `Acuerdo` |
| 15 | **`entregables_planos`** | Control de planos técnicos, revisiones y enlaces en la nube | `Proyecto`, `Especialidad`, `Nombre_Entregable`, `Revision`, `Estado`, `Link` |
| 16 | **`pendientes_entrega`** | Punch List / Observaciones previas a la entrega | `Proyecto`, `Ambiente`, `Elemento`, `Descripcion`, `Prioridad`, `Estado` |
| 17 | **`ingresos_socios`** | Distribución de honorarios y utilidades entre directores | `Fecha`, `Proyecto`, `Socio`, `Categoria`, `Monto` |
| 18 | **`observaciones_municipales`** | Registro de trámites de licencias y expedientes | `Proyecto`, `Nro_Observacion`, `Especialidad`, `Descripcion`, `Estado` |
| 19 | **`entrega_dossier`** | Expediente técnico y dossier de fin de obra | `Proyecto`, `Especialidad`, `Documento`, `Estado` |
| 20 | **`entrega_unidades`** | Inspección y entrega formal de ambientes | `Proyecto`, `Unidad`, `Propietario`, `Estado`, `Fecha_Entrega` |

---

## 🚀 Cómo Empezar a Usar esta Base de Datos

### Opción A: Probar localmente
1. Copie el archivo `BD_COTA_APP_PRUEBAS.xlsx` de esta carpeta a la raíz del repositorio (`D:\cota-app\BD_COTA_APP_PRUEBAS.xlsx`) reemplazando o respaldando el anterior.
2. Inicie la aplicación con `streamlit run app.py`.
3. Podrá dar de alta su primer proyecto desde el módulo **"Nuevo Proyecto"**.

### Opción B: Sincronización en la Nube (Google Drive / Sheets)
1. Suba el archivo `BD_COTA_APP_PRUEBAS.xlsx` a su unidad de Google Drive del estudio.
2. Si utiliza la integración con Service Account (`GSHEETS_URL`), vincule el ID o URL del documento en `.streamlit/secrets.toml`.
