"""
Domicilios, formularios
"""

from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

from ..distritos.models import Distrito


class DomicilioForm(FlaskForm):
    """Formulario Domicilio"""

    distrito = SelectField("Distrito", coerce=int, validators=[DataRequired()])
    edificio = StringField("Edificio", validators=[DataRequired(), Length(max=64)])
    estado = StringField("Estado", validators=[DataRequired(), Length(max=64)])
    municipio = StringField("Municipio", validators=[DataRequired(), Length(max=64)])
    calle = StringField("Calle", validators=[DataRequired(), Length(max=256)])
    num_ext = StringField("Núm. Exterior", validators=[Optional()])
    num_int = StringField("Núm. Interior", validators=[Optional()])
    colonia = StringField("Colonia", validators=[Optional(), Length(max=256)])
    cp = IntegerField("CP", validators=[DataRequired()])
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones en distrito"""
        super().__init__(*args, **kwargs)
        self.distrito.choices = [
            (d.id, d.nombre_corto) for d in Distrito.query.filter_by(estatus="A").order_by(Distrito.nombre_corto).all()
        ]
