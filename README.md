# 📚 Base de Conocimiento Técnica — IoT Fenster

Plataforma integral de gestión de conocimiento técnico, soporte SAT de obra y búsqueda semántica para dispositivos IoT Fenster / MySmartWindow. Permite indexar manuales PDF, sincronizar automáticamente videos y tutoriales de YouTube, visualizar documentos con deep-linking exacto a página, generar Packs de Obra offline en ZIP con un solo clic, **simular y generar esquemas eléctricos unifilares 230V interactivos**, experimentar con el **Laboratorio Integral IoT + SCADA con física de persiana continua**, diagnosticar averías telefónicas mediante un **asistente guiado de Triage SAT**, gestionar asistencias técnicas en un **Mini-CRM con contacto directo por WhatsApp y llamada**, y emitir **partes oficiales SAT y órdenes de RMA en PDF A4 vectorial**.

---

## 📸 Capturas de Pantalla

### 🔍 1. Buscador Inteligente y Resultados Híbridos
Búsqueda instantánea con filtros por dispositivo, categoría, chips de temas frecuentes y visualización combinada de PDFs técnicos y vídeos tutoriales.

![Buscador Principal](docs/screenshots/02_buscador_principal.png)
![Resultados de Búsqueda](docs/screenshots/03_busqueda_resultados.png)

---

### 📄 2. Visor PDF Integrado (Deep-Linking)
Abre directamente la página relevante donde se encontró la coincidencia, con herramientas de zoom, descarga directa y descarga de Pack de Obra.

![Visor PDF Integrado](docs/screenshots/09_visor_pdf.png)

---

### 📦 3. Packs de Obra e Instalación (Descarga Offline ZIP)
Diseñado para técnicos e instaladores en zonas sin cobertura móvil (sótanos, chalets). Permite descargar con un solo clic todos los manuales y la guía de enlaces a vídeos de cada dispositivo en un archivo ZIP.

![Modal Pack de Obra](docs/screenshots/06_pack_obra_modal.png)

---

