"""
Listas de Acuerdos, vistas
"""

import json
import re
from datetime import datetime, time, timedelta

import pytz
from flask import Blueprint, current_app, flash, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.datastructures import CombinedMultiDict
from werkzeug.exceptions import NotFound

from pjecz_hercules_beta_flask.blueprints.autoridades.models import Autoridad
from pjecz_hercules_beta_flask.blueprints.bitacoras.models import Bitacora
from pjecz_hercules_beta_flask.blueprints.listas_de_acuerdos.forms import ListaDeAcuerdoMateriaNewForm, ListaDeAcuerdoNewForm
from pjecz_hercules_beta_flask.blueprints.listas_de_acuerdos.models import ListaDeAcuerdo
from pjecz_hercules_beta_flask.blueprints.materias.models import Materia
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
from pjecz_hercules_beta_flask.lib.safe_string import safe_clave, safe_message
from pjecz_hercules_beta_flask.lib.storage import GoogleCloudStorage

MODULO = "LISTAS DE ACUERDOS"
HORAS_BUENO = 14  # Bandera verde si se creó antes de 14 horas del día
HORAS_CRITICO = 16  # Bandera roja si se creó después de 16 horas del día
LIMITE_DIAS = 365  # Un año, aunque autoridad.limite_dias_listas_de_acuerdos sea mayor, gana el menor
LIMITE_DIAS_ELIMINAR = LIMITE_DIAS_RECUPERAR = 1
LIMITE_ADMINISTRADORES_DIAS = 3650  # Administradores pueden manipular diez años
ORGANOS_JURISDICCIONALES_QUE_PUEDEN_ELEGIR_MATERIA = (
    "JUZGADO DE PRIMERA INSTANCIA ORAL",
    "PLENO O SALA DEL TSJ",
    "TRIBUNAL DISTRITAL",
)

listas_de_acuerdos = Blueprint("listas_de_acuerdos", __name__, template_folder="templates")


