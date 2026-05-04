"""
Módulo de configuração centralizada
Gerencia conexões com banco de dados e configurações da aplicação
"""

import os
from pathlib import Path
from sqlmodel import create_engine, Session
import streamlit as st


def get_database_url() -> str:
    """
    Obtém a URL do banco de dados de forma segura.
    Prioridade:
    1. st.secrets (Streamlit Cloud)
    2. Variável de ambiente DATABASE_URL
    3. SQLite local para desenvolvimento
    """
    # Tenta pegar do secrets.toml (Streamlit Cloud)
    try:
        db_url = st.secrets["database"]["DATABASE_URL"]
        if db_url and db_url != "postgresql://usuario:senha@host:porta/nome_do_banco?sslmode=require":
            # Ajusta protocolo se necessário
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql://", 1)
            return db_url
    except (FileNotFoundError, KeyError, TypeError):
        pass
    
    # Tenta pegar de variável de ambiente
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        return db_url
    
    # Fallback para SQLite local (desenvolvimento)
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    return f"sqlite:///{data_dir}/contabilidade.db"


def create_db_engine():
    """
    Cria o engine do banco de dados com configurações apropriadas
    """
    db_url = get_database_url()
    
    # Configurações específicas para SQLite
    if "sqlite" in db_url:
        connect_args = {"check_same_thread": False}
        pool_config = {}
    else:
        connect_args = {}
        pool_config = {
            "pool_pre_ping": True,
            "pool_size": 5,
            "max_overflow": 10
        }
    
    return create_engine(db_url, echo=False, connect_args=connect_args, **pool_config)


# Engine global (singleton)
engine = create_db_engine()


def get_session() -> Session:
    """
    Factory para criar sessões do banco de dados
    """
    return Session(engine)


def get_default_password() -> str:
    """
    Retorna a senha padrão para usuários de exemplo
    """
    try:
        return st.secrets["security"]["SENHA_PADRAO"]
    except (FileNotFoundError, KeyError, TypeError):
        pass
    
    return os.getenv("SENHA_PADRAO", "123")
