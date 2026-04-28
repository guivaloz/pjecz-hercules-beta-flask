"""
Ofi Documentos, formularios
"""

from flask_wtf import FlaskForm
from wtforms import DateField, HiddenField, StringField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, Regexp

FOLIO_REGEXP = r"[\w-]+\d+\/\d{4}"  # CLAVE-NUM/AÑO


class OfiDocumentoForm(FlaskForm):
    """Formulario OfiDocumento"""

    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    folio = StringField("Folio (CLAVE-NUM/AÑO)", validators=[Optional(), Regexp(FOLIO_REGEXP)])
    vencimiento_fecha = DateField("Fecha de vencimiento", validators=[Optional()])
    contenido_md = TextAreaField("Contenido MD", validators=[Optional()], render_kw={"rows": 10})
    contenido_html = TextAreaField("Contenido HTML", validators=[Optional()], render_kw={"rows": 10})
    contenido_sfdt = TextAreaField("Contenido SFDT", validators=[Optional()], render_kw={"rows": 10})
    cadena_oficio_id = HiddenField("Cadena de Oficio", validators=[Optional()])
    continuar = HiddenField("Continuar", default="0")  # 1 = seguir editando, 0 = salir
    # No tiene guardar = SubmitField("Guardar")