@listas_de_acuerdos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@listas_de_acuerdos.route("/listas_de_acuerdos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Listas de Acuerdos"""
    local_tz = pytz.timezone(current_app.config["TZ"])
    medianoche = time.min

    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()

    # Consultar
    consulta = ListaDeAcuerdo.query

    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(ListaDeAcuerdo.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(ListaDeAcuerdo.estatus == "A")
    if "estatus" in request.form:
        consulta = consulta.filter(ListaDeAcuerdo.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(ListaDeAcuerdo.estatus == "A")
    if "autoridad_id" in request.form:
        autoridad = Autoridad.query.get(request.form["autoridad_id"])
        if autoridad:
            consulta = consulta.filter(ListaDeAcuerdo.autoridad_id == autoridad.id)
    elif "autoridad_clave" in request.form:
        autoridad_clave = safe_clave(request.form["autoridad_clave"])
        if autoridad_clave != "":
            consulta = consulta.join(Autoridad).filter(Autoridad.clave.contains(autoridad_clave))

    # Filtrar por fechas, si vienen invertidas se corrigen
    fecha_desde = None
    fecha_hasta = None
    if "fecha_desde" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["fecha_desde"]):
        fecha_desde = request.form["fecha_desde"]
    if "fecha_hasta" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["fecha_hasta"]):
        fecha_hasta = request.form["fecha_hasta"]
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        fecha_desde, fecha_hasta = fecha_hasta, fecha_desde
    if fecha_desde:
        consulta = consulta.filter(ListaDeAcuerdo.fecha >= fecha_desde)
    if fecha_hasta:
        consulta = consulta.filter(ListaDeAcuerdo.fecha <= fecha_hasta)

    # Ordenar y paginar
    registros = consulta.order_by(ListaDeAcuerdo.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()

    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        # La columna creado esta en UTC, convertir a local
        creado_local = resultado.creado.astimezone(local_tz)
        # Determinar el tiempo bueno
        tiempo_limite_bueno = datetime.combine(resultado.fecha, medianoche) + timedelta(hours=HORAS_BUENO)
        # Determinar el tiempo critico
        tiempo_limite_critico = datetime.combine(resultado.fecha, medianoche) + timedelta(hours=HORAS_CRITICO)
        # Por defecto el semáforo es verde (0)
        semaforo = 0
        # Si creado_local es mayor a tiempo_limite_bueno, entonces el semáforo es amarillo (1)
        if creado_local > local_tz.localize(tiempo_limite_bueno):
            semaforo = 1
        # Si creado_local es mayor a tiempo_limite_critico, entonces el semáforo es rojo (2)
        if creado_local > local_tz.localize(tiempo_limite_critico):
            semaforo = 2
        # Acumular fila
        data.append(
            {
                "detalle": {
                    "fecha": resultado.fecha.strftime("%Y-%m-%d 00:00:00"),
                    "url": url_for("listas_de_acuerdos.detail", lista_de_acuerdo_id=resultado.id),
                },
                "autoridad_clave": resultado.autoridad.clave,
                "descripcion": resultado.descripcion,
                "creado": {
                    "tiempo": creado_local.strftime("%Y-%m-%dT%H:%M:%S"),
                    "semaforo": semaforo,
                },
            }
        )

    # Entregar JSON
    return output_datatable_json(draw, total, data)


@listas_de_acuerdos.route("/listas_de_acuerdos/admin_datatable_json", methods=["GET", "POST"])
def admin_datatable_json():
    """DataTable JSON con Lista De Acuerdos para administrador"""
    local_tz = pytz.timezone(current_app.config["TZ"])
    medianoche = time.min

    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()

    # Consultar
    consulta = ListaDeAcuerdo.query

    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(ListaDeAcuerdo.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(ListaDeAcuerdo.estatus == "A")
    if "autoridad_id" in request.form:
        consulta = consulta.filter(ListaDeAcuerdo.autoridad_id == request.form["autoridad_id"])
    elif "autoridad_clave" in request.form:
        autoridad_clave = safe_clave(request.form["autoridad_clave"])
        if autoridad_clave != "":
            consulta = consulta.join(Autoridad).filter(Autoridad.clave.contains(autoridad_clave))

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
        consulta = consulta.filter(ListaDeAcuerdo.fecha >= creado_desde)
    if creado_hasta:
        consulta = consulta.filter(ListaDeAcuerdo.fecha <= creado_hasta)

    # Ordenar y paginar
    registros = consulta.order_by(ListaDeAcuerdo.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()

    # Elaborar datos para DataTable
    data = []
    for lista_de_acuerdo in registros:
        # La columna creado esta en UTC, convertir a local
        creado_local = lista_de_acuerdo.creado.astimezone(local_tz)
        # Determinar el tiempo bueno
        tiempo_limite_bueno = datetime.combine(lista_de_acuerdo.fecha, medianoche) + timedelta(hours=HORAS_BUENO)
        # Determinar el tiempo critico
        tiempo_limite_critico = datetime.combine(lista_de_acuerdo.fecha, medianoche) + timedelta(hours=HORAS_CRITICO)
        # Por defecto el semáforo es verde (0)
        semaforo = 0
        # Si la autoridad tiene limite_dias_listas_de_acuerdos igual a cero
        if lista_de_acuerdo.autoridad.limite_dias_listas_de_acuerdos == 0:
            # Si creado_local es mayor a tiempo_limite_bueno, entonces el semáforo es amarillo (1)
            if creado_local > local_tz.localize(tiempo_limite_bueno):
                semaforo = 1
            # Si creado_local es mayor a tiempo_limite_critico, entonces el semáforo es rojo (2)
            if creado_local > local_tz.localize(tiempo_limite_critico):
                semaforo = 2
        # Acumular datos
        data.append(
            {
                "detalle": {
                    "id": lista_de_acuerdo.id,
                    "url": url_for("listas_de_acuerdos.detail", lista_de_acuerdo_id=lista_de_acuerdo.id),
                },
                "creado": {
                    "tiempo": lista_de_acuerdo.creado.strftime("%Y-%m-%dT%H:%M:%S"),
                    "semaforo": semaforo,
                },
                "autoridad_clave": lista_de_acuerdo.autoridad.clave,
                "fecha": lista_de_acuerdo.fecha.strftime("%Y-%m-%d 00:00:00"),
                "descripcion": lista_de_acuerdo.descripcion,
            }
        )

    # Entregar JSON
    return output_datatable_json(draw, total, data)


@listas_de_acuerdos.route("/listas_de_acuerdos")
def list_active():
    """Listado de Listas de Acuerdos activos"""
    filtros = None
    titulo = None
    mostrar_filtro_autoridad_clave = True

    # Si es administrador
    plantilla = "listas_de_acuerdos/list.jinja2"
    if current_user.can_admin(MODULO):
        plantilla = "listas_de_acuerdos/list_admin.jinja2"

    # Si viene autoridad_id o autoridad_clave en la URL, agregar a los filtros
    autoridad = None
    if "autoridad_id" in request.args and request.args.get("autoridad_id") is not None:
        autoridad = Autoridad.query.get(request.args.get("autoridad_id"))
    elif "autoridad_clave" in request.args:
        autoridad_clave = safe_clave(request.args.get("autoridad_clave"))
        autoridad = Autoridad.query.filter_by(clave=autoridad_clave).first()
    if autoridad is not None:
        filtros = {"estatus": "A", "autoridad_id": autoridad.id}
        titulo = f"Listas de Acuerdos de {autoridad.descripcion_corta}"
        mostrar_filtro_autoridad_clave = False

    # Si es administrador
    if titulo is None and current_user.can_admin(MODULO):
        titulo = "Todas las Listas de Acuerdos"
        filtros = {"estatus": "A"}

    # Si puede editar o crear, solo ve lo de su autoridad
    if titulo is None and (current_user.can_insert(MODULO) or current_user.can_edit(MODULO)):
        filtros = {"estatus": "A", "autoridad_id": current_user.autoridad.id}
        titulo = f"Listas de Acuerdos de {current_user.autoridad.descripcion_corta}"
        mostrar_filtro_autoridad_clave = False

    # De lo contrario, es observador
    if titulo is None:
        filtros = {"estatus": "A"}
        titulo = "Listas de Acuerdos"

    # Entregar
    return render_template(
        plantilla,
        autoridad=autoridad,
        filtros=json.dumps(filtros),
        titulo=titulo,
        mostrar_filtro_autoridad_clave=mostrar_filtro_autoridad_clave,
        estatus="A",
    )


@listas_de_acuerdos.route("/listas_de_acuerdos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Listas de Acuerdos inactivos"""
    return render_template(
        "listas_de_acuerdos/list.jinja2",
        estatus="B",
        filtros={"estatus": "B"},
        titulo="Listas de Acuerdos inactivos",
    )


@listas_de_acuerdos.route("/listas_de_acuerdos/<int:lista_de_acuerdo_id>")
def detail(lista_de_acuerdo_id):
    """Detalle de un Lista de Acuerdo"""
    lista_de_acuerdo = ListaDeAcuerdo.query.get_or_404(lista_de_acuerdo_id)
    title = f"Lista de Acuerdos {lista_de_acuerdo.fecha.strftime('%Y-%m-%d')} del {lista_de_acuerdo.autoridad.clave}"
    return render_template("listas_de_acuerdos/detail.jinja2", lista_de_acuerdo=lista_de_acuerdo, title=title)


@listas_de_acuerdos.route("/listas_de_acuerdos/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Subir ListaDeAcuerdo como Juzgado"""
    local_tz = pytz.timezone(current_app.config["TZ"])

    # Validar autoridad
    autoridad = current_user.autoridad
    if autoridad is None or autoridad.estatus != "A":
        flash("El juzgado/autoridad no existe o no es activa.", "warning")
        return redirect(url_for("listas_de_acuerdos.list_active"))
    if not autoridad.distrito.es_distrito_judicial:
        flash("El juzgado/autoridad no está en un distrito jurisdiccional.", "warning")
        return redirect(url_for("listas_de_acuerdos.list_active"))
    if not autoridad.es_jurisdiccional:
        flash("El juzgado/autoridad no es jurisdiccional.", "warning")
        return redirect(url_for("listas_de_acuerdos.list_active"))
    if autoridad.directorio_listas_de_acuerdos is None or autoridad.directorio_listas_de_acuerdos == "":
        flash("El juzgado/autoridad no tiene directorio para listas de acuerdos.", "warning")
        return redirect(url_for("listas_de_acuerdos.list_active"))

    # Google App Engine usa tiempo universal, sin esta correccion las fechas de la noche cambian al dia siguiente
    ahora_utc = datetime.now(timezone("UTC"))
    ahora_mx_coah = ahora_utc.astimezone(local_tz)

    # Definir la fecha límite para el juzgado
    hoy = ahora_mx_coah.date()
    hoy_dt = ahora_mx_coah
    if autoridad.limite_dias_listas_de_acuerdos < LIMITE_DIAS:
        mi_limite_dias = autoridad.limite_dias_listas_de_acuerdos
    else:
        mi_limite_dias = LIMITE_DIAS
    if mi_limite_dias > 0:
        limite_dt = hoy_dt + timedelta(days=-mi_limite_dias)
    else:
        limite_dt = hoy_dt

    # Decidir entre formulario sin materia o con materia
    con_materia = autoridad.organo_jurisdiccional in ORGANOS_JURISDICCIONALES_QUE_PUEDEN_ELEGIR_MATERIA
    if con_materia:
        form = ListaDeAcuerdoMateriaNewForm(CombinedMultiDict((request.files, request.form)))
    else:
        form = ListaDeAcuerdoNewForm(CombinedMultiDict((request.files, request.form)))

    # Si viene el formulario
    if form.validate_on_submit():
        es_valido = True

        # Validar fecha
        if mi_limite_dias > 0:
            fecha = form.fecha.data
            if not limite_dt <= datetime(year=fecha.year, month=fecha.month, day=fecha.day, tzinfo=local_tz) <= hoy_dt:
                flash(f"La fecha no debe ser del futuro ni anterior a {mi_limite_dias} días.", "warning")
                es_valido = False
        else:
            fecha = hoy

        # Inicializar la liberia GCS con el directorio base, la fecha, las extensiones y los meses como palabras
        gcstorage = GoogleCloudStorage(
            base_directory=autoridad.directorio_listas_de_acuerdos,
            upload_date=fecha,
            allowed_extensions=["pdf"],
            month_in_word=True,
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_LISTAS_DE_ACUERDOS"],
        )

        # Validar archivo
        archivo = request.files["archivo"]
        try:
            gcstorage.set_content_type(archivo.filename)
        except MyFilenameError, MyNotAllowedExtensionError, MyUnknownExtensionError:
            flash("Tipo de archivo no permitido.", "warning")
            es_valido = False
        except Exception:
            flash("Error desconocido al validar el archivo.", "danger")
            es_valido = False

        # No es válido, entonces se vuelve a mostrar el formulario
        if es_valido is False:
            return render_template(
                "listas_de_acuerdos/new.jinja2",
                form=form,
                mi_limite_dias=mi_limite_dias,
                con_materia=con_materia,
            )

        # Definir descripción
        descripcion = "LISTA DE ACUERDOS"
        if con_materia:
            materia_id = form.materia.data  # Es un SelectField
            materia = Materia.query.get(materia_id)
            if materia.nombre != "NO DEFINIDO":
                descripcion = f"LISTA DE ACUERDOS {materia.nombre}"

        # Si existe una lista de acuerdos de la misma fecha, dar de baja la antigua
        anterior_borrada = False
        if con_materia is False:
            anterior_lista_de_acuerdo = (
                ListaDeAcuerdo.query.filter(ListaDeAcuerdo.autoridad == autoridad)
                .filter(ListaDeAcuerdo.fecha == fecha)
                .filter_by(estatus="A")
                .first()
            )
            if anterior_lista_de_acuerdo:
                anterior_lista_de_acuerdo.delete()
                anterior_borrada = True
        else:
            anterior_lista_de_acuerdo = (
                ListaDeAcuerdo.query.filter(ListaDeAcuerdo.autoridad == autoridad)
                .filter(ListaDeAcuerdo.fecha == fecha)
                .filter_by(descripcion=descripcion)
                .filter_by(estatus="A")
                .first()
            )
            if anterior_lista_de_acuerdo:
                anterior_lista_de_acuerdo.delete()
                anterior_borrada = True

        # Insertar registro
        lista_de_acuerdo = ListaDeAcuerdo(
            autoridad=autoridad,
            fecha=fecha,
            descripcion=descripcion,
        )
        lista_de_acuerdo.save()

        # Subir a Google Cloud Storage
        es_exitoso = True
        try:
            gcstorage.set_filename(hashed_id=lista_de_acuerdo.encode_id(), description=descripcion)
            gcstorage.upload(archivo.stream.read())
        except MyFilenameError, MyNotAllowedExtensionError, MyUnknownExtensionError:
            flash("Tipo de archivo no permitido.", "warning")
            es_exitoso = False
        except Exception:
            flash("Error desconocido al subir el archivo.", "danger")
            es_exitoso = False

        # Si se sube con éxito, actualizar el registro con la URL del archivo y mostrar el detalle
        if es_exitoso:
            lista_de_acuerdo.archivo = gcstorage.filename
            lista_de_acuerdo.url = gcstorage.url
            lista_de_acuerdo.save()
            if anterior_borrada:
                bitacora_descripcion = "Reemplazada "
            else:
                bitacora_descripcion = "Nueva "
            bitacora_descripcion += f"Lista de Acuerdos de {autoridad.clave} del {lista_de_acuerdo.fecha.strftime('%Y-%m-%d')}"
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(bitacora_descripcion),
                url=url_for("listas_de_acuerdos.detail", lista_de_acuerdo_id=lista_de_acuerdo.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)

    # Llenar de los campos del formulario
    form.distrito.data = autoridad.distrito.nombre
    form.autoridad.data = autoridad.descripcion
    form.fecha.data = hoy

    # Si puede elegir la materia
    if con_materia:
        materia_por_defecto = Materia.query.get(1)
        form.materia.data = materia_por_defecto.id  # Es un SelectField, se necesita el id

    # Mostrar formulario
    return render_template(
        "listas_de_acuerdos/new.jinja2",
        form=form,
        mi_limite_dias=mi_limite_dias,
        con_materia=con_materia,
    )


@listas_de_acuerdos.route("/listas_de_acuerdos/nuevo_con_autoridad_id/<int:autoridad_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.ADMINISTRAR)
def new_with_autoridad_id(autoridad_id):
    """Subir ListaDeAcuerdo para una autoridad como administrador"""

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
    if autoridad.directorio_listas_de_acuerdos is None or autoridad.directorio_listas_de_acuerdos == "":
        flash("El juzgado/autoridad no tiene directorio para listas de acuerdos.", "warning")
        return redirect(url_for("autoridades.detail", autoridad_id=autoridad.id))

    # Google App Engine usa tiempo universal, sin esta correccion las fechas de la noche cambian al dia siguiente
    ahora_utc = datetime.now(timezone("UTC"))
    ahora_mx_coah = ahora_utc.astimezone(local_tz)

    # Para validar la fecha
    hoy = ahora_mx_coah.date()
    hoy_dt = ahora_mx_coah
    limite_dt = hoy_dt + timedelta(days=-LIMITE_ADMINISTRADORES_DIAS)

    # Decidir entre formulario sin materia o con materia
    con_materia = autoridad.organo_jurisdiccional in ORGANOS_JURISDICCIONALES_QUE_PUEDEN_ELEGIR_MATERIA
    if con_materia:
        form = ListaDeAcuerdoMateriaNewForm(CombinedMultiDict((request.files, request.form)))
    else:
        form = ListaDeAcuerdoNewForm(CombinedMultiDict((request.files, request.form)))

    # Si viene el formulario
    if form.validate_on_submit():
        es_valido = True

        # Validar fecha
        fecha = form.fecha.data
        if not limite_dt <= datetime(year=fecha.year, month=fecha.month, day=fecha.day, tzinfo=local_tz) <= hoy_dt:
            flash(f"La fecha no debe ser del futuro ni anterior a {LIMITE_ADMINISTRADORES_DIAS} días.", "warning")
            es_valido = False

        # Inicializar la liberia GCS con el directorio base, la fecha, las extensiones y los meses como palabras
        gcstorage = GoogleCloudStorage(
            base_directory=autoridad.directorio_listas_de_acuerdos,
            upload_date=fecha,
            allowed_extensions=["pdf"],
            month_in_word=True,
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_LISTAS_DE_ACUERDOS"],
        )

        # Validar archivo
        archivo = request.files["archivo"]
        try:
            gcstorage.set_content_type(archivo.filename)
        except MyFilenameError, MyNotAllowedExtensionError, MyUnknownExtensionError:
            flash("Tipo de archivo no permitido.", "warning")
            es_valido = False
        except Exception:
            flash("Error desconocido al validar el archivo.", "danger")
            es_valido = False

        # No es válido, entonces se vuelve a mostrar el formulario
        if es_valido is False:
            return render_template(
                "listas_de_acuerdos/new_for_autoridad.jinja2",
                form=form,
                autoridad=autoridad,
                con_materia=con_materia,
            )

        # Definir descripción
        descripcion = "LISTA DE ACUERDOS"
        if con_materia:
            materia_id = form.materia.data  # Es un SelectField
            materia = Materia.query.get(materia_id)
            if materia.nombre != "NO DEFINIDO":
                descripcion = f"LISTA DE ACUERDOS {materia.nombre}"

        # Si existe una lista de acuerdos de la misma fecha, dar de baja la antigua
        anterior_borrada = False
        if con_materia is False:
            anterior_lista_de_acuerdo = (
                ListaDeAcuerdo.query.filter(ListaDeAcuerdo.autoridad == autoridad)
                .filter(ListaDeAcuerdo.fecha == fecha)
                .filter_by(estatus="A")
                .first()
            )
            if anterior_lista_de_acuerdo:
                anterior_lista_de_acuerdo.delete()
                anterior_borrada = True
        else:
            anterior_lista_de_acuerdo = (
                ListaDeAcuerdo.query.filter(ListaDeAcuerdo.autoridad == autoridad)
                .filter(ListaDeAcuerdo.fecha == fecha)
                .filter_by(descripcion=descripcion)
                .filter_by(estatus="A")
                .first()
            )
            if anterior_lista_de_acuerdo:
                anterior_lista_de_acuerdo.delete()
                anterior_borrada = True

        # Insertar registro
        lista_de_acuerdo = ListaDeAcuerdo(
            autoridad=autoridad,
            fecha=fecha,
            descripcion=descripcion,
        )
        lista_de_acuerdo.save()

        # Subir a Google Cloud Storage
        es_exitoso = True
        try:
            gcstorage.set_filename(hashed_id=lista_de_acuerdo.encode_id(), description=descripcion)
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
            lista_de_acuerdo.archivo = gcstorage.filename
            lista_de_acuerdo.url = gcstorage.url
            lista_de_acuerdo.save()
            if anterior_borrada:
                bitacora_descripcion = "Reemplazada "
            else:
                bitacora_descripcion = "Nueva "
            bitacora_descripcion += f"Lista de Acuerdos del {lista_de_acuerdo.fecha.strftime('%Y-%m-%d')} de {autoridad.clave}"
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(bitacora_descripcion),
                url=url_for("listas_de_acuerdos.detail", lista_de_acuerdo_id=lista_de_acuerdo.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)

    # Llenar de los campos del formulario
    form.distrito.data = autoridad.distrito.nombre  # Read only
    form.autoridad.data = autoridad.descripcion  # Read only
    form.fecha.data = hoy

    # Si puede elegir la materia
    if con_materia:
        materia_por_defecto = Materia.query.get(1)
        form.materia.data = materia_por_defecto.id  # Es un SelectField, se necesita el id

    # Mostrar formulario
    return render_template(
        "listas_de_acuerdos/new_for_autoridad.jinja2",
        form=form,
        autoridad=autoridad,
        con_materia=con_materia,
    )


@listas_de_acuerdos.route("/listas_de_acuerdos/eliminar/<int:lista_de_acuerdo_id>")
@permission_required(MODULO, Permiso.CREAR)
def delete(lista_de_acuerdo_id):
    """Eliminar ListaDeAcuerdo"""
    local_tz = pytz.timezone(current_app.config["TZ"])

    # Consultar
    lista_de_acuerdo = ListaDeAcuerdo.query.get_or_404(lista_de_acuerdo_id)
    detalle_url = url_for("listas_de_acuerdos.detail", lista_de_acuerdo_id=lista_de_acuerdo.id)

    # Validar que se pueda eliminar
    if lista_de_acuerdo.estatus == "B":
        flash("No puede eliminar esta Lista de Acuerdos porque ya está eliminada.", "success")
        return redirect(detalle_url)

    # Definir la descripción para la bitácora
    fecha_y_autoridad = f"{lista_de_acuerdo.fecha.strftime('%Y-%m-%d')} de {lista_de_acuerdo.autoridad.clave}"
    descripcion = safe_message(f"Eliminada Lista de Acuerdos del {fecha_y_autoridad} por {current_user.email}")

    # Si es administrador, puede eliminar
    if current_user.can_admin(MODULO):
        lista_de_acuerdo.delete()
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
    if current_user.autoridad_id != lista_de_acuerdo.autoridad_id:
        flash("No se puede eliminar porque no le pertenece.", "warning")
        return redirect(detalle_url)

    # Si fue creado hace menos del límite de días
    if lista_de_acuerdo.creado >= datetime.now(tz=local_tz) - timedelta(days=LIMITE_DIAS_ELIMINAR):
        lista_de_acuerdo.delete()
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


@listas_de_acuerdos.route("/listas_de_acuerdos/recuperar/<int:lista_de_acuerdo_id>")
@permission_required(MODULO, Permiso.CREAR)
def recover(lista_de_acuerdo_id):
    """Recuperar ListaDeAcuerdo"""

    # Consultar
    lista_de_acuerdo = ListaDeAcuerdo.query.get_or_404(lista_de_acuerdo_id)
    detalle_url = url_for("listas_de_acuerdos.detail", lista_de_acuerdo_id=lista_de_acuerdo.id)

    # Validar que se pueda recuperar
    if lista_de_acuerdo.estatus == "A":
        flash("No puede eliminar esta Lista de Acuerdos porque ya está activa.", "success")
        return redirect(detalle_url)

    # Evitar que se recupere si ya existe una con la misma fecha
    if (
        ListaDeAcuerdo.query.filter(ListaDeAcuerdo.autoridad == current_user.autoridad)
        .filter(ListaDeAcuerdo.fecha == lista_de_acuerdo.fecha)
        .filter_by(estatus="A")
        .first()
    ):
        flash("No puede recuperar esta lista porque ya hay una activa de la misma fecha.", "warning")
        return redirect(detalle_url)

    # Definir la descripción para la bitácora
    fecha_y_autoridad = f"{lista_de_acuerdo.fecha.strftime('%Y-%m-%d')} de {lista_de_acuerdo.autoridad.clave}"
    descripcion = safe_message(f"Recuperada Lista de Acuerdos del {fecha_y_autoridad} por {current_user.email}")

    # Si es administrador, puede recuperar
    if current_user.can_admin(MODULO):
        lista_de_acuerdo.recover()
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
    if current_user.autoridad_id != lista_de_acuerdo.autoridad_id:
        flash("No se puede recuperar porque no le pertenece.", "warning")
        return redirect(detalle_url)

    # Si fue creado hace menos del límite de días
    if lista_de_acuerdo.creado >= datetime.now(tz=timezone(current_app.config["TZ"])) - timedelta(days=LIMITE_DIAS_RECUPERAR):
        lista_de_acuerdo.recover()
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


@listas_de_acuerdos.route("/listas_de_acuerdos/ver_archivo_pdf/<int:lista_de_acuerdo_id>")
def view_file_pdf(lista_de_acuerdo_id):
    """Ver archivo PDF de ListaDeAcuerdo para insertarlo en un iframe en el detalle"""

    # Consultar
    lista_de_acuerdo = ListaDeAcuerdo.query.get_or_404(lista_de_acuerdo_id)

    # Obtener el contenido del archivo
    try:
        archivo = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_LISTAS_DE_ACUERDOS"],
            blob_name=get_blob_name_from_url(lista_de_acuerdo.url),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
        raise NotFound("No se encontró el archivo.") from error

    # Entregar el archivo
    response = make_response(archivo)
    response.headers["Content-Type"] = "application/pdf"
    return response


@listas_de_acuerdos.route("/listas_de_acuerdos/descargar_archivo_pdf/<int:lista_de_acuerdo_id>")
def download_file_pdf(lista_de_acuerdo_id):
    """Descargar archivo PDF de ListaDeAcuerdo"""

    # Consultar
    lista_de_acuerdo = ListaDeAcuerdo.query.get_or_404(lista_de_acuerdo_id)

    # Obtener el contenido del archivo
    try:
        archivo = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_LISTAS_DE_ACUERDOS"],
            blob_name=get_blob_name_from_url(lista_de_acuerdo.url),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
        raise NotFound("No se encontró el archivo.") from error

    # Entregar el archivo
    response = make_response(archivo)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"attachment; filename={lista_de_acuerdo.archivo}"
    return response
