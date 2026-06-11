"""
VASPEC Digitalizaciones, vistas
"""

from flask import Blueprint, current_app, flash, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func
from werkzeug.exceptions import NotFound

from pjecz_hercules_beta_flask.blueprints.autoridades.models import Autoridad
from pjecz_hercules_beta_flask.blueprints.bitacoras.models import Bitacora
from pjecz_hercules_beta_flask.blueprints.materias.models import Materia
from pjecz_hercules_beta_flask.blueprints.modulos.models import Modulo
from pjecz_hercules_beta_flask.blueprints.permisos.models import Permiso
from pjecz_hercules_beta_flask.blueprints.usuarios.decorators import permission_required
from pjecz_hercules_beta_flask.blueprints.vsp_digitalizaciones.models import VspDigitalizacion
from pjecz_hercules_beta_flask.config.extensions import database
from pjecz_hercules_beta_flask.lib.datatables import get_datatable_parameters, output_datatable_json
from pjecz_hercules_beta_flask.lib.exceptions import MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError
from pjecz_hercules_beta_flask.lib.google_cloud_storage import get_blob_name_from_url, get_file_from_gcs
from pjecz_hercules_beta_flask.lib.safe_string import safe_clave, safe_expediente, safe_message, safe_string

MODULO = "VSP DIGITALIZACIONES"

vsp_digitalizaciones = Blueprint("vsp_digitalizaciones", __name__, template_folder="templates")


@vsp_digitalizaciones.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@vsp_digitalizaciones.route("/vsp_digitalizaciones/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de digitalizaciones"""

    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()

    # Consultar
    consulta = VspDigitalizacion.query

    # Hacer join con Autoridad
    consulta = consulta.join(Autoridad)

    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "autoridad_id" in request.form:
        autoridad = Autoridad.query.get(request.form["autoridad_id"])
        if autoridad:
            consulta = consulta.filter(VspDigitalizacion.autoridad_id == autoridad.id)
    elif "autoridad_clave" in request.form:
        autoridad_clave = safe_clave(request.form["autoridad_clave"])
        if autoridad_clave != "":
            consulta = consulta.filter(Autoridad.clave.contains(autoridad_clave))
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], save_enie=True)
        if descripcion != "":
            consulta = consulta.filter(VspDigitalizacion.descripcion.contains(descripcion))
    if "expediente" in request.form:
        try:
            expediente = safe_expediente(request.form["expediente"])
            consulta = consulta.filter(VspDigitalizacion.expediente == expediente)
        except IndexError, ValueError:
            pass

    # Ordenar y paginar
    registros = (
        consulta.order_by(Autoridad.clave, VspDigitalizacion.expediente_anio, VspDigitalizacion.expediente_num)
        .offset(start)
        .limit(rows_per_page)
        .all()
    )
    total = consulta.count()

    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "autoridad": resultado.autoridad.clave,
                "detalle": {
                    "expediente": resultado.expediente,
                    "url": url_for("vsp_digitalizaciones.detail", vsp_digitalizacion_id=resultado.id),
                },
                "descripcion": resultado.descripcion if len(resultado.descripcion) < 48 else resultado.descripcion[:48] + "…",
                "tamano": resultado.tamano if resultado.tamano is not None else "",
                "tiempo": resultado.tiempo.strftime("%Y-%m-%d %H:%M") if resultado.tiempo is not None else "",
                "enviado": resultado.enviado.strftime("%Y-%m-%d %H:%M") if resultado.enviado is not None else "",
            }
        )

    # Entregar JSON
    return output_datatable_json(draw, total, data)


@vsp_digitalizaciones.route("/vsp_digitalizaciones")
def list_active():
    """Listado de digitalizaciones activas"""
    return render_template(
        "vsp_digitalizaciones/list.jinja2",
        estatus="A",
        filtros={"estatus": "A"},
        titulo="Digitalizaciones",
    )


