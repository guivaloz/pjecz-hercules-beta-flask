"""
Archivos Documentos Tipos, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length


class ArcDocumentoTipoForm(FlaskForm):
    """Formulario ArcDocumentoTipo"""

    nombre = StringField("Nombre (único)", validators=[DataRequired(), Length(max=32)])
    guardar = SubmitField("Guardar")
