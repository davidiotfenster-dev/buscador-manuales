# G2 · Grupos de incidencia — propuesta basada en datos reales

> **Fecha:** 2026-09-11 · Preparación del paso 2.1 del [plan de mejora](PLAN_MEJORA_V1.md)
> **Fuente:** `data/sat/Incidencias.xlsx` — **119 incidencias reales** de soporte.

El documento de V1 plantea un workshop para *inventar* los grupos de incidencia, con una lista de ejemplo de 12 (Conectividad, Control, Instalación, Configuración, App, Cuenta, Sensores, Firmware, Integraciones, Seguridad, Cloud, Hardware).

**No hace falta inventarlos: ya existen.** SAT lleva tiempo etiquetando cada incidencia en el campo `problema` del Excel, con una taxonomía de 11 etiquetas. El workshop no tiene que crear la lista desde cero, sino validar y consolidar la que ya se usa.

---

## 1. Por qué no se usan los tickets de la aplicación

La tabla `tickets_sat` tiene 47 registros, pero **no sirven como muestra**: 39 de los 47 son el mismo ticket de prueba repetido (*«La persiana sube al pulsar la orden de bajar en la App»*), generado por el script de humo `tools/manual_checks/test_flujo_sat_email.py` al ejecutarse dentro de `pytest`. Solo hay 6 síntomas distintos y 5 instaladores.

El histórico real está en el Excel que ya lee `app/sat_autoresolver.py`, y es el que se analiza aquí.

---

## 2. La taxonomía que ya se usa

Frecuencia de cada etiqueta sobre las 119 incidencias:

| Etiqueta actual | Incidencias | % |
|---|---:|---:|
| Vinculación | 41 | 34 % |
| Gestual | 31 | 26 % |
| Aplicación | 28 | 24 % |
| Wifi | 22 | 18 % |
| Pulsador | 15 | 13 % |
| Conexión | 14 | 12 % |
| Otro | 13 | 11 % |
| Integraciones | 11 | 9 % |
| Instalación | 7 | 6 % |
| Rotura | 6 | 5 % |
| Sensor de Apertura | 1 | 1 % |
| *(sin etiquetar)* | 17 | 14 % |

Los porcentajes suman más de 100 % porque una incidencia puede llevar varias etiquetas.

---

## 3. Tres hallazgos que condicionan el diseño de la tabla

### 3.1 · La clasificación es múltiple, no única

**46 % de las incidencias (55 de 119) llevan dos o más etiquetas.** Una llega a tener seis.

| Etiquetas por incidencia | Incidencias |
|---:|---:|
| 1 | 47 |
| 2 | 31 |
| 3 | 19 |
| 4 | 3 |
| 5 | 1 |
| 6 | 1 |

Esto choca de frente con el flujo propuesto para la V1, que asume **un** grupo por ticket (`NUEVO TICKET → SELECCIÓN DE GRUPO DE INCIDENCIA → PREGUNTAS DEL GRUPO`). Hay que decidirlo antes de crear la tabla, porque cambia el esquema:

- **Un grupo principal** (`grupo_id` en `tickets_sat`): más simple, encaja con el flujo del documento, pero pierde información que SAT ya registra hoy.
- **Un grupo principal + secundarios** (tabla puente `ticket_grupos`): refleja la realidad, y permite que el cuestionario encadene las preguntas de varios grupos.

Recomendación: **grupo principal obligatorio y secundarios opcionales**. El flujo por pasos usa el principal para decidir qué preguntas mostrar; los secundarios se pueden marcar al cerrar y sirven para las métricas.

### 3.2 · Una cuarta parte de las incidencias no encaja en ningún grupo

17 sin etiquetar más 13 marcadas como «Otro» son **30 de 119, el 25 %**. No es ruido: es la prueba de que G12 (incidencias nuevas OTHER/NEW) no es un extra, sino parte del flujo normal. Un cuarto de los casos necesita esa salida.

### 3.3 · «Sensor de Apertura» tiene exactamente una incidencia

Es literalmente el ejemplo que puso el jefe: *«saber si el DEVICE es CONNECT-1 o CONNECT-2 puede evitar poner el GRUPO SENSOR DE APERTURA como GRUPO inicial»*. Los datos le dan la razón — 1 caso de 119. No debe ser un grupo de primer nivel: es una pregunta dentro de otro grupo, condicionada al dispositivo.

---

## 4. Lista candidata de grupos

Consolidación de las 11 etiquetas actuales en **9 grupos**, dentro del rango de 8-12 que pedía el documento:

