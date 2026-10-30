"""
DGT Tipos, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from pjecz_hercules_beta_flask.blueprints.bitacoras.models import Bitacora
from pjecz_hercules_beta_flask.blueprints.dgt_tipos.forms import DgtTipoForm
from pjecz_hercules_beta_flask.blueprints.dgt_tipos.models import DgtTipo
from pjecz_hercules_beta_flask.blueprints.modulos.models import Modulo
from pjecz_hercules_beta_flask.blueprints.permisos.models import Permiso
from pjecz_hercules_beta_flask.blueprints.usuarios.decorators import permission_required
from pjecz_hercules_beta_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_hercules_beta_flask.lib.safe_string import safe_clave, safe_message, safe_string, safe_uuid

MODULO = "DGT TIPOS"

dgt_tipos = Blueprint("dgt_tipos", __name__, template_folder="templates")


@dgt_tipos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@dgt_tipos.route("/dgt_tipos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de DGT Tipos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = DgtTipo.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(DgtTipo.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(DgtTipo.estatus == "A")
    if "clave" in request.form:
        try:
            clave = safe_clave(request.form["clave"], max_len=64)
            if clave != "":
                consulta = consulta.filter(DgtTipo.clave.contains(clave))
        except ValueError:
            pass
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], save_enie=True)
        if descripcion != "":
            consulta = consulta.filter(DgtTipo.descripcion.contains(descripcion))
    # Ordenar y paginar
    registros = consulta.order_by(DgtTipo.clave).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for item in registros:
        data.append(
            {
                "detalle": {
                    "clave": item.clave,
                    "url": url_for("dgt_tipos.detail", dgt_tipo_id=item.id),
                },
                "descripcion": item.descripcion,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@dgt_tipos.route("/dgt_tipos")
def list_active():
    """Listado de DGT Tipos activos"""
    return render_template(
        "dgt_tipos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="DGT Tipos",
        estatus="A",
    )


@dgt_tipos.route("/dgt_tipos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de DGT Tipos inactivos"""
    return render_template(
        "dgt_tipos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="DGT Tipos inactivos",
        estatus="B",
    )


@dgt_tipos.route("/dgt_tipos/<dgt_tipo_id>")
def detail(dgt_tipo_id):
    """Detalle de un DGT Tipo"""
    dgt_tipo_id = safe_uuid(dgt_tipo_id)
    if dgt_tipo_id == "":
        flash("ID de DGT Tipo inválido", "warning")
        return redirect(url_for("dgt_tipos.list_active"))
    dgt_tipo = DgtTipo.query.get_or_404(dgt_tipo_id)
    return render_template("dgt_tipos/detail.jinja2", dgt_tipo=dgt_tipo)


@dgt_tipos.route("/dgt_tipos/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo DGT Tipo"""
    form = DgtTipoForm()
    if form.validate_on_submit():
        clave = safe_clave(form.clave.data, max_len=64)
        descripcion = safe_string(form.descripcion.data, save_enie=True)
        # Validar que la clave no se repita
        if DgtTipo.query.filter_by(clave=clave).first():
            flash("Esa clave ya está en uso. Debe de ser única.", "warning")
            return render_template("dgt_tipos/new.jinja2", form=form)
        # Guardar
        dgt_tipo = DgtTipo(
            clave=clave,
            descripcion=descripcion,
        )
        dgt_tipo.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo DGT Tipo {dgt_tipo.clave}"),
            url=url_for("dgt_tipos.detail", dgt_tipo_id=dgt_tipo.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template("dgt_tipos/new.jinja2", form=form)


@dgt_tipos.route("/dgt_tipos/edicion/<dgt_tipo_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(dgt_tipo_id):
    """Editar DGT Tipo"""
    dgt_tipo_id = safe_uuid(dgt_tipo_id)
    if dgt_tipo_id == "":
        flash("ID de DGT Tipo inválido", "warning")
        return redirect(url_for("dgt_tipos.list_active"))
    dgt_tipo = DgtTipo.query.get_or_404(dgt_tipo_id)
    form = DgtTipoForm()
    if form.validate_on_submit():
        es_valido = True
        # Si cambia la clave verificar que no este en uso
        clave = safe_clave(form.clave.data, max_len=64)
        if dgt_tipo.clave != clave:
            dgt_tipo_existente = DgtTipo.query.filter_by(clave=clave).first()
            if dgt_tipo_existente and dgt_tipo_existente.id != dgt_tipo.id:
                es_valido = False
                flash("La clave ya está en uso. Debe de ser única.", "warning")
        # Si es valido actualizar
        if es_valido:
            dgt_tipo.clave = clave
            dgt_tipo.descripcion = safe_string(form.descripcion.data, save_enie=True)
            dgt_tipo.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado DGT Tipo {dgt_tipo.clave}"),
                url=url_for("dgt_tipos.detail", dgt_tipo_id=dgt_tipo.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.clave.data = dgt_tipo.clave
    form.descripcion.data = dgt_tipo.descripcion
    return render_template("dgt_tipos/edit.jinja2", form=form, dgt_tipo=dgt_tipo)


@dgt_tipos.route("/dgt_tipos/eliminar/<dgt_tipo_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(dgt_tipo_id):
    """Eliminar DGT Tipo"""
    dgt_tipo_id = safe_uuid(dgt_tipo_id)
    if dgt_tipo_id == "":
        flash("ID de DGT Tipo inválido", "warning")
        return redirect(url_for("dgt_tipos.list_active"))
    dgt_tipo = DgtTipo.query.get_or_404(dgt_tipo_id)
    if dgt_tipo.estatus == "A":
        dgt_tipo.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado DGT Tipo {dgt_tipo.clave}"),
            url=url_for("dgt_tipos.detail", dgt_tipo_id=dgt_tipo.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("dgt_tipos.detail", dgt_tipo_id=dgt_tipo.id))


@dgt_tipos.route("/dgt_tipos/recuperar/<dgt_tipo_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(dgt_tipo_id):
    """Recuperar DGT Tipo"""
    dgt_tipo_id = safe_uuid(dgt_tipo_id)
    if dgt_tipo_id == "":
        flash("ID de DGT Tipo inválido", "warning")
        return redirect(url_for("dgt_tipos.list_active"))
    dgt_tipo = DgtTipo.query.get_or_404(dgt_tipo_id)
    if dgt_tipo.estatus == "B":
        dgt_tipo.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado DGT Tipo {dgt_tipo.clave}"),
            url=url_for("dgt_tipos.detail", dgt_tipo_id=dgt_tipo.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("dgt_tipos.detail", dgt_tipo_id=dgt_tipo.id))
