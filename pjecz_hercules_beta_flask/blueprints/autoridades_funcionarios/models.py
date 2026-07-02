"""
Autoridades Funcionarios, modelos
"""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pjecz_hercules_beta_flask.config.extensions import database
from pjecz_hercules_beta_flask.lib.universal_mixin import UniversalMixin


class AutoridadFuncionario(database.Model, UniversalMixin):
    """AutoridadFuncionario"""

    # Nombre de la tabla
    __tablename__ = "autoridades_funcionarios"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    autoridad_id: Mapped[int] = mapped_column(ForeignKey("autoridades.id"))
    autoridad: Mapped["Autoridad"] = relationship(back_populates="autoridades_funcionarios")
    funcionario_id: Mapped[int] = mapped_column(ForeignKey("funcionarios.id"))
    funcionario: Mapped["Funcionario"] = relationship(back_populates="autoridades_funcionarios")

    # Columnas
    descripcion: Mapped[str] = mapped_column(String(256))

    def __repr__(self):
        """Representación"""
        return f"<AutoridadFuncionario {self.descripcion}>"
