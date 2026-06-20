"""
Exhortos Tipos Diligencias
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.functions import now

from pjecz_hercules_beta_flask.config.extensions import database
from pjecz_hercules_beta_flask.lib.universal_mixin import UniversalMixin


class ExhExhortoPromocion(database.Model, UniversalMixin):
    """ExhExhortoPromocion"""

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

    # Nombre de la tabla
    __tablename__ = "exh_exhortos_promociones"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    exh_exhorto_id: Mapped[int] = mapped_column(ForeignKey("exh_exhortos.id"))
    exh_exhorto: Mapped["ExhExhorto"] = relationship(back_populates="exh_exhortos_promociones")

    # Identificador del origen de la promoción;
    # Puede ser el folio del oficio u otro documento desde donde partió la promoción
    folio_origen_promocion: Mapped[str] = mapped_column(String(64))

    # Número de fojas que contiene la promoción.
    # El valor 0 significa "No Especificado".
    fojas: Mapped[int]

    # Fecha y hora en que el Poder Judicial promovente registró que se envió la promoción en su hora local.
    # En caso de no enviar este dato, el Poder Judicial promovido puede tomar su fecha hora local.
    fecha_origen: Mapped[Optional[datetime]] = mapped_column(DateTime, default=now())

    # Texto simple que contenga información extra o relevante sobre el exhorto.
    observaciones: Mapped[Optional[str]] = mapped_column(String(1024))

    # Folio de la promoción recibida, se va a generar cuando se entreguen todos los archivos
    folio_promocion_recibida: Mapped[Optional[str]] = mapped_column(String(64))

    #
    # Internos
    #

    # Si el remitente es INTERNO entonces fue creada por nosotros, si es EXTERNO fue creada por otro PJ
    remitente: Mapped[str] = mapped_column(
        Enum(*REMITENTES, name="exh_exhortos_promociones_remitentes", native_enum=False), index=True
    )

    # Estado de la promoción y el estado anterior, para cuando se necesite revertir un cambio de estado
    estado: Mapped[str] = mapped_column(Enum(*ESTADOS, name="exh_exhortos_promociones_estados", native_enum=False), index=True)
    estado_anterior: Mapped[Optional[str]]

    # Conservar el JSON que se genera cuando se hace el envío y el que se recibe con el acuse
    paquete_enviado: Mapped[Optional[dict]] = mapped_column(JSONB)
    acuse_recibido: Mapped[Optional[dict]] = mapped_column(JSONB)

    #
    # Hijos
    #

    # Hijo: archivos
    # Colección de los datos referentes a los archivos que se van a recibir el Poder Judicial exhortado en el envío del Exhorto.
    exh_exhortos_promociones_archivos: Mapped[List["ExhExhortoPromocionArchivo"]] = relationship(
        back_populates="exh_exhorto_promocion"
    )

    # Hijo: promoventes
    # Contiene la definición de los promoventes, en este caso el juzgado quien realiza la promoción
    exh_exhortos_promociones_promoventes: Mapped[List["ExhExhortoPromocionPromovente"]] = relationship(
        back_populates="exh_exhorto_promocion"
    )

    def __repr__(self):
        """Representación"""
        return f"<ExhExhortoPromocion {self.id}>"
