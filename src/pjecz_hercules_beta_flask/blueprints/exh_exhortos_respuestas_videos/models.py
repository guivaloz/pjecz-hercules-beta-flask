"""
Exh Exhortos Respuestas Videos, modelos
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pjecz_hercules_beta_flask.config.extensions import database
from pjecz_hercules_beta_flask.lib.universal_mixin import UniversalMixin


class ExhExhortoRespuestaVideo(database.Model, UniversalMixin):
    """ExhExhortoRespuestaVideo"""

    # Nombre de la tabla
    __tablename__ = "exh_exhortos_respuestas_videos"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    exh_exhorto_respuesta_id: Mapped[int] = mapped_column(ForeignKey("exh_exhortos_respuestas.id"))
    exh_exhorto_respuesta: Mapped["ExhExhortoRespuesta"] = relationship(back_populates="exh_exhortos_respuestas_videos")

    # El título del video, esto para que pueda identificarse
    titulo: Mapped[str] = mapped_column(String(256))

    # Descripción del video/audiencia realizada
    descripcion: Mapped[Optional[str]] = mapped_column(String(1024))

    # Fecha (o fecha hora) en que se realizó el video y/o audiencia.
    fecha: Mapped[Optional[datetime]]

    # URL que el usuario final podrá accesar para poder visualizar el video
    url_acceso: Mapped[str] = mapped_column(String(512))

    def __repr__(self):
        """Representación"""
        return f"<ExhExhortoRespuestaVideo {self.id}>"
