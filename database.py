from sqlalchemy import create_engine, Column, Integer, String, Float, Text, ForeignKey, LargeBinary
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DATABASE_URL = "sqlite:///./motor_cv.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Vacante(Base):
    __tablename__ = "vacantes"
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, index=True)
    descripcion = Column(Text)
    evaluaciones = relationship("Evaluacion", back_populates="vacante")

class Candidato(Base):
    __tablename__ = "candidatos"
    id = Column(Integer, primary_key=True, index=True)
    nombre_archivo = Column(String)
    email = Column(String)
    telefono = Column(String)
    texto_completo = Column(Text)
    skills_detectadas = Column(Text)
    pdf_bytes = Column(LargeBinary, nullable=True)
    evaluaciones = relationship("Evaluacion", back_populates="candidato")

class Evaluacion(Base):
    __tablename__ = "evaluaciones"
    id = Column(Integer, primary_key=True, index=True)
    vacante_id = Column(Integer, ForeignKey("vacantes.id"))
    candidato_id = Column(Integer, ForeignKey("candidatos.id"))
    score_similitud = Column(Float)
    resumen_ejecutivo = Column(Text)
    justificacion_fit = Column(Text)

    vacante = relationship("Vacante", back_populates="evaluaciones")
    candidato = relationship("Candidato", back_populates="evaluaciones")

Base.metadata.create_all(bind=engine)