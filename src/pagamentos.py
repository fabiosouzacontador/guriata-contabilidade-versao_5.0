"""
Módulo de integração com Stripe para processamento de pagamentos
"""
import os
import stripe
from datetime import date, timedelta
from typing import Optional, Dict, Any

# Configurar chave da API do Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

def criar_customer_stripe(email: str, nome: str, usuario_id: int) -> Optional[str]:
    """
    Cria um customer no Stripe para o usuário
    Retorna o customer_id ou None em caso de erro
    """
    try:
        if not stripe.api_key:
            print("⚠️ Stripe não configurado (modo sandbox)")
            return f"test_customer_{usuario_id}"
        
        customer = stripe.Customer.create(
            email=email,
            name=nome,
            metadata={"usuario_id": str(usuario_id)}
        )
        return customer.id
    except Exception as e:
        print(f"Erro ao criar customer Stripe: {e}")
        return None

def criar_checkout_session(plano_id: int, plano_nome: str, preco: float, 
                           customer_id: str, success_url: str, cancel_url: str) -> Optional[str]:
    """
    Cria uma sessão de checkout do Stripe
    Retorna a URL de checkout ou None em caso de erro
    """
    try:
        if not stripe.api_key:
            print("⚠️ Stripe não configurado (modo sandbox)")
            # Em modo sandbox, retorna URL fictícia
            return f"/checkout/success?session_id=test_session_{plano_id}"
        
        # Criar preço dinamicamente se não existir
        price = stripe.Price.create(
            unit_amount=int(preco * 100),  # Stripe usa centavos
            currency="brl",
            recurring={"interval": "month"},
            product_data={"name": f"Guriatã - Plano {plano_nome}"}
        )
        
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card", "boleto", "pix"],
            line_items=[{"price": price.id, "quantity": 1}],
            mode="subscription",
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            metadata={"plano_id": str(plano_id)}
        )
        return session.url
    except Exception as e:
        print(f"Erro ao criar checkout session: {e}")
        return None

def cancelar_assinatura_stripe(subscription_id: str) -> bool:
    """
    Cancela uma assinatura no Stripe
    """
    try:
        if not stripe.api_key:
            print("⚠️ Stripe não configurado (modo sandbox)")
            return True
        
        stripe.Subscription.delete(subscription_id)
        return True
    except Exception as e:
        print(f"Erro ao cancelar assinatura: {e}")
        return False

def verificar_pagamento_webhook(payload: bytes, sig_header: str, webhook_secret: str) -> Optional[Dict[str, Any]]:
    """
    Verifica e processa webhook do Stripe
    Retorna o evento se válido, None caso contrário
    """
    try:
        if not stripe.api_key:
            # Em modo sandbox, simula evento
            return {"type": "checkout.session.completed", "data": {"object": {}}}
        
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
        return event
    except Exception as e:
        print(f"Erro ao verificar webhook: {e}")
        return None

def processar_assinatura_pago(session_id: str, usuario_id: int, plano_id: int, 
                               data_inicio: date, session=None) -> bool:
    """
    Processa uma assinatura após pagamento confirmado
    Atualiza os dados do usuário no banco
    """
    from sqlmodel import select
    
    try:
        # Buscar modelos
        from app import Usuario, Assinatura, Plano
        
        # Atualizar usuário
        usuario = session.get(Usuario, usuario_id)
        if not usuario:
            print(f"Usuário {usuario_id} não encontrado")
            return False
        
        plano = session.get(Plano, plano_id)
        if not plano:
            print(f"Plano {plano_id} não encontrado")
            return False
        
        # Calcular data de fim (30 dias)
        data_fim = data_inicio + timedelta(days=30)
        
        # Atualizar usuário com plano
        usuario.plano_id = plano_id
        usuario.assinatura_ativa = True
        usuario.data_assinatura_inicio = data_inicio
        usuario.data_assinatura_fim = data_fim
        
        # Criar registro de assinatura
        assinatura = Assinatura(
            usuario_id=usuario_id,
            plano_id=plano_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            status="ativa",
            stripe_subscription_id=session_id if session_id.startswith("sub_") else None,
            ultimo_pagamento=data_inicio,
            proximo_cobranca=data_fim
        )
        
        session.add(usuario)
        session.add(assinatura)
        session.commit()
        
        print(f"✅ Assinatura ativada para usuário {usuario_id} - Plano {plano.nome}")
        return True
        
    except Exception as e:
        print(f"Erro ao processar assinatura: {e}")
        if session:
            session.rollback()
        return False

def obter_status_assinatura(usuario_id: int, session=None) -> Dict[str, Any]:
    """
    Obtém o status atual da assinatura do usuário
    """
    from sqlmodel import select
    from app import Usuario, Assinatura, Plano
    
    resultado = {
        "tem_assinatura": False,
        "plano": "Gratuito",
        "status": "inativo",
        "data_fim": None,
        "pode_upgrade": True
    }
    
    try:
        usuario = session.get(Usuario, usuario_id)
        if not usuario:
            return resultado
        
        if usuario.plano_id:
            plano = session.get(Plano, usuario.plano_id)
            if plano:
                resultado["tem_assinatura"] = usuario.assinatura_ativa
                resultado["plano"] = plano.nome
                resultado["preco"] = plano.preco_mensal
                resultado["max_usuarios"] = plano.max_usuarios
                resultado["max_turmas"] = plano.max_turmas
                
                # Verificar se está ativa e dentro do período
                if usuario.assinatura_ativa and usuario.data_assinatura_fim:
                    if usuario.data_assinatura_fim >= date.today():
                        resultado["status"] = "ativa"
                    else:
                        resultado["status"] = "expirada"
                        resultado["pode_upgrade"] = True
                else:
                    resultado["status"] = "inativa"
                
                resultado["data_fim"] = usuario.data_assinatura_fim
        
        return resultado
        
    except Exception as e:
        print(f"Erro ao obter status: {e}")
        return resultado
