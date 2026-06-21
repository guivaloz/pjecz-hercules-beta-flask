"""
Exhortos Tipos Diligencias, modelos
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.functions import now

from pjecz_hercules_beta_flask.config.extensions import database
from pjecz_hercules_beta_flask.lib.universal_mixin import UniversalMixin


class ExhTipoDiligencia(database.Model, UniversalMixin):
    """ExhTipoDiligencia"""

    # Nombre de la tabla
    __tablename__ = "exh_tipos_diligencias"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Columnas
    clave: Mapped[str] = mapped_column(String(16), unique=True)
    descripcion: Mapped[str] = mapped_column(String(256))

    # Hijo
    exh_exhortos: Mapped[List["ExhExhorto"]] = relationship(back_populates="exh_tipo_diligencia")

    def __repr__(self):
        """Representación"""
        return f"<ExhTipoDiligencia {self.clave}>"
