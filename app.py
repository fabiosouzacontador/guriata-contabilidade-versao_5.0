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
import os
import bcrypt

# ==============================================================================
# 1. CONFIGURAÇÕES & DESIGN
# ==============================================================================
warnings.filterwarnings("ignore")

# Função para carregar a logo e converter para base64 (para favicon)
def get_logo_base64():
    logo_path = "assets/logo.png"
    if Path(logo_path).exists():
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

logo_base64 = get_logo_base64()

# Configuração da página com favicon e título
st.set_page_config(
    page_title="Guriata - Sistema Contábil",
    layout="centered",
    page_icon="🦅" if not logo_base64 else f"data:image/png;base64,{logo_base64}",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# FUNÇÕES DE FORMATAÇÃO
# ==============================================================================
def formatar_data_br(data):
    """Converte date para string no formato DD/MM/AAAA"""
    if data:
        return data.strftime('%d/%m/%Y')
    return ""

def fmt_moeda(v):
    return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ==============================================================================
# FUNÇÕES DE SEGURANÇA PARA SENHAS
# ==============================================================================
def hash_senha(senha: str) -> str:
    """Gera hash da senha usando bcrypt"""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(senha.encode('utf-8'), salt).decode('utf-8')

def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Verifica se a senha corresponde ao hash"""
    try:
        return bcrypt.checkpw(senha.encode('utf-8'), senha_hash.encode('utf-8'))
    except:
        return False

st.markdown("""
<style>
    html, body, [class*="css"], .stDataFrame, .kpi-val, .razonete-body, .col-debito, .col-credito {
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important;
    }
    .block-container {
        padding-top: 2.5rem !important;
        padding-bottom: 1rem !important;
        max-width: 680px !important;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stTextInput>div>div, .stSelectbox>div>div, .stNumberInput>div>div, .stDateInput>div>div, .stTextArea>div>div {
        border-radius: 8px;
        border: 1px solid #e0e0e0;
    }
    .kpi-card {
        background: white;
        border: 1px solid #f0f0f0;
        border-left: 4px solid #004b8d;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        text-align: center;
        height: 100%;
    }
    .kpi-title { font-size: 0.8rem; color: #888; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
    .kpi-val { font-size: 1.8rem; font-weight: 700; color: #2c3e50; margin-top: 8px; }
    .stDataFrame { border: 1px solid #f0f0f0; border-radius: 8px; overflow: hidden; }
    .razonete-container {
        background: white; border: 1px solid #e0e0e0; border-radius: 8px;
        margin-bottom: 20px; overflow: hidden; page-break-inside: avoid;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .razonete-header {
        text-align: center; font-weight: 600; font-size: 0.95em;
        color: white; background-color: #004b8d; padding: 10px;
    }
    .razonete-body { display: flex; min-height: 80px; font-size: 0.78em; font-weight: 600; }
    .col-debito { width: 50%; border-right: 1px solid #ddd; text-align: center; padding: 10px 6px; color: #c0392b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .col-credito { width: 50%; text-align: center; padding: 10px 6px; color: #27ae60; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .report-header {
        background-color: #f8f9fa; color: #004b8d;
        padding: 12px; border-radius: 8px; text-align: center;
        font-weight: 700; margin-bottom: 15px; border: 1px solid #e9ecef;
    }
    .legal-box {
        background-color: #fff3cd; border: 1px solid #ffeeba; color: #856404;
        padding: 20px; border-radius: 8px; font-size: 0.9em; text-align: justify;
        margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .total-card {
        background: linear-gradient(135deg, #004b8d, #0066c0);
        color: white;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        margin-top: 20px;
    }
    .total-card h3 { margin: 0; font-size: 1rem; }
    .total-card .valor { font-size: 1.5rem; font-weight: bold; margin-top: 5px; }
    @media print {
        [data-testid="stSidebar"] { display: none; }
        .stButton, .stForm, .stSelectbox, .stTextInput, .stNumberInput, .stDateInput, .stTextArea { display: none !important; }
        .imprimir-btn { display: none !important; }
        .block-container { padding-top: 0 !important; }
        .stDataFrame, .razonete-container { display: block !important; width: 100% !important; }
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

def slugify(s):
    safe = s.lower()
    replacements = {
        'ã': 'a', 'á': 'a', 'à': 'a', 'â': 'a', 'ä': 'a',
        'é': 'e', 'ê': 'e', 'ë': 'e',
        'í': 'i', 'î': 'i', 'ì': 'i', 'ï': 'i',
        'ó': 'o', 'õ': 'o', 'ô': 'o', 'ö': 'o',
        'ú': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c', ' ': '_'
    }
    for old, new in replacements.items():
        safe = safe.replace(old, new)
    return ''.join(ch for ch in safe if ch.isalnum() or ch == '_')

def botao_imprimir(menu, me, session):
    html_content = gerar_html_impressao(menu, me, session)
    file_name = f"relatorio_{slugify(menu)}.html"
    st.download_button(
        label="⬇️ Baixar Relatório HTML",
        data=html_content.encode('utf-8'),
        file_name=file_name,
        mime="text/html",
        help="Baixe o relatório em HTML. Abra o arquivo no navegador e use Ctrl+P para imprimir ou salvar como PDF."
    )

def gerar_html_impressao(menu, me, session):
    def tabela_html(cabecalhos, linhas):
        html_t = "table"
        for h in cabecalhos:
            html_t += f"<th>{h}</th>"
        html_t += "tr"
        for linha in linhas:
            html_t += "<table>"
            for v in linha:
                html_t += f" looks{v}Nine"
            html_t += "</tr>"
        html_t += "</table>"
        return html_t

    def formatar_conta_row(conta, dados):
        return [
            f"{conta} - {dados['nome']}",
            fmt_moeda(dados['total_debito']),
            fmt_moeda(dados['total_credito']),
            fmt_moeda(dados['saldo'])
        ]

    def gerar_balanco_html(grupos, nomes_grupos):
        html_b = ""
        for pfx in sorted(grupos.keys()):
            linhas = grupos[pfx]
            if not linhas:
                continue
            subtotal = sum(l["Saldo"] for l in linhas)
            html_b += f"<h3>{nomes_grupos.get(pfx, pfx)}</h3>"
            html_b += tabela_html(["Conta", "Saldo"], [[l["Conta"], fmt_moeda(l["Saldo"])] for l in linhas])
            html_b += f"<p><strong>Subtotal:</strong> {fmt_moeda(subtotal)}</p>"
        return html_b

    html = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Relatório - {menu}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; color: #222; }}
        h1 {{ color: #004b8d; text-align: center; margin-bottom: 0.2rem; }}
        h2 {{ color: #024b82; margin-top: 1.8rem; }}
        h3 {{ color: #0356a5; margin: 1.2rem 0 0.4rem; }}
        p {{ margin: 0.35rem 0; }}
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
            linhas = []
            mapa_nomes = get_mapa_nomes()
            for l in lancs:
                linhas.append([
                    formatar_data_br(l.data_lancamento),
                    f"{l.conta_debito} - {mapa_nomes.get(l.conta_debito, l.conta_debito)}",
                    f"{l.conta_credito} - {mapa_nomes.get(l.conta_credito, l.conta_credito)}",
                    fmt_moeda(l.valor),
                    l.historico or "—"
                ])
            html += "<h2>Diário de Lançamentos</h2>"
            html += tabela_html(["Data", "Débito", "Crédito", "Valor", "Histórico"], linhas)
        else:
            html += "<p>Nenhum lançamento registrado.</p>"

    elif menu == "Razonetes":
        mov = calcular_movimentacao(me.id)
        html += "<h2>Razonetes</h2>"
        for conta, v in sorted(mov.items()):
            html += f"<h3>{conta} - {v['nome']}</h3>"
            html += tabela_html(
                ["Total Débito", "Total Crédito", "Saldo"],
                [[fmt_moeda(v['total_debito']), fmt_moeda(v['total_credito']), fmt_moeda(v['saldo'])]]
            )

    elif menu == "Balancete":
        mov = calcular_movimentacao(me.id)
        html += "<h2>Balancete completo</h2>"
        if mov:
            linhas = [formatar_conta_row(k, v) for k, v in sorted(mov.items())]
            html += tabela_html(["Conta", "Débito", "Crédito", "Saldo"], linhas)
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
            "Deduções de Receita":          [(k, d['saldo'] * -1) for k, d in sorted(mov.items()) if k.startswith('3.2')],
            "Receitas Financeiras":         [(k, d['saldo']) for k, d in sorted(mov.items()) if k.startswith('3.3')],
            "Custos (CMV / CSP)":           [(k, d['saldo'] * -1) for k, d in sorted(mov.items()) if k.startswith('4')],
            "Despesas Operacionais":        [(k, d['saldo'] * -1) for k, d in sorted(mov.items()) if k.startswith('5')],
            "Despesas Financeiras":         [(k, d['saldo'] * -1) for k, d in sorted(mov.items()) if k.startswith('6.1')],
        }
        html += "<h2>Demonstração do Resultado do Exercício</h2>"
        for titulo, linhas in grupos.items():
            if linhas:
                html += f"<h3>{titulo}</h3>"
                html += tabela_html(
                    ["Conta", "Valor"],
                    [[f"{conta} - {mov[conta]['nome']}", fmt_moeda(valor)] for conta, valor in linhas]
                )
                subtotal = sum(v for _, v in linhas)
                html += f"<p><strong>Subtotal {titulo}:</strong> {fmt_moeda(subtotal)}</p>"

        rec_bruta    = sum(v for _, v in grupos["Receitas Operacionais Brutas"])
        deducoes     = sum(v for _, v in grupos["Deduções de Receita"])
        rec_liquida  = rec_bruta + deducoes
        custos       = sum(v for _, v in grupos["Custos (CMV / CSP)"])
        lucro_bruto  = rec_liquida + custos
        despesas_op  = sum(v for _, v in grupos["Despesas Operacionais"])
        rec_fin      = sum(v for _, v in grupos["Receitas Financeiras"])
        desp_fin     = sum(v for _, v in grupos["Despesas Financeiras"])
        res_op       = lucro_bruto + despesas_op
        res_final    = res_op + rec_fin + desp_fin

        html += "<h3>Resumo</h3>"
        html += tabela_html(["Descrição", "Valor"], [
            ["Receita Operacional Bruta",    fmt_moeda(rec_bruta)],
            ["Deduções da Receita",          fmt_moeda(deducoes)],
            ["Receita Líquida",              fmt_moeda(rec_liquida)],
            ["Custos",                       fmt_moeda(custos)],
            ["Lucro Bruto",                  fmt_moeda(lucro_bruto)],
            ["Despesas Operacionais",        fmt_moeda(despesas_op)],
            ["Receitas Financeiras",         fmt_moeda(rec_fin)],
            ["Despesas Financeiras",         fmt_moeda(desp_fin)],
            ["Resultado Líquido",            fmt_moeda(res_final)]
        ])

    elif menu == "Balanço":
        at, pas, _, _, grupos_a, grupos_p, _, nomes_a, nomes_p = gerar_demonstrativos(me.id)
        html += "<h2>Balanço Patrimonial</h2>"
        html += "<h3>Ativo</h3>"
        html += gerar_balanco_html(grupos_a, nomes_a)
        html += f"<p><strong>Total do Ativo:</strong> {fmt_moeda(at)}</p>"
        html += "<h3>Passivo e Patrimônio Líquido</h3>"
        html += gerar_balanco_html(grupos_p, nomes_p)
        html += f"<p><strong>Total do Passivo + PL:</strong> {fmt_moeda(pas)}</p>"

    html += "</body></html>"
    return html

# ==============================================================================
# 2. BANCO DE DADOS & PLANO DE CONTAS MASTER
# ==============================================================================
DATABASE_URL = "postgresql://neondb_owner:npg_1ZQMkSRiK6pc@ep-damp-recipe-an7lkxz4-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)

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

def get_session(): return Session(engine)

def carregar_dados_padrao(session):
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
            ("1", "ATIVO", "S", "D"), ("1.1", "CIRCULANTE", "S", "D"),
            ("1.1.1", "Caixa Geral", "A", "D"), ("1.1.2", "Bancos Conta Movimento", "A", "D"),
            ("1.1.3", "Aplicações Financeiras", "A", "D"), ("1.1.4", "Clientes", "A", "D"),
            ("1.1.5", "Estoques", "A", "D"), ("1.1.6", "Impostos a Recuperar", "A", "D"),
            ("1.2", "NÃO CIRCULANTE", "S", "D"), ("1.2.1", "Realizável LP", "S", "D"),
            ("1.2.3", "Imobilizado", "S", "D"), ("1.2.3.1", "Imóveis", "A", "D"),
            ("1.2.3.2", "Veículos", "A", "D"), ("1.2.3.3", "Móveis e Utensílios", "A", "D"),
            ("1.2.3.4", "Equip. Informática", "A", "D"), ("1.2.4", "Intangível", "A", "D"),
            ("2", "PASSIVO", "S", "C"), ("2.1", "CIRCULANTE", "S", "C"),
            ("2.1.1", "Fornecedores", "A", "C"), ("2.1.2", "Salários a Pagar", "A", "C"),
            ("2.1.3", "Obrigações Sociais", "A", "C"), ("2.1.4", "Impostos a Recolher", "A", "C"),
            ("2.2", "NÃO CIRCULANTE", "S", "C"), ("2.2.1", "Financiamentos LP", "A", "C"),
            ("2.3", "PATRIMÔNIO LÍQUIDO", "S", "C"), ("2.3.1", "Capital Social", "A", "C"),
            ("2.3.2", "Reservas de Lucros", "A", "C"), ("2.3.3", "Lucros Acumulados", "A", "C"),
            ("3", "RECEITAS", "S", "C"), ("3.1", "RECEITA BRUTA", "S", "C"),
            ("3.1.1", "Venda de Mercadorias", "A", "C"), ("3.1.2", "Serviços", "A", "C"),
            ("3.2", "DEDUÇÕES", "S", "D"), ("3.2.1", "Devoluções", "A", "D"),
            ("3.2.2", "Impostos s/ Vendas", "A", "D"),
            ("3.3", "RECEITAS FINANCEIRAS", "S", "C"), ("3.3.1", "Juros Ativos", "A", "C"),
            ("4", "CUSTOS", "S", "D"), ("4.1", "CUSTOS OPERACIONAIS", "S", "D"),
            ("4.1.1", "CMV", "A", "D"), ("4.1.2", "CSP", "A", "D"),
            ("5", "DESPESAS", "S", "D"), ("5.1", "DESPESAS COM PESSOAL", "S", "D"),
            ("5.1.1", "Salários", "A", "D"), ("5.1.2", "Pró-Labore", "A", "D"),
            ("5.2", "ADMINISTRATIVAS", "S", "D"), ("5.2.1", "Aluguel", "A", "D"),
            ("5.2.2", "Energia", "A", "D"), ("5.2.3", "Água", "A", "D"),
            ("5.2.4", "Internet", "A", "D"), ("5.2.5", "Material Escritório", "A", "D"),
            ("5.2.6", "Manutenção", "A", "D"), ("5.2.7", "Publicidade", "A", "D"),
            ("6", "RESULTADO FINANCEIRO", "S", "D"), ("6.1", "DESPESAS FINANCEIRAS", "S", "D"),
            ("6.1.1", "Juros Passivos", "A", "D"), ("6.1.2", "Tarifas Bancárias", "A", "D")
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
        resultado[k] = {
            'nome': mapa_nome.get(k, k),
            'natureza': nat,
            'total_debito': v['deb'],
            'total_credito': v['cred'],
            'saldo': saldo
        }
    return resultado

def calcular_movimentacao_detalhada(uid):
    """Retorna movimentação detalhada por lançamento para os razonetes"""
    s = get_session()
    lancamentos = s.exec(
        select(Lancamento).where(Lancamento.usuario_id == uid)
        .order_by(Lancamento.data_lancamento)
    ).all()
    
    mapa_nome = get_mapa_nomes()
    resultado = {}
    
    for lanc in lancamentos:
        # Processa conta de débito
        if lanc.conta_debito not in resultado:
            resultado[lanc.conta_debito] = {
                'nome': mapa_nome.get(lanc.conta_debito, lanc.conta_debito),
                'lancamentos': []
            }
        resultado[lanc.conta_debito]['lancamentos'].append({
            'data': lanc.data_lancamento,
            'tipo': 'D',
            'valor': lanc.valor,
            'historico': lanc.historico,
            'conta_contrapartida': lanc.conta_credito
        })
        
        # Processa conta de crédito
        if lanc.conta_credito not in resultado:
            resultado[lanc.conta_credito] = {
                'nome': mapa_nome.get(lanc.conta_credito, lanc.conta_credito),
                'lancamentos': []
            }
        resultado[lanc.conta_credito]['lancamentos'].append({
            'data': lanc.data_lancamento,
            'tipo': 'C',
            'valor': lanc.valor,
            'historico': lanc.historico,
            'conta_contrapartida': lanc.conta_debito
        })
    
    # Calcula saldos acumulados
    for conta in resultado:
        saldo = 0
        for i, lanc in enumerate(resultado[conta]['lancamentos']):
            if lanc['tipo'] == 'D':
                saldo += lanc['valor']
            else:
                saldo -= lanc['valor']
            resultado[conta]['lancamentos'][i]['saldo_parcial'] = saldo
        resultado[conta]['saldo_final'] = saldo
        resultado[conta]['natureza'] = 'Devedora' if saldo >= 0 else 'Credora'
    
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
        if conta.startswith('3.1'):
            rec_bruta += saldo
        elif conta.startswith('3.2'):
            deducoes += saldo
        elif conta.startswith('3.3'):
            rec_financ += saldo
        elif conta.startswith('4'):
            custos += saldo
        elif conta.startswith('5'):
            despesas_op += saldo
        elif conta.startswith('6.1'):
            desp_financ += saldo
        elif conta.startswith('1'):
            ativo_total += saldo
            linha = {"Conta": f"{conta} - {d['nome']}", "Saldo": saldo}
            encaixou = False
            for pfx in ["1.2.4", "1.2.3", "1.2.1", "1.1"]:
                if conta.startswith(pfx):
                    grupos_ativo[pfx].append(linha); encaixou = True; break
            if not encaixou:
                grupos_ativo["1.1"].append(linha)
        elif conta.startswith('2'):
            passivo_total += saldo
            linha = {"Conta": f"{conta} - {d['nome']}", "Saldo": saldo}
            encaixou = False
            for pfx in ["2.3", "2.2", "2.1"]:
                if conta.startswith(pfx):
                    grupos_passivo[pfx].append(linha); encaixou = True; break
            if not encaixou:
                grupos_passivo["2.1"].append(linha)

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
        if p == user.senha or (hasattr(user, 'senha') and user.senha and user.senha.startswith('$2b$') and verificar_senha(p, user.senha)):
            st.session_state["user"] = user
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")
    else:
        st.error("Usuário ou senha incorretos.")

def logout():
    st.session_state["user"] = None
    st.rerun()

# ── TELA DE LOGIN ──────────────────────────────────────────────────────────────
if "user" not in st.session_state or not st.session_state["user"]:
    st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(135deg, #e8f4f8 0%, #d4eaf4 50%, #c8e0ef 100%) !important;
            min-height: 100vh;
        }
        [data-testid="stHeader"] { display: none !important; }
        [data-testid="stSidebar"] { display: none !important; }
        footer { display: none !important; }
        .block-container {
            padding-top: 6vh !important;
            padding-bottom: 0 !important;
            max-width: 480px !important;
        }
        .login-card {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 75, 141, 0.15), 0 4px 16px rgba(0,0,0,0.08);
            overflow: hidden;
            margin-bottom: 0;
        }
        .login-hero {
            background: linear-gradient(160deg, #d4eaf4 0%, #e8f4f8 60%, #f0f8fc 100%);
            padding: 36px 40px 28px 40px;
            text-align: center;
            border-bottom: 1px solid #e8f0f5;
        }
        .field-label {
            color: #334155;
            font-size: 0.72em;
            font-weight: 700;
            letter-spacing: 0.8px;
            text-transform: uppercase;
            margin: 14px 0 4px 0;
            display: block;
        }
        .stTextInput > div > div > input {
            border-radius: 10px !important;
            border: 1.5px solid #e2e8f0 !important;
            height: 44px !important;
            font-size: 0.92em !important;
            padding: 0 14px !important;
            background: #f8fafc !important;
            color: #1e293b !important;
            transition: all 0.2s !important;
        }
        .stTextInput > div > div > input:focus {
            border-color: #004b8d !important;
            background: white !important;
            box-shadow: 0 0 0 3px rgba(0, 75, 141, 0.10) !important;
        }
        .stTextInput > div > div > input::placeholder { color: #94a3b8 !important; }
        .stTextInput label { display: none !important; }
        .stFormSubmitButton > button {
            height: 48px !important;
            font-size: 0.95em !important;
            font-weight: 700 !important;
            letter-spacing: 1px !important;
            border-radius: 10px !important;
            background: linear-gradient(135deg, #004b8d 0%, #0066c0 100%) !important;
            border: none !important;
            margin-top: 20px !important;
            box-shadow: 0 4px 14px rgba(0, 75, 141, 0.35) !important;
            transition: all 0.2s !important;
        }
        .stFormSubmitButton > button:hover {
            background: linear-gradient(135deg, #003d75 0%, #0055a0 100%) !important;
            box-shadow: 0 6px 20px rgba(0, 75, 141, 0.45) !important;
            transform: translateY(-1px) !important;
        }
        [data-testid="stForm"] {
            border: none !important;
            padding: 0 !important;
            background: transparent !important;
        }
    </style>
    """, unsafe_allow_html=True)

    logo_b64 = get_image_base64("assets/logo.png")
    if logo_b64:
        img_tag = f"<img src='data:image/png;base64,{logo_b64}' style='width:140px;max-width:75%;filter:drop-shadow(0 6px 16px rgba(0,75,141,0.18));'>"
    else:
        img_tag = "<div style='font-size:5rem;'>🦅</div>"

    st.markdown(f"""
    <div class='login-card'>
        <div class='login-hero'>
            {img_tag}
        </div>
    """, unsafe_allow_html=True)

    with st.form("login_form", clear_on_submit=True):
        st.markdown("<span class='field-label'>👤 Login de acesso</span>", unsafe_allow_html=True)
        st.text_input("u", key="u_log", placeholder="Digite seu usuário", label_visibility="collapsed")
        st.text_input("p", type="password", key="u_pass", placeholder="Digite sua senha", label_visibility="collapsed")
        submitted = st.form_submit_button("ENTRAR", type="primary", use_container_width=True)
        if submitted:
            login()

    st.markdown("""
    <div style='text-align:center;margin-top:20px;color:#94a3b8;font-size:0.75em;line-height:1.6;'>
        Plataforma para o ensino da contabilidade<br>
        Todos os direitos reservados · Versão 5.0
    </div>
    """, unsafe_allow_html=True)

    st.stop()

# ==============================================================================
# 5. PÓS-LOGIN: sessão e termos
# ==============================================================================
session = get_session()
try:
    me = session.get(Usuario, st.session_state["user"].id)
except:
    logout(); st.stop()

if not me.termos_aceitos:
    st.write(""); st.write("")
    c1, c2, c3 = st.columns([1, 4, 1])
    with c2:
        st.markdown("""<div class="legal-box">
            <h4>⚠️ POLÍTICA DE USO E PRIVACIDADE</h4>
            <p>Este sistema é um ambiente de simulação acadêmica (Sandbox),
            desenvolvido estritamente para fins pedagógicos.</p>
            <p><b>1. Dados Proibidos:</b> Em conformidade com a LGPD, é terminantemente
            <b>PROIBIDA</b> a inserção de dados verídicos.</p>
        </div>""", unsafe_allow_html=True)
        if st.button("✅ Li e Concordo com os Termos", type="primary", use_container_width=True):
            me.termos_aceitos = True; session.add(me); session.commit(); st.rerun()
    st.stop()

# ==============================================================================
# 6. MENU LATERAL
# ==============================================================================
with st.sidebar:
    try: st.image("assets/logo.png", width=100)
    except: pass
    st.write(f"Olá, **{me.nome.split()[0]}**")
    st.caption(f"Perfil: {me.perfil.replace('admin', 'Administrador').upper()}")

    opts = ["Dashboard", "Meu Perfil"]
    if me.perfil == 'admin':
        opts.extend(["Escolas", "Professores", "Turmas", "Alunos",
                     "Escrituração e Diário", "Razonetes", "Balancete", "DRE", "Balanço"])
    elif me.perfil == 'professor':
        opts.extend(["Minhas Turmas", "Meus Alunos", "Postar Aulas",
                     "Escrituração e Diário", "Razonetes", "Balancete", "DRE", "Balanço"])
    elif me.perfil == 'aluno':
        opts.extend(["Minhas Aulas", "Escrituração e Diário",
                     "Razonetes", "Balancete", "DRE", "Balanço"])

    menu = st.sidebar.radio("Navegação", opts, label_visibility="collapsed")
    st.markdown("---")
    if st.button("🚪 Sair do Sistema", use_container_width=True): logout()

# ==============================================================================
# 7. CONTEÚDO
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
        st.divider()
        st.subheader("🎯 Suas Turmas")
        if minhas_turmas:
            col1, col2 = st.columns(2)
            for idx, turma in enumerate(minhas_turmas):
                alunos_na_turma = session.exec(select(Usuario).where(Usuario.turma_id == turma.id)).all()
                aulas_turma = session.exec(select(Aula).where(Aula.turma_id == turma.id)).all()
                col = col1 if idx % 2 == 0 else col2
                with col.container(border=True):
                    col.write(f"**{turma.nome}**")
                    col.caption(f"Ano: {turma.ano_letivo}")
                    col.metric("Alunos", len(alunos_na_turma))
                    col.metric("Aulas", len(aulas_turma))
        else:
            st.info("Você ainda não tem turmas. Acesse 'Minhas Turmas' para criar uma!")
        st.divider()
        st.subheader("📖 Últimas Aulas Postadas")
        aulas_recentes = session.exec(select(Aula).where(Aula.professor_id == me.id).order_by(desc(Aula.data_postagem))).all()[:5]
        if aulas_recentes:
            for aula in aulas_recentes:
                turma_aula = session.get(Turma, aula.turma_id)
                with st.container(border=True):
                    st.write(f"**{aula.titulo}**")
                    st.caption(f"📚 {turma_aula.nome if turma_aula else '?'} • 📅 {formatar_data_br(aula.data_postagem)}")
                    st.write(f"_{aula.descricao[:80]}..._" if len(aula.descricao) > 80 else f"_{aula.descricao}_")
        else:
            st.info("Você ainda não postou nenhuma aula.")
    elif me.perfil == 'aluno':
        _, _, rec, luc, _, _, _, _, _ = gerar_demonstrativos(me.id)
        c1, c2 = st.columns(2)
        c1.markdown(f"<div class='kpi-card'><div class='kpi-title'>Receita Bruta</div><div class='kpi-val' style='color:green'>{fmt_moeda(rec)}</div></div>", unsafe_allow_html=True)
        cor_luc = 'green' if luc >= 0 else 'red'
        c2.markdown(f"<div class='kpi-card'><div class='kpi-title'>Resultado Líquido</div><div class='kpi-val' style='color:{cor_luc}'>{fmt_moeda(luc)}</div></div>", unsafe_allow_html=True)
        if me.turma_id:
            turma = session.get(Turma, me.turma_id)
            aulas_turma = session.exec(select(Aula).where(Aula.turma_id == me.turma_id)).all()
            st.divider()
            st.subheader("📚 Sua Turma e Aulas")
            c1, c2 = st.columns(2)
            c1.metric("Turma", turma.nome if turma else "?")
            c2.metric("Aulas Disponíveis", len(aulas_turma))
    if me.perfil != 'professor':
        st.divider()
        st.subheader("📚 Plano de Contas Geral")
        contas_db = session.exec(select(ContaContabil).order_by(ContaContabil.codigo)).all()
        df_contas = pd.DataFrame([{"Código": c.codigo, "Nome": c.nome, "Tipo": "Analítica" if c.tipo == 'A' else "Sintética", "Natureza": c.natureza} for c in contas_db])
        st.dataframe(df_contas, use_container_width=True, hide_index=True)

elif menu == "Meu Perfil":
    st.header("👤 Meu Perfil")
    with st.form("myprofile"):
        n = st.text_input("Meu Nome", value=me.nome)
        s = st.text_input("Minha Senha", value="", type="password", placeholder="Digite nova senha (opcional)")
        if me.perfil == 'professor' and me.escola_id:
            escola = session.get(Escola, me.escola_id)
            st.selectbox("Escola vinculada", [escola], format_func=lambda x: x.nome, disabled=True)
        if st.form_submit_button("💾 Atualizar", type="primary", use_container_width=True):
            me.nome = n
            if s:
                me.senha = hash_senha(s)
            session.add(me); session.commit()
            st.success("Perfil atualizado!")
            st.rerun()

# ==============================================================================
# ESCRITURAÇÃO E DIÁRIO
# ==============================================================================
elif menu == "Escrituração e Diário":
    st.header("📝 Escrituração")
    mapa = get_contas_analiticas()
    if not mapa:
        st.error("Nenhuma conta contábil encontrada. Contate o administrador.")
        st.stop()
    
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
        gravar = st.form_submit_button("✅ Gravar Lançamento", type="primary", use_container_width=True)
    
    if gravar:
        if db and cr:
            if db == cr:
                st.error("❌ As contas de débito e crédito não podem ser iguais!")
            else:
                try:
                    session.add(Lancamento(
                        data_lancamento=d,
                        valor=v,
                        historico=h,
                        conta_debito=db.split(" - ")[0],
                        conta_credito=cr.split(" - ")[0],
                        usuario_id=me.id
                    ))
                    session.commit()
                    st.success("✅ Lançamento gravado com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro ao gravar lançamento: {str(e)}")
        else:
            st.warning("⚠️ Selecione as contas de Débito e Crédito antes de gravar.")

    # Listar lançamentos
    lancs = session.exec(
        select(Lancamento).where(Lancamento.usuario_id == me.id)
        .order_by(desc(Lancamento.data_lancamento))
    ).all()
    
    if lancs:
        mapa_nomes = get_mapa_nomes()
        st.divider()
        st.subheader("📋 Lançamentos Registrados")
        
        if 'editando_lancamento' not in st.session_state:
            st.session_state.editando_lancamento = None
        
        def salvar_edicao(lanc_id, nova_data, novo_debito, novo_credito, novo_valor, novo_historico):
            with get_session() as s:
                lanc = s.get(Lancamento, lanc_id)
                if lanc:
                    lanc.data_lancamento = nova_data
                    lanc.conta_debito = novo_debito.split(" - ")[0]
                    lanc.conta_credito = novo_credito.split(" - ")[0]
                    lanc.valor = novo_valor
                    lanc.historico = novo_historico
                    s.add(lanc)
                    s.commit()
                    st.success("✅ Lançamento editado!")
                    st.session_state.editando_lancamento = None
                    st.rerun()
        
        def cancelar_edicao():
            st.session_state.editando_lancamento = None
            st.rerun()
        
        for lanc in lancs:
            with st.container(border=True):
                col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1.5, 1])
                
                with col1:
                    st.write(f"📅 {formatar_data_br(lanc.data_lancamento)}")
                with col2:
                    st.write(f"💳 **Débito:** {lanc.conta_debito} - {mapa_nomes.get(lanc.conta_debito, '')}")
                with col3:
                    st.write(f"💰 **Crédito:** {lanc.conta_credito} - {mapa_nomes.get(lanc.conta_credito, '')}")
                with col4:
                    st.write(f"💵 **Valor:** {fmt_moeda(lanc.valor)}")
                with col5:
                    if st.button("✏️", key=f"edit_{lanc.id}"):
                        st.session_state.editando_lancamento = lanc.id
                    if st.button("🗑️", key=f"del_{lanc.id}"):
                        session.delete(lanc)
                        session.commit()
                        st.rerun()
                
                if lanc.historico:
                    st.caption(f"📝 {lanc.historico}")
                
                if st.session_state.editando_lancamento == lanc.id:
                    st.markdown("---")
                    st.markdown("**✏️ Editando Lançamento**")
                    col1, col2 = st.columns(2)
                    with col1:
                        nova_data = st.date_input("Data", value=lanc.data_lancamento, key=f"data_{lanc.id}")
                        novo_debito = st.selectbox("Débito", contas, 
                            index=contas.index(f"{lanc.conta_debito} - {mapa_nomes.get(lanc.conta_debito, '')}") 
                            if f"{lanc.conta_debito} - {mapa_nomes.get(lanc.conta_debito, '')}" in contas else 0,
                            key=f"deb_{lanc.id}")
                        novo_valor = st.number_input("Valor", value=lanc.valor, min_value=0.01, key=f"val_{lanc.id}")
                    with col2:
                        novo_credito = st.selectbox("Crédito", contas,
                            index=contas.index(f"{lanc.conta_credito} - {mapa_nomes.get(lanc.conta_credito, '')}")
                            if f"{lanc.conta_credito} - {mapa_nomes.get(lanc.conta_credito, '')}" in contas else 0,
                            key=f"cred_{lanc.id}")
                        novo_historico = st.text_area("Histórico", value=lanc.historico or "", key=f"hist_{lanc.id}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("💾 Salvar", key=f"save_{lanc.id}"):
                            salvar_edicao(lanc.id, nova_data, novo_debito, novo_credito, novo_valor, novo_historico)
                    with col2:
                        if st.button("❌ Cancelar", key=f"cancel_{lanc.id}"):
                            cancelar_edicao()
        
        botao_imprimir(menu, me, session)

# ==============================================================================
# MINHAS TURMAS (PROFESSOR)
# ==============================================================================
elif menu == "Minhas Turmas":
    st.header("🏫 Minhas Turmas")
    
    if me.perfil == 'professor':
        minhas_turmas = session.exec(select(Turma).where(Turma.professor_id == me.id)).all()
        
        st.info(f"📌 Professor: **{me.nome}**")
        
        st.subheader("➕ Criar Nova Turma")
        with st.form("nova_turma", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nome_turma = st.text_input("Nome da turma", placeholder="Ex: 3º Ano A - Contabilidade")
            with col2:
                ano_letivo = st.text_input("Ano letivo", value=str(date.today().year))
            criar = st.form_submit_button("📌 Criar Turma", use_container_width=True)
        
        if criar:
            if nome_turma and ano_letivo:
                escola_id = me.escola_id if me.escola_id else 1
                nova_turma = Turma(
                    nome=nome_turma,
                    ano_letivo=ano_letivo,
                    professor_id=me.id,
                    escola_id=escola_id
                )
                session.add(nova_turma)
                session.commit()
                st.success(f"✅ Turma '{nome_turma}' criada!")
                st.rerun()
            else:
                st.warning("⚠️ Preencha o nome da turma e o ano letivo.")
        
        st.divider()
        st.subheader(f"📚 Minhas Turmas ({len(minhas_turmas)})")
        
        if minhas_turmas:
            for turma in minhas_turmas:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        st.markdown(f"**📖 {turma.nome}**")
                        st.caption(f"📅 {turma.ano_letivo}")
                        st.caption(f"🆔 ID: {turma.id}")
                    
                    with col2:
                        alunos_turma = session.exec(select(Usuario).where(Usuario.turma_id == turma.id)).all()
                        st.metric("👨‍🎓 Alunos", len(alunos_turma))
                        
                        aulas_turma = session.exec(select(Aula).where(Aula.turma_id == turma.id)).all()
                        st.metric("📹 Aulas", len(aulas_turma))
                    
                    with col3:
                        if len(alunos_turma) == 0:
                            if st.button("🗑️ Excluir", key=f"del_{turma.id}"):
                                session.delete(turma)
                                session.commit()
                                st.rerun()
                        else:
                            st.info(f"⚠️ {len(alunos_turma)} alunos")
                    
                    with st.expander("🔍 Ver alunos"):
                        if alunos_turma:
                            for aluno in alunos_turma:
                                st.write(f"- {aluno.nome} (@{aluno.username})")
                        else:
                            st.info("Nenhum aluno matriculado")
        else:
            st.info("📭 Nenhuma turma criada ainda.")
    
    elif me.perfil == 'admin':
        st.info("👑 Acesse o menu 'Turmas' para gerenciar todas as turmas.")
        todas_turmas = session.exec(select(Turma)).all()
        if todas_turmas:
            st.metric("Total de Turmas", len(todas_turmas))
    else:
        st.warning("⚠️ Esta seção é apenas para professores.")

# ==============================================================================
# MEUS ALUNOS (PROFESSOR)
# ==============================================================================
elif menu == "Meus Alunos":
    st.header("👥 Meus Alunos")
    
    if me.perfil == 'professor':
        minhas_turmas = session.exec(select(Turma).where(Turma.professor_id == me.id)).all()
        
        if not minhas_turmas:
            st.error("❌ Você não tem turmas. Crie uma em 'Minhas Turmas' primeiro!")
        else:
            st.subheader("➕ Matricular Aluno")
            with st.form("matricular", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    nome_aluno = st.text_input("Nome completo", placeholder="Ex: João Silva")
                    login_aluno = st.text_input("Login", placeholder="joao.silva")
                with col2:
                    turma_sel = st.selectbox("Turma", minhas_turmas, format_func=lambda x: f"{x.nome} ({x.ano_letivo})")
                    st.caption("Senha inicial: **123**")
                
                matricular = st.form_submit_button("✅ Matricular", use_container_width=True)
            
            if matricular:
                if nome_aluno and login_aluno:
                    existe = session.exec(select(Usuario).where(Usuario.username == login_aluno)).first()
                    if existe:
                        st.error("❌ Login já existe!")
                    else:
                        novo_aluno = Usuario(
                            nome=nome_aluno,
                            username=login_aluno,
                            senha=hash_senha("123"),
                            perfil="aluno",
                            turma_id=turma_sel.id,
                            criado_por_id=me.id
                        )
                        session.add(novo_aluno)
                        session.commit()
                        st.success(f"✅ Aluno {nome_aluno} matriculado!")
                        st.rerun()
                else:
                    st.warning("⚠️ Preencha nome e login.")
            
            st.divider()
            st.subheader("📋 Alunos Matriculados")
            
            turmas_ids = [t.id for t in minhas_turmas]
            alunos = session.exec(
                select(Usuario).where(Usuario.perfil == 'aluno').where(Usuario.turma_id.in_(turmas_ids))
            ).all()
            
            if alunos:
                turmas_dict = {t.id: f"{t.nome} ({t.ano_letivo})" for t in minhas_turmas}
                for aluno in alunos:
                    with st.container(border=True):
                        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                        with col1:
                            st.write(f"**{aluno.nome}**")
                            st.caption(f"👤 @{aluno.username}")
                        with col2:
                            st.write(f"📚 {turmas_dict.get(aluno.turma_id, '—')}")
                        with col3:
                            st.caption(f"📅 {formatar_data_br(aluno.data_criacao)}")
                        with col4:
                            if st.button("🗑️", key=f"del_{aluno.id}"):
                                session.delete(aluno)
                                session.commit()
                                st.rerun()
            else:
                st.info("📭 Nenhum aluno matriculado.")
    else:
        st.warning("⚠️ Esta seção é apenas para professores.")

# ==============================================================================
# POSTAR AULAS (PROFESSOR)
# ==============================================================================
elif menu == "Postar Aulas":
    st.header("📹 Postar Aulas")
    
    if me.perfil == 'professor':
        minhas_turmas = session.exec(select(Turma).where(Turma.professor_id == me.id)).all()
        
        if not minhas_turmas:
            st.error("❌ Você não tem turmas. Crie uma em 'Minhas Turmas' primeiro!")
        else:
            st.subheader("📝 Nova Aula")
            with st.form("postar", clear_on_submit=True):
                turma_sel = st.selectbox("Turma", minhas_turmas, format_func=lambda x: f"{x.nome} ({x.ano_letivo})")
                titulo = st.text_input("Título da aula", placeholder="Ex: Introdução à Contabilidade")
                descricao = st.text_area("Descrição", placeholder="Descreva o conteúdo da aula...")
                arquivo = st.file_uploader("Anexar arquivo", type=["pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "txt", "jpg", "png"])
                
                publicar = st.form_submit_button("📤 Publicar Aula", use_container_width=True)
            
            if publicar:
                if titulo and descricao:
                    arquivo_blob = arquivo.read() if arquivo else None
                    nova_aula = Aula(
                        titulo=titulo,
                        descricao=descricao,
                        arquivo_blob=arquivo_blob,
                        nome_arquivo=arquivo.name if arquivo else None,
                        professor_id=me.id,
                        turma_id=turma_sel.id
                    )
                    session.add(nova_aula)
                    session.commit()
                    st.success(f"✅ Aula '{titulo}' publicada!")
                    st.rerun()
                else:
                    st.warning("⚠️ Preencha título e descrição.")
            
            st.divider()
            st.subheader("📚 Aulas Publicadas")
            
            aulas = session.exec(select(Aula).where(Aula.professor_id == me.id).order_by(desc(Aula.data_postagem))).all()
            if aulas:
                turmas_dict = {t.id: t.nome for t in minhas_turmas}
                for aula in aulas:
                    with st.container(border=True):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**{aula.titulo}**")
                            st.caption(f"📚 {turmas_dict.get(aula.turma_id, '?')} • 📅 {formatar_data_br(aula.data_postagem)}")
                            st.write(aula.descricao[:100] + "..." if len(aula.descricao) > 100 else aula.descricao)
                        with col2:
                            if aula.arquivo_blob and aula.nome_arquivo:
                                st.download_button("⬇️ Download", data=aula.arquivo_blob, file_name=aula.nome_arquivo, key=f"dl_{aula.id}")
                            if st.button("🗑️ Excluir", key=f"del_{aula.id}"):
                                session.delete(aula)
                                session.commit()
                                st.rerun()
            else:
                st.info("📭 Nenhuma aula publicada ainda.")
    else:
        st.warning("⚠️ Esta seção é apenas para professores.")

# ==============================================================================
# MINHAS AULAS (ALUNO)
# ==============================================================================
elif menu == "Minhas Aulas":
    st.header("📚 Minhas Aulas")
    
    if me.perfil == 'aluno':
        if not me.turma_id:
            st.warning("⚠️ Você não está matriculado em nenhuma turma.")
        else:
            turma = session.get(Turma, me.turma_id)
            if turma:
                st.subheader(f"Aulas da Turma: {turma.nome}")
                aulas = session.exec(select(Aula).where(Aula.turma_id == me.turma_id).order_by(desc(Aula.data_postagem))).all()
                
                if aulas:
                    for aula in aulas:
                        with st.container(border=True):
                            professor = session.get(Usuario, aula.professor_id)
                            st.write(f"**{aula.titulo}**")
                            st.caption(f"👨‍🏫 {professor.nome if professor else '?'} • 📅 {formatar_data_br(aula.data_postagem)}")
                            st.write(aula.descricao)
                            if aula.arquivo_blob and aula.nome_arquivo:
                                st.download_button("⬇️ Baixar Material", data=aula.arquivo_blob, file_name=aula.nome_arquivo, key=f"aluno_dl_{aula.id}")
                else:
                    st.info("📭 Nenhuma aula disponível ainda.")
            else:
                st.error("Turma não encontrada.")
    else:
        st.warning("⚠️ Esta seção é apenas para alunos.")

# ==============================================================================
# ESCOLAS, PROFESSORES, TURMAS, ALUNOS (ADMIN)
# ==============================================================================
elif menu == "Escolas":
    st.header("🏢 Escolas")
    
    st.subheader("➕ Nova Escola")
    with st.form("nova_escola", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nome_escola = st.text_input("Nome da escola")
        with col2:
            cidade = st.text_input("Cidade")
        salvar = st.form_submit_button("💾 Salvar", use_container_width=True)
    
    if salvar:
        if nome_escola and cidade:
            session.add(Escola(nome=nome_escola, cidade=cidade))
            session.commit()
            st.success(f"✅ Escola '{nome_escola}' cadastrada!")
            st.rerun()
        else:
            st.warning("⚠️ Preencha todos os campos.")
    
    st.divider()
    st.subheader("📋 Escolas Cadastradas")
    
    escolas = session.exec(select(Escola)).all()
    if escolas:
        for escola in escolas:
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 2, 1])
                col1.write(f"**{escola.nome}**")
                col1.caption(f"📍 {escola.cidade}")
                col2.write(f"ID: {escola.id}")
                if col3.button("🗑️", key=f"del_escola_{escola.id}"):
                    # Verificar se tem professores vinculados
                    profs = session.exec(select(Usuario).where(Usuario.escola_id == escola.id).where(Usuario.perfil == 'professor')).all()
                    if profs:
                        st.error(f"❌ Escola tem {len(profs)} professor(es) vinculado(s).")
                    else:
                        session.delete(escola)
                        session.commit()
                        st.rerun()
    else:
        st.info("📭 Nenhuma escola cadastrada.")

elif menu == "Professores":
    st.header("👨‍🏫 Professores")
    
    escolas = session.exec(select(Escola)).all()
    if not escolas:
        st.warning("⚠️ Cadastre uma escola primeiro!")
    else:
        st.subheader("➕ Novo Professor")
        with st.form("novo_professor", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nome_prof = st.text_input("Nome completo")
                login_prof = st.text_input("Login")
            with col2:
                escola_prof = st.selectbox("Escola", escolas, format_func=lambda x: f"{x.nome} - {x.cidade}")
                st.caption("Senha inicial: **123**")
            salvar = st.form_submit_button("💾 Cadastrar", use_container_width=True)
        
        if salvar:
            if nome_prof and login_prof:
                existe = session.exec(select(Usuario).where(Usuario.username == login_prof)).first()
                if existe:
                    st.error("❌ Login já existe!")
                else:
                    session.add(Usuario(
                        nome=nome_prof,
                        username=login_prof,
                        senha=hash_senha("123"),
                        perfil="professor",
                        escola_id=escola_prof.id,
                        criado_por_id=me.id
                    ))
                    session.commit()
                    st.success(f"✅ Professor '{nome_prof}' cadastrado!")
                    st.rerun()
            else:
                st.warning("⚠️ Preencha todos os campos.")
    
    st.divider()
    st.subheader("📋 Professores Cadastrados")
    
    profs = session.exec(select(Usuario).where(Usuario.perfil == 'professor')).all()
    if profs:
        escola_map = {e.id: f"{e.nome} - {e.cidade}" for e in escolas}
        for prof in profs:
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                col1.write(f"**{prof.nome}**")
                col1.caption(f"👤 @{prof.username}")
                col2.write(f"🏫 {escola_map.get(prof.escola_id, '—')}")
                turmas_prof = session.exec(select(Turma).where(Turma.professor_id == prof.id)).all()
                col3.caption(f"📚 {len(turmas_prof)} turma(s)")
                if col4.button("🗑️", key=f"del_prof_{prof.id}"):
                    if turmas_prof:
                        st.error(f"❌ Professor tem {len(turmas_prof)} turma(s).")
                    else:
                        session.delete(prof)
                        session.commit()
                        st.rerun()
    else:
        st.info("📭 Nenhum professor cadastrado.")

elif menu == "Turmas":
    st.header("🏫 Turmas")
    
    professores = session.exec(select(Usuario).where(Usuario.perfil == 'professor')).all()
    if not professores:
        st.warning("⚠️ Cadastre um professor primeiro!")
    else:
        st.subheader("➕ Nova Turma")
        with st.form("nova_turma_admin", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nome_turma = st.text_input("Nome da turma")
                ano_letivo = st.text_input("Ano letivo", value=str(date.today().year))
            with col2:
                professor_turma = st.selectbox("Professor", professores, format_func=lambda x: x.nome)
            salvar = st.form_submit_button("💾 Criar", use_container_width=True)
        
        if salvar:
            if nome_turma and ano_letivo:
                escola_id = professor_turma.escola_id if professor_turma.escola_id else 1
                session.add(Turma(
                    nome=nome_turma,
                    ano_letivo=ano_letivo,
                    professor_id=professor_turma.id,
                    escola_id=escola_id
                ))
                session.commit()
                st.success(f"✅ Turma '{nome_turma}' criada!")
                st.rerun()
            else:
                st.warning("⚠️ Preencha todos os campos.")
    
    st.divider()
    st.subheader("📋 Turmas Cadastradas")
    
    turmas = session.exec(select(Turma)).all()
    if turmas:
        prof_map = {p.id: p.nome for p in professores}
        for turma in turmas:
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                col1.write(f"**{turma.nome}**")
                col1.caption(f"📅 {turma.ano_letivo}")
                col2.write(f"👨‍🏫 {prof_map.get(turma.professor_id, '—')}")
                alunos_turma = session.exec(select(Usuario).where(Usuario.turma_id == turma.id)).all()
                col3.caption(f"🎓 {len(alunos_turma)} aluno(s)")
                if col4.button("🗑️", key=f"del_turma_{turma.id}"):
                    if alunos_turma:
                        st.error(f"❌ Turma tem {len(alunos_turma)} aluno(s).")
                    else:
                        session.delete(turma)
                        session.commit()
                        st.rerun()
    else:
        st.info("📭 Nenhuma turma cadastrada.")

elif menu == "Alunos":
    st.header("🎓 Alunos")
    
    turmas = session.exec(select(Turma)).all()
    if not turmas:
        st.warning("⚠️ Cadastre uma turma primeiro!")
    else:
        st.subheader("➕ Novo Aluno")
        with st.form("novo_aluno_admin", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nome_aluno = st.text_input("Nome completo")
                login_aluno = st.text_input("Login")
            with col2:
                turma_aluno = st.selectbox("Turma", turmas, format_func=lambda x: f"{x.nome} ({x.ano_letivo})")
                st.caption("Senha inicial: **123**")
            salvar = st.form_submit_button("💾 Matricular", use_container_width=True)
        
        if salvar:
            if nome_aluno and login_aluno:
                existe = session.exec(select(Usuario).where(Usuario.username == login_aluno)).first()
                if existe:
                    st.error("❌ Login já existe!")
                else:
                    session.add(Usuario(
                        nome=nome_aluno,
                        username=login_aluno,
                        senha=hash_senha("123"),
                        perfil="aluno",
                        turma_id=turma_aluno.id,
                        criado_por_id=me.id
                    ))
                    session.commit()
                    st.success(f"✅ Aluno '{nome_aluno}' matriculado!")
                    st.rerun()
            else:
                st.warning("⚠️ Preencha todos os campos.")
    
    st.divider()
    st.subheader("📋 Alunos Matriculados")
    
    alunos = session.exec(select(Usuario).where(Usuario.perfil == 'aluno')).all()
    if alunos:
        turma_map = {t.id: f"{t.nome} ({t.ano_letivo})" for t in turmas}
        for aluno in alunos:
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                col1.write(f"**{aluno.nome}**")
                col1.caption(f"👤 @{aluno.username}")
                col2.write(f"📚 {turma_map.get(aluno.turma_id, '—')}")
                col3.caption(f"📅 {formatar_data_br(aluno.data_criacao)}")
                if col4.button("🗑️", key=f"del_aluno_{aluno.id}"):
                    session.delete(aluno)
                    session.commit()
                    st.rerun()
    else:
        st.info("📭 Nenhum aluno matriculado.")

# ==============================================================================
# RAZONETES, BALANCETE, DRE, BALANÇO (MANTIDOS)
# ==============================================================================
elif menu == "Razonetes":
    st.header("🗂️ Razonetes")
    
    mov = calcular_movimentacao(me.id)
    if not mov:
        st.info("📭 Nenhuma movimentação encontrada.")
    else:
        cols = st.columns(2)
        i = 0
        for k, v in sorted(mov.items()):
            html = f"""
            <div class='razonete-container'>
                <div class='razonete-header'>{k} - {v['nome']}</div>
                <div style='display:flex;background:#f8f9fa;border-bottom:1px solid #e0e0e0;'>
                    <div style='width:50%;text-align:center;padding:4px 6px;font-weight:700;color:#c0392b;'>DÉBITO</div>
                    <div style='width:50%;text-align:center;padding:4px 6px;font-weight:700;color:#27ae60;'>CRÉDITO</div>
                </div>
                <div class='razonete-body'>
                    <div class='col-debito'>{fmt_moeda(v['total_debito'])}</div>
                    <div class='col-credito'>{fmt_moeda(v['total_credito'])}</div>
                </div>
                <div style='padding:10px;text-align:center;background:#f8f9fa;border-top:1px solid #ddd;'>
                    <strong>Saldo: {fmt_moeda(v['saldo'])}</strong> ({'Devedor' if v['saldo'] >= 0 else 'Credor'})
                </div>
            </div>
            """
            cols[i % 2].markdown(html, unsafe_allow_html=True)
            i += 1
    
    botao_imprimir(menu, me, session)

elif menu == "Balancete":
    st.header("⚖️ Balancete")
    
    mov = calcular_movimentacao(me.id)
    if not mov:
        st.info("📭 Nenhuma movimentação encontrada.")
    else:
        dados_tabela = []
        total_debito = 0
        total_credito = 0
        
        for k, v in sorted(mov.items()):
            dados_tabela.append({
                "Conta": f"{k} - {v['nome']}",
                "Débito": fmt_moeda(v['total_debito']),
                "Crédito": fmt_moeda(v['total_credito']),
                "Saldo": fmt_moeda(v['saldo'])
            })
            total_debito += v['total_debito']
            total_credito += v['total_credito']
        
        st.dataframe(pd.DataFrame(dados_tabela), use_container_width=True, hide_index=True)
        
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💰 TOTAL DÉBITOS", fmt_moeda(total_debito))
        with col2:
            st.metric("💰 TOTAL CRÉDITOS", fmt_moeda(total_credito))
        with col3:
            diferenca = total_debito - total_credito
            st.metric("📊 DIFERENÇA", fmt_moeda(abs(diferenca)), 
                     delta="Equilibrado" if abs(diferenca) < 0.01 else "Desequilibrado")
        
        if abs(total_debito - total_credito) > 0.01:
            st.warning("⚠️ Balancete desequilibrado!")
        else:
            st.success("✅ Balancete equilibrado!")
    
    botao_imprimir(menu, me, session)

elif menu == "DRE":
    st.header("📉 Demonstração do Resultado do Exercício")
    
    with st.spinner("🔄 Calculando DRE..."):
        mov = calcular_movimentacao(me.id)
    
    receitas = 0
    deducoes = 0
    custos = 0
    despesas = 0
    receitas_fin = 0
    despesas_fin = 0
    
    for codigo, dados in mov.items():
        saldo = dados['saldo']
        if codigo.startswith('3.1'):
            receitas += saldo
        elif codigo.startswith('3.2'):
            deducoes += abs(saldo)
        elif codigo.startswith('3.3'):
            receitas_fin += saldo
        elif codigo.startswith('4'):
            custos += abs(saldo)
        elif codigo.startswith('5'):
            despesas += abs(saldo)
        elif codigo.startswith('6.1'):
            despesas_fin += abs(saldo)
    
    receita_liquida = receitas - deducoes
    lucro_bruto = receita_liquida - custos
    resultado_op = lucro_bruto - despesas
    resultado_final = resultado_op + receitas_fin - despesas_fin
    
    st.markdown(f"""
    <div style='background:white; border-radius:10px; padding:20px; margin:10px 0;'>
        <p><strong>(+) Receita Operacional Bruta</strong> <span style='float:right'>{fmt_moeda(receitas)}</span></p>
        <p><strong>(-) Deduções da Receita</strong> <span style='float:right'>{fmt_moeda(deducoes)}</span></p>
        <p style='background:#e3f2fd; padding:8px; border-radius:5px;'><strong>(=) Receita Operacional Líquida</strong> <span style='float:right'>{fmt_moeda(receita_liquida)}</span></p>
        <p><strong>(-) Custos (CMV/CSP)</strong> <span style='float:right'>{fmt_moeda(custos)}</span></p>
        <p style='background:#e8f5e9; padding:8px; border-radius:5px;'><strong>(=) Lucro Bruto</strong> <span style='float:right'>{fmt_moeda(lucro_bruto)}</span></p>
        <p><strong>(-) Despesas Operacionais</strong> <span style='float:right'>{fmt_moeda(despesas)}</span></p>
        <p style='background:#fff3e0; padding:8px; border-radius:5px;'><strong>(=) Resultado Operacional</strong> <span style='float:right'>{fmt_moeda(resultado_op)}</span></p>
        <p><strong>(+) Receitas Financeiras</strong> <span style='float:right'>{fmt_moeda(receitas_fin)}</span></p>
        <p><strong>(-) Despesas Financeiras</strong> <span style='float:right'>{fmt_moeda(despesas_fin)}</span></p>
        <div style='background:linear-gradient(135deg,#004b8d,#0066c0); color:white; padding:15px; border-radius:10px; margin-top:15px; text-align:center;'>
            <h3 style='margin:0;'>(=) Resultado Líquido do Exercício</h3>
            <h2 style='margin:5px 0 0; color:{"#4caf50" if resultado_final >= 0 else "#f44336"};'>{fmt_moeda(resultado_final)}</h2>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    botao_imprimir(menu, me, session)

elif menu == "Balanço":
    st.header("🏛️ Balanço Patrimonial")
    
    at, pas, _, _, grupos_a, grupos_p, _, nomes_a, nomes_p = gerar_demonstrativos(me.id)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("<div class='report-header'>ATIVO</div>", unsafe_allow_html=True)
        total_ativo = 0
        for grupo in sorted(grupos_a.keys()):
            linhas = grupos_a[grupo]
            if linhas:
                st.markdown(f"**{nomes_a.get(grupo, grupo)}**")
                for item in linhas:
                    st.write(f"&nbsp;&nbsp;• {item['Conta']}: {item['Saldo']}")
                subtotal = sum(l['Saldo'] for l in linhas)
                st.caption(f"Subtotal: {fmt_moeda(subtotal)}")
                total_ativo += subtotal
                st.markdown("---")
        st.markdown(f"### Total do Ativo: {fmt_moeda(total_ativo)}")
    
    with col2:
        st.markdown("<div class='report-header'>PASSIVO + PL</div>", unsafe_allow_html=True)
        total_passivo = 0
        for grupo in sorted(grupos_p.keys()):
            linhas = grupos_p[grupo]
            if linhas:
                st.markdown(f"**{nomes_p.get(grupo, grupo)}**")
                for item in linhas:
                    st.write(f"&nbsp;&nbsp;• {item['Conta']}: {item['Saldo']}")
                subtotal = sum(l['Saldo'] for l in linhas)
                st.caption(f"Subtotal: {fmt_moeda(subtotal)}")
                total_passivo += subtotal
                st.markdown("---")
        st.markdown(f"### Total do Passivo + PL: {fmt_moeda(total_passivo)}")
    
    if abs(total_ativo - total_passivo) < 0.01:
        st.success("✅ Balanço equilibrado! Ativo = Passivo + PL")
    else:
        st.error(f"⚠️ Diferença de {fmt_moeda(total_ativo - total_passivo)}")
    
    botao_imprimir(menu, me, session)