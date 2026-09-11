import os
import logging
import secrets
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey, inspect, text
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

    # Preparado para el futuro RAG con IA (silo empírico de casos resueltos)
    embedding = Column(Vector(1536))

    comentarios = relationship("TicketComentario", back_populates="ticket", cascade="all, delete-orphan", order_by="TicketComentario.fecha.asc()")
    grupo = relationship("IncidentGroup", foreign_keys=[grupo_id])
    grupos_secundarios = relationship("IncidentGroup", secondary="ticket_grupos_secundarios", viewonly=True)

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
    etiquetas: str = ""
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
            nivel_acceso=nivel_acceso
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

def obtener_manual_por_archivo(nombre_archivo: str):
    """Busca un manual por su nombre de archivo para verificación RBAC."""
    db = SessionLocal()
    try:
        m = db.query(Manual).filter(Manual.nombre_archivo == nombre_archivo).first()
        if m:
            return {
                "id": m.id,
                "nombre_original": m.nombre_original,
                "nombre_archivo": m.nombre_archivo,
                "dispositivo": m.dispositivo,
                "nivel_acceso": m.nivel_acceso
            }
        return None
    finally:
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
    fragmentos: list = None
) -> int:
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
            video_existente.transcripcion_texto = transcripcion_texto
            
            db.query(VideoFragmento).filter(VideoFragmento.video_id == video_existente.id).delete()
            if fragmentos:
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
                    ) as relevancia
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
                ORDER BY video_db_id, relevancia DESC
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
    fila = db.execute(
        text("""
            INSERT INTO ticket_contadores (anio, ultimo) VALUES (:anio, 1)
            ON CONFLICT (anio) DO UPDATE SET ultimo = ticket_contadores.ultimo + 1
            RETURNING ultimo
        """),
        {"anio": anio}
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
    for campo, valor in datos_actualizacion.items():
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
        "por_grupo": contar_tickets_por_grupo(db)
    }


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

