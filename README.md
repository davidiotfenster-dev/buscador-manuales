# Buscador de Manuales

Aplicación web sencilla para subir los manuales (PDF) de tu empresa y
buscar en ellos por palabras clave, sin tener que abrir cada archivo
uno por uno.

## ¿Cómo funciona?

1. Subes los PDF desde la pestaña **"Subir manuales"** (arrastrando o
   seleccionando varios a la vez, con dispositivo/categoría opcionales).
2. La app extrae el texto de cada PDF y lo indexa en una base de datos
   SQLite con búsqueda de texto completo (FTS5), página por página.
   Si una página es un escaneo sin texto, se intenta leer con OCR
   (ver más abajo).
3. Desde la pestaña **"Buscar"** escribes lo que necesitas (ej. "resetear
   cámara") y te aparecen los manuales relevantes con una miniatura de
   la página, un fragmento resaltado, y un enlace que abre el PDF
   **directamente en la página** donde está la coincidencia.
4. Puedes filtrar por dispositivo/categoría y elegir el orden de los
   resultados (relevancia, más recientes, o más páginas coincidentes).
   Mientras escribes, aparecen sugerencias basadas en lo ya indexado,
   y debajo del buscador se guardan tus búsquedas recientes (solo en
   tu navegador).

## Instalación

Necesitas Python 3.10 o superior.

```bash
cd buscador-manuales
python3 -m venv venv
source venv/bin/activate      # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### OCR para PDFs escaneados (opcional pero recomendado)

Si alguno de tus manuales es un escaneo (imagen) sin texto seleccionable,
la app puede leerlo igualmente con OCR, pero necesita el programa
**Tesseract** instalado en el sistema (además del paquete `pytesseract`,
que ya está en `requirements.txt`):

```bash
# Ubuntu / Debian
sudo apt install tesseract-ocr tesseract-ocr-spa

# macOS (con Homebrew)
brew install tesseract tesseract-lang

# Windows
# Descarga el instalador desde: https://github.com/UB-Mannheim/tesseract/wiki
```

`tesseract-ocr-spa` es el paquete de idioma español — sin él, el OCR
solo reconocerá bien texto en inglés. Si Tesseract no está instalado,
la aplicación funciona igual, simplemente avisa en la consola y esas
páginas escaneadas no aparecerán en las búsquedas.

## Ejecutar la aplicación

```bash
uvicorn app.main:app --reload
```

Abre tu navegador en: **http://127.0.0.1:8000**

## Estructura del proyecto

```
buscador-manuales/
├── app/
│   ├── main.py          # Rutas de la API, extracción de texto y OCR
│   ├── database.py      # Acceso a SQLite + búsqueda FTS5 + migraciones
│   ├── templates/
│   │   └── index.html   # Interfaz web
│   └── static/
│       ├── estilo.css
│       └── app.js
├── manuales/             # Aquí se guardan los PDF subidos
├── data/
│   └── manuales.db       # Base de datos (se crea sola al arrancar)
└── requirements.txt
```

## Actualizar el proyecto sin perder tus manuales

`database.py` incluye un pequeño sistema de migraciones (`_MIGRACIONES`):
cada vez que el esquema de la base de datos cambia en una versión nueva
del proyecto, se añade una función de migración en vez de borrar todo.
Así, si sobrescribes los archivos `.py` con una versión más reciente,
tu base de datos existente se actualiza sola al arrancar, sin perder
los manuales ya indexados (siempre que la migración no requiera
volver a extraer el texto de los PDF, en cuyo caso el propio aviso de
la migración lo indicará).

## Próximos pasos (cuando quieras evolucionar a RAG)

Este proyecto está pensado para escalar sin tirar nada:

1. **Añadir embeddings**: en `database.py` ya tienes el texto completo
   de cada manual guardado; se puede trocear por secciones y generar
   embeddings (por ejemplo con `sentence-transformers` en local, o con
   la API de Voyage/OpenAI/Anthropic).
2. **Búsqueda vectorial**: puedes seguir usando SQLite añadiendo la
   extensión `sqlite-vec`, o migrar esos embeddings a una base vectorial
   dedicada (Chroma, Qdrant...) si el volumen de manuales crece mucho.
3. **Capa de "preguntar"**: cuando tengas la búsqueda vectorial, añades
   un endpoint que recupere los fragmentos más relevantes y se los pase
   a un modelo (como Claude) para que responda la pregunta con esa
   información como contexto — eso ya sería el RAG completo.

## Notas

- Si un PDF es un escaneo (imagen) sin texto, la extracción no
  encontrará contenido para ese manual. Para esos casos, en el futuro
  se puede añadir OCR (por ejemplo con `pytesseract`).
- La base de datos y los PDF se guardan localmente en `data/` y
  `manuales/` — haz copia de seguridad de esas carpetas si es
  información importante.
