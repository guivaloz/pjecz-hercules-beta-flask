"""
CLI DB
"""

import csv
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from typer import Typer

from pjecz_hercules_beta_flask.app import app
from pjecz_hercules_beta_flask.blueprints.autoridades.models import Autoridad
from pjecz_hercules_beta_flask.blueprints.distritos.models import Distrito
from pjecz_hercules_beta_flask.blueprints.domicilios.models import Domicilio
from pjecz_hercules_beta_flask.blueprints.estados.models import Estado
from pjecz_hercules_beta_flask.blueprints.materias.models import Materia
from pjecz_hercules_beta_flask.blueprints.modulos.models import Modulo
from pjecz_hercules_beta_flask.blueprints.municipios.models import Municipio
from pjecz_hercules_beta_flask.blueprints.oficinas.models import Oficina
from pjecz_hercules_beta_flask.blueprints.permisos.models import Permiso
from pjecz_hercules_beta_flask.blueprints.roles.models import Rol
from pjecz_hercules_beta_flask.blueprints.usuarios.models import Usuario
from pjecz_hercules_beta_flask.blueprints.usuarios_roles.models import UsuarioRol
from pjecz_hercules_beta_flask.config.extensions import database, pwd_context
from pjecz_hercules_beta_flask.lib.pwgen import generar_contrasena
from pjecz_hercules_beta_flask.lib.safe_string import safe_clave, safe_email, safe_string

# Rutas a los archivos CSV
AUTORIDADES_CSV = "seed/autoridades.csv"
DISTRITOS_CSV = "seed/distritos.csv"
DOMICILIOS_CSV = "seed/domicilios.csv"
ESTADOS_CSV = "seed/estados.csv"
MATERIAS_CSV = "seed/materias.csv"
MUNICIPIOS_CSV = "seed/municipios.csv"
MODULOS_CSV = "seed/modulos.csv"
OFICINAS_CSV = "seed/oficinas.csv"
PERMISOS_CSV = "seed/roles_permisos.csv"
ROLES_CSV = "seed/roles_permisos.csv"
USUARIOS_CSV = "seed/usuarios_roles.csv"
USUARIOS_ROLES_CSV = "seed/usuarios_roles.csv"

# Cargar variables de entorno
load_dotenv()
DEPLOYMENT_ENVIRONMENT = os.getenv("DEPLOYMENT_ENVIRONMENT", "DEVELOPMENT")

# Inicializar la aplicación
app.app_context().push()

db = Typer()


