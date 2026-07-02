"""
Estrados, formularios
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired
from wtforms import DateField, FileField, StringField, SubmitField
from wtforms.validators import DataRequired, Length


class EstradoNewForm(FlaskForm):
    """Formulario para nuevo Estrado"""

    distrito = StringField("Distrito")  # Read only
    autoridad = StringField("Autoridad")  # Read only
    fecha = DateField("Fecha", validators=[DataRequired()])
    descripcion = StringField("Descripcion", validators=[DataRequired(), Length(max=256)])
    archivo = FileField("Archivo PDF", validators=[FileRequired()])
    guardar = SubmitField("Guardar")


class EstradoEditForm(FlaskForm):
    """Formulario para editar Estrado"""

    fecha = DateField("Fecha", validators=[DataRequired()])
    descripcion = StringField("Descripcion", validators=[DataRequired(), Length(max=256)])
    guardar = SubmitField("Guardar")
