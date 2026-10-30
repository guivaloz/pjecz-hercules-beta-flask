"""
DGT Plataformas, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length


class DgtPlataformaForm(FlaskForm):
    """Formulario DgtPlataforma"""

    clave = StringField("Clave", validators=[DataRequired(), Length(max=64)])
    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    api_key = StringField("API key", validators=[DataRequired(), Length(max=128)])
    guardar = SubmitField("Guardar")
