# COTA APP // Diseño de Interiores, Arquitectura & Obra

Software de gestión integral de diseño, especificaciones FF&E, entregables técnicos, obra y finanzas diseñado para estudios pequeños y medianos de **Arquitectura y Diseño de Interiores**.

## ✨ Características Principales

### 1. Portafolio Ejecutivo del Estudio (6 Vistas Globales)
- **🗂️ Portafolio Activo**: KPIs ejecutivos del estudio (Cartera Activa, Avance de Diseño, FF&E por Aprobar, Hitos por Cobrar) y tarjetas de proyectos con acceso directo a la Ficha Integral.
- **🗓️ Agenda & Cronograma**: Calendario mensual de entregas de diseño, tareas de obra y próximos vencimientos.
- **🛋️ Catálogo FF&E Global**: Buscador transversal de mobiliario, iluminación, revestimientos y griferías en todos los proyectos.
- **👷 Directorio de Contratistas**: Evaluación automática por estrellas (1–5 ★), especialidades, historial de cotizaciones y sugerencia inteligente según disponibilidad.
- **💰 Finanzas del Estudio**: Estado de resultados por proyecto (Cobrado vs. Gastado vs. Margen Neto), gráfico comparativo y registro de gastos fijos de oficina.
- **📦 Archivo Histórico**: Proyectos cerrados con opción de reactivación o depuración en cascada.

### 2. Ficha Integral por Proyecto (8 Módulos Especializados)
1. **📐 Resumen & Brief**: Ficha técnica (Cliente, Tipología, Área $\text{m}^2$, Estilo, Encargado), panel visual de avance de las 8 fases y balance económico.
2. **🎨 Fases de Diseño**: Cronograma de las 8 etapas del ciclo de diseño y obra con aprobación de cliente y diagrama Gantt interactivo.
3. **🛋️ FF&E y Acabados por Ambiente**: Planilla de especificaciones por ambiente (*Sala, Comedor, Cocina, Dormitorios, etc.*) con cálculo automático de `Costo_Estimado = Cantidad × P. Unitario` y desglose presupuestal por ambiente.
4. **📋 Planos y Entregables**: Control de revisiones (`Rev 0`, `Rev A`, etc.), estados de aprobación y enlaces a expediente técnico en la nube.
5. **🏗️ Obra y Partidas**: Gestión de partidas constructivas, presupuestos pactados, pagos a contratistas y programación de tareas.
6. **💰 Cobros y Finanzas**: Plan de hitos de cobro al cliente (Anticipo, Hitos de Diseño, Supervisión, Liquidación) y caja chica de obra.
7. **📝 Actas de Reunión**: Importador inteligente de notas de reunión / Google Meet, control de asistencia, acuerdos y exportación formal a PDF con membrete del estudio.
8. **🔍 Punch List**: Inspección de observaciones y detalles finales por ambiente previo a la entrega formal.

## 🎨 Identidad Visual: *Warm Architectural Atelier*
- **Fondo Principal**: Blanco Hueso / Papel Arquitectónico (`#F7F4EF`)
- **Superficies Secundarias**: Piedra Travertino (`#EFECE6`)
- **Acento Principal**: Rojo Arcilla / Terracota (`#C85A32`)
- **Tipografía**: `Plus Jakarta Sans` & `JetBrains Mono`

## 🚀 Ejecución Local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 🧪 Pruebas Automatizadas

```bash
pytest -v -o pythonpath=. tests
```