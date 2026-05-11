"""
CLI Modulos
"""

import re

from rich.console import Console
from typer import Typer

from pjecz_hercules_beta_flask.app import app
from pjecz_hercules_beta_flask.blueprints.modulos.models import Modulo

# Inicializar la aplicación
app.app_context().push()

modulos = Typer()


@modulos.command()
def actualizar_iconos():
    """Actualiza los iconos de los módulos, de 'mdi:ICONO' a 'mdi mid-ICONO'"""
    console = Console()
    contador = 0
    for modulo in Modulo.query.order_by(Modulo.nombre).all():
        if re.match(r"mdi:\w+", modulo.icono):
            modulo.icono = modulo.icono.replace("mdi:", "mdi mdi-")
            modulo.save()
            console.print(f"[green]Actualizado: {modulo.icono}")
            contador += 1
    console.print(f"[green]Se actualizaron {contador} iconos")
