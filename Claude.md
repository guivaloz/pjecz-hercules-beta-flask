# CLAUDE.md — Aplicación Web Flask

Guía de contexto para Claude Code al trabajar en este proyecto.

---

## Descripción del proyecto

Aplicación web construida con **Flask** y base de datos **PostgreSQL**.
Backend en Python, orientada a ser mantenible, segura y lista para producción.
Usa Bootstrap para el frontend, con enfoque en usabilidad y profesionalismo.

---

## Stack tecnológico

| Capa         | Tecnología                          |
|--------------|-------------------------------------|
| Lenguaje     | Python 3.14                         |
| Framework    | Flask 3.1.3                         |
| Base de datos| PostgreSQL (psycopg2 / SQLAlchemy)  |
| ORM          | SQLAlchemy + Flask-SQLAlchemy       |
| Autenticación| Flask-Login                         |
| Formularios  | Flask-WTF (WTForms)                 |
| Variables de entorno | pydantic-settings (.env)    |
| Servidor dev | Flask built-in (debug=True)         |
| Servidor prod| Gunicorn + Google Cloud App Engine  |

---

## Estructura del proyecto

```
pjecz-hercules-beta-flask/
├── pjecz_hercules_beta_flask/       # Código fuente de la aplicación
│   ├── __init__.py
│   ├── app.py                       # Aplicación principal
│   ├── blueprints/                  # Blueprints organizados por módulos
│   │   ├── __init__.py
│   │   └── <MODULO>/                # Módulo específico (ej. ofi_plantillas)
│   │       ├── __init__.py
│   │       ├── forms.py             # Formularios WTForms para este módulo
│   │       ├── models.py            # Modelos SQLAlchemy para este módulo
│   │       ├── tasks.py             # Tareas asíncronas (si aplica)
│   │       ├── views.py             # Rutas y lógica de vistas para este módulo
│   │       └── templates/<MODULO>/  # Plantillas para este módulo
│   │           └── *.jinja2         # Plantillas HTML
│   ├── config/                      # Configuraciones
│   ├── lib/                         # Librerías auxiliares
│   ├── static/                      # CSS, JS, imágenes
│   └── templates                    # Plantillas globales
├── .env                             # Variables locales (NO en git)
└── pyproject.toml                   # Dependencias y configuración del proyecto
```

---

## Configuración (settings.py)

```python
class Settings(BaseSettings):
    """Settings"""

    # Variables de entorno
    ENVIRONMENT: str = get_secret("ENVIRONMENT", "development")
    HOST: str = get_secret("HOST", "http://127.0.0.1:5000")
    PREFIX: str = get_secret("PREFIX", "")
    SECRET_KEY: str = get_secret("SECRET_KEY", "")
    SALT: str = get_secret("SALT", "")
    SQLALCHEMY_DATABASE_URI: str = get_secret("SQLALCHEMY_DATABASE_URI", "")
    TZ: str = get_secret("TZ", "America/Mexico_City")

    # Incrementar el tamaño de lo que se sube en los formularios
    MAX_CONTENT_LENGTH: int = 24 * 1024 * 1024
    MAX_FORM_MEMORY_SIZE: int = 24 * 1024 * 1024

    class Config:
        """Load configuration"""

        @classmethod
        def customise_sources(cls, init_settings, env_settings, file_secret_settings):
            """Change the order of precedence of settings sources"""
            return env_settings, file_secret_settings, init_settings
```

> Nunca poner credenciales en código. Siempre usar variables de entorno.

---

## Aplicación (app.py)

```python
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

# Inicializar extensiones
csrf.init_app(app)
database.init_app(app)
login_manager.init_app(app)
moment.init_app(app)

# Cargar el modelo de usuario para la autenticación
authentication(Usuario)
```

Usar **Blueprints** siempre. Evitar rutas sueltas en `app.py`.

---

## Base de datos

- ORM: **SQLAlchemy** para todo acceso a datos.
- Para insertar datos, crear una instancia del modelo y llamar a `save()` (que hace `db.session.add()` y `db.session.commit()`).

```python
instancia = Modelo(
    columna_1=columna_1,
    columna_2=columna_2,
)
instancia.save()
```

- Para actualizar, modificar los atributos y luego llamar a `save()`.

```python
instancia.columna_1 = nuevo_valor
instancia.save()
```

---

## Seguridad

- `SECRET_KEY` aleatoria y larga (mínimo 32 bytes).
- CSRF habilitado con Flask-WTF en todos los formularios.
- Validar y sanitizar toda entrada del usuario con WTForms.
- Usar HTTPS en producción (Google Cloud App Engine).

---

## Convenciones de código

- Seguir **PEP 8**. Ignorar **F821** (variables no definidas) en modelos y vistas.
- La longuitud máxima de línea es 128 caracteres.
- Nombres de clases en **PascalCase** con un prefijo de tres letras (ej. `OfiPlantilla`).
- Nombres de variables y funciones en **snake_case**.
- Nombres de rutas y URLs en **snake_case**
- Blueprints por módulo, no por tipo de archivo.

---

## Lo que Claude NO debe hacer

- No ejecutar `flask run` en modo producción.
- No hacer `db.drop_all()` ni `db.create_all()` en código de producción.
- No hardcodear contraseñas, tokens ni URIs de conexión.
- No ignorar errores de base de datos sin rollback.
- No crear rutas fuera de blueprints.
