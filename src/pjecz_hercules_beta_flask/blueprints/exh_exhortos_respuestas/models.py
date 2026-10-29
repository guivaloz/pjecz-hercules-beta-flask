"""
Exh Exhortos Respuestas, modelos
"""

from typing import Optional

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pjecz_hercules_beta_flask.config.extensions import database
from pjecz_hercules_beta_flask.lib.universal_mixin import UniversalMixin


class ExhExhortoRespuesta(database.Model, UniversalMixin):
    """ExhExhortoRespuesta"""

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

    TIPOS_DILIGENCIADOS = {
        0: "No Diligenciado",
        1: "Parcialmente Diligenciado",
        2: "Diligenciado",
    }

    # Nombre de la tabla
    __tablename__ = "exh_exhortos_respuestas"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    exh_exhorto_id: Mapped[int] = mapped_column(ForeignKey("exh_exhortos.id"))
    exh_exhorto: Mapped["ExhExhorto"] = relationship(back_populates="exh_exhortos_respuestas")

    # Identificador propio del Poder Judicial exhortado con el que identifica la respuesta del exhorto.
    # Este dato puede ser un número consecutivo (ej "1", "2", "3"...),
    # un GUID/UUID o cualquíer otro valor con que se identifique la respuesta
    respuesta_origen_id: Mapped[str] = mapped_column(String(64))

    # Identificador INEGI del municipio que corresponde al
    # Juzgado/Área al que se turnó el Exhorto y que realiza la respuesta de este
    municipio_turnado_id: Mapped[int]

    # Identificador propio del PJ exhortado que corresponde al Juzgado/Área al que se turna el Exhorto y está respondiendo
    area_turnado_id: Mapped[Optional[str]] = mapped_column(String(64))

    # Nombre del Juzgado/Área al que el Exhorto se turnó y está respondiendo.
    area_turnado_nombre: Mapped[str] = mapped_column(String(256))

    # Número de Exhorto con el que se radicó en el Juzgado/Área que se turnó el exhorto.
    # Este número sirve para que el usuario pueda identificar su exhorto dentro del Juzgado/Área donde se turnó.
    numero_exhorto: Mapped[Optional[str]] = mapped_column(String(64))

    # Valor que representa si se realizó la diligenciación del Exhorto:
    # 0 = No Diligenciado
    # 1 = Parcialmente Diligenciado
    # 2 = Diligenciado"
    tipo_diligenciado: Mapped[Optional[int]]

    # Texto simple referente a alguna observación u observaciones correspondientes a la respuesta del Exhorto
    observaciones: Mapped[Optional[str]] = mapped_column(String(1024))

    #
    # Internos
    #

    # Si el remitente es INTERNO entonces fue creada por nosotros, si es EXTERNO fue creada por otro PJ
    remitente: Mapped[str] = mapped_column(
        Enum(*REMITENTES, name="exh_exhortos_respuestas_remitentes", native_enum=False), index=True
    )

    # Estado de la respuesta y el estado anterior, para cuando se necesite revertir un cambio de estado
    estado: Mapped[str] = mapped_column(Enum(*ESTADOS, name="exh_exhortos_respuestas_estados", native_enum=False), index=True)
    estado_anterior: Mapped[Optional[str]]

    # Conservar el JSON que se genera cuando se hace el envío y el que se recibe con el acuse
    paquete_enviado: Mapped[Optional[dict]] = mapped_column(JSONB)
    acuse_recibido: Mapped[Optional[dict]] = mapped_column(JSONB)

    #
    # Hijos
    #

    # Hijo: Archivos de la respuesta
    exh_exhortos_respuestas_archivos: Mapped[list["ExhExhortoRespuestaArchivo"]] = relationship(
        back_populates="exh_exhorto_respuesta"
    )

    # Hijo: Videos de la respuesta
    exh_exhortos_respuestas_videos: Mapped[list["ExhExhortoRespuestaVideo"]] = relationship(
        back_populates="exh_exhorto_respuesta"
    )

    @property
    def tipo_diligenciado_nombre(self):
        """Nombre del tipo de diligenciado"""
        if self.tipo_diligenciado in self.TIPOS_DILIGENCIADOS:
            return self.TIPOS_DILIGENCIADOS[self.tipo_diligenciado]
        return "No Diligenciado"

    def __repr__(self):
        """Representación"""
        return f"<ExhExhortoRespuesta {self.id}>"
