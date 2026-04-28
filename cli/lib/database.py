"""
Database utilities
"""

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from pjecz_hercules_beta_flask.config.settings import get_settings


@lru_cache()
def get_database() -> Session:
    """Obtener la sesion de la base de datos"""
    settings = get_settings()
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return session_local()
