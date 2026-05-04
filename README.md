# 🦅 Guriatã - Sistema Educacional de Contabilidade

Sistema interativo para ensino de contabilidade através de lançamentos, razonetes, balancetes, DRE e Balanço Patrimonial.

## 🚀 Funcionalidades

- **Lançamentos Contábeis**: Registre débitos e créditos com histórico
- **Razonetes**: Visualize movimentações por conta no formato T
- **Balancete**: Consulte saldos de todas as contas
- **DRE (Demonstração do Resultado)**: Apure o resultado do exercício
- **Balanço Patrimonial**: Gere o BP completo (Ativo e Passivo)
- **Múltiplos Usuários**: Perfis de admin, professor e aluno
- **Gamificação**: Sistema de XP para engajamento

## 🛠️ Instalação

### 1. Clone o repositório

```bash
git clone <url-do-repositorio>
cd guriata
```

### 2. Crie um ambiente virtual (recomendado)

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure as credenciais do banco de dados

#### Opção A: Streamlit Cloud (Recomendado)

No dashboard do Streamlit Cloud, adicione o segredo `DATABASE_URL`:

```toml
[database]
DATABASE_URL = "postgresql://usuario:senha@host:porta/banco?sslmode=require"
```

#### Opção B: Local (.streamlit/secrets.toml)

Crie o arquivo `.streamlit/secrets.toml`:

```toml
[database]
DATABASE_URL = "postgresql://usuario:senha@host:porta/banco?sslmode=require"

[security]
SENHA_PADRAO = "123"
```

#### Opção C: Variável de Ambiente

```bash
export DATABASE_URL="postgresql://usuario:senha@host:porta/banco?sslmode=require"
```

### 5. Execute a aplicação

```bash
streamlit run app.py
```

Acesse `http://localhost:8501` no seu navegador.

## 👤 Usuários Padrão

| Username   | Senha | Perfil    |
|------------|-------|-----------|
| admin      | 123   | Admin     |
| professor  | 123   | Professor |
| aluno      | 123   | Aluno     |

**⚠️ Importante**: Altere as senhas padrão em produção!

## 📁 Estrutura do Projeto

```
guriata/
├── app.py                      # Aplicação principal (UI Streamlit)
├── requirements.txt            # Dependências Python
├── README.md                   # Este arquivo
├── .env.example                # Exemplo de variáveis de ambiente
├── .gitignore                  # Arquivos ignorados pelo Git
├── .streamlit/
│   └── secrets.toml           # Credenciais (NÃO COMMITAR)
├── assets/
│   └── logo.png               # Logo da aplicação
└── src/
    ├── __init__.py            # Pacote principal
    ├── config.py              # Configurações e conexão DB
    ├── database.py            # Funções de acesso a dados
    ├── utils.py               # Utilitários (formatação, hash)
    ├── models/
    │   ├── account_model.py   # Modelo ContaContabil
    │   ├── lancamento_model.py # Modelo Lancamento
    │   └── usuario_model.py   # Modelo Usuario
    ├── controllers/
    │   ├── razonete_controller.py
    │   ├── balancete_controller.py
    │   ├── dre_controller.py
    │   └── balanco_controller.py
    └── services/
        └── usuario_service.py # Regras de negócio de usuário
```

## 🔒 Segurança

- Senhas são hasheadas com bcrypt (12 rounds)
- Credenciais NUNCA devem ser commitadas no Git
- Use `.streamlit/secrets.toml` ou variáveis de ambiente
- O arquivo `secrets.toml` está no `.gitignore`

## 🏗️ Arquitetura

O projeto segue uma arquitetura MVC simplificada:

- **Models**: Definição das tabelas (SQLModel)
- **Controllers**: Lógica de consulta e relatórios
- **Services**: Regras de negócio (autenticação, CRUD)
- **Views**: Interface Streamlit (app.py)

## 🧪 Desenvolvimento

### Rodar testes (futuro)

```bash
pytest tests/
```

### Formatar código

```bash
black src/ app.py
flake8 src/ app.py
```

### Verificar tipos

```bash
mypy src/ app.py
```

## ☁️ Deploy no Streamlit Cloud

1. Conecte seu repositório GitHub ao Streamlit Cloud
2. Configure as variáveis de ambiente no dashboard
3. Defina o comando: `streamlit run app.py`
4. Deploy automático a cada push na main

## 📝 Licença

Este projeto é destinado fins educacionais.

## 🤝 Contribuição

Contribuições são bem-vindas! Siga os passos:

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

---

**Desenvolvido com ❤️ para educação contábil**
