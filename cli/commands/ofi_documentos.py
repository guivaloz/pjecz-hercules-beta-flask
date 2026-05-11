"""
CLI Oficios Documentos
"""

from rich.console import Console
from rich.table import Table
from sqlalchemy import select
from typer import Exit, Option, Typer

from pjecz_hercules_beta_flask.app import app
from pjecz_hercules_beta_flask.blueprints.autoridades.models import Autoridad
from pjecz_hercules_beta_flask.blueprints.ofi_documentos.models import OfiDocumento
from pjecz_hercules_beta_flask.blueprints.roles.models import Rol
from pjecz_hercules_beta_flask.blueprints.usuarios.models import Usuario
from pjecz_hercules_beta_flask.blueprints.usuarios_roles.models import UsuarioRol
from pjecz_hercules_beta_flask.config.extensions import database

# Inicializar la aplicación
app.app_context().push()

ofi_documentos = Typer()


@ofi_documentos.command()
def consultar():
    """Mostrar una tabla con los documentos de oficios"""
    console = Console()
    console.print("Consultando los documentos de oficios...")


@ofi_documentos.command()
def enviar_a_efirma():
    """Enviar un documento al motor de firma electrónica"""
    console = Console()
    console.print("Enviando un documento al motor de firma electrónica...")


@ofi_documentos.command()
def enviar_a_sendgrid():
    """Enviar los mensajes a los destinatarios utilizando SendGrid"""
    console = Console()
    console.print("Enviando los mensajes a los destinatarios utilizando SendGrid...")


@ofi_documentos.command()
def convertir_a_pdf():
    """Convertir a PDF un documento de oficio"""
    console = Console()
    console.print("Convirtiendo a PDF un documento de oficio...")


@ofi_documentos.command()
def regresar_a_borrador():
    """Regresar a borrador un documento de oficio"""
    console = Console()
    console.print("Regresar a borrador un documento de oficio...")
