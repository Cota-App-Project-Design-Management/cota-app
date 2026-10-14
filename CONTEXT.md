# COTA APP - PROJECT & DESIGN MANAGEMENT (v1.0)
- **Objetivo:** SaaS comercial de gestión de proyectos, presupuestos, materiales y contratistas para estudios de arquitectura, diseño de interiores y remodelación.
- **Reglas de esta versión:**
  1. Sin Chatbot ni API de Gemini (`google.generativeai` eliminado).
  2. Sin módulos internos privados (eliminados el tab y vistas de VDC Hub, Matriz POP, y las tablas `pop_matrix`, `metricas_cfg`, `metricas_log`).
  3. Nombres dinámicos: Directores/Socios configurables desde el sidebar (`lista_socios`), sin nombres propios fijos ("Alvaro"/"Rodrigo") en el código.
  4. Estética oscura estilo Palantir (`#070B14`, `#0d1424`, `#1e293b`, `#00E5FF`). Sin emojis decorativos salvo los semáforos de estado (`🟡`, `🔵`, `🟢`, `🔴`, `⚪`).
