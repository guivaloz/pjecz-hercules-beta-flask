"""
Oficios Plantillas, vsitas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ...lib.clean_html import clean_html
from ...lib.datatables import get_datatable_parameters, output_datatable_json
from ...lib.safe_string import safe_clave, safe_message, safe_string, safe_uuid
from ..autoridades.models import Autoridad
from ..bitacoras.models import Bitacora
from ..modulos.models import Modulo
from ..permisos.models import Permiso
from ..usuarios.decorators import permission_required
from ..usuarios.models import Usuario
from .forms import OfiPlantillaForm
from .models import OfiPlantilla

MODULO = "OFI PLANTILLAS"

ofi_plantillas = Blueprint("ofi_plantillas", __name__, template_folder="templates")


@ofi_plantillas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@ofi_plantillas.route("/ofi_plantillas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de plantillas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = OfiPlantilla.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(OfiPlantilla.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(OfiPlantilla.estatus == "A")
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], save_enie=True)
        if descripcion:
            consulta = consulta.filter(OfiPlantilla.descripcion.contains(descripcion))
    # Luego filtrar por columnas de otras tablas
    tabla_usuario_incluida = False
    if "propietario" in request.form:
        if tabla_usuario_incluida is False:
            consulta = consulta.join(Usuario)
            tabla_usuario_incluida = True
        propietario = request.form["propietario"].lower()
        consulta = consulta.filter(Usuario.email.contains(propietario))
    if "autoridad" in request.form:
        autoridad = safe_clave(request.form["autoridad"])
        if autoridad:
            if tabla_usuario_incluida is False:
                consulta = consulta.join(Usuario)
                tabla_usuario_incluida = True
            consulta = consulta.join(Autoridad, Usuario.autoridad_id == Autoridad.id)
            consulta = consulta.filter(Autoridad.clave.contains(autoridad))
    if "usuario_autoridad_id" in request.form:
        if tabla_usuario_incluida is False:
            consulta = consulta.join(Usuario)
            tabla_usuario_incluida = True
        consulta = consulta.filter(Usuario.autoridad_id == request.form["usuario_autoridad_id"])
    # Ordenar y paginar
    registros = consulta.order_by(OfiPlantilla.descripcion).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("ofi_plantillas.detail", ofi_plantilla_id=resultado.id),
                    "url_edicion": (
                        url_for("ofi_plantillas.edit", ofi_plantilla_id=resultado.id)
                        if current_user.can_edit("OFI PLANTILLAS")
                        else ""
                    ),
                    "url_nuevo": (
                        url_for("ofi_documentos.new", ofi_plantilla_id=resultado.id)
                        if current_user.can_insert("OFI DOCUMENTOS")
                        else ""
                    ),
                },
                "propietario": {
                    "email": resultado.usuario.email,
                    "nombre": resultado.usuario.nombre,
                    "url": url_for("usuarios.detail", usuario_id=resultado.usuario.id),
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
                "descripcion": resultado.descripcion,
                "creado": resultado.creado.strftime("%Y-%m-%d %H:%M"),
                "esta_archivado": resultado.esta_archivado,
                "esta_compartida": resultado.esta_compartida,
                "toggle_esta_archivado": {
                    "id": resultado.id,
                    "esta_archivado": resultado.esta_archivado,
                    "url": (
                        url_for("ofi_plantillas.toggle_esta_archivado_json", ofi_plantilla_id=resultado.id)
                        if current_user.can_edit(MODULO)
                        else ""
                    ),
                },
                "toggle_esta_compartida": {
                    "id": resultado.id,
                    "esta_compartida": resultado.esta_compartida,
                    "url": (
                        url_for("ofi_plantillas.toggle_esta_compartida_json", ofi_plantilla_id=resultado.id)
                        if current_user.can_edit(MODULO)
                        else ""
                    ),
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@ofi_plantillas.route("/ofi_plantillas")
def list_active():
    """Listado de Ofi Plantillas activos"""
    if current_user.can_admin(MODULO):
        return render_template(
            "ofi_plantillas/list_admin.jinja2",
            filtros=json.dumps({"estatus": "A"}),
            titulo="Plantillas",
            estatus="A",
        )
    return render_template(
        "ofi_plantillas/list.jinja2",
        filtros=json.dumps({"estatus": "A", "usuario_autoridad_id": current_user.autoridad.id}),
        titulo="Plantillas",
        estatus="A",
    )


@ofi_plantillas.route("/ofi_plantillas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Ofi Plantillas inactivos"""
    if current_user.can_admin(MODULO):
        return render_template(
            "ofi_plantillas/list_admin.jinja2",
            filtros=json.dumps({"estatus": "B"}),
            titulo="Plantillas inactivos",
            estatus="B",
        )
    return render_template(
        "ofi_plantillas/list.jinja2",
        filtros=json.dumps({"estatus": "B", "usuario_autoridad_id": current_user.autoridad.id}),
        titulo="Plantillas inactivos",
        estatus="B",
    )


