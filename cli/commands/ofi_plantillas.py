"""
CLI Oficios Documentos
"""

from rich.console import Console
from rich.table import Table
from sqlalchemy import select
from typer import Exit, Option, Typer

from cli.lib.database import get_database
from pjecz_hercules_beta_flask.app import app
from pjecz_hercules_beta_flask.blueprints.autoridades.models import Autoridad
from pjecz_hercules_beta_flask.blueprints.ofi_plantillas.models import OfiPlantilla
from pjecz_hercules_beta_flask.blueprints.roles.models import Rol
from pjecz_hercules_beta_flask.blueprints.usuarios.models import Usuario
from pjecz_hercules_beta_flask.blueprints.usuarios_roles.models import UsuarioRol

app.app_context().push()

ofi_plantillas = Typer()


@ofi_plantillas.command()
def consultar():
    """Mostrar una tabla con las plantillas de oficios"""
    console = Console()
    console.print("Consultando las plantillas de oficios...")

    # Iniciar la sesión de base de datos
    database = get_database()

    # Preparar la consulta
    stmt = (
        select(
            OfiPlantilla.descripcion,
            Usuario.email,
            Usuario.puesto,
            Autoridad.clave,
            OfiPlantilla.destinatarios_emails,
            OfiPlantilla.esta_archivado,
            OfiPlantilla.esta_compartida,
        )
        .select_from(
            OfiPlantilla,
        )
        .join(
            Usuario,
        )
        .join(
            Autoridad,
        )
    )

    # Solo los que tengan estatus A
    stmt = stmt.filter(OfiPlantilla.estatus == "A")

    # Ordenar por descripción
    stmt = stmt.order_by(OfiPlantilla.descripcion)

    # Mostrar tabla
    tabla = Table(title="Oficios Plantillas")
    tabla.add_column("Descripción")
    tabla.add_column("Usuario e-mail")
    tabla.add_column("Usuario puesto")
    tabla.add_column("Autoridad")
    tabla.add_column("Destinatarios")
    tabla.add_column("Arch.")
    tabla.add_column("Comp.")
    for item in database.execute(stmt):
        tabla.add_row(
            item.descripcion,
            item.email,
            item.puesto,
            item.clave,
            item.destinatarios_emails or "",
            "Sí" if item.esta_archivado else "",
            "Sí" if item.esta_compartida else "",
        )
    console.print(tabla)
