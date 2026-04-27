"""
CLI Autoridades
"""

import re

from rich.console import Console
from typer import Typer

from pjecz_hercules_beta_flask.app import app
from pjecz_hercules_beta_flask.blueprints.autoridades.models import Autoridad

app.app_context().push()

autoridades = Typer()


@autoridades.command()
def actualizar_iconos():
    """Actualiza los tablero_icono de las autoridades, de 'mdi:ICONO' a 'mdi mid-ICONO'"""
    console = Console()
    contador = 0
    for autoridad in Autoridad.query.order_by(Autoridad.clave).all():
        if autoridad.tablero_icono and re.match(r"mdi:\w+", autoridad.tablero_icono):
            autoridad.tablero_icono = autoridad.tablero_icono.replace("mdi:", "mdi mdi-")
            autoridad.save()
            console.print(f"[green]Actualizado: {autoridad.tablero_icono}")
            contador += 1
    console.print(f"[green]Se actualizaron {contador} iconos")
