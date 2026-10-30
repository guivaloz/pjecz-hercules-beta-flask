"""
DGT Plataformas Endpoints, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from pjecz_hercules_beta_flask.blueprints.bitacoras.models import Bitacora
from pjecz_hercules_beta_flask.blueprints.dgt_plataformas.models import DgtPlataforma
from pjecz_hercules_beta_flask.blueprints.dgt_plataformas_endpoints.forms import DgtPlataformaEndpointForm
from pjecz_hercules_beta_flask.blueprints.dgt_plataformas_endpoints.models import DgtPlataformaEndpoint
from pjecz_hercules_beta_flask.blueprints.modulos.models import Modulo
from pjecz_hercules_beta_flask.blueprints.permisos.models import Permiso
from pjecz_hercules_beta_flask.blueprints.usuarios.decorators import permission_required
from pjecz_hercules_beta_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_hercules_beta_flask.lib.safe_string import safe_message, safe_string, safe_uuid

MODULO = "DGT PLATAFORMAS ENDPOINTS"

dgt_plataformas_endpoints = Blueprint("dgt_plataformas_endpoints", __name__, template_folder="templates")


@dgt_plataformas_endpoints.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@dgt_plataformas_endpoints.route("/dgt_plataformas_endpoints/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de DGT Plataformas Endpoints"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = DgtPlataformaEndpoint.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(DgtPlataformaEndpoint.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(DgtPlataformaEndpoint.estatus == "A")
    if "dgt_plataforma_id" in request.form:
        dgt_plataforma_id = safe_uuid(request.form["dgt_plataforma_id"])
        if dgt_plataforma_id != "":
            consulta = consulta.filter(DgtPlataformaEndpoint.dgt_plataforma_id == dgt_plataforma_id)
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], save_enie=True)
        if descripcion != "":
            consulta = consulta.filter(DgtPlataformaEndpoint.descripcion.contains(descripcion))
    if "proposito" in request.form:
        proposito = safe_string(request.form["proposito"])
        if proposito in DgtPlataformaEndpoint.PROPOSITOS:
            consulta = consulta.filter(DgtPlataformaEndpoint.proposito == proposito)
    if "metodo" in request.form:
        metodo = safe_string(request.form["metodo"])
        if metodo in DgtPlataformaEndpoint.METODOS:
            consulta = consulta.filter(DgtPlataformaEndpoint.metodo == metodo)
    # Luego filtrar por columnas de otras tablas
    if "dgt_plataforma_descripcion" in request.form:
        dgt_plataforma_descripcion = safe_string(request.form["dgt_plataforma_descripcion"], save_enie=True)
        if dgt_plataforma_descripcion != "":
            consulta = consulta.join(DgtPlataforma).filter(DgtPlataforma.descripcion.contains(dgt_plataforma_descripcion))
    # Ordenar y paginar
    registros = consulta.order_by(DgtPlataformaEndpoint.descripcion).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for item in registros:
        data.append(
            {
                "detalle": {
                    "descripcion": item.descripcion,
                    "url": url_for("dgt_plataformas_endpoints.detail", dgt_plataforma_endpoint_id=item.id),
                },
                "dgt_plataforma_descripcion": item.dgt_plataforma.descripcion,
                "proposito": item.proposito,
                "metodo": item.metodo,
                "ruta": item.ruta,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@dgt_plataformas_endpoints.route("/dgt_plataformas_endpoints")
def list_active():
    """Listado de DGT Plataformas Endpoints activos"""
    return render_template(
        "dgt_plataformas_endpoints/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="DGT Plataformas Endpoints",
        estatus="A",
    )


@dgt_plataformas_endpoints.route("/dgt_plataformas_endpoints/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de DGT Plataformas Endpoints inactivos"""
    return render_template(
        "dgt_plataformas_endpoints/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="DGT Plataformas Endpoints inactivos",
        estatus="B",
    )


@dgt_plataformas_endpoints.route("/dgt_plataformas_endpoints/<dgt_plataforma_endpoint_id>")
def detail(dgt_plataforma_endpoint_id):
    """Detalle de un DGT Plataforma Endpoint"""
    dgt_plataforma_endpoint_id = safe_uuid(dgt_plataforma_endpoint_id)
    if dgt_plataforma_endpoint_id == "":
        flash("ID de DGT Plataforma Endpoint inválido", "warning")
        return redirect(url_for("dgt_plataformas_endpoints.list_active"))
    dgt_plataforma_endpoint = DgtPlataformaEndpoint.query.get_or_404(dgt_plataforma_endpoint_id)
    return render_template(
        "dgt_plataformas_endpoints/detail.jinja2",
        dgt_plataforma_endpoint=dgt_plataforma_endpoint,
        payload_muestra=json.dumps(dgt_plataforma_endpoint.payload_muestra, indent=2, ensure_ascii=False),
    )


