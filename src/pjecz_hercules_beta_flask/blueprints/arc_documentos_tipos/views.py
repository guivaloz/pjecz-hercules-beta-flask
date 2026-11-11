"""
Archivos Documentos Tipos, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from pjecz_hercules_beta_flask.blueprints.arc_documentos_tipos.forms import ArcDocumentoTipoForm
from pjecz_hercules_beta_flask.blueprints.arc_documentos_tipos.models import ArcDocumentoTipo
from pjecz_hercules_beta_flask.blueprints.bitacoras.models import Bitacora
from pjecz_hercules_beta_flask.blueprints.modulos.models import Modulo
from pjecz_hercules_beta_flask.blueprints.permisos.models import Permiso
from pjecz_hercules_beta_flask.blueprints.usuarios.decorators import permission_required
from pjecz_hercules_beta_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_hercules_beta_flask.lib.safe_string import safe_message, safe_string

MODULO = "ARC DOCUMENTOS TIPOS"

arc_documentos_tipos = Blueprint("arc_documentos_tipos", __name__, template_folder="templates")


@arc_documentos_tipos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@arc_documentos_tipos.route("/arc_documentos_tipos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Tipos de Documentos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ArcDocumentoTipo.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(ArcDocumentoTipo.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(ArcDocumentoTipo.estatus == "A")
    if "nombre" in request.form:
        nombre = safe_string(request.form["nombre"], save_enie=True)
        if nombre != "":
            consulta = consulta.filter(ArcDocumentoTipo.nombre.contains(nombre))
    # Ordenar y paginar
    registros = consulta.order_by(ArcDocumentoTipo.nombre).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "nombre": resultado.nombre,
                    "url": url_for("arc_documentos_tipos.detail", arc_documento_tipo_id=resultado.id),
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@arc_documentos_tipos.route("/arc_documentos_tipos")
def list_active():
    """Listado de Tipos de Documentos activos"""
    return render_template(
        "arc_documentos_tipos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Tipos de Documentos",
        estatus="A",
    )


@arc_documentos_tipos.route("/arc_documentos_tipos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Tipos de Documentos inactivos"""
    return render_template(
        "arc_documentos_tipos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Tipos de Documentos inactivos",
        estatus="B",
    )


@arc_documentos_tipos.route("/arc_documentos_tipos/<int:arc_documento_tipo_id>")
def detail(arc_documento_tipo_id):
    """Detalle de un Tipo de Documento"""
    arc_documento_tipo = ArcDocumentoTipo.query.get_or_404(arc_documento_tipo_id)
    return render_template("arc_documentos_tipos/detail.jinja2", arc_documento_tipo=arc_documento_tipo)


@arc_documentos_tipos.route("/arc_documentos_tipos/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Tipo de Documento"""
    form = ArcDocumentoTipoForm()
    if form.validate_on_submit():
        es_valido = True
        # Validar que el nombre no se repita
        nombre = safe_string(form.nombre.data, save_enie=True)
        if ArcDocumentoTipo.query.filter_by(nombre=nombre).first():
            flash("El nombre ya está en uso. Debe de ser único.", "warning")
            es_valido = False
        # Si es válido, guardar
        if es_valido is True:
            arc_documento_tipo = ArcDocumentoTipo(nombre=nombre)
            arc_documento_tipo.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nuevo Tipo de Documento {arc_documento_tipo.nombre}"),
                url=url_for("arc_documentos_tipos.detail", arc_documento_tipo_id=arc_documento_tipo.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    return render_template("arc_documentos_tipos/new.jinja2", form=form)


@arc_documentos_tipos.route("/arc_documentos_tipos/edicion/<int:arc_documento_tipo_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(arc_documento_tipo_id):
    """Editar Tipo de Documento"""
    arc_documento_tipo = ArcDocumentoTipo.query.get_or_404(arc_documento_tipo_id)
    form = ArcDocumentoTipoForm()
    if form.validate_on_submit():
        es_valido = True
        # Si cambia el nombre verificar que no este en uso
        nombre = safe_string(form.nombre.data, save_enie=True)
        if arc_documento_tipo.nombre != nombre:
            arc_documento_tipo_existente = ArcDocumentoTipo.query.filter_by(nombre=nombre).first()
            if arc_documento_tipo_existente and arc_documento_tipo_existente.id != arc_documento_tipo.id:
                es_valido = False
                flash("El nombre ya está en uso. Debe de ser único.", "warning")
        # Si es válido, actualizar
        if es_valido:
            arc_documento_tipo.nombre = nombre
            arc_documento_tipo.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Tipo de Documento {arc_documento_tipo.nombre}"),
                url=url_for("arc_documentos_tipos.detail", arc_documento_tipo_id=arc_documento_tipo.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.nombre.data = arc_documento_tipo.nombre
    return render_template("arc_documentos_tipos/edit.jinja2", form=form, arc_documento_tipo=arc_documento_tipo)


@arc_documentos_tipos.route("/arc_documentos_tipos/eliminar/<int:arc_documento_tipo_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(arc_documento_tipo_id):
    """Eliminar Tipo de Documento"""
    arc_documento_tipo = ArcDocumentoTipo.query.get_or_404(arc_documento_tipo_id)
    if arc_documento_tipo.estatus == "A":
        arc_documento_tipo.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Tipo de Documento {arc_documento_tipo.nombre}"),
            url=url_for("arc_documentos_tipos.detail", arc_documento_tipo_id=arc_documento_tipo.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("arc_documentos_tipos.detail", arc_documento_tipo_id=arc_documento_tipo.id))


@arc_documentos_tipos.route("/arc_documentos_tipos/recuperar/<int:arc_documento_tipo_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(arc_documento_tipo_id):
    """Recuperar Tipo de Documento"""
    arc_documento_tipo = ArcDocumentoTipo.query.get_or_404(arc_documento_tipo_id)
    if arc_documento_tipo.estatus == "B":
        arc_documento_tipo.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Tipo de Documento {arc_documento_tipo.nombre}"),
            url=url_for("arc_documentos_tipos.detail", arc_documento_tipo_id=arc_documento_tipo.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("arc_documentos_tipos.detail", arc_documento_tipo_id=arc_documento_tipo.id))


@arc_documentos_tipos.route("/arc_documentos_tipos/select2_json", methods=["GET", "POST"])
def select2_json():
    """Proporcionar el JSON de juzgados extintos para elegir con un Select2"""
    consulta = ArcDocumentoTipo.query.filter(ArcDocumentoTipo.estatus == "A")
    if "searchString" in request.form:
        nombre = safe_string(request.form["searchString"])
        if nombre != "":
            consulta = consulta.filter(ArcDocumentoTipo.nombre.contains(nombre))
    resultados = []
    for item in consulta.order_by(ArcDocumentoTipo.nombre).limit(10).all():
        resultados.append({"id": item.id, "text": f"{item.nombre}: {item.descripcion_corta}"})
    return {"results": resultados, "pagination": {"more": False}}
