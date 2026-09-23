# G1 — Descubrimiento con el equipo de soporte

> **Qué es este documento.** G1 es el primer grupo del plan de V1 y tiene tres tareas: 1.1 reunión
> de descubrimiento, 1.2 inventario de incidencias reales y 1.3 priorización. Este documento cierra
> **1.2 y 1.3** con los datos reales, y deja **1.1** preparada para que sea una reunión de validación
> de una hora en vez de un descubrimiento desde cero.
>
> **Fuente:** las 119 incidencias de `data/sat/Incidencias.xlsx`, del 23/07/2025 al 03/12/2025.
> Ninguna cifra viene de la documentación del repositorio.

---

## Estado de las tres tareas

| Tarea | Objetivo del plan | Estado |
|---|---|---|
| **1.2 Inventario de incidencias reales** | 30–50 incidencias | ✅ **Hecho y superado: 119** |
| **1.3 Priorización** | Seleccionar las 10–15 representativas | ✅ **Hecho aquí abajo** |
| **1.1 Reunión de descubrimiento** | Entender cómo trabaja SAT | 🟡 **Preparada, pendiente de celebrarla** |

1.1 es una reunión con personas: no se puede resolver desde el código. Lo que sí se puede es llegar
a ella con las respuestas que los datos ya dan, para que el equipo solo tenga que confirmarlas o
corregirlas. Eso es lo que hay en la última sección.

---

## 1.2 — El inventario

**119 incidencias en 133 días: 5,4 por semana.** No es un volumen que justifique automatizar por
ahorro de tiempo bruto, pero sí lo bastante regular como para que los mismos problemas se repitan,
que es lo que hace útil un buscador.

| | |
|---|---|
| **Estado** | 90 resueltas · 7 sin tratar · 5 en proceso · 17 sin estado anotado |
| **Dispositivos por incidencia** | mediana 5, máximo 15 (dato en 81 de 119) |
| **Reparto por dispositivo** | Konect Elite 48 · Connect‑1 36 · Connect‑2 9 · BlickDomi Antiguo 4 · C‑Wall 1 |
| **Reparto por distribuidor** | Solven 32 · Kommerling 31 · IoT Fenster 23 · VBH 11 · Procomsa 5 · 17 sin anotar |

**Tiempo de resolución.** Mediana de **1 día**, pero la media es 7,5 porque hay cola larga: el caso
más lento tardó 75 días. **El 44 % se cierra el mismo día.** Hay 15 incidencias con fecha de entrada
y sin fecha de solución.

---

## 1.3 — Priorización

El plan pide puntuar por cuatro dimensiones. Tres se miden directamente; la cuarta hay que
aproximarla, y conviene saber con qué:

| Dimensión | Cómo se mide aquí | ¿Es medida o estimada? |
|---|---|---|
| **Frecuencia** | Recuento de la etiqueta en el campo `Problema` | Medida |
| **Tiempo de resolución** | `Fecha de Solución` − `Fecha de Entrada` | Medida (86 de 119 tienen ambas) |
| **Dificultad** | % de casos que necesitaron asistencia presencial, firmware, servidor o reposición | Aproximada |
| **Impacto** | No hay campo de impacto. Se usa el **% que no llegó a resolverse** | Aproximada, y es la más débil |

### La tabla

| Etiqueta | n | % del total | Mediana días | **Necesitó llamada** | Se resolvió con documentación | Casos caros | Sin resolver |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Vinculación** | 41 | 34 % | 0 | **83 %** | 66 % | 15 % | 10 % |
| **Gestual** | 31 | 26 % | 0 | **77 %** | 55 % | 23 % | 13 % |
| **Aplicación** | 28 | 24 % | 1 | 39 % | 75 % | 11 % | 7 % |
| **Wifi** | 22 | 18 % | 0 | **68 %** | 59 % | 18 % | 18 % |
| **Pulsador** | 15 | 13 % | 0,5 | 53 % | 27 % | 20 % | 13 % |
| **Conexión** | 14 | 12 % | 1 | 57 % | 43 % | 21 % | **29 %** |
| **Otro** | 13 | 11 % | **7** | 54 % | 46 % | **31 %** | 15 % |
| **Integraciones** | 11 | 9 % | 2,5 | 27 % | **82 %** | 18 % | 18 % |
| **Instalación** | 7 | 6 % | 2 | 71 % | 57 % | **43 %** | 0 % |
| **Rotura** | 6 | 5 % | 3 | 67 % | 67 % | 33 % | 0 % |
| **Sensor de Apertura** | 1 | 1 % | — | 0 % | 0 % | 0 % | 100 % |
| *(sin etiquetar)* | 17 | 14 % | — | — | — | — | — |

