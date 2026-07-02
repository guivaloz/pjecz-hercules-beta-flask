"""
Abogados, formularios
"""

from flask_wtf import FlaskForm
from wtforms import DateField, StringField, SubmitField
from wtforms.validators import DataRequired, Length


class AbogadoForm(FlaskForm):
    """Formulario Abogado"""

    fecha = DateField("Fecha", validators=[DataRequired()])
    numero = StringField("Número", validators=[DataRequired(), Length(max=24)])
    libro = StringField("Libro", validators=[DataRequired(), Length(max=24)])
    nombre = StringField("Nombre", validators=[DataRequired(), Length(max=256)])
    guardar = SubmitField("Guardar")
