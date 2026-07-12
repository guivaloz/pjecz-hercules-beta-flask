"""
Centros Trabajos, vistas
"""

import json

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from pjecz_hercules_beta_flask.blueprints.bitacoras.models import Bitacora
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
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
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
                "telefono": resultado.telefono,
                "distrito_clave": resultado.distrito.clave,
                "distrito_nombre_corto": resultado.distrito.nombre_corto,
                "domicilio_edificio": resultado.domicilio.edificio,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@centros_trabajos.route("/centros_trabajos")
def list_active():
    """Listado de Centros de Trabajo activos"""
    return render_template(
        "centros_trabajos/list.jinja2",
        estatus="A",
        filtros={"estatus": "A"},
        titulo="Centros de Trabajo",
    )


@centros_trabajos.route("/centros_trabajos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Centros de Trabajo inactivos"""
    return render_template(
        "centros_trabajos/list.jinja2",
        estatus="B",
        filtros={"estatus": "B"},
        titulo="Centros de Trabajo inactivos",
    )


@centros_trabajos.route("/centros_trabajos/<centro_trabajo_id>")
def detail(centro_trabajo_id):
    """Detalle de un Centro de Trabajo"""
    centro_trabajo = CentroTrabajo.query.get_or_404(centro_trabajo_id)
    return render_template("centros_trabajos/detail.jinja2", centro_trabajo=centro_trabajo)
