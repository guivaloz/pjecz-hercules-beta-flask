"""
Oficios Documentos Adjuntos, vistas
"""

import json
from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.datastructures import CombinedMultiDict
from werkzeug.utils import secure_filename

from ...lib.datatables import get_datatable_parameters, output_datatable_json
from ...lib.exceptions import (
    MyBucketNotFoundError,
    MyFileNotFoundError,
    MyNotValidParamError,
    MyUploadError,
)
from ...lib.google_cloud_storage import EXTENSIONS_MEDIA_TYPES, get_blob_name_from_url, get_file_from_gcs, upload_file_to_gcs
from ...lib.safe_string import safe_clave, safe_message, safe_string, safe_uuid
from ..bitacoras.models import Bitacora
from ..modulos.models import Modulo
from ..ofi_documentos.models import OfiDocumento
from ..permisos.models import Permiso
from ..usuarios.decorators import permission_required
from ..usuarios.models import Usuario
from .forms import OfiDocumentoAdjuntoForm
from .models import OfiDocumentoAdjunto

MAX_FILE_SIZE_MB = 20
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

MODULO = "OFI DOCUMENTOS ADJUNTOS"

ofi_documentos_adjuntos = Blueprint("ofi_documentos_adjuntos", __name__, template_folder="templates")


