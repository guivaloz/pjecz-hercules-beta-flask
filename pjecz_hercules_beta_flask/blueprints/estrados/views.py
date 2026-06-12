"""
Estrados, vistas
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
from pjecz_hercules_beta_flask.blueprints.estrados.forms import EstradoEditForm, EstradoNewForm
from pjecz_hercules_beta_flask.blueprints.estrados.models import Estrado
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

MODULO = "ESTRADOS"
LIMITE_DIAS = 30  # Treinta dias
LIMITE_DIAS_EDITAR = LIMITE_DIAS_ELIMINAR = LIMITE_DIAS_RECUPERAR = 7
LIMITE_ADMINISTRADORES_DIAS = 3650  # Administradores pueden manipular diez años

estrados = Blueprint("estrados", __name__, template_folder="templates")


@estrados.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@estrados.route("/estrados/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Estrados"""

    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()

    # Consultar
    consulta = Estrado.query

    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(Estrado.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(Estrado.estatus == "A")
    if "autoridad_id" in request.form:
        autoridad = Autoridad.query.get(request.form["autoridad_id"])
        if autoridad:
            consulta = consulta.filter(Estrado.autoridad_id == autoridad.id)
    elif "autoridad_clave" in request.form:
        autoridad_clave = safe_clave(request.form["autoridad_clave"])
        if autoridad_clave != "":
            consulta = consulta.join(Autoridad).filter(Autoridad.clave.contains(autoridad_clave))
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], save_enie=True)
        if descripcion != "":
            consulta = consulta.filter(Estrado.descripcion.contains(descripcion))

    # Ordenar y paginar
    registros = consulta.order_by(Estrado.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()

    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "fecha": resultado.fecha.strftime("%Y-%m-%d 00:00:00"),
                    "autoridad_clave": resultado.autoridad.clave,
                    "detalle": {
                        "descripcion": resultado.descripcion,
                        "url": url_for("edictos.detail", edicto_id=resultado.id),
                    },
                },
            }
        )

    # Entregar JSON
    return output_datatable_json(draw, total, data)


