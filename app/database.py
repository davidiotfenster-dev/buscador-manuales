import os
import re
import logging
import secrets
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy import create_engine, Column, Integer, Float, String, Text, Boolean, DateTime, ForeignKey, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import bcrypt
from .sinonimos import expandir_query

logger = logging.getLogger("buscador_manuales")

# Raíz del proyecto: donde viven alembic.ini y el directorio alembic/
BASE_DIR = Path(__file__).resolve().parent.parent

# Roles válidos del sistema — cualquier rol fuera de esta lista se rechaza
ROLES_VALIDOS = {"admin", "tecnico", "comercial"}

# URL por defecto si no se inyecta desde Docker
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:password@localhost:5432/buscador_manuales"
)

# Configuración robusta del pool de conexiones PostgreSQL
# - pool_pre_ping: Comprueba con 'SELECT 1' la validez del socket antes de usarlo (evita cuelgues por conexiones caídas o timeouts de red)
# - pool_recycle: Recicla conexiones cada 5 minutos para evitar sockets obsoletos
# - pool_size & max_overflow: Permite hasta 40 conexiones concurrentes bajo carga (evita QueuePool limit timeout)
# - pool_timeout: Tiempo máximo de espera rápido (15s) en lugar de bloquearse 30s
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=20,
    pool_timeout=15,
    pool_recycle=300,
    pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Generador de sesiones de base de datos para FastAPI Depends con cierre automático garantizado."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------
# Modelos de Base de Datos
# ---------------------------------------------------------------------

class User(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="comercial") # roles: admin, tecnico, comercial
    is_first_login = Column(Boolean, default=True)

class Manual(Base):
    __tablename__ = "manuales"
    id = Column(Integer, primary_key=True, index=True)
    nombre_original = Column(String, nullable=False)
    nombre_archivo = Column(String, unique=True, nullable=False)
    dispositivo = Column(String)
    categoria = Column(String)
    etiquetas = Column(Text, default="")
    num_paginas = Column(Integer, default=0)
    nivel_acceso = Column(String, default="publico") # publico o tecnico
    # SHA-256 del PDF. Sin esto, subir el mismo fichero con otro nombre crea otro
    # manual: asi llegaron a existir siete copias identicas de la guia de wifi,
    # que ademas devolvia siete veces el mismo resultado en cada busqueda.
    contenido_hash = Column(String(64), index=True, nullable=True)
    fecha_subida = Column(DateTime(timezone=True), server_default=func.now())

    paginas = relationship("Pagina", back_populates="manual", cascade="all, delete-orphan")

class Pagina(Base):
    __tablename__ = "paginas"
    id = Column(Integer, primary_key=True, index=True)
    manual_id = Column(Integer, ForeignKey("manuales.id", ondelete="CASCADE"))
    numero_pagina = Column(Integer, nullable=False)
    texto = Column(Text, nullable=False)
    obtenido_por_ocr = Column(Boolean, default=False)
    
    # Preparado para el futuro RAG con IA (ej: OpenAI genera vectores de tamaño 1536)
    embedding = Column(Vector(1536))
    
    manual = relationship("Manual", back_populates="paginas")

class Video(Base):
    __tablename__ = "videos"
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(String, unique=True, index=True, nullable=False) # e.g. j7V8uHqqbq0
    titulo = Column(String, nullable=False)
    canal = Column(String, default="MySmartWindow")
    url = Column(String, nullable=False)
    miniatura_url = Column(String)
    dispositivo = Column(String)
    categoria = Column(String)
    etiquetas = Column(Text, default="")
    nivel_acceso = Column(String, default="publico") # publico o tecnico
    transcripcion_texto = Column(Text, default="")
    fecha_subida = Column(DateTime(timezone=True), server_default=func.now())

    # Preparado para el futuro RAG con IA
    embedding = Column(Vector(1536))

    fragmentos = relationship("VideoFragmento", back_populates="video", cascade="all, delete-orphan")

class VideoFragmento(Base):
    __tablename__ = "video_fragmentos"
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    segundo_inicio = Column(Integer, nullable=False, default=0) # en segundos
    duracion = Column(Integer, default=0)
    texto = Column(Text, nullable=False)

    # Preparado para el futuro RAG con IA
    embedding = Column(Vector(1536))

    video = relationship("Video", back_populates="fragmentos")

class IncidentGroup(Base):
    """Grupo de incidencia: la taxonomía con la que SAT clasifica una avería.

    Sustituye a la lista fija que hasta ahora vivía en el HTML del cuestionario.
    Los grupos sembrados salen del análisis de las 119 incidencias reales de
    data/sat/Incidencias.xlsx (ver docs/G2_TAXONOMIA_GRUPOS.md).
    """
    __tablename__ = "incident_groups"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False, index=True)  # VINCULACION, CONECTIVIDAD...
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    # Madurez del grupo. Los 9 sembrados salen de 119 incidencias reales y nacen
    # 'estable'; los que cree SAT sobre la marcha nacen 'nuevo', para poder
    # distinguir en la reunion la taxonomia validada de la que esta a prueba.
    estado_revision = Column(String, default="estable", nullable=False)  # estable, nuevo, en_revision
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TicketGrupoSecundario(Base):
    """Grupos adicionales de un ticket.

    El 46% de las incidencias reales lleva más de una etiqueta, así que el grupo
    principal (tickets_sat.grupo_id) no basta para reflejar lo que SAT registra.
    El principal decide qué preguntas se muestran; los secundarios sirven para
    las métricas y para no perder información al cerrar.
    """
    __tablename__ = "ticket_grupos_secundarios"
    ticket_id = Column(Integer, ForeignKey("tickets_sat.id", ondelete="CASCADE"), primary_key=True)
    grupo_id = Column(Integer, ForeignKey("incident_groups.id", ondelete="CASCADE"), primary_key=True)


class TicketSAT(Base):
    __tablename__ = "tickets_sat"
    id = Column(Integer, primary_key=True, index=True)
    numero_ticket = Column(String, unique=True, index=True, nullable=False) # e.g. "SAT-2026-0001"
    instalador = Column(String, nullable=False, index=True)
    email = Column(String, default="") # Email destinatario para envío automático
    telefono = Column(String, default="")
    obra = Column(String, default="")
    distribuidor = Column(String, default="") # e.g. Solven, Procomsa, Kömmerling, VBH
    dispositivo = Column(String, default="") # Connect-1, C-Wall, C-Pulsar, etc.
    motor = Column(String, default="") # Somfy 4 hilos, Cherubini, etc.
    sintoma = Column(Text, nullable=False)
    diagnostico = Column(Text, default="")
    solucion = Column(Text, default="")
    grupo_id = Column(Integer, ForeignKey("incident_groups.id", ondelete="SET NULL"), nullable=True, index=True)
    estado = Column(String, default="en_espera", index=True) # en_espera, resuelto, rma_pendiente, descartado
    prioridad = Column(String, default="normal") # normal, urgente
    creado_por = Column(String, default="") # email del usuario técnico/admin
    notas = Column(Text, default="")
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_actualizacion = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # --- Cierre técnico estructurado (G10) ---
    # Captura qué resolvió la incidencia, para poder responder a la pregunta que hoy
    # no tiene respuesta: ¿nuestra documentación resuelve? En el histórico de 119
    # incidencias, "Vídeos" aparece 29 veces como acción correctiva y no queda registrado
    # en ninguna parte. Null significa "sin cerrar todavía", que no es lo mismo que "no".
    cierre_resuelto = Column(Boolean, nullable=True)              # ¿se resolvió el problema del cliente?
    cierre_descripcion = Column(Text, default="")                 # qué se hizo, en una frase
    cierre_doc_suficiente = Column(Boolean, nullable=True)        # ¿bastó con la documentación existente?
    cierre_manual_id = Column(Integer, ForeignKey("manuales.id", ondelete="SET NULL"), nullable=True, index=True)
    cierre_video_id = Column(Integer, ForeignKey("videos.id", ondelete="SET NULL"), nullable=True, index=True)
    cierre_doc_texto = Column(Text, default="")                   # fuente usada cuando no es un manual ni un vídeo
    cierre_alternativa = Column(Text, default="")                 # qué se hizo cuando la documentación no bastó
    cierre_escalado = Column(Boolean, nullable=True)              # ¿hubo que escalar a ingeniería?
    # Fecha propia del cierre: fecha_actualizacion cambia con cualquier edición posterior,
    # así que no sirve para medir el tiempo de resolución de G15.
    cierre_fecha = Column(DateTime(timezone=True), nullable=True)
    cierre_por = Column(String, default="")                       # email de quien cerró

    # Preparado para el futuro RAG con IA (silo empírico de casos resueltos)
    embedding = Column(Vector(1536))

    comentarios = relationship("TicketComentario", back_populates="ticket", cascade="all, delete-orphan", order_by="TicketComentario.fecha.asc()")
    grupo = relationship("IncidentGroup", foreign_keys=[grupo_id])
    cierre_manual = relationship("Manual", foreign_keys=[cierre_manual_id])
    cierre_video = relationship("Video", foreign_keys=[cierre_video_id])
    grupos_secundarios = relationship("IncidentGroup", secondary="ticket_grupos_secundarios", viewonly=True)