@ofi_plantillas.route("/ofi_plantillas/<ofi_plantilla_id>")
def detail(ofi_plantilla_id):
    """Detalle de un plantilla"""
    ofi_plantilla_id = safe_uuid(ofi_plantilla_id)
    if ofi_plantilla_id == "":
        flash("ID de plantilla inválido", "warning")
        return redirect(url_for("ofi_plantillas.list_active"))
    ofi_plantilla = OfiPlantilla.query.get_or_404(ofi_plantilla_id)
    return render_template("ofi_plantillas/detail.jinja2", ofi_plantilla=ofi_plantilla)


@ofi_plantillas.route("/ofi_plantillas/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nueva plantilla"""
    form = OfiPlantillaForm()
    if form.validate_on_submit():
        # Validar propietario
        propietario = Usuario.query.filter_by(id=form.propietario.data).first()
        if not propietario:
            flash("Propietario inválido", "warning")
            return redirect(url_for("ofi_plantillas.new"))
        # Limpiar los textos con listados de correos electronicos de espacios
        destinatarios_emails = str(form.destinatarios_emails.data).strip().replace(" ", "")
        con_copias_emails = str(form.con_copias_emails.data).strip().replace(" ", "")
        remitente_email = str(form.remitente_email.data).strip().replace(" ", "")
        # Insertar
        ofi_plantilla = OfiPlantilla(
            usuario=propietario,
            descripcion=safe_string(form.descripcion.data, save_enie=True),
            destinatarios_emails=destinatarios_emails,
            con_copias_emails=con_copias_emails,
            remitente_email=remitente_email,
            contenido_md=str(form.contenido_md.data),
            contenido_html=clean_html(str(form.contenido_html.data)),
            contenido_sfdt=None,
        )
        ofi_plantilla.save()
        # Registrar en bitácora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nueva plantilla {ofi_plantilla.descripcion}"),
            url=url_for("ofi_plantillas.detail", ofi_plantilla_id=ofi_plantilla.id),
        )
        bitacora.save()
        # Redireccionar al detalle
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    # Entregar formulario
    return render_template("ofi_plantillas/new.jinja2", form=form)


@ofi_plantillas.route("/ofi_plantillas/edicion/<ofi_plantilla_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(ofi_plantilla_id):
    """Editar plantilla"""
    ofi_plantilla_id = safe_uuid(ofi_plantilla_id)
    if not ofi_plantilla_id:
        flash("ID de plantilla inválido", "warning")
        return redirect(url_for("ofi_plantillas.list_active"))
    ofi_plantilla = OfiPlantilla.query.get_or_404(ofi_plantilla_id)
    form = OfiPlantillaForm()
    if form.validate_on_submit():
        # Validar propietario
        es_valido = True
        propietario = Usuario.query.filter_by(id=form.propietario.data).first()
        if not propietario:
            flash("Propietario inválido", "warning")
            es_valido = False
        # Limpiar los textos con listados de correos electronicos de espacios
        destinatarios_emails = str(form.destinatarios_emails.data).strip().replace(" ", "")
        con_copias_emails = str(form.con_copias_emails.data).strip().replace(" ", "")
        remitente_email = str(form.remitente_email.data).strip().replace(" ", "")
        # Si es válido
        if es_valido:
            ofi_plantilla.descripcion = safe_string(form.descripcion.data, save_enie=True)
            ofi_plantilla.usuario = propietario
            ofi_plantilla.destinatarios_emails = destinatarios_emails
            ofi_plantilla.con_copias_emails = con_copias_emails
            ofi_plantilla.remitente_email = remitente_email
            ofi_plantilla.contenido_md = form.contenido_md.data
            ofi_plantilla.contenido_html = clean_html(str(form.contenido_html.data))
            ofi_plantilla.contenido_sfdt = form.contenido_sfdt.data
            ofi_plantilla.esta_archivado = form.esta_archivado.data
            ofi_plantilla.esta_compartida = form.esta_compartida.data
            ofi_plantilla.save()
        # Registrar en bitácora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editado plantilla {ofi_plantilla.descripcion}"),
            url=url_for("ofi_plantillas.detail", ofi_plantilla_id=ofi_plantilla.id),
        )
        bitacora.save()
        # Redireccionar al detalle
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    # Cargar datos al formulario
    form.descripcion.data = ofi_plantilla.descripcion
    form.destinatarios_emails.data = ofi_plantilla.destinatarios_emails
    form.con_copias_emails.data = ofi_plantilla.con_copias_emails
    form.remitente_email.data = ofi_plantilla.remitente_email
    form.contenido_md.data = ofi_plantilla.contenido_md
    form.contenido_html.data = ofi_plantilla.contenido_html
    form.contenido_sfdt.data = ofi_plantilla.contenido_sfdt
    form.esta_archivado.data = ofi_plantilla.esta_archivado
    form.esta_compartida.data = ofi_plantilla.esta_compartida
    # Entregar formulario
    return render_template("ofi_plantillas/edit.jinja2", form=form, ofi_plantilla=ofi_plantilla)