| Código | Nombre | De qué etiquetas sale | Incidencias |
|---|---|---|---:|
| `VINCULACION` | Vinculación y emparejamiento | Vinculación | 41 |
| `CONECTIVIDAD` | Conectividad y red | Wifi + Conexión | 36 |
| `GESTUAL` | Control gestual | Gestual | 31 |
| `APP` | Aplicación móvil | Aplicación | 28 |
| `PULSADOR` | Pulsador y control físico | Pulsador | 15 |
| `INTEGRACIONES` | Integraciones (Alexa, Google, KNX…) | Integraciones | 11 |
| `INSTALACION` | Instalación y montaje | Instalación | 7 |
| `HARDWARE` | Rotura y avería física | Rotura | 6 |
| `OTRO` | Sin clasificar / incidencia nueva | Otro + sin etiquetar | 30 |

**Decisiones que lleva implícitas esta lista, y que conviene confirmar en la reunión:**

1. **Wifi + Conexión se fusionan** en `CONECTIVIDAD`. Hoy se usan por separado, pero ambas son problemas de enlace. Si SAT las distingue por algo concreto (router frente a nube), conviene mantenerlas separadas y serían 10 grupos.
2. **«Sensor de Apertura» desaparece** como grupo y pasa a ser una pregunta condicionada al dispositivo.
3. **`OTRO` no es un cajón de sastre**, es la entrada de G12: cada incidencia que cae ahí es candidata a grupo nuevo.
4. La lista **no incluye** varios grupos del ejemplo del documento — Cuenta, Firmware, Seguridad, Cloud, Configuración — porque **ninguna incidencia real los ha necesitado todavía**. Mejor crearlos cuando aparezcan, desde `OTRO`, que arrancar con grupos vacíos.

---

## 5. Datos que también salen del análisis

Útiles para G3 (preguntas vitales) y G10 (cierre técnico).

### Dispositivos

| Dispositivo | Incidencias |
|---|---:|
| Konect Elite | 47 |
| Connect-1 | 36 |
| *(vacío)* | 22 |
| Connect-2 | 8 |
| BlickDomi Antiguo | 4 |
| C-Wall | 1 |

**Konect Elite es el dispositivo más frecuente**, por encima de Connect-1. Está contemplado en el cuestionario actual (`vista_asistencia.html`), pero conviene comprobar que la documentación indexada lo cubre igual de bien que a los Connect.

### Distribuidores

Solven 32 · Kommerling 31 · IoT Fenster 23 · *(vacío)* 17 · VBH 11 · Procomsa 5.

Confirma que **Partner/distribuidor es una buena pregunta vital**: discrimina de verdad y está casi siempre informado.

### Campos que se piden pero casi nadie rellena

- **Sistema operativo del móvil:** vacío en 78 de 119 (66 %).
- **Compañía de internet:** vacío en 68 de 119 (57 %).

Ambos son justo los datos que más ayudan en `CONECTIVIDAD` y `APP`. Si en G3 se clasifican las preguntas como `required` / `recommended` / `automatic`, estos dos son los primeros candidatos a **obligatorios dentro de su grupo** — no globalmente, o se alarga el formulario sin motivo.

> Detalle de calidad de dato: la compañía aparece como `Digi` y como `DIGI`, y hay un valor `Con un Movil`. Al pasar a entidad configurable conviene que sea una lista cerrada.

### Acción correctiva — la taxonomía que alimenta G10

| Acción | Veces |
|---|---:|
| Llamada | 62 |
| Mensaje Informativo | 49 |
| Vídeos | 29 |
| Tiempo | 13 |
| Incomparecencia | 13 |
| Firmware | 12 |
| Reset | 9 |
| Incidencia ajena a nosotros | 7 |
| Asistencia presencial | 3 |
| Servidor | 3 |

Esto es material directo para el cierre técnico estructurado (G10):

- **`Vídeos` (29 casos) ya es `document_used`.** La documentación se está usando para resolver en uno de cada cuatro casos, y hoy eso no se registra en ningún sitio de la aplicación.
- **`Asistencia presencial` (3) e `Incidencia ajena a nosotros` (7) son `escalated`.**
- **`Llamada` y `Mensaje Informativo` suman 111** de las acciones: la mayoría se resuelve hablando. La pregunta que G10 debería contestar es *cuántas de esas llamadas se habrían evitado con un documento*, que es exactamente `documentation_sufficient`.

---

## 6. Qué decidir en la reunión

1. ¿Un grupo por ticket, o principal más secundarios? **Afecta al esquema**, conviene cerrarlo antes de crear la tabla.
2. ¿`CONECTIVIDAD` unificado, o `WIFI` y `CONEXION` separados? 9 grupos frente a 10.
3. ¿Se arranca solo con los 9 grupos que los datos respaldan, o se crean también los del ejemplo del documento aunque estén vacíos?
4. ¿`SENSOR_APERTURA` se retira como grupo y pasa a pregunta condicionada al dispositivo?

Con esas cuatro respuestas, el paso 2.1 (crear la tabla y sembrarla) es trabajo de un día.
