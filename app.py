import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime
from sqlmodel import SQLModel, Field, select, desc, text, create_engine, Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
import base64
from pathlib import Path
import warnings
import time
import bcrypt
import os
from dotenv import load_dotenv

# ==============================================================================
# 1. CONFIGURAÇÕES & DESIGN
# ==============================================================================
warnings.filterwarnings("ignore")

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Verificar se deve mostrar landing page ou sistema
show_landing = os.environ.get("SHOW_LANDING", "true").lower() == "true"

# Configurar página apenas se não for landing page
if not show_landing or st.query_params.get("page") == "sistema":
    st.set_page_config(
        page_title="Guriatã - Sistema",
        layout="centered",
        page_icon="assets/logo.png",
        initial_sidebar_state="expanded"
    )
else:
    st.set_page_config(
        page_title="Guriatã - Plataforma de Ensino de Contabilidade",
        layout="wide",
        page_icon="🦅",
        initial_sidebar_state="collapsed"
    )

def formatar_data_br(data):
    if data:
        return data.strftime('%d/%m/%Y')
    return ""

def fmt_moeda(v):
    return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def hash_senha(senha: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(senha.encode('utf-8'), salt).decode('utf-8')

def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        return bcrypt.checkpw(senha.encode('utf-8'), senha_hash.encode('utf-8'))
    except:
        return False

st.markdown("""
<style>
    /* Layout geral */
    .block-container { padding-top: 2rem !important; max-width: 1200px !important; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stTextInput>div>div>input { border-radius: 8px; border: 1px solid #e0e0e0; height: 44px; }
    .stSelectbox>div>div { border-radius: 8px; border: 1px solid #e0e0e0; }
    
    /* ========== CORREÇÃO DEFINITIVA DO HISTÓRICO ========== */
    .stCaption, 
    caption, 
    .stMarkdown caption,
    div[data-testid="stCaption"],
    div[data-testid="stMarkdown"] caption,
    .element-container .stCaption,
    .stAlert .stCaption {
        color: #000000 !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        opacity: 1 !important;
        background: transparent !important;
        font-family: 'Segoe UI', 'Aptos', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    
    .stContainer p, 
    .stContainer .stMarkdown,
    .stContainer .stCaption,
    div[data-testid="stContainer"] p,
    div[data-testid="stContainer"] .stMarkdown,
    div[data-testid="stContainer"] .stCaption {
        color: #111111 !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        opacity: 1 !important;
    }
    
    .stContainer .stMarkdown p {
        color: #1a1a1a !important;
        font-size: 12.5px !important;
        font-weight: 500 !important;
        opacity: 1 !important;
    }
    
    [class*="caption"], 
    [class*="Caption"],
    .element-container .stMarkdown:has(caption) {
        color: #000000 !important;
        opacity: 1 !important;
        font-weight: 500 !important;
    }
    
    /* Botões */
    .stButton button {
        padding: 4px 8px !important;
        font-size: 12px !important;
        border-radius: 6px !important;
        height: auto !important;
        min-height: 32px !important;
        width: auto !important;
        min-width: 70px !important;
        max-width: 100px !important;
        white-space: nowrap !important;
        background-color: #dc3545 !important;
        color: white !important;
        border: none !important;
    }
    
    .stButton button:hover {
        background-color: #c82333 !important;
        color: white !important;
    }
    
    .stButton button[kind="primary"] {
        background: linear-gradient(135deg, #004b8d 0%, #0066c0 100%) !important;
    }
    
    .stButton button[kind="primary"]:hover {
        background: linear-gradient(135deg, #003d6e 0%, #0055a3 100%) !important;
    }
    
    /* KPI Cards */
    .kpi-card {
        background: white;
        border-left: 4px solid #004b8d;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    
    /* Razonetes */
    .razonete-container {
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        margin-bottom: 20px;
        overflow: hidden;
    }
    
    .razonete-header {
        text-align: center;
        font-weight: 600;
        color: white;
        background-color: #004b8d;
        padding: 10px;
    }
    
    .razonete-body { 
        display: flex; 
        flex-direction: column;
        min-height: 80px;
        max-height: 400px;
        overflow-y: auto;
    }
    
    .lancamento-item {
        display: flex;
        border-bottom: 1px solid #f0f0f0;
        font-size: 12px;
    }
    
    .lancamento-debito {
        width: 50%;
        text-align: center;
        padding: 8px;
        color: #c0392b;
        border-right: 1px solid #ddd;
    }
    
    .lancamento-credito {
        width: 50%;
        text-align: center;
        padding: 8px;
        color: #27ae60;
    }
    
    .lancamento-data {
        font-size: 10px;
        color: #666;
        margin-top: 2px;
    }
    
    .legal-box {
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        color: #856404;
        padding: 20px;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    
    .report-header {
        background-color: #f8f9fa;
        color: #004b8d;
        padding: 12px;
        border-radius: 8px;
        text-align: center;
        font-weight: 700;
        margin-bottom: 15px;
    }
    
    .balanco-grupo {
        background-color: #e8f0fe;
        padding: 8px;
        border-radius: 5px;
        margin-top: 10px;
        font-weight: bold;
    }
    
    .balanco-conta {
        padding-left: 30px;
        font-size: 0.9em;
        color: #444;
    }
    
    @media print {
        .stSidebar, .stButton, .stForm { display: none !important; }
        .block-container { padding-top: 0 !important; }
    }
</style>
            
""", unsafe_allow_html=True)

# ==============================================================================
# UTILITÁRIOS
# ==============================================================================
def get_image_base64(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except:
        return None

def mostrar_landing_page():
    """Mostra a landing page com informações do sistema e botão de acesso"""
    
    # CSS personalizado para landing page
    st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] { 
            background: linear-gradient(135deg, #004b8d 0%, #0066c0 50%, #0052a3 100%) !important; 
            min-height: 100vh; 
        }
        [data-testid="stHeader"], [data-testid="stSidebar"], footer, .stDeployButton { display: none !important; }
        .block-container { padding-top: 2rem !important; max-width: 1400px !important; }
        
        /* Hero Section */
        .hero-section { 
            text-align: center; 
            padding: 60px 20px; 
            color: white;
        }
        .hero-title { 
            font-size: 4rem; 
            font-weight: 800; 
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .hero-subtitle { 
            font-size: 1.8rem; 
            font-weight: 300; 
            margin-bottom: 20px;
            opacity: 0.95;
        }
        .hero-description { 
            font-size: 1.2rem; 
            max-width: 800px; 
            line-height: 1.8; 
            margin: 0 auto 40px;
            opacity: 0.9;
        }
        
        /* Stats */
        .stats-container { 
            display: flex; 
            justify-content: center; 
            gap: 30px; 
            margin: 50px 0;
            flex-wrap: wrap;
        }
        .stat-box { 
            background: rgba(255,255,255,0.15); 
            backdrop-filter: blur(10px);
            padding: 30px 40px; 
            border-radius: 15px; 
            text-align: center;
            min-width: 150px;
            border: 1px solid rgba(255,255,255,0.2);
        }
        .stat-number { 
            font-size: 3rem; 
            font-weight: 800; 
            color: #f5a623;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
        }
        .stat-label { 
            font-size: 1rem; 
            margin-top: 8px;
            opacity: 0.9;
        }
        
        /* CTA Button */
        .cta-button {
            display: inline-block;
            background: linear-gradient(135deg, #f5a623 0%, #ffb830 100%);
            color: #004b8d !important;
            padding: 18px 50px;
            border-radius: 12px;
            text-decoration: none;
            font-weight: 700;
            font-size: 1.2rem;
            margin: 30px 0;
            box-shadow: 0 8px 30px rgba(245,166,35,0.4);
            transition: all 0.3s ease;
        }
        .cta-button:hover {
            transform: translateY(-3px);
            box-shadow: 0 12px 40px rgba(245,166,35,0.5);
        }
        
        /* Target Audience */
        .audience-section {
            background: white;
            color: #333;
            padding: 60px 40px;
            border-radius: 20px;
            margin: 60px 0;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        .audience-title {
            color: #004b8d;
            font-size: 2rem;
            text-align: center;
            margin-bottom: 40px;
            font-weight: 700;
        }
        .audience-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 30px;
        }
        .audience-card {
            background: linear-gradient(135deg, #e8f4f8 0%, #d4eaf4 100%);
            padding: 30px 20px;
            border-radius: 15px;
            text-align: center;
            border: 2px solid transparent;
            transition: all 0.3s ease;
        }
        .audience-card:hover {
            border-color: #f5a623;
            transform: translateY(-5px);
        }
        .audience-icon {
            font-size: 3rem;
            margin-bottom: 15px;
        }
        .audience-name {
            font-size: 1.2rem;
            font-weight: 700;
            color: #004b8d;
        }
        
        /* Features */
        .features-section {
            background: rgba(255,255,255,0.1);
            padding: 50px 40px;
            border-radius: 20px;
            margin: 40px 0;
        }
        .features-title {
            color: white;
            font-size: 2rem;
            text-align: center;
            margin-bottom: 40px;
            font-weight: 700;
        }
        .feature-item {
            display: flex;
            align-items: center;
            gap: 15px;
            margin: 20px 0;
            font-size: 1.1rem;
        }
        .feature-check {
            color: #4caf50;
            font-size: 1.5rem;
            font-weight: bold;
        }
        
        /* Pricing Preview */
        .pricing-preview {
            background: white;
            color: #333;
            padding: 60px 40px;
            border-radius: 20px;
            margin: 60px 0;
        }
        .pricing-title {
            color: #004b8d;
            font-size: 2.2rem;
            text-align: center;
            margin-bottom: 50px;
            font-weight: 700;
        }
        
        /* Footer */
        .landing-footer {
            text-align: center;
            padding: 40px 20px;
            color: rgba(255,255,255,0.8);
            margin-top: 60px;
        }
        .sandbox-warning {
            background: rgba(245,166,35,0.2);
            border: 2px solid #f5a623;
            padding: 15px 30px;
            border-radius: 10px;
            display: inline-block;
            margin-top: 20px;
            font-weight: 600;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Hero Section
    st.markdown("""
    <div class="hero-section">
        <div class="hero-title">🦅 Guriatã</div>
        <div class="hero-subtitle">Plataforma de Ensino de Contabilidade</div>
        <div class="hero-description">
            Aprenda contabilidade na prática com um ambiente completo e seguro. 
            Lançamentos contábeis, razonetes, balancete, DRE e balanço patrimonial 
            em uma única plataforma desenvolvida para universidades, escolas e professores.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Stats
    st.markdown("""
    <div class="stats-container">
        <div class="stat-box">
            <div class="stat-number">3</div>
            <div class="stat-label">Perfis de Acesso</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">80+</div>
            <div class="stat-label">Contas Contábeis</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">5</div>
            <div class="stat-label">Relatórios</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">∞</div>
            <div class="stat-label">Lançamentos</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Botão de acesso
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🚀 ACESSAR SISTEMA GRATUITAMENTE", type="primary", use_container_width=True, key="btn_acesso_landing"):
            st.query_params["page"] = "sistema"
            st.rerun()
    
    st.markdown("<div style='text-align:center;margin:20px 0;'><a href='#publico' style='color:white;text-decoration:none;font-size:0.95rem;'>↓ Conheça nosso público</a></div>", unsafe_allow_html=True)
    
    # Público Alvo
    st.markdown("<a id='publico'></a>", unsafe_allow_html=True)
    st.markdown("""
    <div class="audience-section">
        <div class="audience-title">🎯 Para Quem é o Guriatã?</div>
        <div class="audience-grid">
            <div class="audience-card">
                <div class="audience-icon">🏛️</div>
                <div class="audience-name">Universidades</div>
                <p style="margin-top:10px;font-size:0.9rem;">Cursos de Ciências Contábeis que buscam prática real</p>
            </div>
            <div class="audience-card">
                <div class="audience-icon">🏫</div>
                <div class="audience-name">Escolas Técnicas</div>
                <p style="margin-top:10px;font-size:0.9rem;">Ensino médio técnico em contabilidade</p>
            </div>
            <div class="audience-card">
                <div class="audience-icon">👨‍🏫</div>
                <div class="audience-name">Professores</div>
                <p style="margin-top:10px;font-size:0.9rem;">Educadores que ensinam contabilidade</p>
            </div>
            <div class="audience-card">
                <div class="audience-icon">📚</div>
                <div class="audience-name">Alunos</div>
                <p style="margin-top:10px;font-size:0.9rem;">Estudantes de todos os níveis</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Funcionalidades
    st.markdown("""
    <div class="features-section">
        <div class="features-title">✨ Funcionalidades Completas</div>
    </div>
    """, unsafe_allow_html=True)
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        st.markdown("""
        <div class="feature-item"><span class="feature-check">✓</span><span><strong>Lançamentos Contábeis:</strong> Registre débitos e créditos com histórico</span></div>
        <div class="feature-item"><span class="feature-check">✓</span><span><strong>Razonetes (T):</strong> Visualize movimentações por conta</span></div>
        <div class="feature-item"><span class="feature-check">✓</span><span><strong>Balancete:</strong> Verifique saldo de todas as contas</span></div>
        """, unsafe_allow_html=True)
    with col_f2:
        st.markdown("""
        <div class="feature-item"><span class="feature-check">✓</span><span><strong>DRE:</strong> Demonstração do Resultado do Exercício</span></div>
        <div class="feature-item"><span class="feature-check">✓</span><span><strong>Balanço Patrimonial:</strong> Ativo, Passivo e PL equilibrados</span></div>
        <div class="feature-item"><span class="feature-check">✓</span><span><strong>Múltiplos Perfis:</strong> Admin, Professor e Aluno</span></div>
        """, unsafe_allow_html=True)
    
    # Pricing Preview
    st.markdown("""
    <div class="pricing-preview">
        <div class="pricing-title">💰 Planos Flexíveis para Cada Necessidade</div>
    </div>
    """, unsafe_allow_html=True)
    
    col_p1, col_p2, col_p3, col_p4 = st.columns(4)
    with col_p1:
        st.markdown("""
        <div style="background:#f8f9fa;padding:20px;border-radius:10px;text-align:center;">
            <h4 style="color:#004b8d;margin:0;">Gratuito</h4>
            <h2 style="color:#333;margin:10px 0;">R$ 0</h2>
            <p style="font-size:0.85rem;color:#666;">Para estudantes</p>
            <hr style="border:none;border-top:1px solid #ddd;margin:15px 0;">
            <p style="font-size:0.8rem;">1 usuário<br>1 turma<br>Lançamentos ilimitados</p>
        </div>
        """, unsafe_allow_html=True)
    with col_p2:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#004b8d,#0066c0);color:white;padding:20px;border-radius:10px;text-align:center;position:relative;">
            <div style="position:absolute;top:-10px;left:50%;transform:translateX(-50%);background:#f5a623;color:#004b8d;padding:3px 10px;border-radius:10px;font-size:0.7rem;font-weight:bold;">POPULAR</div>
            <h4 style="margin:0;">Professor</h4>
            <h2 style="margin:10px 0;">R$ 49,90<span style="font-size:1rem;">/mês</span></h2>
            <p style="font-size:0.85rem;opacity:0.9;">Para educadores</p>
            <hr style="border:none;border-top:1px solid rgba(255,255,255,0.3);margin:15px 0;">
            <p style="font-size:0.8rem;">50 alunos<br>5 turmas<br>Relatórios avançados</p>
        </div>
        """, unsafe_allow_html=True)
    with col_p3:
        st.markdown("""
        <div style="background:#f8f9fa;padding:20px;border-radius:10px;text-align:center;">
            <h4 style="color:#004b8d;margin:0;">Escola</h4>
            <h2 style="color:#333;margin:10px 0;">R$ 299,90</h2>
            <p style="font-size:0.85rem;color:#666;">Instituições</p>
            <hr style="border:none;border-top:1px solid #ddd;margin:15px 0;">
            <p style="font-size:0.8rem;">500 alunos<br>50 turmas<br>Suporte dedicado</p>
        </div>
        """, unsafe_allow_html=True)
    with col_p4:
        st.markdown("""
        <div style="background:#f8f9fa;padding:20px;border-radius:10px;text-align:center;">
            <h4 style="color:#004b8d;margin:0;">Enterprise</h4>
            <h2 style="color:#333;margin:10px 0;">R$ 999,90</h2>
            <p style="font-size:0.85rem;color:#666;">Solução completa</p>
            <hr style="border:none;border-top:1px solid #ddd;margin:15px 0;">
            <p style="font-size:0.8rem;">Ilimitado<br>White-label<br>Gerente de conta</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Footer
    st.markdown("""
    <div class="landing-footer">
        <p><strong>⚠️ AMBIENTE SANDBOX</strong></p>
        <p>Este sistema é destinado exclusivamente para fins educacionais.</p>
        <p>NÃO insira dados reais ou sensíveis. Em conformidade com a LGPD.</p>
        <div class="sandbox-warning">🔒 Dados fictícios apenas · Versão 5.0</div>
        <p style="margin-top:30px;font-size:0.85rem;">© 2024 Guriatã - Todos os direitos reservados · Desenvolvido com ❤️ para educação contábil no Brasil</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Esconder menu lateral e parar execução
    st.stop()

# Mostrar landing page se configurado
if show_landing and st.query_params.get("page") != "sistema":
    mostrar_landing_page()

def formatar_data_br(data):
    if data:
        return data.strftime('%d/%m/%Y')
    return ""

def fmt_moeda(v):
    return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def hash_senha(senha: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(senha.encode('utf-8'), salt).decode('utf-8')

def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        return bcrypt.checkpw(senha.encode('utf-8'), senha_hash.encode('utf-8'))
    except:
        return False

def slugify(s):
    safe = s.lower()
    replacements = {'ã': 'a', 'á': 'a', 'à': 'a', 'â': 'a', 'ä': 'a',
                    'é': 'e', 'ê': 'e', 'ë': 'e', 'í': 'i', 'î': 'i', 'ì': 'i', 'ï': 'i',
                    'ó': 'o', 'õ': 'o', 'ô': 'o', 'ö': 'o', 'ú': 'u', 'û': 'u', 'ü': 'u',
                    'ç': 'c', ' ': '_'}
    for old, new in replacements.items():
        safe = safe.replace(old, new)
    return ''.join(ch for ch in safe if ch.isalnum() or ch == '_')

def botao_imprimir(menu, me, session):
    html_content = gerar_html_impressao(menu, me, session)
    st.download_button(label="⬇️ Baixar Relatório HTML", data=html_content.encode('utf-8'),
                       file_name=f"relatorio_{slugify(menu)}.html", mime="text/html")

def gerar_html_impressao(menu, me, session):
    def tabela_html(cabecalhos, linhas):
        html = '<table border="1" style="border-collapse:collapse; width:100%;">'
        html += '<tr>' + ''.join(f'<th style="padding:8px; background:#f2f2f2;">{h}</th>' for h in cabecalhos) + '</tr>'
        for linha in linhas:
            html += '<tr>' + ''.join(f'<td style="padding:8px;">{v}</td>' for v in linha) + '</tr>'
        html += '</table>'
        return html

    html = f"""<!DOCTYPE html>
<html lang="pt-br">
<head><meta charset="UTF-8"><title>Relatório - {menu}</title>
<style>
    body {{ font-family: Arial, sans-serif; margin: 20px; }}
    h1 {{ color: #004b8d; text-align: center; }}
    table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background-color: #f2f2f2; }}
    .info-box {{ background: #eef4fb; border: 1px solid #d5e4f6; padding: 10px; border-radius: 6px; margin-bottom: 16px; }}
</style>
</head>
<body>
    <h1>Relatório - {menu}</h1>
    <div class="info-box">
        <p><strong>Gerado em:</strong> {date.today()}</p>
        <p><strong>Usuário:</strong> {me.nome} ({me.username})</p>
    </div>
"""
    if menu == "Escrituração e Diário":
        lancs = session.exec(select(Lancamento).where(Lancamento.usuario_id == me.id).order_by(Lancamento.data_lancamento)).all()
        if lancs:
            mapa_nomes = get_mapa_nomes()
            linhas = [[formatar_data_br(l.data_lancamento),
                       f"{l.conta_debito} - {mapa_nomes.get(l.conta_debito, l.conta_debito)}",
                       f"{l.conta_credito} - {mapa_nomes.get(l.conta_credito, l.conta_credito)}",
                       fmt_moeda(l.valor), l.historico or "—"] for l in lancs]
            html += "<h2>Diário de Lançamentos</h2>" + tabela_html(["Data", "Débito", "Crédito", "Valor", "Histórico"], linhas)
        else:
            html += "<p>Nenhum lançamento registrado.</p>"
    elif menu == "Razonetes":
        lancs = session.exec(select(Lancamento).where(Lancamento.usuario_id == me.id).order_by(Lancamento.data_lancamento)).all()
        mov = calcular_movimentacao(me.id)
        html += "<h2>Razonetes com Lançamentos</h2>"
        for conta, v in sorted(mov.items()):
            html += f"<h3>{conta} - {v['nome']}</h3>"
            html += "<table border='1' style='border-collapse:collapse; width:100%;'>"
            html += "<tr><th>Data</th><th>Débito</th><th>Crédito</th><th>Histórico</th></tr>"
            for l in lancs:
                if l.conta_debito == conta:
                    html += f"<tr><td>{formatar_data_br(l.data_lancamento)}</td><td style='color:#c0392b'>{fmt_moeda(l.valor)}</td><td>-</td><td>{l.historico or ''}</td></tr>"
                if l.conta_credito == conta:
                    html += f"<tr><td>{formatar_data_br(l.data_lancamento)}</td><td>-</td><td style='color:#27ae60'>{fmt_moeda(l.valor)}</td><td>{l.historico or ''}</td></tr>"
            html += f"<tr style='background:#f0f0f0; font-weight:bold'><td>TOTAL</td><td>{fmt_moeda(v['total_debito'])}</td><td>{fmt_moeda(v['total_credito'])}</td><td>Saldo: {fmt_moeda(v['saldo'])}</td></tr>"
            html += "</table><br>"
    elif menu == "Balancete":
        mov = calcular_movimentacao(me.id)
        if mov:
            linhas = [[f"{k} - {v['nome']}", fmt_moeda(v['total_debito']), fmt_moeda(v['total_credito']), fmt_moeda(v['saldo'])]
                      for k, v in sorted(mov.items())]
            html += "<h2>Balancete completo</h2>" + tabela_html(["Conta", "Débito", "Crédito", "Saldo"], linhas)
            total_debito = sum(v['total_debito'] for v in mov.values())
            total_credito = sum(v['total_credito'] for v in mov.values())
            html += f"<p><strong>Total Débitos:</strong> {fmt_moeda(total_debito)}</p>"
            html += f"<p><strong>Total Créditos:</strong> {fmt_moeda(total_credito)}</p>"
            html += f"<p><strong>Diferença:</strong> {fmt_moeda(total_debito - total_credito)}</p>"
        else:
            html += "<p>Nenhuma movimentação encontrada.</p>"
    elif menu == "DRE":
        mov = calcular_movimentacao(me.id)
        grupos = {
            "Receitas Operacionais Brutas": [(k, d['saldo']) for k, d in sorted(mov.items()) if k.startswith('3.1')],
            "Deduções de Receita": [(k, d['saldo'] * -1) for k, d in sorted(mov.items()) if k.startswith('3.2')],
            "Receitas Financeiras": [(k, d['saldo']) for k, d in sorted(mov.items()) if k.startswith('3.3')],
            "Custos (CMV / CSP)": [(k, d['saldo'] * -1) for k, d in sorted(mov.items()) if k.startswith('4')],
            "Despesas Operacionais": [(k, d['saldo'] * -1) for k, d in sorted(mov.items()) if k.startswith('5')],
            "Despesas Financeiras": [(k, d['saldo'] * -1) for k, d in sorted(mov.items()) if k.startswith('6.1')],
        }
        html += "<h2>Demonstração do Resultado do Exercício</h2>"
        for titulo, linhas in grupos.items():
            if linhas:
                html += f"<h3>{titulo}</h3>" + tabela_html(["Conta", "Valor"],
                         [[f"{conta} - {mov[conta]['nome']}", fmt_moeda(valor)] for conta, valor in linhas])
                html += f"<p><strong>Subtotal:</strong> {fmt_moeda(sum(v for _, v in linhas))}</p>"

        rec_bruta = sum(v for _, v in grupos["Receitas Operacionais Brutas"])
        deducoes = sum(v for _, v in grupos["Deduções de Receita"])
        rec_liquida = rec_bruta + deducoes
        custos = sum(v for _, v in grupos["Custos (CMV / CSP)"])
        lucro_bruto = rec_liquida + custos
        despesas_op = sum(v for _, v in grupos["Despesas Operacionais"])
        rec_fin = sum(v for _, v in grupos["Receitas Financeiras"])
        desp_fin = sum(v for _, v in grupos["Despesas Financeiras"])
        res_op = lucro_bruto + despesas_op
        res_final = res_op + rec_fin + desp_fin

        html += "<h3>Resumo</h3>" + tabela_html(["Descrição", "Valor"], [
            ["Receita Operacional Bruta", fmt_moeda(rec_bruta)],
            ["Deduções da Receita", fmt_moeda(deducoes)],
            ["Receita Líquida", fmt_moeda(rec_liquida)],
            ["Custos", fmt_moeda(custos)],
            ["Lucro Bruto", fmt_moeda(lucro_bruto)],
            ["Despesas Operacionais", fmt_moeda(despesas_op)],
            ["Receitas Financeiras", fmt_moeda(rec_fin)],
            ["Despesas Financeiras", fmt_moeda(desp_fin)],
            ["Resultado Líquido", fmt_moeda(res_final)]
        ])
    elif menu == "Balanço":
        at, pas, _, _, grupos_a, grupos_p, _, nomes_a, nomes_p = gerar_demonstrativos(me.id)
        html += "<h2>Balanço Patrimonial</h2><h3>Ativo</h3>"
        for pfx in sorted(grupos_a.keys()):
            if grupos_a[pfx]:
                html += f"<h4>{nomes_a.get(pfx, pfx)}</h4>" + tabela_html(["Conta", "Saldo"],
                         [[l["Conta"], fmt_moeda(l["Saldo"])] for l in grupos_a[pfx]])
                html += f"<p><strong>Subtotal:</strong> {fmt_moeda(sum(l['Saldo'] for l in grupos_a[pfx]))}</p>"
        html += f"<p><strong>Total do Ativo:</strong> {fmt_moeda(at)}</p>"
        html += "<h3>Passivo e Patrimônio Líquido</h3>"
        for pfx in sorted(grupos_p.keys()):
            if grupos_p[pfx]:
                html += f"<h4>{nomes_p.get(pfx, pfx)}</h4>" + tabela_html(["Conta", "Saldo"],
                         [[l["Conta"], fmt_moeda(l["Saldo"])] for l in grupos_p[pfx]])
                html += f"<p><strong>Subtotal:</strong> {fmt_moeda(sum(l['Saldo'] for l in grupos_p[pfx]))}</p>"
        html += f"<p><strong>Total do Passivo + PL:</strong> {fmt_moeda(pas)}</p>"
    html += "</body></html>"
    return html

# ==============================================================================
# 2. BANCO DE DADOS (NEON POSTGRESQL)
# ==============================================================================
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# URL do banco de dados via variável de ambiente (NUNCA hardcoded no código)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/contabilidade.db")

engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True, pool_size=5, max_overflow=10)

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

class Usuario(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    senha: str
    nome: str
    perfil: str
    termos_aceitos: bool = Field(default=False)
    criado_por_id: Optional[int] = Field(default=None)
    escola_id: Optional[int] = Field(default=None)
    turma_id: Optional[int] = Field(default=None)
    xp: int = Field(default=0)
    data_criacao: date = Field(default_factory=date.today)
    # Campos para monetização
    plano_id: Optional[int] = Field(default=None, foreign_key="plano.id")
    assinatura_ativa: bool = Field(default=False)
    data_assinatura_inicio: Optional[date] = Field(default=None)
    data_assinatura_fim: Optional[date] = Field(default=None)
    stripe_customer_id: Optional[str] = Field(default=None)

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

class ContaContabil(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    codigo: str
    nome: str
    tipo: str
    natureza: str

class Lancamento(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    data_lancamento: date
    conta_debito: str
    conta_credito: str
    valor: float
    historico: str
    usuario_id: int = Field(foreign_key="usuario.id")

# ==============================================================================
# MODELOS DE MONETIZAÇÃO
# ==============================================================================
class Plano(SQLModel, table=True):
    """Planos de assinatura da plataforma"""
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str  # "Gratuito", "Professor", "Escola", "Enterprise"
    descricao: str
    preco_mensal: float  # 0 para gratuito
    max_usuarios: int = 1  # Número máximo de usuários (alunos)
    max_turmas: int = 1
    recursos: str  # JSON ou texto com lista de recursos inclusos
    stripe_price_id: Optional[str] = Field(default=None)  # ID do preço no Stripe
    ativo: bool = Field(default=True)

class Assinatura(SQLModel, table=True):
    """Registro de assinaturas dos usuários"""
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuario.id")
    plano_id: int = Field(foreign_key="plano.id")
    data_inicio: date
    data_fim: Optional[date] = None
    status: str = "ativa"  # ativa, cancelada, expirada, pendente
    stripe_subscription_id: Optional[str] = Field(default=None)
    stripe_customer_id: Optional[str] = Field(default=None)
    ultimo_pagamento: Optional[date] = Field(default=None)
    proximo_cobranca: Optional[date] = Field(default=None)

def get_session(): return Session(engine)

def carregar_dados_padrao(session):
    # Criar planos de assinatura se não existirem
    if not session.exec(select(Plano)).first():
        print("Criando planos de assinatura...")
        planos = [
            Plano(
                nome="Gratuito",
                descricao="Plano básico para estudantes individuais",
                preco_mensal=0,
                max_usuarios=1,
                max_turmas=1,
                recursos='["Lançamentos ilimitados", "Balancete", "Razonetes", "Suporte por e-mail"]',
                ativo=True
            ),
            Plano(
                nome="Professor",
                descricao="Para professores que desejam gerenciar múltiplas turmas",
                preco_mensal=49.90,
                max_usuarios=50,
                max_turmas=5,
                recursos='["Tudo do plano Gratuito", "Até 50 alunos", "Até 5 turmas", "Relatórios avançados", "Exportação Excel/PDF", "Suporte prioritário"]',
                stripe_price_id="",  # Preencher com ID do Stripe
                ativo=True
            ),
            Plano(
                nome="Escola",
                descricao="Para escolas e instituições de ensino",
                preco_mensal=299.90,
                max_usuarios=500,
                max_turmas=50,
                recursos='["Tudo do plano Professor", "Até 500 alunos", "Até 50 turmas", "Múltiplos professores", "Dashboard administrativo", "API de integração", "Suporte dedicado"]',
                stripe_price_id="",  # Preencher com ID do Stripe
                ativo=True
            ),
            Plano(
                nome="Enterprise",
                descricao="Solução completa para grandes instituições",
                preco_mensal=999.90,
                max_usuarios=-1,  # Ilimitado
                max_turmas=-1,  # Ilimitado
                recursos='["Tudo do plano Escola", "Usuários ilimitados", "Turmas ilimitadas", "White-label", "Treinamento personalizado", "SLA garantido", "Gerente de conta"]',
                stripe_price_id="",  # Preencher com ID do Stripe
                ativo=True
            )
        ]
        for plano in planos:
            session.add(plano)
        session.commit()
    
    if not session.exec(select(Usuario).where(Usuario.username == "admin")).first():
        esc = session.exec(select(Escola).where(Escola.nome == "Sede Administrativa")).first()
        if not esc:
            esc = Escola(nome="Sede Administrativa", cidade="Matriz")
            session.add(esc); session.commit(); session.refresh(esc)
        admin = Usuario(username="admin", senha=hash_senha("123"), nome="Administrador Geral", perfil="admin", termos_aceitos=True, escola_id=esc.id)
        session.add(admin)
        session.commit()

    if not session.exec(select(ContaContabil)).first():
        contas = [
            ("1", "ATIVO", "S", "D"),
            ("1.1", "CIRCULANTE", "S", "D"),
            ("1.1.1", "Caixa Geral", "A", "D"),
            ("1.1.2", "Bancos Conta Movimento", "A", "D"),
            ("1.1.3", "Aplicações Financeiras", "A", "D"),
            ("1.1.4", "Clientes", "A", "D"),
            ("1.1.5", "Estoques", "A", "D"),
            ("1.1.6", "Impostos a Recuperar", "A", "D"),
            ("1.1.7", "Adiantamento a Fornecedores", "A", "D"),
            ("1.1.8", "Adiantamento a Funcionários", "A", "D"),
            ("1.2", "NÃO CIRCULANTE", "S", "D"),
            ("1.2.1", "Realizável a Longo Prazo", "S", "D"),
            ("1.2.2", "Investimentos", "S", "D"),
            ("1.2.2.1", "Participações em Outras Empresas", "A", "D"),
            ("1.2.2.2", "Investimentos Imobiliários", "A", "D"),
            ("1.2.3", "Imobilizado", "S", "D"),
            ("1.2.3.1", "Imóveis", "A", "D"),
            ("1.2.3.2", "Veículos", "A", "D"),
            ("1.2.3.3", "Móveis e Utensílios", "A", "D"),
            ("1.2.3.4", "Equipamentos de Informática", "A", "D"),
            ("1.2.4", "Intangível", "A", "D"),
            ("2", "PASSIVO", "S", "C"),
            ("2.1", "CIRCULANTE", "S", "C"),
            ("2.1.1", "Fornecedores", "A", "C"),
            ("2.1.2", "Salários a Pagar", "A", "C"),
            ("2.1.3", "Obrigações Sociais", "A", "C"),
            ("2.1.4", "Impostos a Recolher", "A", "C"),
            ("2.1.5", "Adiantamento de Clientes", "A", "C"),
            ("2.1.6", "Aluguéis a Pagar", "A", "C"),
            ("2.1.7", "Dividendos a Pagar", "A", "C"),
            ("2.1.8", "Empréstimos e Financiamentos (CP)", "A", "C"),
            ("2.2", "NÃO CIRCULANTE", "S", "C"),
            ("2.2.1", "Empréstimos e Financiamentos (LP)", "A", "C"),
            ("2.2.2", "Financiamentos (LP)", "A", "C"),
            ("2.3", "PATRIMÔNIO LÍQUIDO", "S", "C"),
            ("2.3.1", "Capital Social", "A", "C"),
            ("2.3.2", "Reservas de Lucros", "A", "C"),
            ("2.3.3", "Lucros Acumulados", "A", "C"),
            ("2.3.4", "Ajustes de Avaliação Patrimonial", "A", "C"),
            ("2.3.5", "Dividendos Propostos", "A", "C"),
            ("3", "RECEITAS", "S", "C"),
            ("3.1", "RECEITA OPERACIONAL BRUTA", "S", "C"),
            ("3.1.1", "Venda de Mercadorias", "A", "C"),
            ("3.1.2", "Prestação de Serviços", "A", "C"),
            ("3.1.3", "Receita de Serviços Financeiros", "A", "C"),
            ("3.2", "DEDUÇÕES DA RECEITA BRUTA", "S", "D"),
            ("3.2.1", "Devoluções de Vendas", "A", "D"),
            ("3.2.2", "Impostos Incidentes sobre Vendas", "A", "D"),
            ("3.2.3", "Descontos Incondicionais Concedidos", "A", "D"),
            ("3.3", "RECEITAS FINANCEIRAS", "S", "C"),
            ("3.3.1", "Juros Ativos", "A", "C"),
            ("3.3.2", "Rendimentos de Aplicações Financeiras", "A", "C"),
            ("3.3.3", "Descontos Financeiros Obtidos", "A", "C"),
            ("3.4", "OUTRAS RECEITAS OPERACIONAIS", "S", "C"),
            ("3.4.1", "Receitas com Aluguéis", "A", "C"),
            ("3.4.2", "Receitas Eventuais", "A", "C"),
            ("4", "CUSTOS", "S", "D"),
            ("4.1", "CUSTO DOS PRODUTOS VENDIDOS", "S", "D"),
            ("4.1.1", "Custo das Mercadorias Vendidas (CMV)", "A", "D"),
            ("4.1.2", "Custo dos Serviços Prestados (CSP)", "A", "D"),
            ("4.1.3", "Compras de Mercadorias", "A", "D"),
            ("4.1.4", "Fretes e Seguros sobre Compras", "A", "D"),
            ("5", "DESPESAS OPERACIONAIS", "S", "D"),
            ("5.1", "DESPESAS COM PESSOAL", "S", "D"),
            ("5.1.1", "Salários e Ordenados", "A", "D"),
            ("5.1.2", "Pró-labore", "A", "D"),
            ("5.1.3", "Encargos Sociais (INSS, FGTS)", "A", "D"),
            ("5.1.4", "Benefícios (Vale Transporte, Alimentação)", "A", "D"),
            ("5.1.5", "13º Salário", "A", "D"),
            ("5.2", "DESPESAS ADMINISTRATIVAS", "S", "D"),
            ("5.2.1", "Aluguel", "A", "D"),
            ("5.2.2", "Energia Elétrica", "A", "D"),
            ("5.2.3", "Água e Esgoto", "A", "D"),
            ("5.2.4", "Telefonia e Internet", "A", "D"),
            ("5.2.5", "Material de Escritório", "A", "D"),
            ("5.2.6", "Manutenção e Reparos", "A", "D"),
            ("5.2.7", "Publicidade e Propaganda", "A", "D"),
            ("5.2.8", "Despesas com Transporte", "A", "D"),
            ("5.2.9", "Seguros", "A", "D"),
            ("5.2.10", "Serviços de Terceiros (Consultoria)", "A", "D"),
            ("5.3", "DESPESAS COMERCIAIS", "S", "D"),
            ("5.3.1", "Comissões sobre Vendas", "A", "D"),
            ("5.3.2", "Descontos Condicionais Concedidos", "A", "D"),
            ("5.4", "DESPESAS TRIBUTÁRIAS", "S", "D"),
            ("5.4.1", "PIS sobre Faturamento", "A", "D"),
            ("5.4.2", "COFINS sobre Faturamento", "A", "D"),
            ("5.4.3", "ISSQN (Imposto sobre Serviços)", "A", "D"),
            ("5.4.4", "IRPJ", "A", "D"),
            ("5.4.5", "CSLL (Contribuição Social)", "A", "D"),
            ("6", "RESULTADO FINANCEIRO LÍQUIDO", "S", "D"),
            ("6.1", "DESPESAS FINANCEIRAS", "S", "D"),
            ("6.1.1", "Juros Passivos", "A", "D"),
            ("6.1.2", "Tarifas Bancárias", "A", "D"),
            ("6.1.3", "Descontos Financeiros Concedidos", "A", "D"),
            ("6.1.4", "Despesas com Juros de Empréstimos", "A", "D"),
            ("7", "OUTRAS DESPESAS OPERACIONAIS", "S", "D"),
            ("7.1", "Despesas Eventuais", "A", "D"),
            ("7.2", "Perdas com Créditos Incobráveis", "A", "D"),
        ]

        for c, n, t, nat in contas:
            session.add(ContaContabil(codigo=c, nome=n, tipo=t, natureza=nat))
        session.commit()

def inicializar_banco():
    SQLModel.metadata.create_all(engine)
    session = get_session()
    carregar_dados_padrao(session)

inicializar_banco()

# ==============================================================================
# 3. LÓGICA CONTÁBIL
# ==============================================================================
def get_mapa_nomes():
    return {c.codigo: c.nome for c in get_session().exec(select(ContaContabil)).all()}

def get_contas_analiticas():
    return {c.codigo: f"{c.codigo} - {c.nome}" for c in get_session().exec(select(ContaContabil).where(ContaContabil.tipo == 'A')).all()}

def calcular_movimentacao(uid):
    s = get_session()
    lancs = s.exec(select(Lancamento).where(Lancamento.usuario_id == uid)).all()
    dados = {}
    mapa_nat = {c.codigo: c.natureza for c in s.exec(select(ContaContabil)).all()}
    mapa_nome = get_mapa_nomes()
    for l in lancs:
        if l.conta_debito not in dados:
            dados[l.conta_debito] = {'deb': 0.0, 'cred': 0.0}
        dados[l.conta_debito]['deb'] += l.valor
        if l.conta_credito not in dados:
            dados[l.conta_credito] = {'deb': 0.0, 'cred': 0.0}
        dados[l.conta_credito]['cred'] += l.valor
    resultado = {}
    for k, v in dados.items():
        nat = mapa_nat.get(k, 'D')
        saldo = v['deb'] - v['cred'] if nat == 'D' else v['cred'] - v['deb']
        resultado[k] = {'nome': mapa_nome.get(k, k), 'natureza': nat, 'total_debito': v['deb'], 'total_credito': v['cred'], 'saldo': saldo}
    return resultado

def gerar_demonstrativos(uid):
    mov = calcular_movimentacao(uid)
    rec_bruta = deducoes = custos = despesas_op = rec_financ = desp_financ = 0.0
    ativo_total = passivo_total = 0.0
    grupos_ativo = {"1.1": [], "1.2.1": [], "1.2.3": [], "1.2.4": []}
    grupos_passivo = {"2.1": [], "2.2": [], "2.3": []}
    nomes_grupos_a = {"1.1": "Ativo Circulante", "1.2.1": "Realizável a Longo Prazo", "1.2.3": "Imobilizado", "1.2.4": "Intangível"}
    nomes_grupos_p = {"2.1": "Passivo Circulante", "2.2": "Passivo Não Circulante", "2.3": "Patrimônio Líquido"}

    for conta, d in mov.items():
        saldo = d['saldo']
        if conta.startswith('3.1'): rec_bruta += saldo
        elif conta.startswith('3.2'): deducoes += saldo
        elif conta.startswith('3.3'): rec_financ += saldo
        elif conta.startswith('4'): custos += saldo
        elif conta.startswith('5'): despesas_op += saldo
        elif conta.startswith('6.1'): desp_financ += saldo
        elif conta.startswith('1'):
            ativo_total += saldo
            linha = {"Conta": f"{conta} - {d['nome']}", "Saldo": saldo}
            encaixou = False
            for pfx in ["1.2.4", "1.2.3", "1.2.1", "1.1"]:
                if conta.startswith(pfx):
                    grupos_ativo[pfx].append(linha); encaixou = True; break
            if not encaixou: grupos_ativo["1.1"].append(linha)
        elif conta.startswith('2'):
            passivo_total += saldo
            linha = {"Conta": f"{conta} - {d['nome']}", "Saldo": saldo}
            encaixou = False
            for pfx in ["2.3", "2.2", "2.1"]:
                if conta.startswith(pfx):
                    grupos_passivo[pfx].append(linha); encaixou = True; break
            if not encaixou: grupos_passivo["2.1"].append(linha)

    rec_liquida = rec_bruta - deducoes
    lucro_bruto = rec_liquida - custos
    res_operacional = lucro_bruto - despesas_op
    res_liquido = res_operacional + rec_financ - desp_financ

    if res_liquido != 0:
        passivo_total += res_liquido
        grupos_passivo["2.3"].append({"Conta": "Resultado do Exercício", "Saldo": res_liquido})

    dre_rows = [
        {"Descrição": "(=) Receita Operacional Bruta", "Valor": fmt_moeda(rec_bruta)},
        {"Descrição": "(-) Deduções da Receita", "Valor": fmt_moeda(deducoes * -1)},
        {"Descrição": "(=) Receita Operacional Líquida", "Valor": fmt_moeda(rec_liquida)},
        {"Descrição": "(-) Custos (CMV/CSP)", "Valor": fmt_moeda(custos * -1)},
        {"Descrição": "(=) Lucro Bruto", "Valor": fmt_moeda(lucro_bruto)},
        {"Descrição": "(-) Despesas Operacionais", "Valor": fmt_moeda(despesas_op * -1)},
        {"Descrição": "(+) Receitas Financeiras", "Valor": fmt_moeda(rec_financ)},
        {"Descrição": "(-) Despesas Financeiras", "Valor": fmt_moeda(desp_financ * -1)},
        {"Descrição": "(=) Resultado Líquido do Exercício", "Valor": fmt_moeda(res_liquido)}
    ]
    df_dre = pd.DataFrame(dre_rows)
    return ativo_total, passivo_total, rec_bruta, res_liquido, grupos_ativo, grupos_passivo, df_dre, nomes_grupos_a, nomes_grupos_p

# ==============================================================================
# 4. LOGIN & SISTEMA
# ==============================================================================
def login():
    s = get_session()
    u = st.session_state.get("u_log", "").strip()
    p = st.session_state.get("u_pass", "").strip()
    user = s.exec(select(Usuario).where(Usuario.username == u)).first()
    if user:
        if user.senha.startswith('$2b$'):
            senha_valida = verificar_senha(p, user.senha)
        else:
            senha_valida = (p == user.senha)
            if senha_valida:
                user.senha = hash_senha(p)
                s.add(user); s.commit()
        if senha_valida:
            st.session_state["user"] = user
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")
    else:
        st.error("Usuário ou senha incorretos.")

def logout():
    st.session_state["user"] = None
    st.rerun()

if "user" not in st.session_state or not st.session_state["user"]:
    st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] { background: linear-gradient(135deg, #e8f4f8 0%, #d4eaf4 50%, #c8e0ef 100%) !important; min-height: 100vh; }
        [data-testid="stHeader"], [data-testid="stSidebar"], footer { display: none !important; }
        .block-container { padding-top: 6vh !important; max-width: 480px !important; }
        .login-card { background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0,75,141,0.15); overflow: hidden; }
        .login-hero { background: linear-gradient(160deg, #d4eaf4 0%, #e8f4f8 60%, #f0f8fc 100%); padding: 36px 40px; text-align: center; }
        .field-label { color: #334155; font-size: 0.72em; font-weight: 700; text-transform: uppercase; margin: 14px 0 4px 0; }
        .stTextInput>div>div>input { border-radius: 10px !important; border: none !important; height: 44px !important; background: #f8fafc !important; box-shadow: none !important; outline: none !important; }
        .stFormSubmitButton>button { height: 48px !important; border-radius: 10px !important; background: linear-gradient(135deg, #004b8d 0%, #0066c0 100%) !important; color: white !important; font-weight: 700 !important; font-size: 15px !important; border: none !important; box-shadow: none !important; }
    </style>
    """, unsafe_allow_html=True)
    logo_b64 = get_image_base64("assets/logo.png")
    img_tag = f"<img src='data:image/png;base64,{logo_b64}' style='width:140px;'>" if logo_b64 else "<div style='font-size:5rem;'>🦅</div>"
    st.markdown(f"<div class='login-card'><div class='login-hero'>{img_tag}</div>", unsafe_allow_html=True)
    with st.form("login_form", clear_on_submit=True):
        st.markdown("<span class='field-label'>👤 Login de acesso</span>", unsafe_allow_html=True)
        st.text_input("u", key="u_log", placeholder="Digite seu usuário", label_visibility="collapsed")
        st.text_input("p", type="password", key="u_pass", placeholder="Digite sua senha", label_visibility="collapsed")
        if st.form_submit_button("ENTRAR", type="primary"):
            login()
    st.markdown("""<div style='text-align:center;margin-top:20px;color:#94a3b8;'>Plataforma para o ensino da contabilidade<br>Todos os direitos reservados · Versão 5.0</div>""", unsafe_allow_html=True)
    st.stop()

session = get_session()
try:
    me = session.get(Usuario, st.session_state["user"].id)
except:
    logout(); st.stop()

if not me.termos_aceitos:
    st.write(""); st.write("")
    c1, c2, c3 = st.columns([1, 4, 1])
    with c2:
        st.markdown("""<div class="legal-box"><h4>⚠️ POLÍTICA DE USO E PRIVACIDADE</h4>
            <p>Este sistema é um ambiente de simulação acadêmica (Sandbox), desenvolvido estritamente para fins pedagógicos.</p>
            <p><b>1. Dados Proibidos:</b> Em conformidade com a LGPD, é terminantemente PROIBIDA a inserção de dados verídicos.</p>
        </div>""", unsafe_allow_html=True)
        if st.button("✅ Li e Concordo com os Termos", type="primary", use_container_width=True):
            me.termos_aceitos = True; session.add(me); session.commit(); st.rerun()
    st.stop()

with st.sidebar:
    try: st.image("assets/logo.png", width=100)
    except: pass
    st.write(f"Olá, **{me.nome.split()[0]}**")
    st.caption(f"Perfil: {me.perfil.replace('admin', 'Administrador').upper()}")
    opts = ["Dashboard", "Meu Perfil"]
    if me.perfil == 'admin':
        opts.extend(["Escolas", "Professores", "Turmas", "Alunos",
                     "Plano de Contas",
                     "Escrituração e Diário", "Razonetes", "Balancete", "DRE", "Balanço"])
    elif me.perfil == 'professor':
        opts.extend(["Minhas Turmas", "Meus Alunos", "Postar Aulas",
                     "Escrituração e Diário", "Razonetes", "Balancete", "DRE", "Balanço"])
    elif me.perfil == 'aluno':
        opts.extend(["Minhas Aulas", "Escrituração e Diário",
                     "Razonetes", "Balancete", "DRE", "Balanço"])
    menu = st.sidebar.radio("Navegação", opts, label_visibility="collapsed")
    st.markdown("---")
    if st.button("🚪 Sair do Sistema"): logout()

# ==============================================================================
# 5. DASHBOARD
# ==============================================================================
if menu == "Dashboard":
    st.title("📊 Painel de Controle")
    if me.perfil == 'admin':
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"<div class='kpi-card'><div class='kpi-title'>Escolas</div><div class='kpi-val'>{len(session.exec(select(Escola)).all())}</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='kpi-card'><div class='kpi-title'>Professores</div><div class='kpi-val'>{len(session.exec(select(Usuario).where(Usuario.perfil=='professor')).all())}</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='kpi-card'><div class='kpi-title'>Alunos</div><div class='kpi-val'>{len(session.exec(select(Usuario).where(Usuario.perfil=='aluno')).all())}</div></div>", unsafe_allow_html=True)
    elif me.perfil == 'professor':
        minhas_turmas = session.exec(select(Turma).where(Turma.professor_id == me.id)).all()
        total_turmas = len(minhas_turmas)
        total_alunos = len(session.exec(select(Usuario).where(Usuario.perfil == 'aluno').where(Usuario.turma_id.in_([t.id for t in minhas_turmas]))).all()) if minhas_turmas else 0
        total_aulas = len(session.exec(select(Aula).where(Aula.professor_id == me.id)).all())
        escola_nome = session.get(Escola, me.escola_id).nome if me.escola_id else "Não vinculada"
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"<div class='kpi-card'><div class='kpi-title'>Minhas Turmas</div><div class='kpi-val'>{total_turmas}</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='kpi-card'><div class='kpi-title'>Total de Alunos</div><div class='kpi-val'>{total_alunos}</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='kpi-card'><div class='kpi-title'>Aulas Postadas</div><div class='kpi-val'>{total_aulas}</div></div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='kpi-card'><div class='kpi-title'>Instituição</div><div class='kpi-val'>{escola_nome[:15]}...</div></div>", unsafe_allow_html=True)
    elif me.perfil == 'aluno':
        _, _, rec, luc, _, _, _, _, _ = gerar_demonstrativos(me.id)
        c1, c2 = st.columns(2)
        c1.markdown(f"<div class='kpi-card'><div class='kpi-title'>Receita Bruta</div><div class='kpi-val' style='color:green'>{fmt_moeda(rec)}</div></div>", unsafe_allow_html=True)
        cor_luc = 'green' if luc >= 0 else 'red'
        c2.markdown(f"<div class='kpi-card'><div class='kpi-title'>Resultado Líquido</div><div class='kpi-val' style='color:{cor_luc}'>{fmt_moeda(luc)}</div></div>", unsafe_allow_html=True)

    st.divider()
    st.subheader("📚 Plano de Contas Geral")
    contas_db = session.exec(select(ContaContabil).order_by(ContaContabil.codigo)).all()
    df_contas = pd.DataFrame([{"Código": c.codigo, "Nome": c.nome, "Tipo": "Analítica" if c.tipo == 'A' else "Sintética", "Natureza": c.natureza} for c in contas_db])
    st.dataframe(df_contas, use_container_width=True, hide_index=True)

# ==============================================================================
# 6. MEU PERFIL
# ==============================================================================
elif menu == "Meu Perfil":
    st.header("👤 Meu Perfil")
    with st.form("myprofile"):
        n = st.text_input("Meu Nome", value=me.nome)
        s = st.text_input("Minha Senha", value="", type="password", placeholder="Digite nova senha (opcional)")
        if me.perfil == 'professor' and me.escola_id:
            escola = session.get(Escola, me.escola_id)
            st.selectbox("Escola vinculada", [escola], format_func=lambda x: x.nome, disabled=True)
        if st.form_submit_button("💾 Atualizar", type="primary"):
            me.nome = n
            if s:
                me.senha = hash_senha(s)
            session.add(me); session.commit()
            st.success("Perfil atualizado!")
            st.rerun()

# ==============================================================================
# 7. MINHAS TURMAS (PROFESSOR)
# ==============================================================================
elif menu == "Minhas Turmas":
    st.header("🏫 Minhas Turmas")
    if me.perfil == 'professor':
        st.subheader("➕ Criar Nova Turma")
        with st.form("nova_turma_professor", clear_on_submit=True):
            n = st.text_input("Nome da turma", placeholder="Ex: 3º Ano A — Contabilidade")
            a = st.text_input("Ano letivo", value="2026", placeholder="Ex: 2026")
            if st.form_submit_button("📌 Criar Turma", type="primary"):
                if n and a:
                    session.add(Turma(nome=n, ano_letivo=a, professor_id=me.id, escola_id=me.escola_id or 1))
                    session.commit()
                    st.success(f"Turma '{n}' criada com sucesso!")
                    st.rerun()
                else:
                    st.warning("Preencha o nome e o ano letivo antes de salvar.")
        st.divider()
        st.subheader("📚 Suas Turmas")
        minhas_turmas = session.exec(select(Turma).where(Turma.professor_id == me.id)).all()
        if minhas_turmas:
            for t in minhas_turmas:
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.write(f"**{t.nome}**")
                    st.caption(f"📅 {t.ano_letivo}")
                with col2:
                    alunos_turma = session.exec(select(Usuario).where(Usuario.turma_id == t.id)).all()
                    st.metric("Alunos", len(alunos_turma))
                with col3:
                    if st.button("🗑️ Excluir", key=f"del_turma_{t.id}", use_container_width=True):
                        if len(alunos_turma) > 0:
                            st.error(f"Não é possível excluir a turma '{t.nome}' pois existem {len(alunos_turma)} aluno(s) matriculado(s).")
                        else:
                            session.delete(t)
                            session.commit()
                            st.success(f"Turma '{t.nome}' excluída com sucesso!")
                            st.rerun()
                st.divider()
        else:
            st.info("Você ainda não tem turmas criadas. Crie uma usando o formulário acima!")
    else:
        st.warning("Esta seção é apenas para professores.")

# ==============================================================================
# 8. MEUS ALUNOS (PROFESSOR)
# ==============================================================================
elif menu == "Meus Alunos":
    st.header("👥 Meus Alunos")
    if me.perfil == 'professor':
        minhas_turmas = session.exec(select(Turma).where(Turma.professor_id == me.id)).all()
        if not minhas_turmas:
            st.error("Você não tem turmas criadas ainda. Crie uma turma em 'Minhas Turmas' primeiro!")
        else:
            st.subheader("➕ Matricular Novo Aluno")
            with st.form("matricular_aluno_professor", clear_on_submit=True):
                n = st.text_input("Nome completo do aluno", placeholder="Ex: João Pedro Oliveira")
                u = st.text_input("Login de acesso", placeholder="Ex: joao.pedro")
                t = st.selectbox("Turma", minhas_turmas, format_func=lambda x: f"{x.nome} ({x.ano_letivo})")
                st.caption("A senha inicial será **123**. O aluno poderá alterá-la no primeiro acesso.")
                if st.form_submit_button("✅ Matricular Aluno", type="primary"):
                    if n and u:
                        if session.exec(select(Usuario).where(Usuario.username == u)).first():
                            st.error("❌ Este login já está em uso. Escolha outro.")
                        else:
                            session.add(Usuario(nome=n, username=u, senha=hash_senha("123"), perfil="aluno", turma_id=t.id, criado_por_id=me.id))
                            session.commit()
                            st.success(f"Aluno '{n}' matriculado com sucesso!")
                            st.rerun()
                    else:
                        st.warning("Preencha o nome e o login antes de salvar.")
            st.divider()
            st.subheader("📋 Seus Alunos")
            turmas_dict = {t.id: t.nome for t in minhas_turmas}
            alunos = session.exec(select(Usuario).where(Usuario.perfil == 'aluno').where(Usuario.turma_id.in_([t.id for t in minhas_turmas]))).all()
            if alunos:
                for aluno in alunos:
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    with col1:
                        st.write(f"**{aluno.nome}**")
                        st.caption(f"👤 @{aluno.username}")
                    with col2:
                        st.write(f"📚 {turmas_dict.get(aluno.turma_id, '—')}")
                    with col3:
                        st.caption(f"⭐ XP: {aluno.xp}")
                    with col4:
                        if st.button("🗑️", key=f"del_aluno_{aluno.id}", help="Excluir aluno", use_container_width=True):
                            lancamentos_aluno = session.exec(select(Lancamento).where(Lancamento.usuario_id == aluno.id)).all()
                            for lanc in lancamentos_aluno:
                                session.delete(lanc)
                            session.delete(aluno)
                            session.commit()
                            st.success(f"Aluno '{aluno.nome}' excluído com sucesso!")
                            st.rerun()
                    st.divider()
            else:
                st.info("Nenhum aluno matriculado em suas turmas. Use o formulário acima para adicionar alunos!")
    else:
        st.warning("Esta seção é apenas para professores.")

# ==============================================================================
# 9. POSTAR AULAS (PROFESSOR)
# ==============================================================================
elif menu == "Postar Aulas":
    st.header("📹 Postar Aulas")
    if me.perfil == 'professor':
        minhas_turmas = session.exec(select(Turma).where(Turma.professor_id == me.id)).all()
        if not minhas_turmas:
            st.error("Você não tem turmas criadas. Crie uma turma antes de postar aulas.")
        else:
            with st.form("postar_aula", clear_on_submit=True):
                turma = st.selectbox("Turma", minhas_turmas, format_func=lambda x: f"{x.nome} ({x.ano_letivo})")
                titulo = st.text_input("Título da aula", placeholder="Ex: Introdução à Contabilidade")
                descricao = st.text_area("Descrição / Conteúdo", placeholder="Descreva o conteúdo da aula...")
                arquivo = st.file_uploader("Anexar arquivo (PDF, DOC, PPT, etc.)", type=["pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "txt", "jpg", "png"])
                if st.form_submit_button("📤 Postar Aula", type="primary"):
                    if titulo and descricao:
                        arquivo_blob = arquivo.read() if arquivo else None
                        session.add(Aula(titulo=titulo, descricao=descricao, arquivo_blob=arquivo_blob,
                                         nome_arquivo=arquivo.name if arquivo else None,
                                         professor_id=me.id, turma_id=turma.id))
                        session.commit()
                        st.success("✅ Aula postada com sucesso!")
                        st.rerun()
                    else:
                        st.warning("Preencha pelo menos o título e a descrição da aula.")
            st.divider()
            st.subheader("📚 Aulas Postadas")
            aulas = session.exec(select(Aula).where(Aula.professor_id == me.id)).all()
            if aulas:
                turmas_dict = {t.id: t.nome for t in minhas_turmas}
                for aula in reversed(aulas):
                    col1, col2 = st.columns([3, 1])
                    col1.write(f"**{aula.titulo}** — {turmas_dict.get(aula.turma_id, '?')}")
                    col1.write(f"*{aula.descricao[:100]}...*" if len(aula.descricao) > 100 else f"*{aula.descricao}*")
                    col1.caption(f"📅 Postada em: {formatar_data_br(aula.data_postagem)}")
                    if aula.arquivo_blob and aula.nome_arquivo:
                        try:
                            col2.download_button(label="⬇️ Download", data=aula.arquivo_blob, file_name=aula.nome_arquivo, key=f"download_aula_{aula.id}")
                        except:
                            col2.error("Erro: arquivo inválido")
                    if col2.button("🗑️ Excluir", key=f"del_aula_{aula.id}", use_container_width=True):
                        session.delete(aula)
                        session.commit()
                        st.rerun()
                    st.divider()
            else:
                st.info("Você ainda não postou nenhuma aula.")
    else:
        st.warning("Esta seção é apenas para professores.")

# ==============================================================================
# 10. MINHAS AULAS (ALUNO)
# ==============================================================================
elif menu == "Minhas Aulas":
    st.header("📚 Minhas Aulas")
    if me.perfil == 'aluno':
        if me.turma_id:
            aulas = session.exec(select(Aula).where(Aula.turma_id == me.turma_id)).all()
            turma = session.get(Turma, me.turma_id)
            st.subheader(f"Aulas de {turma.nome if turma else 'sua turma'}")
            if aulas:
                for aula in reversed(aulas):
                    with st.container(border=True):
                        col1, col2 = st.columns([3, 1])
                        col1.write(f"**{aula.titulo}**")
                        professor = session.get(Usuario, aula.professor_id)
                        col2.caption(f"👨‍🏫 {professor.nome if professor else '?'}")
                        col1.write(aula.descricao)
                        col1.caption(f"📅 Postada em: {formatar_data_br(aula.data_postagem)}")
                        if aula.arquivo_blob and aula.nome_arquivo:
                            try:
                                col1.download_button(label="⬇️ Baixar Arquivo", data=aula.arquivo_blob, file_name=aula.nome_arquivo, key=f"download_aula_aluno_{aula.id}")
                            except:
                                col1.error("Erro ao baixar arquivo")
            else:
                st.info("Nenhuma aula disponível no momento. Seu professor em breve postará aulas aqui!")
        else:
            st.warning("Você não está matriculado em nenhuma turma.")
    else:
        st.warning("Esta seção é apenas para alunos.")

# ==============================================================================
# 11. ESCOLAS (ADMIN)
# ==============================================================================
elif menu == "Escolas":
    st.header("🏢 Escolas")
    st.subheader("➕ Cadastrar nova escola")
    with st.form("ne", clear_on_submit=True):
        n = st.text_input("Nome da escola", placeholder="Ex: Escola Estadual Dom Pedro II")
        c = st.text_input("Cidade", placeholder="Ex: São Luís")
        if st.form_submit_button("💾 Salvar escola", type="primary"):
            if n and c:
                session.add(Escola(nome=n, cidade=c))
                session.commit()
                st.success(f"Escola '{n}' cadastrada com sucesso!")
                st.rerun()
            else:
                st.warning("Preencha o nome e a cidade antes de salvar.")
    st.divider()
    st.subheader("📋 Escolas cadastradas")
    escolas_lista = session.exec(select(Escola)).all()
    if escolas_lista:
        for escola in escolas_lista:
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.write(f"**{escola.nome}**")
                st.caption(f"📍 {escola.cidade}")
            with col2:
                st.caption(f"ID: {escola.id}")
            with col3:
                if st.button("🗑️ Excluir", key=f"del_escola_{escola.id}", use_container_width=True):
                    professores_vinculados = session.exec(select(Usuario).where(Usuario.escola_id == escola.id).where(Usuario.perfil == 'professor')).all()
                    if professores_vinculados:
                        st.error(f"Não é possível excluir a escola '{escola.nome}' pois existem {len(professores_vinculados)} professor(es) vinculado(s).")
                    else:
                        session.delete(escola)
                        session.commit()
                        st.success(f"Escola '{escola.nome}' excluída com sucesso!")
                        st.rerun()
            st.divider()
    else:
        st.info("Nenhuma escola cadastrada ainda.")

# ==============================================================================
# 12. PROFESSORES (ADMIN)
# ==============================================================================
elif menu == "Professores":
    st.header("👨‍🏫 Professores")
    escolas = session.exec(select(Escola)).all()
    if not escolas:
        st.warning("⚠️ Cadastre uma escola antes de adicionar professores.")
    else:
        st.subheader("➕ Cadastrar novo professor")
        with st.form("np", clear_on_submit=True):
            n = st.text_input("Nome completo", placeholder="Ex: Maria da Silva Santos")
            u = st.text_input("Login de acesso", placeholder="Ex: maria.santos")
            e = st.selectbox("Escola vinculada", escolas, format_func=lambda x: x.nome)
            st.caption("A senha inicial será **123**. O professor poderá alterá-la no primeiro acesso.")
            if st.form_submit_button("💾 Cadastrar professor", type="primary"):
                if n and u:
                    if session.exec(select(Usuario).where(Usuario.username == u)).first():
                        st.error("❌ Este login já está em uso. Escolha outro.")
                    else:
                        session.add(Usuario(nome=n, username=u, senha=hash_senha("123"), perfil="professor", escola_id=e.id, criado_por_id=me.id))
                        session.commit()
                        st.success(f"Professor '{n}' cadastrado com sucesso!")
                        st.rerun()
                else:
                    st.warning("Preencha o nome e o login antes de salvar.")
    st.divider()
    st.subheader("📋 Professores cadastrados")
    profs = session.exec(select(Usuario).where(Usuario.perfil == 'professor')).all()
    if profs:
        escola_map = {e.id: e.nome for e in escolas}
        for prof in profs:
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            with col1:
                st.write(f"**{prof.nome}**")
                st.caption(f"👤 @{prof.username}")
            with col2:
                st.write(f"🏫 {escola_map.get(prof.escola_id, '—')}")
            with col3:
                turmas_prof = session.exec(select(Turma).where(Turma.professor_id == prof.id)).all()
                st.caption(f"📚 {len(turmas_prof)} turma(s)")
            with col4:
                if st.button("🗑️", key=f"del_prof_{prof.id}", help="Excluir professor", use_container_width=True):
                    if turmas_prof:
                        st.error(f"Não é possível excluir o professor '{prof.nome}' pois ele possui {len(turmas_prof)} turma(s) vinculada(s).")
                    else:
                        session.delete(prof)
                        session.commit()
                        st.success(f"Professor '{prof.nome}' excluído com sucesso!")
                        st.rerun()
            st.divider()
    else:
        st.info("Nenhum professor cadastrado ainda.")

# ==============================================================================
# 13. TURMAS (ADMIN)
# ==============================================================================
elif menu == "Turmas":
    st.header("🏫 Turmas")
    if me.perfil == 'admin':
        st.subheader("➕ Criar nova turma")
        professores_list = session.exec(select(Usuario).where(Usuario.perfil == 'professor')).all()
        if not professores_list:
            st.warning("⚠️ Cadastre um professor antes de criar turmas.")
        else:
            with st.form("nt", clear_on_submit=True):
                n = st.text_input("Nome da turma", placeholder="Ex: 3º Ano A — Contabilidade")
                a = st.text_input("Ano letivo", value="2026", placeholder="Ex: 2026")
                professor = st.selectbox("Professor responsável", professores_list, format_func=lambda x: x.nome)
                if st.form_submit_button("💾 Criar turma", type="primary"):
                    if n and a:
                        session.add(Turma(nome=n, ano_letivo=a, professor_id=professor.id, escola_id=professor.escola_id or 1))
                        session.commit()
                        st.success(f"Turma '{n}' criada com sucesso!")
                        st.rerun()
                    else:
                        st.warning("Preencha o nome e o ano letivo antes de salvar.")
        st.divider()
        st.subheader("📋 Turmas cadastradas")
        ts = session.exec(select(Turma)).all()
        if ts:
            professores_map = {p.id: p.nome for p in professores_list}
            for turma in ts:
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                with col1:
                    st.write(f"**{turma.nome}**")
                    st.caption(f"📅 {turma.ano_letivo}")
                with col2:
                    st.write(f"👨‍🏫 {professores_map.get(turma.professor_id, '—')}")
                with col3:
                    alunos_turma = session.exec(select(Usuario).where(Usuario.turma_id == turma.id)).all()
                    st.caption(f"🎓 {len(alunos_turma)} aluno(s)")
                with col4:
                    if st.button("🗑️", key=f"del_turma_{turma.id}", help="Excluir turma", use_container_width=True):
                        if alunos_turma:
                            st.error(f"Não é possível excluir a turma '{turma.nome}' pois existem {len(alunos_turma)} aluno(s) matriculado(s).")
                        else:
                            session.delete(turma)
                            session.commit()
                            st.success(f"Turma '{turma.nome}' excluída com sucesso!")
                            st.rerun()
                st.divider()
        else:
            st.info("Nenhuma turma cadastrada ainda.")
    else:
        st.warning("Esta seção não está disponível para seu perfil.")

# ==============================================================================
# 14. PLANO DE CONTAS (ADMIN)
# ==============================================================================
elif menu == "Plano de Contas":
    st.header("📊 Plano de Contas - Gerência")
    
    tab1, tab2, tab3 = st.tabs(["📋 Visualizar Contas", "➕ Nova Conta", "✏️ Editar/Excluir Conta"])
    
    with tab1:
        st.subheader("Plano de Contas Completo")
        contas_db = session.exec(select(ContaContabil).order_by(ContaContabil.codigo)).all()
        if contas_db:
            df_contas = pd.DataFrame([{
                "Código": c.codigo, 
                "Nome": c.nome, 
                "Tipo": "Analítica" if c.tipo == 'A' else "Sintética", 
                "Natureza": "Devedora" if c.natureza == 'D' else "Credora"
            } for c in contas_db])
            st.dataframe(df_contas, use_container_width=True, hide_index=True)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total de Contas", len(contas_db))
            col2.metric("Contas Analíticas", sum(1 for c in contas_db if c.tipo == 'A'))
            col3.metric("Contas Sintéticas", sum(1 for c in contas_db if c.tipo == 'S'))
        else:
            st.info("Nenhuma conta cadastrada.")
    
    with tab2:
        st.subheader("➕ Criar Nova Conta Contábil")
        st.warning("⚠️ **Atenção:** Ao criar contas, respeite a hierarquia do plano de contas!")
        
        with st.form("nova_conta", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                codigo = st.text_input("Código da Conta", placeholder="Ex: 1.1.9 ou 5.2.11")
                nome = st.text_input("Nome da Conta", placeholder="Ex: Despesas com Viagens")
            with col2:
                tipo = st.selectbox("Tipo da Conta", 
                                   options=["A", "S"],
                                   format_func=lambda x: "Analítica (lançável)" if x == "A" else "Sintética (agrupadora)")
                natureza = st.selectbox("Natureza da Conta",
                                       options=["D", "C"],
                                       format_func=lambda x: "Devedora" if x == "D" else "Credora")
            
            conta_existente = session.exec(select(ContaContabil).where(ContaContabil.codigo == codigo)).first() if codigo else None
            
            if codigo and conta_existente:
                st.error(f"❌ Já existe uma conta com o código '{codigo}'!")
            
            if st.form_submit_button("💾 Criar Conta", type="primary"):
                if codigo and nome:
                    if conta_existente:
                        st.error("Código já em uso!")
                    else:
                        if not codigo.replace('.', '').isdigit():
                            st.error("Código deve conter apenas números e pontos (Ex: 1.1.1)")
                        else:
                            try:
                                session.add(ContaContabil(
                                    codigo=codigo,
                                    nome=nome,
                                    tipo=tipo,
                                    natureza=natureza
                                ))
                                session.commit()
                                st.success(f"✅ Conta '{codigo} - {nome}' criada com sucesso!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erro ao criar conta: {str(e)}")
                else:
                    st.warning("Preencha o código e o nome da conta!")
    
    with tab3:
        st.subheader("✏️ Editar ou Excluir Conta")
        
        contas_analiticas = session.exec(select(ContaContabil).where(ContaContabil.tipo == 'A').order_by(ContaContabil.codigo)).all()
        
        if contas_analiticas:
            contas_options = {f"{c.codigo} - {c.nome}": c for c in contas_analiticas}
            conta_selecionada_nome = st.selectbox("Selecione a conta para editar/excluir", 
                                                  options=list(contas_options.keys()))
            
            if conta_selecionada_nome:
                conta = contas_options[conta_selecionada_nome]
                
                tem_lancamentos = session.exec(
                    select(Lancamento).where(
                        (Lancamento.conta_debito == conta.codigo) | 
                        (Lancamento.conta_credito == conta.codigo)
                    )
                ).first() is not None
                
                if tem_lancamentos:
                    st.warning("⚠️ **Esta conta possui lançamentos vinculados!** Alterações podem afetar o histórico contábil.")
                
                with st.form("editar_conta", clear_on_submit=False):
                    st.markdown(f"**Editando:** {conta.codigo} - {conta.nome}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        novo_codigo = st.text_input("Novo código", value=conta.codigo)
                        novo_nome = st.text_input("Novo nome", value=conta.nome)
                    with col2:
                        novo_tipo = st.selectbox("Novo tipo", 
                                                options=["A", "S"],
                                                index=0 if conta.tipo == "A" else 1,
                                                format_func=lambda x: "Analítica" if x == "A" else "Sintética")
                        nova_natureza = st.selectbox("Nova natureza",
                                                    options=["D", "C"],
                                                    index=0 if conta.natureza == "D" else 1,
                                                    format_func=lambda x: "Devedora" if x == "D" else "Credora")
                    
                    col_btn1, col_btn2 = st.columns([1, 1])
                    with col_btn1:
                        if st.form_submit_button("💾 Salvar Alterações", type="primary"):
                            if novo_codigo and novo_nome:
                                codigo_existente = session.exec(
                                    select(ContaContabil).where(
                                        ContaContabil.codigo == novo_codigo,
                                        ContaContabil.id != conta.id
                                    )
                                ).first()
                                
                                if codigo_existente:
                                    st.error("❌ Este código já está em uso por outra conta!")
                                else:
                                    try:
                                        if novo_codigo != conta.codigo and tem_lancamentos:
                                            lancamentos_debito = session.exec(
                                                select(Lancamento).where(Lancamento.conta_debito == conta.codigo)
                                            ).all()
                                            lancamentos_credito = session.exec(
                                                select(Lancamento).where(Lancamento.conta_credito == conta.codigo)
                                            ).all()
                                            
                                            for lanc in lancamentos_debito:
                                                lanc.conta_debito = novo_codigo
                                            for lanc in lancamentos_credito:
                                                lanc.conta_credito = novo_codigo
                                        
                                        conta.codigo = novo_codigo
                                        conta.nome = novo_nome
                                        conta.tipo = novo_tipo
                                        conta.natureza = nova_natureza
                                        
                                        session.commit()
                                        st.success("✅ Conta atualizada com sucesso!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Erro ao atualizar: {str(e)}")
                            else:
                                st.warning("Preencha código e nome!")
                    
                    with col_btn2:
                        if st.form_submit_button("🗑️ Excluir Conta", type="secondary"):
                            if tem_lancamentos:
                                st.error(f"❌ Não é possível excluir a conta '{conta.codigo} - {conta.nome}' pois existem lançamentos vinculados a ela!")
                            else:
                                try:
                                    session.delete(conta)
                                    session.commit()
                                    st.success("✅ Conta excluída com sucesso!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Erro ao excluir: {str(e)}")
        else:
            st.info("Nenhuma conta analítica disponível para edição.")

# ==============================================================================
# 15. ALUNOS (ADMIN)
# ==============================================================================
elif menu == "Alunos":
    st.header("🎓 Alunos")
    turmas = session.exec(select(Turma)).all()
    if me.perfil == 'admin':
        if not turmas:
            st.warning("⚠️ Cadastre uma turma antes de matricular alunos.")
        else:
            st.subheader("➕ Matricular novo aluno")
            with st.form("na", clear_on_submit=True):
                n = st.text_input("Nome completo do aluno", placeholder="Ex: João Pedro Oliveira")
                u = st.text_input("Login de acesso", placeholder="Ex: joao.pedro")
                t = st.selectbox("Turma", turmas, format_func=lambda x: f"{x.nome} ({x.ano_letivo})")
                st.caption("A senha inicial será **123**. O aluno poderá alterá-la no primeiro acesso.")
                if st.form_submit_button("💾 Matricular aluno", type="primary"):
                    if n and u:
                        if session.exec(select(Usuario).where(Usuario.username == u)).first():
                            st.error("❌ Este login já está em uso. Escolha outro.")
                        else:
                            session.add(Usuario(nome=n, username=u, senha=hash_senha("123"), perfil="aluno", turma_id=t.id, criado_por_id=me.id))
                            session.commit()
                            st.success(f"Aluno '{n}' matriculado com sucesso!")
                            st.rerun()
                    else:
                        st.warning("Preencha o nome e o login antes de salvar.")
            st.divider()
            st.subheader("📋 Alunos matriculados")
            alunos = session.exec(select(Usuario).where(Usuario.perfil == 'aluno')).all()
            if alunos:
                turma_map = {t.id: f"{t.nome} ({t.ano_letivo})" for t in turmas}
                for aluno in alunos:
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    with col1:
                        st.write(f"**{aluno.nome}**")
                        st.caption(f"👤 @{aluno.username}")
                    with col2:
                        st.write(f"📚 {turma_map.get(aluno.turma_id, '—')}")
                    with col3:
                        st.caption(f"📅 {formatar_data_br(aluno.data_criacao)}")
                    with col4:
                        if st.button("🗑️", key=f"del_aluno_{aluno.id}", help="Excluir aluno", use_container_width=True):
                            lancamentos_aluno = session.exec(select(Lancamento).where(Lancamento.usuario_id == aluno.id)).all()
                            for lanc in lancamentos_aluno:
                                session.delete(lanc)
                            session.delete(aluno)
                            session.commit()
                            st.success(f"Aluno '{aluno.nome}' excluído com sucesso!")
                            st.rerun()
                    st.divider()
            else:
                st.info("Nenhum aluno matriculado ainda.")
    else:
        st.warning("Esta seção é apenas para administradores.")
        
# ==============================================================================
# 16. ESCRITURAÇÃO E DIÁRIO (COM EDIÇÃO)
# ==============================================================================
elif menu == "Escrituração e Diário":
    st.header("📝 Escrituração Contábil")
    mapa = get_contas_analiticas()
    contas = sorted(list(mapa.values()))

    with st.form("lanc", clear_on_submit=True):
        ce, cd = st.columns(2)
        with ce:
            d = st.date_input("Data", value=date.today())
            db = st.selectbox("Débito", contas, index=None)
            cr = st.selectbox("Crédito", contas, index=None)
        with cd:
            v = st.number_input("Valor (R$)", min_value=0.01, step=0.01)
            h = st.text_area("Histórico", placeholder="Descreva a operação...")
        if st.form_submit_button("✅ Gravar Lançamento", type="primary"):
            if db and cr:
                if db == cr:
                    st.error("❌ As contas de débito e crédito não podem ser iguais!")
                else:
                    try:
                        session.add(Lancamento(data_lancamento=d, valor=v, historico=h,
                            conta_debito=db.split(" - ")[0], conta_credito=cr.split(" - ")[0],
                            usuario_id=me.id))
                        session.commit()
                        st.success("✅ Lançamento gravado com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro ao gravar lançamento: {str(e)}")
            else:
                st.warning("⚠️ Selecione as contas de Débito e Crédito antes de gravar.")

    lancs = session.exec(select(Lancamento).where(Lancamento.usuario_id == me.id).order_by(desc(Lancamento.data_lancamento))).all()
    if lancs:
        mapa_nomes = get_mapa_nomes()
        st.divider()
        st.subheader("📋 Lançamentos Registrados")

        for l in lancs:
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([2, 2.5, 2.5, 2])
                col1.write(f"📅 {formatar_data_br(l.data_lancamento)}")
                col2.write(f"💳 {l.conta_debito} - {mapa_nomes.get(l.conta_debito, '')}")
                col3.write(f"💰 {l.conta_credito} - {mapa_nomes.get(l.conta_credito, '')}")
                col4.write(f"💵 {fmt_moeda(l.valor)}")

                if l.historico:
                    st.markdown(f"**📝 {l.historico}**")

                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("✏️ Editar", key=f"edit_{l.id}", use_container_width=True):
                        st.session_state["editando_id"] = l.id
                        st.session_state["editando_data"] = l.data_lancamento
                        st.session_state["editando_debito"] = f"{l.conta_debito} - {mapa_nomes.get(l.conta_debito, '')}"
                        st.session_state["editando_credito"] = f"{l.conta_credito} - {mapa_nomes.get(l.conta_credito, '')}"
                        st.session_state["editando_valor"] = l.valor
                        st.session_state["editando_historico"] = l.historico
                        st.rerun()
                with col_b:
                    if st.button("🗑️ Excluir", key=f"del_{l.id}", use_container_width=True):
                        session.delete(l)
                        session.commit()
                        st.success("Lançamento excluído!")
                        st.rerun()

        if "editando_id" in st.session_state:
            st.divider()
            st.subheader("✏️ Editando Lançamento")
            with st.form("editar_lancamento", clear_on_submit=False):
                col1, col2 = st.columns(2)
                with col1:
                    nova_data = st.date_input("Data", value=st.session_state["editando_data"])
                    novo_debito = st.selectbox("Débito", contas, index=contas.index(st.session_state["editando_debito"]) if st.session_state["editando_debito"] in contas else 0)
                    novo_credito = st.selectbox("Crédito", contas, index=contas.index(st.session_state["editando_credito"]) if st.session_state["editando_credito"] in contas else 0)
                with col2:
                    novo_valor = st.number_input("Valor (R$)", min_value=0.01, step=0.01, value=st.session_state["editando_valor"])
                    novo_historico = st.text_area("Histórico", value=st.session_state["editando_historico"])

                col_a, col_b = st.columns(2)
                with col_a:
                    if st.form_submit_button("💾 Salvar Alterações", type="primary"):
                        if novo_debito and novo_credito:
                            if novo_debito == novo_credito:
                                st.error("❌ As contas de débito e crédito não podem ser iguais!")
                            else:
                                try:
                                    lancamento = session.get(Lancamento, st.session_state["editando_id"])
                                    if lancamento:
                                        lancamento.data_lancamento = nova_data
                                        lancamento.conta_debito = novo_debito.split(" - ")[0]
                                        lancamento.conta_credito = novo_credito.split(" - ")[0]
                                        lancamento.valor = novo_valor
                                        lancamento.historico = novo_historico
                                        session.commit()
                                        st.success("✅ Lançamento atualizado com sucesso!")
                                        for k in ["editando_id","editando_data","editando_debito","editando_credito","editando_valor","editando_historico"]:
                                            del st.session_state[k]
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Erro ao atualizar: {str(e)}")
                        else:
                            st.warning("⚠️ Selecione as contas de Débito e Crédito.")

                with col_b:
                    if st.form_submit_button("❌ Cancelar Edição", type="secondary"):
                        for k in ["editando_id","editando_data","editando_debito","editando_credito","editando_valor","editando_historico"]:
                            del st.session_state[k]
                        st.rerun()

        botao_imprimir(menu, me, session)
    else:
        st.info("Nenhum lançamento registrado ainda. Utilize o formulário acima para adicionar seu primeiro lançamento contábil!")

# ==============================================================================
# 17. RAZONETES
# ==============================================================================
elif menu == "Razonetes":
    st.header("🗂️ Razonetes com Lançamentos Sequenciais")
    mov = calcular_movimentacao(me.id)
    lancs = session.exec(select(Lancamento).where(Lancamento.usuario_id == me.id).order_by(Lancamento.data_lancamento)).all()

    if mov and lancs:
        mapa_nomes = get_mapa_nomes()
        cols = st.columns(2)
        i = 0

        for conta, v in sorted(mov.items()):
            nome_conta = mapa_nomes.get(conta, conta)

            html = f"""<div class='razonete-container'>
                <div class='razonete-header'>{conta} - {nome_conta}</div>
                <div style='display:flex; border-bottom:1px solid #e0e0e0; background:#f5f5f5;'>
                    <div style='width:50%; text-align:center; padding:8px; font-weight:700; color:#c0392b;'>DÉBITO</div>
                    <div style='width:50%; text-align:center; padding:8px; font-weight:700; color:#27ae60;'>CRÉDITO</div>
                </div>
                <div class='razonete-body'>"""

            for l in lancs:
                if l.conta_debito == conta:
                    html += f"""
                    <div class='lancamento-item'>
                        <div class='lancamento-debito'>
                            {fmt_moeda(l.valor)}
                            <div class='lancamento-data'>{formatar_data_br(l.data_lancamento)}</div>
                        </div>
                        <div class='lancamento-credito'>-</div>
                    </div>"""
                elif l.conta_credito == conta:
                    html += f"""
                    <div class='lancamento-item'>
                        <div class='lancamento-debito'>-</div>
                        <div class='lancamento-credito'>
                            {fmt_moeda(l.valor)}
                            <div class='lancamento-data'>{formatar_data_br(l.data_lancamento)}</div>
                        </div>
                    </div>"""

            cor_saldo = "#c0392b" if v['saldo'] >= 0 else "#27ae60"
            rotulo = 'Devedor' if v['saldo'] >= 0 else 'Credor'
            html += f"""
                </div>
                <div style='padding:12px; text-align:center; background:#f8f9fa; border-top:1px solid #ddd; font-weight:bold;'>
                    <div style='display:flex; justify-content:space-between; flex-wrap:wrap; gap:4px;'>
                        <span>D: {fmt_moeda(v['total_debito'])}</span>
                        <span>C: {fmt_moeda(v['total_credito'])}</span>
                        <span style='color:{cor_saldo}'>Saldo: {fmt_moeda(v['saldo'])} ({rotulo})</span>
                    </div>
                </div>
            </div>"""

            cols[i % 2].markdown(html, unsafe_allow_html=True)
            i += 1

        botao_imprimir(menu, me, session)
    else:
        st.info("Nenhuma movimentação encontrada. Registre lançamentos para visualizar os razonetes.")

# ==============================================================================
# 18. BALANCETE
# ==============================================================================
elif menu == "Balancete":
    st.header("⚖️ Balancete de Verificação")
    mov = calcular_movimentacao(me.id)
    if mov:
        dados_tabela = []
        total_debito = 0
        total_credito = 0
        for k, v in sorted(mov.items()):
            dados_tabela.append({
                "Conta": f"{k} - {v['nome']}",
                "Débito": v['total_debito'],
                "Crédito": v['total_credito'],
                "Saldo": v['saldo']
            })
            total_debito += v['total_debito']
            total_credito += v['total_credito']
        df = pd.DataFrame(dados_tabela)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        col1.metric("💰 TOTAL DÉBITOS", fmt_moeda(total_debito))
        col2.metric("💰 TOTAL CRÉDITOS", fmt_moeda(total_credito))
        col3.metric("📊 DIFERENÇA", fmt_moeda(abs(total_debito - total_credito)),
                    delta="Equilibrado" if abs(total_debito - total_credito) < 0.01 else "Desequilibrado")
        if abs(total_debito - total_credito) > 0.01:
            st.warning("⚠️ O balancete está desequilibrado! Verifique seus lançamentos.")
        else:
            st.success("✅ Balancete equilibrado! Os débitos e créditos estão balanceados.")
    else:
        st.info("Nenhuma movimentação encontrada. Registre lançamentos para visualizar o balancete.")
    botao_imprimir(menu, me, session)

# ==============================================================================
# 19. DRE
# ==============================================================================
elif menu == "DRE":
    st.header("📉 Demonstração do Resultado do Exercício")
    mov = calcular_movimentacao(me.id)
    rec_bruta = sum(d['saldo'] for k, d in mov.items() if k.startswith('3.1'))
    deducoes = sum(abs(d['saldo']) for k, d in mov.items() if k.startswith('3.2'))
    custos = sum(abs(d['saldo']) for k, d in mov.items() if k.startswith('4'))
    despesas = sum(abs(d['saldo']) for k, d in mov.items() if k.startswith('5'))
    rec_fin = sum(d['saldo'] for k, d in mov.items() if k.startswith('3.3'))
    desp_fin = sum(abs(d['saldo']) for k, d in mov.items() if k.startswith('6.1'))
    receita_liquida = rec_bruta - deducoes
    lucro_bruto = receita_liquida - custos
    resultado_op = lucro_bruto - despesas
    resultado_final = resultado_op + rec_fin - desp_fin

    st.markdown(f"""
    <div style='background:white; border-radius:10px; padding:20px; margin:10px 0;'>
        <p><strong>(+) Receita Operacional Bruta</strong> <span style='float:right'>{fmt_moeda(rec_bruta)}</span></p>
        <p><strong>(-) Deduções da Receita</strong> <span style='float:right'>{fmt_moeda(deducoes)}</span></p>
        <p style='background:#e3f2fd; padding:8px; border-radius:5px;'><strong>(=) Receita Operacional Líquida</strong> <span style='float:right'>{fmt_moeda(receita_liquida)}</span></p>
        <p><strong>(-) Custos (CMV/CSP)</strong> <span style='float:right'>{fmt_moeda(custos)}</span></p>
        <p style='background:#e8f5e9; padding:8px; border-radius:5px;'><strong>(=) Lucro Bruto</strong> <span style='float:right'>{fmt_moeda(lucro_bruto)}</span></p>
        <p><strong>(-) Despesas Operacionais</strong> <span style='float:right'>{fmt_moeda(despesas)}</span></p>
        <p style='background:#fff3e0; padding:8px; border-radius:5px;'><strong>(=) Resultado Operacional</strong> <span style='float:right'>{fmt_moeda(resultado_op)}</span></p>
        <p><strong>(+) Receitas Financeiras</strong> <span style='float:right'>{fmt_moeda(rec_fin)}</span></p>
        <p><strong>(-) Despesas Financeiras</strong> <span style='float:right'>{fmt_moeda(desp_fin)}</span></p>
        <div style='background:linear-gradient(135deg,#004b8d,#0066c0); color:white; padding:15px; border-radius:10px; margin-top:15px; text-align:center;'>
            <h3 style='margin:0;'>(=) Resultado Líquido do Exercício</h3>
            <h2 style='margin:5px 0 0; color:{"#4caf50" if resultado_final >= 0 else "#f44336"};'>{fmt_moeda(resultado_final)}</h2>
        </div>
    </div>
    """, unsafe_allow_html=True)
    botao_imprimir(menu, me, session)

# ==============================================================================
# 20. BALANÇO PATRIMONIAL
# ==============================================================================
elif menu == "Balanço":
    st.header("🏛️ Balanço Patrimonial")
    at, pas, _, _, grupos_a, grupos_p, _, nomes_a, nomes_p = gerar_demonstrativos(me.id)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div class='report-header'>ATIVO</div>", unsafe_allow_html=True)
        total_ativo = 0
        for grupo in sorted(grupos_a.keys()):
            if grupos_a[grupo]:
                st.markdown(f"<div class='balanco-grupo'>{nomes_a.get(grupo, grupo)}</div>", unsafe_allow_html=True)
                for item in grupos_a[grupo]:
                    st.markdown(f"<div class='balanco-conta'>• {item['Conta']}: {fmt_moeda(item['Saldo'])}</div>", unsafe_allow_html=True)
                subtotal = sum(l['Saldo'] for l in grupos_a[grupo])
                st.caption(f"Subtotal do grupo: {fmt_moeda(subtotal)}")
                total_ativo += subtotal
                st.markdown("---")
        st.markdown(f"### Total do Ativo: {fmt_moeda(total_ativo)}")

    with c2:
        st.markdown("<div class='report-header'>PASSIVO + PATRIMÔNIO LÍQUIDO</div>", unsafe_allow_html=True)
        total_passivo = 0
        for grupo in sorted(grupos_p.keys()):
            if grupos_p[grupo]:
                st.markdown(f"<div class='balanco-grupo'>{nomes_p.get(grupo, grupo)}</div>", unsafe_allow_html=True)
                for item in grupos_p[grupo]:
                    st.markdown(f"<div class='balanco-conta'>• {item['Conta']}: {fmt_moeda(item['Saldo'])}</div>", unsafe_allow_html=True)
                subtotal = sum(l['Saldo'] for l in grupos_p[grupo])
                st.caption(f"Subtotal do grupo: {fmt_moeda(subtotal)}")
                total_passivo += subtotal
                st.markdown("---")
        st.markdown(f"### Total do Passivo + PL: {fmt_moeda(total_passivo)}")

    st.markdown("---")
    if abs(total_ativo - total_passivo) < 0.01:
        st.success("✅ **Balanço Equilibrado!** O Ativo é igual ao Passivo + Patrimônio Líquido.")
    else:
        st.error(f"⚠️ **Balanço Desequilibrado!** Diferença de {fmt_moeda(total_ativo - total_passivo)}")

    botao_imprimir(menu, me, session)

# ==============================================================================
# FIM DO CÓDIGO
# ==============================================================================