@ofi_plantillas.route("/ofi_plantillas/eliminar/<ofi_plantilla_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(ofi_plantilla_id):
    """Eliminar plantilla"""
    ofi_plantilla_id = safe_uuid(ofi_plantilla_id)
    if ofi_plantilla_id == "":
        flash("ID de plantilla inválido", "warning")
        return redirect(url_for("ofi_plantillas.list_active"))
    ofi_plantilla = OfiPlantilla.query.get_or_404(ofi_plantilla_id)
    if ofi_plantilla.estatus == "A":
        ofi_plantilla.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado plantilla {ofi_plantilla.descripcion}"),
            url=url_for("ofi_plantillas.detail", ofi_plantilla_id=ofi_plantilla.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("ofi_plantillas.detail", ofi_plantilla_id=ofi_plantilla.id))


@ofi_plantillas.route("/ofi_plantillas/toggle_esta_archivado_json/<ofi_plantilla_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def toggle_esta_archivado_json(ofi_plantilla_id):
    """Cambiar esta_archivado de una plantilla para el boton en datatable"""

    # Consultar la plantilla
    ofi_plantilla_id = safe_uuid(ofi_plantilla_id)
    if not ofi_plantilla_id:
        return {"success": False, "message": "ID inválido"}
    ofi_plantilla = OfiPlantilla.query.get_or_404(ofi_plantilla_id)
    if ofi_plantilla is None:
        return {"success": False, "message": "No encontrado"}

    # Cambiar esta_archivado a su opuesto
    ofi_plantilla.esta_archivado = not ofi_plantilla.esta_archivado

    # Guardar
    ofi_plantilla.save()

    # Elaborar el mensaje
    if ofi_plantilla.esta_archivado:
        mensaje = f"La plantilla {ofi_plantilla.descripcion} ha sido archivada."
    else:
        mensaje = f"La plantilla {ofi_plantilla.descripcion} ha sido desarchivada."

    # Entregar JSON
    return {
        "success": True,
        "message": mensaje,
        "esta_archivado": ofi_plantilla.esta_archivado,
        "id": ofi_plantilla.id,
    }


@ofi_plantillas.route("/ofi_plantillas/toggle_esta_compartida_json/<ofi_plantilla_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def toggle_esta_compartida_json(ofi_plantilla_id):
    """Cambiar esta_compartida de una plantilla para el boton en datatable"""

    # Consultar la plantilla
    ofi_plantilla_id = safe_uuid(ofi_plantilla_id)
    if not ofi_plantilla_id:
        return {"success": False, "message": "ID inválido"}
    ofi_plantilla = OfiPlantilla.query.get_or_404(ofi_plantilla_id)
    if ofi_plantilla is None:
        return {"success": False, "message": "No encontrado"}

    # Cambiar esta_compartida a su opuesto
    ofi_plantilla.esta_compartida = not ofi_plantilla.esta_compartida

    # Guardar
    ofi_plantilla.save()

    # Elaborar el mensaje
    if ofi_plantilla.esta_compartida:
        mensaje = f"La plantilla {ofi_plantilla.descripcion} ahora está compartida."
    else:
        mensaje = f"La plantilla {ofi_plantilla.descripcion} ahora es privada."

    # Entregar JSON
    return {
        "success": True,
        "message": mensaje,
        "esta_compartida": ofi_plantilla.esta_compartida,
        "id": ofi_plantilla.id,
    }


@ofi_plantillas.route("/ofi_plantillas/compartidas_json", methods=["GET", "POST"])
def shared_json():
    """Proporcionar el JSON de plantillas compartidas de la autoridad_clave para elaborar el selector de plantillas"""
    consulta = (
        OfiPlantilla.query.join(Usuario)
        .join(Autoridad)
        .filter(OfiPlantilla.estatus == "A")
        .filter(OfiPlantilla.esta_archivado.is_(False))
        .filter(OfiPlantilla.esta_compartida.is_(True))
        .filter(Usuario.estatus == "A")
    )
    autoridad_clave = request.args.get("autoridad_clave", "").strip()
    if autoridad_clave:
        autoridad_clave = safe_clave(autoridad_clave)
        if autoridad_clave != "":
            consulta = consulta.filter(Autoridad.clave == autoridad_clave)
    resultados = []
    for ofi_plantilla in consulta.order_by(OfiPlantilla.descripcion).all():
        resultados.append(
            {
                "id": ofi_plantilla.id,
                "descripcion": ofi_plantilla.descripcion,
                "tablero_icono": ofi_plantilla.usuario.autoridad.tablero_icono,
            }
        )
    if len(resultados) == 0:
        return {
            "success": False,
            "message": (
                f"No hay plantillas compartidas en {autoridad_clave}" if autoridad_clave else "No hay plantillas compartidas"
            ),
        }
    return {
        "success": True,
        "message": f"Plantillas de {autoridad_clave}" if autoridad_clave else "Todas las plantillas",
        "data": resultados,
    }


@ofi_plantillas.route("/ofi_plantillas/mis_plantillas_json", methods=["GET", "POST"])
def my_templates_json():
    """Proporcionar el JSON de plantillas privadas para el asistente de nuevo oficio"""
    consulta = (
        OfiPlantilla.query.filter(OfiPlantilla.estatus == "A")
        .filter(OfiPlantilla.esta_archivado.is_(False))
        .filter(OfiPlantilla.esta_compartida.is_(False))
        .filter(OfiPlantilla.usuario_id == current_user.id)
    )
    resultados = []
    for ofi_plantilla in consulta.order_by(OfiPlantilla.descripcion).all():
        resultados.append(
            {
                "id": ofi_plantilla.id,
                "descripcion": ofi_plantilla.descripcion,
            }
        )
    if len(resultados) == 0:
        return {
            "success": False,
            "message": "No se encontraron plantillas para el usuario actual",
        }
    return {
        "success": True,
        "message": f"Plantillas del usuario {current_user.email}",
        "data": resultados,
    }


@ofi_plantillas.route("/ofi_plantillas/vista_previa_json", methods=["GET", "POST"])
def preview_json():
    """Proporcionar el JSON de una plantilla con el UUID en el URL para elaborar una vista previa"""

    # Validar el UUID
    ofi_plantilla_id = request.args.get("id", "").strip()
    if not ofi_plantilla_id:
        return {"success": False, "message": "ID de plantilla no proporcionado"}
    ofi_plantilla_id = safe_uuid(ofi_plantilla_id)
    if not ofi_plantilla_id:
        return {"success": False, "message": "ID de plantilla inválido"}
    ofi_plantilla = OfiPlantilla.query.get(ofi_plantilla_id)
    if not ofi_plantilla:
        return {"success": False, "message": "Plantilla no encontrada"}

    # Copiar el contenido HTML a esta variable para reemplazar los marcadores
    contenido_html = ofi_plantilla.contenido_html

    # Reemplazar los destinatarios
    if ofi_plantilla.destinatarios_emails and contenido_html.find("[[DESTINATARIOS]]") != -1:
        destinatarios_emails = ofi_plantilla.destinatarios_emails.split(",")
        destinatarios_str = ""
        for email in destinatarios_emails:
            destinatario = Usuario.query.filter_by(email=email).filter_by(estatus="A").first()
            if destinatario:
                destinatarios_str += f"{destinatario.nombre}<br>\n"
                destinatarios_str += f"{destinatario.puesto}<br>\n"
                destinatarios_str += f"{destinatario.autoridad.descripcion}<br>\n"
        contenido_html = contenido_html.replace("[[DESTINATARIOS]]", destinatarios_str)

    # Reemplazar los con copias
    if ofi_plantilla.con_copias_emails and contenido_html.find("[[CON COPIAS]]") != -1:
        con_copias_emails = ofi_plantilla.con_copias_emails.split(",")
        con_copias_str = ""
        for email in con_copias_emails:
            con_copia = Usuario.query.filter_by(email=email).filter_by(estatus="A").first()
            if con_copia:
                con_copias_str += f"{con_copia.nombre}, {con_copia.autoridad.descripcion}<br>\n"
        contenido_html = contenido_html.replace("[[CON COPIAS]]", con_copias_str)

    # Entregar JSON
    return {
        "success": True,
        "message": f"Vista previa de la plantilla {ofi_plantilla.descripcion}",
        "data": {
            "descripcion": ofi_plantilla.descripcion,
            "contenido_html": contenido_html,
        },
    }
