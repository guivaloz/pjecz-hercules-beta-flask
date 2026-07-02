"""
Exhortos, modelos
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.functions import now

from pjecz_hercules_beta_flask.config.extensions import database
from pjecz_hercules_beta_flask.lib.universal_mixin import UniversalMixin


class ExhExhorto(database.Model, UniversalMixin):
    """ExhExhorto"""

    ESTADOS = {
        "RECIBIDO": "Recibido",
        "TRANSFIRIENDO": "Transfiriendo",
        "PROCESANDO": "Procesando",
        "RECHAZADO": "Rechazado",
        "CONTESTADO": "Contestado",
        "PENDIENTE": "Pendiente",
        "CANCELADO": "Cancelado",
        "POR ENVIAR": "Por enviar",
        "RECIBIDO CON EXITO": "Recibido con éxito",
        "RESPONDIDO": "Respondido",
        "ARCHIVADO": "Archivado",
    }

    REMITENTES = {
        "INTERNO": "Interno",
        "EXTERNO": "Externo",
    }

    # Nombre de la tabla
    __tablename__ = "exh_exhortos"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea: Autoridad, Juzgado/Área al que se turna el Exhorto y hará el correspondiente proceso de este
    autoridad_id: Mapped[int] = mapped_column(ForeignKey("autoridades.id"))
    autoridad: Mapped["Autoridad"] = relationship(back_populates="exh_exhortos")

    # Clave foránea: Área de recepción
    exh_area_id: Mapped[int] = mapped_column(ForeignKey("exh_areas.id"))
    exh_area: Mapped["ExhArea"] = relationship(back_populates="exh_exhortos")

    # Clave foránea: Tipo de diligencia
    exh_tipo_diligencia_id: Mapped[int] = mapped_column(ForeignKey("exh_tipos_diligencias.id"))
    exh_tipo_diligencia: Mapped["ExhTipoDiligencia"] = relationship(back_populates="exh_exhortos")

    # Clave foránea: Municipio de Origen donde está localizado el Juzgado del PJ exhortante
    # Cuando haya comunicación por medio de la API se debe recibir o transmitir el identificador INEGI del municipio
    municipio_origen_id: Mapped[int] = mapped_column(ForeignKey("municipios.id"))
    municipio_origen: Mapped["Municipio"] = relationship(back_populates="exh_exhortos_origenes")

    # UUID identificador con el que el PJ exhortante identifica el exhorto que envía
    exhorto_origen_id: Mapped[str] = mapped_column(String(64))

    # ID del municipio del Estado del PJ exhortado al que se quiere enviar el Exhorto
    # NO es una clave foránea para no causar conflicto con municipio_origen_id
    municipio_destino_id: Mapped[int]

    # Materia (el que se obtuvo en la consulta de materias del PJ exhortado) al que el Exhorto hace referencia
    materia_clave: Mapped[str] = mapped_column(String(32))
    materia_nombre: Mapped[str] = mapped_column(String(256))

    # Identificador propio y nombre del Juzgado/Área que envía el Exhorto
    juzgado_origen_id: Mapped[Optional[str]] = mapped_column(String(64))
    juzgado_origen_nombre: Mapped[str] = mapped_column(String(256))

    # El número de expediente (o carpeta procesal, carpeta...) que tiene el asunto en el Juzgado de Origen
    numero_expediente_origen: Mapped[str] = mapped_column(String(256))

    # El número del oficio con el que se envía el exhorto, el que corresponde al control interno del Juzgado de origen
    numero_oficio_origen: Mapped[Optional[str]] = mapped_column(String(256))

    # Nombre del tipo de Juicio, o asunto, listado de los delitos (para materia Penal)
    # que corresponde al Expediente del cual el Juzgado envía el Exhorto
    tipo_juicio_asunto_delitos: Mapped[str] = mapped_column(String(256))

    # Nombre completo del Juez del Juzgado o titular del Área que envía el Exhorto, opcional
    juez_exhortante: Mapped[Optional[str]] = mapped_column(String(256))

    # Número de fojas que contiene el exhorto. El valor 0 significa "No Especificado"
    fojas: Mapped[int]

    # Cantidad de dias a partir del día que se recibió en el Poder Judicial exhortado que se tiene para responder el Exhorto.
    # El valor de 0 significa "No Especificado"
    dias_responder: Mapped[int]

    # Identificador correspondiente al tipo de diligencia según el catálogo
    # Y nombre del tipo de diligenciación que le corresponde al exhorto enviado.
    # Este puede contener valores como "Oficio", "Petición de Parte".
    # Al asignar la propiedad "tipoDiligenciaId", no es necesario especificar este campo.
    # Aunque se tiene la clave foránea, se conservan estas propiedades por memoria y compatibilidad
    tipo_diligencia_id: Mapped[Optional[str]] = mapped_column(String(32), default="")
    tipo_diligenciacion_nombre: Mapped[Optional[str]] = mapped_column(String(256), default="")

    # Fecha y hora en que el Poder Judicial exhortante registró que se envió el exhorto en su hora local.
    # En caso de no enviar este dato, el Poder Judicial exhortado puede tomar su fecha hora local.
    fecha_origen: Mapped[Optional[datetime]] = mapped_column(default=now())

    # Texto simple que contenga información extra o relevante sobre el exhorto, opcional
    observaciones: Mapped[Optional[str]] = mapped_column(String(1024))

    #
    # Acuse
    #

    # Este dato puede ser un alfanumérico, un número secuencial, un GUID/UUID... que sea único en el Poder Judicial exhortando
    # para que pueda ser localizado el Exhorto posteriomente en el endpoint Consulta de Exhorto.
    # Este dato debe ser URL frendly, es decir que se pueda usar en el segmento de URL para el endpoint de la consulta
    folio_seguimiento: Mapped[Optional[str]] = mapped_column(String(64))

    # Fecha hora local en el que el Poder Judicial exhortado marca que se recibió el Exhorto
    acuse_fecha_hora_recepcion: Mapped[Optional[datetime]]

    # Identificador del muncipio en donde se recibió o turnó el exhorto.
    # Puede dar el caso que el exhorto se turne directamente al Juzgado,
    # por lo que este dato seria el identificador del municipio donde está el Juzgado.
    # En caso que se tenga una "Oficialía Virtual", no es necesario especificar este dato.
    # NOTA: este dato corresponde al catálogo de municipios del INEGI.
    acuse_municipio_area_recibe_id: Mapped[Optional[int]]

    # Identificador del área o Juzgado turnado en donde se recibe el Exhorto.
    # En caso que todavía no esté turnado o se disponga de una "Oficialía Virtual", este dato puede no ir en la respuesta.
    acuse_area_recibe_id: Mapped[Optional[str]] = mapped_column(String(64))

    # Nombre del área o Juzgado turnado en donde se encuentra el Exhorto.
    # En caso de tener una "Oficialía Virtual", este dato puede omitirse
    acuse_area_recibe_nombre: Mapped[Optional[str]] = mapped_column(String(256))

    # Acuse Contiene una URL para abrir una página con la información referente a la recepción del exhorto que se realizó.
    # Esta página el Juzgado que envió el exhorto la puede imprimir como acuse de recibido y evidencia de que el exhorto
    # fue enviado correctamente al Poder Judicial exhortado o también una página que muestre el estatus del exhorto.
    acuse_url_info: Mapped[Optional[str]] = mapped_column(String(256))

    #
    # Consulta
    #

    # Identificador INEGI del municipio que corresponde al Juzgado/Área al que se turnó el Exhorto
    municipio_turnado_id: Mapped[Optional[str]] = mapped_column(String(3))
    municipio_turnado_nombre: Mapped[Optional[str]] = mapped_column(String(256))

    # Identificador propio del Poder Judicial Exhortado que corresponde al Juzgado/Área
    # al que se turna el Exhorto y hará el correspondiente proceso de este.
    area_turnado_id: Mapped[Optional[str]] = mapped_column(String(16))
    area_turnado_nombre: Mapped[Optional[str]] = mapped_column(String(256))

    # Número de Exhorto con el que se radica en el Juzgado/Área que se turnó el exhorto.
    # Este número sirve para que el usuario pueda indentificar su exhorto dentro del Juzgado/Área donde se turnó.
    numero_exhorto: Mapped[Optional[str]] = mapped_column(String(64))

    #
    # Internos
    #

    # Campo para saber si es un proceso interno o extorno
    remitente: Mapped[str] = mapped_column(Enum(*REMITENTES, name="exh_exhortos_remitentes", native_enum=False), index=True)

    # Estado del exhorto y el estado anterior, para cuando se necesite revertir un cambio de estado
    estado: Mapped[str] = mapped_column(Enum(*ESTADOS, name="exh_exhortos_estados", native_enum=False), index=True)
    estado_anterior: Mapped[Optional[str]] = mapped_column(String(24))

    # Conservar el JSON que se genera cuando se hace el envío y el que se recibe con el acuse
    paquete_enviado: Mapped[Optional[dict]] = mapped_column(JSONB)
    acuse_recibido: Mapped[Optional[dict]] = mapped_column(JSONB)

    #
    # Hijos
    #

    # Hijo: Archivos
    # Colección de los datos referentes a los archivos que se van a recibir el Poder Judicial exhortado en el envío del Exhorto.
    exh_exhortos_archivos: Mapped[List["ExhExhortoArchivo"]] = relationship("ExhExhortoArchivo", back_populates="exh_exhorto")

    # Hijo: Partes
    # Contiene la definición de las partes del Expediente/Juicio/Asunto en el Juzgado/Área de origen
    exh_exhortos_partes: Mapped[List["ExhExhortoParte"]] = relationship("ExhExhortoParte", back_populates="exh_exhorto")

    # Hijo: Promoventes
    # Contiene la definición del promovente o los promoventes del exhorto, que comúnmente será el representante legal o abogado.
    # Donde se debe especificar el correo electrónico para darle acceso a medios electrónicos.
    # exh_exhortos_promoventes: Mapped[List["ExhExhortoPromovente"]] = relationship(
    #     "ExhExhortoPromovente", back_populates="exh_exhorto"
    # )

    # Hijo: Actualizaciones
    # exh_exhortos_actualizaciones: Mapped[List["ExhExhortoActualizacion"]] = relationship(
    #     "ExhExhortoActualizacion", back_populates="exh_exhorto"
    # )

    # Hijo: Promociones
    # exh_exhortos_promociones: Mapped[List["ExhExhortoPromocion"]] = relationship(
    #     "ExhExhortoPromocion", back_populates="exh_exhorto"
    # )

    # Hijo: Respuestas
    # exh_exhortos_respuestas: Mapped[List["ExhExhortoRespuesta"]] = relationship(
    #     "ExhExhortoRespuesta", back_populates="exh_exhorto"
    # )

    def __repr__(self):
        """Representación"""
        return f"<ExhExhorto {self.id}>"
