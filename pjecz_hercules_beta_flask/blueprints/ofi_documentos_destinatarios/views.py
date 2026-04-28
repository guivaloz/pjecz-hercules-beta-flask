"""
Oficios Documentos Destinatarios, vistas
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
from ..usuarios.models import Usuario
from .models import OfiDocumentoDestinatario

MODULO = "OFI DOCUMENTOS DESTINATARIOS"

ofi_documentos_destinatarios = Blueprint("ofi_documentos_destinatarios", __name__, template_folder="templates")


@ofi_documentos_destinatarios.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@ofi_documentos_destinatarios.route("/ofi_documentos_destinatarios/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de destinatarios"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = OfiDocumentoDestinatario.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "ofi_documento_id" in request.form:
        consulta = consulta.filter(OfiDocumentoDestinatario.ofi_documento_id == request.form["ofi_documento_id"])
    # Ordenar y paginar
    consulta = consulta.join(Usuario)
    registros = consulta.order_by(Usuario.email).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("ofi_documentos_destinatarios.detail", ofi_documento_destinatario_id=resultado.id),
                },
                "usuario_nombre": resultado.usuario.nombre,
                "usuario_email": resultado.usuario.email,
                "fue_leido": resultado.fue_leido,
                "con_copia": resultado.con_copia,
                "acciones": url_for("ofi_documentos_destinatarios.delete", ofi_documento_destinatario_id=resultado.id),
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@ofi_documentos_destinatarios.route("/ofi_documentos_destinatarios/<ofi_documento_destinatario_id>")
def detail(ofi_documento_destinatario_id):
    """Detalle de un destinatario"""
    ofi_documento_destinatario_id = safe_uuid(ofi_documento_destinatario_id)
    if ofi_documento_destinatario_id == "":
        flash("ID de destinatario inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento_destinatario = OfiDocumentoDestinatario.query.get_or_404(ofi_documento_destinatario_id)
    return render_template("ofi_documentos_destinatarios/detail.jinja2", ofi_documento_destinatario=ofi_documento_destinatario)


@ofi_documentos_destinatarios.route("/ofi_documentos_destinatarios/eliminar/<ofi_documento_destinatario_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(ofi_documento_destinatario_id):
    """Eliminar destinatario"""
    # Consultar el destinatario
    ofi_documento_destinatario_id = safe_uuid(ofi_documento_destinatario_id)
    if ofi_documento_destinatario_id == "":
        flash("ID de destinatario inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento_destinatario = OfiDocumentoDestinatario.query.get_or_404(ofi_documento_destinatario_id)
    # Validar el estatus, que no esté eliminado
    if ofi_documento_destinatario.estatus == "A":
        flash("El adjunto ya está eliminado", "warning")
        return redirect(
            url_for("ofi_documentos_destinatarios.detail", ofi_documento_destinatario_id=ofi_documento_destinatario.id)
        )
    # Eliminar el destinatario
    ofi_documento_destinatario.delete()
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Eliminado destinatario {ofi_documento_destinatario.nombre}"),
        url=url_for("ofi_documentos_destinatarios.detail", ofi_documento_destinatario_id=ofi_documento_destinatario.id),
    )
    bitacora.save()
    flash(bitacora.descripcion, "success")
    return redirect(url_for("ofi_documentos_destinatarios.detail", ofi_documento_destinatario_id=ofi_documento_destinatario.id))


@ofi_documentos_destinatarios.route("/ofi_documentos_destinatarios/recuperar/<ofi_documento_destinatario_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(ofi_documento_destinatario_id):
    """Recuperar destinatario"""
    # Consultar el destinatario
    ofi_documento_destinatario_id = safe_uuid(ofi_documento_destinatario_id)
    if ofi_documento_destinatario_id == "":
        flash("ID de destinatario inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento_destinatario = OfiDocumentoDestinatario.query.get_or_404(ofi_documento_destinatario_id)
    # Validar el estatus, que esté eliminado
    if ofi_documento_destinatario.estatus == "B":
        flash("El destinatario no está eliminado", "warning")
        return redirect(
            url_for("ofi_documentos_destinatarios.detail", ofi_documento_destinatario_id=ofi_documento_destinatario.id)
        )
    # Recuperar el destinatario
    ofi_documento_destinatario.recover()
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Recuperado destinatario {ofi_documento_destinatario.nombre}"),
        url=url_for("ofi_documentos_destinatarios.detail", ofi_documento_destinatario_id=ofi_documento_destinatario.id),
    )
    bitacora.save()
    flash(bitacora.descripcion, "success")
    return redirect(url_for("ofi_documentos_destinatarios.detail", ofi_documento_destinatario_id=ofi_documento_destinatario.id))
