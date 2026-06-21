"""
REDAMS, modelos
"""

from datetime import date

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pjecz_hercules_beta_flask.config.extensions import database
from pjecz_hercules_beta_flask.lib.universal_mixin import UniversalMixin


class Redam(database.Model, UniversalMixin):
    """Redam"""

    # Nombre de la tabla
    __tablename__ = "redam"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Claves foráneas
    autoridad_id: Mapped[int] = mapped_column(ForeignKey("autoridades.id"))
    autoridad: Mapped["Autoridad"] = relationship(back_populates="redam")

    # Columnas
    nombre: Mapped[str] = mapped_column(String(256))
    expediente: Mapped[str] = mapped_column(String(256))
    fecha: Mapped[date]
    observaciones: Mapped[str] = mapped_column(String(1024))

    def __repr__(self):
        """Representación"""
        return f"<Redam {self.id}>"