### Lo que dice esta tabla

**1. La columna que manda es la de llamadas.** El 52 % de todas las incidencias acabó en una llamada
de teléfono. Ahí es donde se va el tiempo del operador, y no se reparte por igual:

| | Llamadas | de un total de |
|---|---:|---:|
| Vinculación | **34** | 41 |
| Gestual | **24** | 31 |
| Wifi | **15** | 22 |
| Aplicación | 11 | 28 |
| Pulsador | 8 | 15 |
| Conexión | 8 | 14 |

Hubo **62 incidencias con llamada**. Una incidencia con varias etiquetas aparece en cada fila, así
que la columna suma más de 62; lo que importa es el reparto: **Vinculación, Gestual y Wifi están
detrás de la mayoría de las llamadas**. Son el objetivo.

**2. Y a la vez son documentables.** Vinculación se resuelve con documentación en el 66 % de los
casos. Es decir: **se manda un vídeo o un mensaje explicativo, y aun así hace falta llamar en el
83 %**. Eso apunta a que el material existe pero el cliente no lo encuentra o no lo entiende — que
es exactamente el problema que ataca este proyecto.

**3. Aplicación es el contraste que confirma la lectura.** Mismo orden de frecuencia que Wifi, pero
solo necesita llamada el 39 % de las veces y se resuelve con documentación el 75 %. Lo que ya está
bien explicado, se resuelve solo.

**4. «Otro» es la señal de alarma.** Solo 13 casos, pero **mediana de 7 días** (el resto está en
0 o 1) y el 31 % requirió firmware, servidor o presencia. Lo que no encaja en la taxonomía es lo que
más cuesta cerrar. Esto es el argumento a favor de G12 (incidencias nuevas): no es un extra, es la
válvula de escape de los casos caros.

**5. Instalación es la más cara por caso:** 43 % requirió asistencia presencial, firmware o
reposición, con solo 7 casos.

**6. Conexión es la que más se queda sin cerrar:** 29 % sin resolver.

### Las incidencias representativas

El plan pide 10–15. Estas salen de leer los 102 comentarios y agrupar lo que se repite. La columna
**Casos** es cuántos comentarios mencionan ese problema — es una búsqueda de texto, no una
clasificación que haya hecho SAT, así que la lista es una propuesta a validar en la reunión, no un
dato cerrado.

| # | Incidencia | Casos | Grupo | Por qué está en la lista |
|---|---|---:|---|---|
| 1 | **No sabe vincular** — desconoce el procedimiento, sin avería | 12 | Vinculación | La más repetida, y la más barata de documentar: 75 % se resuelve con documentación, mediana 0 días |
| 2 | **Integración con Alexa o Google tras vincular** | 12 | Integraciones | 83 % se resuelve con documentación y solo el 27 % necesita llamada: es el patrón de «documentación que funciona» |
| 3 | **Reflejos, haces de luz o sol sobre el sensor** | 6 | Gestual | Mediana 3 días y 33 % de casos caros. Es físico, no de software: la documentación aquí es de colocación |
| 4 | **Rango de detección o calibración mal ajustados** | 6 | Gestual | Mediana 0 días: se arregla en la llamada. Candidato claro a vídeo |
| 5 | **Motor o sensor roto: requiere reposición** | 4 | Rotura | Es el camino de RMA. No se documenta: se detecta pronto para no perder tiempo |
| 6 | **Cambio de router, operador o wifi sin desvincular antes** | 3 | Vinculación + Wifi | **100 % se resolvió con documentación y 0 % fue caro.** El caso perfecto para un documento SAT |
| 7 | **Red a 5 GHz en lugar de 2.4 GHz** | 3 | Wifi | Causa raíz recurrente y con solución conocida; mediana 3,5 días porque tarda en detectarse |
| 8 | **Aplicación equivocada: Blickdomi en vez de Konect** | 3 | Aplicación | 100 % documentación, 0 días. Una pregunta al inicio del ticket lo descarta |
| 9 | **Dispositivo fantasma: eliminado pero sigue apareciendo** | 3 | Vinculación | 67 % acabó en caso caro. Difícil de resolver, conviene reconocerlo pronto |
| 10 | **Cobertura irregular: se conecta y desconecta según la zona** | 3 | Conexión | Confundible con avería; en realidad es alcance de la red |
| 11 | **Firmware descuadrado tras actualizar** | 2 | Otro | **Mediana 37,5 días.** Pocos casos, pero son los que se eternizan |
| 12 | **Dispositivos demasiado juntos que se detectan entre sí** | 1 | Gestual | Poco frecuente pero con solución concreta y repetible (ajustar el haz) |
| 13 | **El gestual no funciona en oscilo** | 1 | Gestual | No es una avería: es una limitación del producto. Debe responderla la documentación, no una llamada |
| 14 | **Perfil o cajón no compatible con el gestual** | 1 | Instalación | Mismo caso: limitación, no avería |
| 15 | **Producto de otro fabricante** (mando de Kommerling, no Konect) | 1 | — | Es el 6 % de incidencias ajenas. Detectarlo al principio ahorra el ticket entero |

