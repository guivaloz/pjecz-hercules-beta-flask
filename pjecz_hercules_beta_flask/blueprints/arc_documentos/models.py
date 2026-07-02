"""
Archivos Documentos, modelos
"""

from typing import List, Optional

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pjecz_hercules_beta_flask.config.extensions import database
from pjecz_hercules_beta_flask.lib.universal_mixin import UniversalMixin


class ArcDocumento(database.Model, UniversalMixin):
    """ArcDocumento"""

    UBICACIONES = {
        "NO DEFINIDO": "No Definido",
        "ARCHIVO": "Archivo",
        "JUZGADO": "Juzgado",
        "REMESA": "Remesa",
    }

    TIPO_JUZGADOS = {
        "ORAL": "Oral",
        "TRADICIONAL": "Tradiccional",
    }

    # Nombre de la tabla
    __tablename__ = "arc_documentos"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    autoridad_id: Mapped[int] = mapped_column(ForeignKey("autoridades.id"))
    autoridad: Mapped["Autoridad"] = relationship(back_populates="arc_documentos")
    arc_juzgado_origen_id: Mapped[int] = mapped_column(ForeignKey("arc_juzgados_extintos.id"))
    arc_juzgado_origen: Mapped["ArcJuzgadoExtinto"] = relationship(back_populates="arc_documentos")
    arc_documento_tipo_id: Mapped[int] = mapped_column(ForeignKey("arc_documentos_tipos.id"))
    arc_documento_tipo: Mapped["ArcDocumentoTipo"] = relationship(back_populates="arc_documentos")

    # Columnas
    actor: Mapped[str] = mapped_column(String(256))
    anio: Mapped[int]
    demandado: Mapped[str] = mapped_column(String(256))
    expediente: Mapped[str] = mapped_column(String(16), index=True)
    expediente_numero: Mapped[int]
    juicio: Mapped[str] = mapped_column(String(128))
    arc_juzgados_origen_claves: Mapped[str] = mapped_column(String(512))
    fojas: Mapped[int]
    tipo_juzgado: Mapped[str] = mapped_column(
        Enum(*TIPO_JUZGADOS, name="arc_documentos_tipo_juzgados", native_enum=False), index=True
    )
    ubicacion: Mapped[str] = mapped_column(
        Enum(*UBICACIONES, name="arc_documentos_ubicaciones", native_enum=False),
        index=True,
        default="NO DEFINIDO",
        server_default="NO DEFINIDO",
    )
    notas: Mapped[Optional[str]] = mapped_column(String(256))

    # Hijos
    arc_documentos_bitacoras: Mapped[List["ArcDocumentoBitacora"]] = relationship(back_populates="arc_documento")
    arc_solicitudes: Mapped[List["ArcSolicitud"]] = relationship(back_populates="arc_documento")
    arc_remesas_documentos: Mapped[List["ArcRemesaDocumento"]] = relationship(back_populates="arc_documento")

    def __repr__(self):
        """Representación"""
        return f"<ArcDocumento {self.id}>"
