"""
Communications, enviar al motor de firma electrónica
"""

import json
import os
from datetime import datetime
from io import BytesIO

import requests
from dotenv import load_dotenv
from xhtml2pdf import pisa

from pjecz_hercules_beta_flask.app import app
from pjecz_hercules_beta_flask.blueprints.ofi_documentos.communications import bitacora
from pjecz_hercules_beta_flask.blueprints.ofi_documentos.models import OfiDocumento
from pjecz_hercules_beta_flask.lib.cryptography import simmetric_decrypt
from pjecz_hercules_beta_flask.lib.exceptions import (
    MyBucketNotFoundError,
    MyConnectionError,
    MyIsDeletedError,
    MyNotExistsError,
    MyNotValidParamError,
    MyRequestError,
    MyResponseError,
    MyStatusCodeError,
    MyUploadError,
)
from pjecz_hercules_beta_flask.lib.google_cloud_storage import upload_file_to_gcs
from pjecz_hercules_beta_flask.lib.safe_string import safe_uuid

# Cargar variables de entorno
load_dotenv()
CLOUD_STORAGE_DEPOSITO_OFICIOS = os.getenv("CLOUD_STORAGE_DEPOSITO_OFICIOS", "")
EFIRMA_SER_FIRMAR_DOC_PDF_URL = os.getenv("EFIRMA_SER_FIRMAR_DOC_PDF_URL", "")
EFIRMA_SER_CANCELAR_DOC_PDF_URL = os.getenv("EFIRMA_SER_CANCELAR_DOC_PDF_URL", "")
EFIRMA_APLICACION_IDENTIFICADOR = int(os.getenv("EFIRMA_APLICACION_IDENTIFICADOR", 0))
EFIRMA_APLICACION_CONTRASENA = os.getenv("EFIRMA_APLICACION_CONTRASENA", "")
EFIRMA_REGISTRO_IDENTIFICADOR = int(os.getenv("EFIRMA_REGISTRO_IDENTIFICADOR", 0))
EFIRMA_REGISTRO_CONTRASENA = os.getenv("EFIRMA_REGISTRO_CONTRASENA", "")
FERNET_KEY = os.getenv("FERNET_KEY", "")
TIMEOUT = 120  # segundos

# Cargar la aplicación para tener acceso a la base de datos
app.app_context().push()


