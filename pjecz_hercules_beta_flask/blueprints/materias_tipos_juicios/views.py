"""
Materias Tipos de Juicios, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from pjecz_hercules_beta_flask.blueprints.bitacoras.models import Bitacora
from pjecz_hercules_beta_flask.blueprints.materias.models import Materia
from pjecz_hercules_beta_flask.blueprints.materias_tipos_juicios.forms import MateriaTipoJuicioForm
from pjecz_hercules_beta_flask.blueprints.materias_tipos_juicios.models import MateriaTipoJuicio
from pjecz_hercules_beta_flask.blueprints.modulos.models import Modulo
from pjecz_hercules_beta_flask.blueprints.permisos.models import Permiso
from pjecz_hercules_beta_flask.blueprints.usuarios.decorators import permission_required
from pjecz_hercules_beta_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_hercules_beta_flask.lib.safe_string import safe_message, safe_string

MODULO = "MATERIAS TIPOS JUICIOS"

materias_tipos_juicios = Blueprint("materias_tipos_juicios", __name__, template_folder="templates")


@materias_tipos_juicios.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@materias_tipos_juicios.route("/materias_tipos_juicios/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Materias Tipos Juicios"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = MateriaTipoJuicio.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(MateriaTipoJuicio.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(MateriaTipoJuicio.estatus == "A")
    if "materia_id" in request.form:
        consulta = consulta.filter(MateriaTipoJuicio.materia_id == request.form["materia_id"])
    elif "materia_nombre" in request.form:
        materia_nombre = safe_string(request.form["materia_nombre"], save_enie=True)
        if materia_nombre != "":
            consulta = consulta.join(Materia).filter(Materia.nombre.contains(materia_nombre))
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], save_enie=True)
        if descripcion != "":
            consulta = consulta.filter(MateriaTipoJuicio.descripcion.contains(descripcion))
    # Ordenar y paginar
    registros = consulta.order_by(MateriaTipoJuicio.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "descripcion": resultado.descripcion,
                    "url": url_for("materias_tipos_juicios.detail", materia_tipo_juicio_id=resultado.id),
                },
                "materia_nombre": resultado.materia.nombre,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@materias_tipos_juicios.route("/materias_tipos_juicios")
def list_active():
    """Listado de Materias Tipos Juicios activos"""
    return render_template(
        "materias_tipos_juicios/list.jinja2",
        estatus="A",
        filtros={"estatus": "A"},
        titulo="Tipos de Juicios",
    )


@materias_tipos_juicios.route("/materias_tipos_juicios/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Materias Tipos Juicios inactivos"""
    return render_template(
        "materias_tipos_juicios/list.jinja2",
        estatus="B",
        filtros={"estatus": "B"},
        titulo="Tipos de Juicios inactivos",
    )


@materias_tipos_juicios.route("/materias_tipos_juicios/<int:materia_tipo_juicio_id>")
def detail(materia_tipo_juicio_id):
    """Detalle de un Materia Tipo Juicio"""
    materia_tipo_juicio = MateriaTipoJuicio.query.get_or_404(materia_tipo_juicio_id)
    return render_template("materias_tipos_juicios/detail.jinja2", materia_tipo_juicio=materia_tipo_juicio)


@materias_tipos_juicios.route("/materias_tipos_juicios/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Materia Tipo de Juicio"""
    form = MateriaTipoJuicioForm()
    if form.validate_on_submit():
        materia_tipo_juicio = MateriaTipoJuicio(
            materia_id=form.materia.data,
            descripcion=safe_string(form.descripcion.data),
        )
        materia_tipo_juicio.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(
                f"Nuevo Tipo de Juicio {materia_tipo_juicio.descripcion} en {materia_tipo_juicio.materia.nombre}"
            ),
            url=url_for("materias_tipos_juicios.detail", materia_tipo_juicio_id=materia_tipo_juicio.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template("materias_tipos_juicios/new.jinja2", form=form)


@materias_tipos_juicios.route("/materias_tipos_juicios/edicion/<int:materia_tipo_juicio_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(materia_tipo_juicio_id):
    """Editar Materia Tipo de Juicio"""
    materia_tipo_juicio = MateriaTipoJuicio.query.get_or_404(materia_tipo_juicio_id)
    form = MateriaTipoJuicioForm()
    if form.validate_on_submit():
        materia_tipo_juicio.materia_id = form.materia.data
        materia_tipo_juicio.descripcion = safe_string(form.descripcion.data)
        materia_tipo_juicio.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(
                f"Editado Materia Tipo de Juicio {materia_tipo_juicio.descripcion} en {materia_tipo_juicio.materia.nombre}"
            ),
            url=url_for("materias_tipos_juicios.detail", materia_tipo_juicio_id=materia_tipo_juicio.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.materia.data = materia_tipo_juicio.materia_id
    form.descripcion.data = materia_tipo_juicio.descripcion
    return render_template("materias_tipos_juicios/edit.jinja2", form=form, materia_tipo_juicio=materia_tipo_juicio)


@materias_tipos_juicios.route("/materias_tipos_juicios/eliminar/<int:materia_tipo_juicio_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(materia_tipo_juicio_id):
    """Eliminar Tipo de Juicio"""
    materia_tipo_juicio = MateriaTipoJuicio.query.get_or_404(materia_tipo_juicio_id)
    if materia_tipo_juicio.estatus == "A":
        materia_tipo_juicio.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Tipo de Juicio {materia_tipo_juicio.descripcion}"),
            url=url_for("materias_tipos_juicios.detail", materia_tipo_juicio_id=materia_tipo_juicio.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("materias_tipos_juicios.detail", materia_tipo_juicio_id=materia_tipo_juicio.id))


@materias_tipos_juicios.route("/materias_tipos_juicios/recuperar/<int:materia_tipo_juicio_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(materia_tipo_juicio_id):
    """Recuperar Tipo de Juicio"""
    materia_tipo_juicio = MateriaTipoJuicio.query.get_or_404(materia_tipo_juicio_id)
    if materia_tipo_juicio.estatus == "B":
        materia_tipo_juicio.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Tipo de Juicio {materia_tipo_juicio.descripcion}"),
            url=url_for("materias_tipos_juicios.detail", materia_tipo_juicio_id=materia_tipo_juicio.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("materias_tipos_juicios.detail", materia_tipo_juicio_id=materia_tipo_juicio.id))


@materias_tipos_juicios.route("/materias_tipos_juicios/select_json", methods=["GET", "POST"])
def select_json():
    """Proporcionar el JSON con los ids, descripciones para elegir con un select"""
    # Consultar
    consulta = MateriaTipoJuicio.query.filter_by(estatus="A")
    # Filtrar
    if "materia_id" in request.args:
        materia_id = request.args["materia_id"]
        consulta = consulta.filter_by(materia_id=materia_id)
    # Ordenar
    consulta = consulta.order_by(MateriaTipoJuicio.descripcion)
    # Elaborar datos para Select
    data = []
    for resultado in consulta.all():
        data.append(
            {
                "id": resultado.id,
                "descripcion": resultado.descripcion,
            }
        )
    # Entregar JSON
    return json.dumps(data)
