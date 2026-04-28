"""
Conversions, convertir a PDF
"""

import os
from datetime import datetime
from io import BytesIO

from dotenv import load_dotenv
from xhtml2pdf import pisa

from pjecz_hercules_beta_flask.app import app
from pjecz_hercules_beta_flask.blueprints.ofi_documentos.conversions import bitacora
from pjecz_hercules_beta_flask.blueprints.ofi_documentos.models import OfiDocumento
from pjecz_hercules_beta_flask.lib.exceptions import (
    MyBucketNotFoundError,
    MyIsDeletedError,
    MyNotExistsError,
    MyNotValidParamError,
    MyUploadError,
)
from pjecz_hercules_beta_flask.lib.google_cloud_storage import upload_file_to_gcs
from pjecz_hercules_beta_flask.lib.safe_string import safe_uuid

# Cargar variables de entorno
load_dotenv()
CLOUD_STORAGE_DEPOSITO_OFICIOS = os.getenv("CLOUD_STORAGE_DEPOSITO_OFICIOS", "")

# Cargar la aplicación para tener acceso a la base de datos
app.app_context().push()


def convertir_a_pdf(ofi_documento_id: str) -> tuple[str, str, str]:
    """Convertir a PDF"""
    mensajes = []
    mensaje_info = f"Inicia convertir a PDF {ofi_documento_id}"
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
                font-size: 11pt;
                margin-bottom: 0px;
                margin-top: 0px;
                margin-left: 0px;
                margin-right: 0px;
                padding-bottom: 0px;
                padding-left: 0px;
                padding-right: 0px;
                padding-top: 0px;
            }
            p {
                margin-bottom: 12px;
                margin-top: 0px;
                padding-bottom: 0px;
                padding-top: 0px;
                line-height: 1.2;
            }
            table.content-table {
                border-collapse: collapse;
                border-bottom-color: black;
                border-bottom-style: solid;
                border-bottom-width: 0.5px;
                border-left-color: black;
                border-left-style: solid;
                border-left-width: 0.5px;
                border-right-color: black;
                border-right-style: solid;
                border-right-width: 0.5px;
                border-top-color: black;
                border-top-style: solid;
                border-top-width: 0.5px;
                margin-bottom: 12px;
                margin-top: 0px;
                margin-left: 0px;
                margin-right: 0px;
                padding-bottom: 0px;
                padding-left: 0px;
                padding-right: 0px;
                padding-top: 0px;
                width: 100%;
            }
            table.layout-table {
                border-collapse: collapse;
                border-bottom-color: black;
                border-bottom-style: solid;
                border-bottom-width: 0.5px;
                border-left-color: black;
                border-left-style: solid;
                border-left-width: 0.5px;
                border-right-color: black;
                border-right-style: solid;
                border-right-width: 0.5px;
                border-top-color: black;
                border-top-style: solid;
                border-top-width: 0.5px;
                margin-bottom: 12px;
                margin-top: 0px;
                margin-left: 0px;
                margin-right: 0px;
                padding-bottom: 0px;
                padding-left: 0px;
                padding-right: 0px;
                padding-top: 0px;
            }
            table.content-table td,
            table.layout-table td {
                border-bottom-color: black;
                border-bottom-style: solid;
                border-bottom-width: 0.5px;
                border-left-color: black;
                border-left-style: solid;
                border-left-width: 0.5px;
                border-right-color: black;
                border-right-style: solid;
                border-right-width: 0.5px;
                border-top-color: black;
                border-top-style: solid;
                border-top-width: 0.5px;
                margin-bottom: 0px;
                margin-top: 0px;
                margin-left: 0px;
                margin-right: 0px;
                padding-bottom: 4px;
                padding-left: 4px;
                padding-right: 4px;
                padding-top: 4px;
                line-height: 1;
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
        archivo_pdf_url = upload_file_to_gcs(
            bucket_name=CLOUD_STORAGE_DEPOSITO_OFICIOS,
            blob_name=blob_name,
            content_type="application/pdf",
            data=archivo_pdf_bytes,
        )
    except (MyBucketNotFoundError, MyUploadError) as error:
        bitacora.error(f"Error al subir el archivo PDF a Google Cloud Storage: {error}")
        raise error

    # Actualizar el documento con la URL del archivo PDF
    ofi_documento.archivo_pdf_url = archivo_pdf_url
    ofi_documento.save()

    # Elaborar mensaje_termino
    mensaje_termino = "Termina convertir a PDF."
    mensajes.append(mensaje_termino)
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return "\n".join(mensajes), archivo_pdf_nombre, archivo_pdf_url