class CuestionarioAsistencia(Base):
    """Lo que el técnico contesta en el cuestionario de asistencia, tal cual llega.

    Hasta ahora el cuestionario se evaluaba y las respuestas se tiraban: el
    técnico rellenaba doce bloques, recibía un diagnóstico y **no quedaba
    rastro** de qué había contestado. Eso impide lo dos cosas que hacen falta
    para G3.2 —diseñar la tabla de preguntas con datos en vez de a ojo— y para
    medir si el triaje acierta.

    Se guarda el envío entero en `respuestas_json` en lugar de una columna por
    pregunta a propósito: las preguntas todavía van a cambiar, y una tabla con
    ochenta columnas quedaría obsoleta a la primera. Los cuatro campos sueltos
    de arriba son los que se consultan a menudo, para no tener que abrir el JSON
    solo para filtrar.
    """
    __tablename__ = "cuestionarios_asistencia"
    id = Column(Integer, primary_key=True, index=True)
    # Null cuando lo rellena alguien sin sesión: el endpoint de triaje es
    # accesible sin token y no se quiere perder ese envío por no tener autor.
    creado_por = Column(String, default="")
    # El ticket nace después del cuestionario, si es que nace. SET NULL para que
    # borrar un ticket no borre la evidencia de lo que se contestó.
    ticket_id = Column(Integer, ForeignKey("tickets_sat.id", ondelete="SET NULL"), nullable=True, index=True)
    dispositivo = Column(String, default="", index=True)
    area_incidencia = Column(String, default="", index=True)
    diagnostico_titulo = Column(String, default="")
    # Decimal, no entero: el triaje devuelve 89.3, y redondear a 89 seria
    # inventar precision en la direccion contraria.
    confianza = Column(Float, nullable=True)
    respuestas_json = Column(Text, default="")
    fecha = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    ticket = relationship("TicketSAT", backref="cuestionarios")


class TicketComentario(Base):
    """Historial de comentarios, cambios de estado y eventos en un ticket SAT."""
    __tablename__ = "ticket_comentarios"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets_sat.id", ondelete="CASCADE"), nullable=False, index=True)
    autor = Column(String, nullable=False, default="")  # email del autor
    texto = Column(Text, nullable=False, default="")
    tipo = Column(String, default="nota")  # nota, cambio_estado, email_enviado, creacion, auto_resolucion
    metadata_json = Column(Text, default="")  # JSON extra (e.g. estado_anterior, estado_nuevo)
    fecha = Column(DateTime(timezone=True), server_default=func.now())

    ticket = relationship("TicketSAT", back_populates="comentarios")

class TicketContador(Base):
    """Contador atómico por año para generar numero_ticket sin condiciones de carrera."""
    __tablename__ = "ticket_contadores"
    anio = Column(Integer, primary_key=True)
    ultimo = Column(Integer, nullable=False, default=0)


# ---------------------------------------------------------------------
# Funciones principales
# ---------------------------------------------------------------------

def _ejecutar_migraciones() -> None:
    """Lleva el esquema a la última revisión de Alembic.

    Si encuentra una base de datos anterior a Alembic (tiene tablas pero no
    alembic_version, porque se creó con create_all), la adopta marcándola en la
    revisión actual en lugar de intentar recrear el esquema.
    """
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BASE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BASE_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", DATABASE_URL)

    tablas = set(inspect(engine).get_table_names())
    if "alembic_version" not in tablas and "manuales" in tablas:
        logger.info("Base de datos preexistente sin historial de Alembic: se adopta en head.")
        command.stamp(cfg, "head")

    command.upgrade(cfg, "head")
    logger.info("Migraciones aplicadas: esquema en head.")


def init_db() -> None:
    """Aplica las migraciones y crea el usuario admin por defecto."""
    try:
        _ejecutar_migraciones()

        # Crear usuario administrador si no existe
        db = SessionLocal()
        try:
            admin_user = db.query(User).filter(User.email == "admin@empresa.com").first()
            if not admin_user:
                env_password = os.environ.get("ADMIN_DEFAULT_PASSWORD")
                if env_password:
                    admin_password = env_password
                    logger.info("Usuario admin inicial configurado desde ADMIN_DEFAULT_PASSWORD.")
                else:
                    admin_password = secrets.token_urlsafe(16)
                    # Guardar en archivo local temporal seguro en lugar de volcar en stdout/logs centralizados
                    try:
                        from pathlib import Path
                        creds_file = Path(".admin_initial_password")
                        creds_file.write_text(f"admin@empresa.com:{admin_password}\n", encoding="utf-8")
                        logger.warning("="*60)
                        logger.warning("USUARIO ADMIN CREADO POR PRIMERA VEZ (admin@empresa.com)")
                        logger.warning("Contraseña guardada en '.admin_initial_password'. ¡Bórralo tras iniciar sesión!")
                        logger.warning("="*60)
                    except Exception:
                        logger.warning(f"Usuario admin inicial: admin@empresa.com / Contraseña: {admin_password}")

                hashed_pw = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode("utf-8")
                nuevo_admin = User(email="admin@empresa.com", password_hash=hashed_pw, role="admin", is_first_login=True)
                db.add(nuevo_admin)
                db.commit()
        finally:
            db.close()
    except Exception as e:
        # No se puede continuar: arrancar con el esquema a medias deja la aplicación
        # sirviendo peticiones contra tablas que no existen.
        logger.error(f"Error inicializando base de datos: {e}")
        raise

def insertar_manual(
    nombre_original: str,
    nombre_archivo: str,
    dispositivo: str,
    categoria: str,
    paginas: List[Tuple[str, bool]],
    nivel_acceso: str = "publico",
    etiquetas: str = "",
    contenido_hash: str = ""
) -> int:
    db = SessionLocal()
    try:
        nuevo_manual = Manual(
            nombre_original=nombre_original,
            nombre_archivo=nombre_archivo,
            dispositivo=dispositivo,
            categoria=categoria,
            etiquetas=etiquetas,
            num_paginas=len(paginas),
            nivel_acceso=nivel_acceso,
            contenido_hash=contenido_hash or None
        )
        db.add(nuevo_manual)
        db.flush() # Para obtener el ID

        paginas_db = []
        for i, (texto_pagina, es_ocr) in enumerate(paginas, start=1):
            p = Pagina(
                manual_id=nuevo_manual.id,
                numero_pagina=i,
                texto=texto_pagina,
                obtenido_por_ocr=es_ocr
            )
            paginas_db.append(p)
        
        db.add_all(paginas_db)
        db.commit()
        return nuevo_manual.id
    finally:
        db.close()

def actualizar_manual(manual_id: int, dispositivo: str, categoria: str, nivel_acceso: str, etiquetas: str, nombre_original: Optional[str] = None) -> bool:
    db = SessionLocal()
    try:
        m = db.query(Manual).filter(Manual.id == manual_id).first()
        if not m:
            return False
        if nombre_original:
            m.nombre_original = nombre_original
        m.dispositivo = dispositivo
        m.categoria = categoria
        m.nivel_acceso = nivel_acceso
        m.etiquetas = etiquetas
        db.commit()
        return True
    finally:
        db.close()

def actualizar_paginas_manual(manual_id: int, paginas: list):
    db = SessionLocal()
    try:
        # Eliminar páginas antiguas
        db.query(Pagina).filter(Pagina.manual_id == manual_id).delete()
        
        # Insertar nuevas
        paginas_db = []
        for i, (texto_pagina, es_ocr) in enumerate(paginas, start=1):
            p = Pagina(
                manual_id=manual_id,
                numero_pagina=i,
                texto=texto_pagina,
                obtenido_por_ocr=es_ocr
            )
            paginas_db.append(p)
            
        db.add_all(paginas_db)
        
        # Actualizar contador de páginas
        manual = db.query(Manual).filter(Manual.id == manual_id).first()
        if manual:
            manual.num_paginas = len(paginas)
            
        db.commit()
    finally:
        db.close()

def listar_manuales():
    db = SessionLocal()
    try:
        manuales = db.query(Manual).order_by(Manual.fecha_subida.desc()).all()
        return [
            {
                "id": m.id,
                "nombre_original": m.nombre_original,
                "nombre_archivo": m.nombre_archivo,
                "dispositivo": m.dispositivo,
                "categoria": m.categoria,
                "etiquetas": m.etiquetas or "",
                "num_paginas": m.num_paginas,
                "nivel_acceso": m.nivel_acceso,
                "fecha_subida": str(m.fecha_subida)
            } for m in manuales
        ]
    finally:
        db.close()

def listar_filtros() -> Tuple[List[str], List[str], List[str]]:
    db = SessionLocal()
    try:
        dispositivos_m = db.query(Manual.dispositivo).filter(Manual.dispositivo.isnot(None), Manual.dispositivo != "").distinct().all()
        categorias_m = db.query(Manual.categoria).filter(Manual.categoria.isnot(None), Manual.categoria != "").distinct().all()
        
        dispositivos_v = db.query(Video.dispositivo).filter(Video.dispositivo.isnot(None), Video.dispositivo != "").distinct().all()
        categorias_v = db.query(Video.categoria).filter(Video.categoria.isnot(None), Video.categoria != "").distinct().all()

        dispositivos = sorted(list(set([d[0] for d in dispositivos_m + dispositivos_v if d[0]])))
        categorias = sorted(list(set([c[0] for c in categorias_m + categorias_v if c[0]])))
        
        # Extraer etiquetas únicas de manuales y videos
        manuales_tags = db.query(Manual.etiquetas).filter(Manual.etiquetas.isnot(None), Manual.etiquetas != "").all()
        videos_tags = db.query(Video.etiquetas).filter(Video.etiquetas.isnot(None), Video.etiquetas != "").all()
        tags_set = set()
        for mt in manuales_tags + videos_tags:
            if mt[0]:
                for t in mt[0].split(","):
                    tag_limpio = t.strip()
                    if tag_limpio:
                        tags_set.add(tag_limpio)
                        
        return dispositivos, categorias, sorted(list(tags_set))
    finally:
        db.close()