> Las reglas de texto tocan 49 de los 119 comentarios. El resto son casos únicos o descripciones
> demasiado genéricas para agrupar. Eso **no** es un fallo del inventario: significa que la mitad de
> las incidencias son variaciones de las 15 de arriba, y la otra mitad son de cola larga.

### Recomendación de orden

Si hay que elegir por dónde empezar a documentar, el orden por retorno es:

1. **Vinculación** — 34 llamadas. Casos 1, 6, 8 y 9 de la tabla.
2. **Gestual** — 24 llamadas, y buena parte son de colocación física (casos 3, 4, 12), que es justo
   lo que un vídeo explica mejor que una llamada.
3. **Wifi** — 15 llamadas, y el caso 7 tiene causa raíz única y conocida.

No recomiendo empezar por Aplicación aunque sea la tercera en frecuencia: ya se resuelve sola el
75 % de las veces.

---

## 1.1 — Guión para la reunión de descubrimiento

El plan pide cinco cosas de esta reunión. **Cuatro ya tienen respuesta en los datos** y solo hay que
confirmarlas; la quinta es la única que hay que descubrir de verdad.

| Lo que pide el plan | Lo que ya dicen los datos | Qué hay que preguntar |
|---|---|---|
| Identificar grandes familias de problemas | Las 11 etiquetas de `Problema`, ya en uso | ¿Falta alguna? ¿Sobra «Sensor de Apertura», con 1 caso de 119? |
| Detectar consultas frecuentes | Vinculación 41, Gestual 31, Aplicación 28 | ¿Coincide con vuestra sensación? |
| Entender qué información pide primero el operador | — | **Esto no está en los datos.** Es lo que hay que descubrir |
| Detectar qué documentación se usa realmente | Vídeos en 29 casos, mensaje informativo en 49 | ¿Qué vídeos concretos? ¿De dónde los sacáis? |
| Identificar dónde se pierde más tiempo | 62 llamadas; «Otro» tarda 7 días de mediana | ¿Se pierde en la llamada, o antes, buscando qué contestar? |

### Las preguntas que solo puede responder el equipo

1. **¿Qué es lo primero que preguntáis al descolgar?** Es el orden real de las preguntas vitales de
   G3, y no se puede deducir del Excel.
2. **¿Cuándo decidís llamar en vez de mandar un mensaje?** Con 62 llamadas y 49 mensajes, la
   frontera existe pero no está escrita.
3. **¿Dónde están los vídeos que mandáis?** Aparecen en 29 incidencias y hay referencias a un canal
   de YouTube; el sistema no los tiene indexados como documentación de soporte.
4. **Las 17 incidencias sin etiquetar:** ¿se quedaron sin clasificar por falta de tiempo, o porque
   ninguna etiqueta servía? La respuesta cambia por completo la prioridad de G12.

### Lo que conviene enseñar en la reunión

- La tabla de priorización de 1.3, para confirmar que el orden Vinculación → Gestual → Wifi les
  cuadra.
- Las 15 incidencias representativas, para que tachen las que no reconozcan y añadan las que falten.
- Las cuatro preguntas de taxonomía de [`G2_TAXONOMIA_GRUPOS.md`](G2_TAXONOMIA_GRUPOS.md), que son
  las que bloquean seguir construyendo.

---

## Qué queda de G1

Una sola cosa: **celebrar la reunión**. Con eso 1.1 se cierra y G1 pasa de 30 % a completo.

Lo que salga de ella alimenta directamente a **G2.1** (validar los 9 grupos), **G3.1** (el orden real
de las preguntas vitales) y **G9.1** (qué documentos SAT escribir primero — que es la lista de
arriba).
