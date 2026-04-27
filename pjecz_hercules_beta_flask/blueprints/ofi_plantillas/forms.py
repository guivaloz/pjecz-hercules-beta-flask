"""
Ofi Plantillas, formularios
"""

from flask_wtf import FlaskForm
from wtforms import BooleanField, HiddenField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class OfiPlantillaForm(FlaskForm):
    """Formulario OfiPlantilla"""

    descripcion = StringField("Descripción", validators=[DataRequired()])
    propietario = SelectField(
        "Propietario (lo relaciona a la autoridad)", coerce=int, validate_choice=False, validators=[DataRequired()]
    )
    destinatarios_emails = StringField("Destinatarios (e-mails separados por comas)", validators=[Optional(), Length(max=1024)])
    con_copias_emails = StringField("Con Copias (e-mails separados por comas)", validators=[Optional(), Length(max=1024)])
    remitente_email = StringField("Remitente", validators=[Optional(), Length(max=256)])
    contenido_md = TextAreaField("Contenido MD", validators=[Optional()], render_kw={"rows": 10})
    contenido_html = TextAreaField("Contenido HTML", validators=[Optional()], render_kw={"rows": 10})
    contenido_sfdt = TextAreaField("Contenido SFDT", validators=[Optional()], render_kw={"rows": 10})
    esta_archivado = BooleanField("Está Archivada", validators=[Optional()])
    esta_compartida = BooleanField("Está Compartida", validators=[Optional()])
    continuar = HiddenField("Continuar", default="0")  # 1 = seguir editando, 0 = salir
    # No tiene guardar = SubmitField("Guardar")
