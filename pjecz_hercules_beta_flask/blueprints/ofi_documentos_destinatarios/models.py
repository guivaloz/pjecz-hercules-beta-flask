"""
Ofi Documentos Destinatarios, modelos
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...config.extensions import database
from ...lib.universal_mixin import UniversalMixin


class OfiDocumentoDestinatario(database.Model, UniversalMixin):
    """OfiDocumentoDestinatario"""

    # Nombre de la tabla
    __tablename__ = "ofi_documentos_destinatarios"

    # Clave primaria
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Clave foránea
    ofi_documento_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ofi_documentos.id"))
    ofi_documento: Mapped["OfiDocumento"] = relationship(back_populates="ofi_documentos_destinatarios")
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    usuario: Mapped["Usuario"] = relationship(back_populates="ofi_documentos_destinatarios")

    # Columnas
    con_copia: Mapped[bool] = mapped_column(default=False)
    fue_leido: Mapped[bool] = mapped_column(default=False)
    fue_leido_tiempo: Mapped[Optional[datetime]]

    @property
    def email(self):
        """Email del destinatario"""
        return self.usuario.email

    @property
    def nombre(self):
        """Nombre del destinatario"""
        return self.usuario.nombre

    def __repr__(self):
        """Representación"""
        return f"<OfiDocumentoDestinatario {self.id}>"
