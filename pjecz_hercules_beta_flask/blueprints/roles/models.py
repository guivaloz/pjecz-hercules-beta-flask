"""
Roles
"""

from typing import List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...config.extensions import database
from ...lib.universal_mixin import UniversalMixin


class Rol(database.Model, UniversalMixin):
    """Rol"""

    # Nombre de la tabla
    __tablename__ = "roles"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Columnas
    nombre: Mapped[str] = mapped_column(String(256), unique=True)

    # Hijos
    permisos: Mapped[List["Permiso"]] = relationship(back_populates="rol")
    usuarios_roles: Mapped[List["UsuarioRol"]] = relationship(back_populates="rol")
    # soportes_categorias_roles: Mapped[List["SoporteCategoria"]] = relationship(back_populates="rol")

    def __repr__(self):
        """Representación"""
        return f"<Rol {self.nombre}>"
