import os
import logging
import secrets
from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import bcrypt
from .sinonimos import expandir_query

logger = logging.getLogger("buscador_manuales")

# Roles válidos del sistema — cualquier rol fuera de esta lista se rechaza
ROLES_VALIDOS = {"admin", "tecnico", "comercial"}

# URL por defecto si no se inyecta desde Docker
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:password@localhost:5432/buscador_manuales"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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
    
    fragmentos = relationship("VideoFragmento", back_populates="video", cascade="all, delete-orphan")

class VideoFragmento(Base):
    __tablename__ = "video_fragmentos"
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    segundo_inicio = Column(Integer, nullable=False, default=0) # en segundos
    duracion = Column(Integer, default=0)
    texto = Column(Text, nullable=False)
    
    video = relationship("Video", back_populates="fragmentos")

class TicketSAT(Base):
    __tablename__ = "tickets_sat"
    id = Column(Integer, primary_key=True, index=True)
    numero_ticket = Column(String, unique=True, index=True, nullable=False) # e.g. "SAT-2026-0001"
    instalador = Column(String, nullable=False, index=True)
    telefono = Column(String, default="")
    obra = Column(String, default="")
    distribuidor = Column(String, default="") # e.g. Solven, Procomsa, Kömmerling, VBH
    dispositivo = Column(String, default="") # Connect-1, C-Wall, C-Pulsar, etc.
    motor = Column(String, default="") # Somfy 4 hilos, Cherubini, etc.
    sintoma = Column(Text, nullable=False)
    diagnostico = Column(Text, default="")
    solucion = Column(Text, default="")
    estado = Column(String, default="en_espera", index=True) # en_espera, resuelto, rma_pendiente, descartado
    prioridad = Column(String, default="normal") # normal, urgente
    creado_por = Column(String, default="") # email del usuario técnico/admin
    notas = Column(Text, default="")
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_actualizacion = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ---------------------------------------------------------------------
# Funciones principales
# ---------------------------------------------------------------------

def init_db() -> None:
    """Crea las tablas, inicializa pgvector y crea usuario admin por defecto."""
    try:
        # Habilitar pgvector, unaccent y configuración de búsqueda insensible a acentos en postgres
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent"))
            conn.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_ts_config WHERE cfgname = 'spanish_unaccent') THEN
                        CREATE TEXT SEARCH CONFIGURATION spanish_unaccent (COPY = spanish);
                        ALTER TEXT SEARCH CONFIGURATION spanish_unaccent
                            ALTER MAPPING FOR hword, hword_part, word
                            WITH unaccent, spanish_stem;
                    END IF;
                END
                $$;
            """))
            conn.execute(text("ALTER TABLE manuales ADD COLUMN IF NOT EXISTS etiquetas TEXT DEFAULT '';"))
            conn.commit()
            
        Base.metadata.create_all(bind=engine)

        # Migración de rendimiento: columnas generadas tsvector e índices GIN
        with engine.connect() as conn:
            conn.execute(text("""
                DO $$
                BEGIN
                    -- Columna generada y GIN para paginas (texto_tsv)
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'paginas' AND column_name = 'texto_tsv'
                    ) THEN
                        ALTER TABLE paginas ADD COLUMN texto_tsv tsvector
                            GENERATED ALWAYS AS (to_tsvector('spanish', texto)) STORED;
                    END IF;
                    
                    -- Columna generada y GIN para manuales (metadatos_tsv)
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'manuales' AND column_name = 'metadatos_tsv'
                    ) THEN
                        ALTER TABLE manuales ADD COLUMN metadatos_tsv tsvector
                            GENERATED ALWAYS AS (
                                to_tsvector('spanish', nombre_original || ' ' || COALESCE(dispositivo,'') || ' ' || COALESCE(categoria,'') || ' ' || COALESCE(etiquetas,''))
                            ) STORED;
                    END IF;
                END
                $$;
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_paginas_tsv ON paginas USING GIN (texto_tsv);"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_manuales_tsv ON manuales USING GIN (metadatos_tsv);"))
            conn.commit()
        
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
        logger.error(f"Error inicializando base de datos: {e}")

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

