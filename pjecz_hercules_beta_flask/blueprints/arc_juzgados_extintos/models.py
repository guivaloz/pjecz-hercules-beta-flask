"""
Archivos Juzgados Extintos, modelos
"""

from typing import List

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pjecz_hercules_beta_flask.config.extensions import database
from pjecz_hercules_beta_flask.lib.universal_mixin import UniversalMixin


class ArcJuzgadoExtinto(database.Model, UniversalMixin):
    """ArcJuzgadoExtinto"""

    # Nombre de la tabla
    __tablename__ = "arc_juzgados_extintos"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    distrito_id: Mapped[int] = mapped_column(ForeignKey("distritos.id"))
    distrito: Mapped["Distrito"] = relationship(back_populates="arc_juzgados_extintos")

    # Columnas
    clave: Mapped[str] = mapped_column(String(16), unique=True)
    descripcion_corta: Mapped[str] = mapped_column(String(64))
    descripcion: Mapped[str] = mapped_column(String(256))

    # Hijos
    arc_documentos: Mapped[List["ArcDocumento"]] = relationship(back_populates="arc_juzgado_origen")

    @property
    def nombre(self):
        """Junta clave : descripcion_corta"""
        return self.clave + " : " + self.descripcion_corta

    def __repr__(self):
        """Representación"""
        return f"<ArcJuzgadoExtinto {self.id}>"
