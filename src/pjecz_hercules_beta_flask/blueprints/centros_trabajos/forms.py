"""
Centros Trabajos, formularios
"""

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, Regexp

from pjecz_hercules_beta_flask.blueprints.distritos.models import Distrito
from pjecz_hercules_beta_flask.blueprints.domicilios.models import Domicilio
from pjecz_hercules_beta_flask.lib.safe_string import CLAVE_REGEXP


class CentroTrabajoForm(FlaskForm):
    """Formulario CentroTrabajo"""

    clave = StringField("Clave (única de hasta 16 caracteres)", validators=[DataRequired(), Regexp(CLAVE_REGEXP)])
    nombre = StringField("Nombre", validators=[DataRequired(), Length(max=256)])
    distrito = SelectField("Distrito", coerce=int, validators=[DataRequired()])
    domicilio = SelectField("Domicilio", coerce=int, validators=[DataRequired()])
    telefono = StringField("Teléfono", validators=[Optional(), Length(max=48)])
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones en distrito y domicilio"""
        super().__init__(*args, **kwargs)
        self.distrito.choices = [
            (d.id, d.nombre_corto) for d in Distrito.query.filter_by(estatus="A").order_by(Distrito.nombre_corto).all()
        ]
        self.domicilio.choices = [
            (d.id, d.edificio) for d in Domicilio.query.filter_by(estatus="A").order_by(Domicilio.edificio).all()
        ]