def obtener_video(video_db_id: int):
    db = SessionLocal()
    try:
        v = db.query(Video).filter(Video.id == video_db_id).first()
        if v:
            return {
                "id": v.id,
                "video_id": v.video_id,
                "titulo": v.titulo,
                "canal": v.canal,
                "url": v.url,
                "miniatura_url": v.miniatura_url,
                "dispositivo": v.dispositivo,
                "categoria": v.categoria,
                "etiquetas": v.etiquetas or "",
                "nivel_acceso": v.nivel_acceso
            }
        return None
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

def buscar_videos(query: str, dispositivo: str = "", categoria: str = "", limite: int = 15, role: str = "admin"):
    """
    Busca en videos de YouTube y sus fragmentos transcritos usando PostgreSQL FTS.
    """
    db = SessionLocal()
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
            SELECT 
                v.id AS video_db_id, v.video_id, v.titulo, v.canal, v.url, v.miniatura_url,
                v.dispositivo, v.categoria, v.etiquetas, v.nivel_acceso, v.fecha_subida,
                COALESCE(vf.segundo_inicio, 0) as segundo_inicio,
                ts_headline('spanish', COALESCE(vf.texto, v.titulo), websearch_to_tsquery('spanish', :query), 'StartSel=<mark>, StopSel=</mark>, MaxWords=30, MinWords=15') as fragmento,
                ts_rank(
                    setweight(to_tsvector('spanish', v.titulo || ' ' || COALESCE(v.dispositivo, '') || ' ' || COALESCE(v.categoria, '') || ' ' || COALESCE(v.etiquetas, '')), 'A') || 
                    setweight(to_tsvector('spanish', COALESCE(vf.texto, v.transcripcion_texto, '')), 'C'),
                    websearch_to_tsquery('spanish', :query)
                ) as relevancia
            FROM videos v
            LEFT JOIN video_fragmentos vf ON vf.video_id = v.id
            WHERE {where_sql} AND (
                setweight(to_tsvector('spanish', v.titulo || ' ' || COALESCE(v.dispositivo, '') || ' ' || COALESCE(v.categoria, '') || ' ' || COALESCE(v.etiquetas, '')), 'A') || 
                setweight(to_tsvector('spanish', COALESCE(vf.texto, v.transcripcion_texto, '')), 'C')
            ) @@ websearch_to_tsquery('spanish', :query)
            ORDER BY relevancia DESC
        """
        query_expandida = expandir_query(query)
        params = {"query": query_expandida, "dispositivo": dispositivo, "categoria": categoria}
        filas = db.execute(text(sql), params).fetchall()
        
        mejor_por_video = {}
        for fila in filas:
            vid = fila.video_db_id
            if vid not in mejor_por_video:
                mejor_por_video[vid] = fila
                
        resultados = []
        for vid, fila in mejor_por_video.items():
            segundos = int(fila.segundo_inicio or 0)
            mins = segundos // 60
            secs = segundos % 60
            tiempo_formateado = f"{mins:02d}:{secs:02d}"
            url_con_tiempo = f"https://www.youtube.com/watch?v={fila.video_id}&t={segundos}s"
            
            resultados.append({
                "tipo": "video",
                "id": vid,
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
            SELECT 
                m.id AS manual_id, m.nombre_original, m.nombre_archivo, 
                m.dispositivo, m.categoria, m.etiquetas, m.num_paginas, m.fecha_subida, m.nivel_acceso,
                p.numero_pagina, 
                ts_headline('spanish', p.texto, websearch_to_tsquery('spanish', :query), 'StartSel=<mark>, StopSel=</mark>, MaxWords=30, MinWords=15') as fragmento,
                ts_rank(
                    setweight(m.metadatos_tsv, 'A') || 
                    setweight(p.texto_tsv, 'C'),
                    websearch_to_tsquery('spanish', :query)
                ) as relevancia
            FROM paginas p
            JOIN manuales m ON m.id = p.manual_id
            WHERE {where_sql} AND (
                setweight(m.metadatos_tsv, 'A') || 
                setweight(p.texto_tsv, 'C')
            ) @@ websearch_to_tsquery('spanish', :query)
            ORDER BY relevancia DESC
        """
        
        query_expandida = expandir_query(query)
        params = {"query": query_expandida, "dispositivo": dispositivo, "categoria": categoria}
        filas = db.execute(text(sql), params).fetchall()

        mejor_por_manual = {}
        conteo_paginas = {}
        
        for fila in filas:
            mid = fila.manual_id
            conteo_paginas[mid] = conteo_paginas.get(mid, 0) + 1
            if mid not in mejor_por_manual:
                mejor_por_manual[mid] = fila

        resultados_manuales = []
        for mid, fila in mejor_por_manual.items():
            resultados_manuales.append({
                "tipo": "manual",
                "id": mid,
                "manual_id": mid,
                "nombre": fila.nombre_original,
                "nombre_original": fila.nombre_original,
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
                "paginas_coincidentes": conteo_paginas[mid],
                "nivel_acceso": fila.nivel_acceso
            })

        resultados_videos = buscar_videos(query_expandida, dispositivo=dispositivo, categoria=categoria, limite=limite, role=role)

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

