import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, ForeignKey, LargeBinary
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# Cargar las variables del archivo .env
load_dotenv()

# Conexión remota a Supabase o respaldo local
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./motor_cv.db")

# LÍNEA DEFENSIVA: Si por error quedó el parámetro pgbouncer, lo removemos para evitar el fallo de psycopg2
if DATABASE_URL and "?pgbouncer=true" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("?pgbouncer=true", "")
elif DATABASE_URL and "&pgbouncer=true" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("&pgbouncer=true", "")

if "sqlite" in DATABASE_URL:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Vacante(Base):
    __tablename__ = "vacantes"
    
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, index=True)
    descripcion = Column(Text)
    
    evaluaciones = relationship("Evaluacion", back_populates="vacante", cascade="all, delete-orphan")


class Candidato(Base):
    __tablename__ = "candidatos"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre_archivo = Column(String)
    
    # Datos completos extraídos por la IA
    nombre = Column(String, default="No especificado")
    edad = Column(String, default="No especificada")
    sexo = Column(String, default="No especificado")
    email = Column(String, default="No especificado")
    telefono = Column(String, default="No especificado")
    perfil_destacado = Column(String, default="General")  # Categoría / Puesto sugerido
    desempeno = Column(String, default="Alto Potencial")    # Desempeño / Nivel evaluado
    experiencia = Column(Text, default="")
    skills = Column(Text, default="")
    puntos_fuertes = Column(Text, default="")
    texto_completo = Column(Text, default="")
    archivo_bytes = Column(LargeBinary, nullable=True)
    
    evaluaciones = relationship("Evaluacion", back_populates="candidato", cascade="all, delete-orphan")
    entrevista = relationship("Entrevista", back_populates="candidato", uselist=False, cascade="all, delete-orphan")


class Evaluacion(Base):
    __tablename__ = "evaluaciones"
    
    id = Column(Integer, primary_key=True, index=True)
    vacante_id = Column(Integer, ForeignKey("vacantes.id"))
    candidato_id = Column(Integer, ForeignKey("candidatos.id"))
    score_similitud = Column(Float, default=0.0)
    resumen_ejecutivo = Column(Text, default="")
    justificacion_fit = Column(Text, default="")

    vacante = relationship("Vacante", back_populates="evaluaciones")
    candidato = relationship("Candidato", back_populates="evaluaciones")


class Entrevista(Base):
    __tablename__ = "entrevistas"
    
    id = Column(Integer, primary_key=True, index=True)
    candidato_id = Column(Integer, ForeignKey("candidatos.id"), unique=True)
    nombre = Column(String)
    puesto = Column(String)
    fecha = Column(String)
    hora = Column(String)
    lugar = Column(String, default="Google Meet")
    estado = Column(String, default="🗓️ Programada")
    tipo_finalista = Column(String, default="En capacitación")

    candidato = relationship("Candidato", back_populates="entrevista")


Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()