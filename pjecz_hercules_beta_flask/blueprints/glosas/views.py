"""
Glosas, vistas
"""

import json
import re
from datetime import date, datetime, timedelta

import pytz
from flask import Blueprint, current_app, flash, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.datastructures import CombinedMultiDict
from werkzeug.exceptions import NotFound

from pjecz_hercules_beta_flask.blueprints.autoridades.models import Autoridad
from pjecz_hercules_beta_flask.blueprints.bitacoras.models import Bitacora
from pjecz_hercules_beta_flask.blueprints.glosas.forms import GlosaEditForm, GlosaNewForm
from pjecz_hercules_beta_flask.blueprints.glosas.models import Glosa
from pjecz_hercules_beta_flask.blueprints.modulos.models import Modulo
from pjecz_hercules_beta_flask.blueprints.permisos.models import Permiso
from pjecz_hercules_beta_flask.blueprints.usuarios.decorators import permission_required
from pjecz_hercules_beta_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_hercules_beta_flask.lib.exceptions import (
    MyBucketNotFoundError,
    MyFilenameError,
    MyFileNotFoundError,
    MyMissingConfigurationError,
    MyNotAllowedExtensionError,
    MyNotValidParamError,
    MyUnknownExtensionError,
)
from pjecz_hercules_beta_flask.lib.google_cloud_storage import get_blob_name_from_url, get_file_from_gcs
from pjecz_hercules_beta_flask.lib.safe_string import (
    safe_clave,
    safe_expediente,
    safe_message,
    safe_string,
)
from pjecz_hercules_beta_flask.lib.storage import GoogleCloudStorage

MODULO = "GLOSAS"
LIMITE_DIAS = 365  # Un año
LIMITE_DIAS_EDITAR = LIMITE_DIAS_ELIMINAR = LIMITE_DIAS_RECUPERAR = 7
LIMITE_ADMINISTRADORES_DIAS = 3650  # Administradores pueden manipular diez años
ORGANOS_JURISDICCIONALES = ("PLENO O SALA DEL TSJ", "TRIBUNAL DE CONCILIACION Y ARBITRAJE")

glosas = Blueprint("glosas", __name__, template_folder="templates")


@glosas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@glosas.route("/glosas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Glosas"""

    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()

    # Consultar
    consulta = Glosa.query

    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(Glosa.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(Glosa.estatus == "A")
    if "autoridad_id" in request.form:
        autoridad = Autoridad.query.get(request.form["autoridad_id"])
        if autoridad:
            consulta = consulta.filter(Glosa.autoridad_id == autoridad.id)
    elif "autoridad_clave" in request.form:
        autoridad_clave = safe_clave(request.form["autoridad_clave"])
        if autoridad_clave != "":
            consulta = consulta.join(Autoridad).filter(Autoridad.clave.contains(autoridad_clave))
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], save_enie=True)
        if descripcion != "":
            consulta = consulta.filter(Glosa.descripcion.contains(descripcion))
    if "expediente" in request.form:
        try:
            expediente = safe_expediente(request.form["expediente"])
            consulta = consulta.filter(Glosa.expediente == expediente)
        except IndexError, ValueError:
            pass

    # Ordenar y paginar
    registros = consulta.order_by(Glosa.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()

    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "fecha": resultado.fecha.strftime("%Y-%m-%d 00:00:00"),
                "autoridad_clave": resultado.autoridad.clave,
                "detalle": {
                    "descripcion": resultado.descripcion,
                    "url": url_for("glosas.detail", glosa_id=resultado.id),
                },
                "expediente": resultado.expediente,
                "tipo_juicio": resultado.tipo_juicio,
            }
        )

    # Entregar JSON
    return output_datatable_json(draw, total, data)