def obtener_manual(manual_id: int):
    db = SessionLocal()
    try:
        m = db.query(Manual).filter(Manual.id == manual_id).first()
        if m:
            return {
                "id": m.id,
                "nombre_original": m.nombre_original,
                "nombre_archivo": m.nombre_archivo,
                "dispositivo": m.dispositivo,
                "categoria": m.categoria,
                "etiquetas": m.etiquetas or "",
                "nivel_acceso": m.nivel_acceso
            }
        return None
    finally:
        db.close()

def obtener_manual_por_archivo(nombre_archivo: str, db: Optional[Any] = None):
    """Busca un manual por su nombre de archivo.

    Devuelve también `categoria` y `etiquetas`, que antes faltaban. El
    sincronizador decide con ellas si al manual le faltan metadatos, y al no
    llegar nunca daba por vacías las etiquetas de todos: en **cada arranque**
    reescribía dispositivo, categoría y nivel de acceso de la biblioteca
    entera, borrando lo que hubiera elegido el administrador al subir el PDF.
    """
    cerrar_db = db is None
    if db is None:
        db = SessionLocal()
    try:
        m = db.query(Manual).filter(Manual.nombre_archivo == nombre_archivo).first()
        if m:
            return {
                "id": m.id,
                "nombre_original": m.nombre_original,
                "nombre_archivo": m.nombre_archivo,
                "dispositivo": m.dispositivo,
                "categoria": m.categoria,
                "etiquetas": m.etiquetas,
                "nivel_acceso": m.nivel_acceso
            }
        return None
    finally:
        if cerrar_db:
            db.close()

def calcular_hash_contenido(datos: bytes) -> str:
    """SHA-256 del PDF, que es lo unico que identifica de verdad un documento.

    El nombre no sirve: el mismo fichero subido dos veces llega con nombres
    distintos, y dos ficheros distintos pueden llamarse igual.
    """
    import hashlib
    return hashlib.sha256(datos).hexdigest()


def obtener_manual_por_hash(contenido_hash: str, db=None) -> Optional[dict]:
    """Devuelve el manual que ya tiene ese contenido, o None.

    `db` es opcional para poder pasar una sesión existente (los tests usan una
    base de datos distinta de la del engine del módulo). Sin él abre la suya,
    como el resto de funciones de manuales.
    """
    if not contenido_hash:
        return None
    propia = db is None
    db = db or SessionLocal()
    try:
        m = db.query(Manual).filter(Manual.contenido_hash == contenido_hash).first()
        if not m:
            return None
        return {"id": m.id, "nombre_original": m.nombre_original, "nombre_archivo": m.nombre_archivo}
    finally:
        if propia:
            db.close()


def fijar_hash_manual(manual_id: int, contenido_hash: str, db=None) -> None:
    """Rellena el hash de un manual dado de alta antes de que existiera la columna.

    Solo rellena huecos: si ya tiene hash no lo pisa, porque reescribirlo
    enmascararía que el fichero de disco ha cambiado.
    """
    propia = db is None
    db = db or SessionLocal()
    try:
        m = db.query(Manual).filter(Manual.id == manual_id).first()
        if m and not m.contenido_hash:
            m.contenido_hash = contenido_hash
            db.commit()
    finally:
        if propia:
            db.close()


def eliminar_manual(manual_id: int) -> None:
    db = SessionLocal()
    try:
        manual = db.query(Manual).filter(Manual.id == manual_id).first()
        if manual:
            db.delete(manual)
            db.commit()
    finally:
        db.close()

# ---------------------------------------------------------------------
# Gestión de Videos (YouTube)
# ---------------------------------------------------------------------

def insertar_video(
    video_id: str,
    titulo: str,
    canal: str,
    url: str,
    miniatura_url: str,
    dispositivo: str = "",
    categoria: str = "",
    etiquetas: str = "",
    nivel_acceso: str = "publico",
    transcripcion_texto: str = "",
    fragmentos: list = None,
    db: Optional[Any] = None
) -> int:
    # `db` permite pasar una sesion ya abierta (los tests usan la base de
    # pruebas); si no se pasa, se abre y se cierra una propia como siempre.
    cerrar_db = db is None
    if db is None:
        db = SessionLocal()
    try:
        video_existente = db.query(Video).filter(Video.video_id == video_id).first()
        if video_existente:
            video_existente.titulo = titulo
            video_existente.canal = canal
            video_existente.miniatura_url = miniatura_url
            if dispositivo: video_existente.dispositivo = dispositivo
            if categoria: video_existente.categoria = categoria
            if etiquetas: video_existente.etiquetas = etiquetas
            video_existente.nivel_acceso = nivel_acceso

            # El contenido textual solo se pisa si el que llega trae algo.
            # Los 43 videos del canal son mudos: YouTube no da transcripcion y
            # el texto util viene del pipeline de vision/OCR (descarga-videos).
            # Sin esta guarda, una sola re-sincronizacion dejaba el video sin
            # texto y sin fragmentos, en silencio y sin forma de recuperarlo.
            if transcripcion_texto:
                video_existente.transcripcion_texto = transcripcion_texto

            if fragmentos:
                db.query(VideoFragmento).filter(VideoFragmento.video_id == video_existente.id).delete()
                db_frags = [
                    VideoFragmento(
                        video_id=video_existente.id,
                        segundo_inicio=int(f.get("start", 0)),
                        duracion=int(f.get("duration", 0)),
                        texto=f.get("text", "")
                    ) for f in fragmentos
                ]
                db.add_all(db_frags)
            db.commit()
            return video_existente.id
            
        nuevo_video = Video(
            video_id=video_id,
            titulo=titulo,
            canal=canal,
            url=url,
            miniatura_url=miniatura_url,
            dispositivo=dispositivo,
            categoria=categoria,
            etiquetas=etiquetas,
            nivel_acceso=nivel_acceso,
            transcripcion_texto=transcripcion_texto
        )
        db.add(nuevo_video)
        db.flush()
        
        if fragmentos:
            db_frags = [
                VideoFragmento(
                    video_id=nuevo_video.id,
                    segundo_inicio=int(f.get("start", 0)),
                    duracion=int(f.get("duration", 0)),
                    texto=f.get("text", "")
                ) for f in fragmentos
            ]
            db.add_all(db_frags)
            
        db.commit()
        return nuevo_video.id
    finally:
        if cerrar_db:
            db.close()

def listar_videos(role: str = "admin") -> list:
    db = SessionLocal()
    try:
        query = db.query(Video).order_by(Video.fecha_subida.desc())
        if role == "comercial":
            query = query.filter(Video.nivel_acceso == "publico")
        videos = query.all()
        return [
            {
                "id": v.id,
                "video_id": v.video_id,
                "titulo": v.titulo,
                "canal": v.canal,
                "url": v.url,
                "miniatura_url": v.miniatura_url,
                "dispositivo": v.dispositivo,
                "categoria": v.categoria,
                "etiquetas": v.etiquetas or "",
                "nivel_acceso": v.nivel_acceso,
                "tiene_subtitulos": bool(v.transcripcion_texto and v.transcripcion_texto.strip()),
                "fecha_subida": str(v.fecha_subida)
            } for v in videos
        ]
    finally:
        db.close()



def eliminar_video(video_db_id: int) -> bool:
    db = SessionLocal()
    try:
        v = db.query(Video).filter(Video.id == video_db_id).first()
        if v:
            db.delete(v)
            db.commit()
            return True
        return False
    finally:
        db.close()

def actualizar_video(video_db_id: int, dispositivo: str, categoria: str, nivel_acceso: str, etiquetas: str) -> bool:
    db = SessionLocal()
    try:
        v = db.query(Video).filter(Video.id == video_db_id).first()
        if not v:
            return False
        v.dispositivo = dispositivo
        v.categoria = categoria
        v.nivel_acceso = nivel_acceso
        v.etiquetas = etiquetas
        db.commit()
        return True
    finally:
        db.close()

def obtener_video_por_youtube_id(video_id: str) -> Optional[dict]:
    """Busca un video por su ID de YouTube sin descargar transcripciones."""
    db = SessionLocal()
    try:
        v = db.query(Video).filter(Video.video_id == video_id).first()
        if not v:
            return None
        return {
            "id": v.id,
            "video_id": v.video_id,
            "titulo": v.titulo,
            "canal": v.canal,
            "dispositivo": v.dispositivo,
            "categoria": v.categoria,
            "etiquetas": v.etiquetas,
            "transcripcion_texto": v.transcripcion_texto
        }
    finally:
        db.close()