@estrados.route("/estrados/admin_datatable_json", methods=["GET", "POST"])
def admin_datatable_json():
    """DataTable JSON con Estrados para administrador"""

    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()

    # Consultar
    consulta = Estrado.query

    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(Estrado.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(Estrado.estatus == "A")
    if "autoridad_id" in request.form:
        consulta = consulta.filter(Estrado.autoridad_id == request.form["autoridad_id"])
    elif "autoridad_clave" in request.form:
        autoridad_clave = safe_clave(request.form["autoridad_clave"])
        if autoridad_clave != "":
            consulta = consulta.join(Autoridad).filter(Autoridad.clave.contains(autoridad_clave))
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], save_enie=True)
        if descripcion != "":
            consulta = consulta.filter(Estrado.descripcion.contains(descripcion))

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
        consulta = consulta.filter(Estrado.fecha >= creado_desde)
    if creado_hasta:
        consulta = consulta.filter(Estrado.fecha <= creado_hasta)

    # Ordenar y paginar
    registros = consulta.order_by(Estrado.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()

    # Elaborar datos para DataTable
    data = []
    for estrado in registros:
        data.append(
            {
                "detalle": {
                    "id": estrado.id,
                    "url": url_for("estrados.detail", estrado_id=estrado.id),
                },
                "creado": estrado.creado.strftime("%Y-%m-%dT%H:%M:%S"),
                "autoridad_clave": estrado.autoridad.clave,
                "fecha": estrado.fecha.strftime("%Y-%m-%d 00:00:00"),
                "descripcion": estrado.descripcion,
            }
        )

    # Entregar JSON
    return output_datatable_json(draw, total, data)


@estrados.route("/estrados")
def list_active():
    """Listado de Estrados activos"""
    filtros = None
    titulo = None
    mostrar_filtro_autoridad_clave = True

    # Si es administrador
    plantilla = "estrados/list.jinja2"
    if current_user.can_admin(MODULO):
        plantilla = "estrados/list_admin.jinja2"

    # Si viene autoridad_id o autoridad_clave en la URL, agregar a los filtros
    autoridad = None
    if "autoridad_id" in request.args and request.args.get("autoridad_id") is not None:
        autoridad = Autoridad.query.get(request.args.get("autoridad_id"))
    elif "autoridad_clave" in request.args:
        autoridad_clave = safe_clave(request.args.get("autoridad_clave"))
        autoridad = Autoridad.query.filter_by(clave=autoridad_clave).first()
    if autoridad is not None:
        filtros = {"estatus": "A", "autoridad_id": autoridad.id}
        titulo = f"Estrados de {autoridad.descripcion_corta}"
        mostrar_filtro_autoridad_clave = False

    # Si es administrador
    if titulo is None and current_user.can_admin(MODULO):
        titulo = "Todos los Estrados"
        filtros = {"estatus": "A"}

    # Si puede editar o crear, solo ve lo de su autoridad
    if titulo is None and (current_user.can_insert(MODULO) or current_user.can_edit(MODULO)):
        filtros = {"estatus": "A", "autoridad_id": current_user.autoridad.id}
        titulo = f"Estrados de {current_user.autoridad.descripcion_corta}"
        mostrar_filtro_autoridad_clave = False

    # De lo contrario, es observador
    if titulo is None:
        filtros = {"estatus": "A"}
        titulo = "Estrados"

    # Entregar
    return render_template(
        plantilla,
        autoridad=autoridad,
        filtros=json.dumps(filtros),
        titulo=titulo,
        mostrar_filtro_autoridad_clave=mostrar_filtro_autoridad_clave,
        estatus="A",
    )


@estrados.route("/estrados/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Estrados inactivos"""
    return render_template(
        "estrados/list.jinja2",
        estatus="B",
        filtros={"estatus": "B"},
        titulo="Estrados inactivos",
    )


@estrados.route("/estrados/<int:estrado_id>")
def detail(estrado_id):
    """Detalle de un Estrado"""
    estrado = Estrado.query.get_or_404(estrado_id)
    return render_template("estrados/detail.jinja2", estrado=estrado)


@estrados.route("/estrados/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Subir Estrado como juzgado"""

    # Validar autoridad
    autoridad = current_user.autoridad
    if autoridad is None or autoridad.estatus != "A":
        flash("El juzgado/autoridad no existe o no es activa.", "warning")
        return redirect(url_for("estrados.list_active"))
    if not autoridad.distrito.es_distrito_judicial:
        flash("El juzgado/autoridad no está en un distrito jurisdiccional.", "warning")
        return redirect(url_for("estrados.list_active"))
    if not autoridad.es_jurisdiccional:
        flash("El juzgado/autoridad no es jurisdiccional.", "warning")
        return redirect(url_for("estrados.list_active"))
    if autoridad.directorio_estrados is None or autoridad.directorio_estrados == "":
        flash("El juzgado/autoridad no tiene directorio para estrados.", "warning")
        return redirect(url_for("estrados.list_active"))

    # Definir la fecha límite para el juzgado
    hoy = date.today()
    hoy_dt = datetime(year=hoy.year, month=hoy.month, day=hoy.day)
    limite_dt = hoy_dt + timedelta(days=-LIMITE_DIAS)

    # Si viene el formulario
    form = EstradoNewForm(CombinedMultiDict((request.files, request.form)))
    if form.validate_on_submit():
        es_valido = True

        # Validar fecha
        fecha = form.fecha.data
        if not limite_dt <= datetime(year=fecha.year, month=fecha.month, day=fecha.day) <= hoy_dt:
            flash(f"La fecha no debe ser del futuro ni anterior a {LIMITE_DIAS} días.", "warning")
            form.fecha.data = hoy
            es_valido = False

        # Validar descripción
        descripcion = safe_string(form.descripcion.data, save_enie=True)
        if descripcion == "":
            flash("La descripción es incorrecta.", "warning")
            es_valido = False

        # Inicializar la liberia GCS con el directorio base, la fecha, las extensiones y los meses como palabras
        gcstorage = GoogleCloudStorage(
            base_directory=autoridad.directorio_estrados,
            upload_date=fecha,
            allowed_extensions=["pdf"],
            month_in_word=True,
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_ESTRADOS"],
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
        estrado = Estrado(
            autoridad=autoridad,
            fecha=fecha,
            descripcion=descripcion,
        )
        estrado.save()

        # Subir a Google Cloud Storage
        es_exitoso = True
        try:
            gcstorage.set_filename(hashed_id=estrado.encode_id(), description=descripcion)
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
            estrado.archivo = gcstorage.filename  # Conservar el nombre original
            estrado.url = gcstorage.url
            estrado.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nuevo Estrado de {autoridad.clave} sobre {estrado.descripcion}"),
                url=url_for("estrados.detail", estrado_id=estrado.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)

        # Como no se subio con exito, se cambia el estatus a "B"
        estrado.estatus = "B"
        estrado.save()

    # Valores por defecto
    form.distrito.data = autoridad.distrito.nombre
    form.autoridad.data = autoridad.descripcion
    form.fecha.data = hoy

    # Entregar el formulario
    return render_template("estrados/new.jinja2", form=form)


@estrados.route("/estrados/nuevo/<int:autoridad_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.ADMINISTRAR)
def new_with_autoridad_id(autoridad_id):
    """Subir Estrado para una autoridad como administrador"""

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
    if autoridad.directorio_estrados is None or autoridad.directorio_estrados == "":
        flash("El juzgado/autoridad no tiene directorio para estrados.", "warning")
        return redirect(url_for("autoridades.detail", autoridad_id=autoridad.id))

    # Para validar las fechas
    hoy = date.today()
    hoy_dt = datetime(year=hoy.year, month=hoy.month, day=hoy.day)
    limite_dt = hoy_dt + timedelta(days=-LIMITE_ADMINISTRADORES_DIAS)

    # Si viene el formulario
    form = EstradoNewForm(CombinedMultiDict((request.files, request.form)))
    if form.validate_on_submit():
        es_valido = True

        # Validar fecha
        fecha = form.fecha.data
        if not limite_dt <= datetime(year=fecha.year, month=fecha.month, day=fecha.day) <= hoy_dt:
            flash(f"La fecha no debe ser del futuro ni anterior a {LIMITE_ADMINISTRADORES_DIAS} días.", "warning")
            form.fecha.data = hoy
            es_valido = False

        # Validar descripción
        descripcion = safe_string(form.descripcion.data, save_enie=True)
        if descripcion == "":
            flash("La descripción es incorrecta.", "warning")
            es_valido = False

        # Inicializar la liberia GCS con el directorio base, la fecha, las extensiones y los meses como palabras
        gcstorage = GoogleCloudStorage(
            base_directory=autoridad.directorio_estrados,
            upload_date=fecha,
            allowed_extensions=["pdf"],
            month_in_word=True,
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_ESTRADOS"],
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
            return render_template("estrados/new_for_autoridad.jinja2", form=form, autoridad=autoridad)

        # Insertar registro
        estrado = Estrado(
            autoridad=autoridad,
            fecha=fecha,
            tipo_juicio=tipo_juicio,
            descripcion=descripcion,
            expediente=form.expediente.data,
        )
        estrado.save()

        # Subir a Google Cloud Storage
        es_exitoso = True
        try:
            gcstorage.set_filename(hashed_id=estrado.encode_id(), description=descripcion)
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
            estrado.archivo = gcstorage.filename  # Conservar el nombre original
            estrado.url = gcstorage.url
            estrado.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nueva Estrado de {autoridad.clave} sobre {estrado.descripcion}"),
                url=url_for("estrados.detail", estrado_id=estrado.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)

        # Como no se subio con exito, se cambia el estatus a "B"
        estrado.estatus = "B"
        estrado.save()

    # Valores por defecto
    form.distrito.data = autoridad.distrito.nombre
    form.autoridad.data = autoridad.descripcion
    form.fecha.data = hoy

    # Entregar el formulario
    return render_template("estrados/new_for_autoridad.jinja2", form=form, autoridad=autoridad)


@estrados.route("/estrados/editar/<int:estrado_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(estrado_id):
    """Editar Estrado"""
    local_tz = pytz.timezone(current_app.config["TZ"])

    # Consultar
    estrado = Estrado.query.get_or_404(estrado_id)

    # Si NO es administrador
    if not (current_user.can_admin(MODULO)):
        # Validar que le pertenezca
        if current_user.autoridad_id != estrado.autoridad_id:
            flash("No puede editar registros ajenos.", "warning")
            return redirect(url_for("estrados.list_active"))
        # Si fue creado hace más de LIMITES_DIAS_EDITAR
        if estrado.creado < datetime.now(tz=local_tz) - timedelta(days=LIMITE_DIAS_EDITAR):
            flash(f"Ya no puede editar porque fue creado hace más de {LIMITE_DIAS_EDITAR} dias.", "warning")
            return redirect(url_for("estrados.detail", estrado_id=estrado.id))

    # Definir la fecha límite
    hoy = date.today()
    hoy_dt = datetime(year=hoy.year, month=hoy.month, day=hoy.day)
    limite_dt = hoy_dt + timedelta(days=-LIMITE_DIAS)

    # Si viene el formulario
    form = EstradoEditForm()
    if form.validate_on_submit():
        es_valido = True

        # Validar fecha
        fecha = form.fecha.data
        if not limite_dt <= datetime(year=fecha.year, month=fecha.month, day=fecha.day) <= hoy_dt:
            flash(f"La fecha no debe ser del futuro ni anterior a {LIMITE_DIAS} días.", "warning")
            form.fecha.data = hoy
            es_valido = False

        # Validar descripción
        descripcion = safe_string(form.descripcion.data, save_enie=True)
        if descripcion == "":
            flash("La descripción es incorrecta.", "warning")
            es_valido = False

        # Si es válido, entonces se guarda
        if es_valido:
            estrado.fecha = fecha
            estrado.descripcion = descripcion
            estrado.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado el Estrado de {estrado.autoridad.clave} sobre {estrado.descripcion}"),
                url=url_for("glosas.detail", glosa_id=estrado.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)

    # Definir valores en el formulario
    form.fecha.data = estrado.fecha
    form.descripcion.data = estrado.descripcion

    # Entregar el formulario
    return render_template("glosas/edit.jinja2", form=form, glosa=estrado)


@estrados.route("/estrados/eliminar/<int:estrado_id>")
@permission_required(MODULO, Permiso.CREAR)
def delete(estrado_id):
    """Eliminar Estrado"""
    local_tz = pytz.timezone(current_app.config["TZ"])

    # Consultar
    estrado = Estrado.query.get_or_404(estrado_id)
    detalle_url = url_for("estrados.detail", estrado_id=estrado.id)

    # Validar que se pueda eliminar
    if estrado.estatus == "B":
        flash("No puede eliminar este Estrado porque ya está eliminado.", "success")
        return redirect(detalle_url)

    # Definir la descripción para la bitácora
    descripcion = safe_message(f"Eliminado Estrado {estrado.id} por {current_user.email}")

    # Si es administrador, puede eliminar
    if current_user.can_admin(MODULO):
        estrado.delete()
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
    if current_user.autoridad_id != estrado.autoridad_id:
        flash("No se puede eliminar porque no le pertenece.", "warning")
        return redirect(detalle_url)

    # Si fue creado hace menos del límite de días
    if estrado.creado >= datetime.now(tz=local_tz) - timedelta(days=LIMITE_DIAS_ELIMINAR):
        estrado.delete()
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


@estrados.route("/estrados/recuperar/<int:estrado_id>")
@permission_required(MODULO, Permiso.CREAR)
def recover(estrado_id):
    """Recuperar Estrado"""
    local_tz = pytz.timezone(current_app.config["TZ"])

    # Consultar
    estrado = Estrado.query.get_or_404(estrado_id)
    detalle_url = url_for("estrados.detail", estrado_id=estrado.id)

    # Validar que se pueda recuperar
    if estrado.estatus == "A":
        flash("No puede recuperar este estrado porque ya está activo.", "success")
        return redirect(detalle_url)

    # Definir la descripción para la bitácora
    descripcion = safe_message(f"Recuperado Estrado {estrado.id} por {current_user.email}")

    # Si es administrador, puede recuperar
    if current_user.can_admin(MODULO):
        estrado.recover()
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
    if current_user.autoridad_id != estrado.autoridad_id:
        flash("No se puede recuperar porque no le pertenece.", "warning")
        return redirect(detalle_url)

    # Si fue creado hace menos del límite de días
    if estrado.creado >= datetime.now(tz=local_tz) - timedelta(days=LIMITE_DIAS_RECUPERAR):
        estrado.recover()
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


@estrados.route("/estrados/ver_archivo_pdf/<int:estrado_id>")
def view_file_pdf(estrado_id):
    """Ver archivo PDF de Estrado para insertarlo en un iframe en el detalle"""

    # Consultar
    estrado = Estrado.query.get_or_404(estrado_id)

    # Obtener el contenido del archivo
    try:
        archivo = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_ESTRADOS"],
            blob_name=get_blob_name_from_url(estrado.url),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
        raise NotFound("No se encontró el archivo.") from error

    # Entregar el archivo
    response = make_response(archivo)
    response.headers["Content-Type"] = "application/pdf"
    return response


@estrados.route("/estrados/descargar_archivo_pdf/<int:estrado_id>")
def download_file_pdf(estrado_id):
    """Descargar archivo PDF de Estrado"""

    # Consultar
    estrado = Estrado.query.get_or_404(estrado_id)

    # Obtener el contenido del archivo
    try:
        archivo = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_ESTRADOS"],
            blob_name=get_blob_name_from_url(estrado.url),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
        raise NotFound("No se encontró el archivo.") from error

    # Entregar el archivo
    response = make_response(archivo)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"attachment; filename={estrado.archivo}"
    return response
