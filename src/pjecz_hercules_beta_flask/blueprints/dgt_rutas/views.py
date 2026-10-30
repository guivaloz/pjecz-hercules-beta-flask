"""
DGT Rutas, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from pjecz_hercules_beta_flask.blueprints.bitacoras.models import Bitacora
from pjecz_hercules_beta_flask.blueprints.dgt_depositos.models import DgtDepositos
from pjecz_hercules_beta_flask.blueprints.dgt_digitalizaciones_bitacoras.models import DgtDigitalizacionBitacora
from pjecz_hercules_beta_flask.blueprints.dgt_entregas_bitacoras.models import DgtEntregaBitacora
from pjecz_hercules_beta_flask.blueprints.dgt_rutas.forms import DgtRutaForm
from pjecz_hercules_beta_flask.blueprints.dgt_rutas.models import DgtRuta
from pjecz_hercules_beta_flask.blueprints.dgt_tipos.models import DgtTipo
from pjecz_hercules_beta_flask.blueprints.modulos.models import Modulo
from pjecz_hercules_beta_flask.blueprints.permisos.models import Permiso
from pjecz_hercules_beta_flask.blueprints.usuarios.decorators import permission_required
from pjecz_hercules_beta_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_hercules_beta_flask.lib.safe_string import safe_clave, safe_message, safe_string, safe_uuid

MODULO = "DGT RUTAS"

dgt_rutas = Blueprint("dgt_rutas", __name__, template_folder="templates")


@dgt_rutas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@dgt_rutas.route("/dgt_rutas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de DGT Rutas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = DgtRuta.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(DgtRuta.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(DgtRuta.estatus == "A")
    if "clave" in request.form:
        try:
            clave = safe_clave(request.form["clave"], max_len=64)
            if clave != "":
                consulta = consulta.filter(DgtRuta.clave.contains(clave))
        except ValueError:
            pass
    if "autoridad_clave" in request.form:
        try:
            autoridad_clave = safe_clave(request.form["autoridad_clave"])
            if autoridad_clave != "":
                consulta = consulta.filter(DgtRuta.autoridad_clave.contains(autoridad_clave))
        except ValueError:
            pass
    # Luego filtrar por columnas de otras tablas
    if "dgt_deposito_id" in request.form:
        consulta = consulta.filter(DgtRuta.dgt_deposito_id == request.form["dgt_deposito_id"])
    if "dgt_tipo_id" in request.form:
        consulta = consulta.filter(DgtRuta.dgt_tipo_id == request.form["dgt_tipo_id"])
    if "dgt_deposito_clave" in request.form:
        try:
            dgt_deposito_clave = safe_clave(request.form["dgt_deposito_clave"], max_len=64)
            if dgt_deposito_clave != "":
                consulta = consulta.join(DgtDepositos).filter(DgtDepositos.clave.contains(dgt_deposito_clave))
        except ValueError:
            pass
    if "dgt_tipo_clave" in request.form:
        try:
            dgt_tipo_clave = safe_clave(request.form["dgt_tipo_clave"], max_len=64)
            if dgt_tipo_clave != "":
                consulta = consulta.join(DgtTipo).filter(DgtTipo.clave.contains(dgt_tipo_clave))
        except ValueError:
            pass
    # Ordenar y paginar
    registros = consulta.order_by(DgtRuta.clave).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for item in registros:
        data.append(
            {
                "detalle": {
                    "clave": item.clave,
                    "url": url_for("dgt_rutas.detail", dgt_ruta_id=item.id),
                },
                "dgt_deposito_clave": item.dgt_deposito.clave,
                "autoridad_clave": item.autoridad_clave,
                "dgt_tipo_clave": item.dgt_tipo.clave,
                "directorio": item.directorio,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@dgt_rutas.route("/dgt_rutas")
def list_active():
    """Listado de DGT Rutas activas"""
    return render_template(
        "dgt_rutas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="DGT Rutas",
        estatus="A",
    )


@dgt_rutas.route("/dgt_rutas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de DGT Rutas inactivas"""
    return render_template(
        "dgt_rutas/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="DGT Rutas inactivas",
        estatus="B",
    )


@dgt_rutas.route("/dgt_rutas/<dgt_ruta_id>")
def detail(dgt_ruta_id):
    """Detalle de una DGT Ruta"""
    dgt_ruta_id = safe_uuid(dgt_ruta_id)
    if dgt_ruta_id == "":
        flash("ID de DGT Ruta inválido", "warning")
        return redirect(url_for("dgt_rutas.list_active"))
    dgt_ruta = DgtRuta.query.get_or_404(dgt_ruta_id)
    return render_template(
        "dgt_rutas/detail.jinja2",
        dgt_ruta=dgt_ruta,
        dgt_digitalizaciones_eventos=DgtDigitalizacionBitacora.EVENTOS,
        dgt_entregas_eventos=DgtEntregaBitacora.EVENTOS,
    )


