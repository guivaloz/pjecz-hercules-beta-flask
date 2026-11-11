"""
Archivos Juzgados Extintos, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from pjecz_hercules_beta_flask.blueprints.arc_juzgados_extintos.forms import ArcJuzgadoExtintoForm
from pjecz_hercules_beta_flask.blueprints.arc_juzgados_extintos.models import ArcJuzgadoExtinto
from pjecz_hercules_beta_flask.blueprints.bitacoras.models import Bitacora
from pjecz_hercules_beta_flask.blueprints.distritos.models import Distrito
from pjecz_hercules_beta_flask.blueprints.modulos.models import Modulo
from pjecz_hercules_beta_flask.blueprints.permisos.models import Permiso
from pjecz_hercules_beta_flask.blueprints.usuarios.decorators import permission_required
from pjecz_hercules_beta_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_hercules_beta_flask.lib.safe_string import safe_clave, safe_message, safe_string

MODULO = "ARC JUZGADOS EXTINTOS"

arc_juzgados_extintos = Blueprint("arc_juzgados_extintos", __name__, template_folder="templates")


@arc_juzgados_extintos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@arc_juzgados_extintos.route("/arc_juzgados_extintos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Juzgados Extintos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ArcJuzgadoExtinto.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(ArcJuzgadoExtinto.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(ArcJuzgadoExtinto.estatus == "A")
    if "distrito_id" in request.form:
        try:
            distrito_id = int(request.form["distrito_id"])
            consulta = consulta.filter(ArcJuzgadoExtinto.distrito_id == distrito_id)
        except ValueError:
            pass
    if "clave" in request.form:
        try:
            clave = safe_clave(request.form["clave"])
            if clave != "":
                consulta = consulta.filter(ArcJuzgadoExtinto.clave.contains(clave))
        except ValueError:
            pass
    if "descripcion_corta" in request.form:
        descripcion_corta = safe_string(request.form["descripcion_corta"], save_enie=True)
        if descripcion_corta != "":
            consulta = consulta.filter(ArcJuzgadoExtinto.descripcion_corta.contains(descripcion_corta))
    # Luego filtrar por columnas de otras tablas
    if "distrito_clave" in request.form:
        try:
            distrito_clave = safe_clave(request.form["distrito_clave"])
            if distrito_clave != "":
                consulta = consulta.join(Distrito).filter(Distrito.clave.contains(distrito_clave))
        except ValueError:
            pass
    # Ordenar y paginar
    registros = consulta.order_by(ArcJuzgadoExtinto.clave).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "clave": resultado.clave,
                    "url": url_for("arc_juzgados_extintos.detail", arc_juzgado_extinto_id=resultado.id),
                },
                "descripcion_corta": resultado.descripcion_corta,
                "descripcion": resultado.descripcion,
                "distrito_clave": resultado.distrito.clave,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@arc_juzgados_extintos.route("/arc_juzgados_extintos")
def list_active():
    """Listado de Juzgados Extintos activos"""
    return render_template(
        "arc_juzgados_extintos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Juzgados Extintos",
        estatus="A",
    )


@arc_juzgados_extintos.route("/arc_juzgados_extintos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Juzgados Extintos inactivos"""
    return render_template(
        "arc_juzgados_extintos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Juzgados Extintos inactivos",
        estatus="B",
    )


@arc_juzgados_extintos.route("/arc_juzgados_extintos/<int:arc_juzgado_extinto_id>")
def detail(arc_juzgado_extinto_id):
    """Detalle de un Juzgado Extinto"""
    arc_juzgado_extinto = ArcJuzgadoExtinto.query.get_or_404(arc_juzgado_extinto_id)
    return render_template("arc_juzgados_extintos/detail.jinja2", arc_juzgado_extinto=arc_juzgado_extinto)


