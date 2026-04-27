"""
Sistemas
"""

from flask import Blueprint, redirect, render_template, send_from_directory
from flask_login import current_user

# Roles que deben estar en la base de datos
ROLES_SOPORTES_TICKETS = [
    "ADMINISTRADOR",
    "SOPORTE ADMINISTRADOR",
    "SOPORTE ASISTENTE",
    "SOPORTE FIRMA SICAP ZOOM",
    "SOPORTE INFORMATICA",
    "SOPORTE INFRAESTRUCTURA",
    "SOPORTE PAIIJ",
    "SOPORTE PLATAFORMA WEB",
    "SOPORTE PODER EN LINEA",
    "SOPORTE SAJI",
    "SOPORTE SIGE",
    "SOPORTE TECNICO",
    "SOPORTE USUARIO",
]
ROLES_RECIBOS_NOMINA = ["ADMINISTRADOR", "SOPORTE USUARIO"]

sistemas = Blueprint("sistemas", __name__, template_folder="templates")


@sistemas.route("/")
def start():
    """Pagina Inicial"""

    # Si el usuario está autenticado
    if current_user.is_authenticated:
        # Obtener los roles del usuario
        mis_roles = set(current_user.get_roles())

        # Mostrar start.jinja2
        return render_template(
            "sistemas/start.jinja2",
            mostrar_recibos_nomina=mis_roles.intersection(ROLES_RECIBOS_NOMINA) and current_user.curp != "",
            mostrar_tickets_soporte=mis_roles.intersection(ROLES_SOPORTES_TICKETS),
        )

    # No está autenticado, debe de iniciar sesión
    return redirect("/login")


@sistemas.route("/favicon.ico")
def favicon():
    """Favicon"""
    return send_from_directory("static/img", "favicon.ico", mimetype="image/vnd.microsoft.icon")


@sistemas.app_errorhandler(400)
def bad_request(error):
    """Solicitud errónea"""
    return render_template("sistemas/403.jinja2", error=error), 403


@sistemas.app_errorhandler(403)
def forbidden(error):
    """Acceso no autorizado"""
    return render_template("sistemas/403.jinja2"), 403


@sistemas.app_errorhandler(404)
def page_not_found(error):
    """Error página no encontrada"""
    return render_template("sistemas/404.jinja2"), 404


@sistemas.app_errorhandler(500)
def internal_server_error(error):
    """Error del servidor"""
    return render_template("sistemas/500.jinja2"), 500
