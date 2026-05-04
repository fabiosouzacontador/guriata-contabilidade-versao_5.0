# 📋 Guia de Migração - Refatoração de Segurança e Arquitetura

## Resumo das Mudanças

Este documento descreve as alterações realizadas para corrigir problemas críticos de segurança e melhorar a arquitetura do projeto Guriatã.

---

## 🔴 Problemas Corrigidos

### 1. Credenciais Expostas (CRÍTICO)
**Antes:**
```python
# app.py - Linha 380
DATABASE_URL = "postgresql://neondb_owner:npg_1ZQMkSRiK6pc@..."
```

**Depois:**
```python
# src/config.py
def get_database_url() -> str:
    # Prioridade: st.secrets > variável de ambiente > SQLite local
    try:
        return st.secrets["database"]["DATABASE_URL"]
    except (FileNotFoundError, KeyError):
        return os.getenv("DATABASE_URL", "sqlite:///data/contabilidade.db")
```

**Ação Necessária:** 
- ✅ **IMEDIATO**: Rotacionar a senha do banco de dados Neon
- Criar `.streamlit/secrets.toml` com suas credenciais reais
- NUNCA commitar `secrets.toml` no Git

### 2. Senhas em Texto Plano
**Antes:**
```python
admin = Usuario(username="admin", senha="123", ...)
```

**Depois:**
```python
from src.utils import hash_senha

senha_padrao = get_default_password()
admin = Usuario(
    username="admin",
    senha=hash_senha(senha_padrao),
    ...
)
```

### 3. Modelos Duplicados
**Antes:** Dois conjuntos de modelos (app.py e src/models/)

**Depois:** Modelos centralizados em `src/models/`

---

## 📁 Novos Arquivos Criados

| Arquivo | Propósito |
|---------|-----------|
| `.streamlit/secrets.toml` | Armazena credenciais sensíveis (NÃO COMMITAR) |
| `.env.example` | Template de variáveis de ambiente |
| `src/config.py` | Configuração centralizada do banco de dados |
| `src/utils.py` | Funções utilitárias (formatação, hash) |
| `src/__init__.py` | Pacote Python com exports |
| `src/services/usuario_service.py` | Service de usuário com regras de negócio |
| `README.md` | Documentação completa do projeto |
| `MIGRACAO.md` | Este arquivo |

---

## 🔄 Próximos Passos (Refatoração do app.py)

O `app.py` ainda contém código duplicado que deve ser migrado:

### Passo 1: Remover definições duplicadas de modelos
No `app.py`, remover as classes:
- `Escola`
- `Turma`
- `Usuario`
- `Aula`
- `ContaContabil`
- `Lancamento`

E importar de `src.models`:
```python
from src.models.usuario_model import Usuario
from src.models.account_model import ContaContabil
from src.models.lancamento_model import Lancamento
```

### Passo 2: Substituir conexão direta pelo config
No `app.py`, substituir:
```python
# REMOVER:
DATABASE_URL = "postgresql://..."
engine = create_engine(DATABASE_URL, ...)

# USAR:
from src.config import engine, get_session
```

### Passo 3: Usar services para lógica de negócio
```python
# EM VEZ DE:
usuario = session.exec(select(Usuario).where(...)).first()

# USAR:
from src.services.usuario_service import UsuarioService
with Session(engine) as session:
    service = UsuarioService(session)
    usuario = service.buscar_por_username(username)
```

---

## ✅ Checklist de Validação

- [ ] Criar `.streamlit/secrets.toml` com credenciais reais
- [ ] Atualizar senha do banco de dados no Neon (segurança)
- [ ] Testar conexão local com SQLite
- [ ] Testar deploy no Streamlit Cloud
- [ ] Verificar se usuários padrão são criados com senha hasheada
- [ ] Validar login com usuários admin/professor/aluno
- [ ] Testar criação de lançamentos
- [ ] Testar geração de relatórios (Razonete, Balancete, DRE, BP)

---

## 🚨 Ação de Segurança IMEDIATA

A senha do banco de dados foi exposta publicamente. Siga estes passos:

1. **Acesse o painel do Neon** (https://console.neon.tech)
2. **Vá até o projeto** correspondente
3. **Gere uma nova senha** para o usuário `neondb_owner`
4. **Atualize o secrets.toml** com a nova string de conexão
5. **Teste a conexão** localmente
6. **Revogue o acesso antigo** se possível

Nova string de conexão (exemplo):
```toml
[database]
DATABASE_URL = "postgresql://neondb_owner:NOVA_SENA@ep-damp-recipe-an7lkxz4-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require"
```

---

## 📞 Suporte

Em caso de dúvidas durante a migração:

1. Consulte o `README.md` para instruções de instalação
2. Verifique os logs de erro ao executar `streamlit run app.py`
3. Certifique-se de que todos os imports estão corretos

---

**Data da migração:** Maio 2024  
**Responsável:** Refatoração automática baseada em melhores práticas
