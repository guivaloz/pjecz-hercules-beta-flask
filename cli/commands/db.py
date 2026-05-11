"""
CLI DB
"""

import csv
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from typer import Typer

from pjecz_hercules_beta_flask.app import app
from pjecz_hercules_beta_flask.blueprints.estados.models import Estado
from pjecz_hercules_beta_flask.blueprints.materias.models import Materia
from pjecz_hercules_beta_flask.blueprints.modulos.models import Modulo
from pjecz_hercules_beta_flask.blueprints.municipios.models import Municipio
from pjecz_hercules_beta_flask.config.extensions import database
from pjecz_hercules_beta_flask.lib.safe_string import safe_clave, safe_string

# Cargar variables de entorno
load_dotenv()
DEPLOYMENT_ENVIRONMENT = os.getenv("DEPLOYMENT_ENVIRONMENT", "DEVELOPMENT")

# Rutas a los archivos CSV
ESTADOS_CSV = "seed/estados.csv"
MUNICIPIOS_CSV = "seed/municipios.csv"
MATERIAS_CSV = "seed/materias.csv"
MODULOS_CSV = "seed/modulos.csv"

# Inicializar la aplicación y la base de datos
app.app_context().push()
database.init_app(app)

db = Typer()


def alimentar_estados():
    """Alimentar Estados"""
    console = Console()
    ruta = Path(ESTADOS_CSV)
    if not ruta.exists():
        console.print(f"[red]AVISO: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        console.print(f"[red]AVISO: {ruta.name} no es un archivo.")
        sys.exit(1)
    console.print("Alimentando estados...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            estado_id = int(row["estado_id"])
            clave = safe_clave(row["clave"])
            nombre = safe_string(row["nombre"], save_enie=True)
            estatus = row["estatus"]
            if estado_id != contador + 1:
                console.print(f"[yellow]AVISO: estado_id {estado_id} no es consecutivo")
                sys.exit(1)
            Estado(
                clave=clave,
                nombre=nombre,
                estatus=estatus,
            ).save()
            contador += 1
    console.print(f"[green]{contador} estados alimentados.")


def alimentar_municipios():
    """Alimentar Municipios"""
    console = Console()
    ruta = Path(MUNICIPIOS_CSV)
    if not ruta.exists():
        console.print(f"[red]AVISO: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        console.print(f"[red]AVISO: {ruta.name} no es un archivo.")
        sys.exit(1)
    console.print("Alimentando municipios...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            municipio_id = int(row["municipio_id"])
            estado_id = int(row["estado_id"])
            clave = safe_clave(row["clave"])
            nombre = safe_string(row["nombre"], save_enie=True)
            estatus = row["estatus"]
            if municipio_id != contador + 1:
                console.print(f"[yellow]AVISO: municipio_id {municipio_id} no es consecutivo")
                sys.exit(1)
            Municipio(
                estado_id=estado_id,
                clave=clave,
                nombre=nombre,
                estatus=estatus,
            ).save()
            contador += 1
    console.print(f"[green]{contador} municipios alimentados.")


def alimentar_materias():
    """Alimentar Materias"""
    console = Console()
    ruta = Path(MATERIAS_CSV)
    if not ruta.exists():
        console.print(f"[red]AVISO: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        console.print(f"[red]AVISO: {ruta.name} no es un archivo.")
        sys.exit(1)
    console.print("Alimentando materias...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            materia_id = int(row["materia_id"])
            clave = row["clave"]
            nombre = safe_string(row["nombre"], save_enie=True)
            descripcion = safe_string(row["descripcion"], max_len=1024, do_unidecode=False, save_enie=True)
            en_sentencias = row["en_sentencias"] == "1"
            estatus = row["estatus"]
            if materia_id != contador + 1:
                console.print(f"[yellow]AVISO: materia_id {materia_id} no es consecutivo")
                sys.exit(1)
            Materia(
                clave=clave,
                nombre=nombre,
                descripcion=descripcion,
                en_sentencias=en_sentencias,
                estatus=estatus,
            ).save()
            contador += 1
    console.print(f"[green]{contador} materias alimentadas.")


def alimentar_modulos():
    """Alimentar Modulos"""
    console = Console()
    ruta_csv = Path(MODULOS_CSV)
    if not ruta_csv.exists():
        console.print(f"[red]AVISO: {ruta_csv.name} no se encontró.")
        sys.exit(1)
    if not ruta_csv.is_file():
        console.print(f"[red]AVISO: {ruta_csv.name} no es un archivo.")
        sys.exit(1)
    console.print("Alimentando modulos...")
    contador = 0
    with open(ruta_csv, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            modulo_id = int(row["modulo_id"])
            nombre = safe_string(row["nombre"], save_enie=True)
            nombre_corto = safe_string(row["nombre_corto"], do_unidecode=False, save_enie=True, to_uppercase=False)
            icono = row["icono"]
            ruta = row["ruta"]
            en_navegacion = row["en_navegacion"] == "1"
            en_plataforma_carina = row["en_plataforma_carina"] == "1"
            en_plataforma_hercules = row["en_plataforma_hercules"] == "1"
            en_plataforma_web = row["en_plataforma_web"] == "1"
            en_portal_notarias = row["en_portal_notarias"] == "1"
            estatus = row["estatus"]
            if modulo_id != contador + 1:
                console.print(f"[yellow]AVISO: modulo_id {modulo_id} no es consecutivo")
                sys.exit(1)
            Modulo(
                nombre=nombre,
                nombre_corto=nombre_corto,
                icono=icono,
                ruta=ruta,
                en_navegacion=en_navegacion,
                en_plataforma_carina=en_plataforma_carina,
                en_plataforma_hercules=en_plataforma_hercules,
                en_plataforma_web=en_plataforma_web,
                en_portal_notarias=en_portal_notarias,
                estatus=estatus,
            ).save()
            contador += 1
    console.print(f"[green]{contador} modulos alimentados.")


@db.command()
def inicializar():
    """Inicializar la base de datos"""
    console = Console()
    if DEPLOYMENT_ENVIRONMENT == "PRODUCTION":
        console.print("[red]PROHIBIDO: No se inicializa porque este es el servidor de producción.")
        sys.exit(1)
    database.drop_all()
    database.create_all()
    console.print("[green]La base de datos se ha inicializado correctamente.")


@db.command()
def alimientar():
    """Alimentar la base de datos con los datos en los archivos CSV en la carpeta 'seed'"""
    console = Console()
    if DEPLOYMENT_ENVIRONMENT == "PRODUCTION":
        console.print("[red]PROHIBIDO: No se inicializa porque este es el servidor de producción.")
        sys.exit(1)
    alimentar_estados()
    alimentar_municipios()
    alimentar_materias()
    alimentar_modulos()
    console.print("[green]La base de datos se ha alimentado correctamente.")


@db.command()
def reiniciar():
    """Reiniciar la base de datos (inicializar y alimentar)"""
    inicializar()
    alimientar()
