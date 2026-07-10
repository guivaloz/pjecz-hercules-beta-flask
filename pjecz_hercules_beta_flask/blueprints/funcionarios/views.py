"""
Funcionarios, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from pjecz_hercules_beta_flask.blueprints.bitacoras.models import Bitacora
from pjecz_hercules_beta_flask.blueprints.centros_trabajos.models import CentroTrabajo
from pjecz_hercules_beta_flask.blueprints.funcionarios.forms import FuncionarioForm
from pjecz_hercules_beta_flask.blueprints.funcionarios.models import Funcionario
from pjecz_hercules_beta_flask.blueprints.modulos.models import Modulo
from pjecz_hercules_beta_flask.blueprints.permisos.models import Permiso
from pjecz_hercules_beta_flask.blueprints.usuarios.decorators import permission_required
from pjecz_hercules_beta_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_hercules_beta_flask.lib.safe_string import safe_email, safe_message, safe_string

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
        consulta = consulta.filter(Funcionario.centro_trabajo_id == request.form["centro_trabajo_id"])
    if "email" in request.form:
        try:
            email = safe_email(request.form["email"], search_fragment=True)
            if email != "":
                consulta = consulta.filter(Funcionario.email.contains(email))
        except ValueError:
            pass
    if "nombres" in request.form:
        nombres = safe_string(request.form["nombres"], save_enie=True)
        if nombres != "":
            consulta = consulta.filter(Funcionario.nombres.contains(nombres))
    if "apellido_paterno" in request.form:
        apellido_paterno = safe_string(request.form["apellido_paterno"], save_enie=True)
        if apellido_paterno != "":
            consulta = consulta.filter(Funcionario.apellido_paterno.contains(apellido_paterno))
    if "puesto" in request.form:
        puesto = safe_string(request.form["puesto"])
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
                    "email": resultado.email,
                    "url": url_for("funcionarios.detail", funcionario_id=resultado.id),
                },
                "curp": resultado.curp[:4] + "************",
                "nombre": resultado.nombre,
                "puesto": resultado.puesto,
                "centro_trabajo_clave": resultado.centro_trabajo.clave,
                "centro_trabajo_nombre": resultado.centro_trabajo.nombre,
                "telefono": resultado.telefono,
                "extension": resultado.extension,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@funcionarios.route("/funcionarios")
def list_active():
    """Listado de Funcionarios activos"""
    return render_template(
        "funcionarios/list.jinja2",
        estatus="A",
        filtros={"estatus": "A"},
        titulo="Funcionarios",
    )


@funcionarios.route("/funcionarios/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Funcionarios inactivos"""
    return render_template(
        "funcionarios/list.jinja2",
        estatus="B",
        filtros={"estatus": "B"},
        titulo="Funcionarios inactivos",
    )


@funcionarios.route("/funcionarios/<funcionario_id>")
def detail(funcionario_id):
    """Detalle de un Funcionario"""
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    return render_template("funcionarios/detail.jinja2", funcionario=funcionario)


