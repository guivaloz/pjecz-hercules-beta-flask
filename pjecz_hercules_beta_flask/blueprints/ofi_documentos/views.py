"""
Oficios Documentos, vistas
"""

import json
from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
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
                    "fullscreen_url": url_for("ofi_documentos.fullscreen", ofi_documento_id=resultado.id),
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
        "ofi_documentos/list_my_documents.jinja2",
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
    # Definir por defecto que no se muestran los botones
    mostrar_boton_editar = False
    mostrar_boton_firmar = False
    mostrar_boton_enviar = False
    mostrar_boton_archivar_desarchivar = False
    mostrar_boton_cancelar_descancelar = False
    # Definir si el usuario puede escribir y/o firmar
    usuario_roles = current_user.get_roles()
    puede_escribir = ROL_ESCRITOR in usuario_roles
    puede_firmar = ROL_FIRMANTE in usuario_roles
    # Definir si el documento es de la autoridad del usuario
    es_de_mi_autoridad = current_user.autoridad_id == ofi_documento.usuario.autoridad_id
    # Si puede firmar y el documento es de su autoridad
    if puede_firmar and es_de_mi_autoridad:
        # Si está en BORRADOR, puede editar y firmar
        if ofi_documento.estado == "BORRADOR":
            mostrar_boton_editar = True
            mostrar_boton_firmar = True
        # Si está en FIRMADO o ENVIADO, puede enviar o archivar
        if ofi_documento.estado in ["FIRMADO", "ENVIADO"]:
            mostrar_boton_enviar = True
        # Si NO está cancelado y NO es BORRADOR, se puede archivar/desarchivar
        if ofi_documento.esta_cancelado is False and ofi_documento.estado != "BORRADOR":
            mostrar_boton_archivar_desarchivar = True
        # Si NO está archivado, puede cancelar/descancelar
        if ofi_documento.esta_archivado is False:
            mostrar_boton_cancelar_descancelar = True
    # Si puede escribir y el documento es de su autoridad
    if puede_escribir and es_de_mi_autoridad:
        # Si está en BORRADOR, puede editar
        if ofi_documento.estado == "BORRADOR":
            mostrar_boton_editar = True
        # Si está en FIRMADO o ENVIADO, puede enviar o archivar
        if ofi_documento.estado in ["FIRMADO", "ENVIADO"]:
            mostrar_boton_enviar = True
        # Si NO está cancelado y NO es BORRADOR, se puede archivar/desarchivar
        if ofi_documento.esta_cancelado is False and ofi_documento.estado != "BORRADOR":
            mostrar_boton_archivar_desarchivar = True
        # Si NO está archivado, puede cancelar/descancelar
        if ofi_documento.esta_archivado is False:
            mostrar_boton_cancelar_descancelar = True
    # Definir que por defecto no se muestran los botones para agregar archivos y destinatarios
    mostrar_botones_agregar = False
    # Si NO está cancelado y NO está archivado
    if not ofi_documento.esta_cancelado or not ofi_documento.esta_archivado:
        # Si el usuario es el propietario del documento o si pertenece a la autoridad del propietario, mostrar los botones
        propietario = ofi_documento.usuario
        autoridad = ofi_documento.usuario.autoridad
        mostrar_botones_agregar = current_user.id == propietario.id or current_user.autoridad.id == autoridad.id
    # Si sólo puede ver, no mostrar ningún botón
    if current_user.permisos[MODULO] <= 1:
        mostrar_boton_editar = False
        mostrar_boton_firmar = False
        mostrar_boton_enviar = False
        mostrar_boton_archivar_desarchivar = False
        mostrar_boton_cancelar_descancelar = False
    # Entregar el detalle
    return render_template(
        "ofi_documentos/detail.jinja2",
        ofi_documento=ofi_documento,
        mostrar_botones_agregar=mostrar_botones_agregar,
        mostrar_boton_editar=mostrar_boton_editar,
        mostrar_boton_firmar=mostrar_boton_firmar,
        mostrar_boton_enviar=mostrar_boton_enviar,
        mostrar_boton_archivar_desarchivar=mostrar_boton_archivar_desarchivar,
        mostrar_boton_cancelar_descancelar=mostrar_boton_cancelar_descancelar,
    )


