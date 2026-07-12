"""
REDAMS, vistas
"""

import json

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from pjecz_hercules_beta_flask.blueprints.autoridades.models import Autoridad
from pjecz_hercules_beta_flask.blueprints.bitacoras.models import Bitacora
from pjecz_hercules_beta_flask.blueprints.distritos.models import Distrito
from pjecz_hercules_beta_flask.blueprints.modulos.models import Modulo
from pjecz_hercules_beta_flask.blueprints.permisos.models import Permiso
from pjecz_hercules_beta_flask.blueprints.redams.forms import RedamForm
from pjecz_hercules_beta_flask.blueprints.redams.models import Redam
from pjecz_hercules_beta_flask.blueprints.usuarios.decorators import permission_required
from pjecz_hercules_beta_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_hercules_beta_flask.lib.safe_string import safe_clave, safe_expediente, safe_message, safe_string

MODULO = "REDAM"

redams = Blueprint("redams", __name__, template_folder="templates")


@redams.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@redams.route("/redams/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de REDAMs"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Redam.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "autoridad_id" in request.form:
        consulta = consulta.filter_by(autoridad_id=request.form["autoridad_id"])
    if "nombre" in request.form:
        nombre = safe_string(request.form["nombre"], save_enie=True)
        if nombre != "":
            consulta = consulta.filter(Redam.nombre.contains(nombre))
    if "expediente" in request.form:
        try:
            expediente = safe_expediente(request.form["expediente"])
            if expediente != "":
                consulta = consulta.filter(Redam.expediente.contains(expediente))
        except ValueError:
            pass
    # Ordenar y paginar
    registros = consulta.order_by(Redam.nombre).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("redams.detail", redam_id=resultado.id),
                },
                "nombre": resultado.nombre,
                "expediente": resultado.expediente,
                "fecha": resultado.fecha.strftime("%Y-%m-%d 00:00:00"),
                "distrito_nombre_corto": resultado.autoridad.distrito.nombre_corto,
                "autoridad_descripcion_corta": resultado.autoridad.descripcion_corta,
                "observaciones": resultado.observaciones,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@redams.route("/redams")
def list_active():
    """Listado de REDAMs activos"""
    return render_template(
        "redams/list.jinja2",
        estatus="A",
        filtros={"estatus": "A"},
        titulo="REDAMs",
    )


@redams.route("/redams/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de REDAMs inactivos"""
    return render_template(
        "redams/list.jinja2",
        estatus="B",
        filtros={"estatus": "B"},
        titulo="REDAMs inactivos",
    )


@redams.route("/redams/<redam_id>")
def detail(redam_id):
    """Detalle de un REDAM"""
    redam = Redam.query.get_or_404(redam_id)
    return render_template("redams/detail.jinja2", redam=redam)


@redams.route("/redams/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo REDAM"""
    form = RedamForm()
    if form.validate_on_submit():
        autoridad = Autoridad.query.get_or_404(form.autoridad.data)
        redam = Redam(
            autoridad=autoridad,
            nombre=safe_string(form.nombre.data, save_enie=True),
            expediente=safe_expediente(form.expediente.data),
            fecha=form.fecha.data,
            observaciones=safe_string(form.observaciones.data, max_len=1024),
        )
        redam.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo REDAM {redam.nombre}"),
            url=url_for("redams.detail", redam_id=redam.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template(
        "redams/new.jinja2",
        form=form,
        distrito_por_defecto=Distrito.query.filter_by(clave="ND").first(),
        autoridad_por_defecto=Autoridad.query.filter_by(clave="ND").first(),
    )


@redams.route("/redams/edicion/<redam_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(redam_id):
    """Editar REDAM"""
    redam_id = safe_uuid(redam_id)
    if redam_id == "":
        abort(400)
    redam = Redam.query.get_or_404(redam_id)
    form = RedamForm()
    if form.validate_on_submit():
        redam.autoridad = Autoridad.query.get_or_404(form.autoridad.data)
        redam.nombre = safe_string(form.nombre.data, save_enie=True)
        redam.expediente = safe_expediente(form.expediente.data)
        redam.fecha = form.fecha.data
        redam.observaciones = safe_string(form.observaciones.data)
        redam.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editado REDAM {redam.nombre}"),
            url=url_for("redams.detail", redam_id=redam.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.nombre.data = redam.nombre
    form.expediente.data = redam.expediente
    form.fecha.data = redam.fecha
    form.observaciones.data = redam.observaciones
    return render_template("redams/edit.jinja2", form=form, redam=redam)


@redams.route("/redams/eliminar/<redam_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(redam_id):
    """Eliminar REDAM"""
    redam = Redam.query.get_or_404(redam_id)
    if redam.estatus == "A":
        redam.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado REDAM {redam.nombre}"),
            url=url_for("redams.detail", redam_id=redam.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("redams.detail", redam_id=redam.id))


@redams.route("/redams/recuperar/<redam_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(redam_id):
    """Recuperar REDAM"""
    redam = Redam.query.get_or_404(redam_id)
    if redam.estatus == "B":
        redam.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado REDAM {redam.nombre}"),
            url=url_for("redams.detail", redam_id=redam.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("redams.detail", redam_id=redam.id))