@dgt_rutas.route("/dgt_rutas/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nueva DGT Ruta"""
    form = DgtRutaForm()
    if form.validate_on_submit():
        clave = safe_clave(form.clave.data, max_len=64)
        autoridad_clave = safe_clave(form.autoridad_clave.data)
        directorio = safe_string(form.directorio.data, max_len=512, save_enie=True, to_uppercase=False)
        # Validar que la clave no se repita
        if DgtRuta.query.filter_by(clave=clave).first():
            flash("Esa clave ya está en uso. Debe de ser única.", "warning")
            return render_template("dgt_rutas/new.jinja2", form=form)
        # Guardar
        dgt_ruta = DgtRuta(
            dgt_deposito_id=form.dgt_deposito.data,
            dgt_tipo_id=form.dgt_tipo.data,
            clave=clave,
            directorio=directorio,
            autoridad_clave=autoridad_clave,
        )
        dgt_ruta.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nueva DGT Ruta {dgt_ruta.clave}"),
            url=url_for("dgt_rutas.detail", dgt_ruta_id=dgt_ruta.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template("dgt_rutas/new.jinja2", form=form)


@dgt_rutas.route("/dgt_rutas/edicion/<dgt_ruta_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(dgt_ruta_id):
    """Editar DGT Ruta"""
    dgt_ruta_id = safe_uuid(dgt_ruta_id)
    if dgt_ruta_id == "":
        flash("ID de DGT Ruta inválido", "warning")
        return redirect(url_for("dgt_rutas.list_active"))
    dgt_ruta = DgtRuta.query.get_or_404(dgt_ruta_id)
    form = DgtRutaForm()
    if form.validate_on_submit():
        es_valido = True
        # Si cambia la clave verificar que no este en uso
        clave = safe_clave(form.clave.data, max_len=64)
        if dgt_ruta.clave != clave:
            dgt_ruta_existente = DgtRuta.query.filter_by(clave=clave).first()
            if dgt_ruta_existente and dgt_ruta_existente.id != dgt_ruta.id:
                es_valido = False
                flash("La clave ya está en uso. Debe de ser única.", "warning")
        # Si es valido actualizar
        if es_valido:
            dgt_ruta.dgt_deposito_id = form.dgt_deposito.data
            dgt_ruta.dgt_tipo_id = form.dgt_tipo.data
            dgt_ruta.clave = clave
            dgt_ruta.autoridad_clave = safe_clave(form.autoridad_clave.data)
            dgt_ruta.directorio = safe_string(form.directorio.data, max_len=512, save_enie=True, to_uppercase=False)
            dgt_ruta.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editada DGT Ruta {dgt_ruta.clave}"),
                url=url_for("dgt_rutas.detail", dgt_ruta_id=dgt_ruta.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.dgt_deposito.data = str(dgt_ruta.dgt_deposito_id)  # Se manda dgt_deposito_id porque es un select
    form.dgt_tipo.data = str(dgt_ruta.dgt_tipo_id)  # Se manda dgt_tipo_id porque es un select
    form.clave.data = dgt_ruta.clave
    form.autoridad_clave.data = dgt_ruta.autoridad_clave
    form.directorio.data = dgt_ruta.directorio
    return render_template("dgt_rutas/edit.jinja2", form=form, dgt_ruta=dgt_ruta)


@dgt_rutas.route("/dgt_rutas/eliminar/<dgt_ruta_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(dgt_ruta_id):
    """Eliminar DGT Ruta"""
    dgt_ruta_id = safe_uuid(dgt_ruta_id)
    if dgt_ruta_id == "":
        flash("ID de DGT Ruta inválido", "warning")
        return redirect(url_for("dgt_rutas.list_active"))
    dgt_ruta = DgtRuta.query.get_or_404(dgt_ruta_id)
    if dgt_ruta.estatus == "A":
        dgt_ruta.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminada DGT Ruta {dgt_ruta.clave}"),
            url=url_for("dgt_rutas.detail", dgt_ruta_id=dgt_ruta.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("dgt_rutas.detail", dgt_ruta_id=dgt_ruta.id))


@dgt_rutas.route("/dgt_rutas/recuperar/<dgt_ruta_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(dgt_ruta_id):
    """Recuperar DGT Ruta"""
    dgt_ruta_id = safe_uuid(dgt_ruta_id)
    if dgt_ruta_id == "":
        flash("ID de DGT Ruta inválido", "warning")
        return redirect(url_for("dgt_rutas.list_active"))
    dgt_ruta = DgtRuta.query.get_or_404(dgt_ruta_id)
    if dgt_ruta.estatus == "B":
        dgt_ruta.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperada DGT Ruta {dgt_ruta.clave}"),
            url=url_for("dgt_rutas.detail", dgt_ruta_id=dgt_ruta.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("dgt_rutas.detail", dgt_ruta_id=dgt_ruta.id))
