# 🚀 Guia de Inicialização do Guriatã

## Como Rodar o Sistema com Landing Page

### 1. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 2. Configurar Variáveis de Ambiente (Opcional)
Copie o arquivo de exemplo:
```bash
cp .env.example .env
```

Edite o `.env` com suas credenciais:
```
DATABASE_URL=sqlite:///guriata.db
SHOW_LANDING=true
```

### 3. Executar o Sistema

**Com Landing Page (padrão):**
```bash
streamlit run app.py
```

O sistema abrirá automaticamente no navegador mostrando:
- ✅ Página de apresentação com informações do sistema
- ✅ Público-alvo (Universidades, Escolas, Professores, Alunos)
- ✅ Funcionalidades completas
- ✅ Planos e preços
- ✅ Botão "ACESSAR SISTEMA GRATUITAMENTE"

**Apenas Sistema (sem landing page):**
```bash
SHOW_LANDING=false streamlit run app.py
```

Ou edite o `.env`:
```
SHOW_LANDING=false
```

## 🔐 Acessos Padrão

| Perfil | Usuário | Senha |
|--------|---------|-------|
| Admin | admin | admin123 |
| Professor | professor | prof123 |
| Aluno | aluno | aluno123 |

## 📱 Navegação

1. **Landing Page** → Clique em "ACESSAR SISTEMA GRATUITAMENTE"
2. **Login** → Digite usuário e senha
3. **Sistema** → Acesse todas as funcionalidades contábeis

## 💰 Planos Disponíveis

- **Gratuito**: R$ 0/mês (1 usuário, 1 turma)
- **Professor**: R$ 49,90/mês (50 alunos, 5 turmas)
- **Escola**: R$ 299,90/mês (500 alunos, 50 turmas)
- **Enterprise**: R$ 999,90/mês (ilimitado)

## 🛠️ Troubleshooting

**Erro de banco de dados:**
```bash
rm guriata.db
streamlit run app.py
```

**Porta já em uso:**
```bash
streamlit run app.py --server.port 8502
```

## 📞 Suporte

Para dúvidas ou suporte técnico, consulte a documentação em `MONETIZACAO.md`.

---
© 2024 Guriatã - Plataforma de Ensino de Contabilidade
