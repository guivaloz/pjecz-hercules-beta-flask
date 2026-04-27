"""
Autoridades, formularios
"""

from flask import current_app
from flask_wtf import FlaskForm
from wtforms import BooleanField, ColorField, IntegerField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, Regexp

from ...lib.safe_string import CLAVE_REGEXP
from ..distritos.models import Distrito
from ..estados.models import Estado
from ..materias.models import Materia
from ..municipios.models import Municipio
from .models import Autoridad


class AutoridadNewForm(FlaskForm):
    """Formulario para nueva Autoridad"""

    clave = StringField("Clave (única de hasta 16 caracteres)", validators=[DataRequired(), Regexp(CLAVE_REGEXP)])
    distrito = SelectField("Distrito", coerce=int, validators=[DataRequired()])
    materia = SelectField("Materia", coerce=int, validators=[DataRequired()])
    municipio = SelectField("Municipio", coerce=int, validators=[DataRequired()])
    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    descripcion_corta = StringField("Descripción corta (máximo 64 caracteres)", validators=[DataRequired(), Length(max=64)])
    es_archivo_solicitante = BooleanField("Es Archivo Solicitante", validators=[Optional()])
    es_cemasc = BooleanField("Es CEMASC", validators=[Optional()])
    es_defensoria = BooleanField("Es Defensoría", validators=[Optional()])
    es_extinto = BooleanField("Es Extinto", validators=[Optional()])
    es_jurisdiccional = BooleanField("Es Jurisdiccional", validators=[Optional()])
    es_notaria = BooleanField("Es Notaría", validators=[Optional()])
    es_organo_especializado = BooleanField("Es Órgano Especializado", validators=[Optional()])
    es_revisor_escrituras = BooleanField("Es revisor de escrituras", validators=[Optional()])
    audiencia_categoria = SelectField(
        "Categoría de Audiencias", choices=Autoridad.AUDIENCIAS_CATEGORIAS.items(), validators=[DataRequired()]
    )
    organo_jurisdiccional = SelectField(
        "Órgano Jurisdiccional", choices=Autoridad.ORGANOS_JURISDICCIONALES.items(), validators=[DataRequired()]
    )
    sede = SelectField("Sede (distrito geográfico para AJG)", choices=Autoridad.SEDES.items(), validators=[DataRequired()])
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones en distrito, materia y municipio"""
        super().__init__(*args, **kwargs)
        self.distrito.choices = [
            (d.id, d.nombre_corto) for d in Distrito.query.filter_by(estatus="A").order_by(Distrito.nombre_corto).all()
        ]
        self.materia.choices = [(m.id, m.nombre) for m in Materia.query.filter_by(estatus="A").order_by(Materia.nombre).all()]
        self.municipio.choices = [
            (m.id, m.nombre)
            for m in Municipio.query.join(Estado)
            .filter(Estado.clave == current_app.config["ESTADO_CLAVE"])
            .order_by(Municipio.nombre)
            .all()
        ]


class AutoridadEditForm(FlaskForm):
    """Formulario para editar Autoridad"""

    clave = StringField("Clave (única de hasta 16 caracteres)", validators=[DataRequired(), Regexp(CLAVE_REGEXP)])
    distrito = SelectField("Distrito", coerce=int, validators=[DataRequired()])
    materia = SelectField("Materia", coerce=int, validators=[DataRequired()])
    municipio = SelectField("Municipio", coerce=int, validators=[DataRequired()])
    datawarehouse_id = IntegerField("DataWareHouse ID", validators=[Optional()])
    datawarehouse_id_saji = IntegerField("DataWareHouse ID (SAJI 2025)", validators=[Optional()])
    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    descripcion_corta = StringField("Descripción corta (máximo 64 caracteres)", validators=[DataRequired(), Length(max=64)])
    es_archivo_solicitante = BooleanField("Es Archivo Solicitante", validators=[Optional()])
    es_cemasc = BooleanField("Es CEMASC", validators=[Optional()])
    es_defensoria = BooleanField("Es Defensoría", validators=[Optional()])
    es_extinto = BooleanField("Es Extinto", validators=[Optional()])
    es_jurisdiccional = BooleanField("Es Jurisdiccional", validators=[Optional()])
    es_notaria = BooleanField("Es Notaría", validators=[Optional()])
    es_organo_especializado = BooleanField("Es Órgano Especializado", validators=[Optional()])
    es_revisor_escrituras = BooleanField("Es revisor de escrituras", validators=[Optional()])
    audiencia_categoria = SelectField(
        "Categoría de Audiencias", choices=Autoridad.AUDIENCIAS_CATEGORIAS.items(), validators=[DataRequired()]
    )
    organo_jurisdiccional = SelectField(
        "Órgano Jurisdiccional", choices=Autoridad.ORGANOS_JURISDICCIONALES.items(), validators=[DataRequired()]
    )
    sede = SelectField("Sede (distrito geográfico para AJG)", choices=Autoridad.SEDES.items(), validators=[DataRequired()])
    directorio_edictos = StringField("Directorio para edictos")  # Read only
    directorio_glosas = StringField("Directorio para glosas")  # Read only
    directorio_listas_de_acuerdos = StringField("Directorio para listas de acuerdos")  # Read only
    directorio_sentencias = StringField("Directorio para sentencias")  # Read only
    limite_dias_listas_de_acuerdos = IntegerField("Límite días para listas de acuerdos", validators=[NumberRange(0, 365)])
    pagina_cabecera_url = StringField("URL imagen página cabecera")
    pagina_pie_url = StringField("URL imagen página pie")
    tabla_renglon_color = ColorField("Color renglon tabla")
    tablero_icono = StringField("Icono tablero (si se deja vacío, no aparece en Nuevo Oficio)")
    destinatarios_emails = StringField("Destinatarios emails (separados por comas)", validators=[Optional(), Length(max=1024)])
    con_copias_emails = StringField("Con Copias emails (separados por comas)", validators=[Optional(), Length(max=1024)])
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones en distrito, materia y municipio"""
        super().__init__(*args, **kwargs)
        self.distrito.choices = [
            (d.id, d.nombre_corto) for d in Distrito.query.filter_by(estatus="A").order_by(Distrito.nombre_corto).all()
        ]
        self.materia.choices = [(m.id, m.nombre) for m in Materia.query.filter_by(estatus="A").order_by(Materia.nombre).all()]
        self.municipio.choices = [
            (m.id, m.nombre)
            for m in Municipio.query.join(Estado)
            .filter(Estado.clave == current_app.config["ESTADO_CLAVE"])
            .order_by(Municipio.nombre)
            .all()
        ]