@glosas.route("/glosas/admin_datatable_json", methods=["GET", "POST"])
def admin_datatable_json():
    """DataTable JSON con Glosa para administrador"""

    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()

    # Consultar
    consulta = Glosa.query

    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(Glosa.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(Glosa.estatus == "A")
    if "autoridad_id" in request.form:
        consulta = consulta.filter(Glosa.autoridad_id == request.form["autoridad_id"])
    elif "autoridad_clave" in request.form:
        autoridad_clave = safe_clave(request.form["autoridad_clave"])
        if autoridad_clave != "":
            consulta = consulta.join(Autoridad).filter(Autoridad.clave.contains(autoridad_clave))
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], save_enie=True)
        if descripcion != "":
            consulta = consulta.filter(Glosa.descripcion.contains(descripcion))
    if "expediente" in request.form:
        try:
            expediente = safe_expediente(request.form["expediente"])
            consulta = consulta.filter(Glosa.expediente == expediente)
        except IndexError, ValueError:
            pass

    # Filtrar por creado, si vienen invertidas se corrigen
    creado_desde = None
    creado_hasta = None
    if "creado_desde" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["creado_desde"]):
        creado_desde = request.form["creado_desde"]
    if "creado_hasta" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["creado_hasta"]):
        creado_hasta = request.form["creado_hasta"]
    if creado_desde and creado_hasta and creado_desde > creado_hasta:
        creado_desde, creado_hasta = creado_hasta, creado_desde
    if creado_desde:
        consulta = consulta.filter(Glosa.fecha >= creado_desde)
    if creado_hasta:
        consulta = consulta.filter(Glosa.fecha <= creado_hasta)

    # Ordenar y paginar
    registros = consulta.order_by(Glosa.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()

    # Elaborar datos para DataTable
    data = []
    for glosa in registros:
        data.append(
            {
                "detalle": {
                    "id": glosa.id,
                    "url": url_for("glosas.detail", glosa_id=glosa.id),
                },
                "creado": glosa.creado.strftime("%Y-%m-%dT%H:%M:%S"),
                "autoridad_clave": glosa.autoridad.clave,
                "fecha": glosa.fecha.strftime("%Y-%m-%d 00:00:00"),
                "descripcion": glosa.descripcion,
                "expediente": glosa.expediente,
                "tipo_juicio": glosa.tipo_juicio,
            }
        )

    # Entregar JSON
    return output_datatable_json(draw, total, data)


@glosas.route("/glosas")
def list_active():
    """Listado de Glosas activos"""
    filtros = None
    titulo = None
    mostrar_filtro_autoridad_clave = True

    # Si es administrador
    plantilla = "glosas/list.jinja2"
    if current_user.can_admin(MODULO):
        plantilla = "glosas/list_admin.jinja2"

    # Si viene autoridad_id o autoridad_clave en la URL, agregar a los filtros
    autoridad = None
    if "autoridad_id" in request.args and request.args.get("autoridad_id") is not None:
        autoridad = Autoridad.query.get(request.args.get("autoridad_id"))
    elif "autoridad_clave" in request.args:
        autoridad_clave = safe_clave(request.args.get("autoridad_clave"))
        autoridad = Autoridad.query.filter_by(clave=autoridad_clave).first()
    if autoridad is not None:
        filtros = {"estatus": "A", "autoridad_id": autoridad.id}
        titulo = f"Glosas de {autoridad.descripcion_corta}"
        mostrar_filtro_autoridad_clave = False

    # Si es administrador
    if titulo is None and current_user.can_admin(MODULO):
        titulo = "Todas las Glosas"
        filtros = {"estatus": "A"}

    # Si puede editar o crear, solo ve lo de su autoridad
    if titulo is None and (current_user.can_insert(MODULO) or current_user.can_edit(MODULO)):
        filtros = {"estatus": "A", "autoridad_id": current_user.autoridad.id}
        titulo = f"Glosas de {current_user.autoridad.descripcion_corta}"
        mostrar_filtro_autoridad_clave = False

    # De lo contrario, es observador
    if titulo is None:
        filtros = {"estatus": "A"}
        titulo = "Glosas"

    # Entregar
    return render_template(
        plantilla,
        autoridad=autoridad,
        filtros=json.dumps(filtros),
        titulo=titulo,
        mostrar_filtro_autoridad_clave=mostrar_filtro_autoridad_clave,
        estatus="A",
    )


@glosas.route("/glosas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Glosas inactivos"""
    return render_template(
        "glosas/list.jinja2",
        estatus="B",
        filtros={"estatus": "B"},
        titulo="Glosas inactivos",
    )


@glosas.route("/glosas/<int:glosa_id>")
def detail(glosa_id):
    """Detalle de un Glosa"""
    glosa = Glosa.query.get_or_404(glosa_id)
    return render_template("glosas/detail.jinja2", glosa=glosa)


@glosas.route("/glosas/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Subir Glosa como Juzgado"""

    # Validar autoridad
    autoridad = current_user.autoridad
    if autoridad is None or autoridad.estatus != "A":
        flash("El juzgado/autoridad no existe o no es activa.", "warning")
        return redirect(url_for("glosas.list_active"))
    if not autoridad.distrito.es_distrito_judicial:
        flash("El juzgado/autoridad no está en un distrito jurisdiccional.", "warning")
        return redirect(url_for("glosas.list_active"))
    if not autoridad.es_jurisdiccional:
        flash("El juzgado/autoridad no es jurisdiccional.", "warning")
        return redirect(url_for("glosas.list_active"))
    if autoridad.directorio_glosas is None or autoridad.directorio_glosas == "":
        flash("El juzgado/autoridad no tiene directorio para glosas.", "warning")
        return redirect(url_for("glosas.list_active"))

    # Definir la fecha límite para el juzgado
    hoy = date.today()
    hoy_dt = datetime(year=hoy.year, month=hoy.month, day=hoy.day)
    limite_dt = hoy_dt + timedelta(days=-LIMITE_DIAS)

    # Si viene el formulario
    form = GlosaNewForm(CombinedMultiDict((request.files, request.form)))
    if form.validate_on_submit():
        es_valido = True

        # Validar fecha
        fecha = form.fecha.data
        if not limite_dt <= datetime(year=fecha.year, month=fecha.month, day=fecha.day) <= hoy_dt:
            flash(f"La fecha no debe ser del futuro ni anterior a {LIMITE_DIAS} días.", "warning")
            form.fecha.data = hoy
            es_valido = False

        # Tomar tipo de juicio
        tipo_juicio = form.tipo_juicio.data

        # Validar descripción
        descripcion = safe_string(form.descripcion.data, save_enie=True)
        if descripcion == "":
            flash("La descripción es incorrecta.", "warning")
            es_valido = False

        # Validar expediente
        try:
            expediente = safe_expediente(form.expediente.data)
        except IndexError, ValueError:
            flash("El expediente es incorrecto.", "warning")
            es_valido = False

        # Inicializar la liberia GCS con el directorio base, la fecha, las extensiones y los meses como palabras
        gcstorage = GoogleCloudStorage(
            base_directory=autoridad.directorio_glosas,
            upload_date=fecha,
            allowed_extensions=["pdf"],
            month_in_word=True,
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_GLOSAS"],
        )

        # Validar archivo
        archivo = request.files["archivo"]
        try:
            gcstorage.set_content_type(archivo.filename)
        except MyNotAllowedExtensionError:
            flash("Tipo de archivo no permitido.", "warning")
            es_valido = False
        except MyUnknownExtensionError:
            flash("Tipo de archivo desconocido.", "warning")
            es_valido = False

        # Insertar registro
        glosa = Glosa(
            autoridad=autoridad,
            fecha=fecha,
            tipo_juicio=tipo_juicio,
            descripcion=descripcion,
            expediente=expediente,
        )
        glosa.save()

        # Subir a Google Cloud Storage
        es_exitoso = True
        try:
            gcstorage.set_filename(hashed_id=glosa.encode_id(), description=descripcion)
            gcstorage.upload(archivo.stream.read())
        except MyFilenameError, MyNotAllowedExtensionError, MyUnknownExtensionError:
            flash("Error fatal al subir el archivo a GCS.", "warning")
            es_exitoso = False
        except MyMissingConfigurationError:
            flash("Error al subir el archivo porque falla la configuración de GCS.", "danger")
            es_exitoso = False
        except Exception:
            flash("Error desconocido al subir el archivo.", "danger")
            es_exitoso = False

        # Si se sube con éxito, actualizar el registro con la URL del archivo y mostrar el detalle
        if es_exitoso:
            glosa.archivo = gcstorage.filename  # Conservar el nombre original
            glosa.url = gcstorage.url
            glosa.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nueva Glosa de {autoridad.clave} sobre {glosa.descripcion}"),
                url=url_for("glosas.detail", glosa_id=glosa.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)

        # Como no se subio con exito, se cambia el estatus a "B"
        glosa.estatus = "B"
        glosa.save()

    # Valores por defecto
    form.distrito.data = autoridad.distrito.nombre
    form.autoridad.data = autoridad.descripcion
    form.fecha.data = hoy

    # Entregar el formulario
    return render_template("glosas/new.jinja2", form=form)


@glosas.route("/glosas/nuevo_con_autoridad_id/<int:autoridad_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.ADMINISTRAR)
def new_with_autoridad_id(autoridad_id):
    """Subir Glosa para una autoridad como administrador"""

    # Validar autoridad
    autoridad = Autoridad.query.get_or_404(autoridad_id)
    if autoridad is None:
        flash("El juzgado/autoridad no existe.", "warning")
        return redirect(url_for("listas_de_acuerdos.list_active"))
    if autoridad.estatus != "A":
        flash("El juzgado/autoridad no es activa.", "warning")
        return redirect(url_for("autoridades.detail", autoridad_id=autoridad.id))
    if not autoridad.distrito.es_distrito_judicial:
        flash("El juzgado/autoridad no está en un distrito jurisdiccional.", "warning")
        return redirect(url_for("autoridades.detail", autoridad_id=autoridad.id))
    if not autoridad.es_jurisdiccional:
        flash("El juzgado/autoridad no es jurisdiccional.", "warning")
        return redirect(url_for("autoridades.detail", autoridad_id=autoridad.id))
    if autoridad.directorio_glosas is None or autoridad.directorio_glosas == "":
        flash("El juzgado/autoridad no tiene directorio para glosas.", "warning")
        return redirect(url_for("autoridades.detail", autoridad_id=autoridad.id))

    # Para validar las fechas
    hoy = date.today()
    hoy_dt = datetime(year=hoy.year, month=hoy.month, day=hoy.day)
    limite_dt = hoy_dt + timedelta(days=-LIMITE_ADMINISTRADORES_DIAS)

    # Si viene el formulario
    form = GlosaNewForm(CombinedMultiDict((request.files, request.form)))
    if form.validate_on_submit():
        es_valido = True

        # Validar fecha
        fecha = form.fecha.data
        if not limite_dt <= datetime(year=fecha.year, month=fecha.month, day=fecha.day) <= hoy_dt:
            flash(f"La fecha no debe ser del futuro ni anterior a {LIMITE_ADMINISTRADORES_DIAS} días.", "warning")
            form.fecha.data = hoy
            es_valido = False

        # Tomar tipo de juicio
        tipo_juicio = form.tipo_juicio.data

        # Validar descripción
        descripcion = safe_string(form.descripcion.data, save_enie=True)
        if descripcion == "":
            flash("La descripción es incorrecta.", "warning")
            es_valido = False

        # Validar expediente
        try:
            expediente = safe_expediente(form.expediente.data)
        except IndexError, ValueError:
            flash("El expediente es incorrecto.", "warning")
            es_valido = False

        # Inicializar la liberia GCS con el directorio base, la fecha, las extensiones y los meses como palabras
        gcstorage = GoogleCloudStorage(
            base_directory=autoridad.directorio_glosas,
            upload_date=fecha,
            allowed_extensions=["pdf"],
            month_in_word=True,
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_GLOSAS"],
        )

        # Validar archivo
        archivo = request.files["archivo"]
        try:
            gcstorage.set_content_type(archivo.filename)
        except MyNotAllowedExtensionError:
            flash("Tipo de archivo no permitido.", "warning")
            es_valido = False
        except MyUnknownExtensionError:
            flash("Tipo de archivo desconocido.", "warning")
            es_valido = False

        # No es válido, entonces se vuelve a mostrar el formulario
        if es_valido is False:
            return render_template("glosas/new_for_autoridad.jinja2", form=form, autoridad=autoridad)

        # Insertar registro
        glosa = Glosa(
            autoridad=autoridad,
            fecha=fecha,
            tipo_juicio=tipo_juicio,
            descripcion=descripcion,
            expediente=form.expediente.data,
        )
        glosa.save()

        # Subir a Google Cloud Storage
        es_exitoso = True
        try:
            gcstorage.set_filename(hashed_id=glosa.encode_id(), description=descripcion)
            gcstorage.upload(archivo.stream.read())
        except MyFilenameError, MyNotAllowedExtensionError, MyUnknownExtensionError:
            flash("Error fatal al subir el archivo a GCS.", "warning")
            es_exitoso = False
        except MyMissingConfigurationError:
            flash("Error al subir el archivo porque falla la configuración de GCS.", "danger")
            es_exitoso = False
        except Exception:
            flash("Error desconocido al subir el archivo.", "danger")
            es_exitoso = False

        # Si se sube con éxito, actualizar el registro con la URL del archivo y mostrar el detalle
        if es_exitoso:
            glosa.archivo = gcstorage.filename  # Conservar el nombre original
            glosa.url = gcstorage.url
            glosa.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nueva Glosa de {autoridad.clave} sobre {glosa.descripcion}"),
                url=url_for("glosas.detail", glosa_id=glosa.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)

        # Como no se subio con exito, se cambia el estatus a "B"
        glosa.estatus = "B"
        glosa.save()

    # Valores por defecto
    form.distrito.data = autoridad.distrito.nombre
    form.autoridad.data = autoridad.descripcion
    form.fecha.data = hoy

    # Entregar el formulario
    return render_template("glosas/new_for_autoridad.jinja2", form=form, autoridad=autoridad)


@glosas.route("/glosas/editar/<int:glosa_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(glosa_id):
    """Editar Glosa"""
    local_tz = pytz.timezone(current_app.config["TZ"])

    # Consultar
    glosa = Glosa.query.get_or_404(glosa_id)

    # Si NO es administrador
    if not (current_user.can_admin(MODULO)):
        # Validar que le pertenezca
        if current_user.autoridad_id != glosa.autoridad_id:
            flash("No puede editar registros ajenos.", "warning")
            return redirect(url_for("glosas.list_active"))
        # Si fue creado hace más de LIMITES_DIAS_EDITAR
        if glosa.creado < datetime.now(tz=local_tz) - timedelta(days=LIMITE_DIAS_EDITAR):
            flash(f"Ya no puede editar porque fue creado hace más de {LIMITE_DIAS_EDITAR} dias.", "warning")
            return redirect(url_for("glosas.detail", glosa_id=glosa.id))

    # Definir la fecha límite
    hoy = date.today()
    hoy_dt = datetime(year=hoy.year, month=hoy.month, day=hoy.day)
    limite_dt = hoy_dt + timedelta(days=-LIMITE_DIAS)

    # Si viene el formulario
    form = GlosaEditForm()
    if form.validate_on_submit():
        es_valido = True

        # Validar fecha
        fecha = form.fecha.data
        if not limite_dt <= datetime(year=fecha.year, month=fecha.month, day=fecha.day) <= hoy_dt:
            flash(f"La fecha no debe ser del futuro ni anterior a {LIMITE_DIAS} días.", "warning")
            form.fecha.data = hoy
            es_valido = False

        # Tomar tipo de juicio
        tipo_juicio = form.tipo_juicio.data

        # Validar descripción
        descripcion = safe_string(form.descripcion.data, save_enie=True)
        if descripcion == "":
            flash("La descripción es incorrecta.", "warning")
            es_valido = False

        # Validar expediente
        try:
            expediente = safe_expediente(form.expediente.data)
        except IndexError, ValueError:
            flash("El expediente es incorrecto.", "warning")
            es_valido = False

        # Si es válido, entonces se guarda
        if es_valido:
            glosa.fecha = fecha
            glosa.tipo_juicio = tipo_juicio
            glosa.descripcion = descripcion
            glosa.expediente = expediente
            glosa.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editada la Glosa de {glosa.autoridad.clave} sobre {glosa.descripcion}"),
                url=url_for("glosas.detail", glosa_id=glosa.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)

    # Definir valores en el formulario
    form.fecha.data = glosa.fecha
    form.tipo_juicio.data = glosa.tipo_juicio
    form.descripcion.data = glosa.descripcion
    form.expediente.data = glosa.expediente

    # Entregar el formulario
    return render_template("glosas/edit.jinja2", form=form, glosa=glosa)


@glosas.route("/glosas/eliminar/<int:glosa_id>")
@permission_required(MODULO, Permiso.CREAR)
def delete(glosa_id):
    """Eliminar Glosa"""
    local_tz = pytz.timezone(current_app.config["TZ"])

    # Consultar
    glosa = Glosa.query.get_or_404(glosa_id)
    detalle_url = url_for("glosas.detail", glosa_id=glosa.id)

    # Validar que se pueda eliminar
    if glosa.estatus == "B":
        flash("No puede eliminar esta Glosa porque ya está eliminada.", "success")
        return redirect(detalle_url)

    # Definir la descripción para la bitácora
    descripcion = safe_message(f"Eliminada Glosa {glosa.id} por {current_user.email}")

    # Si es administrador, puede eliminar
    if current_user.can_admin(MODULO):
        glosa.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=descripcion,
            url=detalle_url,
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)

    # Si NO le pertenece, mostrar mensaje y redirigir
    if current_user.autoridad_id != glosa.autoridad_id:
        flash("No se puede eliminar porque no le pertenece.", "warning")
        return redirect(detalle_url)

    # Si fue creado hace menos del límite de días
    if glosa.creado >= datetime.now(tz=local_tz) - timedelta(days=LIMITE_DIAS_ELIMINAR):
        glosa.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=descripcion,
            url=detalle_url,
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)

    # No se puede eliminar
    flash(f"No se puede eliminar porque fue creado hace más de {LIMITE_DIAS_ELIMINAR} dias.", "warning")
    return redirect(detalle_url)


@glosas.route("/glosas/recuperar/<int:glosa_id>")
@permission_required(MODULO, Permiso.CREAR)
def recover(glosa_id):
    """Recuperar Glosa"""
    local_tz = pytz.timezone(current_app.config["TZ"])

    # Consultar
    glosa = Glosa.query.get_or_404(glosa_id)
    detalle_url = url_for("glosas.detail", glosa_id=glosa.id)

    # Validar que se pueda recuperar
    if glosa.estatus == "A":
        flash("No puede recuperar esta Glosa porque ya está activa.", "success")
        return redirect(detalle_url)

    # Definir la descripción para la bitácora
    descripcion = safe_message(f"Recuperada Glosa {glosa.id} por {current_user.email}")

    # Si es administrador, puede recuperar
    if current_user.can_admin(MODULO):
        glosa.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=descripcion,
            url=detalle_url,
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)

    # Si NO le pertenece, mostrar mensaje y redirigir
    if current_user.autoridad_id != glosa.autoridad_id:
        flash("No se puede recuperar porque no le pertenece.", "warning")
        return redirect(detalle_url)

    # Si fue creado hace menos del límite de días
    if glosa.creado >= datetime.now(tz=local_tz) - timedelta(days=LIMITE_DIAS_RECUPERAR):
        glosa.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=descripcion,
            url=detalle_url,
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)

    # No se puede recuperar
    flash(f"No se puede recuperar porque fue creado hace más de {LIMITE_DIAS_RECUPERAR} dias.", "warning")
    return redirect(detalle_url)


@glosas.route("/glosas/ver_archivo_pdf/<int:glosa_id>")
def view_file_pdf(glosa_id):
    """Ver archivo PDF de Glosa para insertarlo en un iframe en el detalle"""

    # Consultar
    glosa = Glosa.query.get_or_404(glosa_id)

    # Obtener el contenido del archivo
    try:
        archivo = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_GLOSAS"],
            blob_name=get_blob_name_from_url(glosa.url),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
        raise NotFound("No se encontró el archivo.") from error

    # Entregar el archivo
    response = make_response(archivo)
    response.headers["Content-Type"] = "application/pdf"
    return response


@glosas.route("/glosas/descargar_archivo_pdf/<int:glosa_id>")
def download_file_pdf(glosa_id):
    """Descargar archivo PDF de Glosa"""

    # Consultar
    glosa = Glosa.query.get_or_404(glosa_id)

    # Obtener el contenido del archivo
    try:
        archivo = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_GLOSAS"],
            blob_name=get_blob_name_from_url(glosa.url),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
        raise NotFound("No se encontró el archivo.") from error

    # Entregar el archivo
    response = make_response(archivo)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"attachment; filename={glosa.archivo}"
    return response
