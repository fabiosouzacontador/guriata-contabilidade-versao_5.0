# 🚀 Guia de Monetização - Guriatã

## ✅ O que foi implementado

### 1. Segurança
- [x] Removida senha hardcoded do banco de dados
- [x] Credenciais agora via variável de ambiente `DATABASE_URL`
- [x] Arquivo `.env.example` criado como template
- [x] `.gitignore` configurado para não expor `.env`

### 2. Modelos de Dados para Assinaturas
- [x] Tabela `Plano` - define os planos disponíveis
- [x] Tabela `Assinatura` - registra assinaturas dos usuários
- [x] Campos no `Usuario` para controle de assinatura

### 3. Planos Criados
| Plano | Preço | Usuários | Turmas |
|-------|-------|----------|--------|
| Gratuito | R$ 0 | 1 | 1 |
| Professor | R$ 49,90/mês | 50 | 5 |
| Escola | R$ 299,90/mês | 500 | 50 |
| Enterprise | R$ 999,90/mês | Ilimitado | Ilimitado |

### 4. Landing Page com Pricing
- [x] Seção de preços moderna e responsiva
- [x] Destaque para plano "Professor" (mais popular)
- [x] Calls-to-action claros

### 5. Integração Stripe (pronta para configurar)
- [x] Módulo `src/pagamentos.py` com funções:
  - `criar_customer_stripe()`
  - `criar_checkout_session()`
  - `cancelar_assinatura_stripe()`
  - `processar_assinatura_pago()`
  - `obter_status_assinatura()`

---

## 📋 Próximos Passos

### Passo 1: Configurar Variáveis de Ambiente
```bash
# Copie o template
cp .env.example .env

# Edite com suas credenciais reais
nano .env
```

**Importante:** Substitua a DATABASE_URL pela sua conexão real do Neon/PostgreSQL.

### Passo 2: Configurar Stripe
1. Crie conta em https://stripe.com
2. Obtenha as chaves API no Dashboard
3. Preencha no `.env`:
   ```
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_PUBLISHABLE_KEY=pk_test_...
   STRIPE_WEBHOOK_SECRET=whsec_...
   ```

### Passo 3: Criar Produtos no Stripe
No Dashboard do Stripe:
1. Vá em Products > Add Product
2. Crie 3 produtos: "Guriatã - Plano Professor", "Guriatã - Plano Escola", "Guriatã - Plano Enterprise"
3. Configure preços recorrentes mensais em BRL
4. Copie os `price_id` e atualize no código (função `carregar_dados_padrao`)

### Passo 4: Implementar Webhook
Crie endpoint `/webhook` no app.py para receber eventos do Stripe:
```python
@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    # Processar checkout.session.completed
    # Ativar assinatura do usuário
```

### Passo 5: Adicionar UI de Upgrade no App
Na sidebar ou perfil do usuário:
- Mostrar plano atual
- Botão "Fazer Upgrade"
- Histórico de pagamentos

---

## 💡 Estratégias de Monetização Recomendadas

### 1. Freemium (Já implementado)
- Plano gratuito funcional atrai usuários
- Limitações incentivam upgrade

### 2. Teste Grátis
- Ofereça 7-14 dias grátis no plano Professor
- Requer cartão de crédito (reduz churn)

### 3. Desconto Anual
- Cobrança anual com 2 meses grátis
- Melhora cash flow e retenção

### 4. Programa de Indicação
- "Indique um colega e ganhe 1 mês grátis"
- Crescimento orgânico

### 5. Parcerias com Instituições
- Descontos para universidades
- Licenças site-wide

---

## 🔧 Manutenção

### Verificar Assinaturas Expiradas
Execute diariamente (cron job):
```python
# Verificar data_assinatura_fim < hoje
# Marcar assinatura_ativa = False
# Notificar usuário por e-mail
```

### Métricas para Acompanhar
- MRR (Monthly Recurring Revenue)
- Churn rate
- LTV (Lifetime Value)
- CAC (Customer Acquisition Cost)

---

## 📞 Suporte Técnico

Para dúvidas sobre implementação:
1. Verifique logs de erro
2. Teste em modo sandbox primeiro
3. Use Stripe CLI para testar webhooks localmente

**Documentação oficial:**
- [Stripe Docs](https://stripe.com/docs)
- [SQLModel](https://sqlmodel.tiangolo.com/)
- [Streamlit](https://docs.streamlit.io/)
