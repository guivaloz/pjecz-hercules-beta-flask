"""
Funcionarios, formularios
"""

from flask_wtf import FlaskForm
from wtforms import BooleanField, DateField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional, Regexp

from pjecz_hercules_beta_flask.blueprints.centros_trabajos.models import CentroTrabajo
from pjecz_hercules_beta_flask.lib.safe_string import CURP_REGEXP


class FuncionarioForm(FlaskForm):
    """Formulario Funcionario"""

    nombres = StringField("Nombres", validators=[DataRequired(), Length(max=256)])
    apellido_paterno = StringField("Apellido paterno", validators=[DataRequired(), Length(max=256)])
    apellido_materno = StringField("Apellido materno", validators=[Optional(), Length(max=256)])
    curp = StringField("CURP", validators=[DataRequired(), Regexp(CURP_REGEXP)])
    email = StringField("e-mail", validators=[DataRequired(), Email(), Length(max=256)])
    centro_trabajo = SelectField("Centro de Trabajo", coerce=int, validators=[DataRequired()])
    puesto = StringField("Puesto", validators=[Optional(), Length(max=256)])
    puesto_clave = StringField("Clave del puesto", validators=[Optional(), Length(max=32)])
    ingreso_fecha = DateField("Fecha de ingreso", validators=[DataRequired()])
    telefono = StringField("Teléfono", validators=[Optional(), Length(max=48)])
    extension = StringField("Extensión", validators=[Optional(), Length(max=24)])
    domicilio_oficial = StringField("Domicilio oficial", validators=[Optional(), Length(max=512)])
    fotografia_url = StringField("URL de la fotografía", validators=[Optional(), Length(max=512)])
    en_funciones = BooleanField("En funciones", validators=[Optional()])
    en_sentencias = BooleanField("En sentencias", validators=[Optional()])
    en_soportes = BooleanField("En soportes", validators=[Optional()])
    en_tesis_jurisprudencias = BooleanField("En tesis y jurisprudencias", validators=[Optional()])
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones en centro_trabajo"""
        super().__init__(*args, **kwargs)
        self.centro_trabajo.choices = [
            (c.id, f"{c.clave} - {c.nombre}")
            for c in CentroTrabajo.query.filter_by(estatus="A").order_by(CentroTrabajo.clave).all()
        ]