### 🎥 4. Biblioteca de Recursos & YouTube Auto-Sync
Gestión centralizada de manuales PDF y vídeos de YouTube sincronizados automáticamente con el canal oficial [@MySmartWindow](https://www.youtube.com/@MySmartWindow) cada 24 horas en segundo plano.

![Biblioteca de Manuales](docs/screenshots/04_biblioteca_manuales.png)
![Biblioteca de Videos YouTube](docs/screenshots/05_biblioteca_videos.png)

---

### 👥 5. Seguridad y Gestión de Accesos (RBAC)
Control de acceso basado en roles (`admin`, `tecnico`, `comercial`) con autenticación JWT, restricción de descarga por nivel de confidencialidad y panel de administración de usuarios.

![Acceso al Sistema](docs/screenshots/01_login.png)
![Gestión de Usuarios](docs/screenshots/07_gestion_usuarios.png)
![Indexar Documentación](docs/screenshots/08_indexar_documentacion.png)

---

### 🌗 6. Modo Claro / Oscuro
Selector de tema integrado con persistencia en `localStorage` y detección automática de preferencia del sistema. Disponible desde la pantalla de login y la cabecera principal.

![Modo Claro - Login](docs/screenshots/10_modo_claro_login.png)
![Modo Claro - Buscador](docs/screenshots/11_modo_claro_buscador.png)
![Modo Claro - Biblioteca](docs/screenshots/14_modo_claro_biblioteca.png)

---

### 🔌 7. Esquemas Eléctricos 230V Interactivos y Modo Ampliado
Simulador visual unifilar 230V para instaladores en obra con animación de corriente activa, inversión de fases (Swap Giro), selección de motores mecánicos de 4 hilos y **Modo Ampliado / Pantalla Completa** con controles de maniobra en vivo integrados.

![Simulador Eléctrico 230V Interactivo](docs/screenshots/16_esquemas_electricos_230v.png)
![Esquema en Modo Pantalla Completa](docs/screenshots/17_esquema_fullscreen.png)

---

### 🩺 8. Asistente Guiado de Triage SAT (Soporte Telefónico)
Árbol de diagnóstico técnico guiado paso a paso con cálculo de probabilidad de acierto (hasta 98%), checklist de comprobación en obra, botón directo para enviar indicaciones por WhatsApp y derivación inmediata a Ticket SAT.

![Asistente Guiado de Triage SAT](docs/screenshots/18_triage_sat_wizard.png)

---

### 🗂️ 9. Mini-CRM de Tickets SAT e Informes Oficiales RMA en PDF
Gestión completa del ciclo de vida de incidencias técnicas en obra: panel de métricas KPI, filtros dinámicos por estado, botones de contacto directo (WhatsApp y llamada telefónica), y exportación vectorial oficial de partes de asistencia y órdenes de RMA en formato A4 con casillas de firma.

![Mini-CRM de Tickets SAT](docs/screenshots/19_mini_crm_tickets_sat.png)
![Parte Oficial SAT y Orden de RMA en PDF](docs/screenshots/20_parte_sat_pdf.png)

---

## ✨ Características Principales

- **Búsqueda Avanzada en Español con Tesauro SAT**: Motor PostgreSQL con `tsvector`, diccionarios de derivación morfológica (stemming), insensibilidad a acentos y **Tesauro Técnico de Sinónimos SAT** (`data/thesaurus_manuales.ths`) con más de 500 términos mapeados para resolver averías, problemas de conectividad (CG-NAT, WMF, aislamiento de clientes), procedimientos de reset y equivalencias entre marcas partner.
- **🩺 Asistencia SAT Inteligente (Cuestionario en 4 Bloques & Dictamen en Vivo)**: Sistema de diagnóstico interactivo guiado paso a paso en 4 bloques técnicos (Identificación de Partner y Producto, Comportamiento y Matriz de Inferencia Físico vs App, Red Wi-Fi y Sistema Móvil, Contexto Temporal y Checklist de Descarte). Proporciona cálculo algorítmico de certeza, explicación de causa raíz, protocolo de acción con descarte automático, enlace directo al manual PDF oficial, descarga directa del Parte Oficial SAT en PDF sin requerir email, y botón de exportación a WhatsApp.
- **🔌 Esquemas Eléctricos 230V Interactivos y Modo Pantalla Completa**: Diagrama unifilar vectorial SVG dinámico para instaladores en obra. Modela paso de corriente alterna, relés internos K1/K2, sentido de giro del rotor, inversión de fases (Swap Giro), selector de dispositivos (Connect-1, Connect-2, C-Wall, C-Pulsar, etc.), selector de motores mecánicos de 4 hilos, descarga del diagrama en `.SVG` y **Modo Ampliado / Pantalla Completa** (`⛶ Ver en Grande` o tecla `Escape`) con controles de maniobra en vivo accesibles a pantalla completa.
- **🗂️ Mini-CRM de Tickets SAT e Historial de Averías**: Módulo integral de gestión de incidencias de soporte con persistencia en PostgreSQL (`tickets_sat`), numeración correlativa anual (`SAT-2026-XXXX`), panel de KPIs en vivo (Total, Resueltos, En Espera, Pendientes de RMA), filtros dinámicos por estado/búsqueda, y **botones de acción directa para llamar por teléfono (`tel:`) o abrir chat de WhatsApp (`wa.me`)** con el instalador con un solo clic.
- **📄 Exportador Oficial de Partes SAT y Órdenes de RMA en PDF (A4)**: Generador vectorial profesional con **ReportLab** que crea partes de asistencia técnica A4 listos para imprimir o adjuntar al proveedor. Incluye membrete corporativo, datos de distribuidor y obra, desglose pericial de síntomas/causas/soluciones, dictamen de procedencia RMA y casillas de firma física y digital para técnico e instalador.
- **📧 Despachador de Correos Electrónicos (`email_sender.py`)**: Módulo asíncrono para envío de informes técnicos con el PDF adjunto mediante SMTP o modo simulado.
- **Sincronizador Automático de Manuales (`sync_manuales.py`)**: Herramienta CLI y hook de arranque que detecta automáticamente nuevos archivos PDF en `manuales/`, extrae el contenido textual sanitizado y actualiza la base de datos con metadatos de catálogo enriquecidos y niveles de acceso RBAC.
- **Deep-Linking a Páginas PDF**: Cada resultado apunta a la página exacta donde se localizó el término.
- **Sincronización Automática con YouTube**: Cron de fondo que rastrea las novedades del canal `@MySmartWindow` e indexa títulos, descripciones y subtítulos.
- **OCR Integrado para Escaneos**: Extracción de texto con Tesseract OCR (`tesseract-ocr-spa`) para páginas sin texto seleccionable.
- **Packs de Obra Offline**: Generación al vuelo de paquetes ZIP con todos los recursos de un dispositivo específico para instalaciones sin internet.
- **Control de Acceso Basado en Roles (RBAC)**:
  - `admin`: Acceso total, subida de archivos, reindexación, administración de usuarios y tickets SAT.
  - `tecnico`: Acceso a manuales técnicos y comerciales, buscador, visor, esquemas 230V, asistencia SAT y mini-CRM SAT con exportación PDF.
  - `comercial`: Acceso restringido exclusivamente a documentación pública y catálogo comercial.
- **Seguridad Reforzada**: Tokens JWT con rotación, protección contra Path Traversal, mitigación de ataques XSS con sanitización estricta, rate-limiting contra fuerza bruta en login y ejecución en contenedores sin privilegios de root.
- **Tema Claro / Oscuro**: Selector de apariencia con detección automática de preferencia del sistema y persistencia en `localStorage`.
- **Búsqueda Insensible a Acentos**: Configuración `spanish_unaccent` en PostgreSQL para que búsquedas como `instalacion` e `INSTALACIÓN` devuelvan los mismos resultados.
- **Rendimiento FTS con Índices GIN y Columnas Generadas**: manuales, páginas, vídeos, fragmentos de vídeo y tickets SAT tienen columnas `tsvector` calculadas como `GENERATED ALWAYS ... STORED` e indexadas mediante GIN (más índices trigram en tickets), eliminando el recálculo en tiempo de consulta para búsquedas instantáneas a gran escala.
- **Páginas 403 / 404 Amigables**: En lugar de respuestas JSON crudas de backend, el sistema sirve páginas HTML con diseño corporativo IoT Fenster (soporte claro/oscuro, badges de rol y enlace al buscador) cuando un comercial intenta acceder a documentación técnica confidencial o si el archivo no existe.

---

## 🧪 Suite de Tests Automatizados (Pytest)

El proyecto cuenta con una batería de pruebas de regresión y seguridad para endpoints críticos de control de acceso (RBAC), prevención de brechas y negociación de contenido:

```bash
# Ejecutar la suite completa de tests
pytest
```

**185 tests, ~26 segundos.** Son dos familias con requisitos distintos:

- `tests/unit` y `tests/api` no necesitan nada levantado: el arranque (`init_db()`) se neutraliza y la capa de datos está mockeada.
- `tests/integration` corre contra **PostgreSQL de verdad**, sobre una base de datos de pruebas desechable, porque lo que comprueban —claves foráneas, `SET NULL`, claves primarias compuestas, índices de texto completo— no existe en un mock. Si PostgreSQL no está accesible, se omiten solos en vez de fallar.

En ningún caso se escribe en la base de datos de desarrollo.

Los ficheros de `tools/manual_checks/` se llaman `test_*.py` pero **no forman parte de la suite** (`pytest.ini` fija `testpaths=tests`): son scripts de verificación manual que exigen un servidor real en `localhost:8000` y escriben datos de verdad. Ejecútalos a mano, nunca en CI.

### Cobertura de Tests de Seguridad (`tests/api/test_rbac.py`, `tests/api/test_security.py`)
- **`test_comercial_no_accede_a_tecnico`**: Verifica que un usuario con rol `comercial` recibe HTTP 403 al intentar acceder a manuales clasificados como `tecnico`.
- **`test_comercial_accede_a_publico`**: Comprueba que el rol `comercial` puede consultar sin restricciones los manuales públicos.
- **`test_tecnico_accede_a_tecnico`** y **`test_admin_accede_a_tecnico`**: Garantiza acceso completo para el personal técnico y administradores.
- **`test_path_traversal_bloqueado`**: Prueba múltiples payloads maliciosos (`../`, `..%2F`, `..\\`, `/etc/passwd`, etc.) garantizando que nunca se exponen rutas fuera de `manuales/`.
- **`test_archivo_huerfano_en_disco_no_se_sirve_sin_registro_bd`**: Valida el principio *fail-closed*, asegurando que archivos huérfanos en disco no registrados en BD devuelven 404 en lugar de saltarse el control de acceso.

### Cobertura de Tests de Sinónimos Técnicos (`tests/unit/test_sinonimos.py`)
- **`test_carga_tesauro`**: Valida la integridad sintáctica del archivo `.ths` (más de 500 términos y 80 conceptos).
- **`test_averias_sat_excel`**: Comprueba la expansión de síntomas de avería (`no enciende`, `parpadea constantemente`, `se mueven solas`, `modo candado`, `finales de carrera`).
- **`test_marcas_y_dispositivos_cruzados`**: Comprueba correlación de marcas (`essential+` -> `connect-1`, `sentry` -> `connect-2`, `wave 3` -> `c-wall`, etc.).
- **`test_conectividad_y_red`**: Valida expansión de `cgnat`, `digi plus`, `aislamiento de clientes`, `multicast`, `modo ap`.
- **`test_tolerancia_a_acentos_y_diacriticos`**: Garantiza que consultas con o sin tildes expanden idénticamente.
- **`test_ip_cliente_con_proxy_inverso`**: Comprueba que el limitador de tasa extrae correctamente la IP real mediante `X-Forwarded-For` ante proxies inversos (Nginx, Traefik, Cloudflare).
- **`test_comercial_no_accede_a_miniatura_tecnica`**: Valida que la generación de previsualizaciones y miniaturas también respeta los niveles de confidencialidad.
- **`test_error_html_para_navegador_y_json_para_api`**: Valida la negociación de contenido (`Accept: text/html` devuelve la plantilla visual corporativa y `Accept: application/json` devuelve JSON estructurado).
- **`test_admin_requerido_para_gestion_usuarios`**: Asegura que los endpoints de altas, bajas y cambios de roles están restringidos exclusivamente al rol `admin`.

### Cobertura de Tests de Mini-CRM SAT y Exportador PDF (`tests/api/test_tickets_sat.py`)
- **`test_tecnico_puede_crear_y_listar_ticket`**: Valida la creación de incidencias en PostgreSQL, asignación correlativa de código (`SAT-2026-0001`), persistencia de campos técnicos y filtrado en lista.
- **`test_tecnico_puede_actualizar_estado_ticket`**: Comprueba transiciones de ciclo de vida (`en_espera`, `resuelto`, `rma_pendiente`, `descartado`) y actualización de notas técnicas.
- **`test_comercial_bloqueado_en_tickets_sat`**: Verifica que usuarios con rol `comercial` reciben HTTP 403 al intentar consultar o crear tickets de asistencia.
- **`test_anonimo_bloqueado_en_tickets_sat`**: Comprueba que peticiones no autenticadas devuelven HTTP 401.
- **`test_busqueda_filtrada_tickets`**: Valida el filtrado multicriterio en vivo por instalador, obra, síntoma y número de parte técnico.
- **`test_descargar_pdf_ticket_sat_tecnico`**: Comprueba que el endpoint `/api/sat/tickets/{id}/pdf` genera un documento PDF A4 vectorial válido con firma binaria (`%PDF-1.4`) y cabecera MIME `application/pdf`.
- **`test_comercial_no_puede_descargar_pdf_ticket`**: Garantiza que personal comercial no autorizado tiene vetada la descarga de dictámenes periciales y órdenes RMA.

> **Nota de Producción y Escalado:**  
> Si despliegas con múltiples workers de Uvicorn (`--workers N`) o réplicas del contenedor web detrás de un balanceador, es **obligatorio fijar `SECRET_KEY` en variables de entorno** para que todas las instancias firmen y validen los tokens JWT con la misma clave. Para despliegues horizontales a gran escala, el rate limit de login y el cron de sincronización de YouTube deben respaldarse en Redis o PostgreSQL.

---

## 🚀 Despliegue Rápido con Docker

La forma recomendada de desplegar la aplicación es con Docker Compose:

```bash
# 1. Clonar el repositorio
git clone https://github.com/davidiotfenster-dev/buscador-manuales.git
cd buscador-manuales

# 2. Configurar variables de entorno (OBLIGATORIO)
cp .env.example .env
# Genera una SECRET_KEY propia y define POSTGRES_PASSWORD:
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 3. Iniciar los contenedores
docker-compose up -d --build
```

La aplicación estará disponible en `http://localhost:8000`.

> **`SECRET_KEY` y `POSTGRES_PASSWORD` no tienen valor por defecto.** Si faltan, `docker compose` se detiene con un mensaje explícito y la aplicación no arranca. Es deliberado: antes existía una clave de desarrollo fija en el código, de modo que cualquiera que leyera el repositorio podía firmarse un token de administrador.

---

## 🛠️ Instalación Local (Desarrollo)

Requisitos: **Python 3.11+**, **PostgreSQL** con extensión `vector`, y **Tesseract OCR**.

```bash
# 1. Crear entorno virtual
python -m venv venv
venv\Scripts\activate      # En Linux/macOS: source venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno en .env
# SECRET_KEY es obligatoria: sin ella la aplicación se niega a arrancar.
# Genérala con: python -c "import secrets; print(secrets.token_urlsafe(32))"
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/buscador_manuales
SECRET_KEY=<pega aquí la clave generada>

# 4. Iniciar la aplicación
uvicorn app.main:app --reload --port 8000

# 5. Ejecutar la suite completa (tests/unit + tests/api)
pytest
```

---

## 📂 Estructura del Proyecto

```text
buscador-manuales/
├── app/
│   ├── auth.py              # Seguridad JWT, hashing bcrypt, dependencias RBAC y rate limiting
│   ├── database.py          # Modelos SQLAlchemy, pgvector, usuarios, RBAC y tabla tickets_sat
│   ├── email_sender.py      # Despachador asíncrono SMTP de partes oficiales con adjuntos PDF
│   ├── main.py              # Entrypoint limpio FastAPI: lifespan, middleware de seguridad y routers
│   ├── pdf_generator.py     # Generador de partes oficiales SAT y dictámenes RMA en PDF A4 (ReportLab)
│   ├── sat_autoresolver.py  # Motor experto de triaje y resolución inteligente de incidencias SAT
│   ├── sinonimos.py         # Expansor de consultas técnicas mediante tesauro SAT
│   ├── routers/             # Enrutadores modulares (APIRouter)
│   │   ├── auth.py          # /api/token, /api/me, cambio de clave
│   │   ├── buscar.py        # /api/buscar, /api/filtros, /api/sugerencias
│   │   ├── manuales.py      # /api/subir, /api/manuales, streaming PDF, miniaturas, packs ZIP
│   │   ├── sat.py           # /api/sat/tickets, CRM, triage y partes PDF
│   │   ├── usuarios.py      # /api/usuarios (CRUD y roles RBAC)
│   │   └── videos.py        # /api/videos, sincronización YouTube y estado cron
│   ├── templates/
│   │   ├── index.html       # Orquestador semántico de vistas Jinja2 (~200 líneas)
│   │   ├── error.html       # Página amigable 403/404 adaptativa con modo claro/oscuro
│   │   └── partials/        # Componentes parciales modulares
│   │       ├── footer.html  # Pie de página corporativo con acceso técnico discreto
│   │       ├── modals.html  # Modales (login, visor PDF, packs, videos, tickets)
│   │       ├── navbar.html  # Cabecera principal, logo y selector de tema
│   │       ├── vista_*.html # Vistas individuales (buscar, asistencia, esquemas, laboratorio, tickets)
│   └── static/
│       ├── app.js           # Lógica frontend: SCADA, persiana continua, esquemas 230V y CRM
│       └── logo.png         # Logotipo corporativo IoT Fenster
├── cache_miniaturas/        # Caché local de previsualizaciones PNG
├── data/
│   ├── thesaurus_manuales.ths # Tesauro técnico con +500 términos, marcas partner y averías de obra
│   └── sat/                 # Incidencias.xlsx y Problemas-soluciones.xlsx (leídos por sat_autoresolver.py)
├── docs/
│   └── screenshots/         # Capturas de pantalla de la aplicación
├── manuales/                # Almacenamiento local de archivos PDF
├── scripts/                 # Utilidades y herramientas de administración
│   ├── convert_all_sat.py   # Conversión masiva de documentación SAT a PDF
│   └── register_new_manuals.py # Registro e indexación de nuevos manuales en lote
├── tests/
│   ├── conftest.py          # Fixtures aisladas, generación de tokens JWT y mocks
│   ├── unit/
│   │   └── test_sinonimos.py    # Tests del motor de tesauro y tolerancia léxica (sin red/BD)
│   ├── integration/
│   │   └── test_tickets_sql.py  # SQL real contra PostgreSQL: filtros, búsqueda y paginación
│   └── api/                 # Tests con TestClient contra la app completa
│       ├── test_rbac.py         # Tests críticos de seguridad RBAC y prevención Path Traversal
│       ├── test_security.py     # SQLi/SSRF/subida de archivos/cabeceras de seguridad
│       └── test_tickets_sat.py  # Tests de endpoints del Mini-CRM y generación de PDFs A4
├── tools/
│   └── manual_checks/       # Scripts de verificación manual contra un servidor real (no pytest)
│       ├── test_docker_stack.py   # Verificación completa de endpoints en producción
│       ├── test_security_audit.py # Auditoría DAST de seguridad
│       ├── test_search_pdf.py     # Verificación de búsqueda y descarga real de PDFs
│       ├── test_search_sat.py     # Tests de búsqueda SAT con tesauro
│       └── test_flujo_sat_email.py # Flujo completo de auto-registro SAT con envío de email
├── alembic/                 # Migraciones de base de datos versionadas
│   ├── env.py               # Toma DATABASE_URL de la aplicación; excluye las columnas tsvector del autogenerate
│   └── versions/            # Revisiones: esquema inicial y columnas generadas tsvector + índices
├── alembic.ini              # Configuración de Alembic
├── docs/
│   └── PLAN_MEJORA_V1.md    # Plan de mejora incremental y estado real verificado de la V1
├── Dockerfile               # Imagen Docker de producción (non-root, hardened)
├── docker-compose.yml       # Orquestación con PostgreSQL + pgvector
├── .dockerignore            # Optimización de contexto de compilación Docker
├── requirements.txt         # Dependencias de producción (las que entran en la imagen Docker)
├── requirements-dev.txt     # Dependencias de desarrollo: pytest, pytest-cov, httpx, requests
└── .env.example             # Plantilla documentada de variables de entorno
```

---

## 📋 Registro de Cambios

Todo cambio funcional o de infraestructura se anota aquí, con su motivo y su verificación. El estado real de la V1 y el plan por fases viven en **[`docs/PLAN_MEJORA_V1.md`](docs/PLAN_MEJORA_V1.md)**.

> Para ponerse al día de una sentada, empieza por **[`docs/RESUMEN_2026-09-14.md`](docs/RESUMEN_2026-09-14.md)**: qué se hizo, qué decisiones se tomaron y por dónde seguir. El anterior, [`docs/RESUMEN_2026-09-11.md`](docs/RESUMEN_2026-09-11.md), cubre la auditoría inicial y la Fase 0.

### 2026-09-11 — Fase 0: arranque, secretos y honestidad de los avisos

Rama `feature/auditoria-y-plan-mejora-v1`. Cinco correcciones que impedían desplegar el proyecto fuera del equipo de desarrollo.

| # | Cambio | Motivo |
|---|---|---|
| 0.1 | `create_all()` pasa a ejecutarse **antes** del `ALTER TABLE` en `init_db()`, y su `except` relanza en vez de registrar el error | Sobre una base de datos vacía el `ALTER` fallaba con `UndefinedTable`, el error se silenciaba y la aplicación arrancaba **sin ninguna tabla**, mientras `/health` respondía `ok` |
| 0.2 | `SECRET_KEY` sin valor por defecto: si falta, la aplicación no arranca | El fallback estaba escrito en `app/auth.py` y era el valor realmente en uso; cualquiera que leyera el repositorio podía firmarse un token de administrador |
| 0.3 | `SECRET_KEY` y `POSTGRES_PASSWORD` obligatorias en `docker-compose.yml` (`${VAR:?mensaje}`) | Levantar el stack sin `.env` dejaba la base de datos con la contraseña `cambiar_en_produccion` |
| 0.4 | `.dockerignore` excluye `.env`, `venv/` y `cache_miniaturas/` | El `Dockerfile` hace `COPY . .`: los secretos quedaban dentro de una capa de la imagen, junto con ~296 MB de virtualenv (se excluía `.venv/`, pero el real se llama `venv/`) |
| 0.5 | El modo simulado de `email_sender.py` devuelve `enviado: false` | Sin SMTP configurado devolvía `enviado: true`, así que el técnico recibía confirmación de que el parte SAT había salido cuando solo se había escrito una línea de log |

**Cambios derivados en los tests.** Al dejar de silenciarse el error de `init_db()`, quedó al descubierto que la suite dependía de ese fallo silencioso:

- `tests/conftest.py` neutraliza `init_db()` durante el lifespan del `TestClient`. La suite dejó de intentar alcanzar la base de datos de desarrollo y bajó de **60,7 s a 9 s**.
- `tests/api/test_sat_email.py` se movió a `tools/manual_checks/test_flujo_sat_email.py`: nunca fue un test hermético (golpea `localhost:8000` con credenciales fijas y **crea tickets reales** en cada ejecución de `pytest`).
- El recuento pasa de 69 a **68 tests**. No se ha perdido cobertura: se ha dejado de contar un script manual como test automatizado.

**Verificación.** `init_db()` probado sobre una base de datos vacía desechable → crea las 8 tablas. Stack recreado y `healthy`, `/health` → 200, 28 manuales sincronizados, datos intactos. Suite en verde.

**Pendiente de esta fase.** La `SECRET_KEY` filtrada sigue presente en el `.env` local. El fallback ya no existe en el código, pero hasta sustituir ese valor se sigue firmando con una clave conocida. Al rotarla se cierran todas las sesiones abiertas.

### 2026-09-11 — Fase 1.1: migraciones de base de datos con Alembic

Rama `feature/alembic-migraciones`. El esquema deja de crearse con `create_all()` más una pila de `ALTER TABLE` imperativos dentro de `init_db()` y pasa a estar versionado.

| Revisión | Contenido |
|---|---|
| `a511c79f0cbd` | Extensiones `vector`, `unaccent` y `pg_trgm`, configuración de búsqueda `spanish_unaccent` y las 8 tablas del esquema |
| `b1f4c2d93e77` | Las 6 columnas generadas `tsvector` y los 15 índices GIN y trigram |

Las columnas `tsvector` van en una revisión aparte porque son `GENERATED ALWAYS AS ... STORED`: no se pueden declarar como atributos de un modelo SQLAlchemy, así que se crean con SQL explícito. Por el mismo motivo `alembic/env.py` las excluye de la comparación, para que un `--autogenerate` futuro no proponga borrarlas.

**Qué cambia en el arranque.** `init_db()` pasa de 151 líneas de DDL imperativo a dos pasos: aplicar migraciones y sembrar el usuario admin. Si encuentra una base de datos con tablas pero sin `alembic_version` — creada antes de Alembic — la adopta marcándola en `head` en lugar de intentar recrear el esquema.

**Verificación.** Probado en los dos escenarios sobre bases de datos desechables: vacía (aplica ambas revisiones y deja 8 tablas, 6 columnas `tsvector` y 15 índices) y preexistente sin historial (marca en `head` conservando el esquema). Después, aplicado al stack real: `healthy`, `/health` → 200, y 28 manuales, 170 páginas, 30 vídeos, 47 tickets y 5 usuarios intactos.

**Uso.** Las migraciones se aplican solas al arrancar. Para operarlas a mano:

```bash
alembic current                        # revisión actual
alembic upgrade head                   # aplicar pendientes
alembic revision --autogenerate -m "descripcion"   # nueva revisión desde los modelos
```

### 2026-09-11 — Fases 1.2 y 1.3: base de datos de pruebas y medición de cobertura

Rama `feature/alembic-migraciones`. La suite pasa de 68 a **83 tests** y por primera vez ejercita SQL real.

**Base de datos de pruebas.** El fixture `url_bd_pruebas` crea una base `buscador_manuales_test` desde cero, le aplica las migraciones de Alembic y la destruye al terminar; el fixture `db` entrega una sesión con las tablas vacías antes de cada test. Los 15 tests nuevos de `tests/integration/test_tickets_sql.py` prueban el filtrado, la búsqueda libre, la paginación en SQL y las estadísticas contra PostgreSQL de verdad — hasta ahora esas rutas solo se validaban contra un mock reimplementado en el propio test.

La URL sale de `TEST_DATABASE_URL` o se compone desde el `.env`. **Si PostgreSQL no está accesible, esos tests se omiten en lugar de fallar**, así que la suite sigue siendo ejecutable sin levantar el stack.

Para que funcione desde el host, `docker-compose.yml` publica PostgreSQL **solo en la interfaz de loopback** (`127.0.0.1:5432:5432`). No es accesible desde la red; en un despliegue real esa sección debe eliminarse.

**Dependencias separadas.** `requirements-dev.txt` saca `pytest`, `pytest-cov`, `httpx` y `requests` de la imagen Docker, que instala solo `requirements.txt`. `requests` no se importa en ningún punto de `app/`: lo usan únicamente los scripts de `tools/manual_checks/`.

```bash
pip install -r requirements-dev.txt    # entorno de desarrollo
pytest                                 # 83 tests
pytest --cov=app --cov-report=term     # cobertura
```

**Primera medición real: 51 % de cobertura** sobre 2.071 sentencias. Los puntos más bajos, por si sirven de guía: `email_sender.py` 0 %, `routers/videos.py` 32 %, `routers/auth.py` 38 %, `database.py` 39 %, `routers/manuales.py` 41 %.

### 2026-09-11 — Preparación de G2: taxonomía de grupos de incidencia

Análisis de las 119 incidencias reales de `data/sat/Incidencias.xlsx`, en [`docs/G2_TAXONOMIA_GRUPOS.md`](docs/G2_TAXONOMIA_GRUPOS.md). No hay cambios de código: es el trabajo previo al paso 2.1 del plan.

El hallazgo principal es que **la taxonomía de grupos ya existe**: SAT lleva tiempo etiquetando cada incidencia en el campo `problema`, con 11 etiquetas. De ahí sale una lista candidata de 9 grupos, con el número de incidencias que respalda a cada uno.

Tres cosas que condicionan el esquema de `incident_groups` y conviene cerrar antes de crearlo: el 46 % de las incidencias lleva **más de una etiqueta** (el flujo de la V1 asume una), el 25 % **no encaja en ningún grupo**, y «Sensor de Apertura» tiene **1 incidencia de 119**.

El documento incluye además el reparto por dispositivo y distribuidor, los dos campos que casi nadie rellena (sistema operativo del móvil y compañía de internet, vacíos en el 66 % y el 57 %), y la taxonomía de `accion_correctiva`, que alimenta directamente el cierre técnico estructurado de G10.

### 2026-09-11 — G2: grupos de incidencia (datos y API)

Rama `feature/alembic-migraciones`, migración `3f514b913e75`. La taxonomía de grupos deja de ser una lista fija en el HTML y pasa a ser una entidad de base de datos.

| Cambio | Detalle |
|---|---|
| Tabla `incident_groups` | `code`, `name`, `description`, `is_active`, `sort_order`, sembrada con los 9 grupos del análisis |
| `tickets_sat.grupo_id` | Grupo principal, nullable, con `ON DELETE SET NULL` |
| Tabla `ticket_grupos_secundarios` | Grupos adicionales del ticket |
| `GET /api/sat/grupos` | Taxonomía para el formulario y el cuestionario |
| `GET /api/sat/tickets?grupo=CODIGO` | Filtro por grupo, y `grupo=sin_grupo` para los no clasificados |
| `GET /api/sat/tickets/stats` | Nuevo bloque `por_grupo` |

**Por qué un grupo principal más secundarios.** El 46 % de las incidencias reales lleva más de una etiqueta, así que un único `grupo_id` habría perdido información que SAT ya registra. El principal decide qué preguntas mostrará el cuestionario; los secundarios alimentan las métricas. Es una decisión revisable.

Dos detalles de comportamiento que conviene conocer: un código de grupo desconocido **deja el ticket sin clasificar en lugar de rechazar el alta** (el alta llega desde tres puntos distintos de la interfaz), y el recuento por grupo incluye **los grupos sin ningún ticket**, porque una rama vacía de la taxonomía también es información.

*Actualizado el 2026-09-14.* Los 47 tickets existentes se quedaron sin grupo, y aquí se dio por bueno que fuera una decisión —39 son el mismo ticket de prueba repetido—. Era cierto, pero no era la razón: `TicketSATCreate` no declaraba el campo `grupo`, así que el selector del formulario lo enviaba y pydantic lo descartaba en silencio. **No había forma de clasificar un ticket ni queriendo.** Corregido, y las 119 incidencias reales están importadas y clasificadas.

13 tests nuevos en `tests/integration/test_grupos_incidencia.py`. La suite pasa de 83 a **96 tests**. Queda pendiente la parte de interfaz: el CRUD de administración y que el formulario y el filtro lean de la API.

### 2026-09-11 — G2: interfaz de grupos de incidencia

Rama `feature/alembic-migraciones`. Cierra la parte de uso de G2: la taxonomía ya se puede seleccionar y filtrar desde la aplicación.

- **Formulario de ticket**: nuevo selector «Grupo de Incidencia», que se rellena desde `GET /api/sat/grupos`. No hay ninguna lista de grupos escrita en el HTML: añadir o quitar un grupo ya no toca el código de la vista.
- **Listado**: selector de filtro junto a los botones de estado, con «Todos los grupos» y «Sin clasificar».
- **Tarjeta de ticket**: insignia con el grupo. Un ticket sin grupo se marca en ámbar como «Sin clasificar» en lugar de omitirse — lo que falta por clasificar tiene que verse, o nadie lo clasifica.

**Verificado en el navegador** contra el stack real: los dos selectores se rellenan con los 9 grupos, el filtro por `CONECTIVIDAD` deja el listado vacío (ningún ticket clasificado todavía), el filtro «Sin clasificar» devuelve los 47, y la insignia ámbar aparece en las tarjetas.

Dos cosas que se observaron por el camino y **no** se han tocado, por estar fuera del alcance de este cambio:

- `app/static/app.js` lanza al cargar `ReferenceError: Cannot access 'esquemasModuloInicializado' before initialization`. El módulo de tickets vive dentro de `inicializarModuloEsquemas()`, que en la carga inicial falla y solo se inicializa de verdad al abrir la pestaña. Hoy es inocuo porque el error está capturado, pero significa que la inicialización temprana no funciona.
- La cabecera desborda horizontalmente 103 px con la ventana a 1280 px, por el bloque de correo y rol del usuario.

### 2026-09-14 — Corrección del panel de estado contra el documento de Notion

No toca código: corrige el **[panel visual](https://claude.ai/code/artifact/d2c15cc6-4dee-4af8-bf02-27e577d356f2)**, que se había desviado del documento de V1 al contrastarlo línea a línea con él.

| # | Qué estaba mal | Corrección |
|---|---|---|
| P.1 | **G1 no era el grupo del documento.** Se había sustituido «Descubrimiento con el equipo de soporte» (reuniones 1.1, 1.2 y 1.3) por el gestor de tickets, al 85 % | G1 vuelve a ser el grupo real, al **30 %**: 1.2 (inventario) está hecho y superado con las 119 incidencias, pero 1.1 y 1.3 siguen pendientes. La media baja de **38 % a 35 %** |
| P.2 | El flujo mostraba **8 eslabones** resumidos de los 13 del diagrama | Los 13, numerados y en orden. Vuelven **Vitales 1 / Vitales 2** como bloques separados, los tres silos documentales, «operador aplica solución» y las dos decisiones (`¿Resuelto?`, `¿Documentación suficiente?`) |
| P.3 | Los 5 riesgos se presentaban **todos como abiertos**, incluidos los cerrados en la Fase 0 y la Fase 1 | 8 riesgos con estado: **5 resueltos** (tachados) y **3 abiertos** — sin copia de los 222 MB de PDFs, el puerto 5432 publicado para los tests, y el `PUT` de tickets sin validar estado ni prioridad |
| P.4 | El orden recomendado empezaba por trabajo ya hecho | Empieza por la reunión de validación de la taxonomía (G1), y sigue con G10, G2.4, G3 y la decisión sobre embeddings |
| P.5 | Faltaban detalles del documento en las tarjetas | Los 8 tipos de respuesta y el `required/recommended/automatic` de G3.3, el silo `SUPPORT_DOCUMENTS` de G7.5, los 4 permisos de G16, el **fusionar** y el «en revisión» de G2.3, y los 7 casos de prueba de G17 |

**Por qué importaba P.1.** La división de las preguntas vitales en dos bloques que recupera P.2 no es cosmética: es exactamente lo que el documento pide para **evitar ofrecer «Sensor de Apertura» como grupo antes de saber si el dispositivo es un CONNECT-1 o un CONNECT-2**. Y los datos le dan la razón — ese grupo tiene 1 incidencia de 119.

**El gestor de tickets** sigue en el panel, pero como nota aparte: es la pieza más terminada del proyecto y **no es ninguno de los 17 grupos**, así que no cuenta para el 35 %.

**Verificación.** Estructura del panel comprobada por script: 17 grupos con ids `G1`–`G17` consecutivos, 13 pasos de flujo, 8 riesgos de aridad correcta, 5 rutas, delimitadores balanceados, y la media de los 17 (34,7 → 35 %) coincidiendo con la cifra de cabecera y con los recuentos 1/11/5 de las leyendas y los filtros.

### 2026-09-14 — G1: inventario y priorización de incidencias reales

Sin cambios de código. Cierra dos de las tres tareas de G1 con los datos de `data/sat/Incidencias.xlsx`: **[`docs/G1_DESCUBRIMIENTO_SAT.md`](docs/G1_DESCUBRIMIENTO_SAT.md)**.

| Tarea | Objetivo | Resultado |
|---|---|---|
| **1.2 Inventario** | 30–50 incidencias reales | ✅ **119**, del 23/07/2025 al 03/12/2025 — 5,4 por semana |
| **1.3 Priorización** | Puntuar por frecuencia, impacto, tiempo y dificultad; elegir 10–15 representativas | ✅ Las 11 etiquetas puntuadas y **15 incidencias representativas** |
| **1.1 Reunión** | Entender cómo trabaja SAT | 🟡 Guión preparado; hay que celebrarla |

**La métrica que ordena la prioridad resultó ser la llamada de teléfono.** El 52 % de las incidencias acabó en una llamada, y el reparto no es uniforme: Vinculación necesitó llamada en **34 de 41** casos, Gestual en 24 de 31 y Wifi en 15 de 22. Ahí está el tiempo del operador.

**Y son justo las documentables.** Vinculación se resuelve con documentación en el 66 % de los casos y aun así hace falta llamar en el 83 %: el material existe, pero el cliente no lo encuentra. Es exactamente el problema que ataca este proyecto. El contraste lo confirma: `Aplicación` tiene frecuencia parecida a `Wifi` pero solo necesita llamada el 39 % de las veces y se resuelve con documentación el 75 % — lo que está bien explicado se resuelve solo.

**Dos hallazgos que afectan al plan:**

- **`Otro` tarda 7 días de mediana** cuando el resto está en 0 o 1, y el 31 % requiere firmware, servidor o presencia. Lo que no encaja en la taxonomía es lo que más cuesta cerrar: **G12 (incidencias nuevas) no es un extra, es la válvula de escape de los casos caros**.
- **`Conexión` es la que más se queda sin resolver** (29 %), y **`Instalación` la más cara por caso** (43 % con asistencia presencial, firmware o reposición).

**Orden recomendado para documentar:** Vinculación → Gestual → Wifi. No Aplicación, aunque sea tercera en frecuencia, porque ya se resuelve sola el 75 % de las veces.

**Método y sus límites.** Frecuencia y tiempo de resolución son medidas directas (86 de 119 tienen ambas fechas). Dificultad e impacto son aproximaciones —% de acciones caras y % sin resolver—, y están marcadas como tales en el documento. Las 15 incidencias representativas salen de buscar patrones en los 102 comentarios: tocan 49 de ellos, y **son una propuesta a validar en la reunión, no una clasificación de SAT**.

**Panel actualizado:** G1 pasa de 30 % a 65 %, y la media de la V1 de 35 % a 37 %.

### 2026-09-14 — G10: cierre técnico estructurado

Rama `feature/alembic-migraciones`. La pieza que convierte en dato medible lo que hoy se pierde: en las 119 incidencias reales, `Vídeos` aparece **29 veces** como acción correctiva, y eso no queda registrado en ninguna parte. Sin esto, la pregunta *«¿nuestra documentación resuelve?»* no tiene respuesta posible.

| # | Cambio | Motivo |
|---|---|---|
| 10.1 | 10 columnas `cierre_*` en `tickets_sat` (migración `eec0dc7833f3`) | Los 6 campos que pide el documento, más `cierre_fecha` y `cierre_por`. Todas NULL: **NULL es «sin cerrar», que no es «no se resolvió»** |
| 10.2 | `POST /api/sat/tickets/{id}/cierre` | Registra el cierre, deja rastro en el historial y, si procede, pasa el estado a `resuelto` |
| 10.3 | El `PUT` rechaza con 400 pasar a `resuelto` sin cierre | Un ticket resuelto sin cierre es un agujero permanente en la métrica: no hay forma de rellenarlo después |
| 10.4 | Solo 2 campos obligatorios: `resuelto` y `documentacion_suficiente` | Un técnico al teléfono no rellena seis campos. Exigirlos acabaría en tickets sin cerrar, que es peor que un cierre incompleto |
| 10.5 | `obtener_stats_cierre_tecnico()` en `/api/sat/tickets/stats` | Alimenta G15: % resueltos, **% documentación suficiente**, % escalados y horas hasta el cierre |
| 10.6 | `contar_documentos_usados_en_cierres()` | Responde qué documentos resuelven de verdad, mezclando manuales y vídeos: al operador le da igual el formato |
| 10.7 | Modal de cierre + insignia en la tarjeta + KPI «Doc. suficiente» | El selector rápido de estado ya no falla al marcar «Resuelto»: abre el formulario que falta |

**Tres decisiones que conviene conocer:**

- **Los denominadores.** Todos los porcentajes se calculan sobre los tickets **cerrados**, no sobre el total. Si se mezclaran, el «% documentación suficiente» bajaría solo porque nadie ha rellenado el formulario todavía. Con cero cierres se muestra un guion, no un 0 %.
- **El cierre no toca el estado.** Un ticket puede cerrarse con `resuelto = false` —queda documentado que no se resolvió— y seguir en espera hasta que llegue el recambio. El estado es el flujo de trabajo; el cierre es lo que ocurrió.
- **`cierre_fecha` es una columna propia** porque `fecha_actualizacion` cambia con cualquier edición posterior y falsea el tiempo medio de resolución que pide G15.

**Documento usado: selector más texto libre.** Se elige un manual o vídeo de los que ya hay en el sistema (`cierre_manual_id` / `cierre_video_id`, ambos con `ondelete SET NULL`), y si la fuente fue otra se escribe a mano. Obligar a elegir un documento habría dejado el campo vacío: en el histórico, 62 de 119 incidencias se resolvieron por llamada.

**Verificación.** Migración probada en una base desechable en los dos sentidos (`upgrade` y `downgrade`) antes de tocar la real; los 47 tickets siguen ahí. **113 tests en verde** (eran 96): 11 de integración nuevos —centrados en que los denominadores sean correctos— y 6 de API. Cobertura 54 %. Flujo comprobado en el navegador contra el stack real: el modal abre desde la tarjeta, el bloque «¿qué hubo que hacer?» aparece solo al marcar documentación insuficiente, el cierre se guarda, la tarjeta muestra la insignia y el KPI pasa a «100% sobre 1 cierre». El cierre de prueba se borró después.

**Un aviso de despliegue.** `docker-compose.yml` monta `./app` pero **no** `./alembic`. Una migración nueva no llega al contenedor hasta reconstruir la imagen, y mientras tanto la base de datos va por delante del código y la aplicación entra en bucle de reinicio con `exit 3`. Tras añadir una migración: `docker compose up -d --build web`.

### 2026-09-14 — Limpieza de manuales duplicados

De los 28 manuales de la base de datos, **10 eran copias byte a byte** de otros 5. Se comprobó por `sha256` del fichero, no por el nombre.

| Documento | Copias | Se conserva |
|---|---|---|
| Guía de Redes WiFi, Credenciales y Laboratorio SAT | **7** | id 1 |
| Documentación Funcional y Técnica C-Pulsar | 2 | id 6 |
| Documentación Funcional y Técnica C-Wall | 2 | id 8 |
| Documentación Funcional y Técnica Connect-1 | 2 | id 12 |
| Documentación Funcional y Técnica Connect-2 | 2 | id 14 |

En cada grupo se conservó la fila de menor `id`, la primera subida. Se borraron el fichero y la fila; las páginas indexadas se fueron en cascada (170 → 104).

**Resultado:** 28 → **18 manuales**, y `manuales/` pasa de 221 MB a **54 MB**. Buscar «wifi» devolvía el mismo documento siete veces; ahora devuelve siete documentos distintos.

**Comprobado antes de borrar:** ningún comentario, ticket ni cierre técnico apuntaba a las filas eliminadas, y ninguna ruta del código menciona esos nombres de fichero. Las únicas dependencias de `manuales` son `paginas` (CASCADE) y `tickets_sat.cierre_manual_id` (SET NULL, sin filas).

**Comprobado después:** tras reiniciar, `sincronizar_manuales()` **no** las vuelve a insertar, porque también se borró el PDF del disco — el sincronizador recorre `manuales/*.pdf` y da de alta todo lo que no esté en la base de datos. Borrar solo la fila las habría resucitado en el siguiente arranque.

> La causa se corrigió acto seguido: ver la entrada siguiente.

### 2026-09-14 — Los manuales duplicados ya no se pueden crear

Limpiar las copias no servía de nada si el sistema podía volver a crearlas. Ni la subida ni el sincronizador miraban el contenido: identificaban un manual por su **nombre de fichero**, y el mismo PDF con otro nombre era un manual nuevo.

| # | Cambio | Motivo |
|---|---|---|
| D.1 | Columna `manuales.contenido_hash` con el SHA-256 del PDF (migración `31314c06dfbc`) | El nombre no identifica nada: dos ficheros distintos pueden llamarse igual, y el mismo fichero llega con nombres distintos |
| D.2 | `POST /api/subir` rechaza un PDF cuyo contenido ya exista | Responde con `duplicado: true` y el id del manual que ya lo contiene. **No escribe el fichero ni la fila**: la comprobación va antes de tocar el disco |
| D.3 | `sincronizar_manuales()` omite los ficheros cuyo contenido ya esté dado de alta | Dejar una copia en la carpeta la volvía a insertar en el siguiente arranque |
| D.4 | El sincronizador rellena el hash de los manuales antiguos | La columna nace NULL; se completa cuando ya tiene el fichero abierto, en vez de hacerlo en la migración |
| D.5 | `obtener_manual_por_hash()` y `fijar_hash_manual()` aceptan una sesión | Las funciones de manuales abren la suya contra el engine del módulo, así que no veían la base de pruebas. Las de tickets ya recibían `db` |

`fijar_hash_manual()` **solo rellena huecos**: si el manual ya tiene hash no lo pisa, porque reescribirlo enmascararía que el fichero de disco ha cambiado.

**Verificación.** 6 tests de integración nuevos (**119 en total**, eran 113), incluido el caso de que un hash vacío no case con los manuales antiguos — si casara, la subida los daría por duplicados de cualquier PDF y no se podría subir nada. Probado además sobre el stack real: se dejó en la carpeta una copia de `CONECTIVIDAD_REQUISITOS.pdf` con otro nombre y se reinició. Siguen siendo **18 manuales** y la copia no tiene fila. Antes habría sido el manual 19 y habría aparecido repetida en cada búsqueda.

### 2026-09-14 — G2.4: administración de grupos de incidencia

Rama `feature/alembic-migraciones`. Cierra la crítica original: hasta hoy, **añadir o renombrar un grupo exigía escribir una migración**, así que la taxonomía era «configurable» solo para quien tocara el repositorio.

| # | Cambio | Motivo |
|---|---|---|
| 2.4.1 | Columna `incident_groups.estado_revision` (migración `6cadde48eeca`): `estable`, `nuevo`, `en_revision` | Es el «marcar grupo como nuevo / en revisión» del documento. Distingue la taxonomía que respaldan 119 incidencias reales de la que alguien inventa durante una llamada |
| 2.4.2 | `POST`, `PUT` y `DELETE /api/sat/grupos`, más `PUT /grupos/orden/actualizar` y `POST /grupos/fusionar` | Los seis verbos que pide el documento: crear, editar, ordenar, activar/desactivar, fusionar y marcar en revisión |
| 2.4.3 | Modal de administración, solo admin, desde la vista de tickets | Edición en línea del nombre, selector de madurez, casilla de activo, flechas de orden, borrado y fusión |
| 2.4.4 | El fixture `db` de los tests restaura los 9 grupos sembrados | Un test que reordenaba grupos rompía a los siguientes. Antes solo se reponía `is_active` |

**Cuatro decisiones de diseño:**

- **El `code` no se edita.** Es la referencia estable que usan la API y las exportaciones; renombrarlo rompería cualquier integración. Para eso está fusionar.
- **Un grupo con tickets no se borra** (409). La clave foránea es `SET NULL`: borrarlo dejaría tickets sin clasificar en silencio. La respuesta dice cuántos lo usan y ofrece las dos salidas: fusionar o desactivar.
- **Los grupos nuevos nacen como `nuevo`**, no como `estable`. En la reunión conviene poder separar lo validado de lo que está a prueba.
- **El orden se numera de 10 en 10**, para poder intercalar un grupo entre dos sin reescribir la tabla entera.

**Fusionar es la operación delicada**, y por eso es la más probada: mueve los tickets que tenían el grupo como principal, arrastra los secundarios, y **no duplica** cuando un ticket ya tenía ambos grupos —la tabla puente tiene clave primaria compuesta—. Se hace en dos pasadas, borrando todos los del origen antes de insertar los que faltan: fila a fila, el borrado y el alta de la misma clave caían en el mismo `flush` y SQLAlchemy avisaba de que el `DELETE` no encontraba la fila esperada.

**Verificación.** 19 tests de integración nuevos (**138 en total**, eran 119). Migración probada en una base desechable en los dos sentidos antes de tocar la real; los 9 grupos quedaron en `estable`. Flujo completo comprobado en el navegador: crear un grupo (sale marcado «nuevo» y al final de la lista), renombrarlo en línea, cambiarle la madurez, desactivarlo, subirlo de posición, intentar borrarlo con un ticket detrás —devuelve el 409 con el recuento— y fusionarlo con `OTRO`, que movió el ticket y borró el origen. Todo se dejó como estaba después.

> La migración autogenerada añadía la columna `NOT NULL` **sin** `server_default`, lo que falla sobre las 9 filas existentes. Se corrigió a mano: el `server_default` se pone para rellenarlas y se retira después, para que el valor de las nuevas lo decida el modelo y no la base de datos.

### 2026-09-14 — `alembic/` montado en el contenedor

`docker-compose.yml` montaba `./app` pero no `./alembic`. Una migración nueva no llegaba al contenedor hasta reconstruir la imagen, así que la base de datos quedaba **por delante** del código: Alembic no encontraba la revisión en la que estaba la base y el arranque entraba en bucle de reinicio con `exit 3`, sin traza en el log que lo explicara.

Pasó dos veces en la misma sesión, así que se monta el directorio en vez de dejarlo como nota. Ahora una migración nueva se aplica con un `docker compose restart web`, igual que un cambio en `app/`.

### 2026-09-14 — Los vídeos del canal pasan a ser documentación buscable

Los 43 vídeos del canal son **mudos**: son grabaciones de pantalla sin narración, así que YouTube no ofrece ninguna transcripción y durante meses la tabla `videos` no ha tenido más texto que el título. El pipeline `../descarga-videos` resuelve el hueco por otra vía —extrae fotogramas clave con OpenCV y los describe con un modelo de visión— y produce, por cada vídeo, una lista de pasos con su segundo. Esto es lo que hacía falta en este repositorio para que ese material llegue entero al buscador y no se pierda.

| # | Cambio | Motivo |
|---|---|---|
| V.1 | `insertar_video()` solo pisa `transcripcion_texto` y los fragmentos **si el que llega trae contenido** | Antes los sobrescribía siempre. Como YouTube devuelve cadena vacía para estos vídeos, una sola llamada a `POST /api/videos` sobre un vídeo ya procesado borraba su texto y todos sus fragmentos, en silencio y sin forma de recuperarlo salvo repitiendo el pipeline entero |
| V.2 | `_extraer_videos_canal()` usa `yt-dlp` y deja el HTML como alternativa | Leer el HTML inicial del canal solo devuelve la primera tanda: **30 de 43**. Trece tutoriales —entre ellos los de instalación de C-WALL y de Connect-2— nunca habían llegado al buscador |
| V.3 | `buscar_videos()` desempata por la relevancia del fragmento, no solo por la global | La relevancia sumaba el título (peso `A`), idéntico para todos los fragmentos del mismo vídeo; al empatar, el `DISTINCT ON` elegía uno cualquiera y el enlace acababa casi siempre en el segundo 0. El minuto exacto es justamente lo que aporta el vídeo frente al manual |

**Qué queda cubierto con esto.** La búsqueda por minuto con marca de tiempo, que se había dado por inviable al comprobar que ningún vídeo tenía transcripción, **sí es alcanzable**: los fragmentos no salen del audio sino de los pasos visuales, y `buscar_videos()` ya devuelve `segundo`, `tiempo_formateado` y una URL con `&t=`.

**Verificación.** Búsqueda real contra los vídeos ya ingestados: `luz led bloqueo` devolvía el segundo `00:00` y ahora devuelve `00:02`, que es donde aparece el rótulo. `yt-dlp` sobre el canal devuelve 43 identificadores frente a los 30 del método anterior.

**Pendiente de reconstruir la imagen.** `yt-dlp` se añade a `requirements.txt`; hasta que se reconstruya el contenedor, `_extraer_videos_canal()` avisa por log y sigue usando el HTML, con el catálogo incompleto pero sin romperse.

**Tests.** `tests/integration/test_videos_pipeline.py` (5) fija que una resincronización sin texto no borre el del pipeline, que un texto nuevo sí lo reemplace y que título y miniatura se sigan refrescando desde YouTube. `insertar_video()` acepta ahora un `db=` opcional para poder ejercitarla contra la base de pruebas, igual que ya hacían las funciones de manuales.

#### Resultado de la ingesta

| Antes | Después |
|---|---|
| 30 vídeos, 3 con texto | **43 vídeos, 43 con texto** |
| 63 fragmentos | **1132 fragmentos** con su segundo |
| `categoria` = `VISUAL_APP` para todos | `VINCULACION` 6 · `INSTALACION` 6 · `AUTOMATIZACION` 4 · `RESETEO` 3 · `CONECTIVIDAD` 3 · `CONFIGURACION_APP` 21 |

Búsquedas reales contra el resultado: `hard reset antes de vincular` → *Vinculación AP de C-Pulsar* en **00:08**, justo el aviso; `conectar a BDSMART` → **00:26**; `instalar connect-2` → **01:06**. El vídeo entra como respuesta a un problema concreto y apunta al segundo, que es lo que un manual en PDF no puede dar.

**Cuota gratuita de Gemini.** El límite es `GenerateRequestsPerDayPerProjectPerModel`: 20 peticiones **al día y por modelo**. En la primera tanda se agotó el cupo de un solo modelo y 22 de los 43 vídeos se quedaron con texto de relleno (`"Paso en segundo 12"`) sin que nada avisara. Los pasos 2 y 4 del pipeline rotan ahora entre modelos equivalentes —siete de visión, tres de embeddings—, lo que multiplica el margen por siete sin coste. Esperar no servía: el cupo es diario, no por minuto.

Los embeddings quedaron a medias (33 de 43) por ese mismo límite. No afecta a la búsqueda, que usa el índice de texto completo de PostgreSQL; el vector solo hace falta para el RAG semántico, que es decisión abierta (§5.1).

### 2026-09-14 — El ticket propone qué vídeo sirve

Al cerrar un ticket, el selector «Documento o vídeo que sirvió» ofrecía los 43 vídeos del canal en una lista plana y sin orden: dar con el que servía dependía de acordarse del título. En el histórico de 119 incidencias, «Vídeos» aparece 29 veces como acción correctiva, así que es una elección que se hace a menudo.

`GET /api/sat/tickets/{id}/documentacion-sugerida` cruza las tres cosas que el ticket ya sabe y devuelve los seis mejores vídeos con el motivo de cada uno y el segundo exacto:

| Señal | Peso | Por qué |
|---|---|---|
| Mismo grupo de incidencia | 3.0 | `videos.categoria` comparte vocabulario con `incident_groups.code`, así que no depende de cómo esté redactado el síntoma |
| Coincidencia con el síntoma | 2.5 | Aporta el minuto exacto. Si la frase entera no casa, se reintenta con sus palabras sueltas y puntúa 1.25 |
| Mismo dispositivo | 1.5 | Afina dentro del grupo, pero es grueso: once vídeos son `Connect-1` |

El síntoma va por delante del dispositivo a propósito: con el orden contrario, un ticket de persianas recibía como primera sugerencia el vídeo de resetear el Connect, solo por compartir aparato.

**En el modal**, las sugerencias aparecen encima del selector, cada una con un botón «Usar», un enlace al minuto y la línea de motivos. El selector completo sigue debajo: la sugerencia puede equivocarse y el operador tiene que poder ignorarla.

**Verificación.** Ticket real del grupo `VINCULACION`, dispositivo `C-Pulsar`, síntoma *«no consigo vincular el pulsar, se queda buscando la red»* → los dos primeros son los vídeos de vinculación del C-Pulsar con las tres señales (7.0), y el cuarto es el Hard Reset con dos (4.0). `tests/integration/test_documentacion_sugerida.py` (8).

#### Dos fallos encontrados de paso

| # | Cambio | Motivo |
|---|---|---|
| T.1 | `generar_numero_ticket()` toma como suelo el mayor número que exista de verdad | El contador marcaba `1` con 48 tickets ya creados —los importados del histórico se insertaron con su número puesto, sin pasar por el contador—, así que **toda alta nueva moría con una violación de clave única**. El `GREATEST` conserva la atomicidad del UPSERT y el desfase se corrige solo |
| T.2 | `_clave_dispositivo()` normaliza antes de comparar | Los tickets guardan `C-Wall` y los vídeos `C-WALL`. Comparar en crudo no casaba ni uno |

**El botón «Sincronizar @MySmartWindow»** funciona y ahora ve los 43 vídeos (antes 30). Ejecutado sobre el catálogo ya procesado: 43 sincronizados, 0 errores, y **el texto y los 1132 fragmentos del pipeline intactos** — que es justamente lo que antes se perdía. Requiere la imagen reconstruida (`docker compose build web`), ya hecho.

### 2026-09-14 — G3.1: las respuestas del cuestionario dejan de tirarse

El cuestionario de asistencia son doce bloques que el técnico rellena para obtener un diagnóstico. `POST /api/sat/asistencia-triage` los evaluaba, devolvía el dictamen y **descartaba lo que se había contestado**. No quedaba rastro: ni de qué se preguntó, ni de qué se respondió, ni de si el diagnóstico acertó.

Eso bloquea las dos cosas que vienen después. G3.2 pide una tabla de preguntas configurable, y diseñarla sin datos repetiría el problema que ya hay: doce bloques que nadie ha validado. Y medir si el triaje acierta exige poder mirar atrás.

| # | Cambio | Motivo |
|---|---|---|
| 3.1a | Tabla `cuestionarios_asistencia` (migración `bbd75c7ee2bc`) | Guarda el envío entero en `respuestas_json`, más cuatro campos sueltos —dispositivo, área, diagnóstico y confianza— que son los que se filtran a menudo |
| 3.1b | El triaje guarda y devuelve `cuestionario_id` | Envuelto en su propio `try`: si el registro falla, el técnico sigue viendo su diagnóstico. Lo que se pierde es una fila, no la respuesta al cliente |
| 3.1c | `auto-registrar-enviar` acepta `cuestionario_id` y ata el ticket | El ticket nace después del cuestionario, y solo a veces: de ahí que la relación se complete en dos pasos |
| 3.1d | `GET /api/sat/cuestionarios` y `/cuestionarios/stats` | Las estadísticas dicen qué porcentaje de envíos rellena cada campo. Un campo que no toca nadie sobra del formulario; uno que se rellena siempre es candidato a obligatorio |

**Por qué un JSON y no una columna por pregunta.** Las preguntas van a cambiar con G3.2, y una tabla con ochenta columnas quedaría obsoleta a la primera. El JSON aguanta el cambio; los cuatro campos sueltos evitan abrirlo solo para filtrar.

**`ticket_id` es `SET NULL`.** Borrar un ticket no debe borrar la evidencia de lo que se contestó antes de crearlo — hay un test que lo fija.

**La confianza se guarda como decimal.** El triaje devuelve `89.3`; redondear a `89` sería inventar precisión en la dirección contraria. La primera versión usaba `Integer` y descartaba el valor en silencio, dejando la media a `null`.

**Verificación.** Cuestionario real por HTTP → diagnóstico *«Configuración de Mecanismo de Pared C-Wall»* y `cuestionario_id: 2`. Ambos endpoints de lectura responden 401 sin token. `tests/integration/test_cuestionarios_asistencia.py` (10). Suite: **161 tests**.

**Lo que esto todavía no es.** G3.2 —la tabla `questions` con scope VITAL/GROUP/INCIDENT y los 8 tipos de respuesta— sigue pendiente. Esto solo deja de perder los datos, que es el requisito para hacerla bien.

### 2026-09-14 — Subir un PDF: los dos tipos de documento, y tres fallos por el camino

Los manuales llegan de dos formas. Unos son PDF generados por un programa y llevan capa de texto. Otros son escaneos: páginas que son una imagen y no contienen una sola letra legible por software. La subida ya contemplaba ambos —texto directo y, si la página venía vacía, OCR con tesseract en español—. Al comprobarlo de punta a punta con un PDF de cada tipo, funcionaba. Lo que apareció fue lo demás.

| # | Cambio | Motivo |
|---|---|---|
| P.1 | La extracción se unifica en `app/extraccion_pdf.py` | Había **dos implementaciones**: la de la subida, con OCR, y la de `sync_manuales.py`, sin él. Como el botón «Reindexar» usa la segunda, pulsarlo reemplazaba el texto de todos los manuales escaneados por cadenas vacías |
| P.2 | Una página con capa de texto **pobre** también pasa por OCR | Se decidía «¿hay texto? entonces no hace falta OCR». Un escaneo con un pie de página real —lo que añaden muchos escáneres— se indexaba con esos 29 caracteres y **el contenido de la página se perdía entero** |
| P.3 | `docker-compose.yml` monta `sync_manuales.py` | Es el único módulo de la aplicación que vive fuera de `app/`, así que el montaje no lo cubría: se corrigió el OCR del reindexado y el botón seguía borrando texto, ejecutando la copia vieja de dentro de la imagen |
| P.4 | `obtener_manual_por_archivo()` devuelve `categoria` y `etiquetas` | Sin ellas, el sincronizador daba por vacías las etiquetas de **todos** los manuales y en **cada arranque** reescribía dispositivo, categoría y nivel de acceso de la biblioteca entera. Subías un PDF como `C-Wall` y el siguiente reinicio lo dejaba en `TODOS` |
| P.5 | El sincronizador solo rellena lo que está vacío | Etiquetas vacías significan «faltan metadatos», no «los que hay están mal» |

**El umbral.** Por debajo de 100 caracteres, la capa de texto de una página no se considera su contenido sino un resto. Una página real de un manual pasa de largo con holgura, así que los PDF normales no pagan el coste del OCR. Si el OCR no aporta más que la capa de texto, se conserva la capa: nunca se empeora lo que ya se tenía.

**Verificación, con tres PDF fabricados a propósito.**

| Caso | Antes | Ahora |
|---|---|---|
| PDF con capa de texto (2 págs) | se indexaba bien | igual, sin pasar por OCR |
| PDF que es solo imagen | OCR correcto | igual |
| Escaneo con pie de página real | **29 caracteres, contenido perdido** | 167 caracteres, contenido recuperado |

Las tres palabras clave escondidas en esos PDF (`ZANAHORIA` en la capa de texto, `CALABAZA` en la imagen, `PIMIENTO` en la página mixta) se encuentran las tres desde el buscador. Y el reindexado, que antes dejaba 0 páginas con OCR, ahora **recupera** texto: sobre la biblioteca real aparecieron 2 páginas que llevaban tiempo indexadas en blanco.

`tests/unit/test_extraccion_pdf.py` (7) fija la decisión —cuándo se llama al OCR y con qué texto se acaba— sustituyendo el OCR por una función controlada, así que corren aunque no haya tesseract instalado. Más 2 tests de la consulta de metadatos. Suite: **170 tests**.

### 2026-09-14 — El grupo de incidencia nunca llegaba a guardarse

Al comprobar el efecto de los arreglos sobre el flujo real —crear un ticket y buscarle solución— apareció el fallo que explica por qué **los 47 tickets de la base tienen `grupo_id` nulo**. No es que sean anteriores a G2: es que el alta nunca aceptó el grupo.

El formulario tiene su selector y lo envía (`app.js:3904`). `TicketSATCreate` no declaraba el campo, y pydantic descarta lo que no conoce **sin decir nada**. `TicketSATUpdate` tampoco, así que no había forma de corregirlo después, ni a mano. El selector era decorativo.

| # | Cambio | Motivo |
|---|---|---|
| G.1 | `grupo` en `TicketSATCreate` y `TicketSATUpdate` | Es lo único que faltaba: `crear_ticket_sat()` ya traducía el código a `grupo_id` desde que se hizo G2 |
| G.2 | `actualizar_ticket_sat()` traduce `grupo` → `grupo_id` | La columna es el id y el DTO manda el código; un `setattr` sobre la relación habría reventado |
| G.3 | Un código con errata **no** desclasifica el ticket | Perder la clasificación por escribir mal el código sería otro borrado silencioso. Se avisa por log y se conserva el grupo. La cadena vacía sí desclasifica, a propósito |

**Qué desbloquea.** El grupo es la señal de más peso (3.0) al proponer qué vídeo resuelve un ticket, y el eje de las métricas por grupo que pide el documento. Desde ahora un ticket nuevo nace clasificado; los 47 anteriores siguen pendientes de repasar.

**Verificación.** Tres tickets creados seguidos por la API (`SAT-2026-0050` a `0052`, sin colisión de numeración), y un cuarto con `grupo: VINCULACION` que la respuesta devuelve ya clasificado y que se reclasifica a `CONECTIVIDAD` con un PUT. 5 tests nuevos. Suite: **175 tests**.

### 2026-09-14 — Las 119 incidencias reales entran como tickets clasificados

Los 47 tickets que había en la base **no eran historial**: seis casos distintos, uno de ellos repetido 39 veces, todos creados por `admin@empresa.com` entre el 8 y el 11 de septiembre con instaladores llamados `ndasf` y `Pedro Tecnico Test`. Eran pruebas de desarrollo. Clasificarlos no habría dado métricas que signifiquen nada.

El historial real vive en `data/sat/Incidencias.xlsx` —el mismo del que salieron los 9 grupos— y su columna «Problema» ya trae las etiquetas que puso SAT. La clasificación no se inventa: se traduce.

`tools/importar_incidencias.py` hace esa traducción. Es idempotente por `numero_ticket` (`SAT-HIST-0001`…), así que volver a lanzarlo no duplica, y tiene `--dry-run`.

| Grupo | Principal | Secundario | Total | G2 decía |
|---|---:|---:|---:|---:|
| VINCULACION | 28 | 13 | 41 | 41 |
| GESTUAL | 20 | 11 | 31 | 31 |
| CONECTIVIDAD | 10 | 19 | 29 | 29 ¹ |
| APP | 15 | 13 | 28 | 28 |
| OTRO | 19 | 12 | 31 | 30 ² |
| PULSADOR | 13 | 2 | 15 | 15 |
| INTEGRACIONES | 9 | 2 | 11 | 11 |
| INSTALACION | 3 | 4 | 7 | 7 |
| HARDWARE | 2 | 4 | 6 | 6 |

¹ Wifi (22) + Conexión (14) son 36 etiquetas pero 29 incidencias: muchas llevan las dos.
² 30 más la única de «Sensor de Apertura», que no llegó a ser grupo.

**55 de las 119 (46 %) llevan más de un grupo**, exactamente el porcentaje medido en G2. Por eso el esquema tiene grupo principal más secundarios, y el importador rellena los dos.

**Dos reglas del mapeo que no son obvias:**

- **`OTRO` no manda si hay algo más concreto.** «Otro, Instalación» es una incidencia de instalación que además alguien marcó como rara; dejar `OTRO` de principal escondería la información que sí hay. Afecta a 5 casos. `OTRO` es la entrada de G12, no un cajón de sastre.
- **Una celda vacía es `OTRO`, no un error.** 17 de las 119 no se etiquetaron, y omitirlas falsearía los totales.

**Qué desbloquea.** Las métricas por grupo dejan de estar vacías, y la sugerencia de vídeo al cerrar un ticket pasa a usar su señal de más peso: un ticket de `INSTALACION` sobre un Connect-1 recibe *«¿Cómo se instala Connect-1?»* con `Mismo grupo + Mismo dispositivo` (4.5), en vez de depender solo de cómo esté redactado el síntoma.

`tests/unit/test_importar_incidencias.py` (10) fija las reglas de traducción. Suite: **185 tests**.

> **Los 47 de prueba ya no están.** Se borraron a mano tras la importación; la base tiene ahora 119 tickets, todos del histórico y todos clasificados. La copia previa sigue en `copias/tickets_antes_de_importar_2026-09-14.sql` (ignorada por git).

> **Los 47 de prueba siguen en la base.** Borrarlos es irreversible y se deja en manos de quien decida hacerlo. Hay copia previa en `copias/tickets_antes_de_importar_2026-09-14.sql` (ignorada por git).

### 2026-09-16 — Asistencia SAT: asistente por pasos y veredicto en grande

Rama `feature/rediseno-asistencia-sat`. **Experimento de visualización, pendiente de aceptar o descartar.** No cambia ninguna regla de diagnóstico: `evaluar_cuestionario_asistencia()` no se toca.

El formulario eran **12 bloques desplegados a la vez** en una columna larguísima: no se sabía por dónde ibas ni cuánto faltaba. Y la resolución automática —lo que el sistema deduce, que es la razón de ser de la pantalla— aparecía como un bloque de texto más, indistinguible del resto.

**Los 12 bloques se agrupan en 5 pasos** sin reordenar nada, así que los ~80 ids que lee la evaluación siguen donde estaban y esto es solo presentación. Ningún paso es obligatorio y los puntos de arriba permiten saltar al que sea: en una llamada real el instalador no cuenta las cosas en el orden del formulario.

**El veredicto pasa a ocupar la columna derecha entera**, con semáforo de certeza, el paso a dar ahora y los accesos al vídeo y al manual que resuelven. Se ve de un vistazo, que era el problema.

Cuatro cosas que se arreglaron por el camino, todas del mismo tipo — **algo escrito desde dos sitios donde el segundo borra al primero en silencio**, el patrón que ya aparecía cuatro veces en este proyecto:

| Qué pasaba | Por qué |
|---|---|
| «Reiniciar respuestas» dejaba el formulario sucio | Limpiaba 4 campos de los ~20. El resto —partner, dispositivo, área, estado, ocho desplegables, tres textos— se quedaba, así que el formulario **parecía** limpio y el siguiente diagnóstico salía contaminado. Ahora se guarda una instantánea del formulario recién cargado y se restaura: cualquier campo futuro entra solo. |
| El ticket nacía sin grupo | El payload mandaba el título del dictamen como `sintoma` y no mandaba `grupo`. Ahora el área del cuestionario se traduce a grupo de incidencia, y el síntoma es **lo que escribió el instalador**, no la jerga del diagnóstico — que es además contra lo que casa la búsqueda de vídeos. |
| Los 5 pasos salían a la vez | `display:flex` por clase ganaba al atributo `hidden`. |
| «Siguiente» avanzaba de dos en dos | Los listeners se acumulaban en cada entrada a la vista. |

**Cambiar de menú y volver empieza un caso nuevo.** Salir al Buscador y volver dejaba las respuestas del caso anterior y repintaba su veredicto, así que la siguiente llamada arrancaba contaminada. Pero el motivo más común para salir es **consultar algo en mitad de una llamada**, así que lo anterior se guarda y una barra discreta ofrece recuperarlo de un clic. Solo se avisa si había algo contestado; entrar y salir sin tocar nada no muestra nada.

**Qué queda por decidir** (salió de revisar esta pantalla entera):

- **Unificar los dos vocabularios.** El cuestionario tiene 10 «áreas» y el sistema 9 grupos de incidencia. Hoy se traducen las 5 que significan lo mismo; el resto va sin grupo a propósito. «Dispositivo / electrónica» es la opción marcada por defecto, así que no distingue a quien la eligió de quien no tocó nada: clasificar por ella llenaría HARDWARE de tickets que nadie clasificó, y **un grupo equivocado hace más daño en las métricas que ninguno**.
- **La lista de dispositivos del desplegable.** Falta `C-Pulsar`, y las 119 incidencias reales usan «Konect Elite», que tampoco está.
- **Si Sensores, OTA y Usuario/cuenta deberían ser grupos.** Hoy caen en OTRO, que es la entrada de G12.

`tests/integration/test_grupos_incidencia.py` gana 2 tests por el grupo del ticket. Suite: **186 tests**.

### 2026-09-16 — Copias de seguridad de la base de datos

Rama `feature/copias-y-cierres`.

La base de datos vive en el volumen `pgdata` de Docker. Un `docker compose down -v` —que es la forma habitual de «empezar de cero»— lo borra sin preguntar, y con él se van 119 incidencias reales, 1.132 fragmentos de vídeo (una semana de pipeline y de cuota de Gemini), 18 manuales indexados y 110 cuestionarios. La única copia que había era un `pg_dump` suelto lanzado a mano antes de importar el histórico.

`tools/copia_seguridad.py` vuelca, comprime, rota y —con `--verificar`— restaura la copia en una base desechable y compara los recuentos tabla por tabla. **Una copia que nunca se ha restaurado no es una copia, es un fichero.**

```bash
python tools/copia_seguridad.py --verificar
```

Dos decisiones que los tests fijan:

- **La rotación solo borra ficheros con el nombre que genera el script.** La copia guardada a mano antes de importar el histórico es justamente la que haría falta si aquello hubiera salido mal, y no puede caducar sola a las dos semanas.
- **Un volcado sin la marca final de `pg_dump` se rechaza y no se escribe.** Archivar un volcado cortado es peor que no tener copia: se descubre el día que hace falta restaurar.

**Qué no cubre.** Los PDF de `manuales/` (55 MB) no están en la base de datos ni en git: viven solo en el disco (`tar -czf copias/manuales_$(date +%F).tar.gz manuales/`). Y `copias/` está en el mismo disco que los datos, así que esto protege de un `down -v`, de un borrado por SQL y de una migración que salga mal, **no de que se rompa el disco**. Para eso la carpeta tiene que acabar en otra máquina — es parte de la decisión 5.2 (S3).

**Verificación.** Copia de 1,0 MB sobre los datos reales, restaurada en una base aparte, las siete tablas coinciden. `tests/unit/test_copia_seguridad.py` (6). Suite: **192 tests**.

### 2026-09-16 — G10 deja de ser una pregunta sin respuestas

El formulario de cierre técnico tiene diez campos y **no había ni un solo ticket con ninguno relleno**. G10 —«¿la documentación fue suficiente?»— estaba construido y medía sobre cero. El buscador de casos parecidos tampoco podía decir qué acabó funcionando.

La columna «Acción» del Excel no es texto libre: SAT usaba un vocabulario cerrado de doce acciones. El cierre se deduce en vez de inventarse, igual que «Problema» permitió clasificar por grupo. `tools/cerrar_historico.py` hace la traducción, con `--dry-run`.

**La frontera es una sola: ¿bastó con explicar, o tuvo que actuar alguien?**

| Acciones | Cierre | Casos |
|---|---|---:|
| `Videos`, `Mensaje Informativo`, `Llamada`, `Reset`, `Tiempo` | resuelto, documentación **suficiente** | 56 |
| `Firmware`, `servidor`, `Reposición`, `Asistencia Presencial`, `Ofertar Nuevos Dispositivos` | resuelto, documentación **insuficiente**, escalado | 17 |
| `incompareciencia` | **no** resuelto, no puntúa | 12 |
| `Incidencia Ajena a nosotros` | resuelto, no puntúa, escalado | 4 |

Los 29 en espera y 1 resuelto sin acciones anotadas se quedan sin cierre: rellenarlos «por completar» metería ruido en la única métrica que tenemos de si la documentación sirve. **89 cierres escritos.**

Una llamada cuenta como *explicar*. Aparece en 62 de las 119, y tratarla como fracaso de la documentación diría que casi nada funciona: guiar por teléfono es documentación haciendo su trabajo, solo que en directo.

**El resultado — G10 pasa de no tener respuesta a 76,7 %**, y por fin se puede leer por grupo:

| Grupo | Cierres | Bastó | No bastó | % |
|---|---:|---:|---:|---:|
| GESTUAL | 14 | 9 | 5 | 64 % |
| PULSADOR | 10 | 7 | 3 | 70 % |
| CONECTIVIDAD | 7 | 5 | 2 | 71 % |
| INSTALACION | 3 | 2 | 1 | 67 % |
| INTEGRACIONES | 6 | 5 | 1 | 83 % |
| VINCULACION | 19 | 17 | 2 | 89 % |
| APP | 11 | 10 | 1 | 91 % |

**GESTUAL y PULSADOR son donde la documentación falla más**, y son justo los grupos con vídeos del canal. Es la primera pista con datos sobre qué documentación escribir (G9).

**Lo que no se deriva, y por qué.** `cierre_manual_id` y `cierre_video_id`: la acción «Videos» dice que se mandaron vídeos, no *cuál*, y apuntar uno al azar contaminaría justo la métrica de qué documentación resuelve. `cierre_doc_texto` y `cierre_alternativa` son «qué documentación faltaba», y el Excel no lo recoge.

Todos quedan con `cierre_por = 'historico-excel'`, para distinguirlos de un cierre hecho por una persona. `obtener_stats_cierre_tecnico()` los excluye del **tiempo medio hasta el cierre**: su `cierre_fecha` es la de importación —el Excel no traía fechas— y contarlos metía 89 casos de cero horas. Sí cuentan para «documentación suficiente», que no depende de cuándo pasó.

**Verificación.** Los recuentos derivados cuadran uno a uno con los que da SQL sobre las acciones (12 incomparecencias resueltas, 17 con intervención). `tests/unit/test_cerrar_historico.py` (16). Suite: **208 tests**.

### 2026-09-16 — Las variables SMTP no llegaban al contenedor

`app/email_sender.py` lee `SMTP_HOST`, `SMTP_USER` y `SMTP_PASSWORD` del entorno del proceso, pero `docker-compose.yml` no las pasaba y `.env.example` ni las nombraba. **Rellenar el `.env` no cambiaba nada**: la aplicación seguía en modo simulado y el parte seguía sin salir. El circuito estaba cortado en un sitio donde nadie lo iba a buscar.

Las siete variables pasan ahora al contenedor, todas opcionales —si faltan, la aplicación arranca igual—, y `.env.example` explica que sin ellas el parte se genera pero no se envía.

El aviso al técnico ya era honesto desde la Fase 0 (`enviado: false` y un mensaje que dice que falta SMTP). Ahora tiene tests para que no vuelva a mentir, incluido el caso contrario: con las tres variables puestas se intenta el envío de verdad y el PDF viaja adjunto.

**Sigue pendiente una decisión, no código:** qué buzón usa esto en producción. Hasta rellenarlo, ningún parte SAT sale de la aplicación.

**Verificación.** `docker compose config` resuelve las siete, el contenedor recreado las tiene en su entorno, `/health` → 200. `tests/unit/test_email_sender.py` (6). Suite: **214 tests**.

### 2026-09-16 — Rotar la clave de firma, como script

La `SECRET_KEY` con la que se firman los tokens sigue siendo la que estuvo publicada en el repositorio: el fallback se quitó en la Fase 0, pero el **valor** no se cambió. Quien leyera aquel commit puede firmarse un token de administrador.

`tools/rotar_secret_key.py` la sustituye, guardando la anterior en `copias/`:

```
python tools/rotar_secret_key.py
docker compose up -d --force-recreate web
```

**Cierra todas las sesiones abiertas.** Es lo esperado: de eso se trata.

Es un script y no la línea suelta que se propuso primero porque **esa línea no sobrevive a PowerShell**: las comillas se pierden al pasar el código a `python` y la orden falla a medias — en un fichero de configuración, justo lo que no se quiere. El script no escribe nada si no encuentra exactamente una línea `SECRET_KEY=`, porque crear una donde no había significaría que ese no es el `.env` que usa el stack.

`tests/unit/test_rotar_secret_key.py` (6). Probado además de punta a punta en PowerShell sobre un `.env` de juguete: rota, respalda y deja el resto del fichero intacto. Suite: **220 tests**.

### 2026-09-16 — Abrir la aplicación a otra persona

Al preparar un enlace para que un compañero probase la aplicación salió a la luz que **la pantalla de login anunciaba la contraseña del administrador** (`admin / admin123`, en dos botones de acceso rápido y precargada en los campos) y que esas credenciales funcionaban: `POST /api/token` devolvía 200 con un token de admin.

En `localhost` eso llevaba ahí sin molestar a nadie. El agujero no era la aplicación: era compartirla. Con un enlace, cualquiera que lo recibiera —o lo encontrara— habría sido administrador sobre 119 incidencias reales con nombres de instaladores, con permiso para borrarlo todo.

Los botones, el JS y los `value=` precargados están fuera, con tests para que no vuelvan. **El modo invitado se queda**: no es el agujero —fija el rol en el cliente sin pedir token, y los endpoints de datos siguen devolviendo 401— y quitarlo habría sido cambiar una decisión de producto que nadie pidió.

Dos herramientas nuevas, según cómo se quiera compartir:

**`tools/preparar_acceso_companero.py`** — para compartir *la misma* instancia. Rota la contraseña del admin y crea la cuenta del compañero con rol `tecnico`. Las dos contraseñas van a `.credenciales_companero` (ignorado por git) y a ningún otro sitio: no se imprimen, para que no queden en el historial de la terminal.

**`tools/paquete_companero.py`** — para que monte *su propia* copia. Empaqueta la base de datos y los manuales. Deja fuera el `.env` y los **datos** de `usuarios` (los hashes), pero **no la tabla**: el volcado trae `alembic_version` al día, así que Alembic daría el esquema por hecho y no crearía una tabla que faltase — la aplicación reventaría al buscar el admin, y solo en la máquina del otro. Verificado restaurando en una base limpia: 119 tickets, 89 cierres, 43 vídeos, `usuarios` vacía.

**Compartir la misma instancia resultó ser lo razonable.** El compañero necesita el mismo corpus —es contra lo que prueba— y el riesgo que parecía haber no existe: sus tickets serán `SAT-2026-NNNN` y el histórico real es `SAT-HIST-NNNN`, así que no hay mezcla posible. Al terminar:

```bash
docker compose exec -T db psql -U postgres -d buscador_manuales -c "DELETE FROM tickets_sat WHERE numero_ticket LIKE 'SAT-2026-%';"
```

`tests/unit/test_login_sin_credenciales.py` (8) y `tests/unit/test_paquete_companero.py` (8). Suite: **236 tests**.

### 2026-09-17 — Ficha de obra: qué le pasó antes a ese sitio

Rama `feature/ficha-de-obra`. **Experimento, pendiente de aceptar.**

La idea era una ficha por cliente para ver si ya había habido incidencias del mismo tipo. Al mirar los datos antes de construirla, resultó que cuentan algo distinto y más útil.

**El identificador bueno es la obra, no el instalador.** Los nombres de instalador tienen variantes —`Estela` / `Estella`, `Maria` / `María`, `Inma` / `Inmaculada`— así que agrupar por nombre partiría el historial de la misma persona. Las 79 obras con referencia son todas numéricas y limpias. `distribuidor` tampoco vale: solo hay 5 valores distintos en 102 tickets, es la marca.

**Y lo que se repite no es la avería, es la obra.** De las 10 obras con más de una incidencia, **nueve tienen problemas de grupos distintos**:

| Obra | Grupos |
|---|---|
| 13282, 13871, 14123 | CONECTIVIDAD → VINCULACION |
| 13929, 13941 | CONECTIVIDAD → GESTUAL |
| 13995 | APP → GESTUAL |
| 14399 | GESTUAL → VINCULACION |
| **14257** | **CONECTIVIDAD → CONECTIVIDAD** |

Solo una repite grupo. Si la ficha avisara únicamente de coincidencias del mismo tipo, **se callaría en nueve de cada diez casos en los que tiene algo que decir**. Así que enseña el historial entero y destaca aparte la repetición de grupo.

Lo que se ve durante la llamada, al salir del campo «Obra»:

```
⚠️ Esta obra ya tuvo CONECTIVIDAD antes
   SAT-HIST-0053  2026-08-21  CONECTIVIDAD  No conecta tras cambiar el router
                              · se resolvió, pero hizo falta intervenir
   SAT-HIST-0005  2026-07-02  CONECTIVIDAD  Se cae la conexión por las noches
                              · se resolvió explicando
```

Cada antecedente dice **cómo acabó**, que es lo que cambia el diagnóstico de ahora: una lista de fechas no aporta nada. Ese dato sale de los cierres derivados del histórico.

Tres decisiones que los tests fijan:

- **Sin antecedentes no se pinta nada.** Un panel que dice «no hay nada» en la mayoría de los casos se deja de mirar, y entonces tampoco se ve cuando sí dice algo.
- **La obra se compara normalizada** (sin espacios, sin mayúsculas). El campo es texto libre y lo rellena una persona al teléfono; comparar en crudo partiría el historial de una obra en dos sin que nadie lo notara.
- **Una obra vacía no agrupa.** 40 de las 119 incidencias no traen obra: si la cadena vacía casara consigo misma, cada una vería las otras 39 como antecedentes de un sitio que no tienen en común.

Vista desde un ticket, `ya_paso_lo_mismo` se mide contra **su** grupo, y el propio ticket se excluye: la ficha responde a «¿qué hubo antes?», y contarse a sí mismo la haría decir siempre que sí.

`GET /api/sat/obras/{obra}/ficha` y `GET /api/sat/tickets/{id}/ficha-obra`, ambos de técnico o admin — la ficha lleva nombres de instaladores y síntomas de clientes, el mismo material que los tickets. Una obra sin historial contesta **200 con la ficha vacía, no 404**: «no hay antecedentes» es la respuesta más frecuente y si llegara como error la interfaz aprendería a ignorar el aviso.

**Lo honesto sobre su valor hoy:** con 119 incidencias, solo 10 obras repiten. El aviso saltará poco al principio y crece con el uso. Es barato y no molesta cuando no tiene nada que decir.

`tests/integration/test_ficha_obra.py` (13) y `tests/api/test_ficha_obra_api.py` (6). Suite: **254 tests**.

### 2026-09-17 — El modo invitado reventaba al arrancar

`app.js` son ~6.000 líneas en un solo ámbito, y la aplicación se arrancaba a un tercio del fichero con una llamada suelta a `verificarSesion()`. Esa función entra en el modo invitado, llama a `inicializarModuloEsquemas()`, y esa lee `esquemasModuloInicializado` — un `let` declarado **1.500 líneas más abajo**. Un `let` no existe hasta que se ejecuta su declaración, así que el modo invitado moría con:

```
ReferenceError: Cannot access 'esquemasModuloInicializado' before initialization
```

Estaba en todas las ramas antes de tocar nada; se vio al revisar la consola tras una fusión, y se comprobó en cada rama por separado antes de atribuirlo.

**El fallo no era esa variable: era arrancar a mitad de fichero.** Subir la declaración habría tapado este caso y dejado el siguiente `let` que alguien añada en la misma trampa. El arranque pasa a `queueMicrotask(verificarSesion)`, que corre en cuanto termina de evaluarse el módulo —antes de pintar y antes de que nadie pueda tocar nada— con todo ya definido.

Se comprobó antes de moverlo que **nada a nivel de módulo lee el estado de sesión después de esa línea**, así que aplazarlo no cambia el comportamiento de nada más.

No hay runner de JavaScript en el proyecto, así que `tests/unit/test_arranque_app_js.py` (3) comprueba lo único que se puede sin uno: que el arranque sigue aplazado y por delante de las declaraciones. Es poco, y cubre exactamente la regresión que costó encontrar.

Verificado en el navegador: en modo invitado, `inicializarModuloEsquemas()` deja de lanzar. Suite: **258 tests**.

### 2026-09-22 — El triaje SAT daba siempre el mismo diagnóstico

Rama `fix/triaje-sat-diagnostico-y-formulario`.

**El fallo.** `evaluar_cuestionario_asistencia` elegía diagnóstico con una cadena de trece `if/elif`: ganaba la primera rama que enganchaba. La rama 8 tenía esta condición:

```python
wifi["tipo_red"] in [..., "Dual 2,4/5 GHz"] and wifi["ssid_separados"] == "No"
```

que son **exactamente las dos primeras `<option>`** de los desplegables de Wi-Fi del formulario: las que quedan puestas si el técnico no toca ese bloque. La condición se cumplía siempre, así que cualquier avería salía como «Band Steering Activo en Router». Reproducido contra el motor real antes de tocar nada:

| Caso enviado | Diagnóstico devuelto |
|---|---|
| Formulario en blanco | Band Steering Activo en Router · **95 %** |
| «La persiana no sube ni baja» | Band Steering Activo en Router · 92,9 % |
| «El sensor de temperatura marca mal» (Connect-2) | Band Steering Activo en Router · 94,2 % |
| «La alarma no suena, batería agotada» (WAlarm) | Band Steering Activo en Router · 94,2 % |

Con dos agravantes. Las **ramas 9 a 13** —calibración, sensores Connect-2, C-Wall, WAlarm y cobertura RF— eran inalcanzables salvo cambiando ese desplegable. Y la confianza no avisaba: el recálculo solo podía bajarla hasta `65 + similitud × 60`, así que un diagnóstico falso se presentaba con un 92-95 %.

**Por qué no saltó antes.** Los diez tests que había del cuestionario comprobaban que las respuestas **se guardaban**. Ninguno comprobaba qué diagnóstico salía: la lógica de diagnóstico tenía cobertura cero.

**El arreglo.** El `if/elif` pasa a un sistema de puntuación: cada regla suma el peso de las señales que encuentra y gana la de mayor puntuación. Lo que corrige el sesgo no es el orden, es el peso.

| Señal | Peso | Qué es |
|---|---|---|
| `SENAL_FUERTE` | 3,0 | Evidencia explícita e inequívoca (checklist de hardware, síntoma marcado) |
| `SENAL_MEDIA` | 2,0 | Respuesta explícita distinta del valor por defecto |
| `SENAL_DEBIL` | 0,8 | Condición de entorno que puede venir por defecto |
| `SENAL_FAMILIA` | 1,2 | Orientación por familia de producto, nunca un diagnóstico |

Con `UMBRAL_DECISION = 2,0`, una señal débil sola (0,8) no decide, ni dos sumadas (1,6): hace falta al menos una respuesta explícita del técnico. La condición de Band Steering sigue existiendo y sigue puntuando, pero como `SENAL_DEBIL`.

Si nadie pasa el umbral se devuelve **«Sin diagnóstico concluyente: faltan datos»** con las preguntas que más discriminan, en vez de afirmar el primero de la lista. La confianza sale de la evidencia (`50 + puntuación × 7 + margen × 5`, con el techo de cada regla como máximo), no de un número escrito a mano.

Además, la respuesta incluye ahora `motivos_diagnostico` (en qué se basa) e `hipotesis_consideradas` (qué más se valoró y con cuánta puntuación). Sin eso no había forma de notar desde fuera que el motor estaba repitiendo el valor de un desplegable.

**Los dos Excel de la base SAT ya se usan.** `cargar_base_conocimiento_sat()` **no se llamaba desde ningún punto del proyecto**: las 119 incidencias reales de `Incidencias.xlsx` y las 10 parejas de `Problemas- soluciones.xlsx` se parseaban bien y no las leía nadie. Ahora `buscar_casos_similares()` las cruza con lo que cuenta el cliente y devuelve precedentes junto al diagnóstico. El corte de similitud es 0,45 y no 0,2 porque `calcular_similitud` ya suma 0,35 solo por coincidir el dispositivo: por debajo de eso salían los mismos tres casos para consultas completamente distintas.

**El formulario pasa a empezar por la persona.** Los doce bloques iban de electrónica, Wi-Fi y cableado, y **no preguntaban el correo en ningún momento**; el nombre, la obra y el teléfono estaban al final del primer bloque, en gris, bajo el rótulo «Datos Opcionales de Referencia». El correo es la puerta de entrada al caso, así que el orden pasa a ser:

1. **Quién llama** — correo, nombre, teléfono y obra (paso nuevo)
2. **Comercializadora y equipo** — el antiguo bloque 1
3. **Qué le pasa** — área, estado y síntomas
4. Entorno, cuándo falla y el detalle, detrás

Los tres campos que ya existían conservan sus ids (`asist-input-instalador`, `asist-input-obra`, `asist-input-telefono`) para no romper el JavaScript que ya los lee.

**El correo, además, busca.** Al salir del campo se consulta `GET /api/sat/clientes/historial`, que dice si esa persona ya tiene casos abiertos y rellena los datos de contacto que ya conocemos. La búsqueda es por igualdad exacta sin distinguir mayúsculas, **no por `LIKE`**: con un `LIKE`, teclear «paco@» a medias devolvería los casos de cualquiera cuyo correo lo contuviera, y aquí eso es enseñar datos de un cliente a cuenta de otro. El endpoint exige rol técnico o administrador aunque el triaje en sí sea accesible sin sesión.

**Cinco fallos más, encontrados por el camino.** Los tres primeros son del mismo tipo: algo que no funciona **sin dar ninguna señal de que no funciona**.

- Los dos sitios que abren ticket desde el triaje llevaban **`email: ""` fijo** en el payload. El ticket nacía sin destinatario, así que `auto-registrar-enviar` generaba el parte y no tenía a quién mandárselo.
- **Los cinco botones de repetidor/mesh no hacían nada.** El HTML tiene un grupo de botones `#asist-group-mesh`, pero el JavaScript hacía `getElementById("asist-wifi-mesh").value` sobre un `<select>` que no existe en ninguna plantilla. Con el encadenado opcional, eso se queda en el valor por defecto sin lanzar: `repetidor_mesh` valía **siempre** «Ninguno» pulsara el técnico lo que pulsara.
- **El triaje inventaba un manual cuando no encontraba ninguno:** un `manual_id: 1` fijo, con el nombre construido a mano y la página 3 inventada, apuntando siempre al PDF del Connect-1 o al del C-Pulsar. El técnico recibía una referencia con toda la pinta de ser un resultado de búsqueda y podía citarle al cliente una página que no habla de su avería. Es el mismo tipo de fallo que los avisos de correo de la Fase 0: dar por bueno algo que no ha pasado. Ahora, si no hay manual, no se sugiere ninguno — todos los consumidores del campo ya contemplaban que viniera vacío.
- **`C-Pulsar` faltaba en el desplegable de dispositivos**, pese a tener manual propio y cinco vídeos indexados. Cualquier incidencia de un C-Pulsar se registraba con el dispositivo equivocado. *(«Konect Elite» —47 de las 119 incidencias— no se ha añadido: se entiende que es el nombre comercial de Kömmerling para un Connect-1/2 y su sitio es el campo «Modelo comercial». Queda por confirmar.)*
- `palabras` solo se asignaba dentro del `try` de la consulta de manuales, pero se leía después para buscar el vídeo: si esa consulta fallaba, la búsqueda del vídeo reventaba con `NameError` en lugar de quedarse sin vídeo.

**Cómo se encontraron los dos primeros.** Cruzando los **73 ids** que lee el módulo de asistencia en `app.js` contra los que existen en las plantillas. Esa comprobación queda como test (`test_ningun_id_leido_por_el_js_falta_en_las_plantillas`), porque es la única forma de detectar esta familia de fallos sin un navegador: `getElementById` de un id inexistente devuelve `null`, el encadenado opcional lo convierte en el valor por defecto, y un campo entero deja de recogerse sin que nada falle.

**Verificación.** Reproducido el fallo original contra el motor real y vuelto a ejecutar tras el arreglo: los cuatro casos de la tabla dan ahora diagnósticos distintos o «faltan datos». Comprobado en vivo contra `localhost:8000`. Tests nuevos: `tests/unit/test_diagnostico_triaje.py` (29, incluida una comprobación parametrizada de que **las trece reglas son alcanzables**), `tests/integration/test_flujo_triaje_a_ticket.py` (9, el recorrido llamada → triaje → ticket de extremo a extremo), `tests/unit/test_orden_formulario_asistencia.py` (19) y `tests/integration/test_historial_cliente.py` (7). Suite: **322 tests**.

El funcionamiento del triaje y las decisiones que quedan por validar están en **[`docs/TRIAJE_SAT.md`](docs/TRIAJE_SAT.md)**.

**Pendiente.** Los datos de la persona viajan dentro de `respuestas_json` del cuestionario, no como columnas propias: no hace falta migración, pero tampoco se pueden filtrar cuestionarios por cliente sin abrir el JSON. Y **el cambio no se ha visto en un navegador**: la comprobación ha sido estática (cruce de ids, plantilla servida por el servidor) más los tests. Queda anotado en `docs/PLAN_MEJORA_V1.md`.
