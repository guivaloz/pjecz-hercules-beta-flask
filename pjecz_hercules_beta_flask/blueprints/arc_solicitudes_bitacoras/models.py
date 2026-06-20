"""
Archivos Solicitudes Bitacoras
"""

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pjecz_hercules_beta_flask.config.extensions import database
from pjecz_hercules_beta_flask.lib.universal_mixin import UniversalMixin


class ArcSolicitudBitacora(database.Model, UniversalMixin):
    """ArcSolicitudBitacora"""

    ACCIONES = {
        "SOLICITADA": "Solicitada",
        "CANCELADA": "Cancelada",
        "ASIGNADA": "Asignada",
        "ENCONTRADA": "Encontrada",
        "NO ENCONTRADA": "No Encontrada",
        "ENVIADA": "Enviada",
        "ENTREGADA": "Entregada",
        "PASADA AL HISTORIAL": "Pasa al historial",
        "ELIMINADA": "Eliminada",
        "RECUPERADA": "Recuperada",
    }

    # Nombre de la tabla
    __tablename__ = "arc_solicitudes_bitacoras"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    arc_solicitud_id: Mapped[int] = mapped_column(ForeignKey("arc_solicitudes.id"))
    arc_solicitud: Mapped["ArcSolicitud"] = relationship(back_populates="arc_solicitudes_bitacoras")
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    usuario: Mapped["Usuario"] = relationship(back_populates="arc_solicitudes_bitacoras")

    # Columnas
    accion: Mapped[str] = mapped_column(
        Enum(*ACCIONES, name="arc_solicitudes_bitacoras_acciones", native_enum=False), index=True
    )
    observaciones: Mapped[str] = mapped_column(String(256))

    def __repr__(self):
        """Representación"""
        return f"<ArcSolicitudBitacora {self.id}>"
