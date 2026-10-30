"""
DGT Plataformas, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from pjecz_hercules_beta_flask.blueprints.bitacoras.models import Bitacora
from pjecz_hercules_beta_flask.blueprints.dgt_plataformas.forms import DgtPlataformaForm
from pjecz_hercules_beta_flask.blueprints.dgt_plataformas.models import DgtPlataforma
from pjecz_hercules_beta_flask.blueprints.modulos.models import Modulo
from pjecz_hercules_beta_flask.blueprints.permisos.models import Permiso
from pjecz_hercules_beta_flask.blueprints.usuarios.decorators import permission_required
from pjecz_hercules_beta_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_hercules_beta_flask.lib.safe_string import safe_clave, safe_message, safe_string, safe_uuid

MODULO = "DGT PLATAFORMAS"

dgt_plataformas = Blueprint("dgt_plataformas", __name__, template_folder="templates")


@dgt_plataformas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@dgt_plataformas.route("/dgt_plataformas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de DGT Plataformas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = DgtPlataforma.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(DgtPlataforma.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(DgtPlataforma.estatus == "A")
    if "clave" in request.form:
        try:
            clave = safe_clave(request.form["clave"], max_len=64)
            if clave != "":
                consulta = consulta.filter(DgtPlataforma.clave.contains(clave))
        except ValueError:
            pass
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], save_enie=True)
        if descripcion != "":
            consulta = consulta.filter(DgtPlataforma.descripcion.contains(descripcion))
    # Ordenar y paginar
    registros = consulta.order_by(DgtPlataforma.descripcion).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for item in registros:
        data.append(
            {
                "detalle": {
                    "clave": item.clave,
                    "url": url_for("dgt_plataformas.detail", dgt_plataforma_id=item.id),
                },
                "descripcion": item.descripcion,
                "api_key_oculta": item.api_key_oculta,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@dgt_plataformas.route("/dgt_plataformas")
def list_active():
    """Listado de DGT Plataformas activas"""
    return render_template(
        "dgt_plataformas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="DGT Plataformas",
        estatus="A",
    )


@dgt_plataformas.route("/dgt_plataformas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de DGT Plataformas inactivas"""
    return render_template(
        "dgt_plataformas/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="DGT Plataformas inactivas",
        estatus="B",
    )


@dgt_plataformas.route("/dgt_plataformas/<dgt_plataforma_id>")
def detail(dgt_plataforma_id):
    """Detalle de una DGT Plataforma"""
    dgt_plataforma_id = safe_uuid(dgt_plataforma_id)
    if dgt_plataforma_id == "":
        flash("ID de DGT Plataforma inválido", "warning")
        return redirect(url_for("dgt_plataformas.list_active"))
    dgt_plataforma = DgtPlataforma.query.get_or_404(dgt_plataforma_id)
    return render_template("dgt_plataformas/detail.jinja2", dgt_plataforma=dgt_plataforma)


