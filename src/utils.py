"""
Módulo de utilitários e helpers
Funções auxiliares usadas em toda a aplicação
"""

import bcrypt
from datetime import date, datetime
from typing import Optional


def formatar_data_br(data: Optional[date]) -> str:
    """Formata data para o padrão brasileiro DD/MM/YYYY"""
    if data:
        return data.strftime('%d/%m/%Y')
    return ""


def formatar_moeda(valor: float) -> str:
    """Formata valor monetário para o padrão brasileiro R$ X.XXX,XX"""
    return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def hash_senha(senha: str) -> str:
    """Gera hash seguro da senha usando bcrypt"""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(senha.encode('utf-8'), salt).decode('utf-8')


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Verifica se a senha corresponde ao hash armazenado"""
    try:
        return bcrypt.checkpw(senha.encode('utf-8'), senha_hash.encode('utf-8'))
    except Exception:
        return False


def migrar_senha_plana_para_hash(senha_plana_ou_hash: str, forcar_hash: bool = False) -> str:
    """
    Migra senha plana para hash se necessário.
    Detecta se já é hash (começa com $2) ou se é senha plana.
    """
    # Se já parece ser um hash bcrypt, retorna como está
    if not forcar_hash and senha_plana_ou_hash.startswith('$2'):
        return senha_plana_ou_hash
    
    # Caso contrário, gera hash
    return hash_senha(senha_plana_ou_hash)


def calcular_digito_verificador(codigo: str) -> str:
    """Calcula dígito verificador para códigos de conta (opcional)"""
    soma = sum(int(d) * (i + 1) for i, d in enumerate(codigo.replace('.', '').replace('-', '')))
    return str(soma % 10)


def hoje() -> date:
    """Retorna a data atual"""
    return date.today()


def agora() -> datetime:
    """Retorna o timestamp atual"""
    return datetime.now()
