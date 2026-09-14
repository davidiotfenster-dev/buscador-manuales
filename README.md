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

> Para ponerse al día de una sentada, empieza por **[`docs/RESUMEN_2026-09-11.md`](docs/RESUMEN_2026-09-11.md)**: qué se hizo, qué decisiones se tomaron y por dónde seguir.

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

Los 47 tickets existentes se han quedado sin grupo a propósito: 39 son el mismo ticket de prueba repetido y clasificarlos ensuciaría las métricas.

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
