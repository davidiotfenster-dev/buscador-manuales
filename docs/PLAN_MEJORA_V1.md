# Plan de mejora incremental — Gestor de Soporte V1

> **Corte:** 2026-09-11 · rama `feature/mejora-simulador-laboratorio` · 33 commits
> **Método:** estado verificado abriendo el código y consultando la base de datos en ejecución. No se ha usado `README.md`, `DOCUMENTACION_SISTEMA.md` ni `dossier_tecnico_y_operativo.md` como fuente, porque sobrevaloran el estado real (ver [Anexo A](#anexo-a--documentación-contra-realidad)).
> **Panel visual:** https://claude.ai/code/artifact/d2c15cc6-4dee-4af8-bf02-27e577d356f2
> — corregido el 14/09 contra el documento de Notion: G1 vuelve a ser «Descubrimiento con el equipo de soporte» (no el gestor de tickets), la media real baja de 38 % a **35 %**, el flujo recupera los 13 eslabones del diagrama y los riesgos ya distinguen los 5 cerrados de los 3 abiertos. Detalle en el Registro de Cambios del README.
> **Resumen de la sesión del 11/09:** [`RESUMEN_2026-09-11.md`](RESUMEN_2026-09-11.md)
> **G1 (descubrimiento):** [`G1_DESCUBRIMIENTO_SAT.md`](G1_DESCUBRIMIENTO_SAT.md) — inventario (1.2) y priorización (1.3) cerrados el 14/09 con las 119 incidencias reales; queda celebrar la reunión (1.1).

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
- **Cómo hacerlo** — `tools/rotar_secret_key.py`. Guarda la anterior en `copias/` y **cierra todas las sesiones abiertas**:

  ```
  python tools/rotar_secret_key.py
  docker compose up -d --force-recreate web
  ```

  Es un script y no una línea suelta porque la línea suelta no sobrevive a PowerShell: las comillas se pierden al pasar el código a `python` y la orden falla a medias, que en un fichero de configuración es justo lo que no se quiere. El script no escribe nada si no encuentra exactamente una línea `SECRET_KEY=`.

### 0.3 · Contraseña de PostgreSQL por defecto — ✅ hecho

`docker-compose.yml` usa `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-cambiar_en_produccion}`, y `app/database.py:18-21` tiene un fallback `postgres:password@localhost`. Mismo tratamiento que 0.2: sin variable, sin arranque.

### 0.4 · El `.dockerignore` mete los secretos en la imagen — ✅ hecho

El `Dockerfile` hace `COPY . .` y el `.dockerignore` actual solo excluye `manuales/`, `scratch/`, `__pycache__/`, `*.pyc`, `.git/` y `.venv/`. Dos consecuencias:

- El `.env` real (con `SECRET_KEY`, `POSTGRES_PASSWORD` y `ADMIN_DEFAULT_PASSWORD`) queda dentro de una capa de la imagen.
- El virtualenv real se llama `venv/`, no `.venv/`, así que sus ~296 MB también entran.

- **Cambio:** añadir `.env`, `venv/` y `cache_miniaturas/` al `.dockerignore`.

### 0.5 · El envío de correo informa de éxito sin enviar nada — ✅ hecho (falta el buzón)

`app/email_sender.py:231-235` devuelve `{"enviado": True, "modo": "simulado"}` cuando faltan `SMTP_HOST`, `SMTP_USER` o `SMTP_PASSWORD` — que no aparecen ni en `.env.example` ni en `docker-compose.yml`. El técnico recibe confirmación de que el parte SAT salió cuando solo se ha escrito un log.

- **Cambio:** en modo simulado devolver `enviado: false`. Configurar SMTP de verdad, o dejar explícito en la interfaz que el envío está desactivado.
- **2026-09-16:** el circuito estaba cortado en un segundo sitio que el diagnóstico de arriba señalaba sin sacar la consecuencia. `email_sender.py` lee las variables del **entorno del proceso**, y `docker-compose.yml` no las pasaba: rellenar el `.env` no habría cambiado nada, y el fallo no daba señal. Las siete variables se pasan ya al contenedor y están documentadas en `.env.example`.
- **Pendiente, y es una decisión de producto, no de código:** qué buzón usa esto. Hasta rellenarlo, **ningún parte SAT sale de la aplicación** — se genera el PDF, se avisa de que no ha salido, y hay que hacerlo llegar a mano.

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

### 1.2 · Aislar los tests de la base de datos de desarrollo — ✅ hecho

`tests/conftest.py` solo sobrescribe `SECRET_KEY` (línea 17). No fija `DATABASE_URL` ni usa una base de pruebas. Al instanciar `TestClient(app)` se dispara el lifespan de `app/main.py`, que ejecuta `init_db()` y `sincronizar_manuales()` sobre el Postgres de desarrollo.

Además `tests/api/test_sat_email.py` no es hermético: usa `urllib.request` contra `http://localhost:8000` con credenciales fijas, y **escribe tickets reales** en cada ejecución de `pytest`. Solo pasa porque el stack Docker está levantado; en cualquier máquina sin él, falla.

- **Hecho (2026-09-11):** el `client` de `tests/conftest.py` neutraliza `init_db()` durante el lifespan, y `test_sat_email.py` se ha movido a `tools/manual_checks/test_flujo_sat_email.py`, que es lo que siempre fue. La suite pasó de 60,7 s a 10,6 s porque ya no intenta alcanzar la base de datos. El recuento baja de 69 a **68** tests: no se ha perdido cobertura, se ha dejado de contar un script manual como test.
- **Cerrado (2026-09-11):** el fixture `url_bd_pruebas` crea una base `buscador_manuales_test` desde cero, le aplica las migraciones de Alembic y la destruye al terminar; `db` entrega una sesión con las tablas vacías antes de cada test. La base se toma de `TEST_DATABASE_URL` o se compone desde el `.env`, y si PostgreSQL no está accesible los tests se **omiten** en vez de fallar, así que la suite sigue siendo ejecutable sin el stack.
- Para que esto funcione desde el host, `docker-compose.yml` publica PostgreSQL **solo en la interfaz de loopback** (`127.0.0.1:5432:5432`). En un despliegue real esa sección debe eliminarse.
- `sincronizar_manuales()` sigue ejecutándose en el lifespan de los tests; su excepción está capturada en `app/main.py:44`, así que solo produce un aviso.

### 1.3 · Poder medir la cobertura — ✅ hecho

`pytest-cov` no está declarado en `requirements.txt`, así que el proyecto no puede medir su propia cobertura. La cifra de 37 % de handlers ejercitados se obtuvo con un tracer ad-hoc.

- **Hecho (2026-09-11):** `requirements-dev.txt` separado, con `pytest`, `pytest-cov`, `httpx` y `requests` fuera de la imagen Docker. `requests` no lo importa `app/` en ningún sitio: solo los scripts de `tools/manual_checks/`.
- **Primera medición real: 51 % de cobertura** sobre 2.071 sentencias. Los puntos más bajos: `email_sender.py` 0 %, `videos.py` 32 %, `auth.py` (router) 38 %, `database.py` 39 %, `manuales.py` 41 %.

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

| Paso | Cambio | Estado |
|---|---|---|
| 2.1 | Tabla `incident_groups` (`code`, `name`, `description`, `is_active`, `sort_order`) sembrada con los 9 grupos | ✅ hecho |
| 2.2 | Columna `grupo_id` en `tickets_sat` y tabla `ticket_grupos_secundarios` | ✅ hecho |
| 2.3 | `GET /api/sat/grupos` y formulario que lee de ahí | ✅ hecho |
| 2.4 | CRUD de administración: crear, editar, ordenar, activar y desactivar | ✅ *(2026-09-14)* modal solo admin, más **fusionar** y marcar «nuevo / en revisión». Un grupo con tickets no se borra: 409 con el recuento |
| 2.5 | Filtro por grupo en el listado de tickets | ✅ hecho |
| 2.6 | `tickets por grupo` en `/api/sat/tickets/stats` — **cierra G15 casi entero** | ✅ hecho |

**Hecho (2026-09-11), migración `3f514b913e75`.** Datos, API e interfaz de uso cerrados. Solo queda el CRUD de administración (2.4): hoy los grupos se editan con una migración, no desde la aplicación.

**Decisión tomada sobre la clasificación múltiple:** grupo principal (`tickets_sat.grupo_id`) más secundarios opcionales (`ticket_grupos_secundarios`). El principal decide qué preguntas mostrará el cuestionario; los secundarios recogen el resto de etiquetas y alimentan las métricas. Se eligió así porque el 46 % de las incidencias reales lleva más de una etiqueta y un único `grupo_id` habría perdido esa información. **Es una asunción revisable en la reunión**, no una decisión cerrada.

- Un código de grupo desconocido deja el ticket sin clasificar en lugar de rechazar el alta: el alta llega desde tres puntos distintos de la interfaz y perder un parte SAT por un código mal escrito sería peor.
- `contar_tickets_por_grupo()` usa LEFT JOIN para que **un grupo sin tickets también aparezca**: una rama vacía de la taxonomía es información, dice que ese grupo no se usa.
- 13 tests de integración en `tests/integration/test_grupos_incidencia.py`. La suite pasa de 83 a **96 tests**.

**Resuelto el 2026-09-14, por otra vía.** Los 47 tickets existentes se quedaron sin grupo, y aquí se dio por bueno que era una decisión: 39 eran el mismo ticket de prueba repetido. Era cierto, pero no era la razón. Al comprobar el flujo de alta apareció que **`TicketSATCreate` no declaraba el campo `grupo`**, así que el selector del formulario lo enviaba y pydantic lo descartaba en silencio: no había forma de clasificar un ticket ni queriendo. Corregido, junto con el PUT.

En lugar de clasificar los 47 de prueba, se importaron las **119 incidencias reales** ya clasificadas desde su propia etiqueta (ver Fase 2bis).

Antes de 2.1 hace falta una decisión de producto, no de código: **qué grupos**.

**Preparado (2026-09-11):** [`G2_TAXONOMIA_GRUPOS.md`](G2_TAXONOMIA_GRUPOS.md) analiza las **119 incidencias reales** de `data/sat/Incidencias.xlsx` y propone una lista de 9 grupos. Conclusión principal: la taxonomía **ya existe** — SAT lleva tiempo etiquetando en el campo `problema`, con 11 etiquetas. El workshop no tiene que inventarla, sino validarla.

Tres hallazgos que condicionan el esquema, y que hay que cerrar antes de crear la tabla:

- **El 46 % de las incidencias lleva dos o más etiquetas.** El flujo de la V1 asume un grupo por ticket. Hay que decidir entre `grupo_id` único o principal + secundarios.
- **El 25 % no encaja en ningún grupo** (17 sin etiquetar + 13 «Otro»). G12 no es un extra: es una cuarta parte de los casos.
- **«Sensor de Apertura» tiene 1 incidencia de 119**, justo el ejemplo que puso el jefe. No debe ser grupo de primer nivel.

> Los tickets de `tickets_sat` **no sirven** como muestra: 39 de 47 son el mismo ticket de prueba repetido por el script de humo.

---

## Fase 2bis — El histórico real, clasificado ✅ *(2026-09-14)*

G2 dejó la taxonomía montada pero sin una sola incidencia clasificada. Los 47 tickets de la base no eran historial: seis casos distintos, uno repetido 39 veces, creados por el mismo administrador entre el 8 y el 11 de septiembre con instaladores llamados `ndasf` y `Pedro Tecnico Test`.

El historial real —las 119 incidencias de `data/sat/Incidencias.xlsx`, las mismas que definieron los grupos— nunca había llegado a la base de datos. Y su columna «Problema» ya trae las etiquetas que puso SAT, así que la clasificación **no se inventa: se traduce**.

`tools/importar_incidencias.py`, con `--dry-run` e idempotente por `numero_ticket` (`SAT-HIST-0001`…).

| Grupo | Principal | Secundario | Total | Lo que decía G2 |
|---|---:|---:|---:|---:|
| VINCULACION | 28 | 13 | 41 | 41 |
| GESTUAL | 20 | 11 | 31 | 31 |
| CONECTIVIDAD | 10 | 19 | 29 | 29 |
| APP | 15 | 13 | 28 | 28 |
| PULSADOR | 13 | 2 | 15 | 15 |
| INTEGRACIONES | 9 | 2 | 11 | 11 |
| INSTALACION | 3 | 4 | 7 | 7 |
| HARDWARE | 2 | 4 | 6 | 6 |
| OTRO | 19 | 12 | 31 | 30 + «Sensor de Apertura» |

**55 de las 119 (46 %) llevan más de un grupo**, exactamente el porcentaje medido en G2. Es la confirmación de que la decisión de principal + secundarios era la correcta.

**Dos reglas del mapeo que conviene revisar en la reunión:**

1. **`OTRO` no manda si hay algo más concreto.** «Otro, Instalación» se clasifica como `INSTALACION` con `OTRO` de secundario. Afecta a 5 casos. Si SAT usa «Otro» para decir «esto no encaja en nada», la regla debería ser la contraria.
2. **Las 17 celdas vacías van a `OTRO`.** Omitirlas habría falseado los totales, pero mezclan «no encaja» con «no se etiquetó», que no es lo mismo. Es justamente la pregunta 4 de la agenda.

**Lo que queda.** Los 47 tickets de prueba siguen en la base y aparecen como «sin grupo asignado» en las métricas. Borrarlos es irreversible y se deja en manos de quien decida hacerlo; hay copia previa en `copias/`.

---

## Fase 3 — G10 · Cierre técnico estructurado ✅ *(2026-09-14)*

Barato y de efecto inmediato. Hasta hoy solo había un `estado` genérico y un campo libre `solucion`: al cerrar un ticket no se capturaba nada aprovechable.

| Paso | Cambio | Tamaño | Estado |
|---|---|---|---|
| 3.1 | Seis campos en `tickets_sat`: `resolved`, `resolution_description`, `documentation_sufficient`, `document_used`, `alternative_solution`, `escalated` | S | ✅ migración `eec0dc7833f3`, 10 columnas `cierre_*` |
| 3.2 | Formulario de cierre que los pida | M | ✅ modal, insignia en la tarjeta y `POST /api/sat/tickets/{id}/cierre` |
| 3.3 | Métrica `% documentación suficiente` en stats | S | ✅ bloque `cierre` en `/stats` y KPI en la vista |

Salió antes que G3 porque no dependía de nada, se justifica solo y es lo que alimenta G11 (tareas de conocimiento) y G13 (casos resueltos). **Ya se puede responder a *«¿nuestra documentación resuelve las incidencias?»***, que es la pregunta de fondo del proyecto.

Lo que se decidió al construirlo, por si hay que revisarlo:

- **Solo dos campos obligatorios** (`resuelto` y `documentacion_suficiente`), porque un técnico al teléfono no rellena seis y exigírselos acabaría en tickets sin cerrar.
- **El `PUT` rechaza pasar a `resuelto` sin cierre** (400). Un ticket resuelto sin cierre es un agujero permanente en la métrica.
- **Los porcentajes se calculan sobre los cerrados**, nunca sobre el total, y con cero cierres devuelven `null` en vez de `0`.
- **El cierre no toca el estado**: se puede cerrar diciendo que no se resolvió y seguir en `rma_pendiente`.

Queda fuera, para cuando haga falta: extraer de los cierres un `case_document` que alimente G13, y usar `documentos_mas_usados` para priorizar qué documentación escribir (G9).

---

## Fase 3bis — G10 con datos reales ✅ *(2026-09-16)*

La Fase 3 construyó el cierre. Dos días después seguía **sin un solo ticket cerrado**: el formulario existía, la métrica existía, y medía sobre cero. Un indicador construido que nadie alimenta no es un indicador, es una promesa.

Los 119 tickets del histórico traían la columna «Acción» del Excel, que no es texto libre sino un vocabulario cerrado de doce acciones. `tools/cerrar_historico.py` deduce de ahí el cierre —resuelto, documentación suficiente, escalado— sin inventarlo, del mismo modo que «Problema» permitió clasificar por grupo.

**89 cierres escritos. G10 pasa de `null` a 76,7 %.** Y por grupo, que es donde sirve: GESTUAL 64 %, PULSADOR 70 %, frente a VINCULACION 89 % y APP 91 %.

**Esto responde a la pregunta de fondo del proyecto con datos y no con una estimación.** Donde la documentación falla más es en gestual y pulsador — que son justo los grupos con vídeos del canal. La primera pista con datos sobre qué escribir (G9) sale de aquí, no de una reunión.

Tres cosas que conviene no perder de vista al leer ese 76,7 %:

- **Es histórico, no es el presente.** Son cierres deducidos de lo que SAT hizo en su día, marcados con `cierre_por = 'historico-excel'`. En cuanto haya cierres reales convendrá mirar los dos números por separado.
- **Una llamada cuenta como «explicar».** Aparece en 62 de 119; tratarla como fracaso de la documentación diría que casi nada funciona. Es la decisión más discutible de la traducción y la que más movería el porcentaje si se cambia.
- **El tiempo medio hasta el cierre los excluye.** El Excel no traía fechas, así que su `cierre_fecha` es la de importación. Contarlos metía 89 casos de cero horas.

Lo que sigue sin poder responderse: **qué documento concreto resuelve**. «Videos» dice que se mandaron vídeos, no cuál, así que `documentos_mas_usados` sigue vacío y solo se llenará con cierres reales. Es el dato que G9 necesita para priorizar de verdad.

---

## Fase 3ter — La copia de seguridad que no existía ✅ *(2026-09-16)*

Fuera del camino de funcionalidad, pero por delante de todo lo demás en riesgo: la base de datos vive en el volumen `pgdata` y un `docker compose down -v` la borra sin preguntar. A 2026-09-16 eso son 119 incidencias reales, 1.132 fragmentos de vídeo, 18 manuales y 110 cuestionarios, **ninguno recuperable**.

`tools/copia_seguridad.py` vuelca, comprime, rota y con `--verificar` restaura en una base desechable y compara los recuentos. Una copia que nunca se ha restaurado no es una copia.

Esto **no** cierra 5.2 (S3): `copias/` está en el mismo disco que los datos. Protege de un `down -v`, de un borrado por SQL y de una migración que salga mal, no de que se rompa el disco. Lo que sí hace es quitar la urgencia: la decisión de S3 puede tomarse con calma en vez de a la carrera.

---

## Fase 4 — G3 y G4 · Preguntas configurables

El cuestionario funciona de punta a punta, pero son 12 bloques HTML con ~80 ids fijos y un árbol `if/elif` de 13 ramas. `evaluar_cuestionario_asistencia()` ocupa 446 de las 630 líneas de `app/sat_autoresolver.py` — el 71 % del fichero.

Había además un agujero silencioso: **las respuestas del técnico no se guardaban en ningún sitio**, así que el diagnóstico se calculaba y se perdía. **Resuelto el 2026-09-14** (paso 4.1).

| Paso | Cambio | Tamaño |
|---|---|---|
| 4.1 | ✅ *(2026-09-14)* Persistir las respuestas del cuestionario. Tabla `cuestionarios_asistencia`, atada al ticket cuando sale uno, más un endpoint de estadísticas sobre qué campos se rellenan de verdad | S |
| 4.2 | Tabla `questions` con `scope` (`VITAL` / `GROUP` / `INCIDENT`), tipo, orden y obligatoriedad | M |
| 4.3 | Relación `incident_group_questions` (depende de la fase 2) | S |
| 4.4 | Que el formulario se renderice desde la base de datos en vez de HTML fijo | L |
| 4.5 | Condiciones declarativas `mostrar_si`, en lugar de las 4 líneas de `app.js` que ocultan bloques por literal de dispositivo | M |

**4.1 hecho, y ese era el orden correcto.** Desde ahora se acumulan datos reales, que son los que hacen falta para diseñar 4.2 con criterio en vez de a ojo. `GET /api/sat/cuestionarios/stats` dice qué porcentaje de envíos rellena cada campo: **un campo que no toca nadie sobra del formulario, y uno que se rellena siempre es candidato a obligatorio**. Conviene dejar pasar unas semanas de uso real antes de atacar 4.2.

Se guarda el envío entero como JSON y no una columna por pregunta, precisamente porque 4.2 va a cambiar las preguntas: una tabla con ochenta columnas quedaría obsoleta a la primera.

> Detalle a corregir en 4.5: hoy los bloques ocultos **siguen enviando sus respuestas por defecto** al backend.

---

## Fase 4bis — Los vídeos del canal como documentación ✅ *(2026-09-14)*

**El problema.** Los 43 vídeos del canal son grabaciones de pantalla **sin narración**. YouTube no ofrece transcripción de ninguno, así que la tabla `videos` no tenía más texto que el título: el catálogo entero era invisible para el buscador. Se había llegado a dar por inviable la búsqueda por minuto con marca de tiempo por esta razón.

**La salida.** El pipeline `../descarga-videos` no depende del audio: extrae fotogramas clave con OpenCV y los describe con un modelo de visión, produciendo por cada vídeo una lista de pasos con su segundo. Eso son los fragmentos que le faltaban a `video_fragmentos`, así que la búsqueda por minuto **sí es alcanzable** — solo que el texto viene de la imagen y no del sonido.

| Antes | Después |
|---|---|
| 30 vídeos (de 43), 3 con texto | 43 vídeos, 43 con texto |
| 63 fragmentos | 1132 fragmentos con su segundo |
| Categoría `VISUAL_APP` para todos | Categorías reales, el mismo vocabulario que los grupos de incidencia |

**Por qué importa para el cierre del ticket.** Al compartir vocabulario con `incident_groups`, un ticket del grupo `VINCULACION` propone los seis vídeos de vinculación, y el enlace cae en el segundo exacto. Es lo que un manual en PDF no puede dar. **Hecho el mismo día**: `GET /api/sat/tickets/{id}/documentacion-sugerida` y las sugerencias en el modal de cierre, con el motivo de cada una.

**La señal más fuerte ya está alimentada.** El grupo de incidencia pesa más que el resto, y hasta el 2026-09-14 ningún ticket lo tenía. Con las 119 incidencias reales importadas y clasificadas, un ticket de `INSTALACION` sobre un Connect-1 recibe *«¿Cómo se instala Connect-1?»* con `Mismo grupo + Mismo dispositivo` (4.5), en vez de depender solo de cómo esté redactado el síntoma.

**Lo que se corrigió en este repositorio** está detallado en el README (entrada del 2026-09-14). Lo más serio: `insertar_video()` borraba el texto y los fragmentos en cada llamada, de modo que una sola alta repetida destruía horas de pipeline sin dejar rastro.

---

## Fase 4ter — La ingesta de PDF, verificada ✅ *(2026-09-14)*

Se comprobó de punta a punta qué pasa al subir un manual nuevo, con un PDF de cada tipo fabricado a propósito. El camino principal funcionaba: capa de texto cuando la hay, OCR en español cuando la página es una imagen. Lo que apareció fueron **tres formas distintas de perder texto en silencio**, todas de la misma familia que el fallo de los vídeos.

1. **Dos implementaciones de lo mismo.** La subida hacía OCR; `sync_manuales.py` no. Como «Reindexar» usa la segunda, pulsarlo vaciaba todos los manuales escaneados. Unificado en `app/extraccion_pdf.py`.
2. **El escaneo con pie de página.** Se decidía por «¿hay algo de texto?», y un número de página bastaba para saltarse el OCR y tirar el contenido. Ahora decide por cantidad, con un umbral de 100 caracteres.
3. **Metadatos reescritos en cada arranque.** `obtener_manual_por_archivo()` no devolvía `categoria` ni `etiquetas`, así que el sincronizador creía que a todos los manuales les faltaban metadatos y los sobrescribía enteros al iniciar. El dispositivo elegido al subir se perdía en el siguiente reinicio.

Hay además una trampa de infraestructura que ya había mordido antes con `alembic/`: **`sync_manuales.py` es el único módulo de la aplicación que vive fuera de `app/`**, y el bind mount no lo cubría. La corrección del punto 1 no surtía efecto hasta reconstruir la imagen. Ya está montado.

> **Regla que sale de aquí.** Cada vez que algo se escribe desde dos sitios —la subida y el sincronizador, el pipeline de vídeos y el botón de sincronizar— hay que preguntarse qué pasa cuando el segundo se ejecuta después del primero. En este proyecto la respuesta ha sido tres veces la misma: borra lo que hizo el primero, sin error y sin aviso.

---

## Fase 4quater — Asistencia SAT, la pantalla 🧪 *(2026-09-16, sin aceptar)*

Rama `feature/rediseno-asistencia-sat`. **Experimento de visualización a la espera de aceptarse o descartarse.** Ninguna regla de diagnóstico cambia: `evaluar_cuestionario_asistencia()` no se toca, y los ~80 ids que lee siguen donde estaban.

Los 12 bloques del cuestionario pasan a 5 pasos navegables, y el veredicto —lo que el sistema deduce, que es la razón de ser de la pantalla— pasa de ser un bloque de texto más a ocupar la columna derecha entera, con semáforo de certeza y el paso a dar ahora.

Por el camino salieron cuatro fallos, **los cuatro del mismo tipo**: algo escrito desde dos sitios donde el segundo borra al primero sin dar señal. Es el mismo patrón del Anexo A, y esto lo sube a ocho apariciones en el proyecto. El más caro: «Reiniciar respuestas» limpiaba 4 campos de ~20, así que el formulario *parecía* limpio y el diagnóstico siguiente salía contaminado con el caso anterior.

**Lo que esta fase deja abierto, y son decisiones de producto:**

### 4q.1 · Los dos vocabularios: 10 «áreas» contra 9 grupos

El cuestionario pregunta por 10 áreas; el sistema clasifica en 9 grupos salidos de las 119 incidencias. Hoy se traducen las 5 que significan lo mismo y el resto va **sin grupo a propósito**.

El caso que lo explica: «Dispositivo / electrónica» viene marcada por defecto, así que **no distingue a quien la eligió de quien no tocó nada**. Clasificar por ella llenaría HARDWARE de tickets que nadie clasificó, y un grupo equivocado hace más daño en las métricas que ninguno.

La salida limpia es que el paso «Qué le pasa» use directamente los 9 grupos y desaparezca la traducción. Eso toca el cuestionario, así que conviene resolverlo junto con 4.2 y no antes.

### 4q.2 · La lista de dispositivos

El desplegable no tiene `C-Pulsar`, y las 119 incidencias reales usan «Konect Elite», que tampoco está. Mientras no cuadren, la sugerencia de vídeo y manual pierde su segunda señal de más peso (`Mismo dispositivo`, 1.5).

Es lo más barato de los tres y no depende de nada: en cuanto haya lista buena, se cambia.

### 4q.3 · Sensores, OTA y Usuario/cuenta

Tres áreas del cuestionario que hoy caen en OTRO. OTRO es la entrada de G12 (grupos nuevos) y ya acumula 31 incidencias, así que el dato para decidir esto va a existir pronto.

---

## Fase 3quater — La ficha de obra 🧪 *(2026-09-17, sin aceptar)*

Rama `feature/ficha-de-obra`. Experimento: que al atender una llamada se vea lo que ya le pasó a esa obra.

**La premisa cambió al mirar los datos, y a mejor.** La idea de partida era avisar de incidencias *del mismo tipo*. De las 10 obras del histórico con más de una incidencia, solo una repite grupo: las otras nueve vuelven a llamar por otra cosa. **Lo que se repite no es la avería, es la obra.** Una ficha que solo avisara de coincidencias de grupo se callaría en nueve de cada diez casos en los que tiene algo que decir.

**El identificador es la obra y no el instalador**, porque los nombres tienen variantes (`Estela`/`Estella`, `María`/`Maria`, `Inma`/`Inmaculada`) y agrupar por ellos partiría el historial de la misma persona. `distribuidor` es la marca: 5 valores en 102 tickets.

Esto se apoya entero en dos cosas hechas antes: los **grupos de incidencia** (G2), sin los cuales no habría con qué comparar, y los **cierres derivados** (Fase 3bis), que son los que permiten decir cómo acabó cada antecedente. Una lista de fechas sin desenlace no cambia ningún diagnóstico.

**Qué queda por decidir:**

- **Dónde más debe aparecer.** Hoy solo en Asistencia SAT al salir del campo «Obra». El sitio natural que falta es la ficha del ticket abierto.
- **Si la obra debe dejar de ser texto libre.** Hoy se normaliza al comparar, que tapa el problema sin resolverlo. Un desplegable con las obras ya conocidas evitaría la variante desde el origen — y es el mismo problema que ya tienen los nombres de instalador.
- **Si esto pide una tabla `obras`** en vez de deducirla de los tickets. Hoy no hace falta y deducirla no cuesta nada; haría falta el día que una obra tenga datos propios (dirección, promotor, fecha de entrega).

**Su valor hoy es limitado y conviene decirlo:** con 119 incidencias, solo 10 obras repiten. El aviso saltará poco al principio. Crece con el uso, es barato, y no molesta cuando no tiene nada que decir.


---

## Fase 4quinquies — El diagnóstico del triaje ✅ *(2026-09-22)*

Rama `fix/triaje-sat-diagnostico-y-formulario`. La fase 4quater rediseñó la pantalla dejando el motor intacto a propósito. Al mirar el motor, resultó que **no diagnosticaba**.

`evaluar_cuestionario_asistencia()` elegía con trece `if/elif` y ganaba el primero que enganchaba. La rama 8 se cumplía con `tipo_red == "Dual 2,4/5 GHz"` y `ssid_separados == "No"`, que son las dos primeras `<option>` de los desplegables de Wi-Fi: **las que quedan puestas si nadie toca ese bloque**. Resultado: todo salía como «Band Steering Activo en Router», con un 92-95 % de confianza, incluida una alarma sin batería. Las ramas 9 a 13 eran inalcanzables.

**Es exactamente el problema de 4q.1**, que ya estaba escrito aquí: «"Dispositivo / electrónica" viene marcada por defecto, así que no distingue a quien la eligió de quien no tocó nada». Allí se vio en la clasificación por áreas y se resolvió no clasificando. En el motor de diagnóstico el mismo patrón llevaba un año decidiendo el diagnóstico entero y nadie lo había mirado. **Un valor por defecto no es una respuesta**, y conviene tratarlo como regla del proyecto y no como hallazgo suelto: van dos sitios.

El motor pasa a puntuación por señales con peso (`SENAL_FUERTE` 3,0 / `SENAL_MEDIA` 2,0 / `SENAL_DEBIL` 0,8 / `SENAL_FAMILIA` 1,2) y umbral 2,0, de modo que **una condición que puede venir por defecto no llega sola al umbral**. Sin evidencia suficiente se devuelve «Sin diagnóstico concluyente» con las preguntas que discriminan, en vez de afirmar el primero de la lista. Detalle completo en el `README.md`.

Sobrevivió porque los diez tests del cuestionario comprobaban el **guardado**, nunca el diagnóstico. Ahora hay 29 tests del motor, incluida una comprobación parametrizada de que las trece reglas siguen siendo alcanzables: es la que impide que esto vuelva.

**Lo que esta fase cierra de rebote:** los dos Excel de `data/sat/` (119 incidencias + 10 parejas problema-solución) se cargaban perfectamente y **`cargar_base_conocimiento_sat()` no se llamaba desde ningún punto del proyecto**. Eran código muerto. Ahora alimentan los casos parecidos que acompañan al diagnóstico.

**El cuestionario pasa a empezar por la persona.** No preguntaba el correo en ningún momento, y el nombre, la obra y el teléfono estaban al final del primer bloque como «Datos Opcionales de Referencia». El orden acordado es: quién llama → comercializadora y equipo → qué le pasa → el resto. El correo consulta el historial del cliente al salir del campo (`GET /api/sat/clientes/historial`, con igualdad exacta y rol técnico).

**Lo que deja abierto:**

- **Los datos de la persona viven en `respuestas_json`**, no como columnas de `cuestionarios_asistencia`. No hace falta migración y el ticket sí los guarda en columnas propias, pero no se pueden filtrar cuestionarios por cliente sin abrir el JSON. Si hace falta esa consulta, es una revisión de Alembic con `correo` indexado.
- **4q.2 sigue abierta y ahora pesa más.** Las reglas `sensores_c2`, `cwall` y `walarm` puntúan por familia de producto (`SENAL_FAMILIA`), así que dependen de que el desplegable de dispositivos diga la verdad. Falta `C-Pulsar`, y las 119 incidencias usan «Konect Elite», que tampoco está.
- **El umbral 2,0 y los cuatro pesos están puestos a ojo**, razonados pero sin datos. `GET /api/sat/cuestionarios` ya guarda cada envío con su diagnóstico: en cuanto haya unas decenas de casos reales se puede comprobar cuántos quedan en «no concluyente» y ajustar con datos en vez de con criterio.
- **El manual de reserva sigue siendo inventado.** Cuando la consulta no encuentra nada, se devuelve un `manual_id: 1` fijo con un nombre construido a mano. Es del mismo tipo que los avisos que arregló la Fase 0: enseña como real algo que no se ha encontrado.

---

## Fase 4sexies — Buscador y predicción que se mantienen solos ✅ *(2026-09-23)*

Rama `perf/buscador-y-triaje-rapidos-y-automaticos`. Detalle completo en el `README.md`; funcionamiento en `docs/TRIAJE_SAT.md` (sección 5 bis) y operación en `docs/METER_INFORMACION.md`.

Medido sobre la base real: búsqueda de **147 ms a 11 ms**, búsquedas sin resultado del **73 % al 2 %**, predicción del grupo del **38 % al 62 %** (84 % entre los tres primeros). La confianza de la predicción está calibrada: por encima de 0,6 acierta el 75-89 %.

**Lo que se probó y NO entró, para no repetirlo a ciegas:**

- **Índice con `spanish_unaccent`.** Arregla las tildes pero rompe las raíces: el extractor necesita la tilde para reconocer «-ación», e «instalación» dejaba de encontrar «instalar» e «instalaciones». Las tildes se resuelven en la consulta.
- **BM25.** Igual en la búsqueda general, peor en la del triaje (39 % frente a 49 % en el primer vídeo) y el doble de lento: premia las palabras raras y el nombre del dispositivo lo es. Reevaluar con `python -m app.calidad` cuando el corpus crezca.

**Lo que deja abierto:**

- **Faltan ejemplos en tres grupos.** INSTALACION (4 tickets) y HARDWARE (2) se aciertan el 0 % de las veces por pura falta de datos; OTRO tiene 19 pero casi todos «Incidencia sin descripción». Clasificar tickets de esos grupos es lo que más mejora la predicción, y no requiere tocar código.
- **Las categorías de vídeo y los grupos de ticket no son el mismo vocabulario** (seis contra nueve, cuatro en común). Unificarlos haría exacta la medida de acierto de la búsqueda, que hoy es aproximada. Es la misma familia de problema que 4q.1.
- **No hay documentación de batería** (WAlarm). «batería» no encuentra nada, y no es el buscador.
- **5.1 sigue sin decidir**, y conviene saber en qué estado está: las columnas de embeddings existen y están pobladas a medias (33/43 vídeos, 87/1132 fragmentos, 0 páginas, 0 tickets) por algún script antiguo. Nada las usa. Si se decide que sí, hay que poblarlas enteras antes de usarlas, o los resultados dependerán de qué filas tengan embedding.
- **`uvicorn` corre sin `--reload`** (correcto en producción), así que cambiar código exige `docker restart buscador_web`. Los datos no.

---

## Fase 5 — Decisiones, no trabajo

Estas tres no son tareas: son preguntas que conviene cerrar en reunión, porque determinan el alcance real de la V1.

### 5.1 · ¿Los embeddings entran en la V1? (G7, G13)

La búsqueda léxica es sólida y real: `tsvector`, `unaccent`, `pg_trgm`, configuración `spanish_unaccent`, PDFs con OCR.

*Actualizado el 2026-09-14.* Lo semántico ha dejado de estar a cero: el pipeline de vídeos escribe embeddings de 1536 dimensiones en `videos` y `video_fragmentos` (33 de 43 vídeos; el resto se quedó sin vector al agotarse la cuota gratuita del día). **Nada los lee todavía**: `buscar_videos()` sigue resolviendo por índice de texto completo, y ninguna consulta usa el operador de distancia de pgvector. Los manuales y sus páginas siguen sin un solo vector.

Así que la decisión no cambia, pero el coste sí: escribirlos ya está resuelto y probado sobre datos reales; lo que falta es decidir si la búsqueda pasa a usarlos, y con qué SDK de forma estable —el pipeline tira hoy de la cuota gratuita de Gemini, que da 20 peticiones diarias por modelo y no sostiene un uso en producción.

### 5.2 · ¿Se migra el almacenamiento a S3? (G9)

Hoy es disco local con bind mount. No hay `boto3` ni ningún SDK. Los 222 MB de PDFs viven solo en este portátil, `manuales/` está en `.gitignore` y no hay ninguna copia de seguridad — ni de los ficheros ni de la base de datos.

Independientemente de la decisión sobre S3, **la ausencia de backups es un riesgo activo hoy**: un `docker compose down -v` destruye contenido no recuperable.

### 5.3 · ¿Cloud IoT sigue siendo V1.1? (G14)

`rssi` y `firmware` son campos de texto que rellena una persona, no telemetría. El propio documento del jefe lo sitúa en V1.1. Conviene confirmarlo para que no se cuele en el alcance.

### 5.4 · Aclarar el rol «invitado» (G16)

Los roles reales de servidor son tres: `admin`, `tecnico` y `comercial`, con JWT y bcrypt de verdad (`app/auth.py:99-115`). **«invitado» no es un rol de backend**: es un valor en `localStorage` sin token (`app/static/app.js:355-380`). Conviene aclararlo antes de que el diseño de permisos granulares lo dé por existente.

---

## Anexo A — Documentación contra realidad

Cuatro afirmaciones del repositorio que no se sostenían al abrir el código. Se dejan registradas para que no vuelvan a darse por buenas, con lo que ha cambiado después.

| Afirmación | Realidad al auditar (2026-09-11) | Hoy (2026-09-14) |
|---|---|---|
| 37 tests activos | **69** (`pytest --collect-only`), pero solo el 37 % de los handlers ejecuta su cuerpo | **151**, todos en verde |
| Publicación en S3 cubierta | Disco local y bind mount. Sin `boto3` ni ningún SDK de objetos | Sin cambios: sigue siendo disco local, y sin copia de seguridad (§5.2) |
| Embeddings / pgvector integrados | Solo columnas. **0 filas** con embedding, 0 llamadas | Se escriben en 33 de 43 vídeos y en sus fragmentos, pero **nadie los lee**: la búsqueda sigue siendo léxica (§5.1) |
| 30 vídeos con transcripción y timestamp | 30 vídeos, pero `video_fragmentos` está **vacía**: todo resultado cae a 00:00 | **43 vídeos y 1132 fragmentos** con su segundo. Ninguno viene de una transcripción —el canal es mudo—, sino del pipeline de visión |

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
- **No hay CI.** No existe `.github/workflows` ni ningún pipeline que ejecute los 185 tests: hoy solo se ejecutan si alguien se acuerda. Con la suite ya cubriendo migraciones y PostgreSQL real, montarlo es barato y lo que evita es caro.

---

## Cómo mantener este documento

Cada paso completado se marca aquí con el hash del commit que lo cierra. Si una fase cambia de orden, se anota por qué. Este fichero y el panel visual son la única fuente de estado del proyecto: `README.md`, `DOCUMENTACION_SISTEMA.md` y `dossier_tecnico_y_operativo.md` describen la visión, no lo implementado.