@arc_juzgados_extintos.route("/arc_juzgados_extintos/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Juzgado Extinto"""
    form = ArcJuzgadoExtintoForm()
    if form.validate_on_submit():
        es_valido = True
        # Validar que la clave no se repita
        clave = safe_clave(form.clave.data)
        if ArcJuzgadoExtinto.query.filter_by(clave=clave).first():
            flash("La clave ya está en uso. Debe de ser única.", "warning")
            es_valido = False
        # Si es válido, guardar
        if es_valido is True:
            arc_juzgado_extinto = ArcJuzgadoExtinto(
                clave=clave,
                descripcion_corta=safe_string(form.descripcion_corta.data, save_enie=True),
                descripcion=safe_string(form.descripcion.data, save_enie=True),
                distrito_id=form.distrito.data,
            )
            arc_juzgado_extinto.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nuevo Juzgado Extinto {arc_juzgado_extinto.clave}"),
                url=url_for("arc_juzgados_extintos.detail", arc_juzgado_extinto_id=arc_juzgado_extinto.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    return render_template("arc_juzgados_extintos/new.jinja2", form=form)


@arc_juzgados_extintos.route("/arc_juzgados_extintos/edicion/<int:arc_juzgado_extinto_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(arc_juzgado_extinto_id):
    """Editar Juzgado Extinto"""
    arc_juzgado_extinto = ArcJuzgadoExtinto.query.get_or_404(arc_juzgado_extinto_id)
    form = ArcJuzgadoExtintoForm()
    if form.validate_on_submit():
        es_valido = True
        # Si cambia la clave verificar que no este en uso
        clave = safe_clave(form.clave.data)
        if arc_juzgado_extinto.clave != clave:
            arc_juzgado_extinto_existente = ArcJuzgadoExtinto.query.filter_by(clave=clave).first()
            if arc_juzgado_extinto_existente and arc_juzgado_extinto_existente.id != arc_juzgado_extinto.id:
                es_valido = False
                flash("La clave ya está en uso. Debe de ser única.", "warning")
        # Si es válido, actualizar
        if es_valido:
            arc_juzgado_extinto.clave = clave
            arc_juzgado_extinto.descripcion_corta = safe_string(form.descripcion_corta.data, save_enie=True)
            arc_juzgado_extinto.descripcion = safe_string(form.descripcion.data, save_enie=True)
            arc_juzgado_extinto.distrito_id = form.distrito.data
            arc_juzgado_extinto.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Juzgado Extinto {arc_juzgado_extinto.clave}"),
                url=url_for("arc_juzgados_extintos.detail", arc_juzgado_extinto_id=arc_juzgado_extinto.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.clave.data = arc_juzgado_extinto.clave
    form.descripcion_corta.data = arc_juzgado_extinto.descripcion_corta
    form.descripcion.data = arc_juzgado_extinto.descripcion
    form.distrito.data = arc_juzgado_extinto.distrito_id  # Se manda distrito_id porque es un select
    return render_template("arc_juzgados_extintos/edit.jinja2", form=form, arc_juzgado_extinto=arc_juzgado_extinto)


@arc_juzgados_extintos.route("/arc_juzgados_extintos/eliminar/<int:arc_juzgado_extinto_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(arc_juzgado_extinto_id):
    """Eliminar Juzgado Extinto"""
    arc_juzgado_extinto = ArcJuzgadoExtinto.query.get_or_404(arc_juzgado_extinto_id)
    if arc_juzgado_extinto.estatus == "A":
        arc_juzgado_extinto.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Juzgado Extinto {arc_juzgado_extinto.clave}"),
            url=url_for("arc_juzgados_extintos.detail", arc_juzgado_extinto_id=arc_juzgado_extinto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("arc_juzgados_extintos.detail", arc_juzgado_extinto_id=arc_juzgado_extinto.id))


@arc_juzgados_extintos.route("/arc_juzgados_extintos/recuperar/<int:arc_juzgado_extinto_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(arc_juzgado_extinto_id):
    """Recuperar Juzgado Extinto"""
    arc_juzgado_extinto = ArcJuzgadoExtinto.query.get_or_404(arc_juzgado_extinto_id)
    if arc_juzgado_extinto.estatus == "B":
        arc_juzgado_extinto.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Juzgado Extinto {arc_juzgado_extinto.clave}"),
            url=url_for("arc_juzgados_extintos.detail", arc_juzgado_extinto_id=arc_juzgado_extinto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("arc_juzgados_extintos.detail", arc_juzgado_extinto_id=arc_juzgado_extinto.id))


@arc_juzgados_extintos.route("/arc_juzgados_extintos/select2_json", methods=["GET", "POST"])
def select2_json():
    """Proporcionar el JSON de juzgados extintos para elegir con un Select2"""
    consulta = ArcJuzgadoExtinto.query.filter(ArcJuzgadoExtinto.estatus == "A")
    if "searchString" in request.form:
        clave = safe_clave(request.form["searchString"])
        if clave != "":
            consulta = consulta.filter(ArcJuzgadoExtinto.clave.contains(clave))
    resultados = []
    for item in consulta.order_by(ArcJuzgadoExtinto.clave).limit(10).all():
        resultados.append({"id": item.id, "clave": item.clave, "text": f"{item.clave}: {item.descripcion_corta}"})
    return {"results": resultados, "pagination": {"more": False}}
