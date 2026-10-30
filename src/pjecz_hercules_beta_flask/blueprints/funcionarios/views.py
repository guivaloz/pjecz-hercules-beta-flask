"""
Funcionarios, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from pjecz_hercules_beta_flask.blueprints.bitacoras.models import Bitacora
from pjecz_hercules_beta_flask.blueprints.funcionarios.forms import FuncionarioForm
from pjecz_hercules_beta_flask.blueprints.funcionarios.models import Funcionario
from pjecz_hercules_beta_flask.blueprints.modulos.models import Modulo
from pjecz_hercules_beta_flask.blueprints.permisos.models import Permiso
from pjecz_hercules_beta_flask.blueprints.usuarios.decorators import permission_required
from pjecz_hercules_beta_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_hercules_beta_flask.lib.safe_string import safe_clave, safe_curp, safe_email, safe_message, safe_string, safe_url

MODULO = "FUNCIONARIOS"

funcionarios = Blueprint("funcionarios", __name__, template_folder="templates")


@funcionarios.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@funcionarios.route("/funcionarios/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Funcionarios"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Funcionario.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(Funcionario.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(Funcionario.estatus == "A")
    if "centro_trabajo_id" in request.form:
        try:
            centro_trabajo_id = int(request.form["centro_trabajo_id"])
            consulta = consulta.filter(Funcionario.centro_trabajo_id == centro_trabajo_id)
        except ValueError:
            pass
    if "curp" in request.form:
        curp = safe_curp(request.form["curp"], search_fragment=True)
        if curp != "":
            consulta = consulta.filter(Funcionario.curp.contains(curp))
    if "nombres" in request.form:
        nombres = safe_string(request.form["nombres"], save_enie=True)
        if nombres != "":
            consulta = consulta.filter(Funcionario.nombres.contains(nombres))
    if "apellido_paterno" in request.form:
        apellido_paterno = safe_string(request.form["apellido_paterno"], save_enie=True)
        if apellido_paterno != "":
            consulta = consulta.filter(Funcionario.apellido_paterno.contains(apellido_paterno))
    if "puesto" in request.form:
        puesto = safe_string(request.form["puesto"], save_enie=True)
        if puesto != "":
            consulta = consulta.filter(Funcionario.puesto.contains(puesto))
    # Ordenar y paginar
    registros = consulta.order_by(Funcionario.email).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "curp": resultado.curp,
                    "url": url_for("funcionarios.detail", funcionario_id=resultado.id),
                },
                "nombre": resultado.nombre,
                "puesto": resultado.puesto,
                "centro_trabajo_clave": resultado.centro_trabajo.clave,
                "email": resultado.email,
                "en_funciones": resultado.en_funciones,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@funcionarios.route("/funcionarios")
def list_active():
    """Listado de Funcionarios activos"""
    return render_template(
        "funcionarios/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Funcionarios",
        estatus="A",
    )


@funcionarios.route("/funcionarios/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Funcionarios inactivos"""
    return render_template(
        "funcionarios/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Funcionarios inactivos",
        estatus="B",
    )


@funcionarios.route("/funcionarios/<int:funcionario_id>")
def detail(funcionario_id):
    """Detalle de un Funcionario"""
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    return render_template("funcionarios/detail.jinja2", funcionario=funcionario)


