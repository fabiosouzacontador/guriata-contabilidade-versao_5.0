"""
Módulo de modelos de dados
Exporta todos os modelos da aplicação
"""

from src.models.usuario_model import Usuario
from src.models.account_model import ContaContabil as PlanoConta
from src.models.lancamento_model import Lancamento

# Modelos adicionais que precisam ser definidos aqui
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import date


class Escola(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    cidade: str


class Turma(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    ano_letivo: str
    professor_id: int
    escola_id: int


class Aluno(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    turma_id: int


class Aula(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    titulo: str
    descricao: str
    arquivo_blob: Optional[bytes] = None
    nome_arquivo: Optional[str] = None
    professor_id: int
    turma_id: int
    data_postagem: date = Field(default_factory=date.today)


__all__ = [
    'Usuario',
    'PlanoConta', 
    'Lancamento',
    'Escola',
    'Turma',
    'Aluno',
    'Aula'
]