def buscar_videos(query: str, dispositivo: str = "", categoria: str = "", limite: int = 15, role: str = "admin", db: Optional[Any] = None):
    """
    Busca en videos de YouTube y sus fragmentos transcritos usando PostgreSQL FTS.
    """
    cerrar_db = False
    if db is None:
        db = SessionLocal()
        cerrar_db = True
    try:
        terminos = [t.strip() for t in query.split() if t.strip()]
        if not terminos:
            return []
            
        filtros = []
        if dispositivo:
            filtros.append("v.dispositivo = :dispositivo")
        if categoria:
            filtros.append("v.categoria = :categoria")
        if role == "comercial":
            filtros.append("v.nivel_acceso = 'publico'")
            
        where_sql = " AND ".join(filtros) if filtros else "1=1"

        sql = f"""
            WITH coincidencias AS (
                SELECT
                    v.id AS video_db_id, v.video_id, v.titulo, v.canal, v.url, v.miniatura_url,
                    v.dispositivo, v.categoria, v.etiquetas, v.nivel_acceso, v.fecha_subida,
                    COALESCE(vf.segundo_inicio, 0) as segundo_inicio,
                    ts_headline('spanish', COALESCE(vf.texto, v.titulo), websearch_to_tsquery('spanish', :query), 'StartSel=<mark>, StopSel=</mark>, MaxWords=30, MinWords=15') as fragmento,
                    ts_rank(
                        setweight(v.metadatos_tsv, 'A') ||
                        setweight(COALESCE(vf.texto_tsv, v.transcripcion_tsv), 'C'),
                        websearch_to_tsquery('spanish', :query),
                        32
                    ) as relevancia,
                    -- Relevancia del fragmento por si solo, sin el peso del titulo.
                    -- La de arriba suma el titulo (peso A), que es identico para
                    -- todos los fragmentos del mismo video: al empatar, el
                    -- DISTINCT ON elegia cualquiera y el enlace acababa casi
                    -- siempre en el segundo 0. Esto desempata por el trozo que
                    -- de verdad contiene lo buscado.
                    ts_rank(
                        COALESCE(vf.texto_tsv, v.transcripcion_tsv),
                        websearch_to_tsquery('spanish', :query),
                        32
                    ) as relevancia_fragmento
                FROM videos v
                LEFT JOIN video_fragmentos vf ON vf.video_id = v.id
                WHERE {where_sql} AND (
                    setweight(v.metadatos_tsv, 'A') ||
                    setweight(COALESCE(vf.texto_tsv, v.transcripcion_tsv), 'C')
                ) @@ websearch_to_tsquery('spanish', :query)
            ),
            mejor_por_video AS (
                SELECT DISTINCT ON (video_db_id) *
                FROM coincidencias
                ORDER BY video_db_id, relevancia_fragmento DESC NULLS LAST, relevancia DESC, segundo_inicio
            )
            SELECT * FROM mejor_por_video ORDER BY relevancia DESC LIMIT :limite
        """
        query_expandida = expandir_query(query)
        params = {"query": query_expandida, "dispositivo": dispositivo, "categoria": categoria, "limite": limite}
        filas = db.execute(text(sql), params).fetchall()

        resultados = []
        for fila in filas:
            segundos = int(fila.segundo_inicio or 0)
            mins = segundos // 60
            secs = segundos % 60
            tiempo_formateado = f"{mins:02d}:{secs:02d}"
            url_con_tiempo = f"https://www.youtube.com/watch?v={fila.video_id}&t={segundos}s"

            resultados.append({
                "tipo": "video",
                "id": fila.video_db_id,
                "video_id": fila.video_id,
                "nombre": fila.titulo,
                "titulo": fila.titulo,
                "canal": fila.canal,
                "url": url_con_tiempo,
                "url_embed": f"https://www.youtube.com/embed/{fila.video_id}?start={segundos}&autoplay=1",
                "miniatura": fila.miniatura_url,
                "dispositivo": fila.dispositivo,
                "categoria": fila.categoria,
                "etiquetas": fila.etiquetas or "",
                "nivel_acceso": fila.nivel_acceso,
                "segundo": segundos,
                "tiempo_formateado": tiempo_formateado,
                "fragmento": fila.fragmento,
                "relevancia": fila.relevancia,
                "fecha_subida": str(fila.fecha_subida)
            })
            
        return resultados[:limite]
    except Exception as e:
        logger.error(f"Error en búsqueda de videos: {e}")
        return []
    finally:
        if cerrar_db:
            db.close()

def buscar(query: str, dispositivo: str = "", categoria: str = "", orden: str = "relevancia", limite: int = 20, role: str = "admin"):
    """
    Busca por palabra usando Full Text Search de PostgreSQL y filtra por ROL.
    Combina manuales PDF y videos de YouTube.
    """
    db = SessionLocal()
    try:
        terminos = [t.strip() for t in query.split() if t.strip()]
        if not terminos:
            return {"todos": [], "manuales": [], "videos": [], "total_manuales": 0, "total_videos": 0}
        
        # Filtros base
        filtros = []
        if dispositivo:
            filtros.append(f"m.dispositivo = :dispositivo")
        if categoria:
            filtros.append(f"m.categoria = :categoria")
            
        # RBAC: Control de acceso por rol
        if role == "comercial":
            filtros.append("m.nivel_acceso = 'publico'")
            
        where_sql = " AND ".join(filtros) if filtros else "1=1"
        
        sql = f"""
            WITH coincidencias AS (
                SELECT
                    m.id AS manual_id, m.nombre_original, m.nombre_archivo,
                    m.dispositivo, m.categoria, m.etiquetas, m.num_paginas, m.fecha_subida, m.nivel_acceso,
                    p.numero_pagina,
                    COUNT(*) OVER (PARTITION BY m.id) AS paginas_coincidentes,
                    ts_headline('spanish', p.texto, websearch_to_tsquery('spanish', :query), 'StartSel=<mark>, StopSel=</mark>, MaxWords=30, MinWords=15') as fragmento,
                    ts_rank(
                        setweight(m.metadatos_tsv, 'A') ||
                        setweight(p.texto_tsv, 'C'),
                        websearch_to_tsquery('spanish', :query),
                        32
                    ) as relevancia
                FROM paginas p
                JOIN manuales m ON m.id = p.manual_id
                WHERE {where_sql} AND (
                    setweight(m.metadatos_tsv, 'A') ||
                    setweight(p.texto_tsv, 'C')
                ) @@ websearch_to_tsquery('spanish', :query)
            ),
            mejor_por_manual AS (
                SELECT DISTINCT ON (manual_id) *
                FROM coincidencias
                ORDER BY manual_id, relevancia DESC
            )
            SELECT * FROM mejor_por_manual ORDER BY relevancia DESC LIMIT :limite
        """

        query_expandida = expandir_query(query)
        params = {"query": query_expandida, "dispositivo": dispositivo, "categoria": categoria, "limite": limite}
        filas = db.execute(text(sql), params).fetchall()

        resultados_manuales = []
        for fila in filas:
            mid = fila.manual_id
            resultados_manuales.append({
                "tipo": "manual",
                "id": mid,
                "manual_id": mid,
                "nombre": fila.nombre_original,
                "nombre_original": fila.nombre_original,
                "archivo": fila.nombre_archivo,
                "nombre_archivo": fila.nombre_archivo,
                "dispositivo": fila.dispositivo,
                "categoria": fila.categoria,
                "etiquetas": fila.etiquetas or "",
                "num_paginas": fila.num_paginas,
                "paginas": fila.num_paginas,
                "fecha_subida": str(fila.fecha_subida),
                "numero_pagina": fila.numero_pagina,
                "pagina_encontrada": fila.numero_pagina,
                "fragmento": fila.fragmento,
                "relevancia": fila.relevancia,
                "paginas_coincidentes": fila.paginas_coincidentes,
                "nivel_acceso": fila.nivel_acceso
            })

        resultados_videos = buscar_videos(query_expandida, dispositivo=dispositivo, categoria=categoria, limite=limite, role=role, db=db)

        if orden == "reciente":
            resultados_manuales.sort(key=lambda r: r["fecha_subida"], reverse=True)
            resultados_videos.sort(key=lambda r: r["fecha_subida"], reverse=True)
        elif orden == "paginas_coincidentes":
            resultados_manuales.sort(key=lambda r: r["paginas_coincidentes"], reverse=True)

        combinados = resultados_manuales + resultados_videos
        if orden == "reciente":
            combinados.sort(key=lambda r: r["fecha_subida"], reverse=True)
        else:
            combinados.sort(key=lambda r: r.get("relevancia", 0), reverse=True)
            
        return {
            "todos": combinados[:limite],
            "manuales": resultados_manuales[:limite],
            "videos": resultados_videos[:limite],
            "total_manuales": len(resultados_manuales),
            "total_videos": len(resultados_videos)
        }
    except Exception as e:
        logger.error(f"Error en búsqueda: {e}")
        return {"todos": [], "manuales": [], "videos": [], "total_manuales": 0, "total_videos": 0}
    finally:
        db.close()

# ---------------------------------------------------------------------
# Gestión de Usuarios (Admin)
# ---------------------------------------------------------------------
def listar_usuarios():
    db = SessionLocal()
    try:
        usuarios = db.query(User).all()
        return [{"id": u.id, "email": u.email, "role": u.role, "is_first_login": u.is_first_login} for u in usuarios]
    finally:
        db.close()



def crear_usuario(email: str, password_clara: str, role: str):
    if role not in ROLES_VALIDOS:
        raise ValueError(f"Rol inválido: '{role}'. Roles válidos: {ROLES_VALIDOS}")
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).first():
            return None  # Ya existe
        hashed_pw = bcrypt.hashpw(password_clara.encode('utf-8'), bcrypt.gensalt()).decode("utf-8")
        nuevo_user = User(email=email, password_hash=hashed_pw, role=role, is_first_login=True)
        db.add(nuevo_user)
        db.commit()
        db.refresh(nuevo_user)
        return nuevo_user
    finally:
        db.close()

def eliminar_usuario(user_id: int):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            db.delete(user)
            db.commit()
            return True
        return False
    finally:
        db.close()

