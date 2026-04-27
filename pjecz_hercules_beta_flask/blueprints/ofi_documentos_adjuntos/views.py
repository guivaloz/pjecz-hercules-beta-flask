"""
Oficios Documentos Adjuntos, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ...lib.datatables import get_datatable_parameters, output_datatable_json
from ...lib.safe_string import safe_clave, safe_message, safe_string, safe_uuid
from ..bitacoras.models import Bitacora
from ..modulos.models import Modulo
from ..permisos.models import Permiso
from ..usuarios.decorators import permission_required
from .models import OfiDocumentoAdjunto

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
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("ofi_documentos_adjuntos.detail", ofi_documento_adjunto_id=resultado.id),
                },
                "descripcion": resultado.descripcion,
                "acciones": url_for("ofi_documentos_adjuntos.delete", ofi_documento_adjunto_id=resultado.id),
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


@ofi_documentos_adjuntos.route("/ofi_documentos_adjuntos/eliminar/<ofi_documento_adjunto_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
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
@permission_required(MODULO, Permiso.ADMINISTRAR)
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
