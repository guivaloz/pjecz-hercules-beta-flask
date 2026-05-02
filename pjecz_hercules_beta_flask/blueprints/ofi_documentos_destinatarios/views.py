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
from ..ofi_documentos.models import OfiDocumento
from ..permisos.models import Permiso
from ..usuarios.decorators import permission_required
from ..usuarios.models import Usuario
from .forms import OfiDocumentoDestinatarioForm
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
                "id": resultado.id,  # Necesario para eliminar o recuperar
                "detalle": {
                    "usuario_email": resultado.usuario.email,
                    "url": url_for("ofi_documentos_destinatarios.detail", ofi_documento_destinatario_id=resultado.id),
                },
                "usuario_nombre": resultado.usuario.nombre,
                "usuario_puesto": resultado.usuario.puesto,
                "fue_leido": resultado.fue_leido,
                "con_copia": resultado.con_copia,
                "eliminar_recuperar": {
                    "id": resultado.id,
                    "estatus": resultado.estatus,
                    "url": (
                        url_for("ofi_documentos_destinatarios.delete_recover_json", ofi_documento_destinatario_id=resultado.id)
                        if current_user.can_edit(MODULO)
                        else ""
                    ),
                },
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


@ofi_documentos_destinatarios.route("/ofi_documentos_destinatarios/nuevo/<ofi_documento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_ofi_documento(ofi_documento_id):
    """Nuevo destinatario para un documento"""
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if ofi_documento_id == "":
        flash("ID de documento inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    form = OfiDocumentoDestinatarioForm()
    if form.validate_on_submit():
        es_valido = True
        # Consultar ese destinatario en el documento para descartar si ya lo está
        destinatario_existente = OfiDocumentoDestinatario.query.filter_by(
            ofi_documento_id=ofi_documento_id, usuario_id=form.usuario.data
        ).first()
        if destinatario_existente and destinatario_existente.estatus == "A":
            flash("El destinatario ya está registrado para este documento", "warning")
            es_valido = False
        if es_valido:
            # Si el destinatario existe pero está eliminado, recuperarlo y actualizar con_copia
            if destinatario_existente and destinatario_existente.estatus == "B":
                destinatario_existente.con_copia = form.con_copia.data
                destinatario_existente.recover()
            # Crear el destinatario
            ofi_documento_destinatario = OfiDocumentoDestinatario(
                ofi_documento=ofi_documento,
                usuario_id=form.usuario.data,
                con_copia=form.con_copia.data,
            )
            ofi_documento_destinatario.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nuevo destinatario {ofi_documento_destinatario.usuario.email}"),
                url=url_for("ofi_documentos_destinatarios.detail", ofi_documento_destinatario_id=ofi_documento_destinatario.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(
                url_for("ofi_documentos_destinatarios.detail", ofi_documento_destinatario_id=ofi_documento_destinatario.id)
            )
    # Entregar formulario
    return render_template("ofi_documentos_destinatarios/new_with_ofi_documento.jinja2", form=form, ofi_documento=ofi_documento)


@ofi_documentos_destinatarios.route("/ofi_documentos_destinatarios/eliminar_todos/<ofi_documento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def remove_all(ofi_documento_id):
    """Eliminar todos los destinatarios de un documento"""
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if ofi_documento_id == "":
        flash("ID de documento inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    destinatarios = OfiDocumentoDestinatario.query.filter_by(ofi_documento_id=ofi_documento.id).filter_by(estatus="A").all()
    if not destinatarios:
        flash("No hay destinatarios para eliminar", "warning")
        return redirect(url_for("ofi_documentos_destinatarios.new_with_ofi_documento", ofi_documento_id=ofi_documento_id))
    for destinatario in destinatarios:
        destinatario.delete()
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Eliminados todos los destinatarios del oficio {ofi_documento.descripcion}"),
        url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
    )
    bitacora.save()
    return render_template("ofi_documentos.detail", ofi_documento_id=ofi_documento_id)


@ofi_documentos_destinatarios.route("/ofi_documentos_destinatarios/eliminar/<ofi_documento_destinatario_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
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
@permission_required(MODULO, Permiso.MODIFICAR)
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


@ofi_documentos_destinatarios.route("/ofi_documentos_destinatarios/eliminar_recuperar/<ofi_documento_destinatario_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def delete_recover_json(ofi_documento_destinatario_id):
    """Eliminar o recuperar destinatario, respuesta JSON"""
    # Consultar el adjunto
    ofi_documento_destinatario_id = safe_uuid(ofi_documento_destinatario_id)
    if ofi_documento_destinatario_id == "":
        return {"success": False, "message": "No es un UUID válido"}
    ofi_documento_destinatario = OfiDocumentoDestinatario.query.get(ofi_documento_destinatario_id)
    if ofi_documento_destinatario is None:
        return {"success": False, "message": "No encontrado"}
    # Cambiar el estatus a su opuesto y guardar
    if ofi_documento_destinatario.estatus == "A":
        ofi_documento_destinatario.delete()
        accion = f"Eliminado el destinatario {ofi_documento_destinatario.usuario.email}"
    else:
        ofi_documento_destinatario.recover()
        accion = f"Recuperado el destinatario {ofi_documento_destinatario.usuario.email}"
    # Entregar JSON con el nuevo estatus
    return {
        "success": True,
        "message": accion,
        "estatus": ofi_documento_destinatario.estatus,
        "id": ofi_documento_destinatario.id,
    }
