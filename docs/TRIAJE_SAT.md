# El triaje SAT: qué hace, para qué sirve y cómo decide

> Documento de funcionamiento, escrito para poder discutirlo. La última sección
> recoge las decisiones que se han tomado con criterio pero sin datos: son las
> que conviene corregir si no encajan con cómo trabajáis de verdad.

---

## 1. El objetivo

**Que una llamada de soporte se resuelva en la llamada, y que lo que se aprende
en ella no se pierda.**

Hoy, cuando entra una incidencia, quien atiende tiene que hacer tres cosas a la
vez: averiguar qué le pasa al equipo, recordar qué documentación lo explica, y
dejar constancia de todo. Las tres compiten por la atención mientras hay alguien
esperando al teléfono.

El triaje separa esas tres cosas y se queda con las dos que puede hacer una
máquina:

| Lo que hace el técnico | Lo que hace el triaje |
|---|---|
| Preguntar y escuchar | Ordenar las preguntas y no dejarse ninguna |
| Decidir qué le pasa | Proponer una causa y **decir en qué se basa** |
| Explicar la solución | Traer el manual, el vídeo y los casos anteriores |
| — | Dejar el ticket escrito con el cliente ya puesto |

Lo que **no** pretende ser: un sistema que diagnostique solo. La decisión es del
técnico. El triaje aporta una hipótesis razonada y el material para
contrastarla.

---

## 2. El recorrido de una llamada

El cuestionario son seis pasos. El orden no es decorativo: va de lo que siempre
se sabe a lo que a veces no se sabe.

**1 · Quién llama.** Correo, nombre, teléfono y obra.

El correo va primero porque es *la puerta de entrada al caso*: es el único dato
que el cliente da igual por teléfono que por formulario, y es lo que permite
saber si esto ya lo contó hace dos semanas. Al salir del campo se consulta su
historial: si tiene casos abiertos, sale un aviso antes de empezar a preguntar,
y los datos de contacto que ya conocemos se rellenan solos.

**2 · Comercializadora y equipo.** Partner, dispositivo, modelo comercial y
cuántos equipos están afectados.

La marca importa porque un mismo equipo se vende con tres nombres: Connect-1 es
GreenTeQ Wave 1 en VBH, ICON 1 en Procomsa y Konect en Kömmerling. El triaje
traduce la equivalencia para que el técnico hable en el idioma del cliente.

**3 · Qué le pasa.** El área, el estado actual del equipo y los síntomas.

Aquí está la pregunta que más discrimina de todo el cuestionario: **¿responde al
pulsador físico? ¿y desde la App?** Esas dos respuestas separan un problema
eléctrico de uno de red mejor que ninguna otra cosa.

**4 · Su entorno.** Wi-Fi, app móvil y distancias.

**5 · Cuándo falla.** Momento, reproducibilidad y detonante.

**6 · El detalle.** La descripción con las palabras del cliente y lo que ya se ha
probado.

Ningún paso es obligatorio y el diagnóstico se recalcula con lo que haya. Lo que
ya se ha probado se usa para **tachar pasos**: repetir al instalador algo que ya
ha hecho es la forma más rápida de perder una llamada.

---

## 3. Cómo decide

Hay trece reglas, una por cada avería que sabemos reconocer. **Todas se evalúan
siempre**, cada una suma el peso de las señales que encuentra en las respuestas,
y gana la de más puntuación.

Lo que hace que esto funcione no es el orden de las reglas, es **el peso de cada
señal**:

| Peso | Qué significa | Ejemplo |
|---|---|---|
| **3,0** · Fuerte | Evidencia explícita e inequívoca | «Se oyen los relés pero el motor no se mueve» |
| **2,0** · Media | Una respuesta que el técnico ha cambiado a propósito | El cifrado declarado es WPA3 (el valor por defecto es WPA2) |
| **1,2** · Familia | Orientación por tipo de producto, nunca un diagnóstico | Es un WAlarm |
| **0,8** · Débil | Condición de entorno que **puede venir puesta por defecto** | La red publica ambas bandas con un solo SSID |

