import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Lê DATABASE_URL da variável de ambiente, ou usa o SQLite local padrão
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///qa_metrics.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency do FastAPI que entrega uma sessão do banco por requisição e a fecha no final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()