@ofi_documentos.route("/ofi_documentos/pantalla_completa/<ofi_documento_id>")
def fullscreen(ofi_documento_id):
    """Pantalla completa de un Ofi Documento"""
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Si el documento está cancelado o archivado, no mostrar los botones para agregar archivos y destinatarios
    mostrar_botones_agregar = False
    if not ofi_documento.esta_cancelado or not ofi_documento.esta_archivado:
        # Si el usuario es el propietario del documento o si pertenece a la autoridad del propietario, mostrar los botones
        propietario = ofi_documento.usuario
        autoridad = ofi_documento.usuario.autoridad
        mostrar_botones_agregar = current_user.id == propietario.id or current_user.autoridad.id == autoridad.id
    # Entregar a pantalla completa
    return render_template(
        "ofi_documentos/fullscreen.jinja2",
        ofi_documento=ofi_documento,
        mostrar_botones_agregar=mostrar_botones_agregar,
    )


@ofi_documentos.route("/ofi_documentos/pantalla_completa/documento/<ofi_documento_id>")
def fullscreen_document(ofi_documento_id):
    """Pantalla completa: contenido del frame para el documento"""
    return render_template("ofi_documentos/fullscreen_document.jinja2", ofi_documento_id=ofi_documento_id)


@ofi_documentos.route("/ofi_documentos/pantalla_completa/adjuntos/<ofi_documento_id>")
def fullscreen_attachments(ofi_documento_id):
    """Pantalla completa: contenido del frame para los adjuntos"""
    return render_template("ofi_documentos/fullscreen_attachments.jinja2", ofi_documento_id=ofi_documento_id)


@ofi_documentos.route("/ofi_documentos/pantalla_completa/destinatarios/<ofi_documento_id>")
def fullscreen_recipients(ofi_documento_id):
    """Pantalla completa: contenido del frame para los destinatarios"""
    return render_template("ofi_documentos/fullscreen_recipients.jinja2", ofi_documento_id=ofi_documento_id)


@ofi_documentos.route("/ofi_documentos/fullscreen_json/<ofi_documento_id>", methods=["GET", "POST"])
def fullscreen_json(ofi_documento_id):
    """Entregar JSON para la vista de pantalla completa"""
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        return {
            "success": False,
            "message": "ID de oficio inválido.",
            "data": None,
        }
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Si está eliminado y NO es administrador
    if ofi_documento.estatus != "A" and current_user.can_admin(MODULO) is False:
        return {
            "success": False,
            "message": "Este oficio está eliminado.",
            "data": None,
        }
    # Si el estado es ENVIADO y quien lo ve es un destinatario, se va a marcar como leído
    if ofi_documento.estado == "ENVIADO":
        # Buscar al usuario entre los destinatarios
        usuario_destinatario = (
            OfiDocumentoDestinatario.query.filter_by(ofi_documento_id=ofi_documento.id)
            .filter_by(usuario_id=current_user.id)
            .first()
        )
        # Marcar como leído si es que no lo ha sido
        if usuario_destinatario is not None and usuario_destinatario.fue_leido is False:
            usuario_destinatario.fue_leido = True
            usuario_destinatario.fue_leido_tiempo = datetime.now()
            usuario_destinatario.save()
    # Definir la cabecera
    pagina_cabecera_url = ofi_documento.usuario.autoridad.pagina_cabecera_url
    if pagina_cabecera_url is None or pagina_cabecera_url.strip() == "":
        pagina_cabecera_url = current_app.config["AUTORIDADES_PAGINA_CABECERA_URL"]
    # Definir el pie
    pagina_pie_url = ofi_documento.usuario.autoridad.pagina_pie_url
    if pagina_pie_url is None or pagina_pie_url.strip() == "":
        pagina_pie_url = current_app.config["AUTORIDADES_PAGINA_PIE_URL"]
    # Entregar JSON
    return {
        "success": True,
        "message": "Se encontró el documento.",
        "data": {
            "pagina_cabecera_url": pagina_cabecera_url,
            "contenido_html": ofi_documento.contenido_html,
            "pagina_pie_url": pagina_pie_url,
            "firma_simple": ofi_documento.firma_simple,
            "estado": ofi_documento.estado,
        },
    }


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
                contenido_md=str(form.contenido_md.data).strip(),
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


