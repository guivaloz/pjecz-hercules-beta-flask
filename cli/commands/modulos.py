"""
CLI Modulos
"""

import re

from rich.console import Console
from typer import Typer

from pjecz_hercules_beta_flask.app import app
from pjecz_hercules_beta_flask.blueprints.modulos.models import Modulo

# Listado de módulos en el menú principal
MODULOS_EN_NAVEGACION = [
    "AUTORIDADES",
    "BITACORAS",
    "VSP DIGITALIZACIONES",
    "EDICTOS",
    "GLOSAS",
    "LISTAS DE ACUERDOS",
    "OFICINAS",
    "OFI DOCUMENTOS",
    "SENTENCIAS",
    "USUARIOS",
]

# Inicializar la aplicación
app.app_context().push()

modulos = Typer()


@modulos.command()
def actualizar_iconos():
    """Actualiza los iconos de los módulos, de 'mdi:ICONO' a 'mdi mid-ICONO' y desactiva de la navegación si no lo está"""
    console = Console()
    contador = 0
    for modulo in Modulo.query.order_by(Modulo.nombre).all():
        hay_cambios = False
        if modulo.en_navegacion is True and modulo.nombre not in MODULOS_EN_NAVEGACION:
            modulo.en_navegacion = False
            hay_cambios = True
        if modulo.en_navegacion is False and modulo.nombre in MODULOS_EN_NAVEGACION:
            modulo.en_navegacion = True
            hay_cambios = True
        if re.match(r"mdi:\w+", modulo.icono):
            modulo.icono = modulo.icono.replace("mdi:", "mdi mdi-")
            hay_cambios = True
        if hay_cambios is True:
            modulo.save()
            console.print(f"[green]Actualizado: {modulo.icono}")
            contador += 1
    console.print(f"[green]Se actualizaron {contador} iconos")