**El umbral para afirmar algo es 2,0.** Una señal débil sola (0,8) no llega, ni
dos sumadas (1,6). Hace falta al menos una respuesta explícita del técnico.

Esta es exactamente la corrección del fallo que había: la condición de Band
Steering coincidía con los valores que traían puestos dos desplegables, así que
se cumplía siempre y se comía todos los diagnósticos. Ahora esa condición sigue
existiendo y sigue puntuando, pero como señal **débil**: acompaña, no decide.

La regla general, que merece la pena tener escrita: **un valor por defecto no es
una respuesta.**

### La confianza significa algo

Sale de la evidencia encontrada, no de un número escrito a mano:

```
confianza = 50 + puntuación × 7 + margen_sobre_la_segunda × 5
```

con el techo propio de cada regla como máximo. Sin margen sobre la segunda
hipótesis no se llega arriba, aunque la primera puntúe bien: dos causas igual de
plausibles no son una certeza.

### Cuando no sabe, lo dice

Si ninguna regla llega a 2,0, el triaje **no elige la menos mala**. Devuelve
«Sin diagnóstico concluyente: faltan datos», enseña por dónde apuntaba sin
confirmar, y propone las preguntas que más separarían unas causas de otras.

Es deliberado, y es la parte que más os puede chocar al principio: el sistema
anterior siempre decía algo. Decir «no lo sé todavía, pregunta esto» es más útil
que una causa inventada con un 95 % al lado, porque una causa equivocada manda
al instalador a revisar el router cuando el problema es una pila.

### Siempre explica en qué se basa

Cada diagnóstico viene con sus motivos («Funciona el pulsador físico pero no la
App») y con las hipótesis que se descartaron y su puntuación. Sin eso, el fallo
anterior habría sido indetectable desde fuera: la respuesta llegaba con un 95 %
y sin una sola razón.

---

## 4. Las trece reglas

| Regla | Se activa cuando | Techo |
|---|---|---|
| Relés conmutan, motor no responde | Se oyen los relés y el motor no se mueve | 97 % |
| Inversión de giro | Al ordenar bajar, sube | 96 % |
| WPA3 / Wi-Fi 6-7 | El cifrado o la generación de red declarados son incompatibles | 95 % |
| Incidencia global | Afecta a todos los equipos, o a varios móviles | 94 % |
| Disparidad de móvil | Falla en un móvil y en otros no | 93 % |
| Alimentación / corte térmico | No responde ni al pulsador ni a la App | 92 % |
| Conectividad Wi-Fi | El pulsador va, la App no | 94 % |
| Band Steering | La App no descubre el equipo al vincular | 95 % |
| Calibración | No calibra, se para a medias, no memoriza | 90 % |
| Sensores Connect-2 | Problema de oscilo, temperatura, CO₂ o humedad | 89 % |
| C-Wall | Problema del pulsador de pared | 88 % |
| WAlarm | Batería, sirena, tamper o contacto magnético | 90 % |
| Cobertura RF | RSSI bajo u obstáculos metálicos | 91 % |

Hay un test que comprueba que **las trece siguen siendo alcanzables**. Antes,
cinco de ellas eran código inalcanzable y nadie lo sabía.

---

## 5. De dónde sale el material que acompaña

- **Manual con página exacta** — búsqueda de texto completo sobre los PDF
  indexados. Si no encuentra nada, **no sugiere nada**: antes devolvía un manual
  fijo con una página inventada.
- **Vídeo con el segundo exacto** — cruza el diagnóstico con las transcripciones
  del canal y salta al fragmento que lo explica.
- **Casos parecidos** — las 119 incidencias reales de `Incidencias.xlsx` y las 10
  parejas de `Problemas- soluciones.xlsx`. Estos dos ficheros existían desde
  siempre y **no los leía nadie**: la función que los cargaba no se llamaba
  desde ningún punto del proyecto.
- **Tickets resueltos parecidos** — de la propia base de datos.
- **Plantilla de WhatsApp** — el diagnóstico y los pasos, listos para enviar.