@ofi_documentos.route("/ofi_documentos/edicion/<ofi_documento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(ofi_documento_id):
    """Editar Documento"""
    # Validar que el usuario tenga el rol ESCRITOR o FIRMANTE, para que un ADMINISTRADOR no pueda editar
    roles = current_user.get_roles()
    if ROL_ESCRITOR not in roles and ROL_FIRMANTE not in roles:
        flash("Se necesitan roles de ESCRITOR o FIRMANTE para editar un oficio", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Consultar el documento
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
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
        # Si es válido, guardar los cambios
        if es_valido:
            ofi_documento.descripcion = safe_string(form.descripcion.data, save_enie=True)
            ofi_documento.folio = folio
            ofi_documento.folio_anio = anio_folio
            ofi_documento.folio_num = numero_folio
            ofi_documento.vencimiento_fecha = vencimiento_fecha
            ofi_documento.contenido_md = str(form.contenido_md.data).strip()
            ofi_documento.contenido_html = clean_html(str(form.contenido_html.data))
            ofi_documento.contenido_sfdt = None
            ofi_documento.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Oficio Documento {ofi_documento.descripcion}"),
                url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            # Si NO va a seguir editando, redirigir al detalle, de lo contrario seguir en la edición
            if form.continuar.data != "1":
                return redirect(bitacora.url)
    # Cargar los datos en el formulario
    form.descripcion.data = ofi_documento.descripcion
    form.folio.data = ofi_documento.folio
    form.vencimiento_fecha.data = ofi_documento.vencimiento_fecha
    form.contenido_md.data = ofi_documento.contenido_md
    form.contenido_html.data = ofi_documento.contenido_html
    form.contenido_sfdt.data = ofi_documento.contenido_sfdt
    # Si no tiene folio, sugerir el folio consultando el último documento de la autoridad del usuario
    if ofi_documento.folio is None or ofi_documento.folio == "":
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
        form.folio.data = folio
    # Entregar el formulario
    return render_template(
        "ofi_documentos/edit.jinja2",
        form=form,
        ofi_documento=ofi_documento,
    )


@ofi_documentos.route("/ofi_documentos/firmar/<ofi_documento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def sign(ofi_documento_id):
    """Firmar un Documento"""
    # Validar que el usuario tenga el rol FIRMANTE
    if ROL_FIRMANTE not in current_user.get_roles():
        flash("Se necesita el rol de FIRMANTE para firmar un oficio", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar que la autoridad del oficio sea la misma que la del usuario
    if ofi_documento.usuario.autoridad_id != current_user.autoridad_id:
        flash("No tienes permiso para firmar este oficio, pertenece a otra autoridad", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Validar el estatus, que no esté eliminado
    if ofi_documento.estatus != "A":
        flash("El oficio está eliminado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que tenga el estado BORRADOR
    if ofi_documento.estado != "BORRADOR":
        flash("El oficio no está en estado BORRADOR, no se puede firmar", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Obtener el formuario
    form = OfiDocumentoSignForm()
    if form.validate_on_submit():
        # Validar el tipo de firma
        if form.tipo.data not in ["simple", "avanzada"]:
            flash("Tipo de firma inválido, debe ser 'simple' o 'avanzada'", "warning")
            return redirect(url_for("ofi_documentos.sign", ofi_documento_id=ofi_documento.id))
        # Reemplazar los marcadores en el contenido HTML
        actualizar_contenido_html = False
        contenido_html = ofi_documento.contenido_html
        if "[[REMITENTE NOMBRE]]" in contenido_html:
            contenido_html = contenido_html.replace("[[REMITENTE NOMBRE]]", current_user.nombre)
            actualizar_contenido_html = True
        if "[[REMITENTE PUESTO]]" in contenido_html:
            contenido_html = contenido_html.replace("[[REMITENTE PUESTO]]", current_user.puesto)
            actualizar_contenido_html = True
        if "[[REMITENTE AUTORIDAD]]" in contenido_html:
            contenido_html = contenido_html.replace("[[REMITENTE AUTORIDAD]]", current_user.autoridad.descripcion)
            actualizar_contenido_html = True
        if actualizar_contenido_html:
            ofi_documento.contenido_html = contenido_html
        # Actualizar
        ofi_documento.usuario = current_user  # El usuario que firma es el propietario del oficio
        ofi_documento.descripcion = safe_string(form.descripcion.data, save_enie=True)
        ofi_documento.estado = "FIRMADO"
        ofi_documento.firma_simple = OfiDocumento.elaborar_hash(ofi_documento)
        ofi_documento.firma_simple_tiempo = datetime.now()
        ofi_documento.firma_simple_usuario_id = current_user.id
        ofi_documento.save()
        # Lanzar la tarea en el fondo para convertir a archivo PDF de acuerdo al tipo de firma
        if form.tipo.data == "avanzada":
            current_user.launch_task(
                comando="ofi_documentos.tasks.lanzar_enviar_a_efirma",
                mensaje="Convirtiendo a archivo PDF con firma electrónica avanzada...",
                ofi_documento_id=str(ofi_documento.id),
            )
            descripcion = f"Oficio firmado con firma electrónica avanzada {ofi_documento.folio} {ofi_documento.descripcion}"
        elif form.tipo.data == "simple":
            current_user.launch_task(
                comando="ofi_documentos.tasks.lanzar_convertir_a_pdf",
                mensaje="Convirtiendo a archivo PDF con firma simple...",
                ofi_documento_id=str(ofi_documento.id),
            )
            descripcion = f"Oficio firmado con firma simple {ofi_documento.folio} {ofi_documento.descripcion}"
        # Si tiene destinatarios
        cantidad = 0
        for ofi_destinatario in ofi_documento.ofi_documentos_destinatarios:
            if ofi_destinatario.estatus == "A":
                cantidad += 1
        if cantidad > 0:
            # Lanzar la tarea en el fondo para enviar mensajes por correo electrónico a los destinatarios por SendGrid
            current_user.launch_task(
                comando="ofi_documentos.tasks.lanzar_enviar_a_sendgrid",
                mensaje="Enviado mensajes por correo electrónico a los destinatarios por SendGrid...",
                ofi_documento_id=str(ofi_documento.id),
            )
            ofi_documento.estado = "ENVIADO"
            ofi_documento.enviado_tiempo = datetime.now()
            ofi_documento.save()
            descripcion = f"{descripcion} y enviado a {cantidad} destinatarios"
        # Agregar registro a la bitácora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(descripcion),
            url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    # Cargar los datos en el formulario
    form.descripcion.data = ofi_documento.descripcion
    form.folio.data = ofi_documento.folio  # Read only
    form.vencimiento_fecha.data = ofi_documento.vencimiento_fecha  # Read only
    # Entregar el formulario
    return render_template(
        "ofi_documentos/sign.jinja2",
        form=form,
        ofi_documento=ofi_documento,
        tiene_firma_electronica_avanzada=(current_user.efirma_registro_id is not None and current_user.efirma_registro_id > 0),
    )


@ofi_documentos.route("/ofi_documentos/enviar/<ofi_documento_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def send(ofi_documento_id):
    """Enviar un Ofi Documento"""
    # Validar que el usuario tenga el rol ESCRITOR o FIRMANTE, para que un ADMINISTRADOR no pueda enviar
    roles = current_user.get_roles()
    if ROL_ESCRITOR not in roles and ROL_FIRMANTE not in roles:
        flash("Se necesitan roles de ESCRITOR o FIRMANTE para enviar un oficio", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar que la autoridad del oficio sea la misma que la del usuario
    if ofi_documento.usuario.autoridad_id != current_user.autoridad_id:
        flash("No tienes permiso para enviar este oficio, pertenece a otra autoridad", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Validar el estatus, que no esté eliminado
    if ofi_documento.estatus != "A":
        flash("El oficio está eliminado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que tenga el estado FIRMADO
    if ofi_documento.estado != "FIRMADO":
        flash("El oficio no está en estado FIRMADO, no se puede enviar", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que no esté archivado
    if ofi_documento.esta_archivado:
        flash("El oficio está archivado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que haya al menos un destinatario
    cantidad_destinatarios = (
        OfiDocumentoDestinatario.query.filter_by(ofi_documento_id=ofi_documento.id).filter_by(estatus="A").count()
    )
    if cantidad_destinatarios == 0:
        flash("Este oficio NO tiene destinatarios, no se puede enviar, debe agregarlos", "danger")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Actualizar el estado a ENVIADO
    ofi_documento.estado = "ENVIADO"
    ofi_documento.enviado_tiempo = datetime.now()
    ofi_documento.save()
    # Lanzar la tarea en el fondo para enviar mensajes por correo electrónico a los destinatarios por SendGrid
    current_user.launch_task(
        comando="ofi_documentos.tasks.lanzar_enviar_a_sendgrid",
        mensaje="Enviado mensajes por correo electrónico a los destinatarios por SendGrid...",
        ofi_documento_id=str(ofi_documento.id),
    )
    # Agregar registro a la bitácora
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Enviado Ofi Documento {ofi_documento.descripcion}"),
        url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
    )
    bitacora.save()
    flash(bitacora.descripcion, "success")
    # Redirigir al detalle del oficio
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))


@ofi_documentos.route("/ofi_documentos/cancelar/<ofi_documento_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def cancel(ofi_documento_id):
    """Cancelar Documento"""
    # Validar que el usuario tenga el rol ESCRITOR o FIRMANTE, para que un ADMINISTRADOR no pueda descancelar
    roles = current_user.get_roles()
    if ROL_ESCRITOR not in roles and ROL_FIRMANTE not in roles:
        flash("Se necesitan roles de ESCRITOR o FIRMANTE para descancelar un oficio", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar que la autoridad del oficio sea la misma que la del usuario
    if ofi_documento.usuario.autoridad_id != current_user.autoridad_id:
        flash("No tienes permiso para cancelar este oficio, pertenece a otra autoridad", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Validar que no esté archivado
    if ofi_documento.esta_archivado:
        flash("El oficio ya está archivado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que SI esté cancelado
    if ofi_documento.esta_cancelado is True:
        flash("El oficio ya está caneclado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Actualizar esta_cancelado a verdadero
    ofi_documento.esta_cancelado = True
    # Si el oficio tiene el estado BORRADOR, entonces se limpia el folio
    if ofi_documento.estado == "BORRADOR":
        ofi_documento.folio = None
        ofi_documento.folio_anio = None
        ofi_documento.folio_num = None
    ofi_documento.save()
    # Agregar registro a la bitácora
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Cancelado Oficio Documento {ofi_documento.descripcion}"),
        url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
    )
    bitacora.save()
    flash(bitacora.descripcion, "success")
    # Redirigir al detalle del oficio
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))


@ofi_documentos.route("/ofi_documentos/descancelar/<ofi_documento_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def uncancel(ofi_documento_id):
    """Descancelar Documento"""
    # Validar que el usuario tenga el rol ESCRITOR o FIRMANTE, para que un ADMINISTRADOR no pueda descancelar
    roles = current_user.get_roles()
    if ROL_ESCRITOR not in roles and ROL_FIRMANTE not in roles:
        flash("Se necesitan roles de ESCRITOR o FIRMANTE para descancelar un oficio", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar que la autoridad del oficio sea la misma que la del usuario
    if ofi_documento.usuario.autoridad_id != current_user.autoridad_id:
        flash("No tienes permiso para descancelar este oficio, pertenece a otra autoridad", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que no esté archivado
    if ofi_documento.esta_archivado:
        flash("El oficio ya está archivado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que NO esté cancelado
    if ofi_documento.esta_cancelado is False:
        flash("El oficio no está cancelado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Actualizar esta_cancelado a falso
    ofi_documento.esta_cancelado = False
    ofi_documento.save()
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Descancelado Oficio Documento {ofi_documento.descripcion}"),
        url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
    )
    bitacora.save()
    flash(bitacora.descripcion, "success")
    # Redirigir al detalle del oficio
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))


@ofi_documentos.route("/ofi_documentos/archivar/<ofi_documento_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def archive(ofi_documento_id):
    """Archivar Ofi Documento"""
    # Validar que el usuario tenga el rol ESCRITOR o FIRMANTE, para que un ADMINISTRADOR no pueda cancelar
    roles = current_user.get_roles()
    if ROL_ESCRITOR not in roles and ROL_FIRMANTE not in roles:
        flash("Se necesitan roles de ESCRITOR o FIRMANTE para archivar un oficio", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar que la autoridad del oficio sea la misma que la del usuario
    if ofi_documento.usuario.autoridad_id != current_user.autoridad_id:
        flash("No tienes permiso para archivar este oficio, pertenece a otra autoridad", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Validar que no esté archivado
    if ofi_documento.esta_archivado is True:
        flash("El oficio ya está archivado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que SI esté cancelado
    if ofi_documento.esta_cancelado is True:
        flash("El oficio ya está caneclado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Actualizar esta_archivado a verdadero
    ofi_documento.esta_archivado = True
    ofi_documento.save()
    # Agregar registro a la bitácora
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Archivando Oficio Documento {ofi_documento.descripcion}"),
        url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
    )
    bitacora.save()
    flash(bitacora.descripcion, "success")
    # Redirigir al detalle del oficio
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))


@ofi_documentos.route("/ofi_documentos/desarchivar/<ofi_documento_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def unarchive(ofi_documento_id):
    """Desarchivar Ofi Documento"""
    # Validar que el usuario tenga el rol ESCRITOR o FIRMANTE, para que un ADMINISTRADOR no pueda desarchivar
    roles = current_user.get_roles()
    if ROL_ESCRITOR not in roles and ROL_FIRMANTE not in roles:
        flash("Se necesitan roles de ESCRITOR o FIRMANTE para desarchivar un oficio", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar que la autoridad del oficio sea la misma que la del usuario
    if ofi_documento.usuario.autoridad_id != current_user.autoridad_id:
        flash("No tienes permiso para desarchivar este oficio, pertenece a otra autoridad", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que no esté archivado
    if ofi_documento.esta_archivado is False:
        flash("El oficio NO está archivado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que está cancelado
    if ofi_documento.esta_cancelado:
        flash("El oficio está cancelado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Actualizar esta_archivado a falso
    ofi_documento.esta_archivado = False
    ofi_documento.save()
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Desarchivar Oficio Documento {ofi_documento.descripcion}"),
        url=url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id),
    )
    bitacora.save()
    flash(bitacora.descripcion, "success")
    # Redirigir al detalle del oficio
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))


@ofi_documentos.route("/ofi_documentos/obtener_archivo_pdf_url_json/<ofi_documento_id>", methods=["GET", "POST"])
def get_file_pdf_url_json(ofi_documento_id):
    """Obtener el URL del archivo PDF en formato JSON, para usar en el botón de descarga"""
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        return {
            "success": False,
            "message": "ID de oficio inválido",
        }
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar el estatus, que no esté eliminado
    if ofi_documento.estatus != "A":
        return {
            "success": False,
            "message": "El oficio está eliminado",
        }
    # Validar que tenga el estado FIRMADO o ENVIADO
    if ofi_documento.estado not in ["FIRMADO", "ENVIADO"]:
        return {
            "success": False,
            "message": "No está en estado FIRMADO o ENVIADO",
        }
    # Validar que tenga archivo_pdf_url
    if ofi_documento.archivo_pdf_url is None or ofi_documento.archivo_pdf_url == "":
        return {
            "success": False,
            "message": "Falló la creación del archivo PDF",
        }
    # Entregar el URL del archivo PDF
    return {
        "success": True,
        "message": "Descargar Archivo PDF",
        "url": url_for("ofi_documentos.download_file_pdf", ofi_documento_id=ofi_documento.id),
    }


@ofi_documentos.route("/ofi_documentos/descargar_archivo_pdf/<ofi_documento_id>")
def download_file_pdf(ofi_documento_id):
    """Descargar archivo PDF"""
    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        flash("ID de oficio inválido", "warning")
        return redirect(url_for("ofi_documentos.list_active"))
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    # Validar el estatus, que no esté eliminado
    if ofi_documento.estatus != "A":
        flash("El oficio está eliminado", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que tenga el estado FIRMADO o ENVIADO
    if ofi_documento.estado not in ["FIRMADO", "ENVIADO"]:
        flash("El oficio no está en estado FIRMADO o ENVIADO, no se puede descargar", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Validar que tenga archivo_pdf_url
    if ofi_documento.archivo_pdf_url is None or ofi_documento.archivo_pdf_url == "":
        flash("El oficio no tiene archivo PDF, no se puede descargar", "warning")
        return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento.id))
    # Obtener el contenido del archivo
    try:
        archivo = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_OFICIOS"],
            blob_name=get_blob_name_from_url(ofi_documento.archivo_pdf_url),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
        raise NotFound("No se encontró el archivo.")
    # Entregar el archivo PDF
    response = make_response(archivo)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"attachment; filename={ofi_documento.folio} {ofi_documento.descripcion}.pdf"
    return response


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
