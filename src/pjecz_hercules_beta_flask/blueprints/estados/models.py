"""
Estados, modelos
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pjecz_hercules_beta_flask.config.extensions import database
from pjecz_hercules_beta_flask.lib.universal_mixin import UniversalMixin


class Estado(database.Model, UniversalMixin):
    """Estado"""

    # Nombre de la tabla
    __tablename__ = "estados"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Columnas
    clave: Mapped[str] = mapped_column(String(16), unique=True)
    nombre: Mapped[str] = mapped_column(String(256))

    # Hijos
    exh_externos: Mapped[list["ExhExterno"]] = relationship(back_populates="estado")
    municipios: Mapped[list["Municipio"]] = relationship(back_populates="estado")

    def __repr__(self):
        """Representación"""
        return f"<Estado {self.clave}>"
