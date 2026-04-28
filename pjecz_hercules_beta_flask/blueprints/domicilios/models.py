"""
Domicilios, modelos
"""

from typing import List

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...config.extensions import database
from ...lib.universal_mixin import UniversalMixin


class Domicilio(database.Model, UniversalMixin):
    """Domicilio"""

    # Nombre de la tabla
    __tablename__ = "domicilios"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    distrito_id: Mapped[int] = mapped_column(ForeignKey("distritos.id"))
    distrito: Mapped["Distrito"] = relationship(back_populates="domicilios")

    # Columnas
    edificio: Mapped[str] = mapped_column(String(64), unique=True)
    estado: Mapped[str] = mapped_column(String(64))
    municipio: Mapped[str] = mapped_column(String(64))
    calle: Mapped[str] = mapped_column(String(256))
    num_ext: Mapped[str] = mapped_column(String(24))
    num_int: Mapped[str] = mapped_column(String(24))
    colonia: Mapped[str] = mapped_column(String(256))
    cp: Mapped[int]
    completo: Mapped[str] = mapped_column(String(1024))

    # Hijos
    # centros_trabajos: Mapped[List["CentroTrabajo"]] = relationship(back_populates="domicilio")
    oficinas: Mapped[List["Oficina"]] = relationship(back_populates="domicilio")

    def elaborar_completo(self):
        """Elaborar completo"""
        elementos = []
        if self.calle and self.num_ext and self.num_int:
            elementos.append(f"{self.calle} #{self.num_ext}-{self.num_int}")
        elif self.calle and self.num_ext:
            elementos.append(f"{self.calle} #{self.num_ext}")
        elif self.calle:
            elementos.append(self.calle)
        if self.colonia:
            elementos.append(self.colonia)
        if self.municipio:
            elementos.append(self.municipio)
        if self.estado and self.cp > 0:
            elementos.append(f"{self.estado}, C.P. {self.cp}")
        elif self.estado:
            elementos.append(self.estado)
        return ", ".join(elementos)

    def __repr__(self):
        """Representación"""
        return f"<Domicilio {self.edificio}>"
