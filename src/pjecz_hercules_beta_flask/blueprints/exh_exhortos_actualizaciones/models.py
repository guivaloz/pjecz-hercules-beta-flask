"""
Exhortos Actualizaciones, modelos
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.functions import now

from pjecz_hercules_beta_flask.config.extensions import database
from pjecz_hercules_beta_flask.lib.universal_mixin import UniversalMixin


class ExhExhortoActualizacion(database.Model, UniversalMixin):
    """ExhExhortoActualizacion"""

    ESTADOS = {
        "PENDIENTE": "Pendiente",
        "POR ENVIAR": "Por enviar",
        "ENVIADO": "Enviado",
        "RECHAZADO": "Rechazado",
        "CANCELADO": "Cancelado",
    }

    REMITENTES = {
        "INTERNO": "Interno",
        "EXTERNO": "Externo",
    }

    TIPOS_ACTUALIZACIONES = {
        "AreaTurnado": "Área de Turnado",
        "NumeroExhorto": "Número de Exhorto",
    }

    # Nombre de la tabla
    __tablename__ = "exh_exhortos_actualizaciones"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    exh_exhorto_id: Mapped[int] = mapped_column(ForeignKey("exh_exhortos.id"))
    exh_exhorto: Mapped["ExhExhorto"] = relationship(back_populates="exh_exhortos_actualizaciones")

    # Columnas
    # Identificador que el Poder Judicial exhortado (quien envía la actualización) genera.
    # Este puede ser un consecutivo (ej. "1", "2", ... "45545"), un GUID/UUID, código (ej. "EX-00001-2024update55" ...)
    # o cualquier dato que no se pueda repetir.
    actualizacion_origen_id: Mapped[str] = mapped_column(String(64))

    # Tipo de actualización del exhorto, que está relacionado con el dato o proceso de actualización que sufrió el exhorto.
    # Estos pueden ser:
    # - "AreaTurnado" => Cuando se cambia o se turna el Exhorto al Juzgado/Área que hará la diligenciación.
    # - "NumeroExhorto" => En el Juzgado/Área que va a hacer la diligenciación del exhorto, este ya se radicó y
    #    se le asignó un Número de Exhorto (local) con el que identifican.
    tipo_actualizacion: Mapped[str] = mapped_column(String(64))

    # Fecha hora local en que se registró la actualización
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, default=now())

    # Una descripción que indique cuál fue el dato y/o información del exhorto que se actualizó.
    # Este puede ser: "Turnado al Juzgado Tercero Familiar (Municipio)", "Radicado con Número de Exhorto 99999/2024"
    descripcion: Mapped[str] = mapped_column(String(256))

    #
    # Internos
    #

    # Si el remitente es INTERNO entonces fue creada por nosotros, si es EXTERNO fue creada por otro PJ
    remitente: Mapped[str] = mapped_column(
        Enum(*REMITENTES, name="exh_exhortos_actualizaciones_remitentes", native_enum=False), index=True
    )

    # Estado de la actualización y el estado anterior, para cuando se necesite revertir un cambio de estado
    estado: Mapped[str] = mapped_column(
        Enum(*ESTADOS, name="exh_exhortos_actualizaciones_estados", native_enum=False), index=True
    )
    estado_anterior: Mapped[Optional[str]]

    # Conservar el JSON que se genera cuando se hace el envío y el que se recibe con el acuse
    paquete_enviado: Mapped[Optional[dict]] = mapped_column(JSONB)
    acuse_recibido: Mapped[Optional[dict]] = mapped_column(JSONB)

    def __repr__(self):
        """Representación"""
        return f"<ExhExhortoActualizacion {self.id}>"
