"""
Centros Trabajos, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from pjecz_hercules_beta_flask.blueprints.bitacoras.models import Bitacora
from pjecz_hercules_beta_flask.blueprints.centros_trabajos.forms import CentroTrabajoForm
from pjecz_hercules_beta_flask.blueprints.centros_trabajos.models import CentroTrabajo
from pjecz_hercules_beta_flask.blueprints.modulos.models import Modulo
from pjecz_hercules_beta_flask.blueprints.permisos.models import Permiso
from pjecz_hercules_beta_flask.blueprints.usuarios.decorators import permission_required
from pjecz_hercules_beta_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_hercules_beta_flask.lib.safe_string import safe_clave, safe_message, safe_string

MODULO = "CENTROS TRABAJOS"

centros_trabajos = Blueprint("centros_trabajos", __name__, template_folder="templates")


@centros_trabajos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@centros_trabajos.route("/centros_trabajos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Centros de Trabajo"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = CentroTrabajo.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(CentroTrabajo.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(CentroTrabajo.estatus == "A")
    if "distrito_id" in request.form:
        try:
            distrito_id = int(request.form["distrito_id"])
            consulta = consulta.filter(CentroTrabajo.distrito_id == distrito_id)
        except ValueError:
            pass
    if "domicilio_id" in request.form:
        try:
            domicilio_id = int(request.form["domicilio_id"])
            consulta = consulta.filter(CentroTrabajo.domicilio_id == domicilio_id)
        except ValueError:
            pass
    if "clave" in request.form:
        try:
            clave = safe_clave(request.form["clave"])
            if clave != "":
                consulta = consulta.filter(CentroTrabajo.clave.contains(clave))
        except ValueError:
            pass
    if "nombre" in request.form:
        nombre = safe_string(request.form["nombre"], save_enie=True)
        if nombre != "":
            consulta = consulta.filter(CentroTrabajo.nombre.contains(nombre))
    # Ordenar y paginar
    registros = consulta.order_by(CentroTrabajo.clave).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "clave": resultado.clave,
                    "url": url_for("centros_trabajos.detail", centro_trabajo_id=resultado.id),
                },
                "nombre": resultado.nombre,
                "distrito_nombre_corto": resultado.distrito.nombre_corto,
                "domicilio_edificio": resultado.domicilio.edificio,
                "telefono": resultado.telefono,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@centros_trabajos.route("/centros_trabajos")
def list_active():
    """Listado de Centros de Trabajo activos"""
    return render_template(
        "centros_trabajos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Centros de Trabajo",
        estatus="A",
    )


@centros_trabajos.route("/centros_trabajos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Centros de Trabajo inactivos"""
    return render_template(
        "centros_trabajos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Centros de Trabajo inactivos",
        estatus="B",
    )


@centros_trabajos.route("/centros_trabajos/<int:centro_trabajo_id>")
def detail(centro_trabajo_id):
    """Detalle de un Centro de Trabajo"""
    centro_trabajo = CentroTrabajo.query.get_or_404(centro_trabajo_id)
    return render_template("centros_trabajos/detail.jinja2", centro_trabajo=centro_trabajo)


@centros_trabajos.route("/centros_trabajos/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Centro de Trabajo"""
    form = CentroTrabajoForm()
    if form.validate_on_submit():
        es_valido = True
        # Validar que la clave no se repita
        clave = safe_clave(form.clave.data)
        if CentroTrabajo.query.filter_by(clave=clave).first():
            flash("La clave ya está en uso. Debe de ser única.", "warning")
            es_valido = False
        # Si es válido, guardar
        if es_valido is True:
            centro_trabajo = CentroTrabajo(
                clave=clave,
                nombre=safe_string(form.nombre.data, save_enie=True),
                distrito_id=form.distrito.data,
                domicilio_id=form.domicilio.data,
                telefono=safe_string(form.telefono.data, max_len=48),
            )
            centro_trabajo.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nuevo Centro de Trabajo {centro_trabajo.clave}"),
                url=url_for("centros_trabajos.detail", centro_trabajo_id=centro_trabajo.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    return render_template("centros_trabajos/new.jinja2", form=form)


@centros_trabajos.route("/centros_trabajos/edicion/<int:centro_trabajo_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(centro_trabajo_id):
    """Editar Centro de Trabajo"""
    centro_trabajo = CentroTrabajo.query.get_or_404(centro_trabajo_id)
    form = CentroTrabajoForm()
    if form.validate_on_submit():
        es_valido = True
        # Si cambia la clave verificar que no este en uso
        clave = safe_clave(form.clave.data)
        if centro_trabajo.clave != clave:
            centro_trabajo_existente = CentroTrabajo.query.filter_by(clave=clave).first()
            if centro_trabajo_existente and centro_trabajo_existente.id != centro_trabajo.id:
                es_valido = False
                flash("La clave ya está en uso. Debe de ser única.", "warning")
        # Si es válido, actualizar
        if es_valido:
            centro_trabajo.clave = clave
            centro_trabajo.nombre = safe_string(form.nombre.data, save_enie=True)
            centro_trabajo.distrito_id = form.distrito.data
            centro_trabajo.domicilio_id = form.domicilio.data
            centro_trabajo.telefono = safe_string(form.telefono.data, max_len=48)
            centro_trabajo.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Centro de Trabajo {centro_trabajo.clave}"),
                url=url_for("centros_trabajos.detail", centro_trabajo_id=centro_trabajo.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.clave.data = centro_trabajo.clave
    form.nombre.data = centro_trabajo.nombre
    form.distrito.data = centro_trabajo.distrito_id  # Se manda distrito_id porque es un select
    form.domicilio.data = centro_trabajo.domicilio_id  # Se manda domicilio_id porque es un select
    form.telefono.data = centro_trabajo.telefono
    return render_template("centros_trabajos/edit.jinja2", form=form, centro_trabajo=centro_trabajo)


@centros_trabajos.route("/centros_trabajos/eliminar/<int:centro_trabajo_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(centro_trabajo_id):
    """Eliminar Centro de Trabajo"""
    centro_trabajo = CentroTrabajo.query.get_or_404(centro_trabajo_id)
    if centro_trabajo.estatus == "A":
        centro_trabajo.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Centro de Trabajo {centro_trabajo.clave}"),
            url=url_for("centros_trabajos.detail", centro_trabajo_id=centro_trabajo.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("centros_trabajos.detail", centro_trabajo_id=centro_trabajo.id))


@centros_trabajos.route("/centros_trabajos/recuperar/<int:centro_trabajo_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(centro_trabajo_id):
    """Recuperar Centro de Trabajo"""
    centro_trabajo = CentroTrabajo.query.get_or_404(centro_trabajo_id)
    if centro_trabajo.estatus == "B":
        centro_trabajo.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Centro de Trabajo {centro_trabajo.clave}"),
            url=url_for("centros_trabajos.detail", centro_trabajo_id=centro_trabajo.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("centros_trabajos.detail", centro_trabajo_id=centro_trabajo.id))
