"""
Oficios Documentos, vistas
"""

import json
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ...lib.clean_html import clean_html
from ...lib.datatables import get_datatable_parameters, output_datatable_json
from ...lib.folio import validar_folio
from ...lib.safe_string import safe_clave, safe_email, safe_message, safe_string, safe_uuid
from ..autoridades.models import Autoridad
from ..bitacoras.models import Bitacora
from ..modulos.models import Modulo
from ..ofi_documentos_destinatarios.models import OfiDocumentoDestinatario
from ..ofi_plantillas.models import OfiPlantilla
from ..permisos.models import Permiso
from ..usuarios.decorators import permission_required
from ..usuarios.models import Usuario
from .forms import OfiDocumentoForm
from .models import OfiDocumento

# Roles
ROL_ESCRITOR = "OFICIOS ESCRITOR"
ROL_FIRMANTE = "OFICIOS FIRMANTE"
ROL_LECTOR = "OFICIOS LECTOR"

MODULO = "OFI DOCUMENTOS"

ofi_documentos = Blueprint("ofi_documentos", __name__, template_folder="templates")


@ofi_documentos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@ofi_documentos.route("/ofi_documentos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de documentos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = OfiDocumento.query
    # Iniciar variable boleana para saber si se ha hecho el join con usuarios
    usuario_join_realizado = False
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "usuario_id" in request.form:
        try:
            usuario_id = int(request.form["usuario_id"])
            if usuario_id:
                consulta = consulta.filter(OfiDocumento.usuario_id == usuario_id)
        except ValueError:
            pass
    if "estado" in request.form:
        estado = safe_string(request.form["estado"])
        if estado:
            consulta = consulta.filter(OfiDocumento.estado == estado)
    if "folio" in request.form:
        folio = safe_string(request.form["folio"])
        if folio:
            consulta = consulta.filter(OfiDocumento.folio.contains(folio))
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"])
        if descripcion:
            consulta = consulta.filter(OfiDocumento.descripcion.contains(descripcion))
    # Filtrar por propietario (usuario e-mail)
    if "propietario" in request.form:
        try:
            email = safe_email(request.form["propietario"], search_fragment=True)
            if email:
                if not usuario_join_realizado:
                    consulta = consulta.join(Usuario)
                    usuario_join_realizado = True
                consulta = consulta.filter(Usuario.email.contains(email))
        except ValueError:
            pass
    # Filtrar por ID de autoridad
    if "autoridad_id" in request.form:
        autoridad_id = int(request.form["autoridad_id"])
        if autoridad_id:
            if not usuario_join_realizado:
                consulta = consulta.join(Usuario)
                usuario_join_realizado = True
            consulta = consulta.filter(Usuario.autoridad_id == autoridad_id)
    # Filtrar por clave de la autoridad
    elif "autoridad_clave" in request.form:
        autoridad_clave = safe_clave(request.form["autoridad_clave"])
        if autoridad_clave:
            if not usuario_join_realizado:
                consulta = consulta.join(Usuario)
                usuario_join_realizado = True
            consulta = consulta.join(Autoridad)
            consulta = consulta.filter(Autoridad.clave.contains(autoridad_clave))
    # Filtrar para Mi Bandeja de Entrada
    if "usuario_destinatario_id" in request.form:
        try:
            usuario_destinatario_id = int(request.form["usuario_destinatario_id"])
            if usuario_destinatario_id:
                consulta = consulta.join(OfiDocumentoDestinatario, OfiDocumentoDestinatario.ofi_documento_id == OfiDocumento.id)
                consulta = consulta.filter(OfiDocumentoDestinatario.usuario_id == request.form["usuario_destinatario_id"])
                consulta = consulta.filter(OfiDocumentoDestinatario.estatus == "A")
        except ValueError:
            pass
    # Ordenar y paginar
    registros = consulta.order_by(OfiDocumento.creado.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "detail_url": url_for("ofi_documentos.detail", ofi_documento_id=resultado.id),
                    "fullscreen_url": url_for("ofi_documentos.detail", ofi_documento_id=resultado.id),
                    "sign_url": "",
                },
                "propietario": {
                    "email": resultado.usuario.email,
                    "nombre": resultado.usuario.nombre,
                },
                "autoridad": {
                    "clave": resultado.usuario.autoridad.clave,
                    "nombre": resultado.usuario.autoridad.descripcion_corta,
                    "url": (
                        url_for("autoridades.detail", autoridad_id=resultado.usuario.autoridad.id)
                        if current_user.can_view("AUTORIDADES")
                        else ""
                    ),
                    "color_renglon": (
                        resultado.usuario.autoridad.tabla_renglon_color
                        if resultado.usuario.autoridad.tabla_renglon_color
                        else ""
                    ),
                },
                "folio": resultado.folio,
                "descripcion": resultado.descripcion,
                "creado": resultado.creado.strftime("%Y-%m-%dT%H:%M:%S"),
                "estado": resultado.estado,
                "fila_en_negritas": False,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@ofi_documentos.route("/ofi_documentos")
@ofi_documentos.route("/ofi_documentos/mi_bandeja_entrada")
def list_active():
    """Listado de documentos activos, mi bandeja de entrada"""
    return render_template(
        "ofi_documentos/list.jinja2",
        estatus="A",
        filtros=json.dumps({"estatus": "A", "estado": "ENVIADO", "usuario_destinatario_id": current_user.id}),
        titulo="Mi bandeja de entrada",
    )


@ofi_documentos.route("/ofi_documentos/mis_oficios")
def list_active_mis_oficios():
    """Listado de documentos activos, mis oficios"""
    return render_template(
        "ofi_documentos/list.jinja2",
        estatus="A",
        filtros=json.dumps({"estatus": "A", "usuario_id": current_user.id}),
        titulo="Mis oficios",
    )


@ofi_documentos.route("/ofi_documentos/mi_autoridad")
def list_active_mi_autoridad():
    """Listado de documentos activos, mi autoridad"""
    return render_template(
        "ofi_documentos/list.jinja2",
        estatus="A",
        filtros=json.dumps({"estatus": "A", "autoridad_id": current_user.autoridad.id}),
        titulo=f"Mi Autoridad {current_user.autoridad.descripcion_corta}",
    )


@ofi_documentos.route("/ofi_documentos/administrar")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_active_administrar():
    """Listado de documentos activos, administrar"""
    return render_template(
        "ofi_documentos/list.jinja2",
        estatus="A",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Administrar oficios",
    )


@ofi_documentos.route("/ofi_documentos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de documentos inactivos"""
    return render_template(
        "ofi_documentos/list.jinja2",
        estatus="B",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Oficios eliminados",
    )


@ofi_documentos.route("/ofi_documentos/<ofi_documento_id>")
def detail(ofi_documento_id):
    """Detalle de un documento"""
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if ofi_documento_id == "":
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    return render_template("ofi_documentos/detail.jinja2", ofi_documento=ofi_documento)


@ofi_documentos.route("/ofi_documentos/asistente")
def assistant():
    """Asistente para crear un nuevo documento"""
    return render_template("ofi_documentos/assistant.jinja2", titulo="Nuevo Oficio")


@ofi_documentos.route("/ofi_documentos/nuevo/<ofi_plantilla_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new(ofi_plantilla_id):
    """Nuevo documento"""
    # Consultar la plantilla
    ofi_plantilla_id = safe_uuid(ofi_plantilla_id)
    if not ofi_plantilla_id:
        flash("ID de plantilla inválido", "warning")
        return redirect(url_for("ofi_plantillas.list_active"))
    ofi_plantilla = OfiPlantilla.query.get_or_404(ofi_plantilla_id)
    # Validar que la plantilla no esté eliminada
    if ofi_plantilla.estatus == "B":
        flash("La plantilla está eliminada", "warning")
        return redirect(url_for("ofi_plantillas.list_active"))
    # Validar que la plantilla no esté archivada
    if ofi_plantilla.esta_archivado:
        flash("La plantilla está archivada", "warning")
        return redirect(url_for("ofi_plantillas.list_active"))
    # Si viene autoridad_clave en el URL, consultarla
    autoridad = None
    autoridad_clave = None
    if "autoridad_clave" in request.args:
        autoridad_clave = safe_clave(request.args["autoridad_clave"])
        if autoridad_clave:
            autoridad = Autoridad.query.filter_by(clave=autoridad_clave).first()
    # Obtener el formulario
    form = OfiDocumentoForm()
    if form.validate_on_submit():
        es_valido = True
        # Validar el folio, separar el número y el año
        folio = str(form.folio.data).strip()
        numero_folio = None
        anio_folio = None
        if folio != "":
            try:
                numero_folio, anio_folio = validar_folio(folio)
            except ValueError as error:
                flash(str(error), "warning")
                es_valido = False
        # Validar la fecha de vencimiento
        vencimiento_fecha = form.vencimiento_fecha.data
        if vencimiento_fecha is not None and vencimiento_fecha < datetime.now().date():
            flash("La fecha de vencimiento no puede ser anterior a la fecha actual", "warning")
            es_valido = False
        # Validar que el oficio cadena exista
        ofi_documento_responder = None
        if form.cadena_oficio_id.data:
            ofi_documento_responder = OfiDocumento.query.get(form.cadena_oficio_id.data)
            if ofi_documento_responder is None:
                flash("El oficio cadena no existe", "warning")
                es_valido = False
        # Si es válido, guardar el nuevo oficio
        if es_valido:
            # Guardar el nuevo oficio
            ofi_documento = OfiDocumento(
                usuario=current_user,
                descripcion=safe_string(form.descripcion.data, save_enie=True),
                folio=folio,
                folio_anio=anio_folio,
                folio_num=numero_folio,
                vencimiento_fecha=vencimiento_fecha,
                contenido_md=str(form.contenido_md.data),
                contenido_html=clean_html(str(form.contenido_html.data)),
                contenido_sfdt=None,
                estado="BORRADOR",
                cadena_oficio_id=form.cadena_oficio_id.data if form.cadena_oficio_id.data else None,
            )
            ofi_documento.save()
            # Si la plantilla está compartida y tiene destinatarios_emails
            if ofi_plantilla.esta_compartida and ofi_plantilla.destinatarios_emails:
                for email in ofi_plantilla.destinatarios_emails.split(","):
                    destinatario = Usuario.query.filter_by(email=email).filter_by(estatus="A").first()
                    if destinatario:
                        ofi_documento_destinatario = OfiDocumentoDestinatario(
                            ofi_documento=ofi_documento,
                            usuario=destinatario,
                        )
                        ofi_documento_destinatario.save()
            elif autoridad and autoridad.destinatarios_emails:
                for email in autoridad.destinatarios_emails.split(","):
                    destinatario = Usuario.query.filter_by(email=email).filter_by(estatus="A").first()
                    if destinatario:
                        ofi_documento_destinatario = OfiDocumentoDestinatario(
                            ofi_documento=ofi_documento,
                            usuario=destinatario,
                        )
                        ofi_documento_destinatario.save()
            # Si la plantilla está compartida y tiene con_copias_emails
            if ofi_plantilla.esta_compartida and ofi_plantilla.con_copias_emails:
                for email in ofi_plantilla.con_copias_emails.split(","):
                    con_copia = Usuario.query.filter_by(email=email).filter_by(estatus="A").first()
                    if con_copia:
                        ofi_documento_destinatario = OfiDocumentoDestinatario(
                            ofi_documento=ofi_documento,
                            usuario=con_copia,
                            con_copia=True,
                        )
                        ofi_documento_destinatario.save()
            elif autoridad and autoridad.con_copias_emails:
                for email in autoridad.con_copias_emails:
                    con_copia = Usuario.query.filter_by(email=email).filter_by(estatus="A").first()
                    if con_copia:
                        ofi_documento_destinatario = OfiDocumentoDestinatario(
                            ofi_documento=ofi_documento,
                            usuario=con_copia,
                            con_copia=True,
                        )
                        ofi_documento_destinatario.save()
            # Si trae una cadena de oficio, copiar el destinatario propietario
            if ofi_documento_responder:
                OfiDocumentoDestinatario(
                    ofi_documento=ofi_documento,
                    usuario=ofi_documento_responder.usuario,
                ).save()
            # Insertar en la bitácora
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nuevo documento {ofi_documento.descripcion}"),
                url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            # Si va a segir editando el documento, redirigir a la edición
            if form.continuar.data == "1":
                return redirect(url_for("ofi_documentos.edit", ofi_documento_id=ofi_documento.id))
            # Si no, redirigir al detalle
            return redirect(bitacora.url)
    # Sugerir el folio consultando el último documento de la autoridad del usuario
    ultimo_documento = (
        OfiDocumento.query.join(Usuario)
        .filter(Usuario.autoridad_id == current_user.autoridad_id)
        .filter(OfiDocumento.folio_anio == datetime.now().year)
        .order_by(OfiDocumento.folio_num.desc())
        .first()
    )
    if ultimo_documento:
        folio = f"{ultimo_documento.usuario.autoridad.clave}-{ultimo_documento.folio_num + 1}/{datetime.now().year}"
    else:
        folio = f"{current_user.autoridad.clave}-1/{datetime.now().year}"  # Tal vez sea el primer oficio del año
    # Reemplazar las palabras claves en el contenido HTML
    contenido_html = ofi_plantilla.contenido_html
    contenido_html = contenido_html.replace("[[DIA]]", str(datetime.now().day))
    contenido_html = contenido_html.replace("[[MES]]", str(datetime.now().strftime("%B")))
    contenido_html = contenido_html.replace("[[AÑO]]", str(datetime.now().year))
    contenido_html = contenido_html.replace("[[FOLIO]]", folio)
    # Si es firmante, poner sus datos en el remitente
    if ROL_FIRMANTE in current_user.get_roles():
        contenido_html = contenido_html.replace("[[REMITENTE NOMBRE]]", current_user.nombre)
        contenido_html = contenido_html.replace("[[REMITENTE PUESTO]]", current_user.puesto)
        contenido_html = contenido_html.replace("[[REMITENTE AUTORIDAD]]", current_user.autoridad.descripcion)
    # Si la plantilla tiene destinatarios_emails, poner sus datos en el destinatario
    if ofi_plantilla.destinatarios_emails and contenido_html.find("[[DESTINATARIOS]]") != -1:
        destinatarios_emails = ofi_plantilla.destinatarios_emails.split(",")
        destinatarios_str = ""
        for email in destinatarios_emails:
            destinatario = Usuario.query.filter_by(email=email).filter_by(estatus="A").first()
            if destinatario:
                destinatarios_str += f"{destinatario.nombre}<br>\n"
                if destinatario.puesto:
                    destinatarios_str += f"{destinatario.puesto}<br>\n"
                destinatarios_str += f"{destinatario.autoridad.descripcion}<br>\n"
        contenido_html = contenido_html.replace("[[DESTINATARIOS]]", destinatarios_str)
    # Si la plantilla tiene con_copias_emails, poner sus datos en con copias
    if ofi_plantilla.con_copias_emails and contenido_html.find("[[CON COPIAS]]") != -1:
        con_copias_emails = ofi_plantilla.con_copias_emails.split(",")
        con_copias_str = ""
        for email in con_copias_emails:
            con_copia = Usuario.query.filter_by(email=email).filter_by(estatus="A").first()
            if con_copia:
                con_copias_str += f"{con_copia.nombre}, {con_copia.autoridad.descripcion}<br>\n"
        contenido_html = contenido_html.replace("[[CON COPIAS]]", con_copias_str)
    # Si viene autoridad_clave en el URL, poner sus destinatarios_emails en el destinatario
    if autoridad and autoridad.destinatarios_emails and contenido_html.find("[[DESTINATARIOS]]") != -1:
        destinatarios_emails = autoridad.destinatarios_emails.split(",")
        destinatarios_str = ""
        for email in destinatarios_emails:
            destinatario = Usuario.query.filter_by(email=email).filter_by(estatus="A").first()
            if destinatario:
                destinatarios_str += f"{destinatario.nombre}<br>\n"
                if destinatario.puesto:
                    destinatarios_str += f"{destinatario.puesto}<br>\n"
                destinatarios_str += f"{destinatario.autoridad.descripcion}<br>\n"
        contenido_html = contenido_html.replace("[[DESTINATARIOS]]", destinatarios_str)
    # Si viene autoridad_clave en el URL, poner sus con_copias_emails en con copias
    if autoridad and autoridad.con_copias_emails and contenido_html.find("[[CON COPIAS]]") != -1:
        con_copias_emails = ofi_plantilla.con_copias_emails.split(",")
        con_copias_str = ""
        for email in con_copias_emails:
            con_copia = Usuario.query.filter_by(email=email).filter_by(estatus="A").first()
            if con_copia:
                con_copias_str += f"{con_copia.nombre}, {con_copia.autoridad.descripcion}<br>\n"
        contenido_html = contenido_html.replace("[[CON COPIAS]]", con_copias_str)
    # Cargar los datos de la plantilla en el formulario
    form.descripcion.data = ofi_plantilla.descripcion
    form.contenido_md.data = ofi_plantilla.contenido_md
    form.contenido_html.data = contenido_html
    form.contenido_sfdt.data = ofi_plantilla.contenido_sfdt
    form.folio.data = folio
    # Entregar el formulario
    return render_template(
        "ofi_documentos/new.jinja2",
        form=form,
        ofi_plantilla_id=ofi_plantilla_id,
        autoridad_clave=autoridad_clave if autoridad_clave else "",
    )


@ofi_documentos.route("/ofi_documentos/eliminar/<ofi_documento_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(ofi_documento_id):
    """Eliminar documento"""
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if ofi_documento_id == "":
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar el estatus, que no esté eliminado
    if ofi_documento.estatus != "A":
        flash("El oficio ya está eliminado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Eliminar el oficio
    ofi_documento.folio = None
    ofi_documento.folio_anio = None
    ofi_documento.folio_num = None
    ofi_documento.delete()
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Eliminado documento {ofi_documento.descripcion}"),
        url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
    )
    bitacora.save()
    flash(bitacora.descripcion, "success")
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))


@ofi_documentos.route("/ofi_documentos/recuperar/<ofi_documento_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(ofi_documento_id):
    """Recuperar documento"""
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if ofi_documento_id == "":
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar el estatus, que esté eliminado
    if ofi_documento.estatus != "B":
        flash("El oficio no está eliminado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Recuperar el oficio
    ofi_documento.recover()
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Recuperado documento {ofi_documento.descripcion}"),
        url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
    )
    bitacora.save()
    flash(bitacora.descripcion, "success")
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
