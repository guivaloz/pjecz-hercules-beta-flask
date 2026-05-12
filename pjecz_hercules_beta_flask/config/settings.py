"""
Settings
"""

import os
from functools import lru_cache
from turtle import st

from google.cloud import secretmanager
from pydantic_settings import BaseSettings


def get_secret(secret_id: str, default: str = "") -> str:
    """Obtener el valor del secreto desde Google Cloud Secret Manager o desde las variables de entorno"""
    project_id = os.getenv("PROJECT_ID", "")
    service_prefix = os.getenv("SERVICE_PREFIX", "pjecz_hercules_flask")

    # Si PROJECT_ID está vacío estamos en modo de desarrollo
    if project_id == "":
        value = os.getenv(secret_id.upper(), "")
        # Si el valor es texto vacio, entregar el valor por defecto
        if value == "":
            return default
        return value

    # Tratar de obtener el secreto
    try:
        # Create the secret manager client
        client = secretmanager.SecretManagerServiceClient()
        # Build the resource name of the secret version
        secret = f"{service_prefix}_{secret_id}".lower()
        name = client.secret_version_path(project_id, secret, "latest")
        # Access the secret version
        response = client.access_secret_version(name=name)
        # Return the decoded payload
        return response.payload.data.decode("UTF-8")
    except:
        pass

    # Si no funciona lo anterior, entregar el valor por defecto
    return default


class Settings(BaseSettings):
    """Settings"""

    # Variables de entorno
    AUTORIDADES_PAGINA_CABECERA_URL: str = get_secret("AUTORIDADES_PAGINA_CABECERA_URL")
    AUTORIDADES_PAGINA_PIE_URL: str = get_secret("AUTORIDADES_PAGINA_PIE_URL")
    CLOUD_STORAGE_DEPOSITO: str = get_secret("CLOUD_STORAGE_DEPOSITO")
    CLOUD_STORAGE_DEPOSITO_EDICTOS: str = get_secret("CLOUD_STORAGE_DEPOSITO_EDICTOS")
    CLOUD_STORAGE_DEPOSITO_EXHORTOS: str = get_secret("CLOUD_STORAGE_DEPOSITO_EXHORTOS")
    CLOUD_STORAGE_DEPOSITO_GLOSAS: str = get_secret("CLOUD_STORAGE_DEPOSITO_GLOSAS")
    CLOUD_STORAGE_DEPOSITO_LISTAS_DE_ACUERDOS: str = get_secret("CLOUD_STORAGE_DEPOSITO_LISTAS_DE_ACUERDOS")
    CLOUD_STORAGE_DEPOSITO_OFICIOS: str = get_secret("CLOUD_STORAGE_DEPOSITO_OFICIOS")
    CLOUD_STORAGE_DEPOSITO_PERSEO: str = get_secret("CLOUD_STORAGE_DEPOSITO_PERSEO")
    CLOUD_STORAGE_DEPOSITO_REQUISICIONES: str = get_secret("CLOUD_STORAGE_DEPOSITO_REQUISICIONES")
    CLOUD_STORAGE_DEPOSITO_SENTENCIAS: str = get_secret("CLOUD_STORAGE_DEPOSITO_SENTENCIAS")
    CLOUD_STORAGE_DEPOSITO_VALES_GASOLINA: str = get_secret("CLOUD_STORAGE_DEPOSITO_VALES_GASOLINA")
    ESTADO_CLAVE: str = get_secret("ESTADO_CLAVE", "05")
    HOST: str = get_secret("HOST", "http://127.0.0.1:5000")
    MUNICIPIO_CLAVE: str = get_secret("MUNICIPIO_CLAVE", "030")
    PREFIX: str = get_secret("PREFIX")
    SECRET_KEY: str = get_secret("SECRET_KEY")
    SALT: str = get_secret("SALT")
    SQLALCHEMY_DATABASE_URI: str = get_secret("SQLALCHEMY_DATABASE_URI")
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


@lru_cache()
def get_settings() -> Settings:
    """Get Settings"""
    return Settings()