@funcionarios.route("/funcionarios/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Funconario"""
    form = FuncionarioForm()
    if form.validate_on_submit():
        es_valido = True
        # Validar que el CURP no se repita
        curp = safe_string(form.curp.data)
        if Funcionario.query.filter_by(curp=curp).first():
            flash("La CURP ya está en uso. Debe de ser única.", "warning")
            es_valido = False
        # Validar que el e-mail no se repita
        email = safe_email(form.email.data)
        if Funcionario.query.filter_by(email=email).first():
            flash("El e-mail ya está en uso. Debe de ser único.", "warning")
            es_valido = False
        if es_valido:
            funcionario = Funcionario(
                nombres=safe_string(form.nombres.data),
                apellido_paterno=safe_string(form.apellido_paterno.data),
                apellido_materno=safe_string(form.apellido_materno.data),
                curp=curp,
                email=email,
                puesto=safe_string(form.puesto.data),
                telefono=safe_string(form.telefono.data),
                extension=safe_string(form.extension.data),
                en_funciones=form.en_funciones.data,
                en_sentencias=form.en_sentencias.data,
                en_soportes=form.en_soportes.data,
                en_tesis_jurisprudencias=form.en_tesis_jurisprudencias.data,
                centro_trabajo_id=form.centro_trabajo.data,
                ingreso_fecha=form.ingreso_fecha.data,
            )
            funcionario.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nuevo funcionario {funcionario.nombre}"),
                url=url_for("funcionarios.detail", funcionario_id=funcionario.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    centro_trabajo_no_definido = CentroTrabajo.query.filter_by(nombre="NO DEFINIDO").first()
    if centro_trabajo_no_definido is not None:
        form.centro_trabajo.data = centro_trabajo_no_definido
    return render_template("funcionarios/new.jinja2", form=form)


@funcionarios.route("/funcionarios/edicion/<int:funcionario_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(funcionario_id):
    """Editar Funcionario"""
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    form = FuncionarioForm()
    if form.validate_on_submit():
        es_valido = True
        # Si cambia el CURP verificar que no este en uso
        curp = safe_string(form.curp.data)
        if funcionario.curp != curp:
            funcionario_existente = Funcionario.query.filter_by(curp=curp).first()
            if funcionario_existente and funcionario_existente.id != funcionario.id:
                es_valido = False
                flash("El CURP ya está en uso. Debe de ser único.", "warning")
        # Si cambia el e-mail verificar que no este en uso
        email = safe_email(form.email.data)
        if funcionario.email != email:
            funcionario_existente = Funcionario.query.filter_by(email=email).first()
            if funcionario_existente and funcionario_existente.id != funcionario.id:
                es_valido = False
                flash("La e-mail ya está en uso. Debe de ser único.", "warning")
        # Si es valido actualizar
        if es_valido:
            funcionario.nombres = safe_string(form.nombres.data)
            funcionario.apellido_paterno = safe_string(form.apellido_paterno.data)
            funcionario.apellido_materno = safe_string(form.apellido_materno.data)
            funcionario.curp = curp
            funcionario.email = email
            funcionario.puesto = safe_string(form.puesto.data)
            funcionario.telefono = safe_string(form.telefono.data)
            funcionario.extension = safe_string(form.extension.data)
            funcionario.en_funciones = form.en_funciones.data
            funcionario.en_sentencias = form.en_sentencias.data
            funcionario.en_soportes = form.en_soportes.data
            funcionario.en_tesis_jurisprudencias = form.en_tesis_jurisprudencias.data
            funcionario.centro_trabajo_id = form.centro_trabajo.data
            funcionario.ingreso_fecha = form.ingreso_fecha.data
            funcionario.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado funcionario {funcionario.nombre}"),
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
    form.puesto.data = funcionario.puesto
    form.telefono.data = funcionario.telefono
    form.extension.data = funcionario.extension
    form.en_funciones.data = funcionario.en_funciones
    form.en_sentencias.data = funcionario.en_sentencias
    form.en_soportes.data = funcionario.en_soportes
    form.en_tesis_jurisprudencias.data = funcionario.en_tesis_jurisprudencias
    form.centro_trabajo.data = funcionario.centro_trabajo
    form.ingreso_fecha.data = funcionario.ingreso_fecha
    return render_template("funcionarios/edit.jinja2", form=form, funcionario=funcionario)


@funcionarios.route("/funcionarios/eliminar/<funcionario_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(funcionario_id):
    """Eliminar Funcionario"""
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    if funcionario.estatus == "A":
        funcionario.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Funcionario {funcionario.nombre}"),
            url=url_for("funcionarios.detail", funcionario_id=funcionario.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("funcionarios.detail", funcionario_id=funcionario.id))


@funcionarios.route("/funcionarios/recuperar/<funcionario_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(funcionario_id):
    """Recuperar Funcionario"""
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    if funcionario.estatus == "B":
        funcionario.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Funcionario {funcionario.nombre}"),
            url=url_for("funcionarios.detail", funcionario_id=funcionario.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("funcionarios.detail", funcionario_id=funcionario.id))
