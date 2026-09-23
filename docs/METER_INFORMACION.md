# Meter información nueva: qué pasa solo y cómo comprobarlo

> Para quien vaya a subir manuales, vídeos o tickets. La idea es que **no haya
> que tocar código ni reiniciar nada** para que la información nueva cuente en
> la búsqueda y en la predicción. Aquí está qué ocurre en cada caso, cuánto
> tarda, y cómo medir si el sistema ha mejorado.

---

## Qué pasa al meter cada cosa

| Qué metes | Cómo | Qué pasa solo | Cuándo se nota |
|---|---|---|---|
| **Un manual PDF** | Pestaña «Indexar documentación», o dejarlo en `manuales/` y reindexar | Se extrae el texto (con OCR si es escaneado) y cada página entra en el índice de búsqueda | **Al instante** en la búsqueda. La corrección de erratas conoce sus palabras en **30 s** como mucho |
| **Un vídeo del canal** | Se sincroniza solo cada 24 h, o «Sincronizar» en la biblioteca | Se descarga la transcripción, se trocea por minutos y entra en el índice | Igual que un manual |
| **Un ticket nuevo o reclasificado** | Desde el CRM, como siempre | Pasa a formar parte de lo que usa el triaje para predecir el grupo y para enseñar casos parecidos | En **30 s** como mucho |
| **Un sinónimo** | Editar `data/thesaurus_manuales.ths` y guardar | Se recarga el tesauro | En **5 s** como mucho |
| **Una fila en `Problemas- soluciones.xlsx`** | Editar `data/sat/` y guardar | Se recarga el Excel | En **5 s** como mucho |

Lo que **sí** exige reiniciar el contenedor es cambiar **código**. El servidor
arranca sin recarga automática (`uvicorn` sin `--reload`), que es lo correcto en
producción: `docker restart buscador_web`.

### Por qué no hay que hacer nada

- **La búsqueda** usa columnas generadas de PostgreSQL: el índice se actualiza en
  la misma operación que da de alta la página. No hay nada que reconstruir.
- **La corrección de erratas y la predicción** guardan en memoria lo que
  necesitan y lo reconstruyen solos cuando cambia la «firma» de los datos
  (recuentos, id máximo, última modificación). Esa comprobación es barata y se
  hace como mucho cada 30 segundos.
- **El tesauro y los Excel** se recargan cuando cambia la fecha de modificación
  del fichero.

### Una condición: `data/` tiene que estar montado

Hasta el 23-09-2026, `docker-compose.yml` no montaba `data/` en el contenedor.
La aplicación leía la copia del tesauro y de los Excel que se metió en la
imagen al construirla, así que **editar esos ficheros en el disco no servía de
nada**. Ya está montado. Si alguien reconstruye el despliegue a mano, que no se
pierda esa línea.

---

## Comprobar si el sistema acierta más o menos

Cada vez que se mete un lote de información, conviene medir. Un comando:

```bash
docker exec -w /app buscador_web python -m app.calidad
```

O, como administrador, desde el navegador: `GET /api/sat/calidad`.

Da algo así (cifras del 23-09-2026):

```
Búsqueda
  103 consultas reales (síntomas de tickets)
  latencia        mediana 19.6 ms · p95 37.4 ms
  sin resultados  0.0 %
  vídeo de la categoría correcta en el top-3  70.2 %

Predicción del grupo (deja uno fuera)
  103 tickets clasificados
  acierta el grupo       62.1 %
  grupo entre los 3 1os  83.5 %
  línea base             27.2 %  (decir siempre VINCULACION)
  por confianza:
    0.0–0.4   17 casos   acierta 29.4 %
    0.4–0.6   49 casos   acierta 61.2 %
    0.6–0.8   28 casos   acierta 75.0 %
    0.8–1.0    9 casos   acierta 88.9 %
  por grupo:
    VINCULACION  21/28  75.0 %
    GESTUAL      18/20  90.0 %
    ...
    INSTALACION   0/4    0.0 %
    HARDWARE      0/2    0.0 %
```

### Cómo leerlo

- **«por grupo»** dice dónde falta información. Un grupo con 2 o 4 tickets no
  se puede aprender: INSTALACION y HARDWARE están a 0 % por eso, no porque el
  sistema esté mal. **Clasificar tickets de esos grupos es lo que más va a
  mejorar la predicción.**
- **«por confianza»** dice si la confianza que se enseña significa algo. Si un
  día los tramos altos dejan de acertar más que los bajos, algo se ha roto.
- **El acierto de búsqueda (70 %) es aproximado**: comprueba si sale un vídeo de
  la categoría equivalente al grupo del ticket. Un vídeo puede ser útil sin
  estar en esa categoría. Sirve para comparar antes y después de un cambio, no
  como nota absoluta.

---

## Lo que ya se sabe que falta

- **Nada habla de la batería.** «batería» no devuelve ningún manual ni vídeo: el
  WAlarm, que la usa, no tiene documentación subida. No es un fallo del
  buscador; es contenido que no existe.
- **Grupos con pocos ejemplos:** INSTALACION (4), HARDWARE (2), y OTRO, que tiene
  19 tickets pero casi todos «Incidencia sin descripción», que no enseña nada.
- **Los vídeos tienen seis categorías y los tickets nueve grupos**, y solo cuatro
  se corresponden. Si los vídeos se categorizaran con los mismos grupos que los
  tickets, la medida de acierto de la búsqueda sería exacta en vez de aproximada.