@ofi_documentos_adjuntos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@ofi_documentos_adjuntos.route("/ofi_documentos_adjuntos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de adjuntos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = OfiDocumentoAdjunto.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "ofi_documento_id" in request.form:
        consulta = consulta.filter_by(ofi_documento_id=request.form["ofi_documento_id"])
    # Ordenar y paginar
    registros = consulta.order_by(OfiDocumentoAdjunto.descripcion).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "id": resultado.id,  # Necesario para eliminar o recuperar
                "detalle": {
                    "descripcion": resultado.descripcion,
                    "url": url_for("ofi_documentos_adjuntos.detail", ofi_documento_adjunto_id=resultado.id),
                },
                "descripcion": resultado.descripcion,
                "eliminar_recuperar": {
                    "id": resultado.id,
                    "estatus": resultado.estatus,
                    "url": (
                        url_for("ofi_documentos_adjuntos.delete_recover_json", ofi_documento_adjunto_id=resultado.id)
                        if current_user.can_edit(MODULO)
                        else ""
                    ),
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@ofi_documentos_adjuntos.route("/ofi_documentos_adjuntos/<ofi_documento_adjunto_id>")
def detail(ofi_documento_adjunto_id):
    """Detalle de un adjunto"""
    ofi_documento_adjunto_id = safe_uuid(ofi_documento_adjunto_id)
    if ofi_documento_adjunto_id == "":
        flash("ID de archivo adjunto inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento_adjunto = OfiDocumentoAdjunto.query.get_or_404(ofi_documento_adjunto_id)
    return render_template("ofi_documentos_adjuntos/detail.jinja2", ofi_documento_adjunto=ofi_documento_adjunto)


@ofi_documentos_adjuntos.route("/ofi_documentos_adjuntos/nuevo/<ofi_documento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_ofi_documento(ofi_documento_id):
    """Nuevo adjunto para un documento"""
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if ofi_documento_id == "":
        flash("ID de documento inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    form = OfiDocumentoAdjuntoForm(CombinedMultiDict((request.files, request.form)))
    if form.validate_on_submit():
        es_valido = True
        # Tomar el archivo del formulario
        archivo = request.files["archivo"]
        if not archivo:
            flash("Archivo no proporcionado", "warning")
            es_valido = False
        # Validar la extensión del archivo
        extensiones_permitidas = EXTENSIONS_MEDIA_TYPES.keys()
        archivo_nombre = secure_filename(archivo.filename) if archivo.filename else ""
        if archivo_nombre == "":
            flash("Archivo sin nombre. Por favor, proporcione un archivo con nombre.", "warning")
            es_valido = False
        if es_valido and "." not in archivo_nombre:
            flash(f"Archivo sin extensión. Extensiones permitidas: {', '.join(extensiones_permitidas)}", "warning")
            es_valido = False
        archivo_extension = archivo_nombre.rsplit(".", 1)[1].lower() if es_valido else ""
        if es_valido and archivo_extension not in extensiones_permitidas:
            flash(f"Archivo no permitido. Extensiones permitidas: {', '.join(extensiones_permitidas)}", "warning")
            es_valido = False
        # Validar el tamaño del archivo
        if len(archivo.read()) > MAX_FILE_SIZE_BYTES:
            flash(f"Archivo demasiado grande. Tamaño máximo permitido: {MAX_FILE_SIZE_MB} MB", "warning")
            es_valido = False
        archivo.seek(0)
        # Si es válido, subir el archivo a Google Cloud Storage
        if es_valido:
            # Definir el tiempo en que se subirá el archivo
            tiempo_subida = datetime.now()
            # Insertar el registro del adjunto para obtener su UUID
            ofi_documento_adjunto = OfiDocumentoAdjunto(
                ofi_documento=ofi_documento,
                descripcion=safe_string(form.descripcion.data),
            )
            ofi_documento_adjunto.save()
            # Definir el nombre del archivo a subir
            blob_filename = f"{str(ofi_documento_adjunto.id)}.{archivo_extension}"
            # Definir el blob_name con tiempo_subida
            year = tiempo_subida.strftime("%Y")
            month = tiempo_subida.strftime("%m")
            day = tiempo_subida.strftime("%d")
            blob_name = f"ofi_documentos_adjuntos/{year}/{month}/{day}/{blob_filename}"
            # Subir el archivo a GCS
            try:
                data = archivo.stream.read()
                public_url = upload_file_to_gcs(
                    bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_OFICIOS"],
                    blob_name=blob_name,
                    content_type=EXTENSIONS_MEDIA_TYPES[archivo_extension],
                    data=data,
                )
            except (MyBucketNotFoundError, MyUploadError) as error:
                ofi_documento_adjunto.delete()
                flash(str(error), "danger")
                return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento_id))
            # Actualizar el registro del adjunto con la URL pública
            ofi_documento_adjunto.archivo = archivo_nombre
            ofi_documento_adjunto.url = public_url
            ofi_documento_adjunto.save()
            # Insertar en la Bitácora
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nuevo archivo adjunto {ofi_documento_adjunto.archivo}"),
                url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento_id),
            )
            bitacora.save()
    # Entregar el formulario
    return render_template("ofi_documentos_adjuntos/new_with_ofi_documento.jinja2", form=form, ofi_documento=ofi_documento)


@ofi_documentos_adjuntos.route("/ofi_documentos_adjuntos/eliminar_todos/<ofi_documento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def remove_all(ofi_documento_id):
    """Eliminar todos los adjuntos de un documento"""
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if ofi_documento_id == "":
        flash("ID de documento inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    adjuntos = OfiDocumentoAdjunto.query.filter_by(ofi_documento_id=ofi_documento.id).filter_by(estatus="A").all()
    if not adjuntos:
        flash("No hay adjuntos para eliminar", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    for adjunto in adjuntos:
        adjunto.delete()
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Eliminados todos los adjuntos del oficio {ofi_documento.descripcion}"),
        url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
    )
    bitacora.save()
    return render_template("ofi_documentos.detail", ofi_documento_id=ofi_documento_id)


@ofi_documentos_adjuntos.route("/ofi_documentos_adjuntos/eliminar/<ofi_documento_adjunto_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def delete(ofi_documento_adjunto_id):
    """Eliminar adjunto"""
    # Consultar el adjunto
    ofi_documento_adjunto_id = safe_uuid(ofi_documento_adjunto_id)
    if ofi_documento_adjunto_id == "":
        flash("ID de archivo adjunto inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento_adjunto = OfiDocumentoAdjunto.query.get_or_404(ofi_documento_adjunto_id)
    # Validar el estatus, que no esté eliminado
    if ofi_documento_adjunto.estatus != "A":
        flash("El adjunto ya está eliminado", "warning")
        return redirect(url_for("ofi_documentos_adjuntos.detail", ofi_documento_adjunto_id=ofi_documento_adjunto.id))
    # Eliminar el adjunto
    ofi_documento_adjunto.delete()
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Eliminado adjunto {ofi_documento_adjunto.descripcion}"),
        url=url_for("ofi_documentos_adjuntos.detail", ofi_documento_adjunto_id=ofi_documento_adjunto.id),
    )
    bitacora.save()
    flash(bitacora.descripcion, "success")
    return redirect(url_for("ofi_documentos_adjuntos.detail", ofi_documento_adjunto_id=ofi_documento_adjunto.id))


@ofi_documentos_adjuntos.route("/ofi_documentos_adjuntos/recuperar/<ofi_documento_adjunto_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def recover(ofi_documento_adjunto_id):
    """Recuperar adjunto"""
    # Consultar el adjunto
    ofi_documento_adjunto_id = safe_uuid(ofi_documento_adjunto_id)
    if ofi_documento_adjunto_id == "":
        flash("ID de archivo adjunto inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento_adjunto = OfiDocumentoAdjunto.query.get_or_404(ofi_documento_adjunto_id)
    # Validar el estatus, que esté eliminado
    if ofi_documento_adjunto.estatus != "B":
        flash("El adjunto no está eliminado", "warning")
        return redirect(url_for("ofi_documentos_adjuntos.detail", ofi_documento_adjunto_id=ofi_documento_adjunto.id))
    # Recuperar el adjunto
    ofi_documento_adjunto.recover()
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Recuperado adjunto {ofi_documento_adjunto.descripcion}"),
        url=url_for("ofi_documentos_adjuntos.detail", ofi_documento_adjunto_id=ofi_documento_adjunto.id),
    )
    bitacora.save()
    flash(bitacora.descripcion, "success")
    return redirect(url_for("ofi_documentos_adjuntos.detail", ofi_documento_adjunto_id=ofi_documento_adjunto.id))


@ofi_documentos_adjuntos.route("/ofi_documentos_adjuntos/eliminar_recuperar/<ofi_documento_adjunto_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def delete_recover_json(ofi_documento_adjunto_id):
    """Eliminar o recuperar adjunto, respuesta JSON"""
    # Consultar el adjunto
    ofi_documento_adjunto_id = safe_uuid(ofi_documento_adjunto_id)
    if ofi_documento_adjunto_id == "":
        return {"success": False, "message": "No es un UUID válido"}
    ofi_documento_adjunto = OfiDocumentoAdjunto.query.get(ofi_documento_adjunto_id)
    if ofi_documento_adjunto is None:
        return {"success": False, "message": "No encontrado"}
    # Cambiar el estatus a su opuesto y guardar
    if ofi_documento_adjunto.estatus == "A":
        ofi_documento_adjunto.delete()
        accion = f"Eliminado el adjunto {ofi_documento_adjunto.descripcion}"
    else:
        ofi_documento_adjunto.recover()
        accion = f"Recuperado el adjunto {ofi_documento_adjunto.descripcion}"
    # Entregar JSON con el nuevo estatus
    return {
        "success": True,
        "message": accion,
        "estatus": ofi_documento_adjunto.estatus,
        "id": ofi_documento_adjunto.id,
    }