def obtener_usuario(user_id: int):
    db = SessionLocal()
    try:
        return db.query(User).filter(User.id == user_id).first()
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

def generar_numero_ticket(db) -> str:
    """Genera un identificador correlativo único para tickets SAT, e.g. SAT-2026-0001."""
    import datetime
    anio = datetime.datetime.now().year
    prefijo = f"SAT-{anio}-"
    ultimo = (
        db.query(TicketSAT)
        .filter(TicketSAT.numero_ticket.like(f"{prefijo}%"))
        .order_by(TicketSAT.id.desc())
        .first()
    )
    if ultimo and ultimo.numero_ticket:
        try:
            secuencia = int(ultimo.numero_ticket.split("-")[-1]) + 1
        except Exception:
            secuencia = 1
    else:
        secuencia = 1
    return f"{prefijo}{secuencia:04d}"

def crear_ticket_sat(db, ticket_data: dict, creado_por: str = "") -> TicketSAT:
    numero = generar_numero_ticket(db)
    nuevo_ticket = TicketSAT(
        numero_ticket=numero,
        instalador=ticket_data.get("instalador", "").strip(),
        telefono=ticket_data.get("telefono", "").strip(),
        obra=ticket_data.get("obra", "").strip(),
        distribuidor=ticket_data.get("distribuidor", "").strip(),
        dispositivo=ticket_data.get("dispositivo", "").strip(),
        motor=ticket_data.get("motor", "").strip(),
        sintoma=ticket_data.get("sintoma", "").strip(),
        diagnostico=ticket_data.get("diagnostico", "").strip(),
        solucion=ticket_data.get("solucion", "").strip(),
        estado=ticket_data.get("estado", "en_espera"),
        prioridad=ticket_data.get("prioridad", "normal"),
        creado_por=creado_por,
        notas=ticket_data.get("notas", "").strip()
    )
    db.add(nuevo_ticket)
    db.commit()
    db.refresh(nuevo_ticket)
    return nuevo_ticket

def obtener_tickets_sat(db, q: Optional[str] = None, estado: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[TicketSAT]:
    query = db.query(TicketSAT)
    if estado and estado != "todos":
        query = query.filter(TicketSAT.estado == estado)
    if q and q.strip():
        termino = f"%{q.strip()}%"
        query = query.filter(
            (TicketSAT.numero_ticket.ilike(termino)) |
            (TicketSAT.instalador.ilike(termino)) |
            (TicketSAT.telefono.ilike(termino)) |
            (TicketSAT.obra.ilike(termino)) |
            (TicketSAT.dispositivo.ilike(termino)) |
            (TicketSAT.distribuidor.ilike(termino)) |
            (TicketSAT.sintoma.ilike(termino)) |
            (TicketSAT.diagnostico.ilike(termino))
        )
    return query.order_by(TicketSAT.id.desc()).offset(offset).limit(limit).all()

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
    total = db.query(TicketSAT).count()
    en_espera = db.query(TicketSAT).filter(TicketSAT.estado == "en_espera").count()
    resuelto = db.query(TicketSAT).filter(TicketSAT.estado == "resuelto").count()
    rma_pendiente = db.query(TicketSAT).filter(TicketSAT.estado == "rma_pendiente").count()
    return {
        "total": total,
        "en_espera": en_espera,
        "resuelto": resuelto,
        "rma_pendiente": rma_pendiente
    }

