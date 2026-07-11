"""
Funcionarios-Oficinas, formularios
"""

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired

from pjecz_hercules_beta_flask.blueprints.domicilios.models import Domicilio
from pjecz_hercules_beta_flask.blueprints.oficinas.models import Oficina


class FuncionarioOficinaForm(FlaskForm):
    """Formulario FuncionarioOficina"""

    funcionario = StringField("Funcionario")  # Read only
    oficina = SelectField("Oficina", coerce=int)  # Select2
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones en distrito"""
        super().__init__(*args, **kwargs)
        self.oficina.choices = [
            (o.id, o.clave + " - " + o.descripcion_corta)
            for o in Oficina.query.filter_by(estatus="A").order_by(Oficina.clave).all()
        ]


class FuncionarioOficinaWithDomicilioForm(FlaskForm):
    """Formulario para relacionar oficinas al funcionario a partir de una direccion"""

    funcionario_nombre = StringField("Nombre")  # Read only
    funcionario_puesto = StringField("Puesto")  # Read only
    funcionario_email = StringField("e-mail")  # Read only
    domicilio = SelectField("Domicilio", coerce=int, validators=[DataRequired()])
    asignar = SubmitField("Asignar")
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones en domicilio"""
        super().__init__(*args, **kwargs)
        self.domicilio.choices = [
            (d.id, d.edificio) for d in Domicilio.query.filter_by(estatus="A").order_by(Domicilio.edificio).all()
        ]