@dgt_plataformas_endpoints.route("/dgt_plataformas_endpoints/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo DGT Plataforma Endpoint"""
    form = DgtPlataformaEndpointForm()
    if form.validate_on_submit():
        # Guardar
        dgt_plataforma_endpoint = DgtPlataformaEndpoint(
            dgt_plataforma_id=form.dgt_plataforma.data,
            descripcion=safe_string(form.descripcion.data, max_len=256, save_enie=True),
            ruta=str(form.ruta.data).strip(),
            proposito=form.proposito.data,
            metodo=form.metodo.data,
            payload_muestra=json.loads(form.payload_muestra.data) if (form.payload_muestra.data or "").strip() else {},
        )
        dgt_plataforma_endpoint.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo DGT Plataforma Endpoint {dgt_plataforma_endpoint.descripcion}"),
            url=url_for("dgt_plataformas_endpoints.detail", dgt_plataforma_endpoint_id=dgt_plataforma_endpoint.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template("dgt_plataformas_endpoints/new.jinja2", form=form)


@dgt_plataformas_endpoints.route("/dgt_plataformas_endpoints/edicion/<dgt_plataforma_endpoint_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(dgt_plataforma_endpoint_id):
    """Editar DGT Plataforma Endpoint"""
    dgt_plataforma_endpoint_id = safe_uuid(dgt_plataforma_endpoint_id)
    if dgt_plataforma_endpoint_id == "":
        flash("ID de DGT Plataforma Endpoint inválido", "warning")
        return redirect(url_for("dgt_plataformas_endpoints.list_active"))
    dgt_plataforma_endpoint = DgtPlataformaEndpoint.query.get_or_404(dgt_plataforma_endpoint_id)
    form = DgtPlataformaEndpointForm()
    if form.validate_on_submit():
        dgt_plataforma_endpoint.dgt_plataforma_id = form.dgt_plataforma.data
        dgt_plataforma_endpoint.descripcion = safe_string(form.descripcion.data, max_len=256, save_enie=True)
        dgt_plataforma_endpoint.ruta = str(form.ruta.data).strip()
        dgt_plataforma_endpoint.proposito = form.proposito.data
        dgt_plataforma_endpoint.metodo = form.metodo.data
        dgt_plataforma_endpoint.payload_muestra = json.loads(form.payload_muestra.data) if (form.payload_muestra.data or "").strip() else {}
        dgt_plataforma_endpoint.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editado DGT Plataforma Endpoint {dgt_plataforma_endpoint.descripcion}"),
            url=url_for("dgt_plataformas_endpoints.detail", dgt_plataforma_endpoint_id=dgt_plataforma_endpoint.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.dgt_plataforma.data = str(dgt_plataforma_endpoint.dgt_plataforma_id)  # Se manda dgt_plataforma_id porque es un select
    form.descripcion.data = dgt_plataforma_endpoint.descripcion
    form.ruta.data = dgt_plataforma_endpoint.ruta
    form.proposito.data = dgt_plataforma_endpoint.proposito
    form.metodo.data = dgt_plataforma_endpoint.metodo
    form.payload_muestra.data = json.dumps(dgt_plataforma_endpoint.payload_muestra, indent=2, ensure_ascii=False)
    return render_template("dgt_plataformas_endpoints/edit.jinja2", form=form, dgt_plataforma_endpoint=dgt_plataforma_endpoint)


@dgt_plataformas_endpoints.route("/dgt_plataformas_endpoints/eliminar/<dgt_plataforma_endpoint_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(dgt_plataforma_endpoint_id):
    """Eliminar DGT Plataforma Endpoint"""
    dgt_plataforma_endpoint_id = safe_uuid(dgt_plataforma_endpoint_id)
    if dgt_plataforma_endpoint_id == "":
        flash("ID de DGT Plataforma Endpoint inválido", "warning")
        return redirect(url_for("dgt_plataformas_endpoints.list_active"))
    dgt_plataforma_endpoint = DgtPlataformaEndpoint.query.get_or_404(dgt_plataforma_endpoint_id)
    if dgt_plataforma_endpoint.estatus == "A":
        dgt_plataforma_endpoint.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado DGT Plataforma Endpoint {dgt_plataforma_endpoint.descripcion}"),
            url=url_for("dgt_plataformas_endpoints.detail", dgt_plataforma_endpoint_id=dgt_plataforma_endpoint.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("dgt_plataformas_endpoints.detail", dgt_plataforma_endpoint_id=dgt_plataforma_endpoint.id))


@dgt_plataformas_endpoints.route("/dgt_plataformas_endpoints/recuperar/<dgt_plataforma_endpoint_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(dgt_plataforma_endpoint_id):
    """Recuperar DGT Plataforma Endpoint"""
    dgt_plataforma_endpoint_id = safe_uuid(dgt_plataforma_endpoint_id)
    if dgt_plataforma_endpoint_id == "":
        flash("ID de DGT Plataforma Endpoint inválido", "warning")
        return redirect(url_for("dgt_plataformas_endpoints.list_active"))
    dgt_plataforma_endpoint = DgtPlataformaEndpoint.query.get_or_404(dgt_plataforma_endpoint_id)
    if dgt_plataforma_endpoint.estatus == "B":
        dgt_plataforma_endpoint.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado DGT Plataforma Endpoint {dgt_plataforma_endpoint.descripcion}"),
            url=url_for("dgt_plataformas_endpoints.detail", dgt_plataforma_endpoint_id=dgt_plataforma_endpoint.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("dgt_plataformas_endpoints.detail", dgt_plataforma_endpoint_id=dgt_plataforma_endpoint.id))
