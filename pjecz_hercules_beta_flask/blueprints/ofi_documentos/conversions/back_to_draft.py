"""
Conversions, regresar a borrador
"""

import os

from dotenv import load_dotenv

from pjecz_hercules_beta_flask.app import app
from pjecz_hercules_beta_flask.blueprints.ofi_documentos.conversions import bitacora
from pjecz_hercules_beta_flask.blueprints.ofi_documentos.models import OfiDocumento
from pjecz_hercules_beta_flask.lib.exceptions import (
    MyBucketNotFoundError,
    MyFileNotFoundError,
    MyIsDeletedError,
    MyNotExistsError,
    MyNotValidParamError,
)
from pjecz_hercules_beta_flask.lib.google_cloud_storage import delete_file_from_gcs, get_blob_name_from_url
from pjecz_hercules_beta_flask.lib.safe_string import safe_uuid

# Cargar variables de entorno
load_dotenv()
CLOUD_STORAGE_DEPOSITO_OFICIOS = os.getenv("CLOUD_STORAGE_DEPOSITO_OFICIOS", "")

# Cargar la aplicación para tener acceso a la base de datos
app.app_context().push()


def regresar_a_borrador(ofi_documento_id: str) -> tuple[str, str, str]:
    """Regresar a borrador"""
    mensajes = []
    mensaje_info = f"Inicia regresar a borrador {ofi_documento_id}"
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

    # Validar que esté definida la variable de entorno CLOUD_STORAGE_DEPOSITO_OFICIOS
    if not CLOUD_STORAGE_DEPOSITO_OFICIOS:
        error = "La variable de entorno CLOUD_STORAGE_DEPOSITO_OFICIOS no está definida"
        bitacora.error(error)
        raise MyNotValidParamError(error)

    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        error = "ID de oficio inválido"
        bitacora.error(error)
        raise MyNotValidParamError(error)
    ofi_documento = OfiDocumento.query.get(ofi_documento_id)
    if not ofi_documento:
        error = "El oficio no existe"
        bitacora.error(error)
        raise MyNotExistsError(error)

    # Validar el estatus, que no esté eliminado
    if ofi_documento.estatus != "A":
        error = "El oficio está eliminado"
        bitacora.error(error)
        raise MyIsDeletedError(error)

    # Validar que NO esté cancelado
    if ofi_documento.esta_cancelado:
        error = "El oficio está cancelado"
        bitacora.error(error)
        raise MyIsDeletedError(error)

    # Validar que el estado NO sea BORRADOR
    if ofi_documento.estado == "BORRADOR":
        error = "El oficio ya está en estado BORRADOR"
        bitacora.error(error)
        raise MyNotValidParamError(error)

    # Quitar la firma simple
    if ofi_documento.firma_simple:
        ofi_documento.firma_simple = ""
        ofi_documento.firma_simple_tiempo = None
        ofi_documento.firma_simple_usuario_id = None
        mensaje = "Se ha quitado la firma simple."
        bitacora.info(mensaje)
        mensajes.append(mensaje)

    # Quitar la firma electrónica avanzada
    if ofi_documento.firma_avanzada_efirma_sello_digital:
        ofi_documento.firma_avanzada_nombre = None
        ofi_documento.firma_avanzada_puesto = None
        ofi_documento.firma_avanzada_email = None
        ofi_documento.firma_avanzada_efirma_tiempo = None
        ofi_documento.firma_avanzada_efirma_folio = None
        ofi_documento.firma_avanzada_efirma_sello_digital = None
        ofi_documento.firma_avanzada_efirma_url = None
        ofi_documento.firma_avanzada_efirma_qr_url = None
        ofi_documento.firma_avanzada_efirma_mensaje = None
        ofi_documento.firma_avanzada_efirma_error = None
        ofi_documento.firma_avanzada_cancelo_tiempo = None
        ofi_documento.firma_avanzada_cancelo_motivo = None
        ofi_documento.firma_avanzada_cancelo_error = None
        mensaje = "Se ha quitado la firma electrónica avanzada."
        bitacora.info(mensaje)
        mensajes.append(mensaje)

    # Quitar la URL al archivo PDF
    if ofi_documento.archivo_pdf_url:
        try:
            delete_file_from_gcs(
                bucket_name=CLOUD_STORAGE_DEPOSITO_OFICIOS,
                blob_name=get_blob_name_from_url(ofi_documento.archivo_pdf_url),
            )
            mensaje = "Se ha eliminado el archivo PDF del almacenamiento."
            bitacora.info(mensaje)
            mensajes.append(mensaje)
        except MyBucketNotFoundError as error:
            error = f"El depósito de archivos PDF no existe: {error}"
            bitacora.error(error)
            raise MyBucketNotFoundError(error)
        except (MyFileNotFoundError, MyNotValidParamError) as warning:
            advertencia = f"AVISO: El archivo PDF no existe en el depósito de oficios: {warning}"
            bitacora.warning(advertencia)
            mensajes.append(advertencia)

    # Quitar la URL al archivo PDF
    ofi_documento.archivo_pdf_url = None

    # Poner en falso el archivado
    if ofi_documento.esta_archivado:
        ofi_documento.esta_archivado = False
        mensaje = "Se ha puesto en falso esta_archivado."
        bitacora.info(mensaje)
        mensajes.append(mensaje)

    # Cambiar al estado BORRADOR
    ofi_documento.estado = "BORRADOR"

    # Guardar los cambios
    ofi_documento.save()

    # Elaborar mensaje_termino
    mensaje_termino = "El documento ha sido regresado a borrador exitosamente."
    mensajes.append(mensaje_termino)
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return "\n".join(mensajes), "", ""
