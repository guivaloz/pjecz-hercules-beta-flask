"""
PJECZ Hercules Beta Flask
"""

from flask import Flask

from pjecz_hercules_beta_flask.blueprints.autoridades.views import autoridades
from pjecz_hercules_beta_flask.blueprints.bitacoras.views import bitacoras
from pjecz_hercules_beta_flask.blueprints.bitacoras_apis.views import bitacoras_apis
from pjecz_hercules_beta_flask.blueprints.distritos.views import distritos
from pjecz_hercules_beta_flask.blueprints.domicilios.views import domicilios
from pjecz_hercules_beta_flask.blueprints.entradas_salidas.views import entradas_salidas
from pjecz_hercules_beta_flask.blueprints.estados.views import estados
from pjecz_hercules_beta_flask.blueprints.materias.views import materias
from pjecz_hercules_beta_flask.blueprints.modulos.views import modulos
from pjecz_hercules_beta_flask.blueprints.municipios.views import municipios
from pjecz_hercules_beta_flask.blueprints.ofi_documentos.views import ofi_documentos
from pjecz_hercules_beta_flask.blueprints.ofi_documentos_adjuntos.views import ofi_documentos_adjuntos
from pjecz_hercules_beta_flask.blueprints.ofi_documentos_destinatarios.views import ofi_documentos_destinatarios
from pjecz_hercules_beta_flask.blueprints.ofi_plantillas.views import ofi_plantillas
from pjecz_hercules_beta_flask.blueprints.oficinas.views import oficinas
from pjecz_hercules_beta_flask.blueprints.permisos.views import permisos
from pjecz_hercules_beta_flask.blueprints.roles.views import roles
from pjecz_hercules_beta_flask.blueprints.sistemas.views import sistemas
from pjecz_hercules_beta_flask.blueprints.tareas.views import tareas
from pjecz_hercules_beta_flask.blueprints.usuarios.models import Usuario
from pjecz_hercules_beta_flask.blueprints.usuarios.views import usuarios
from pjecz_hercules_beta_flask.blueprints.usuarios_roles.views import usuarios_roles
from pjecz_hercules_beta_flask.blueprints.vsp_digitalizaciones.views import vsp_digitalizaciones
from pjecz_hercules_beta_flask.config.extensions import authentication, csrf, database, login_manager, moment
from pjecz_hercules_beta_flask.config.settings import Settings

# Crear la aplicación
app = Flask(__name__, instance_relative_config=True)
app.add_url_rule("/favicon.ico", endpoint="sistemas.favicon")
app.config.from_object(Settings())

# Registrar blueprints
app.register_blueprint(autoridades)
app.register_blueprint(bitacoras)
app.register_blueprint(bitacoras_apis)
app.register_blueprint(distritos)
app.register_blueprint(domicilios)
app.register_blueprint(entradas_salidas)
app.register_blueprint(estados)
app.register_blueprint(materias)
app.register_blueprint(modulos)
app.register_blueprint(municipios)
app.register_blueprint(oficinas)
app.register_blueprint(ofi_documentos)
app.register_blueprint(ofi_documentos_adjuntos)
app.register_blueprint(ofi_documentos_destinatarios)
app.register_blueprint(ofi_plantillas)
app.register_blueprint(permisos)
app.register_blueprint(roles)
app.register_blueprint(sistemas)
app.register_blueprint(tareas)
app.register_blueprint(usuarios)
app.register_blueprint(usuarios_roles)
app.register_blueprint(vsp_digitalizaciones)

# Inicializar extensiones
csrf.init_app(app)
database.init_app(app)
login_manager.init_app(app)
moment.init_app(app)

# Cargar el modelo de usuario para la autenticación
authentication(Usuario)
