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

**68 tests, ~9 segundos, sin dependencias externas.** La suite no necesita que el stack de Docker esté levantado ni escribe en la base de datos de desarrollo: el arranque (`init_db()`) se neutraliza durante los tests y la capa de datos está mockeada.

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
