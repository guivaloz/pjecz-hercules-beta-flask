"""
REDAMS, formularios
"""

from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, Regexp

from pjecz_hercules_beta_flask.lib.safe_string import EXPEDIENTE_REGEXP


class RedamForm(FlaskForm):
    """Formulario Redam"""

    distrito = SelectField("Distrito", choices=None, validators=[DataRequired()], validate_choice=False)
    autoridad = SelectField("Autoridad", choices=None, validators=[DataRequired()], validate_choice=False)
    nombre = StringField("Nombre del deudor alimentario", validators=[DataRequired(), Length(max=256)])
    expediente = StringField("Expediente", validators=[DataRequired(), Length(max=16), Regexp(EXPEDIENTE_REGEXP)])
    fecha = DateField("Fecha de emisión de orden de inclusión", validators=[DataRequired()])
    observaciones = TextAreaField("Observaciones", validators=[Optional(), Length(max=1024)])
    guardar = SubmitField("Guardar")
