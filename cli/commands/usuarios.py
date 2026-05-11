"""
CLI Usuarios
"""

import os

from dotenv import load_dotenv
from rich.console import Console
from typer import Typer

from pjecz_hercules_beta_flask.app import app
from pjecz_hercules_beta_flask.blueprints.usuarios.models import Usuario
from pjecz_hercules_beta_flask.config.extensions import pwd_context
from pjecz_hercules_beta_flask.lib.cryptography import convert_string_to_fernet_key, simmetric_crypt, simmetric_decrypt

# Cargar variables de entorno
load_dotenv()
FERNET_KEY = os.getenv("FERNET_KEY", "")
SALT = os.getenv("SALT", "")

# Inicializar la aplicación
app.app_context().push()

usuarios = Typer()


@usuarios.command()
def mostrar_api_key(email: str):
    """Muestra la API Key de un usuario existente"""
    console = Console()
    usuario = Usuario.query.filter(Usuario.email == email).first()
    if usuario is None:
        console.print(f"[red]El usuario con email {email} no existe.[/red]")
        return
    console.print(f"[green]Usuario: {usuario.email}[/green]")
    console.print(f"[green]API Key: {usuario.api_key}[/green]")
    console.print(f"[green]Expira:  {usuario.api_key_expiracion.strftime('%Y-%m-%d')}[/green]")


@usuarios.command()
def mostrar_efirma_contrasena(email: str):
    """Muestra la contraseña de la e-firma de un usuario existente"""
    console = Console()
    if FERNET_KEY == "":
        console.print("[red]No se han configurado la variable de entorno FERNET_KEY.[/red]")
        return
    usuario = Usuario.query.filter(Usuario.email == email).first()
    if usuario is None:
        console.print(f"[red]El usuario con email {email} no existe.[/red]")
        return
    if not usuario.efirma_contrasena:
        console.print(f"[yellow]El usuario {email} no tiene contraseña de e-firma.[/yellow]")
        return
    try:
        efirma_contrasena = simmetric_decrypt(usuario.efirma_contrasena, FERNET_KEY)
    except ValueError as error:
        console.print(f"[red]{error}[/red]")
        return
    console.print(f"[green]Usuario: {usuario.email}[/green]")
    console.print(f"[green]Contraseña e-firma: {efirma_contrasena}[/green]")


@usuarios.command()
def nueva_contrasena(email: str):
    """Nueva contraseña para un usuario existente"""
    console = Console()
    usuario = Usuario.query.filter(Usuario.email == email).first()
    if usuario is None:
        console.print(f"[red]El usuario con email {email} no existe.[/red]")
        return
    contrasena = input("Contraseña: ")
    usuario.contrasena = pwd_context.hash(contrasena.strip())
    usuario.save()
    console.print(f"[green]Se ha actualizado la contraseña para el usuario {email}.[/green]")


@usuarios.command()
def nueva_efirma_contrasena(email: str):
    """Nueva contraseña de e-firma para un usuario existente"""
    console = Console()
    if FERNET_KEY == "":
        console.print("[red]No se han configurado la variable de entorno FERNET_KEY.[/red]")
        return
    usuario = Usuario.query.filter(Usuario.email == email).first()
    if usuario is None:
        console.print(f"[red]El usuario con email {email} no existe.[/red]")
        return
    efirma_contrasena = input("Contraseña e-firma: ")
    if not efirma_contrasena.strip():
        usuario.efirma_contrasena = None
        usuario.save()
        console.print(f"[yellow]Se ha eliminado la contraseña de e-firma para el usuario {email}.[/yellow]")
        return
    try:
        efirma_contrasena_encriptada = simmetric_crypt(efirma_contrasena.strip(), FERNET_KEY)
    except ValueError as error:
        console.print(f"[red]{error}[/red]")
        return
    usuario.efirma_contrasena = efirma_contrasena_encriptada
    usuario.save()
    console.print(f"[green]Se ha actualizado la contraseña de e-firma para el usuario {email}.[/green]")
