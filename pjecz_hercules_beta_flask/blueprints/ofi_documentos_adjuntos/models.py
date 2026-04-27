"""
Ofi Documentos Ajuntos, modelos
"""

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...config.extensions import database
from ...lib.universal_mixin import UniversalMixin


class OfiDocumentoAdjunto(database.Model, UniversalMixin):
    """OfiDocumentoAdjunto"""

    EXTENSIONES = {
        "jpg": ("Imagen", "image/jpg"),
        "jpeg": ("Imagen", "image/jpeg"),
        "png": ("Imagen", "image/png"),
        "pdf": ("Archivo PDF", "application/pdf"),
        "doc": ("Archivo Word", "application/msword"),
        "docx": ("Archivo Word", "application/msword"),
        "xls": ("Archivo Excel", "application/vnd.ms-excel"),
        "xlsx": ("Archivo Excel", "application/vnd.ms-excel"),
    }

    # Nombre de la tabla
    __tablename__ = "ofi_documentos_adjuntos"

    # Clave primaria
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Clave foránea
    ofi_documento_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ofi_documentos.id"))
    ofi_documento: Mapped["OfiDocumento"] = relationship(back_populates="ofi_documentos_adjuntos")

    # Columnas
    descripcion: Mapped[str] = mapped_column(String(256))
    archivo: Mapped[str] = mapped_column(String(256), default="")
    url: Mapped[str] = mapped_column(String(512), default="")
    mime_type: Mapped[str] = mapped_column(String(128), default="")

    def __repr__(self):
        """Representación"""
        return f"<OfiDocumentoAdjunto {self.id}>"
