"""
DGT Digitalizaciones Bitácoras, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from pjecz_hercules_beta_flask.blueprints.dgt_digitalizaciones_bitacoras.models import DgtDigitalizacionBitacora
from pjecz_hercules_beta_flask.blueprints.permisos.models import Permiso
from pjecz_hercules_beta_flask.blueprints.usuarios.decorators import permission_required
from pjecz_hercules_beta_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_hercules_beta_flask.lib.safe_string import safe_string, safe_uuid

MODULO = "DGT DIGITALIZACIONES BITACORAS"

dgt_digitalizaciones_bitacoras = Blueprint("dgt_digitalizaciones_bitacoras", __name__, template_folder="templates")


@dgt_digitalizaciones_bitacoras.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@dgt_digitalizaciones_bitacoras.route("/dgt_digitalizaciones_bitacoras/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de DGT Digitalizaciones Bitácoras"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = DgtDigitalizacionBitacora.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(DgtDigitalizacionBitacora.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(DgtDigitalizacionBitacora.estatus == "A")
    if "dgt_digitalizacion_id" in request.form:
        consulta = consulta.filter(DgtDigitalizacionBitacora.dgt_digitalizacion_id == request.form["dgt_digitalizacion_id"])
    if "evento" in request.form:
        evento = safe_string(request.form["evento"])
        if evento != "":
            consulta = consulta.filter(DgtDigitalizacionBitacora.evento.contains(evento))
    # Ordenar y paginar
    registros = consulta.order_by(DgtDigitalizacionBitacora.creado.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for item in registros:
        data.append(
            {
                "detalle": {
                    "evento": item.evento,
                    "url": url_for(
                        "dgt_digitalizaciones_bitacoras.detail",
                        dgt_digitalizacion_bitacora_id=item.id,
                    ),
                },
                "archivo_tamano": item.archivo_tamano,
                "archivo_actualizado": item.archivo_actualizado.strftime("%Y-%m-%d %H:%M") if item.archivo_actualizado else "",
                "creado": item.creado.strftime("%Y-%m-%d %H:%M") if item.creado else "",
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@dgt_digitalizaciones_bitacoras.route("/dgt_digitalizaciones_bitacoras")
def list_active():
    """Listado de DGT Digitalizaciones Bitácoras activas"""
    return render_template(
        "dgt_digitalizaciones_bitacoras/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="DGT Digitalizaciones Bitácoras",
        estatus="A",
    )


@dgt_digitalizaciones_bitacoras.route("/dgt_digitalizaciones_bitacoras/<dgt_digitalizacion_bitacora_id>")
def detail(dgt_digitalizacion_bitacora_id):
    """Detalle de una DGT Digitalización Bitácora"""
    dgt_digitalizacion_bitacora_id = safe_uuid(dgt_digitalizacion_bitacora_id)
    if dgt_digitalizacion_bitacora_id == "":
        flash("ID de DGT Digitalización Bitácora inválido", "warning")
        return redirect(url_for("dgt_digitalizaciones_bitacoras.list_active"))
    dgt_digitalizacion_bitacora = DgtDigitalizacionBitacora.query.get_or_404(dgt_digitalizacion_bitacora_id)
    return render_template("dgt_digitalizaciones_bitacoras/detail.jinja2", dgt_digitalizacion_bitacora=dgt_digitalizacion_bitacora)
