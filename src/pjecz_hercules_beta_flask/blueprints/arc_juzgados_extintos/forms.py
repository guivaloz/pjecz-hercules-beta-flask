"""
Archivos Juzgados Extintos, formularios
"""

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp

from pjecz_hercules_beta_flask.blueprints.distritos.models import Distrito
from pjecz_hercules_beta_flask.lib.safe_string import CLAVE_REGEXP


class ArcJuzgadoExtintoForm(FlaskForm):
    """Formulario ArcJuzgadoExtinto"""

    clave = StringField("Clave (única de hasta 16 caracteres)", validators=[DataRequired(), Regexp(CLAVE_REGEXP)])
    descripcion_corta = StringField("Descripción corta", validators=[DataRequired(), Length(max=64)])
    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    distrito = SelectField("Distrito", coerce=int, validators=[DataRequired()])
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones en distrito"""
        super().__init__(*args, **kwargs)
        self.distrito.choices = [
            (d.id, d.nombre_corto) for d in Distrito.query.filter_by(estatus="A").order_by(Distrito.nombre_corto).all()
        ]
