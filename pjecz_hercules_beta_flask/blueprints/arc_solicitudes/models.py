"""
Archivos Solicitudes
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pjecz_hercules_beta_flask.config.extensions import database
from pjecz_hercules_beta_flask.lib.universal_mixin import UniversalMixin


class ArcSolicitud(database.Model, UniversalMixin):
    """ArcSolicitud"""

    ESTADOS = {
        "SOLICITADO": "Solicitado",
        "CANCELADO": "Cancelado",
        "ASIGNADO": "Asignado",
        "ENCONTRADO": "Encontrado",
        "NO ENCONTRADO": "No Encontrado",
        "ENVIANDO": "Enviando",
        "ENTREGADO": "Entregado",
    }

    RAZONES = {
        "FALTA DE ORIGEN": "Falta de Origen",
        "NO COINCIDEN LAS PARTES": "No coinciden las partes",
        "PRESTADO": "Prestado",
    }

    # Nombre de la tabla
    __tablename__ = "arc_solicitudes"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    arc_documento_id: Mapped[int] = mapped_column(ForeignKey("arc_documentos.id"))
    arc_documento: Mapped["ArcDocumento"] = relationship(back_populates="arc_solicitudes")
    autoridad_id: Mapped[int] = mapped_column(ForeignKey("autoridades.id"))
    autoridad: Mapped["Autoridad"] = relationship(back_populates="arc_solicitudes")
    usuario_asignado_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    usuario_asignado: Mapped["Usuario"] = relationship(back_populates="arc_solicitudes_asignado")

    # Columnas
    usuario_receptor_id: Mapped[int]
    esta_archivado: Mapped[bool] = mapped_column(default=False)
    num_folio: Mapped[str] = mapped_column(String(16))
    tiempo_recepcion: Mapped[datetime]
    fojas: Mapped[int]
    estado: Mapped[str] = mapped_column(Enum(*ESTADOS, name="arc_solicitudes_estados", native_enum=False), index=True)
    razon: Mapped[str] = mapped_column(Enum(*RAZONES, name="arc_solicitudes_razones", native_enum=False), index=True)
    observaciones_solicitud: Mapped[Optional[str]] = mapped_column(String(256))
    observaciones_razon: Mapped[Optional[str]] = mapped_column(String(256))

    # Hijos
    arc_solicitudes_bitacoras: Mapped[List["ArcSolicitudBitacora"]] = relationship(back_populates="arc_solicitud")

    def __repr__(self):
        """Representación"""
        return f"<ArcSolicitud {self.id}>"
