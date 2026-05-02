"""
Ofi Documentos Adjuntos, formularios
"""

from flask_wtf import FlaskForm
from wtforms import FileField, StringField, SubmitField
from wtforms.validators import DataRequired, Length


class OfiDocumentoAdjuntoForm(FlaskForm):
    """Formulario OfiDocumentoAdjunto"""

    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    archivo = FileField("Archivo", validators=[DataRequired()])
    guardar = SubmitField("Guardar")
