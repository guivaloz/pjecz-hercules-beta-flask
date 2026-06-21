"""
Soportes Categorias, modelos
"""

from typing import List, Optional

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pjecz_hercules_beta_flask.config.extensions import database
from pjecz_hercules_beta_flask.lib.universal_mixin import UniversalMixin


class SoporteCategoria(database.Model, UniversalMixin):
    """SoporteCategoria"""

    DEPARTAMENTOS = {
        "TODOS": "Todos",
        "INFORMATICA": "Informatica",
        "INFRAESTRUCTURA": "Infraestructura",
    }

    # Nombre de la tabla
    __tablename__ = "soportes_categorias"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    rol_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    rol: Mapped["Rol"] = relationship(back_populates="soportes_categorias_roles")

    # Columnas
    nombre: Mapped[str] = mapped_column(String(256), unique=True)
    instrucciones: Mapped[str] = mapped_column(Text)
    departamento: Mapped[Optional[str]] = mapped_column(
        Enum(*DEPARTAMENTOS, name="soportes_categorias_departamentos", native_enum=False), index=True
    )

    # Hijos
    soportes_tickets: Mapped[List["SoporteTicket"]] = relationship(back_populates="soporte_categoria")

    def __repr__(self):
        """Representación"""
        return f"<SoporteCategoria {self.id}>"