@funcionarios.route("/funcionarios/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Funcionario"""
    form = FuncionarioForm()
    if form.validate_on_submit():
        es_valido = True
        # Validar la CURP y el e-mail
        try:
            curp = safe_curp(form.curp.data)
            email = safe_email(form.email.data)
        except ValueError as error:
            flash(str(error), "warning")
            return render_template("funcionarios/new.jinja2", form=form)
        # Validar que la CURP no se repita
        if Funcionario.query.filter_by(curp=curp).first():
            flash("La CURP ya está en uso. Debe de ser única.", "warning")
            es_valido = False
        # Validar que el e-mail no se repita
        if Funcionario.query.filter_by(email=email).first():
            flash("El e-mail ya está en uso. Debe de ser único.", "warning")
            es_valido = False
        # Si es válido, guardar
        if es_valido is True:
            funcionario = Funcionario(
                nombres=safe_string(form.nombres.data, save_enie=True),
                apellido_paterno=safe_string(form.apellido_paterno.data, save_enie=True),
                apellido_materno=safe_string(form.apellido_materno.data, save_enie=True),
                curp=curp,
                email=email,
                centro_trabajo_id=form.centro_trabajo.data,
                puesto=safe_string(form.puesto.data, save_enie=True),
                puesto_clave=safe_clave(form.puesto_clave.data, max_len=32),
                ingreso_fecha=form.ingreso_fecha.data,
                telefono=safe_string(form.telefono.data, max_len=48),
                extension=safe_string(form.extension.data, max_len=24),
                domicilio_oficial=safe_string(form.domicilio_oficial.data, max_len=512, save_enie=True),
                fotografia_url=safe_url(form.fotografia_url.data),
                en_funciones=form.en_funciones.data,
                en_sentencias=form.en_sentencias.data,
                en_soportes=form.en_soportes.data,
                en_tesis_jurisprudencias=form.en_tesis_jurisprudencias.data,
            )
            funcionario.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nuevo Funcionario {funcionario.email}"),
                url=url_for("funcionarios.detail", funcionario_id=funcionario.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    return render_template("funcionarios/new.jinja2", form=form)


@funcionarios.route("/funcionarios/edicion/<int:funcionario_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(funcionario_id):
    """Editar Funcionario"""
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    form = FuncionarioForm()
    if form.validate_on_submit():
        es_valido = True
        # Validar la CURP y el e-mail
        try:
            curp = safe_curp(form.curp.data)
            email = safe_email(form.email.data)
        except ValueError as error:
            flash(str(error), "warning")
            return render_template("funcionarios/edit.jinja2", form=form, funcionario=funcionario)
        # Si cambia la CURP verificar que no este en uso
        if funcionario.curp != curp:
            funcionario_existente = Funcionario.query.filter_by(curp=curp).first()
            if funcionario_existente and funcionario_existente.id != funcionario.id:
                es_valido = False
                flash("La CURP ya está en uso. Debe de ser única.", "warning")
        # Si cambia el e-mail verificar que no este en uso
        if funcionario.email != email:
            funcionario_existente = Funcionario.query.filter_by(email=email).first()
            if funcionario_existente and funcionario_existente.id != funcionario.id:
                es_valido = False
                flash("El e-mail ya está en uso. Debe de ser único.", "warning")
        # Si es válido, actualizar
        if es_valido:
            funcionario.nombres = safe_string(form.nombres.data, save_enie=True)
            funcionario.apellido_paterno = safe_string(form.apellido_paterno.data, save_enie=True)
            funcionario.apellido_materno = safe_string(form.apellido_materno.data, save_enie=True)
            funcionario.curp = curp
            funcionario.email = email
            funcionario.centro_trabajo_id = form.centro_trabajo.data
            funcionario.puesto = safe_string(form.puesto.data, save_enie=True)
            funcionario.puesto_clave = safe_clave(form.puesto_clave.data, max_len=32)
            funcionario.ingreso_fecha = form.ingreso_fecha.data
            funcionario.telefono = safe_string(form.telefono.data, max_len=48)
            funcionario.extension = safe_string(form.extension.data, max_len=24)
            funcionario.domicilio_oficial = safe_string(form.domicilio_oficial.data, max_len=512, save_enie=True)
            funcionario.fotografia_url = safe_url(form.fotografia_url.data)
            funcionario.en_funciones = form.en_funciones.data
            funcionario.en_sentencias = form.en_sentencias.data
            funcionario.en_soportes = form.en_soportes.data
            funcionario.en_tesis_jurisprudencias = form.en_tesis_jurisprudencias.data
            funcionario.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Funcionario {funcionario.email}"),
                url=url_for("funcionarios.detail", funcionario_id=funcionario.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.nombres.data = funcionario.nombres
    form.apellido_paterno.data = funcionario.apellido_paterno
    form.apellido_materno.data = funcionario.apellido_materno
    form.curp.data = funcionario.curp
    form.email.data = funcionario.email
    form.centro_trabajo.data = funcionario.centro_trabajo_id  # Se manda centro_trabajo_id porque es un select
    form.puesto.data = funcionario.puesto
    form.puesto_clave.data = funcionario.puesto_clave
    form.ingreso_fecha.data = funcionario.ingreso_fecha
    form.telefono.data = funcionario.telefono
    form.extension.data = funcionario.extension
    form.domicilio_oficial.data = funcionario.domicilio_oficial
    form.fotografia_url.data = funcionario.fotografia_url
    form.en_funciones.data = funcionario.en_funciones
    form.en_sentencias.data = funcionario.en_sentencias
    form.en_soportes.data = funcionario.en_soportes
    form.en_tesis_jurisprudencias.data = funcionario.en_tesis_jurisprudencias
    return render_template("funcionarios/edit.jinja2", form=form, funcionario=funcionario)


@funcionarios.route("/funcionarios/eliminar/<int:funcionario_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(funcionario_id):
    """Eliminar Funcionario"""
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    if funcionario.estatus == "A":
        funcionario.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Funcionario {funcionario.email}"),
            url=url_for("funcionarios.detail", funcionario_id=funcionario.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("funcionarios.detail", funcionario_id=funcionario.id))


@funcionarios.route("/funcionarios/recuperar/<int:funcionario_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(funcionario_id):
    """Recuperar Funcionario"""
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    if funcionario.estatus == "B":
        funcionario.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Funcionario {funcionario.email}"),
            url=url_for("funcionarios.detail", funcionario_id=funcionario.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("funcionarios.detail", funcionario_id=funcionario.id))