@vsp_digitalizaciones.route("/vsp_digitalizaciones/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de digitalizaciones eliminadas"""
    return render_template(
        "vsp_digitalizaciones/list.jinja2",
        estatus="B",
        filtros={"estatus": "B"},
        titulo="Digitalizaciones eliminadas",
    )


@vsp_digitalizaciones.route("/vsp_digitalizaciones/<int:vsp_digitalizacion_id>")
def detail(vsp_digitalizacion_id):
    """Detalle de un digitalización"""
    vsp_digitalizacion = VspDigitalizacion.query.get_or_404(vsp_digitalizacion_id)
    return render_template("vsp_digitalizaciones/detail.jinja2", vsp_digitalizacion=vsp_digitalizacion)


@vsp_digitalizaciones.route("/vsp_digitalizaciones/eliminar/<int:vsp_digitalizacion_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(vsp_digitalizacion_id):
    """Eliminar digitalización"""
    vsp_digitalizacion = VspDigitalizacion.query.get_or_404(vsp_digitalizacion_id)
    if vsp_digitalizacion.estatus == "A":
        vsp_digitalizacion.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado digitalización {vsp_digitalizacion.descripcion}"),
            url=url_for("vsp_digitalizaciones.detail", vsp_digitalizacion_id=vsp_digitalizacion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("vsp_digitalizaciones.detail", vsp_digitalizacion_id=vsp_digitalizacion.id))


@vsp_digitalizaciones.route("/vsp_digitalizaciones/recuperar/<int:vsp_digitalizacion_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(vsp_digitalizacion_id):
    """Recuperar digitalización"""
    vsp_digitalizacion = VspDigitalizacion.query.get_or_404(vsp_digitalizacion_id)
    if vsp_digitalizacion.estatus == "B":
        vsp_digitalizacion.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado digitalización {vsp_digitalizacion.descripcion}"),
            url=url_for("vsp_digitalizaciones.detail", vsp_digitalizacion_id=vsp_digitalizacion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("vsp_digitalizaciones.detail", vsp_digitalizacion_id=vsp_digitalizacion.id))


@vsp_digitalizaciones.route("/vsp_digitalizaciones/obtener_totales_por_materia_por_anio")
def get_totales_por_materia_por_anio_json():
    """Obtener un listado de totales por materia por año"""

    # Consultar los totales (copiados, enviados) por materia por año
    consulta = (
        database.session.query(
            Materia.nombre.label("materia"),
            VspDigitalizacion.expediente_anio.label("anio"),
            func.count(VspDigitalizacion.id).label("copiados_total"),
            func.count(VspDigitalizacion.enviado).label("enviados_total"),
        )
        .select_from(
            VspDigitalizacion,
        )
        .join(
            Autoridad,
        )
        .join(
            Materia,
        )
        .where(
            VspDigitalizacion.estatus == "A",
        )
        .group_by(
            Materia.nombre,
            VspDigitalizacion.expediente_anio,
        )
        .order_by(
            VspDigitalizacion.expediente_anio,
            Materia.nombre,
        )
        .all()
    )

    # Convertir la consulta a una lista de diccionarios
    totales = [
        {
            "materia_nombre": row.materia,
            "anio": row.anio,
            "copiados_total": row.copiados_total,
            "enviados_total": row.enviados_total,
        }
        for row in consulta
    ]

    # Entregar la lista de totales
    return {
        "success": True,
        "message": "Entrega exitosa del listado de totales por materia",
        "totales": totales,
    }


@vsp_digitalizaciones.route("/vsp_digitalizaciones/dashboard")
def dashboard():
    """Tablero de digitalizaciones"""
    return render_template("vsp_digitalizaciones/dashboard.jinja2")


@vsp_digitalizaciones.route("/vsp_digitalizaciones/obtener_archivo_url/<int:vsp_digitalizacion_id>")
def get_file_url_json(vsp_digitalizacion_id):
    """Obtener la URL de una digitalización para descargar"""

    # Consultar
    vsp_digitalizacion = VspDigitalizacion.query.get_or_404(vsp_digitalizacion_id)

    # Registrar en la bitácora
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Ha obtenido la URL de {vsp_digitalizacion.autoridad.clave} {vsp_digitalizacion.expediente}"),
        url=url_for("vsp_digitalizaciones.detail", vsp_digitalizacion_id=vsp_digitalizacion.id),
    )
    bitacora.save()

    # Entregar la URL
    return {
        "success": True,
        "message": "Entregada la URL de una digitalización para descargar",
        "url": vsp_digitalizacion.url,
    }


@vsp_digitalizaciones.route("/vsp_digitalizaciones/ver_archivo_pdf/<int:vsp_digitalizacion_id>")
def view_file_pdf(vsp_digitalizacion_id):
    """Ver archivo PDF de una digitalización para insertarlo en un iframe en el detalle"""

    # Consultar
    vsp_digitalizacion = VspDigitalizacion.query.get_or_404(vsp_digitalizacion_id)

    # Si el tamaño del archivo es mayor a 30 MB, no se puede mostrar en el iframe
    if vsp_digitalizacion.tamano is not None and vsp_digitalizacion.tamano > 30 * 1024 * 1024:
        raise NotFound("El archivo es demasiado grande para mostrarlo en el iframe.")

    # Obtener el contenido del archivo
    try:
        archivo = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_VSP_DIGITALIZACIONES"],
            blob_name=get_blob_name_from_url(vsp_digitalizacion.url),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
        raise NotFound("No se encontró el archivo.") from error

    # Registrar en la bitácora
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Ha descargado {vsp_digitalizacion.autoridad.clave} {vsp_digitalizacion.expediente}"),
        url=url_for("vsp_digitalizaciones.detail", vsp_digitalizacion_id=vsp_digitalizacion.id),
    )
    bitacora.save()

    # Entregar el archivo
    response = make_response(archivo)
    response.headers["Content-Type"] = "application/pdf"
    return response


@vsp_digitalizaciones.route("/vsp_digitalizaciones/descargar_archivo_pdf/<int:vsp_digitalizacion_id>")
def download_file_pdf(vsp_digitalizacion_id):
    """Descargar archivo PDF de una digitalización"""

    # Consultar
    vsp_digitalizacion = VspDigitalizacion.query.get_or_404(vsp_digitalizacion_id)

    # Si el tamaño del archivo es mayor a 30 MB, no se puede descargar desde el detalle, se debe descargar desde la URL firmada
    if vsp_digitalizacion.tamano is not None and vsp_digitalizacion.tamano > 30 * 1024 * 1024:
        raise NotFound("El archivo es demasiado grande para mostrarlo en el iframe.")

    # Obtener el contenido del archivo
    try:
        archivo = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_VSP_DIGITALIZACIONES"],
            blob_name=get_blob_name_from_url(vsp_digitalizacion.url),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
        raise NotFound("No se encontró el archivo.") from error

    # Entregar el archivo
    response = make_response(archivo)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"attachment; filename={vsp_digitalizacion.archivo}"
    return response
