"""
Pacote Guriatã - Sistema Educacional de Contabilidade
"""

from src.config import engine, get_session, get_default_password
from src.database import (
    create_db_and_tables,
    salvar_lancamento,
    excluir_lancamento_individual,
    limpar_todos_lancamentos,
    limpar_lancamentos_por_usuario,
    deletar_usuario_por_id,
    alterar_senha_usuario,
    populate_initial_data
)
from src.utils import (
    formatar_data_br,
    formatar_moeda,
    hash_senha,
    verificar_senha,
    migrar_senha_plana_para_hash
)

__all__ = [
    'engine',
    'get_session',
    'get_default_password',
    'create_db_and_tables',
    'salvar_lancamento',
    'excluir_lancamento_individual',
    'limpar_todos_lancamentos',
    'limpar_lancamentos_por_usuario',
    'deletar_usuario_por_id',
    'alterar_senha_usuario',
    'populate_initial_data',
    'formatar_data_br',
    'formatar_moeda',
    'hash_senha',
    'verificar_senha',
    'migrar_senha_plana_para_hash'
]