def alimentar_estados():
    """Alimentar Estados"""
    console = Console()
    ruta = Path(ESTADOS_CSV)
    if not ruta.exists():
        console.print(f"[red]ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        console.print(f"[red]ERROR: {ruta.name} no es un archivo.")
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
                console.print(f"[red]ERROR: estado_id {estado_id} no es consecutivo")
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
        console.print(f"[red]ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        console.print(f"[red]ERROR: {ruta.name} no es un archivo.")
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
                console.print(f"[red]ERROR: municipio_id {municipio_id} no es consecutivo")
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
        console.print(f"[red]ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        console.print(f"[red]ERROR: {ruta.name} no es un archivo.")
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
                console.print(f"[red]ERROR: materia_id {materia_id} no es consecutivo")
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
        console.print(f"[red]ERROR: {ruta_csv.name} no se encontró.")
        sys.exit(1)
    if not ruta_csv.is_file():
        console.print(f"[red]ERROR: {ruta_csv.name} no es un archivo.")
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
                console.print(f"[red]ERROR: modulo_id {modulo_id} no es consecutivo")
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


def alimentar_roles():
    """Alimentar Roles"""
    console = Console()
    ruta = Path(ROLES_CSV)
    if not ruta.exists():
        console.print(f"[red]ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        console.print(f"[red]ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
    console.print("Alimentando roles...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            rol_id = int(row["rol_id"])
            nombre = safe_string(row["nombre"], save_enie=True)
            estatus = row["estatus"]
            if rol_id != contador + 1:
                console.print(f"[red]ERROR: rol_id {rol_id} no es consecutivo")
                sys.exit(1)
            Rol(
                nombre=nombre,
                estatus=estatus,
            ).save()
            contador += 1
    console.print(f"[green]{contador} roles alimentados.")


def alimentar_permisos():
    """Alimentar Permisos"""
    console = Console()
    ruta = Path(PERMISOS_CSV)
    if not ruta.exists():
        console.print(f"[red]ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        console.print(f"[red]ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
    modulos = Modulo.query.all()
    if len(modulos) == 0:
        console.print("[red]ERROR: No hay modulos alimentados.")
        sys.exit(1)
    console.print("Alimentando permisos...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            rol_id = int(row["rol_id"])
            estatus = row["estatus"]
            rol = Rol.query.get(rol_id)
            if rol is None:
                console.print(f"[red]ERROR: rol_id {rol_id} no existe")
                sys.exit(1)
            for modulo in modulos:
                columna = modulo.nombre.lower()
                if columna not in row:
                    continue
                if row[columna] == "":
                    continue
                try:
                    nivel = int(row[columna])
                except ValueError:
                    nivel = 0
                if nivel < 0:
                    nivel = 0
                if nivel > 4:
                    nivel = 4
                Permiso(
                    rol=rol,
                    modulo=modulo,
                    nivel=nivel,
                    nombre=f"{rol.nombre} puede {Permiso.NIVELES[nivel]} en {modulo.nombre}",
                    estatus=estatus,
                ).save()
            contador += 1
    console.print(f"[green]{contador} permisos alimentados.")


def alimentar_distritos():
    """Alimentar Distritos"""
    console = Console()
    ruta = Path(DISTRITOS_CSV)
    if not ruta.exists():
        console.print(f"[red]ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        console.print(f"[red]ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
    console.print("Alimentando distritos...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            distrito_id = int(row["distrito_id"])
            clave = safe_clave(row["clave"])
            nombre = safe_string(row["nombre"], save_enie=True)
            nombre_corto = safe_string(row["nombre_corto"], save_enie=True)
            es_distrito_judicial = row["es_distrito_judicial"] == "1"
            es_distrito = row["es_distrito_judicial"] == "1"
            es_jurisdiccional = row["es_distrito_judicial"] == "1"
            estatus = row["estatus"]
            if distrito_id != contador + 1:
                console.print(f"[red]ERROR: distrito_id {distrito_id} no es consecutivo")
                sys.exit(1)
            Distrito(
                clave=clave,
                nombre=nombre,
                nombre_corto=nombre_corto,
                es_distrito_judicial=es_distrito_judicial,
                es_distrito=es_distrito,
                es_jurisdiccional=es_jurisdiccional,
                estatus=estatus,
            ).save()
            contador += 1
    console.print(f"[green]{contador} distritos alimentados.")


def alimentar_autoridades():
    """Alimentar Autoridades"""
    console = Console()
    ruta = Path(AUTORIDADES_CSV)
    if not ruta.exists():
        console.print(f"[red]ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        console.print(f"[red]ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
    distrito_nd = Distrito.query.filter_by(clave="ND").first()
    if distrito_nd is None:
        console.print("[red]ERROR: No se encontró el distrito 'ND'.")
        sys.exit(1)
    materia_nd = Materia.query.filter_by(clave="ND").first()
    if materia_nd is None:
        console.print("[red]ERROR: No se encontró la materia 'ND'.")
        sys.exit(1)
    municipio_default = Municipio.query.filter_by(estado_id=5, clave="030").first()  # Coahuila de Zaragoza, Saltillo
    if municipio_default is None:
        console.print("[red]ERROR: No se encontró el municipio 'Coahuila de Zaragoza, Saltillo'.")
        sys.exit(1)
    console.print("Alimentando autoridades...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            # Si autoridad_id NO es consecutivo, se inserta una autoridad "NO EXISTE"
            autoridad_id = int(row["autoridad_id"])
            while autoridad_id > contador + 1:
                Autoridad(
                    distrito_id=distrito_nd.id,
                    materia_id=materia_nd.id,
                    municipio_id=municipio_default.id,
                    clave=f"NE-{contador}",
                    descripcion="NO EXISTE",
                    descripcion_corta="NO EXISTE",
                    es_archivo_solicitante=False,
                    es_cemasc=False,
                    es_defensoria=False,
                    es_extinto=False,
                    es_jurisdiccional=False,
                    es_notaria=False,
                    es_organo_especializado=False,
                    es_revisor_escrituras=False,
                    organo_jurisdiccional="NO DEFINIDO",
                    directorio_edictos="",
                    directorio_glosas="",
                    directorio_listas_de_acuerdos="",
                    directorio_sentencias="",
                    audiencia_categoria="NO DEFINIDO",
                    limite_dias_listas_de_acuerdos=0,
                    datawarehouse_id=0,
                    sede="ND",
                    estatus="B",
                ).save()
                contador += 1
            distrito_id = int(row["distrito_id"])
            materia_id = int(row["materia_id"])
            municipio_id = int(row["municipio_id"])
            clave = safe_clave(row["clave"])
            descripcion = safe_string(row["descripcion"], save_enie=True)
            descripcion_corta = safe_string(row["descripcion_corta"], save_enie=True)
            es_archivo_solicitante = row["es_archivo_solicitante"] == "1"
            es_cemasc = row["es_archivo_solicitante"] == "1"
            es_defensoria = row["es_archivo_solicitante"] == "1"
            es_extinto = row["es_archivo_solicitante"] == "1"
            es_jurisdiccional = row["es_jurisdiccional"] == "1"
            es_notaria = row["es_notaria"] == "1"
            es_organo_especializado = row["es_organo_especializado"] == "1"
            es_revisor_escrituras = row["es_revisor_escrituras"] == "1"
            organo_jurisdiccional = safe_string(row["organo_jurisdiccional"], save_enie=True)
            directorio_edictos = row["directorio_edictos"]
            directorio_glosas = row["directorio_glosas"]
            directorio_listas_de_acuerdos = row["directorio_listas_de_acuerdos"]
            directorio_sentencias = row["directorio_sentencias"]
            audiencia_categoria = row["audiencia_categoria"]
            limite_dias_listas_de_acuerdos = int(row["limite_dias_listas_de_acuerdos"])
            try:
                datawarehouse_id = int(row["datawarehouse_id"])
            except ValueError:
                datawarehouse_id = 0
            sede = row["sede"]
            estatus = row["estatus"]
            distrito = Distrito.query.get(distrito_id)
            if distrito is None:
                console.print(f"[red]AVISO: distrito_id {distrito_id} no existe")
                sys.exit(1)
            materia = Materia.query.get(materia_id)
            if materia is None:
                console.print(f"[red]AVISO: materia_id {materia_id} no existe")
                sys.exit(1)
            municipio = Municipio.query.get(municipio_id)
            if municipio is None:
                console.print(f"[red]AVISO: municipio_id {municipio_id} no existe")
                sys.exit(1)
            Autoridad(
                distrito=distrito,
                materia=materia,
                municipio=municipio,
                clave=clave,
                descripcion=descripcion,
                descripcion_corta=descripcion_corta,
                es_archivo_solicitante=es_archivo_solicitante,
                es_cemasc=es_cemasc,
                es_defensoria=es_defensoria,
                es_extinto=es_extinto,
                es_jurisdiccional=es_jurisdiccional,
                es_notaria=es_notaria,
                es_organo_especializado=es_organo_especializado,
                es_revisor_escrituras=es_revisor_escrituras,
                organo_jurisdiccional=organo_jurisdiccional,
                directorio_edictos=directorio_edictos,
                directorio_glosas=directorio_glosas,
                directorio_listas_de_acuerdos=directorio_listas_de_acuerdos,
                directorio_sentencias=directorio_sentencias,
                audiencia_categoria=audiencia_categoria,
                limite_dias_listas_de_acuerdos=limite_dias_listas_de_acuerdos,
                datawarehouse_id=datawarehouse_id,
                sede=sede,
                estatus=estatus,
            ).save()
            contador += 1
    console.print(f"[green]{contador} autoridades alimentadas.")


def alimentar_domicilios():
    """Alimentar Domicilios"""
    console = Console()
    ruta = Path(DOMICILIOS_CSV)
    if not ruta.exists():
        console.print(f"[red]ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        console.print(f"[red]ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
    console.print("Alimentando domicilios...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            domicilio_id = int(row["domicilio_id"])
            distrito_clave = safe_clave(row["distrito_clave"])
            edificio = safe_string(row["edificio"], save_enie=True)
            estado = safe_string(row["estado"], save_enie=True)
            municipio = safe_string(row["municipio"], save_enie=True)
            calle = safe_string(row["calle"], save_enie=True)
            num_ext = safe_string(row["num_ext"], save_enie=True)
            num_int = safe_string(row["num_int"], save_enie=True)
            colonia = safe_string(row["colonia"], save_enie=True)
            cp = int(row["cp"])
            estatus = row["estatus"]
            if domicilio_id != contador + 1:
                console.print(f"[red]ERROR: domicilio_id {domicilio_id} no es consecutivo")
                sys.exit(1)
            distrito = Distrito.query.filter_by(clave=distrito_clave).first()
            if distrito is None:
                console.print(f"[red]ERROR: distrito_clave {distrito_clave} no existe")
                sys.exit(1)
            domicilio = Domicilio(
                distrito=distrito,
                edificio=edificio,
                estado=estado,
                municipio=municipio,
                calle=calle,
                num_ext=num_ext,
                num_int=num_int,
                colonia=colonia,
                cp=cp,
                estatus=estatus,
            )
            domicilio.completo = domicilio.elaborar_completo()
            domicilio.save()
            contador += 1
    console.print(f"[green]{contador} distritos alimentados.")


def alimentar_oficinas():
    """Alimentar Oficinas"""
    console = Console()
    ruta = Path(OFICINAS_CSV)
    if not ruta.exists():
        console.print(f"[red]ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        console.print(f"[red]ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
    console.print("Alimentando oficinas...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            oficina_id = int(row["oficina_id"])
            distrito_id = int(row["distrito_id"])
            domicilio_id = int(row["domicilio_id"])
            clave = safe_clave(row["clave"])
            descripcion = safe_string(row["descripcion"], max_len=512, save_enie=True)
            descripcion_corta = safe_string(row["descripcion_corta"], max_len=64, save_enie=True)
            es_jurisdiccional = row["es_jurisdiccional"] == "1"
            apertura = datetime.strptime(row["apertura"], "%H:%M:%S")
            cierre = datetime.strptime(row["cierre"], "%H:%M:%S")
            limite_personas = int(row["limite_personas"])
            telefono = safe_string(row["telefono"], max_len=48)
            extension = safe_string(row["extension"], max_len=24)
            estatus = row["estatus"]
            if oficina_id != contador + 1:
                console.print(f"[red]ERROR: oficina_id {oficina_id} no es consecutivo")
                sys.exit(1)
            distrito = Distrito.query.get(distrito_id)
            if distrito is None:
                console.print(f"[red]ERROR: distrito_id {distrito_id} no existe")
                sys.exit(1)
            domicilio = Domicilio.query.get(domicilio_id)
            if domicilio is None:
                console.print(f"[red]ERROR: domicilio_id {domicilio_id} no existe")
                sys.exit(1)
            Oficina(
                domicilio=domicilio,
                distrito=distrito,
                clave=clave,
                descripcion=descripcion,
                descripcion_corta=descripcion_corta,
                es_jurisdiccional=es_jurisdiccional,
                apertura=apertura,
                cierre=cierre,
                limite_personas=limite_personas,
                telefono=telefono,
                extension=extension,
                estatus=estatus,
            ).save()
            contador += 1
    console.print(f"[green]{contador} oficinas alimentadas.")


def alimentar_usuarios():
    """Alimentar Usuarios"""
    console = Console()
    ruta = Path(USUARIOS_CSV)
    if not ruta.exists():
        console.print(f"[red]ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        console.print(f"[red]ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
    autoridad_nd = Autoridad.query.filter_by(clave="ND").first()
    if autoridad_nd is None:
        console.print("[red]ERROR: No se encontró la autoridad 'ND'.")
        sys.exit(1)
    oficina_nd = Oficina.query.filter_by(clave="ND").first()
    if oficina_nd is None:
        console.print("[red]ERROR: No se encontró la oficina 'ND'.")
        sys.exit(1)
    console.print("Alimentando usuarios...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            # Si usuario_id NO es consecutivo, se inserta un usuario "NO EXISTE"
            usuario_id = int(row["usuario_id"])
            while usuario_id > contador + 1:
                Usuario(
                    autoridad_id=autoridad_nd.id,
                    oficina_id=oficina_nd.id,
                    email=f"no-existe-{contador}@server.com",
                    nombres="NO EXISTE",
                    apellido_paterno="",
                    apellido_materno="",
                    curp="",
                    puesto="",
                    workspace="EXTERNO",
                    estatus="B",
                    api_key="",
                    api_key_expiracion=datetime(year=2000, month=1, day=1),
                    contrasena=pwd_context.hash(generar_contrasena()),
                ).save()
                contador += 1
            autoridad_clave = safe_clave(row["autoridad_clave"])
            oficina_id = int(row["oficina_id"])
            email = safe_email(row["email"])
            nombres = safe_string(row["nombres"], save_enie=True)
            apellido_paterno = safe_string(row["apellido_paterno"], save_enie=True)
            apellido_materno = safe_string(row["apellido_materno"], save_enie=True)
            curp = safe_string(row["curp"])
            puesto = safe_string(row["puesto"], save_enie=True)
            workspace = safe_string(row["workspace"])
            estatus = row["estatus"]
            autoridad = Autoridad.query.filter_by(clave=autoridad_clave).first()
            if autoridad is None:
                console.print(f"[red]ERROR: autoridad_clave {autoridad_clave} no existe")
                sys.exit(1)
            oficina = Oficina.query.get(oficina_id)
            if oficina is None:
                console.print(f"[red]ERROR: oficina_id {oficina_id} no existe")
                sys.exit(1)
            Usuario(
                autoridad=autoridad,
                oficina=oficina,
                email=email,
                nombres=nombres,
                apellido_paterno=apellido_paterno,
                apellido_materno=apellido_materno,
                curp=curp,
                puesto=puesto,
                workspace=workspace,
                estatus=estatus,
                api_key="",
                api_key_expiracion=datetime(year=2000, month=1, day=1),
                contrasena=pwd_context.hash(generar_contrasena()),
            ).save()
            contador += 1
    console.print(f"[green]{contador} usuarios alimentados.")


def alimentar_usuarios_roles():
    """Alimentar Usuarios-Roles"""
    console = Console()
    ruta = Path(USUARIOS_ROLES_CSV)
    if not ruta.exists():
        console.print(f"[red]ERROR: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        console.print(f"[red]ERROR: {ruta.name} no es un archivo.")
        sys.exit(1)
    usuarios_que_no_existen = []
    console.print("Alimentando usuarios-roles...")
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            usuario_id = int(row["usuario_id"])
            usuario = Usuario.query.get(usuario_id)
            if usuario is None:
                usuarios_que_no_existen.append(str(usuario_id))
                continue
            for rol_nombre in row["roles"].split(","):
                rol_nombre = rol_nombre.strip().upper()
                rol = Rol.query.filter_by(nombre=rol_nombre).first()
                if rol is None:
                    continue
                UsuarioRol(
                    usuario=usuario,
                    rol=rol,
                    descripcion=f"{usuario.email} en {rol.nombre}",
                ).save()
                contador += 1
    if usuarios_que_no_existen:
        console.print(f"[yellow]AVISO: {','.join(usuarios_que_no_existen)} usuarios no existen.")
    console.print(f"[green]{contador} usuarios-roles alimentados.")


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
    alimentar_roles()
    alimentar_permisos()
    alimentar_distritos()
    alimentar_autoridades()
    alimentar_domicilios()
    alimentar_oficinas()
    alimentar_usuarios()
    alimentar_usuarios_roles()
    console.print("[green]La base de datos se ha alimentado correctamente.")


@db.command()
def reiniciar():
    """Reiniciar la base de datos (inicializar y alimentar)"""
    inicializar()
    alimientar()
