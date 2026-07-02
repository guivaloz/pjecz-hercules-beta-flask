"""
CLI Autoridades
"""

import os
import re
import sys

from dotenv import load_dotenv
from rich.console import Console
from typer import Typer

from pjecz_hercules_beta_flask.app import app
from pjecz_hercules_beta_flask.blueprints.autoridades.models import Autoridad

# Lista de organismos jurisdiccionales que tienen glosas
ORGANOS_JURISDICCIONALES_CON_GLOSAS = [
    "PLENO O SALA DEL TSJ",
    "TRIBUNAL DE CONCILIACION Y ARBITRAJE",
]

# Cargar variables de entorno
load_dotenv()
DEPLOYMENT_ENVIRONMENT = os.getenv("DEPLOYMENT_ENVIRONMENT", "DEVELOPMENT").upper()

# Inicializar la aplicación
app.app_context().push()

autoridades = Typer()


@autoridades.command()
def actualizar():
    """Actualiza los tablero_icono de las autoridades, de 'mdi:ICONO' a 'mdi mid-ICONO'"""
    console = Console()

    if DEPLOYMENT_ENVIRONMENT != "DEVELOPMENT":
        console.print(f"[red]PROHIBIDO: No se inicializa porque DEPLOYMENT_ENVIRONMENT es {DEPLOYMENT_ENVIRONMENT}.")
        sys.exit(1)

    contador = 0
    for autoridad in Autoridad.query.order_by(Autoridad.clave).all():
        cambios = []

        # Actualizar directorios
        directorio_edictos = ""
        directorio_estrados = ""
        directorio_glosas = ""
        directorio_listas_de_acuerdos = ""
        directorio_sentencias = ""
        if autoridad.es_jurisdiccional is True:
            directorio_edictos = f"{autoridad.distrito.clave}/{autoridad.clave}"
            directorio_estrados = f"{autoridad.distrito.clave}/{autoridad.clave}"
            if autoridad.organo_jurisdiccional in ORGANOS_JURISDICCIONALES_CON_GLOSAS:
                directorio_glosas = f"{autoridad.distrito.clave}/{autoridad.clave}"
            directorio_listas_de_acuerdos = f"{autoridad.distrito.clave}/{autoridad.clave}"
            directorio_sentencias = f"{autoridad.distrito.clave}/{autoridad.clave}"
        if autoridad.es_notaria is True:
            directorio_edictos = f"{autoridad.distrito.clave}/{autoridad.clave}"
            directorio_estrados = ""
            directorio_glosas = ""
            directorio_listas_de_acuerdos = ""
            directorio_sentencias = ""
        if autoridad.directorio_edictos != directorio_edictos:
            autoridad.directorio_edictos = directorio_edictos
            cambios.append(f"directorio_edictos: {autoridad.directorio_edictos}")
        if autoridad.directorio_estrados != directorio_estrados:
            autoridad.directorio_estrados = directorio_estrados
            cambios.append(f"directorio_estrados: {autoridad.directorio_estrados}")
        if autoridad.directorio_glosas != directorio_glosas:
            autoridad.directorio_glosas = directorio_glosas
            cambios.append(f"directorio_glosas: {autoridad.directorio_glosas}")
        if autoridad.directorio_listas_de_acuerdos != directorio_listas_de_acuerdos:
            autoridad.directorio_listas_de_acuerdos = directorio_listas_de_acuerdos
            cambios.append(f"directorio_listas_de_acuerdos: {autoridad.directorio_listas_de_acuerdos}")
        if autoridad.directorio_sentencias != directorio_sentencias:
            autoridad.directorio_sentencias = directorio_sentencias
            cambios.append(f"directorio_sentencias: {autoridad.directorio_sentencias}")

        # Actualizar iconos de 'mdi:ICONO' a 'mdi mid-ICONO'
        if autoridad.tablero_icono and re.match(r"mdi:\w+", autoridad.tablero_icono):
            autoridad.tablero_icono = autoridad.tablero_icono.replace("mdi:", "mdi mdi-")
            cambios.append(f"tablero_icono: {autoridad.tablero_icono}")

        # Guardar cambios
        if cambios:
            autoridad.save()
            console.print(f"[green]Actualizado: {', '.join(cambios)}")
            contador += 1

    # Mostrar mensaje final
    if contador == 0:
        console.print("[yellow]No hubo actualizaciones")
    else:
        console.print(f"[green]Se actualizaron {contador} autoridades")
