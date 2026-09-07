# 📚 Base de Conocimiento Técnica — IoT Fenster

Plataforma integral de gestión de conocimiento técnico, búsqueda semántica y documentación para dispositivos IoT Fenster / MySmartWindow. Permite indexar manuales PDF, sincronizar automáticamente videos y tutoriales de YouTube, visualizar documentos con deep-linking exacto a página y generar Packs de Obra offline en ZIP con un solo clic.

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

## ✨ Características Principales

- **Búsqueda Avanzada en Español**: Motor PostgreSQL con `tsvector` y diccionarios de derivación morfológica (stemming) en español, con soporte para búsqueda vectorial semántica (`pgvector`).
- **Deep-Linking a Páginas PDF**: Cada resultado apunta a la página exacta donde se localizó el término.
- **Sincronización Automática con YouTube**: Cron de fondo que rastrea las novedades del canal `@MySmartWindow` e indexa títulos, descripciones y subtítulos.
- **OCR Integrado para Escaneos**: Extracción de texto con Tesseract OCR (`tesseract-ocr-spa`) para páginas sin texto seleccionable.
- **Packs de Obra Offline**: Generación al vuelo de paquetes ZIP con todos los recursos de un dispositivo específico para instalaciones sin internet.
- **Control de Acceso Basado en Roles (RBAC)**:
  - `admin`: Acceso total, subida de archivos, reindexación y administración de usuarios.
  - `tecnico`: Acceso a manuales técnicos y comerciales, buscador y visor.
  - `comercial`: Acceso restringido exclusivamente a documentación pública.
- **Seguridad Reforzada**: Tokens JWT con rotación, protección contra Path Traversal, mitigación de ataques XSS con sanitización estricta, rate-limiting contra fuerza bruta en login y ejecución en contenedores sin privilegios de root.

---

## 🚀 Despliegue Rápido con Docker

La forma recomendada de desplegar la aplicación es con Docker Compose:

```bash
# 1. Clonar el repositorio
git clone https://github.com/davidiotfenster-dev/buscador-manuales.git
cd buscador-manuales

# 2. Configurar variables de entorno
cp .env.example .env
# Edita .env con tus contraseñas y SECRET_KEY

# 3. Iniciar los contenedores
docker-compose up -d --build
```

La aplicación estará disponible en `http://localhost:8000`.

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
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/buscador_manuales
SECRET_KEY=tu_clave_secreta_super_segura

# 4. Iniciar la aplicación
uvicorn app.main:app --reload --port 8000
```

---

## 📂 Estructura del Proyecto

```
buscador-manuales/
├── app/
│   ├── main.py              # Endpoints FastAPI, seguridad, sincronizador YouTube y OCR
│   ├── database.py          # Modelos SQLAlchemy, pgvector, usuarios y RBAC
│   ├── templates/
│   │   └── index.html       # Interfaz SPA responsiva con Tailwind CSS y Sora/Inter
│   └── static/
│       ├── app.js           # Lógica frontend, autenticación, gestión de vistas
│       └── logo.png         # Logotipo corporativo IoT Fenster
├── docs/
│   └── screenshots/         # Capturas de pantalla de la aplicación
├── manuales/                # Almacenamiento local de archivos PDF
├── Dockerfile               # Imagen Docker de producción (non-root, hardened)
├── docker-compose.yml       # Orquestación con PostgreSQL + pgvector
├── requirements.txt         # Dependencias fijadas para compilación determinista
└── .env.example             # Plantilla documentada de variables de entorno
```
