"""
DGT Depósitos, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from pjecz_hercules_beta_flask.blueprints.bitacoras.models import Bitacora
from pjecz_hercules_beta_flask.blueprints.dgt_depositos.forms import DgtDepositosForm
from pjecz_hercules_beta_flask.blueprints.dgt_depositos.models import DgtDepositos
from pjecz_hercules_beta_flask.blueprints.modulos.models import Modulo
from pjecz_hercules_beta_flask.blueprints.permisos.models import Permiso
from pjecz_hercules_beta_flask.blueprints.usuarios.decorators import permission_required
from pjecz_hercules_beta_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_hercules_beta_flask.lib.safe_string import safe_clave, safe_message, safe_string, safe_uuid

MODULO = "DGT DEPOSITOS"

dgt_depositos = Blueprint("dgt_depositos", __name__, template_folder="templates")


@dgt_depositos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@dgt_depositos.route("/dgt_depositos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de DGT Depósitos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = DgtDepositos.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(DgtDepositos.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(DgtDepositos.estatus == "A")
    if "clave" in request.form:
        try:
            clave = safe_clave(request.form["clave"], max_len=64)
            if clave != "":
                consulta = consulta.filter(DgtDepositos.clave.contains(clave))
        except ValueError:
            pass
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], save_enie=True)
        if descripcion != "":
            consulta = consulta.filter(DgtDepositos.descripcion.contains(descripcion))
    # Ordenar y paginar
    registros = consulta.order_by(DgtDepositos.clave).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for item in registros:
        data.append(
            {
                "detalle": {
                    "clave": item.clave,
                    "url": url_for("dgt_depositos.detail", dgt_deposito_id=item.id),
                },
                "descripcion": item.descripcion,
                "proposito": item.proposito,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@dgt_depositos.route("/dgt_depositos")
def list_active():
    """Listado de DGT Depósitos activos"""
    return render_template(
        "dgt_depositos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="DGT Depósitos",
        estatus="A",
    )


@dgt_depositos.route("/dgt_depositos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de DGT Depósitos inactivos"""
    return render_template(
        "dgt_depositos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="DGT Depósitos inactivos",
        estatus="B",
    )


@dgt_depositos.route("/dgt_depositos/<dgt_deposito_id>")
def detail(dgt_deposito_id):
    """Detalle de un DGT Depósito"""
    dgt_deposito_id = safe_uuid(dgt_deposito_id)
    if dgt_deposito_id == "":
        flash("ID de DGT Depósito inválido", "warning")
        return redirect(url_for("dgt_depositos.list_active"))
    dgt_deposito = DgtDepositos.query.get_or_404(dgt_deposito_id)
    # Según el propósito del depósito, elegir el blueprint del que se tomarán las gráficas
    graficas_blueprint = ""
    if dgt_deposito.proposito == "ENTREGAS" and current_user.can_view("DGT ENTREGAS"):
        graficas_blueprint = "dgt_entregas"
    elif dgt_deposito.proposito == "DIGITALIZACIONES" and current_user.can_view("DGT DIGITALIZACIONES"):
        graficas_blueprint = "dgt_digitalizaciones"
    return render_template(
        "dgt_depositos/detail.jinja2",
        dgt_deposito=dgt_deposito,
        graficas_blueprint=graficas_blueprint,
    )


@dgt_depositos.route("/dgt_depositos/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo DGT Depósito"""
    form = DgtDepositosForm()
    if form.validate_on_submit():
        clave = safe_clave(form.clave.data, max_len=64)
        descripcion = safe_string(form.descripcion.data, save_enie=True)
        # Validar que la clave no se repita
        if DgtDepositos.query.filter_by(clave=clave).first():
            flash("Esa clave ya está en uso. Debe de ser única.", "warning")
            return render_template("dgt_depositos/new.jinja2", form=form)
        # Guardar
        dgt_deposito = DgtDepositos(
            clave=clave,
            descripcion=descripcion,
            proposito=form.proposito.data,
        )
        dgt_deposito.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo DGT Depósito {dgt_deposito.clave}"),
            url=url_for("dgt_depositos.detail", dgt_deposito_id=dgt_deposito.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template("dgt_depositos/new.jinja2", form=form)


@dgt_depositos.route("/dgt_depositos/edicion/<dgt_deposito_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(dgt_deposito_id):
    """Editar DGT Depósito"""
    dgt_deposito_id = safe_uuid(dgt_deposito_id)
    if dgt_deposito_id == "":
        flash("ID de DGT Depósito inválido", "warning")
        return redirect(url_for("dgt_depositos.list_active"))
    dgt_deposito = DgtDepositos.query.get_or_404(dgt_deposito_id)
    form = DgtDepositosForm()
    if form.validate_on_submit():
        es_valido = True
        # Si cambia la clave verificar que no este en uso
        clave = safe_clave(form.clave.data, max_len=64)
        if dgt_deposito.clave != clave:
            dgt_deposito_existente = DgtDepositos.query.filter_by(clave=clave).first()
            if dgt_deposito_existente and dgt_deposito_existente.id != dgt_deposito.id:
                es_valido = False
                flash("La clave ya está en uso. Debe de ser única.", "warning")
        # Si es valido actualizar
        if es_valido:
            dgt_deposito.clave = clave
            dgt_deposito.descripcion = safe_string(form.descripcion.data, save_enie=True)
            dgt_deposito.proposito = form.proposito.data
            dgt_deposito.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado DGT Depósito {dgt_deposito.clave}"),
                url=url_for("dgt_depositos.detail", dgt_deposito_id=dgt_deposito.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.clave.data = dgt_deposito.clave
    form.descripcion.data = dgt_deposito.descripcion
    form.proposito.data = dgt_deposito.proposito
    return render_template("dgt_depositos/edit.jinja2", form=form, dgt_deposito=dgt_deposito)


@dgt_depositos.route("/dgt_depositos/eliminar/<dgt_deposito_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(dgt_deposito_id):
    """Eliminar DGT Depósito"""
    dgt_deposito_id = safe_uuid(dgt_deposito_id)
    if dgt_deposito_id == "":
        flash("ID de DGT Depósito inválido", "warning")
        return redirect(url_for("dgt_depositos.list_active"))
    dgt_deposito = DgtDepositos.query.get_or_404(dgt_deposito_id)
    if dgt_deposito.estatus == "A":
        dgt_deposito.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado DGT Depósito {dgt_deposito.clave}"),
            url=url_for("dgt_depositos.detail", dgt_deposito_id=dgt_deposito.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("dgt_depositos.detail", dgt_deposito_id=dgt_deposito.id))


@dgt_depositos.route("/dgt_depositos/recuperar/<dgt_deposito_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(dgt_deposito_id):
    """Recuperar DGT Depósito"""
    dgt_deposito_id = safe_uuid(dgt_deposito_id)
    if dgt_deposito_id == "":
        flash("ID de DGT Depósito inválido", "warning")
        return redirect(url_for("dgt_depositos.list_active"))
    dgt_deposito = DgtDepositos.query.get_or_404(dgt_deposito_id)
    if dgt_deposito.estatus == "B":
        dgt_deposito.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado DGT Depósito {dgt_deposito.clave}"),
            url=url_for("dgt_depositos.detail", dgt_deposito_id=dgt_deposito.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("dgt_depositos.detail", dgt_deposito_id=dgt_deposito.id))