def cambiar_rol_usuario(user_id: int, nuevo_rol: str):
    if nuevo_rol not in ROLES_VALIDOS:
        raise ValueError(f"Rol inválido: '{nuevo_rol}'. Roles válidos: {ROLES_VALIDOS}")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.role = nuevo_rol
            db.commit()
            return True
        return False
    finally:
        db.close()

def cambiar_password_usuario(user_id: int, nueva_password: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            hashed_pw = bcrypt.hashpw(nueva_password.encode('utf-8'), bcrypt.gensalt()).decode("utf-8")
            user.password_hash = hashed_pw
            user.is_first_login = False
            db.commit()
            return True
        return False
    finally:
        db.close()


# ---------------------------------------------------------------------
# Operaciones Mini-CRM Tickets SAT
# ---------------------------------------------------------------------

def obtener_grupos_incidencia(db, solo_activos: bool = True) -> List["IncidentGroup"]:
    """Lista los grupos de incidencia en su orden de presentación."""
    query = db.query(IncidentGroup)
    if solo_activos:
        query = query.filter(IncidentGroup.is_active.is_(True))
    return query.order_by(IncidentGroup.sort_order, IncidentGroup.name).all()


def obtener_grupo_por_codigo(db, code: str) -> Optional["IncidentGroup"]:
    if not code:
        return None
    return db.query(IncidentGroup).filter(IncidentGroup.code == code.strip().upper()).first()


ESTADOS_REVISION_GRUPO = {"estable", "nuevo", "en_revision"}


def crear_grupo_incidencia(db, datos: dict) -> "IncidentGroup":
    """Da de alta un grupo. El código se normaliza y debe ser único.

    Nace en estado 'nuevo' salvo que se diga otra cosa: un grupo creado sobre la
    marcha durante una llamada no está al mismo nivel que los 9 que salieron del
    análisis de 119 incidencias, y en la reunión conviene poder distinguirlos.
    """
    code = (datos.get("code") or "").strip().upper().replace(" ", "_")
    if not code:
        raise ValueError("El código del grupo es obligatorio")
    if not (datos.get("name") or "").strip():
        raise ValueError("El nombre del grupo es obligatorio")
    if obtener_grupo_por_codigo(db, code):
        raise ValueError(f"Ya existe un grupo con el código {code}")

    estado = datos.get("estado_revision") or "nuevo"
    if estado not in ESTADOS_REVISION_GRUPO:
        raise ValueError(f"Estado de revisión no válido: {estado}")

    # Al final de la lista, para no reordenar lo que ya estaba colocado.
    if datos.get("sort_order") is None:
        maximo = db.query(func.max(IncidentGroup.sort_order)).scalar()
        sort_order = (maximo or 0) + 10
    else:
        sort_order = int(datos["sort_order"])

    grupo = IncidentGroup(
        code=code,
        name=datos["name"].strip(),
        description=(datos.get("description") or "").strip(),
        is_active=datos.get("is_active", True),
        sort_order=sort_order,
        estado_revision=estado,
    )
    db.add(grupo)
    db.commit()
    db.refresh(grupo)
    return grupo


def actualizar_grupo_incidencia(db, code: str, datos: dict) -> Optional["IncidentGroup"]:
    """Edita un grupo. El código no se cambia: es la referencia estable.

    Renombrar el código rompería cualquier integración o exportación que lo use;
    para eso está fusionar_grupos_incidencia().
    """
    grupo = obtener_grupo_por_codigo(db, code)
    if not grupo:
        return None

    if "estado_revision" in datos and datos["estado_revision"] is not None:
        if datos["estado_revision"] not in ESTADOS_REVISION_GRUPO:
            raise ValueError(f"Estado de revisión no válido: {datos['estado_revision']}")
        grupo.estado_revision = datos["estado_revision"]
    if datos.get("name"):
        grupo.name = datos["name"].strip()
    if datos.get("description") is not None:
        grupo.description = datos["description"].strip()
    if datos.get("is_active") is not None:
        grupo.is_active = bool(datos["is_active"])
    if datos.get("sort_order") is not None:
        grupo.sort_order = int(datos["sort_order"])

    db.commit()
    db.refresh(grupo)
    return grupo


def reordenar_grupos_incidencia(db, codigos: List[str]) -> List["IncidentGroup"]:
    """Fija el orden de presentación a partir de la lista de códigos recibida.

    Se numera de 10 en 10 para que luego quepa insertar un grupo entre dos sin
    tener que reescribir toda la tabla.
    """
    for posicion, code in enumerate(codigos, start=1):
        grupo = obtener_grupo_por_codigo(db, code)
        if grupo:
            grupo.sort_order = posicion * 10
    db.commit()
    return obtener_grupos_incidencia(db, solo_activos=False)


def fusionar_grupos_incidencia(db, code_origen: str, code_destino: str) -> Dict[str, Any]:
    """Mueve todo lo del grupo origen al destino y borra el origen.

    Es la operación que hace falta cuando el workshop decide que dos grupos eran
    el mismo. Se mueven los tickets que lo tenían como principal y también los
    secundarios, evitando dejar duplicados en la tabla puente cuando un ticket ya
    tenía ambos grupos.
    """
    origen = obtener_grupo_por_codigo(db, code_origen)
    destino = obtener_grupo_por_codigo(db, code_destino)
    if not origen or not destino:
        raise ValueError("Grupo de origen o de destino inexistente")
    if origen.id == destino.id:
        raise ValueError("No se puede fusionar un grupo consigo mismo")

    principales = db.query(TicketSAT).filter(TicketSAT.grupo_id == origen.id).count()
    db.query(TicketSAT).filter(TicketSAT.grupo_id == origen.id).update(
        {TicketSAT.grupo_id: destino.id}, synchronize_session=False
    )

    # Los secundarios van en dos pasadas: primero se borran todos los del origen
    # y solo despues se insertan los que faltan. Hacerlo fila a fila mezclaria en
    # el mismo flush el borrado y el alta de la misma clave compuesta, y
    # SQLAlchemy avisa de que el DELETE no encuentra la fila que espera.
    tickets_origen = {
        fila.ticket_id
        for fila in db.query(TicketGrupoSecundario).filter(
            TicketGrupoSecundario.grupo_id == origen.id
        ).all()
    }
    ya_con_destino = set()
    if tickets_origen:
        ya_con_destino = {
            fila.ticket_id
            for fila in db.query(TicketGrupoSecundario).filter(
                TicketGrupoSecundario.grupo_id == destino.id,
                TicketGrupoSecundario.ticket_id.in_(tickets_origen),
            ).all()
        }

    db.query(TicketGrupoSecundario).filter(
        TicketGrupoSecundario.grupo_id == origen.id
    ).delete(synchronize_session=False)
    db.flush()

    por_mover = tickets_origen - ya_con_destino
    for ticket_id in por_mover:
        db.add(TicketGrupoSecundario(ticket_id=ticket_id, grupo_id=destino.id))
    movidos = len(por_mover)

    db.delete(origen)
    db.commit()
    return {
        "origen": code_origen.strip().upper(),
        "destino": destino.code,
        "tickets_movidos": principales,
        "secundarios_movidos": movidos,
    }


def eliminar_grupo_incidencia(db, code: str) -> Dict[str, Any]:
    """Borra un grupo, pero solo si no lo usa ningún ticket.

    Con tickets detrás, borrar los dejaría sin clasificar en silencio (la clave
    foránea es SET NULL). Para eso está fusionar, o desactivar si lo que se
    quiere es dejar de ofrecerlo sin perder el histórico.
    """
    grupo = obtener_grupo_por_codigo(db, code)
    if not grupo:
        return {"ok": False, "motivo": "no_existe"}

    principales = db.query(TicketSAT).filter(TicketSAT.grupo_id == grupo.id).count()
    secundarios = db.query(TicketGrupoSecundario).filter(
        TicketGrupoSecundario.grupo_id == grupo.id
    ).count()
    if principales or secundarios:
        return {
            "ok": False,
            "motivo": "en_uso",
            "tickets": principales,
            "secundarios": secundarios,
        }

    db.delete(grupo)
    db.commit()
    return {"ok": True}


def contar_tickets_por_grupo(db) -> List[Dict[str, Any]]:
    """Tickets por grupo, incluidos los grupos sin ninguno y los tickets sin grupo.

    Un grupo vacío también es información: dice que la taxonomía tiene una rama
    que no se usa. Por eso es LEFT JOIN y no un GROUP BY sobre los tickets.
    """
    filas = (
        db.query(IncidentGroup.code, IncidentGroup.name, func.count(TicketSAT.id))
        .outerjoin(TicketSAT, TicketSAT.grupo_id == IncidentGroup.id)
        .group_by(IncidentGroup.id, IncidentGroup.code, IncidentGroup.name, IncidentGroup.sort_order)
        .order_by(IncidentGroup.sort_order, IncidentGroup.name)
        .all()
    )
    resultado = [{"code": c, "name": n, "tickets": t} for c, n, t in filas]

    sin_grupo = db.query(TicketSAT).filter(TicketSAT.grupo_id.is_(None)).count()
    resultado.append({"code": "", "name": "Sin grupo asignado", "tickets": sin_grupo})
    return resultado


def generar_numero_ticket(db) -> str:
    """
    Genera un identificador correlativo único para tickets SAT, e.g. SAT-2026-0001.
    Usa un UPSERT atómico sobre ticket_contadores (en vez de leer el último
    numero_ticket y sumar 1 en Python) para evitar que dos creaciones de ticket
    concurrentes obtengan el mismo número.
    """
    import datetime
    anio = datetime.datetime.now().year

    # El contador puede haberse quedado atras respecto a la tabla: los tickets
    # importados del historico se insertaron con su numero ya puesto, sin pasar
    # por aqui, asi que el contador marcaba 1 con 48 tickets creados y cada alta
    # nueva moria con una violacion de clave unica. Se toma como suelo el mayor
    # numero que exista de verdad, de modo que el desfase se corrige solo.
    siguiente_real = db.execute(
        text("""
            SELECT COALESCE(MAX(CAST(SPLIT_PART(numero_ticket, '-', 3) AS INTEGER)), 0) + 1
            FROM tickets_sat
            WHERE numero_ticket LIKE :patron
        """),
        {"patron": f"SAT-{anio}-%"}
    ).scalar() or 1

    # GREATEST conserva la atomicidad del UPSERT: si dos altas simultaneas
    # calculan el mismo suelo, la segunda sigue subiendo por la rama +1 y no
    # repiten numero.
    fila = db.execute(
        text("""
            INSERT INTO ticket_contadores (anio, ultimo) VALUES (:anio, :suelo)
            ON CONFLICT (anio) DO UPDATE
                SET ultimo = GREATEST(ticket_contadores.ultimo + 1, excluded.ultimo)
            RETURNING ultimo
        """),
        {"anio": anio, "suelo": siguiente_real}
    ).fetchone()
    secuencia = fila.ultimo
    return f"SAT-{anio}-{secuencia:04d}"

def _resolver_grupo_id(db, codigo_grupo: Optional[str]) -> Optional[int]:
    """Traduce un código de grupo a su id. Un código desconocido no rompe el alta."""
    grupo = obtener_grupo_por_codigo(db, codigo_grupo or "")
    return grupo.id if grupo else None


def crear_ticket_sat(db, ticket_data: dict, creado_por: str = "") -> TicketSAT:
    numero = generar_numero_ticket(db)
    nuevo_ticket = TicketSAT(
        numero_ticket=numero,
        instalador=ticket_data.get("instalador", "").strip(),
        email=ticket_data.get("email", "").strip(),
        telefono=ticket_data.get("telefono", "").strip(),
        obra=ticket_data.get("obra", "").strip(),
        distribuidor=ticket_data.get("distribuidor", "").strip(),
        dispositivo=ticket_data.get("dispositivo", "").strip(),
        motor=ticket_data.get("motor", "").strip(),
        sintoma=ticket_data.get("sintoma", "").strip(),
        diagnostico=ticket_data.get("diagnostico", "").strip(),
        solucion=ticket_data.get("solucion", "").strip(),
        grupo_id=_resolver_grupo_id(db, ticket_data.get("grupo")),
        estado=ticket_data.get("estado", "en_espera"),
        prioridad=ticket_data.get("prioridad", "normal"),
        creado_por=creado_por,
        notas=ticket_data.get("notas", "").strip()
    )
    db.add(nuevo_ticket)
    db.commit()
    db.refresh(nuevo_ticket)
    return nuevo_ticket

def _filtrar_tickets_query(db, q: Optional[str] = None, estado: Optional[str] = None, grupo: Optional[str] = None):
    """Construye la query base filtrada para tickets (reutilizable)."""
    query = db.query(TicketSAT)
    if estado and estado != "todos":
        query = query.filter(TicketSAT.estado == estado)
    if grupo and grupo != "todos":
        if grupo == "sin_grupo":
            query = query.filter(TicketSAT.grupo_id.is_(None))
        else:
            query = query.join(IncidentGroup, TicketSAT.grupo_id == IncidentGroup.id).filter(
                IncidentGroup.code == grupo.strip().upper()
            )
    if q and q.strip():
        termino = f"%{q.strip()}%"
        query = query.filter(
            (TicketSAT.numero_ticket.ilike(termino)) |
            (TicketSAT.instalador.ilike(termino)) |
            (TicketSAT.email.ilike(termino)) |
            (TicketSAT.telefono.ilike(termino)) |
            (TicketSAT.obra.ilike(termino)) |
            (TicketSAT.dispositivo.ilike(termino)) |
            (TicketSAT.distribuidor.ilike(termino)) |
            (TicketSAT.sintoma.ilike(termino)) |
            (TicketSAT.diagnostico.ilike(termino))
        )
    return query

def obtener_tickets_sat(db, q: Optional[str] = None, estado: Optional[str] = None, limit: int = 50, offset: int = 0, grupo: Optional[str] = None) -> Tuple[List[TicketSAT], int]:
    """Devuelve (tickets, total_count) con paginación."""
    query = _filtrar_tickets_query(db, q=q, estado=estado, grupo=grupo)
    total = query.count()
    tickets = query.order_by(TicketSAT.id.desc()).offset(offset).limit(limit).all()
    return tickets, total

def obtener_ticket_por_id(db, ticket_id: int) -> Optional[TicketSAT]:
    return db.query(TicketSAT).filter(TicketSAT.id == ticket_id).first()

def actualizar_ticket_sat(db, ticket_id: int, datos_actualizacion: dict) -> Optional[TicketSAT]:
    ticket = obtener_ticket_por_id(db, ticket_id)
    if not ticket:
        return None
    datos = dict(datos_actualizacion)

    # 'grupo' llega como codigo (VINCULACION) y la columna es grupo_id. Sin
    # traducirlo, el setattr caeria sobre la relacion y reventaria, que es por
    # lo que no se podia reclasificar un ticket ni a mano.
    #
    # Una cadena vacia desclasifica a proposito. Un codigo que no existe -una
    # errata- deja el grupo como estaba: perder la clasificacion de un ticket
    # por escribir mal el codigo seria el tipo de borrado silencioso que este
    # proyecto ya ha pagado varias veces.
    if "grupo" in datos:
        codigo = (datos.pop("grupo") or "").strip()
        if not codigo:
            ticket.grupo_id = None
        else:
            resuelto = _resolver_grupo_id(db, codigo)
            if resuelto is not None:
                datos["grupo_id"] = resuelto
            else:
                logger.warning(
                    f"Grupo '{codigo}' desconocido al actualizar el ticket {ticket_id}: "
                    f"se conserva el que tenia."
                )

    for campo, valor in datos.items():
        if hasattr(ticket, campo) and valor is not None:
            setattr(ticket, campo, valor)
    db.commit()
    db.refresh(ticket)
    return ticket

def eliminar_ticket_sat(db, ticket_id: int) -> bool:
    ticket = obtener_ticket_por_id(db, ticket_id)
    if not ticket:
        return False
    db.delete(ticket)
    db.commit()
    return True

def obtener_stats_tickets_sat(db) -> dict:
    """Stats mejorados con métricas SLA y tiempos de resolución."""
    import datetime
    total = db.query(TicketSAT).count()
    en_espera = db.query(TicketSAT).filter(TicketSAT.estado == "en_espera").count()
    resuelto = db.query(TicketSAT).filter(TicketSAT.estado == "resuelto").count()
    rma_pendiente = db.query(TicketSAT).filter(TicketSAT.estado == "rma_pendiente").count()
    descartado = db.query(TicketSAT).filter(TicketSAT.estado == "descartado").count()

    # Tiempo medio de resolución (en horas)
    tiempo_medio_horas = None
    try:
        resueltos = db.query(TicketSAT).filter(
            TicketSAT.estado == "resuelto",
            TicketSAT.fecha_creacion.isnot(None),
            TicketSAT.fecha_actualizacion.isnot(None)
        ).all()
        if resueltos:
            tiempos = []
            for t in resueltos:
                if t.fecha_actualizacion and t.fecha_creacion:
                    delta = t.fecha_actualizacion - t.fecha_creacion
                    tiempos.append(delta.total_seconds() / 3600)
            if tiempos:
                tiempo_medio_horas = round(sum(tiempos) / len(tiempos), 1)
    except Exception:
        pass

    # Tickets creados esta semana y este mes
    ahora = datetime.datetime.now(datetime.timezone.utc)
    inicio_semana = ahora - datetime.timedelta(days=ahora.weekday())
    inicio_semana = inicio_semana.replace(hour=0, minute=0, second=0, microsecond=0)
    inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    esta_semana = db.query(TicketSAT).filter(TicketSAT.fecha_creacion >= inicio_semana).count()
    este_mes = db.query(TicketSAT).filter(TicketSAT.fecha_creacion >= inicio_mes).count()
    resueltos_semana = db.query(TicketSAT).filter(
        TicketSAT.estado == "resuelto",
        TicketSAT.fecha_actualizacion >= inicio_semana
    ).count()

    # Tickets urgentes abiertos (en_espera con prioridad urgente)
    urgentes_abiertos = db.query(TicketSAT).filter(
        TicketSAT.estado == "en_espera",
        TicketSAT.prioridad == "urgente"
    ).count()

    return {
        "total": total,
        "en_espera": en_espera,
        "resuelto": resuelto,
        "rma_pendiente": rma_pendiente,
        "descartado": descartado,
        "urgentes_abiertos": urgentes_abiertos,
        "tiempo_medio_resolucion_horas": tiempo_medio_horas,
        "esta_semana": esta_semana,
        "este_mes": este_mes,
        "resueltos_semana": resueltos_semana,
        "por_grupo": contar_tickets_por_grupo(db),
        "cierre": obtener_stats_cierre_tecnico(db)
    }


def obtener_stats_cierre_tecnico(db) -> dict:
    """Métricas que solo existen gracias al cierre técnico (G10 alimentando G15).

    Todos los porcentajes se calculan sobre los tickets que **tienen cierre**, no
    sobre el total. Un ticket sin cerrar no es un ticket sin resolver: mezclarlos
    daría un «% documentación suficiente» que baja solo porque nadie ha rellenado
    el formulario todavía.
    """
    con_cierre = db.query(TicketSAT).filter(TicketSAT.cierre_fecha.isnot(None)).count()

    def _pct(numerador: int, denominador: int):
        return round(100 * numerador / denominador, 1) if denominador else None

    resueltos = db.query(TicketSAT).filter(TicketSAT.cierre_resuelto.is_(True)).count()
    doc_suficiente = db.query(TicketSAT).filter(TicketSAT.cierre_doc_suficiente.is_(True)).count()
    escalados = db.query(TicketSAT).filter(TicketSAT.cierre_escalado.is_(True)).count()
    # Denominador propio: "¿bastó la documentación?" solo se pregunta de verdad
    # en los cierres donde se contestó, que pueden ser menos que los cerrados.
    doc_contestados = db.query(TicketSAT).filter(TicketSAT.cierre_doc_suficiente.isnot(None)).count()

    # Tiempo de resolución medido con la fecha del cierre, no con fecha_actualizacion
    # (que cambia con cualquier edición posterior y falsea la media).
    horas = []
    for t in db.query(TicketSAT).filter(
        TicketSAT.cierre_fecha.isnot(None), TicketSAT.fecha_creacion.isnot(None)
    ).all():
        horas.append((t.cierre_fecha - t.fecha_creacion).total_seconds() / 3600)

    return {
        "con_cierre": con_cierre,
        "sin_cierre": db.query(TicketSAT).count() - con_cierre,
        "resueltos": resueltos,
        "resueltos_pct": _pct(resueltos, con_cierre),
        "documentacion_suficiente": doc_suficiente,
        "documentacion_suficiente_pct": _pct(doc_suficiente, doc_contestados),
        "escalados": escalados,
        "escalados_pct": _pct(escalados, con_cierre),
        "horas_hasta_cierre": round(sum(horas) / len(horas), 1) if horas else None,
        "documentos_mas_usados": contar_documentos_usados_en_cierres(db),
    }


def contar_documentos_usados_en_cierres(db, limite: int = 10) -> List[dict]:
    """Qué documentos resuelven de verdad — la pregunta que G10 existe para responder.

    Mezcla manuales y vídeos en una sola lista ordenada, porque al operador le da
    igual el formato: lo que quiere saber es qué material resuelve incidencias.
    """
    filas: List[dict] = []
    for modelo, columna, tipo, etiqueta in (
        (Manual, TicketSAT.cierre_manual_id, "manual", Manual.nombre_original),
        (Video, TicketSAT.cierre_video_id, "video", Video.titulo),
    ):
        consulta = (
            db.query(modelo.id, etiqueta, func.count(TicketSAT.id))
            .join(TicketSAT, columna == modelo.id)
            .group_by(modelo.id, etiqueta)
        )
        for doc_id, nombre, veces in consulta.all():
            filas.append({"tipo": tipo, "id": doc_id, "nombre": nombre, "veces": veces})

    filas.sort(key=lambda f: f["veces"], reverse=True)
    return filas[:limite]


def registrar_cierre_tecnico(db, ticket_id: int, datos: dict, autor: str = "") -> Optional[TicketSAT]:
    """Guarda el cierre técnico de un ticket y sella la fecha y el autor.

    No toca `estado`: el cierre describe lo que pasó, y el estado es el flujo de
    trabajo. Un ticket puede cerrarse con `cierre_resuelto=False` —se documenta que
    no se resolvió— y seguir en espera hasta que llegue el recambio.
    """
    import datetime
    ticket = obtener_ticket_por_id(db, ticket_id)
    if not ticket:
        return None

    campos = (
        "cierre_resuelto", "cierre_descripcion", "cierre_doc_suficiente",
        "cierre_manual_id", "cierre_video_id", "cierre_doc_texto",
        "cierre_alternativa", "cierre_escalado",
    )
    for campo in campos:
        if campo in datos and datos[campo] is not None:
            setattr(ticket, campo, datos[campo])

    ticket.cierre_fecha = datetime.datetime.now(datetime.timezone.utc)
    ticket.cierre_por = autor
    db.commit()
    db.refresh(ticket)
    return ticket


# ---------------------------------------------------------------------
# Comentarios / Historial de Tickets SAT
# ---------------------------------------------------------------------

def agregar_comentario_ticket(db, ticket_id: int, autor: str, texto: str, tipo: str = "nota", metadata_json: str = "") -> Optional[TicketComentario]:
    """Agrega un comentario o evento al historial de un ticket."""
    ticket = obtener_ticket_por_id(db, ticket_id)
    if not ticket:
        return None
    comentario = TicketComentario(
        ticket_id=ticket_id,
        autor=autor,
        texto=texto,
        tipo=tipo,
        metadata_json=metadata_json
    )
    if hasattr(db, "add"):
        db.add(comentario)
        db.commit()
        db.refresh(comentario)
    return comentario

def obtener_comentarios_ticket(db, ticket_id: int) -> List[TicketComentario]:
    """Obtiene todos los comentarios de un ticket ordenados cronológicamente."""
    if not hasattr(db, "query"):
        return []
    return db.query(TicketComentario).filter(
        TicketComentario.ticket_id == ticket_id
    ).order_by(TicketComentario.fecha.asc()).all()

def obtener_tickets_para_export(db, q: Optional[str] = None, estado: Optional[str] = None) -> List[TicketSAT]:
    """Devuelve todos los tickets filtrados sin paginación (para export CSV)."""
    query = _filtrar_tickets_query(db, q=q, estado=estado)
    return query.order_by(TicketSAT.id.desc()).all()

def _clave_dispositivo(valor: str) -> str:
    """Reduce un nombre de dispositivo a algo comparable entre tablas.

    Los tickets guardan 'C-Wall' o 'Connect-1' y los videos 'C-WALL' o
    'C-PULSAR': el mismo aparato escrito de dos formas. Comparar en crudo no
    casaba ninguno, que es como una sugerencia deja de sugerir nada.
    """
    return re.sub(r"[^a-z0-9]", "", (valor or "").lower())


# Peso de cada señal al sugerir documentación para un ticket.
# El grupo manda porque comparte vocabulario con `videos.categoria` y no depende
# de cómo esté redactado el síntoma. El síntoma va por delante del dispositivo
# aunque parezca menos fiable: el dispositivo es muy grueso —once vídeos son
# 'Connect-1'— y sin este orden un ticket de persianas recibía como primera
# sugerencia el vídeo de resetear el Connect, solo por compartir aparato.
PESO_GRUPO = 3.0
PESO_SINTOMA = 2.5
PESO_SINTOMA_PARCIAL = 1.25
PESO_DISPOSITIVO = 1.5


def _clave_dispositivo(valor: str) -> str:
    """Reduce un nombre de dispositivo a algo comparable entre tablas.

    Los tickets guardan 'C-Wall' o 'Connect-1' y los vídeos 'C-WALL' o
    'C-PULSAR': el mismo aparato escrito de dos formas. Comparar en crudo no
    casaba ninguno, que es como una sugerencia deja de sugerir nada.
    """
    return re.sub(r"[^a-z0-9]", "", (valor or "").lower())


def _consulta_amplia(sintoma: str, maximo_terminos: int = 8) -> str:
    """Convierte un síntoma largo en una consulta que tolera no acertar entero.

    La búsqueda normal exige que aparezcan todos los términos. Un síntoma
    redactado como una frase —«la persiana sube al pulsar la orden de bajar»—
    no casa con ningún vídeo, mientras que sus palabras sueltas sí. Se usa solo
    como red de seguridad y puntúa menos que la coincidencia completa.
    """
    from .sat_autoresolver import STOP_WORDS, normalizar_texto

    terminos = []
    for palabra in normalizar_texto(sintoma).split():
        if len(palabra) >= 4 and palabra not in STOP_WORDS and palabra not in terminos:
            terminos.append(palabra)
    return " or ".join(terminos[:maximo_terminos])


def sugerir_documentacion_para_ticket(db, ticket_id: int, limite: int = 6) -> Dict[str, Any]:
    """Propone los vídeos que mejor responden a un ticket concreto.

    En las 119 incidencias reales, «Vídeos» aparece 29 veces como acción
    correctiva, pero al cerrar un ticket el selector ofrecía los 43 vídeos del
    canal en una lista plana y sin orden: encontrar el que servía dependía de
    acordarse del título. Aquí se cruzan las tres cosas que el ticket ya sabe
    —grupo de incidencia, dispositivo y síntoma— y se devuelve además el
    segundo exacto del vídeo en el que aparece lo buscado.

    Cada sugerencia explica por qué está ahí: una lista ordenada sin motivo
    obliga a abrir los vídeos uno por uno para averiguarlo.
    """
    ticket = db.get(TicketSAT, ticket_id)
    if ticket is None:
        return {"videos": [], "grupo": "", "dispositivo": ""}

    codigo_grupo = ticket.grupo.code if ticket.grupo else ""
    clave_disp = _clave_dispositivo(ticket.dispositivo)

    candidatos: Dict[int, Dict[str, Any]] = {}

    def _anotar(video_db_id: int, puntos: float, motivo: str, extra: Optional[Dict[str, Any]] = None):
        ficha = candidatos.setdefault(
            video_db_id, {"puntos": 0.0, "motivos": [], "segundo": 0, "tiempo_formateado": "00:00"}
        )
        ficha["puntos"] += puntos
        if motivo and motivo not in ficha["motivos"]:
            ficha["motivos"].append(motivo)
        if extra:
            ficha.update(extra)

    # 1. Mismo grupo de incidencia. La señal más fiable, y no depende de la
    #    redacción del síntoma, que en los tickets reales va de una palabra a
    #    un párrafo.
    if codigo_grupo:
        for video in db.query(Video).filter(Video.categoria == codigo_grupo).all():
            _anotar(video.id, PESO_GRUPO, f"Mismo grupo ({codigo_grupo})")

    # 2. Texto del síntoma. Aporta el minuto exacto, que es lo que un manual en
    #    PDF no puede dar. Si la frase entera no casa, se reintenta con sus
    #    palabras sueltas y puntuando menos.
    sintoma = (ticket.sintoma or "").strip()
    if sintoma:
        coincidencias = buscar_videos(sintoma, limite=limite * 2, db=db)
        peso, plantilla = PESO_SINTOMA, "Coincide con el síntoma en el {}"
        if not coincidencias:
            amplia = _consulta_amplia(sintoma)
            if amplia:
                coincidencias = buscar_videos(amplia, limite=limite * 2, db=db)
                peso, plantilla = PESO_SINTOMA_PARCIAL, "Coincide con parte del síntoma en el {}"
        for resultado in coincidencias:
            _anotar(
                resultado["id"],
                peso,
                plantilla.format(resultado["tiempo_formateado"]),
                {
                    "segundo": resultado["segundo"],
                    "tiempo_formateado": resultado["tiempo_formateado"],
                    "fragmento": resultado.get("fragmento") or "",
                    "relevancia": float(resultado.get("relevancia") or 0.0),
                },
            )

    # 3. Mismo dispositivo. Afina dentro del grupo y por sí solo no basta: casi
    #    la mitad del catálogo está marcado como 'General'.
    if clave_disp:
        for video in db.query(Video).all():
            if _clave_dispositivo(video.dispositivo) == clave_disp:
                _anotar(video.id, PESO_DISPOSITIVO, f"Mismo dispositivo ({ticket.dispositivo})")

    if not candidatos:
        return {"videos": [], "grupo": codigo_grupo, "dispositivo": ticket.dispositivo or ""}

    videos = {v.id: v for v in db.query(Video).filter(Video.id.in_(candidatos.keys())).all()}
    sugerencias = []
    for video_db_id, ficha in candidatos.items():
        video = videos.get(video_db_id)
        if video is None:
            continue
        segundo = int(ficha.get("segundo") or 0)
        sugerencias.append({
            "id": video.id,
            "video_id": video.video_id,
            "titulo": video.titulo,
            "dispositivo": video.dispositivo or "",
            "categoria": video.categoria or "",
            "segundo": segundo,
            "tiempo_formateado": ficha.get("tiempo_formateado") or "00:00",
            "url": f"https://www.youtube.com/watch?v={video.video_id}&t={segundo}s",
            "miniatura": video.miniatura_url or "",
            "fragmento": ficha.get("fragmento", ""),
            "motivos": ficha["motivos"],
            "puntuacion": round(ficha["puntos"], 2),
            "_relevancia": float(ficha.get("relevancia") or 0.0),
        })

    # A igual puntuación manda la relevancia del texto; el título solo desempata
    # al final, para que el orden sea estable entre llamadas.
    sugerencias.sort(key=lambda s: (-s["puntuacion"], -s["_relevancia"], s["titulo"]))
    for s in sugerencias:
        s.pop("_relevancia", None)
    return {
        "videos": sugerencias[:limite],
        "grupo": codigo_grupo,
        "dispositivo": ticket.dispositivo or "",
    }


def guardar_cuestionario_asistencia(db, respuestas: Dict[str, Any], resultado: Dict[str, Any],
                                    creado_por: str = "") -> CuestionarioAsistencia:
    """Deja constancia de un cuestionario contestado y del diagnóstico que produjo.

    Se guarda siempre, incluso si el triaje no acertó: los envíos con
    diagnóstico flojo son justamente los que dicen qué preguntas faltan.

    No debe hacer fallar el triaje. Si esto revienta, el técnico tiene que
    seguir viendo su diagnóstico; lo que se pierde es un registro, no la
    respuesta al cliente, así que el que llama captura el error y sigue.
    """
    import json

    registro = CuestionarioAsistencia(
        creado_por=creado_por or "",
        dispositivo=(respuestas.get("dispositivo") or "").strip(),
        area_incidencia=(respuestas.get("area_incidencia") or "").strip(),
        diagnostico_titulo=(resultado.get("diagnostico_titulo") or "").strip(),
        confianza=float(resultado["confianza"]) if isinstance(resultado.get("confianza"), (int, float)) else None,
        respuestas_json=json.dumps(respuestas, ensure_ascii=False, default=str),
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro


def vincular_cuestionario_a_ticket(db, cuestionario_id: int, ticket_id: int) -> bool:
    """Ata un cuestionario al ticket que salió de él.

    El ticket nace después, y solo a veces: de ahí que la relación se complete
    en dos pasos en lugar de exigir el ticket al guardar el cuestionario.
    """
    registro = db.get(CuestionarioAsistencia, cuestionario_id)
    if registro is None:
        return False
    registro.ticket_id = ticket_id
    db.commit()
    return True


def obtener_cuestionarios_asistencia(db, limite: int = 50, ticket_id: Optional[int] = None) -> List[CuestionarioAsistencia]:
    """Los cuestionarios más recientes, o los de un ticket concreto."""
    consulta = db.query(CuestionarioAsistencia)
    if ticket_id is not None:
        consulta = consulta.filter(CuestionarioAsistencia.ticket_id == ticket_id)
    return consulta.order_by(CuestionarioAsistencia.id.desc()).limit(limite).all()


def estadisticas_cuestionarios(db) -> Dict[str, Any]:
    """Qué se contesta de verdad, que es lo que G3.2 necesita para diseñarse.

    Una tabla de preguntas construida a ojo repite el problema que ya hay: doce
    bloques que nadie ha validado. Con esto se puede ver qué campos se rellenan
    siempre, cuáles no los toca nadie y con qué confianza acaba el triaje.
    """
    import json

    total = db.query(CuestionarioAsistencia).count()
    if not total:
        return {"total": 0, "con_ticket": 0, "confianza_media": None, "campos": [], "por_dispositivo": []}

    con_ticket = db.query(CuestionarioAsistencia).filter(
        CuestionarioAsistencia.ticket_id.isnot(None)
    ).count()

    confianzas = [c for (c,) in db.query(CuestionarioAsistencia.confianza).all() if c is not None]
    confianza_media = round(sum(confianzas) / len(confianzas), 1) if confianzas else None

    # Cuántas veces cada campo llega con algo dentro. Un campo que nunca se
    # rellena sobra en el formulario; uno que se rellena siempre es candidato a
    # obligatorio.
    veces = {}
    for (crudo,) in db.query(CuestionarioAsistencia.respuestas_json).all():
        try:
            datos = json.loads(crudo or "{}")
        except (ValueError, TypeError):
            continue
        for clave, valor in datos.items():
            if valor in (None, "", [], {}):
                continue
            veces[clave] = veces.get(clave, 0) + 1

    campos = sorted(
        ({"campo": k, "veces": v, "porcentaje": round(100 * v / total, 1)} for k, v in veces.items()),
        key=lambda c: -c["veces"],
    )

    por_dispositivo = [
        {"dispositivo": d or "(sin indicar)", "total": n}
        for d, n in db.query(
            CuestionarioAsistencia.dispositivo, func.count(CuestionarioAsistencia.id)
        ).group_by(CuestionarioAsistencia.dispositivo).all()
    ]

    return {
        "total": total,
        "con_ticket": con_ticket,
        "confianza_media": confianza_media,
        "campos": campos,
        "por_dispositivo": sorted(por_dispositivo, key=lambda d: -d["total"]),
    }


def buscar_tickets_resueltos_similares(db, sintoma_norm: str, dispositivo: str = "", limite: int = 5) -> List[Dict[str, Any]]:
    """Busca tickets resueltos similares al síntoma dado usando FTS (feedback loop)."""
    try:
        palabras = [w.strip() for w in sintoma_norm.split() if len(w.strip()) > 2][:6]
        if not palabras:
            return []
        terminos = " | ".join(palabras)
        sql = text("""
            SELECT id, numero_ticket, dispositivo, sintoma, diagnostico, solucion, instalador, obra,
                   ts_rank(busqueda_tsv, to_tsquery('spanish', :q), 32) as relevancia
            FROM tickets_sat
            WHERE estado = 'resuelto'
              AND busqueda_tsv @@ to_tsquery('spanish', :q)
            ORDER BY relevancia DESC
            LIMIT :lim
        """)
        filas = db.execute(sql, {"q": terminos, "lim": limite}).fetchall()
        return [{
            "ticket_id": f.id,
            "numero_ticket": f.numero_ticket,
            "dispositivo": f.dispositivo,
            "sintoma": f.sintoma,
            "diagnostico": f.diagnostico,
            "solucion": f.solucion,
            "instalador": f.instalador,
            "obra": f.obra,
            "relevancia": float(f.relevancia)
        } for f in filas]
    except Exception as e:
        logger.error(f"Error buscando tickets similares: {e}")
        return []

