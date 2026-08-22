"""
CLI Modulos
"""

import os
import re
import sys

from dotenv import load_dotenv
from rich.console import Console
from typer import Typer

from pjecz_hercules_beta_flask.app import create_app
from pjecz_hercules_beta_flask.blueprints.modulos.models import Modulo

# Listado de módulos en el menú principal
MODULOS_EN_NAVEGACION = [
    "ABOGADOS",
    "AUTORIDADES",
    "BITACORAS",
    "VSP DIGITALIZACIONES",
    "EDICTOS",
    "ESTRADOS",
    "GLOSAS",
    "LISTAS DE ACUERDOS",
    "OFICINAS",
    "OFI DOCUMENTOS",
    "SENTENCIAS",
    "TAREAS",
    "USUARIOS",
    "VSP DIGITALIZACIONES",
]

# Cargar variables de entorno
load_dotenv()
DEPLOYMENT_ENVIRONMENT = os.getenv("DEPLOYMENT_ENVIRONMENT", "DEVELOPMENT").upper()

# Inicializar la aplicación
app = create_app()
app.app_context().push()

modulos = Typer()


@modulos.command()
def actualizar():
    """Actualizar los iconos de los módulos, de 'mdi:ICONO' a 'mdi mid-ICONO' y desactiva de la navegación si no lo está"""
    console = Console()
    if DEPLOYMENT_ENVIRONMENT != "DEVELOPMENT":
        console.print(f"[red]PROHIBIDO: No se inicializa porque DEPLOYMENT_ENVIRONMENT es {DEPLOYMENT_ENVIRONMENT}.")
        sys.exit(1)
    contador = 0
    for modulo in Modulo.query.order_by(Modulo.nombre).all():
        mensajes = []
        if modulo.en_navegacion is True and modulo.nombre not in MODULOS_EN_NAVEGACION:
            modulo.en_navegacion = False
            mensajes.append(f"Fuera de navegación: {modulo.nombre}")
        if modulo.en_navegacion is False and modulo.nombre in MODULOS_EN_NAVEGACION:
            modulo.en_navegacion = True
            mensajes.append(f"En navegación: {modulo.nombre}")
        if re.match(r"mdi:\w+", modulo.icono):
            modulo.icono = modulo.icono.replace("mdi:", "mdi mdi-")
            mensajes.append(f"Icono actualizado: {modulo.icono}")
        if len(mensajes) > 0:
            modulo.save()
            console.print(f"[green]Actualizado: {modulo.nombre}[/green]")
            console.print("\n".join(mensajes))
            contador += 1
    console.print(f"[green]Se actualizaron {contador} modulos.[/green]")
