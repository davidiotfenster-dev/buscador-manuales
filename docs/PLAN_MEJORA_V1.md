# Plan de mejora incremental — Gestor de Soporte V1

> **Corte:** 2026-09-11 · rama `feature/mejora-simulador-laboratorio` · 33 commits
> **Método:** estado verificado abriendo el código y consultando la base de datos en ejecución. No se ha usado `README.md`, `DOCUMENTACION_SISTEMA.md` ni `dossier_tecnico_y_operativo.md` como fuente, porque sobrevaloran el estado real (ver [Anexo A](#anexo-a--documentación-contra-realidad)).
> **Panel visual:** https://claude.ai/code/artifact/d2c15cc6-4dee-4af8-bf02-27e577d356f2

El objetivo de este documento es que la V1 avance en pasos pequeños, cada uno del tamaño de un commit, sin bloquear el trabajo del día a día. El orden **no** es por importancia: es por dependencia. Cada fase existe porque la siguiente sería más cara o más arriesgada sin ella.

---

## Punto de partida

| Medida | Valor real |
|---|---|
| Grupos funcionales cerrados | 2 de 17 |
| Grupos parciales | 10 |
| Grupos sin empezar | 5 |
| Completitud media de la V1 | ~32 % |
| Tests que pasan | 69 |
| Handlers que ejecutan su cuerpo en tests | 15 de 40 (37 %) |
| Endpoints HTTP | 41 |
| Tablas en PostgreSQL | 8 |
| Líneas de código | 14.311 (6.178 JS · 4.230 Python · 3.903 HTML) |
| Tickets SAT reales | 44 (40 resueltos) |

**Lectura corta:** el producto funciona y tiene datos reales dentro, pero casi toda la lógica de negocio está cableada en HTML y en árboles `if/elif`, y la suite de tests valida sobre todo el control de acceso, no el comportamiento.

---

## Fase 0 — Lo que hay que arreglar antes de añadir nada ✅ COMPLETADA (2026-09-11)

Son correcciones de horas, no de días. Están primero porque hacían que el proyecto no se pudiera desplegar fuera de este portátil.

**Verificación de cierre:** `init_db()` probado sobre una base de datos vacía desechable → crea las 8 tablas. Stack real recreado y `healthy`, `/health` → 200, 28 manuales sincronizados, datos intactos. Suite en verde.

### 0.1 · El arranque sobre base de datos vacía deja la aplicación sin tablas — ✅ hecho

En `app/database.py:190` se ejecuta `ALTER TABLE manuales ADD COLUMN IF NOT EXISTS etiquetas` **antes** del `Base.metadata.create_all(bind=engine)` de la línea 193. Sobre una base de datos nueva la tabla `manuales` todavía no existe, el `ALTER` lanza `UndefinedTable`, y el `except Exception` de la línea 319 solo escribe una línea de log. La aplicación arranca sin ninguna tabla.

Lo agrava que `/health` (`app/main.py:115`) solo hace `SELECT 1`, así que responde `status: ok, database: connected` con el esquema vacío.

- **Cambio:** mover el `ALTER` detrás del `create_all`; hacer que el `except` aborte el arranque en lugar de registrarlo.
- **Verificación:** `docker compose down -v && docker compose up` debe crear las 8 tablas o fallar de forma visible.

### 0.2 · La clave de firma JWT está publicada en el código — ✅ hecho (falta rotar el valor)

`app/auth.py:18-21` define un fallback fijo (`mysmartwindow_buscador_dev_secret_key_fixed_...`). Ese mismo valor es el que trae `docker-compose.yml` por defecto y el que contiene hoy el `.env` real. Quien lea el repositorio puede firmarse un token `{"sub":"admin@empresa.com","role":"admin"}`.

- **Cambio:** eliminar el fallback; si `SECRET_KEY` no está definida, la aplicación no arranca. Generar una clave nueva y darla por rotada.
- **Efecto esperado:** todos los tokens emitidos hasta ahora dejan de valer. Es el comportamiento correcto.
- **Pendiente:** el fallback ya no existe en el código, pero el `.env` sigue conteniendo la clave filtrada. **Hay que sustituirla por una nueva**; hasta entonces se sigue firmando con un valor conocido.

### 0.3 · Contraseña de PostgreSQL por defecto — ✅ hecho

`docker-compose.yml` usa `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-cambiar_en_produccion}`, y `app/database.py:18-21` tiene un fallback `postgres:password@localhost`. Mismo tratamiento que 0.2: sin variable, sin arranque.

### 0.4 · El `.dockerignore` mete los secretos en la imagen — ✅ hecho

El `Dockerfile` hace `COPY . .` y el `.dockerignore` actual solo excluye `manuales/`, `scratch/`, `__pycache__/`, `*.pyc`, `.git/` y `.venv/`. Dos consecuencias:

- El `.env` real (con `SECRET_KEY`, `POSTGRES_PASSWORD` y `ADMIN_DEFAULT_PASSWORD`) queda dentro de una capa de la imagen.
- El virtualenv real se llama `venv/`, no `.venv/`, así que sus ~296 MB también entran.

- **Cambio:** añadir `.env`, `venv/` y `cache_miniaturas/` al `.dockerignore`.

### 0.5 · El envío de correo informa de éxito sin enviar nada — ✅ hecho

`app/email_sender.py:231-235` devuelve `{"enviado": True, "modo": "simulado"}` cuando faltan `SMTP_HOST`, `SMTP_USER` o `SMTP_PASSWORD` — que no aparecen ni en `.env.example` ni en `docker-compose.yml`. El técnico recibe confirmación de que el parte SAT salió cuando solo se ha escrito un log.

- **Cambio:** en modo simulado devolver `enviado: false`. Configurar SMTP de verdad, o dejar explícito en la interfaz que el envío está desactivado.

---

## Fase 1 — La red de seguridad

Las fases 2 a 4 cambian el esquema de base de datos. Hacerlo sin estas dos piezas significa migrar a mano en cada entorno y no tener forma de saber si algo se rompió.

### 1.1 · Introducir Alembic — ✅ hecho

Hoy no hay ninguna herramienta de migración. El esquema es `create_all` más una pila de `ALTER TABLE` imperativos acumulados dentro de `init_db()` (`app/database.py:190-288`). `create_all` nunca modifica tablas existentes: por eso las columnas `embedding vector(1536)` hubo que añadirlas a mano en las líneas 274-276.

- **Cambio:** añadir `alembic` a `requirements.txt`, generar la revisión inicial a partir del esquema actual y mover ahí los `ALTER`, las columnas generadas `tsvector` y los índices GIN/trigram. Dejar `init_db()` solo con `CREATE EXTENSION` y la semilla del admin.
- **Por qué ahora:** a partir de la fase 2 cada paso añade tablas o columnas. Sin esto, cada uno es una migración manual en cada entorno.
- **Hecho (2026-09-11):** dos revisiones. `a511c79f0cbd` crea el esquema completo (extensiones `vector`/`unaccent`/`pg_trgm`, configuración `spanish_unaccent` y las 8 tablas); `b1f4c2d93e77` añade las 6 columnas generadas `tsvector` y los 15 índices GIN y trigram, que no pueden vivir en los modelos por ser `GENERATED ALWAYS AS ... STORED`. `init_db()` pasa de 151 líneas de DDL imperativo a llamar a `_ejecutar_migraciones()` y sembrar el admin.
- **Adopción de bases existentes:** si encuentra tablas sin `alembic_version`, marca la base en `head` en lugar de recrear el esquema. Así la base de desarrollo actual, con datos reales, se incorporó sin tocar una sola fila.
- **Verificación:** probado en los dos escenarios sobre bases desechables — vacía (aplica ambas revisiones: 8 tablas, 6 columnas tsv, 15 índices) y preexistente sin historial (marca en `head` y conserva el esquema). Después, aplicado al stack real: `healthy`, `/health` 200, 28 manuales, 170 páginas, 30 vídeos, 47 tickets y 5 usuarios intactos.

### 1.2 · Aislar los tests de la base de datos de desarrollo — 🟡 a medias

`tests/conftest.py` solo sobrescribe `SECRET_KEY` (línea 17). No fija `DATABASE_URL` ni usa una base de pruebas. Al instanciar `TestClient(app)` se dispara el lifespan de `app/main.py`, que ejecuta `init_db()` y `sincronizar_manuales()` sobre el Postgres de desarrollo.

Además `tests/api/test_sat_email.py` no es hermético: usa `urllib.request` contra `http://localhost:8000` con credenciales fijas, y **escribe tickets reales** en cada ejecución de `pytest`. Solo pasa porque el stack Docker está levantado; en cualquier máquina sin él, falla.

- **Hecho (2026-09-11):** el `client` de `tests/conftest.py` neutraliza `init_db()` durante el lifespan, y `test_sat_email.py` se ha movido a `tools/manual_checks/test_flujo_sat_email.py`, que es lo que siempre fue. La suite pasó de 60,7 s a 10,6 s porque ya no intenta alcanzar la base de datos. El recuento baja de 69 a **68** tests: no se ha perdido cobertura, se ha dejado de contar un script manual como test.
- **Pendiente:** `DATABASE_URL` propia de pruebas con `create_all`/`drop_all` por sesión, para poder dejar de mockear `SessionLocal` y probar el SQL de verdad. `sincronizar_manuales()` sigue ejecutándose en el lifespan de los tests (su excepción ya está capturada en `app/main.py:44`, así que solo produce un aviso).

### 1.3 · Poder medir la cobertura

`pytest-cov` no está declarado en `requirements.txt`, así que el proyecto no puede medir su propia cobertura. La cifra de 37 % de handlers ejercitados se obtuvo con un tracer ad-hoc.

- **Cambio:** añadir `pytest-cov` y separar `requirements-dev.txt` de `requirements.txt` (hoy `pytest` y `httpx` viven en el de producción).

### 1.4 · Cubrir los handlers que nunca se ejecutan

25 de los 40 handlers se quedan en el guardián RBAC y nunca entran en la función. Por orden de riesgo:

1. `app/routers/auth.py` — los 3 handlers. Login y cambio de contraseña sin probar.
2. `app/routers/buscar.py` — los 3 handlers. Es el corazón del producto.
3. `app/routers/manuales.py` — 6 de 9, incluido `descargar_pack_obra` (111 líneas).
4. `app/routers/usuarios.py` — 3 de 4, incluido el cambio de rol.
5. `app/main.py` — `/health`, del que depende el healthcheck de Docker.

> Ojo con la trampa que ya existe: `tests/api/test_tickets_sat.py` reimplementa en Python el filtrado y la búsqueda (`mock_obtener_tickets`, líneas 39-52). Esos tests validan el mock escrito en el propio test, no la consulta SQL. La paginación en SQL del commit `5041105` no tiene ninguna prueba que la ejecute.

---

## Fase 2 — G2 · Grupos de incidencia

**La pieza que más cosas desbloquea.** Hoy no existe la entidad: ni tabla, ni columna, ni endpoint, ni filtro. Lo único real es una taxonomía fija en HTML (un `select` de dispositivo y una botonera de áreas) que viaja al backend y se usa como prefijo cosmético.

Mientras esto no exista, G4, G12 y el corte por grupo de G15 no pueden existir, y todo lo demás sigue siendo hardcodeo disfrazado de cobertura.

| Paso | Cambio | Tamaño |
|---|---|---|
| 2.1 | Tabla `incident_groups` (`code`, `name`, `description`, `is_active`, `sort_order`) y semilla con las áreas que ya se usan hoy | S |
| 2.2 | Columna `grupo_id` en `tickets_sat`, nullable, con relleno retroactivo desde el prefijo actual | S |
| 2.3 | `GET /api/sat/grupos` y que el formulario lea de ahí en vez del HTML fijo | S |
| 2.4 | CRUD de administración: crear, editar, ordenar, activar y desactivar | M |
| 2.5 | Filtro por grupo en el listado de tickets | S |
| 2.6 | `tickets por grupo` en `/api/sat/tickets/stats` — **cierra G15 casi entero** | S |

Antes de 2.1 hace falta una decisión de producto, no de código: **qué grupos**. El documento de V1 propone no pasar de 8-12 (Conectividad, Control, Instalación, Configuración, App, Cuenta, Sensores, Firmware, Integraciones, Seguridad, Cloud, Hardware). Los 44 tickets reales que ya hay en la base de datos son la mejor fuente para validar esa lista.

---

## Fase 3 — G10 · Cierre técnico estructurado

Barato y de efecto inmediato. Hoy solo hay un `estado` genérico y un campo libre `solucion` (`app/database.py:134`): al cerrar un ticket no se captura nada aprovechable.

| Paso | Cambio | Tamaño |
|---|---|---|
| 3.1 | Seis campos en `tickets_sat`: `resolved`, `resolution_description`, `documentation_sufficient`, `document_used`, `alternative_solution`, `escalated` | S |
| 3.2 | Formulario de cierre que los pida | M |
| 3.3 | Métrica `% documentación suficiente` en stats | S |

Sale antes que G3 porque no depende de nada, se justifica solo y es lo que alimenta G11 (tareas de conocimiento) y G13 (casos resueltos). Con 3.1 y 3.3 hechos, ya se puede responder a *«¿nuestra documentación resuelve las incidencias?»*, que es la pregunta de fondo del proyecto.

---

## Fase 4 — G3 y G4 · Preguntas configurables

El cuestionario funciona de punta a punta, pero son 12 bloques HTML con ~80 ids fijos y un árbol `if/elif` de 13 ramas. `evaluar_cuestionario_asistencia()` ocupa 446 de las 630 líneas de `app/sat_autoresolver.py` — el 71 % del fichero.

Hay además un agujero silencioso: **las respuestas del técnico no se guardan en ningún sitio**. `TicketSAT` no tiene columna para el cuestionario contestado, así que el diagnóstico se calcula y se pierde.

| Paso | Cambio | Tamaño |
|---|---|---|
| 4.1 | Persistir las respuestas del cuestionario en el ticket — valioso por sí solo, sin tocar el motor | S |
| 4.2 | Tabla `questions` con `scope` (`VITAL` / `GROUP` / `INCIDENT`), tipo, orden y obligatoriedad | M |
| 4.3 | Relación `incident_group_questions` (depende de la fase 2) | S |
| 4.4 | Que el formulario se renderice desde la base de datos en vez de HTML fijo | L |
| 4.5 | Condiciones declarativas `mostrar_si`, en lugar de las 4 líneas de `app.js` que ocultan bloques por literal de dispositivo | M |

**Empezar por 4.1.** Es pequeño, no rompe nada, y a partir de ese día se acumulan datos reales que hacen falta para diseñar bien 4.2.

> Detalle a corregir en 4.5: hoy los bloques ocultos **siguen enviando sus respuestas por defecto** al backend.

---

## Fase 5 — Decisiones, no trabajo

Estas tres no son tareas: son preguntas que conviene cerrar en reunión, porque determinan el alcance real de la V1.

### 5.1 · ¿Los embeddings entran en la V1? (G7, G13)

La búsqueda léxica es sólida y real: `tsvector`, `unaccent`, `pg_trgm`, configuración `spanish_unaccent`, PDFs con OCR. Lo semántico **no existe**: hay columnas `Vector(1536)` en 4 tablas, 0 filas con embedding y ninguna llamada que las escriba o lea. No hay ningún SDK de embeddings en `requirements.txt`.

Es la brecha más grande entre lo que asume la documentación y lo que hay. Decidir explícitamente: entra en V1, o se pospone y se deja de contar como cubierto.

### 5.2 · ¿Se migra el almacenamiento a S3? (G9)

Hoy es disco local con bind mount. No hay `boto3` ni ningún SDK. Los 222 MB de PDFs viven solo en este portátil, `manuales/` está en `.gitignore` y no hay ninguna copia de seguridad — ni de los ficheros ni de la base de datos.

Independientemente de la decisión sobre S3, **la ausencia de backups es un riesgo activo hoy**: un `docker compose down -v` destruye contenido no recuperable.

### 5.3 · ¿Cloud IoT sigue siendo V1.1? (G14)

`rssi` y `firmware` son campos de texto que rellena una persona, no telemetría. El propio documento del jefe lo sitúa en V1.1. Conviene confirmarlo para que no se cuele en el alcance.

### 5.4 · Aclarar el rol «invitado» (G16)

Los roles reales de servidor son tres: `admin`, `tecnico` y `comercial`, con JWT y bcrypt de verdad (`app/auth.py:99-115`). **«invitado» no es un rol de backend**: es un valor en `localStorage` sin token (`app/static/app.js:355-380`). Conviene aclararlo antes de que el diseño de permisos granulares lo dé por existente.

---

## Anexo A — Documentación contra realidad

Cuatro afirmaciones del repositorio que no se sostienen al abrir el código. Se dejan registradas para que no vuelvan a darse por buenas.

| Afirmación | Realidad verificada |
|---|---|
| 37 tests activos | **69** (`pytest --collect-only`), pero solo el 37 % de los handlers ejecuta su cuerpo |
| Publicación en S3 cubierta | Disco local y bind mount. Sin `boto3` ni ningún SDK de objetos |
| Embeddings / pgvector integrados | Solo columnas. **0 filas** con embedding, 0 llamadas |
| 30 vídeos con transcripción y timestamp | 30 vídeos, pero `video_fragmentos` está **vacía**: todo resultado cae a 00:00 |

---

## Anexo B — Deuda técnica registrada, fuera del camino crítico

No bloquean la V1, pero conviene que estén escritas:

- **`app/static/app.js` son 4.836 líneas** y el JS total (6.178) pesa más que todo el Python de la aplicación (4.230). Sin build, sin minificado y sin un solo test.
- **`inicializarLaboratorioIntegral` está definida dos veces**, en `app.js:4831` y en `laboratorio.js:281`, y ambas se asignan a `window`. Funciona solo por el orden de carga en `index.html:321-322`; la de `app.js` es código muerto.
- **El versionado de caché de estáticos es manual** (`app.js?v=34`, `laboratorio.js?v=1`). Es fácil olvidarlo al desplegar y servir JS obsoleto.
- **Tailwind se carga por CDN** (`index.html:19`), lo que añade una dependencia externa en tiempo de ejecución y no está recomendado para producción.
- **`tools/manual_checks/`** son 487 líneas en ficheros llamados `test_*.py` que `pytest` no recoge (`testpaths=tests`). El nombre induce a pensar que son tests automatizados; son scripts que exigen un servidor en `localhost:8000`.
- **El rate limiting de login es evitable con una cabecera.** `app/auth.py:117-126` exime a cualquier IP que empiece por `10.`, `172.` o `192.168.`, y dentro de Docker el tráfico llega desde la red bridge `172.x`, con lo que queda desactivado de facto.
- **El token JWT se acepta por query string** (`app/auth.py:51` y `81`), con 24 h de validez, sin refresh ni revocación.
- **`sincronizar_manuales()` se ejecuta de forma síncrona en el arranque** (`app/main.py:43-44`), bloqueando el event loop con OCR incluido antes de aceptar tráfico.
- **No hay CI.** No existe `.github/workflows` ni ningún pipeline que ejecute los 69 tests.

---

## Cómo mantener este documento

Cada paso completado se marca aquí con el hash del commit que lo cierra. Si una fase cambia de orden, se anota por qué. Este fichero y el panel visual son la única fuente de estado del proyecto: `README.md`, `DOCUMENTACION_SISTEMA.md` y `dossier_tecnico_y_operativo.md` describen la visión, no lo implementado.
