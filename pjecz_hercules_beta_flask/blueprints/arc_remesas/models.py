"""
Archivos Remesas
"""

from datetime import datetime
from typing import List

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pjecz_hercules_beta_flask.config.extensions import database
from pjecz_hercules_beta_flask.lib.universal_mixin import UniversalMixin


class ArcRemesa(database.Model, UniversalMixin):
    """ArcRemesa"""

    ESTADOS = {
        "PENDIENTE": "Pendiente",  # El SOLICITANTE comienza una solicitud de Remesa
        "CANCELADO": "Cancelado",  # El SOLICITANTE se arrepiente de crear una Remesa
        "ENVIADO": "Enviado",  # El SOLICITANTE pide que recojan la remesa. El JEFE_REMESA ve el pedido
        "RECHAZADO": "Rechazado",  # El JEFE_REMESA rechaza la remesa
        "ASIGNADO": "Asignado",  # El JEFE_REMESA acepta la remesa y la asigna a un ARCHIVISTA
        "ARCHIVADO": "Archivado",  # El ARCHIVISTA termina de procesar la remesa
        "ARCHIVADO CON ANOMALIA": "Archivado con Anomalía",  # El ARCHIVISTA termina de procesar la remesa pero almenos un documento presentó anomalía
    }

    RAZONES = {
        "SIN ORDEN CRONOLÓGICO": "Sin orden cronológico.",
    }

    ANOMALIAS = {
        "DOCUMENTOS DESORDENADOS": "Expediente desordenados",
        "EXPEDIENTE FISICO NO AGREGADO": "Expediente físico no agregado a la remesa",
    }

    # Nombre de la tabla
    __tablename__ = "arc_remesas"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    autoridad_id: Mapped[int] = mapped_column(ForeignKey("autoridades.id"))
    autoridad: Mapped["Autoridad"] = relationship(back_populates="arc_remesas")
    usuario_asignado_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    usuario_asignado: Mapped["Usuario"] = relationship(back_populates="arc_remesas")
    arc_documento_tipo_id: Mapped[int] = mapped_column(ForeignKey("arc_documentos_tipos.id"))
    arc_documento_tipo: Mapped["ArcDocumentoTipo"] = relationship(back_populates="arc_remesas")

    # Columnas
    anio: Mapped[str] = mapped_column(String(16))
    esta_archivado: Mapped[bool] = mapped_column(default=False)
    num_oficio: Mapped[str] = mapped_column(String(16))
    # rechazo: Mapped[str] = mapped_column(String(256))
    observaciones_solicitante: Mapped[str] = mapped_column(String(256))
    observaciones_archivista: Mapped[str] = mapped_column(String(2048))
    anomalia_general: Mapped[str] = mapped_column(Enum(*ANOMALIAS, name="arc_remesas_anomalias", native_enum=False), index=True)
    tiempo_enviado: Mapped[datetime]
    num_documentos: Mapped[int]
    num_anomalias: Mapped[int]
    # razon: Mapped[str] = mapped_column(Enum(*RAZONES, name="arc_remesas_razones", native_enum=False), index=True)
    estado: Mapped[str] = mapped_column(Enum(*ESTADOS, name="arc_remesas_estados", native_enum=False), index=True)

    # Hijos
    arc_remesas_documentos: Mapped[List["ArcRemesaDocumento"]] = relationship(back_populates="arc_remesa")
    arc_remesas_bitacoras: Mapped[List["ArcRemesaBitacora"]] = relationship(back_populates="arc_remesa")

    def __repr__(self):
        """Representación"""
        return f"<ArcRemesa {self.id}>"