def enviar_a_efirma(ofi_documento_id: str) -> tuple[str, str, str]:
    """Enviar al motor de firma electrónica"""
    mensajes = []
    mensaje_info = "Inicia enviar al motor de firma electrónica"
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

    # Validar que esté definida la variable de entorno CLOUD_STORAGE_DEPOSITO_OFICIOS
    if not CLOUD_STORAGE_DEPOSITO_OFICIOS:
        error = "La variable de entorno CLOUD_STORAGE_DEPOSITO_OFICIOS no está definida"
        bitacora.error(error)
        raise MyNotValidParamError(error)

    # Validar que esté definida la variable de entorno EFIRMA_SER_FIRMAR_DOC_PDF_URL
    if not EFIRMA_SER_FIRMAR_DOC_PDF_URL:
        error = "La variable de entorno EFIRMA_SER_FIRMAR_DOC_PDF_URL no está definida"
        bitacora.error(error)
        raise MyNotValidParamError(error)

    # Validar que esté definida la variable de entorno EFIRMA_SER_CANCELAR_DOC_PDF_URL
    if not EFIRMA_SER_CANCELAR_DOC_PDF_URL:
        error = "La variable de entorno EFIRMA_SER_CANCELAR_DOC_PDF_URL no está definida"
        bitacora.error(error)
        raise MyNotValidParamError(error)

    # Validar que esté definida la variable de entorno EFIRMA_APLICACION_IDENTIFICADOR
    if not EFIRMA_APLICACION_IDENTIFICADOR:
        error = "La variable de entorno EFIRMA_APLICACION_IDENTIFICADOR no está definida"
        bitacora.error(error)
        raise MyNotValidParamError(error)

    # Validar que esté definida la variable de entorno EFIRMA_APLICACION_CONTRASENA
    if not EFIRMA_APLICACION_CONTRASENA:
        error = "La variable de entorno EFIRMA_APLICACION_CONTRASENA no está definida"
        bitacora.error(error)
        raise MyNotValidParamError(error)

    # Validar que estén definida la variable de entorno EFIRMA_REGISTRO_IDENTIFICADOR
    if not EFIRMA_REGISTRO_IDENTIFICADOR:
        error = "La variable de entorno EFIRMA_REGISTRO_IDENTIFICADOR no está definida"
        bitacora.error(error)
        raise MyNotValidParamError(error)

    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        raise MyNotValidParamError("ID de oficio inválido")
    ofi_documento = OfiDocumento.query.get(ofi_documento_id)
    if not ofi_documento:
        raise MyNotExistsError("El oficio no existe")

    # Validar el estatus, que no esté eliminado
    if ofi_documento.estatus != "A":
        raise MyIsDeletedError("El oficio está eliminado")

    # Validar que el estado sea FIRMADO o ENVIADO
    if ofi_documento.estado not in ["FIRMADO", "ENVIADO"]:
        error = "El oficio no está en estado FIRMADO o ENVIADO"
        bitacora.error(error)
        raise MyNotValidParamError(error)

    # Validar que archivo_pdf_url sea None
    if ofi_documento.archivo_pdf_url:
        error = "El oficio ya tiene un archivo PDF asociado."
        bitacora.error(error)
        raise MyNotValidParamError(error)

    # Por defecto, la contraseña del registro de firma electrónica es la variable de entorno EFIRMA_REGISTRO_CONTRASENA
    efirma_contrasena = EFIRMA_REGISTRO_CONTRASENA

    # Si no está definida, se descifra del registro del usuario con la clave FERNET_KEY
    if efirma_contrasena is None or efirma_contrasena == "":
        # Validar que esté definida la variable de entorno FERNET_KEY
        if not FERNET_KEY:
            error = "La variable de entorno FERNET_KEY no está definida"
            bitacora.error(error)
            raise MyNotValidParamError(error)

        # Validar que el usuario tenga una contraseña de efirma
        if not ofi_documento.usuario.efirma_contrasena:
            error = f"El usuario {ofi_documento.usuario.email} no tiene una contraseña de efirma definida."
            bitacora.error(error)
            raise MyNotValidParamError(error)

        # Descifrar la contraseña de efirma del usuario
        try:
            efirma_contrasena = simmetric_decrypt(ofi_documento.usuario.efirma_contrasena, FERNET_KEY)
        except Exception as error:
            error = f"ERROR: No se pudo descifrar la contraseña de efirma: {error}"
            bitacora.error(error)
            raise MyNotValidParamError(error)

    #
    # Convertir el contenido HTML a archivo PDF
    #

    # Iniciar el contenido del archivo PDF
    contenidos = []

    # Agregar tag html y head
    contenidos.append("<html>")
    contenidos.append("<head>")

    # Agregar tag style con el CSS para definir la hoja tamaño carta, la cabecera, el contenido y el pie de página
    contenidos.append(
        """
        <style>
            @page {
                size: letter portrait; /* La hoja carta mide 612pt x 792pt */
                @frame header_frame {
                    -pdf-frame-content: header_content;
                    left: 50pt; width: 512pt; top: 40pt; height: 80pt;
                    /* -pdf-frame-border: 1; Borde alrededor del contenido para ver sus dimensiones */
                }
                @frame content_frame {
                    left: 50pt; width: 512pt; top: 130pt; height: 550pt;
                    /* -pdf-frame-border: 1; Borde alrededor del contenido para ver sus dimensiones */
                }
                @frame footer_frame {
                    -pdf-frame-content: footer_content;
                    left: 50pt; width: 512pt; bottom: 40pt; height: 80pt;
                    /* -pdf-frame-border: 1; Borde alrededor del contenido para ver sus dimensiones */
                }
            }
            body {
                font-family: Arial, sans-serif;
                font-size: 12pt;
            }
        </style>
    """
    )

    # Agregar el cierre del tag head e iniciar el tag body
    contenidos.append("</head>")
    contenidos.append("<body>")

    # Agregar la imagen de cabecera de la autoridad del usuario
    if ofi_documento.usuario.autoridad.pagina_cabecera_url:
        contenidos.append("<div id='header_content'>")
        contenidos.append(f"<img src='{ofi_documento.usuario.autoridad.pagina_cabecera_url}' alt='Cabecera'>")
        contenidos.append("</div>")

    # Agregar la imagen de pie de página de la autoridad del usuario
    if ofi_documento.usuario.autoridad.pagina_pie_url:
        contenidos.append("<div id='footer_content' style='text-align: center;'>")
        if ofi_documento.firma_simple:
            contenidos.append(f"Firma electrónica simple: {ofi_documento.firma_simple}<br>")
        contenidos.append(f"<img src='{ofi_documento.usuario.autoridad.pagina_pie_url}' alt='Pie de página'>")
        contenidos.append("</div>")

    # Agregar el contenido del oficio
    contenidos.append(ofi_documento.contenido_html)

    # Agregar el cierre del tag body y html
    contenidos.append("</body>")
    contenidos.append("</html>")

    # Convertir el contenido HTML a archivo PDF
    pdf_buffer = BytesIO()
    _ = pisa.CreatePDF("\n".join(contenidos), dest=pdf_buffer, encoding="UTF-8")
    pdf_buffer.seek(0)
    archivo_pdf_bytes = pdf_buffer.read()

    #
    # Enviar el archivo PDF al motor de firma electrónica
    #

    # Definir los datos a enviar
    payload_for_data = {
        "idRegistro": EFIRMA_REGISTRO_IDENTIFICADOR,
        "contrasenaRegistro": efirma_contrasena,
        "idAplicacion": EFIRMA_APLICACION_IDENTIFICADOR,
        "contrasenaAplicacion": EFIRMA_APLICACION_CONTRASENA,
        "referencia": "",
        "verificarUrl": "true",
        "tipoRespuesta": "json",
        "modo": "firmarDocumento",
    }

    # Enviar el archivo PDF al motor de firma electrónica
    try:
        respuesta = requests.post(
            url=EFIRMA_SER_FIRMAR_DOC_PDF_URL,
            timeout=TIMEOUT,
            files={"archivo": ("oficio.pdf", archivo_pdf_bytes, "application/pdf")},
            data=payload_for_data,
            verify=False,
        )
        respuesta.raise_for_status()
    except requests.exceptions.ConnectionError as error:
        mensaje = f"Error de conexion con el motor de efirma. {str(error)}"
        bitacora.error(mensaje)
        raise MyConnectionError(mensaje)
    except requests.exceptions.HTTPError as error:
        mensaje = f"Error porque la respuesta no tiene el estado 200 del motor de efirma. {str(error)}"
        bitacora.error(mensaje)
        raise MyStatusCodeError(mensaje)
    except requests.exceptions.RequestException as error:
        mensaje = f"Error desconocido al enviar el archivo PDF al motor de efirma. {str(error)}"
        bitacora.error(mensaje)
        raise MyRequestError(mensaje)

    # Tomar el texto de la respuesta
    texto = respuesta.text

    # Si la contraseña es incorrecta, se registra el error
    if texto == "Contraseña incorrecta":
        mensaje = f"Error de Contraseña. {str(texto)}"
        bitacora.error(mensaje)
        raise MyResponseError(mensaje)

    # Convertir el texto a un diccionario
    texto = respuesta.text.replace('"{', "{").replace('}"', "}")
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError:
        mensaje = f"Error porque respuesta no es JSON: {texto}"
        bitacora.error(mensaje)
        raise MyResponseError(mensaje)

    # Ejemplo de la respuesta esperada:
    # {
    #     'success': True,
    #     'folio': 000000,
    #     'mensaje': 'La operación se ha realizado exitosamente.',
    #     'numeroCertificado': '00000000000000000000',
    #     'nombreAplicacion': 'PlataformaWEB',
    #     'cadenaOriginal': 'XXXXYYMMDDNNN|YYYY-MM-DD HH:MM:SS|XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX|',
    #     'firmo': 'XXXXXXXX',
    #     'documento': 'oficio.pdf',
    #     'huellaDocumento': 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',
    #     'fecha': 'DD/MM/YYYY HH:MM:SS',
    #     'selloDigital': 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',
    #     'url': 'https://efirmapjecz.gob.mx/eFirmaServicios/verificaDocumento.do?verificar=XXXXXXXXXXXXXXX',
    #     'urlDescarga': 'https://efirmapjecz.gob.mx/eFirmaServicios/descargarDocumento.do?p=XXXXXXXXXXXXXXXX',
    # }

    # Validar que la respuesta tenga el campo 'success' y que sea True
    if not datos.get("success", False):
        mensaje = f"Error porque la respuesta no es exitosa: {datos}"
        bitacora.error(mensaje)
        raise MyResponseError(mensaje)

    # Validar que la respuesta tenga el campo 'folio'
    if "folio" not in datos:
        mensaje = f"Error porque la respuesta no tiene el campo 'folio': {datos}"
        bitacora.error(mensaje)
        raise MyResponseError(mensaje)

    # Validar que la respuesta tenga el campo 'mensaje'
    if "mensaje" not in datos:
        mensaje = f"Error porque la respuesta no tiene el campo 'mensaje': {datos}"
        bitacora.error(mensaje)
        raise MyResponseError(mensaje)

    # Validar que la respuesta tenga el campo 'selloDigital'
    if "selloDigital" not in datos:
        mensaje = f"Error porque la respuesta no tiene el campo 'selloDigital': {datos}"
        bitacora.error(mensaje)
        raise MyResponseError(mensaje)

    # Validar que la respuesta tenga el campo 'url'
    if "url" not in datos:
        mensaje = f"Error porque la respuesta no tiene el campo 'url': {datos}"
        bitacora.error(mensaje)
        raise MyResponseError(mensaje)

    # Validar que la respuesta tenga el campo 'urlDescarga'
    if "urlDescarga" not in datos:
        mensaje = f"Error porque la respuesta no tiene el campo 'urlDescarga': {datos}"
        bitacora.error(mensaje)
        raise MyResponseError(mensaje)

    #
    # Descargar el archivo PDF firmado en urlDescarga
    #

    # Descargar el archivo PDF desde el motor de firma electrónica
    try:
        respuesta_pdf = requests.get(
            url=datos["urlDescarga"],
            timeout=TIMEOUT,
            verify=False,
            stream=True,
        )
        respuesta_pdf.raise_for_status()
    except requests.exceptions.ConnectionError as error:
        mensaje = f"Error de conexion al descargar el archivo PDF. {str(error)}"
        bitacora.error(mensaje)
        raise MyConnectionError(mensaje)
    except requests.exceptions.HTTPError as error:
        mensaje = f"Error porque la respuesta no tiene el estado 200 al descargar el archivo PDF. {str(error)}"
        bitacora.error(mensaje)
        raise MyStatusCodeError(mensaje)
    except requests.exceptions.RequestException as error:
        mensaje = f"Error desconocido al descargar el archivo PDF. {str(error)}"
        bitacora.error(mensaje)
        raise MyRequestError(mensaje)

    # Tomar el nuevo archivo PDF con firmado electrónico
    archivo_pdf_efirma = respuesta_pdf.content

    #
    # Subir a Google Cloud Storage el archivo PDF
    #

    # Definir la ruta para blob_name con la fecha actual
    archivo_pdf_nombre = f"{ofi_documento.id}.pdf"
    fecha_hora_recepcion = datetime.now()
    anio = fecha_hora_recepcion.strftime("%Y")
    mes = fecha_hora_recepcion.strftime("%m")
    dia = fecha_hora_recepcion.strftime("%d")
    blob_name = f"ofi_documentos/{anio}/{mes}/{dia}/{archivo_pdf_nombre}"

    # Subir el archivo en Google Storage
    try:
        archivo_pdf_efirma_url = upload_file_to_gcs(
            bucket_name=CLOUD_STORAGE_DEPOSITO_OFICIOS,
            blob_name=blob_name,
            content_type="application/pdf",
            data=archivo_pdf_efirma,
        )
    except (MyBucketNotFoundError, MyUploadError) as error:
        bitacora.error(f"Error al subir el archivo PDF a Google Cloud Storage: {error}")
        raise error

    # Actualizar el documento con la URL del archivo PDF
    ofi_documento.archivo_pdf_url = archivo_pdf_efirma_url

    # Actualizar el documento con los datos de la firma electrónica avanzada
    ofi_documento.firma_avanzada_nombre = ofi_documento.usuario.nombre
    ofi_documento.firma_avanzada_puesto = ofi_documento.usuario.puesto
    ofi_documento.firma_avanzada_email = ofi_documento.usuario.email
    ofi_documento.firma_avanzada_efirma_tiempo = datetime.now()
    ofi_documento.firma_avanzada_efirma_folio = datos.get("folio", None)
    ofi_documento.firma_avanzada_efirma_sello_digital = datos.get("selloDigital", "")
    ofi_documento.firma_avanzada_efirma_url = datos.get("url", "")
    ofi_documento.firma_avanzada_efirma_qr_url = None
    ofi_documento.firma_avanzada_efirma_mensaje = datos.get("mensaje", "")
    ofi_documento.firma_avanzada_efirma_error = None
    ofi_documento.firma_avanzada_cancelo_tiempo = None
    ofi_documento.firma_avanzada_cancelo_motivo = None
    ofi_documento.firma_avanzada_cancelo_error = None
    ofi_documento.save()

    # Elaborar mensaje_termino
    mensaje_termino = "Termina enviar al motor de firma electrónica."
    mensajes.append(mensaje_termino)
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return "\n".join(mensajes), "", ""
