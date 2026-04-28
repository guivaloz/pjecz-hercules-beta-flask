"""
Ofi Documentos, modelos
"""

import hashlib
import uuid
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...config.extensions import database
from ...lib.universal_mixin import UniversalMixin


class OfiDocumento(database.Model, UniversalMixin):
    """OfiDocumento"""

    ESTADOS = {
        "BORRADOR": "Borrador",
        "FIRMADO": "Firmado",
        "ENVIADO": "Enviado",
    }

    # Nombre de la tabla
    __tablename__ = "ofi_documentos"

    # Clave primaria
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Clave foránea
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    usuario: Mapped["Usuario"] = relationship(back_populates="ofi_documentos")

    # Columnas
    descripcion: Mapped[str] = mapped_column(String(256))
    estado: Mapped[str] = mapped_column(Enum(*ESTADOS, name="ofi_documentos_estados", native_enum=False), index=True)
    cadena_oficio_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    esta_archivado: Mapped[bool] = mapped_column(default=False)
    esta_cancelado: Mapped[bool] = mapped_column(default=False)
    vencimiento_fecha: Mapped[Optional[date]]
    enviado_tiempo: Mapped[Optional[datetime]]

    # El folio contiene su año y número
    folio: Mapped[Optional[str]] = mapped_column(String(64))
    folio_anio: Mapped[Optional[int]]
    folio_num: Mapped[Optional[int]]

    # Columnas contenido
    contenido_html: Mapped[Optional[str]] = mapped_column(Text)
    contenido_md: Mapped[Optional[str]] = mapped_column(Text)
    contenido_sfdt: Mapped[Optional[JSONB]] = mapped_column(JSONB)

    # Columnas firma simple
    firma_simple: Mapped[str] = mapped_column(String(256), default="")
    firma_simple_tiempo: Mapped[Optional[datetime]]
    firma_simple_usuario_id: Mapped[Optional[int]]

    # Columnas firma electrónica avanzada
    firma_avanzada_nombre: Mapped[Optional[str]] = mapped_column(String(256))
    firma_avanzada_puesto: Mapped[Optional[str]] = mapped_column(String(256))
    firma_avanzada_email: Mapped[Optional[str]] = mapped_column(String(256))
    firma_avanzada_efirma_tiempo: Mapped[Optional[datetime]]
    firma_avanzada_efirma_folio: Mapped[Optional[int]]
    firma_avanzada_efirma_sello_digital: Mapped[Optional[str]] = mapped_column(String(512))
    firma_avanzada_efirma_url: Mapped[Optional[str]] = mapped_column(String(256))
    firma_avanzada_efirma_qr_url: Mapped[Optional[str]] = mapped_column(String(256))
    firma_avanzada_efirma_mensaje: Mapped[Optional[str]] = mapped_column(String(512))
    firma_avanzada_efirma_error: Mapped[Optional[str]] = mapped_column(String(512))
    firma_avanzada_cancelo_tiempo: Mapped[Optional[datetime]]
    firma_avanzada_cancelo_motivo: Mapped[Optional[str]] = mapped_column(String(256))
    firma_avanzada_cancelo_error: Mapped[Optional[str]] = mapped_column(String(512))

    # Columna para el archivo PDF en Google Cloud Storage, se genera al firmar el documento
    archivo_pdf_url: Mapped[Optional[str]] = mapped_column(String(512))

    # Hijos
    ofi_documentos_adjuntos: Mapped[List["OfiDocumentoAdjunto"]] = relationship(back_populates="ofi_documento")
    ofi_documentos_destinatarios: Mapped[List["OfiDocumentoDestinatario"]] = relationship(back_populates="ofi_documento")

    def elaborar_hash(self):
        """Generate a hash representing the current sample state"""
        elementos = []
        elementos.append(str(self.id))
        elementos.append(str(self.folio_num))
        elementos.append(str(self.folio_anio))
        elementos.append(str(self.contenido_md))
        return hashlib.md5("|".join(elementos).encode("utf-8")).hexdigest()

    def __repr__(self):
        """Representación"""
        return f"<OfiDocumento {self.id}>"
