"""
Soportes Tickets
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pjecz_hercules_beta_flask.config.extensions import database
from pjecz_hercules_beta_flask.lib.universal_mixin import UniversalMixin


class SoporteTicket(database.Model, UniversalMixin):
    """SoporteTicket"""

    ESTADOS = {
        "SIN ATENDER": "Abierto o pendiente",
        "TRABAJANDO": "Trabajando",
        "TERMINADO": "Trabajo concluido, resultado satisfactorio",
        "CERRADO": "Trabajo concluido, resultado indiferente",
        "PENDIENTE": "Pendiente de resolver",
        "CANCELADO": "Cancelado",
    }

    CLASIFICACIONES = {
        "INFRAESTRUCTURA": "INFRAESTRUCTURA",
        "PAIIJ": "PAIIJ",
        "SIGE": "SIGE",
        "SAJI HIPOTECARIO": "SAJI HIPOTECARIO",
        "SAJI LABORAL": "SAJI LABORAL",
        "SICCED": "SICCED",
        "SOPORTE TECNICO": "SOPORTE TÉCNICO",
        "OTRO": "OTRO",
    }

    DEPARTAMENTOS = {
        "INFORMATICA": "INFORMATICA",
        "INFRAESTRUCTURA": "INFRAESTRUCTURA",
    }

    # Nombre de la tabla
    __tablename__ = "soportes_tickets"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Claves foráneas
    funcionario_id: Mapped[int] = mapped_column(ForeignKey("funcionarios.id"))
    funcionario: Mapped["Funcionario"] = relationship(back_populates="soportes_tickets")
    soporte_categoria_id: Mapped[int] = mapped_column(ForeignKey("soportes_categorias.id"))
    soporte_categoria: Mapped["SoporteCategoria"] = relationship(back_populates="soportes_tickets")
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    usuario: Mapped["Usuario"] = relationship(back_populates="soportes_tickets")

    # Columnas
    descripcion: Mapped[str] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(Enum(*ESTADOS, name="soportes_tickets_estados", native_enum=False), index=True)
    resolucion: Mapped[Optional[datetime]]
    soluciones: Mapped[Optional[str]] = mapped_column(Text)
    departamento: Mapped[str] = mapped_column(
        Enum(*DEPARTAMENTOS, name="soportes_tickets_departamentos", native_enum=False), index=True
    )

    # Hijos
    soportes_adjuntos: Mapped[List["SoporteAdjunto"]] = relationship(back_populates="soporte_ticket")

    def __repr__(self):
        """Representación"""
        return f"<SoporteTicket {self.id}>"
