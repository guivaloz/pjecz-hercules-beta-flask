"""
DGT Plataformas Endpoints Bitácoras, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from pjecz_hercules_beta_flask.blueprints.dgt_plataformas_endpoints.models import DgtPlataformaEndpoint
from pjecz_hercules_beta_flask.blueprints.dgt_plataformas_endpoints_bitacoras.models import DgtPlataformaEndpointBitacora
from pjecz_hercules_beta_flask.blueprints.permisos.models import Permiso
from pjecz_hercules_beta_flask.blueprints.usuarios.decorators import permission_required
from pjecz_hercules_beta_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_hercules_beta_flask.lib.safe_string import safe_string, safe_uuid

MODULO = "DGT PLATAFORMAS ENDPOINTS BITACORAS"

dgt_plataformas_endpoints_bitacoras = Blueprint("dgt_plataformas_endpoints_bitacoras", __name__, template_folder="templates")


@dgt_plataformas_endpoints_bitacoras.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@dgt_plataformas_endpoints_bitacoras.route("/dgt_plataformas_endpoints_bitacoras/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de DGT Plataformas Endpoints Bitácoras"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = DgtPlataformaEndpointBitacora.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(DgtPlataformaEndpointBitacora.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(DgtPlataformaEndpointBitacora.estatus == "A")
    if "dgt_plataforma_endpoint_id" in request.form:
        dgt_plataforma_endpoint_id = safe_uuid(request.form["dgt_plataforma_endpoint_id"])
        if dgt_plataforma_endpoint_id != "":
            consulta = consulta.filter(DgtPlataformaEndpointBitacora.dgt_plataforma_endpoint_id == dgt_plataforma_endpoint_id)
    if "respuesta_exitosa" in request.form:
        if request.form["respuesta_exitosa"] == "1":
            consulta = consulta.filter(DgtPlataformaEndpointBitacora.respuesta_exitosa.is_(True))
        elif request.form["respuesta_exitosa"] == "0":
            consulta = consulta.filter(DgtPlataformaEndpointBitacora.respuesta_exitosa.is_(False))
    # Luego filtrar por columnas de otras tablas
    if "dgt_plataforma_endpoint_descripcion" in request.form:
        dgt_plataforma_endpoint_descripcion = safe_string(request.form["dgt_plataforma_endpoint_descripcion"], save_enie=True)
        if dgt_plataforma_endpoint_descripcion != "":
            consulta = consulta.join(DgtPlataformaEndpoint).filter(
                DgtPlataformaEndpoint.descripcion.contains(dgt_plataforma_endpoint_descripcion)
            )
    # Ordenar y paginar
    registros = consulta.order_by(DgtPlataformaEndpointBitacora.creado.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for item in registros:
        data.append(
            {
                "detalle": {
                    "creado": item.creado.strftime("%Y-%m-%d %H:%M:%S") if item.creado else "",
                    "url": url_for("dgt_plataformas_endpoints_bitacoras.detail", dgt_plataforma_endpoint_bitacora_id=item.id),
                },
                "dgt_plataforma_endpoint_descripcion": item.dgt_plataforma_endpoint.descripcion,
                "respuesta_codigo": item.respuesta_codigo,
                "respuesta_exitosa": item.respuesta_exitosa,
                "respuesta_mensaje": item.respuesta_mensaje,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@dgt_plataformas_endpoints_bitacoras.route("/dgt_plataformas_endpoints_bitacoras")
def list_active():
    """Listado de DGT Plataformas Endpoints Bitácoras activas"""
    return render_template(
        "dgt_plataformas_endpoints_bitacoras/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="DGT Plataformas Endpoints Bitácoras",
        estatus="A",
    )


@dgt_plataformas_endpoints_bitacoras.route("/dgt_plataformas_endpoints_bitacoras/<dgt_plataforma_endpoint_bitacora_id>")
def detail(dgt_plataforma_endpoint_bitacora_id):
    """Detalle de una DGT Plataforma Bitácora"""
    dgt_plataforma_endpoint_bitacora_id = safe_uuid(dgt_plataforma_endpoint_bitacora_id)
    if dgt_plataforma_endpoint_bitacora_id == "":
        flash("ID de DGT Plataforma Bitácora inválido", "warning")
        return redirect(url_for("dgt_plataformas_endpoints_bitacoras.list_active"))
    dgt_plataforma_endpoint_bitacora = DgtPlataformaEndpointBitacora.query.get_or_404(dgt_plataforma_endpoint_bitacora_id)
    return render_template(
        "dgt_plataformas_endpoints_bitacoras/detail.jinja2",
        dgt_plataforma_endpoint_bitacora=dgt_plataforma_endpoint_bitacora,
        creado=dgt_plataforma_endpoint_bitacora.creado.strftime("%Y-%m-%d %H:%M:%S") if dgt_plataforma_endpoint_bitacora.creado else "",
        payload=json.dumps(dgt_plataforma_endpoint_bitacora.payload, indent=2, ensure_ascii=False),
        respuesta_datos=json.dumps(dgt_plataforma_endpoint_bitacora.respuesta_datos, indent=2, ensure_ascii=False),
    )