@dgt_plataformas.route("/dgt_plataformas/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nueva DGT Plataforma"""
    form = DgtPlataformaForm()
    if form.validate_on_submit():
        clave = safe_clave(form.clave.data, max_len=64)
        descripcion = safe_string(form.descripcion.data, max_len=256, save_enie=True)
        api_key = str(form.api_key.data).strip()
        # Validar que la clave no se repita
        if DgtPlataforma.query.filter_by(clave=clave).first():
            flash("Esa clave ya está en uso. Debe de ser única.", "warning")
            return render_template("dgt_plataformas/new.jinja2", form=form)
        # Validar que la descripción no se repita
        if DgtPlataforma.query.filter_by(descripcion=descripcion).first():
            flash("Esa descripción ya está en uso. Debe de ser única.", "warning")
            return render_template("dgt_plataformas/new.jinja2", form=form)
        # Guardar
        dgt_plataforma = DgtPlataforma(
            clave=clave,
            descripcion=descripcion,
            api_key=api_key,
        )
        dgt_plataforma.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nueva DGT Plataforma {dgt_plataforma.descripcion}"),
            url=url_for("dgt_plataformas.detail", dgt_plataforma_id=dgt_plataforma.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template("dgt_plataformas/new.jinja2", form=form)


@dgt_plataformas.route("/dgt_plataformas/edicion/<dgt_plataforma_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(dgt_plataforma_id):
    """Editar DGT Plataforma"""
    dgt_plataforma_id = safe_uuid(dgt_plataforma_id)
    if dgt_plataforma_id == "":
        flash("ID de DGT Plataforma inválido", "warning")
        return redirect(url_for("dgt_plataformas.list_active"))
    dgt_plataforma = DgtPlataforma.query.get_or_404(dgt_plataforma_id)
    form = DgtPlataformaForm()
    if form.validate_on_submit():
        es_valido = True
        # Si cambia la clave verificar que no este en uso
        clave = safe_clave(form.clave.data, max_len=64)
        if dgt_plataforma.clave != clave:
            dgt_plataforma_existente = DgtPlataforma.query.filter_by(clave=clave).first()
            if dgt_plataforma_existente and dgt_plataforma_existente.id != dgt_plataforma.id:
                es_valido = False
                flash("La clave ya está en uso. Debe de ser única.", "warning")
        # Si cambia la descripción verificar que no este en uso
        descripcion = safe_string(form.descripcion.data, max_len=256, save_enie=True)
        if dgt_plataforma.descripcion != descripcion:
            dgt_plataforma_existente = DgtPlataforma.query.filter_by(descripcion=descripcion).first()
            if dgt_plataforma_existente and dgt_plataforma_existente.id != dgt_plataforma.id:
                es_valido = False
                flash("La descripción ya está en uso. Debe de ser única.", "warning")
        # Si es valido actualizar
        if es_valido:
            dgt_plataforma.descripcion = descripcion
            dgt_plataforma.api_key = str(form.api_key.data).strip()
            dgt_plataforma.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editada DGT Plataforma {dgt_plataforma.descripcion}"),
                url=url_for("dgt_plataformas.detail", dgt_plataforma_id=dgt_plataforma.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.clave.data = dgt_plataforma.clave
    form.descripcion.data = dgt_plataforma.descripcion
    form.api_key.data = dgt_plataforma.api_key
    return render_template("dgt_plataformas/edit.jinja2", form=form, dgt_plataforma=dgt_plataforma)


@dgt_plataformas.route("/dgt_plataformas/eliminar/<dgt_plataforma_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(dgt_plataforma_id):
    """Eliminar DGT Plataforma"""
    dgt_plataforma_id = safe_uuid(dgt_plataforma_id)
    if dgt_plataforma_id == "":
        flash("ID de DGT Plataforma inválido", "warning")
        return redirect(url_for("dgt_plataformas.list_active"))
    dgt_plataforma = DgtPlataforma.query.get_or_404(dgt_plataforma_id)
    if dgt_plataforma.estatus == "A":
        # Quitar las autoridades asociadas para que queden libres de asignarse a otra plataforma
        autoridades_quitadas = 0
        for dgt_plataforma_autoridad in dgt_plataforma.dgt_plataformas_autoridades:
            if dgt_plataforma_autoridad.estatus == "A":
                dgt_plataforma_autoridad.estatus = "B"
                autoridades_quitadas += 1
        # Al eliminar se guardan en la misma transacción la plataforma y sus autoridades
        dgt_plataforma.delete()
        descripcion = f"Eliminada DGT Plataforma {dgt_plataforma.clave}"
        if autoridades_quitadas > 0:
            descripcion += f" y se quitaron sus {autoridades_quitadas} autoridades"
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(descripcion),
            url=url_for("dgt_plataformas.detail", dgt_plataforma_id=dgt_plataforma.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("dgt_plataformas.detail", dgt_plataforma_id=dgt_plataforma.id))


@dgt_plataformas.route("/dgt_plataformas/recuperar/<dgt_plataforma_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(dgt_plataforma_id):
    """Recuperar DGT Plataforma"""
    dgt_plataforma_id = safe_uuid(dgt_plataforma_id)
    if dgt_plataforma_id == "":
        flash("ID de DGT Plataforma inválido", "warning")
        return redirect(url_for("dgt_plataformas.list_active"))
    dgt_plataforma = DgtPlataforma.query.get_or_404(dgt_plataforma_id)
    if dgt_plataforma.estatus == "B":
        dgt_plataforma.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperada DGT Plataforma {dgt_plataforma.clave}"),
            url=url_for("dgt_plataformas.detail", dgt_plataforma_id=dgt_plataforma.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("dgt_plataformas.detail", dgt_plataforma_id=dgt_plataforma.id))
