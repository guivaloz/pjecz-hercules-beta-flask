"""
Ofi Documentos Destinatarios, formularios
"""

from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, SubmitField
from wtforms.validators import Optional


class OfiDocumentoDestinatarioForm(FlaskForm):
    """Formulario OfiDocumentoDestinatarioForm"""

    usuario = SelectField("Usuario", coerce=int, validate_choice=False, validators=[Optional()])
    con_copia = BooleanField("Con Copia", validators=[Optional()])
    guardar = SubmitField("Guardar")