---

## 6. Lo que he decidido yo y quizá haya que corregir

Esta es la sección importante. Todo lo de abajo está razonado, pero **ninguna de
estas decisiones está respaldada por datos vuestros**.

### 6.1 · El umbral 2,0 y los cuatro pesos

Puestos a ojo. El criterio fue: una condición que puede venir por defecto no
puede decidir sola, y la familia de producto tampoco.

**La consecuencia práctica:** con el formulario a medio rellenar, muchos casos
van a salir como «faltan datos». Si os parece que corta demasiado, se baja el
umbral a 1,5 y con una sola señal media basta.

Esto se puede resolver con datos en vez de opinando: cada envío queda guardado
con su diagnóstico en `GET /api/sat/cuestionarios`. Con treinta o cuarenta
llamadas reales se puede ver qué porcentaje queda sin concluir y ajustar.

### 6.2 · Qué señal es «fuerte» y cuál es «media»

Ejemplo discutible: que el cifrado sea **WPA3** lo he puesto como señal *media*,
no fuerte. Mi razonamiento es que el técnico puede haberlo marcado por
suposición y no por haberlo mirado en el router. Si en la práctica ese dato solo
se rellena cuando se ha comprobado de verdad, debería ser **fuerte**.

Lo mismo al revés: la condición de **Band Steering** la he dejado en *débil*
porque es la que causó el fallo. Si en vuestra experiencia el emparejamiento por
banda dual es de verdad la causa más frecuente, quizá merezca *media* cuando el
técnico confirma expresamente que ha mirado el router.

### 6.3 · Los textos de las trece reglas

**No he inventado ninguno.** Títulos, causas y pasos son los que ya estaban en el
código. Si alguno está mal explicado o los pasos están anticuados, se cambian sin
tocar el motor: están en una tabla, cada regla en su bloque.

### 6.4 · C-Pulsar

Lo he añadido al desplegable de dispositivos porque es una familia real —tiene
manual propio y cinco vídeos indexados— y faltaba. Pero **no he escrito una
regla de diagnóstico para C-Pulsar**, porque eso sería inventarme conocimiento
técnico que no tengo. Hoy un C-Pulsar se registra bien y encuentra su
documentación, pero no tiene averías propias reconocidas.

Si me dictáis las dos o tres averías típicas de C-Pulsar, se añaden como una
regla más.

### 6.5 · «Konect Elite» no está en el desplegable, a propósito

Es el dispositivo más frecuente del histórico: **47 de las 119 incidencias**.
No lo he añadido porque entiendo que es el nombre comercial de Kömmerling para
un Connect-1 o Connect-2, no una familia aparte, y ya tiene su sitio en el campo
«Modelo comercial».

**Si me he equivocado en esto, corrígeme**, porque afecta a casi la mitad del
histórico y a cómo se cruzan los casos parecidos.

### 6.6 · Los datos de la persona no son columnas

Van dentro del JSON de respuestas del cuestionario. El ticket sí los guarda en
columnas propias, así que el historial por correo funciona. Pero **no se pueden
filtrar cuestionarios por cliente** sin abrir el JSON. Si hace falta esa
consulta, es una migración pequeña.

### 6.7 · Las diez «áreas» y los nueve grupos siguen sin cuadrar

Es la cuestión 4q.1 del plan de mejora y no la he tocado: el cuestionario
pregunta por diez áreas y el sistema clasifica en nueve grupos. Hoy se traducen
las cinco que significan lo mismo y el resto va sin grupo a propósito.

Merece la pena resolverlo, y es una decisión de producto, no técnica.

---

## 7. Qué NO hace, para que no haya sorpresas

- **No aprende solo.** Las reglas son fijas. Guarda todo lo necesario para
  ajustarlas con datos, pero el ajuste es manual y deliberado.
- **No sustituye al técnico.** Propone una hipótesis con sus razones.
- **No manda nada a los equipos.** Es diagnóstico y documentación.
- **No abre el ticket por su cuenta.** Deja el borrador relleno; el alta la hace
  una persona.
