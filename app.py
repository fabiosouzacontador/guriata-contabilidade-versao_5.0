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
# FUNÇÕES DE FORMATAÇÃO DE DATA
# ==============================================================================
def formatar_data_br(data):
    """Converte date para string no formato DD/MM/AAAA"""
    if data:
        return data.strftime('%d/%m/%Y')
    return ""

def parse_data_br(data_str):
    """Converte string DD/MM/AAAA para date"""
    return datetime.strptime(data_str, '%d/%m/%Y').date()

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
    .total-card h3 {
        margin: 0;
        font-size: 1rem;
    }
    .total-card .valor {
        font-size: 1.5rem;
        font-weight: bold;
        margin-top: 5px;
    }
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
        html_t = "<table>"
        html_t += "<tr>" + "".join(f"<th>{h}</th>" for h in cabecalhos) + "</tr>"
        for linha in linhas:
            html_t += "<tr>" + "".join(f" looked{v}Nine" for v in linha) + "</tr>"
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
# 2. BANCO DE DADOS & PLANO DE CONTAS MASTER (Neon PostgreSQL)
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
            ("1.1.7", "Adiantamento a Fornecedores", "A", "D"),
            ("1.1.8", "Adiantamento a Funcionários", "A", "D"),
            ("1.1.9", "Aplicações Financeiras (CDB/LC)", "A", "D"),
            ("1.2", "NÃO CIRCULANTE", "S", "D"), ("1.2.1", "Realizável LP", "S", "D"),
            ("1.2.3", "Imobilizado", "S", "D"), ("1.2.3.1", "Imóveis", "A", "D"),
            ("1.2.3.2", "Veículos", "A", "D"), ("1.2.3.3", "Móveis e Utensílios", "A", "D"),
            ("1.2.3.4", "Equip. Informática", "A", "D"), ("1.2.4", "Intangível", "A", "D"),
            ("1.2.5", "Participações em Outras Empresas", "A", "D"),
            ("2", "PASSIVO", "S", "C"), ("2.1", "CIRCULANTE", "S", "C"),
            ("2.1.1", "Fornecedores", "A", "C"), ("2.1.2", "Salários a Pagar", "A", "C"),
            ("2.1.3", "Obrigações Sociais", "A", "C"), ("2.1.4", "Impostos a Recolher", "A", "C"),
            ("2.1.5", "Adiantamento de Clientes", "A", "C"),
            ("2.1.6", "Empréstimos e Financiamentos CP", "A", "C"),
            ("2.2", "NÃO CIRCULANTE", "S", "C"), ("2.2.1", "Financiamentos LP", "A", "C"),
            ("2.2.2", "Empréstimos e Financiamentos LP", "A", "C"),
            ("2.3", "PATRIMÔNIO LÍQUIDO", "S", "C"), ("2.3.1", "Capital Social", "A", "C"),
            ("2.3.2", "Reservas de Lucros", "A", "C"), ("2.3.3", "Lucros Acumulados", "A", "C"),
            ("3", "RECEITAS", "S", "C"), ("3.1", "RECEITA BRUTA", "S", "C"),
            ("3.1.1", "Venda de Mercadorias", "A", "C"), ("3.1.2", "Serviços", "A", "C"),
            ("3.1.3", "Receita de Serviços Financeiros", "A", "C"),
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
            ("5.2.8", "Despesas com Transporte", "A", "D"),
            ("5.3", "DESPESAS TRIBUTÁRIAS", "S", "D"),
            ("5.3.1", "PIS sobre Faturamento", "A", "D"),
            ("5.3.2", "COFINS sobre Faturamento", "A", "D"),
            ("5.3.3", "ISS", "A", "D"),
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
def fmt_moeda(v):
    return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def get_mapa_nomes():
    return {c.codigo: c.nome for c in get_session().exec(select(ContaContabil)).all()}

def get_contas_analiticas():
    return {c.codigo: f"{c.codigo} - {c.nome}" for c in get_session().exec(select(ContaContabil).where(ContaContabil.tipo == 'A')).all()}

def calcular_movimentacao(uid):
    s = get_session()
    lancs = s.exec(select(Lancamento).where(Lancamento.usuario_id == uid)).all()
    dados = {}
    mapa_nat  = {c.codigo: c.natureza for c in s.exec(select(ContaContabil)).all()}
    mapa_nome = {c.codigo: c.nome     for c in s.exec(select(ContaContabil)).all()}
    for l in lancs:
        if l.conta_debito not in dados:
            dados[l.conta_debito] = {'deb': 0.0, 'cred': 0.0}
        dados[l.conta_debito]['deb'] += l.valor
        if l.conta_credito not in dados:
            dados[l.conta_credito] = {'deb': 0.0, 'cred': 0.0}
        dados[l.conta_credito]['cred'] += l.valor
    resultado = {}
    for k, v in dados.items():
        nat   = mapa_nat.get(k, 'D')
        saldo = v['deb'] - v['cred'] if nat == 'D' else v['cred'] - v['deb']
        resultado[k] = {
            'nome':          mapa_nome.get(k, k),
            'natureza':      nat,
            'total_debito':  v['deb'],
            'total_credito': v['cred'],
            'saldo':         saldo
        }
    return resultado

def gerar_demonstrativos(uid):
    mov = calcular_movimentacao(uid)
    rec_bruta    = 0.0
    deducoes     = 0.0
    custos       = 0.0
    despesas_op  = 0.0
    rec_financ   = 0.0
    desp_financ  = 0.0
    ativo_total  = 0.0
    passivo_total = 0.0

    grupos_ativo   = {"1.1": [], "1.2.1": [], "1.2.3": [], "1.2.4": []}
    grupos_passivo = {"2.1": [], "2.2": [], "2.3": []}
    nomes_grupos_a = {
        "1.1":   "Ativo Circulante",
        "1.2.1": "Realizável a Longo Prazo",
        "1.2.3": "Imobilizado",
        "1.2.4": "Intangível"
    }
    nomes_grupos_p = {
        "2.1": "Passivo Circulante",
        "2.2": "Passivo Não Circulante",
        "2.3": "Patrimônio Líquido"
    }

    for conta, d in mov.items():
        saldo = d['saldo']
        if conta.startswith('3.1'):
            rec_bruta   += saldo
        elif conta.startswith('3.2'):
            deducoes    += saldo
        elif conta.startswith('3.3'):
            rec_financ  += saldo
        elif conta.startswith('4'):
            custos      += saldo
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

    rec_liquida      = rec_bruta - deducoes
    lucro_bruto      = rec_liquida - custos
    res_operacional  = lucro_bruto - despesas_op
    res_liquido      = res_operacional + rec_financ - desp_financ

    if res_liquido != 0:
        passivo_total += res_liquido
        grupos_passivo["2.3"].append({"Conta": "Resultado do Exercício", "Saldo": res_liquido})

    dre_rows = [
        {"Descrição": "(=) Receita Operacional Bruta",      "Valor": fmt_moeda(rec_bruta)},
        {"Descrição": "(-) Deduções da Receita",            "Valor": fmt_moeda(deducoes * -1)},
        {"Descrição": "(=) Receita Operacional Líquida",    "Valor": fmt_moeda(rec_liquida)},
        {"Descrição": "(-) Custos (CMV/CSP)",               "Valor": fmt_moeda(custos * -1)},
        {"Descrição": "(=) Lucro Bruto",                    "Valor": fmt_moeda(lucro_bruto)},
        {"Descrição": "(-) Despesas Operacionais",          "Valor": fmt_moeda(despesas_op * -1)},
        {"Descrição": "(+) Receitas Financeiras",           "Valor": fmt_moeda(rec_financ)},
        {"Descrição": "(-) Despesas Financeiras",           "Valor": fmt_moeda(desp_financ * -1)},
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
        # Verifica se é hash ou texto puro (compatibilidade com versões antigas)
        if user.senha.startswith('$2b$'):
            senha_valida = verificar_senha(p, user.senha)
        else:
            senha_valida = (p == user.senha)
            if senha_valida:
                # Migra para hash
                user.senha = hash_senha(p)
                s.add(user)
                s.commit()
        
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

# ── TELA DE LOGIN ──────────────────────────────────────────────────────────────
if "user" not in st.session_state or not st.session_state["user"]:

    if "show_forgot" not in st.session_state:
        st.session_state["show_forgot"] = False

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
        .login-body {
            padding: 28px 36px 32px 36px;
            background: white;
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
        total_turmas  = len(minhas_turmas)
        total_alunos  = len(session.exec(select(Usuario).where(Usuario.perfil == 'aluno').where(Usuario.turma_id.in_([t.id for t in minhas_turmas]))).all()) if minhas_turmas else 0
        total_aulas   = len(session.exec(select(Aula).where(Aula.professor_id == me.id)).all())
        escola_nome   = session.get(Escola, me.escola_id).nome if me.escola_id else "Não vinculada"
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"<div class='kpi-card'><div class='kpi-title'>Minhas Turmas</div><div class='kpi-val'>{total_turmas}</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='kpi-card'><div class='kpi-title'>Total de Alunos</div><div class='kpi-val' style='color:#3498db'>{total_alunos}</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='kpi-card'><div class='kpi-title'>Aulas Postadas</div><div class='kpi-val' style='color:#e74c3c'>{total_aulas}</div></div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='kpi-card'><div class='kpi-title'>Instituição</div><div class='kpi-val' style='font-size:0.9rem'>{escola_nome[:15]}...</div></div>", unsafe_allow_html=True)
        st.divider()
        st.subheader("🎯 Suas Turmas")
        if minhas_turmas:
            col1, col2 = st.columns(2)
            for idx, turma in enumerate(minhas_turmas):
                alunos_na_turma = session.exec(select(Usuario).where(Usuario.turma_id == turma.id)).all()
                aulas_turma     = session.exec(select(Aula).where(Aula.turma_id == turma.id)).all()
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
            turma      = session.get(Turma, me.turma_id)
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
# ESCRIBITURAÇÃO E DIÁRIO (COM EDIÇÃO DE LANÇAMENTOS)
# ==============================================================================
elif menu == "Escrituração e Diário":
    st.header("📝 Escrituração")
    mapa = get_contas_analiticas(); contas = sorted(list(mapa.values()))
    
    with st.form("lanc", clear_on_submit=True):
        ce, cd = st.columns(2)
        with ce:
            d = st.date_input("Data", value=date.today())
            db = st.selectbox("Débito", contas, index=None)
            cr = st.selectbox("Crédito", contas, index=None)
        with cd:
            v = st.number_input("Valor (R$)", min_value=0.01)
            h = st.text_area("Histórico")
        gravar = st.form_submit_button("✅ Gravar Lançamento", type="primary", use_container_width=True)
    
    if gravar:
        if db and cr:
            session.add(Lancamento(data_lancamento=d, valor=v, historico=h,
                conta_debito=db.split(" - ")[0], conta_credito=cr.split(" - ")[0],
                usuario_id=me.id))
            session.commit()
            st.success("Lançamento gravado!")
            st.rerun()
        else:
            st.warning("Selecione as contas de Débito e Crédito antes de gravar.")

    lancs = session.exec(select(Lancamento).where(Lancamento.usuario_id == me.id).order_by(desc(Lancamento.data_lancamento))).all()
    if lancs:
        mapa_nomes = get_mapa_nomes()
        st.divider()
        st.subheader("📋 Lançamentos registrados")
        
        # Estado para controle de edição
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
                    st.success("✅ Lançamento editado com sucesso!")
                    st.session_state.editando_lancamento = None
                    st.rerun()
        
        def cancelar_edicao():
            st.session_state.editando_lancamento = None
            st.rerun()
        
        # Cabeçalho
        cab = st.columns([1.2, 2.5, 2.5, 1.5, 2.5, 1, 1])
        for col, label in zip(cab, ["Data", "Débito", "Crédito", "Valor", "Histórico", "Editar", "Excluir"]):
            col.markdown(f"<div style='font-size:0.78em;font-weight:700;color:#004b8d;padding-bottom:4px;'>{label}</div>", unsafe_allow_html=True)
        st.markdown("<hr style='margin:0 0 6px 0;border-color:#e0e0e0;'>", unsafe_allow_html=True)
        
        for l in lancs:
            cols = st.columns([1.2, 2.5, 2.5, 1.5, 2.5, 1, 1])
            
            with cols[0]:
                st.write(formatar_data_br(l.data_lancamento))
            with cols[1]:
                st.write(f"{l.conta_debito} - {mapa_nomes.get(l.conta_debito, '')}")
            with cols[2]:
                st.write(f"{l.conta_credito} - {mapa_nomes.get(l.conta_credito, '')}")
            with cols[3]:
                st.write(fmt_moeda(l.valor))
            with cols[4]:
                st.write(l.historico or "—")
            with cols[5]:
                if st.button("✏️", key=f"edit_{l.id}", help="Editar lançamento"):
                    st.session_state.editando_lancamento = l.id
            with cols[6]:
                if st.button("🗑️", key=f"del_{l.id}", help="Excluir lançamento"):
                    session.delete(session.get(Lancamento, l.id)); session.commit()
                    st.rerun()
            
            # Formulário de edição
            if st.session_state.editando_lancamento == l.id:
                with st.container(border=True):
                    st.markdown("**✏️ Editando lançamento**")
                    col1, col2 = st.columns(2)
                    with col1:
                        nova_data = st.date_input("Data", value=l.data_lancamento, key=f"data_{l.id}")
                        novo_debito = st.selectbox(
                            "Débito", contas,
                            index=contas.index(f"{l.conta_debito} - {mapa_nomes.get(l.conta_debito, '')}") 
                            if f"{l.conta_debito} - {mapa_nomes.get(l.conta_debito, '')}" in contas else 0,
                            key=f"deb_{l.id}"
                        )
                    with col2:
                        novo_valor = st.number_input("Valor (R$)", value=l.valor, min_value=0.01, step=0.01, key=f"val_{l.id}")
                        novo_credito = st.selectbox(
                            "Crédito", contas,
                            index=contas.index(f"{l.conta_credito} - {mapa_nomes.get(l.conta_credito, '')}")
                            if f"{l.conta_credito} - {mapa_nomes.get(l.conta_credito, '')}" in contas else 0,
                            key=f"cred_{l.id}"
                        )
                    novo_historico = st.text_area("Histórico", value=l.historico or "", key=f"hist_{l.id}")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("💾 Salvar", key=f"save_{l.id}", type="primary"):
                            salvar_edicao(l.id, nova_data, novo_debito, novo_credito, novo_valor, novo_historico)
                    with col2:
                        if st.button("❌ Cancelar", key=f"cancel_{l.id}"):
                            cancelar_edicao()
            
            st.divider()
    
    botao_imprimir(menu, me, session)

# ==============================================================================
# RAZONETES
# ==============================================================================
elif menu == "Razonetes":
    st.header("🗂️ Razonetes")
    mov = calcular_movimentacao(me.id)
    cols = st.columns(2); i = 0
    for k, v in mov.items():
        html = f"""<div class='razonete-container'>
  <div class='razonete-header'>{k} - {v['nome']}</div>
  <div style='display:flex;background:#f8f9fa;border-bottom:1px solid #e0e0e0;'>
    <div style='width:50%;text-align:center;padding:4px 6px;font-size:0.68em;font-weight:700;color:#c0392b;border-right:1px solid #ddd;letter-spacing:0.5px;'>DÉBITO</div>
    <div style='width:50%;text-align:center;padding:4px 6px;font-size:0.68em;font-weight:700;color:#27ae60;letter-spacing:0.5px;'>CRÉDITO</div>
  </div>
  <div class='razonete-body'>
    <div class='col-debito'>{fmt_moeda(v['total_debito'])}</div>
    <div class='col-credito'>{fmt_moeda(v['total_credito'])}</div>
  </div>
</div>"""
        cols[i % 2].markdown(html, unsafe_allow_html=True); i += 1
    botao_imprimir(menu, me, session)

# ==============================================================================
# BALANCETE
# ==============================================================================
elif menu == "Balancete":
    st.header("⚖️ Balancete")
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
        
        with col1:
            st.markdown(f"""
            <div class='total-card'>
                <h3>💰 TOTAL DÉBITOS</h3>
                <div class='valor'>{fmt_moeda(total_debito)}</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class='total-card'>
                <h3>💰 TOTAL CRÉDITOS</h3>
                <div class='valor'>{fmt_moeda(total_credito)}</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            diferenca = total_debito - total_credito
            cor = "#27ae60" if abs(diferenca) < 0.01 else "#c0392b"
            st.markdown(f"""
            <div class='total-card' style='background: linear-gradient(135deg, #2c3e50, #34495e);'>
                <h3>📊 DIFERENÇA</h3>
                <div class='valor' style='color:{cor};'>{fmt_moeda(abs(diferenca))}</div>
                <small style='color:white;'>{"✅ EQUILIBRADO" if abs(diferenca) < 0.01 else "⚠️ DESEQUILIBRADO"}</small>
            </div>
            """, unsafe_allow_html=True)
        
        if abs(total_debito - total_credito) > 0.01:
            st.warning("⚠️ O balancete está desequilibrado! Verifique seus lançamentos.")
        else:
            st.success("✅ Balancete equilibrado! Os débitos e créditos estão balanceados.")
    else:
        st.info("Nenhuma movimentação encontrada. Registre lançamentos para visualizar o balancete.")
    
    botao_imprimir(menu, me, session)

# ==============================================================================
# DRE
# ==============================================================================
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
    
    detalhes_receitas = []
    detalhes_deducoes = []
    detalhes_custos = []
    detalhes_despesas = []
    detalhes_receitas_fin = []
    detalhes_despesas_fin = []
    
    for codigo, dados in mov.items():
        saldo = dados['saldo']
        nome = f"{codigo} - {dados['nome']}"
        
        if codigo.startswith('3.1'):
            receitas += saldo
            if saldo != 0:
                detalhes_receitas.append((nome, saldo))
        elif codigo.startswith('3.2'):
            deducoes += abs(saldo)
            if saldo != 0:
                detalhes_deducoes.append((nome, saldo))
        elif codigo.startswith('3.3'):
            receitas_fin += saldo
            if saldo != 0:
                detalhes_receitas_fin.append((nome, saldo))
        elif codigo.startswith('4'):
            custos += abs(saldo)
            if saldo != 0:
                detalhes_custos.append((nome, saldo))
        elif codigo.startswith('5'):
            despesas += abs(saldo)
            if saldo != 0:
                detalhes_despesas.append((nome, saldo))
        elif codigo.startswith('6.1'):
            despesas_fin += abs(saldo)
            if saldo != 0:
                detalhes_despesas_fin.append((nome, saldo))
    
    receita_liquida = receitas - deducoes
    lucro_bruto = receita_liquida - custos
    resultado_op = lucro_bruto - despesas
    resultado_final = resultado_op + receitas_fin - despesas_fin
    
    st.markdown("""
    <style>
        .dre-card {
            background: white;
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            overflow: hidden;
            margin: 20px auto;
            max-width: 800px;
        }
        .dre-header {
            background: linear-gradient(135deg, #004b8d, #0066c0);
            color: white;
            padding: 20px;
            text-align: center;
        }
        .dre-header h2 { margin: 0; font-size: 1.2rem; }
        .dre-body { padding: 20px; }
        .dre-section { margin-bottom: 20px; border-bottom: 1px solid #eef2f5; padding-bottom: 15px; }
        .dre-section-title { font-weight: 700; color: #004b8d; font-size: 0.85rem; text-transform: uppercase; margin-bottom: 10px; }
        .dre-row { display: flex; justify-content: space-between; padding: 6px 0 6px 15px; font-size: 0.85rem; }
        .dre-row-positive { color: #27ae60; }
        .dre-row-negative { color: #c0392b; }
        .dre-subtotal { display: flex; justify-content: space-between; padding: 8px 15px; font-weight: 600; background: #f8fafc; border-radius: 8px; margin-top: 8px; }
        .dre-line-result { background: #e8f5e9; padding: 12px 15px; border-radius: 10px; margin: 12px 0; font-weight: 700; display: flex; justify-content: space-between; }
        .dre-highlight { background: linear-gradient(135deg, #e8f4f8, #d4eaf4); padding: 20px; text-align: center; border-radius: 12px; margin-top: 20px; }
        .dre-highlight-label { font-size: 0.85rem; font-weight: 600; color: #004b8d; }
        .dre-highlight-value { font-size: 1.8rem; font-weight: 700; margin-top: 5px; }
        .dre-highlight-value.positive { color: #27ae60; }
        .dre-highlight-value.negative { color: #c0392b; }
    </style>
    """, unsafe_allow_html=True)
    
    html = f"""
    <div class="dre-card">
        <div class="dre-header">
            <h2>DEMONSTRAÇÃO DO RESULTADO DO EXERCÍCIO</h2>
        </div>
        <div class="dre-body">
    """
    
    if detalhes_receitas:
        html += '<div class="dre-section"><div class="dre-section-title">📈 RECEITA OPERACIONAL BRUTA</div>'
        for nome, val in detalhes_receitas:
            html += f'<div class="dre-row dre-row-positive"><span>{nome}</span><span>R$ {val:,.2f}</span></div>'
        html += f'<div class="dre-subtotal"><span>Subtotal</span><span>R$ {receitas:,.2f}</span></div></div>'
    else:
        html += f'<div class="dre-section"><div class="dre-section-title">📈 RECEITA OPERACIONAL BRUTA</div><div class="dre-row">R$ {receitas:,.2f}</div></div>'
    
    if detalhes_deducoes:
        html += '<div class="dre-section"><div class="dre-section-title">📉 DEDUÇÕES DA RECEITA</div>'
        for nome, val in detalhes_deducoes:
            html += f'<div class="dre-row dre-row-negative"><span>{nome}</span><span>R$ {abs(val):,.2f}</span></div>'
        html += f'<div class="dre-subtotal"><span>Total das Deduções</span><span>R$ {deducoes:,.2f}</span></div></div>'
    
    cor_rl = "#27ae60" if receita_liquida >= 0 else "#c0392b"
    html += f'<div class="dre-line-result" style="background:#e3f2fd;"><span>(=) RECEITA OPERACIONAL LÍQUIDA</span><span style="color:{cor_rl};">R$ {receita_liquida:,.2f}</span></div>'
    
    if detalhes_custos:
        html += '<div class="dre-section"><div class="dre-section-title">🏭 CUSTOS OPERACIONAIS</div>'
        for nome, val in detalhes_custos:
            html += f'<div class="dre-row dre-row-negative"><span>{nome}</span><span>R$ {abs(val):,.2f}</span></div>'
        html += f'<div class="dre-subtotal"><span>Total dos Custos</span><span>R$ {custos:,.2f}</span></div></div>'
    
    cor_lb = "#27ae60" if lucro_bruto >= 0 else "#c0392b"
    html += f'<div class="dre-line-result" style="background:#e8f5e9;"><span>(=) LUCRO BRUTO</span><span style="color:{cor_lb};">R$ {lucro_bruto:,.2f}</span></div>'
    
    if detalhes_despesas:
        html += '<div class="dre-section"><div class="dre-section-title">💼 DESPESAS OPERACIONAIS</div>'
        for nome, val in detalhes_despesas:
            html += f'<div class="dre-row dre-row-negative"><span>{nome}</span><span>R$ {abs(val):,.2f}</span></div>'
        html += f'<div class="dre-subtotal"><span>Total das Despesas</span><span>R$ {despesas:,.2f}</span></div></div>'
    
    cor_ro = "#27ae60" if resultado_op >= 0 else "#c0392b"
    html += f'<div class="dre-line-result" style="background:#fff3e0;"><span>(=) RESULTADO OPERACIONAL</span><span style="color:{cor_ro};">R$ {resultado_op:,.2f}</span></div>'
    
    if detalhes_receitas_fin:
        html += '<div class="dre-section"><div class="dre-section-title">💰 RECEITAS FINANCEIRAS</div>'
        for nome, val in detalhes_receitas_fin:
            html += f'<div class="dre-row dre-row-positive"><span>{nome}</span><span>R$ {val:,.2f}</span></div>'
        html += f'<div class="dre-subtotal"><span>Total</span><span>R$ {receitas_fin:,.2f}</span></div></div>'
    
    if detalhes_despesas_fin:
        html += '<div class="dre-section"><div class="dre-section-title">💸 DESPESAS FINANCEIRAS</div>'
        for nome, val in detalhes_despesas_fin:
            html += f'<div class="dre-row dre-row-negative"><span>{nome}</span><span>R$ {abs(val):,.2f}</span></div>'
        html += f'<div class="dre-subtotal"><span>Total</span><span>R$ {despesas_fin:,.2f}</span></div></div>'
    
    classe_final = "positive" if resultado_final >= 0 else "negative"
    texto_final = "LUCRO LÍQUIDO DO EXERCÍCIO" if resultado_final >= 0 else "PREJUÍZO DO EXERCÍCIO"
    
    html += f"""
            <div class="dre-highlight">
                <div class="dre-highlight-label">(=) {texto_final}</div>
                <div class="dre-highlight-value {classe_final}">R$ {abs(resultado_final):,.2f}</div>
            </div>
        </div>
    </div>
    """
    
    st.markdown(html, unsafe_allow_html=True)
    botao_imprimir(menu, me, session)

# ==============================================================================
# BALANÇO
# ==============================================================================
elif menu == "Balanço":
    st.header("🏛️ Balanço Patrimonial")
    at, pas, _, _, grupos_a, grupos_p, _, nomes_a, nomes_p = gerar_demonstrativos(me.id)

    def render_lado(grupos, nomes_grupos, total_geral):
        rows = ""
        for pfx in sorted(grupos.keys()):
            linhas = grupos[pfx]
            if not linhas: continue
            subtotal   = sum(l["Saldo"] for l in linhas)
            nome_grupo = nomes_grupos.get(pfx, pfx)
            rows += f"<table><td colspan='2' style='background:#e8f0fe;font-weight:700;font-size:0.82em;padding:6px 10px;color:#004b8d;border-top:2px solid #c5d8f6;'>{nome_grupo}</td></tr>"
            for l in linhas:
                rows += f"<tr><td style='padding:4px 10px 4px 20px;font-size:0.8em;color:#444;'>{l['Conta']}</td><td style='text-align:right;padding:4px 10px;font-size:0.8em;color:#222;white-space:nowrap;'>{fmt_moeda(l['Saldo'])}</td>"
            rows += f"<tr style='background:#f0f4fb;'><td style='text-align:right;padding:3px 10px;font-size:0.78em;color:#555;font-style:italic;'>Subtotal</td><td style='text-align:right;padding:3px 10px;font-size:0.8em;font-weight:700;color:#004b8d;white-space:nowrap;border-top:1px solid #c5d8f6;'>{fmt_moeda(subtotal)}</td>"
        rows += f"<tr style='background:#004b8d;'><td style='padding:8px 10px;font-size:0.85em;font-weight:700;color:white;'>TOTAL GERAL</td><td style='text-align:right;padding:8px 10px;font-size:0.88em;font-weight:700;color:white;white-space:nowrap;'>{fmt_moeda(total_geral)}</td>"
        return f"<table style='width:100%;border-collapse:collapse;border:1px solid #dde4f0;border-radius:8px;overflow:hidden;'>{rows}</table>"

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div class='report-header'>ATIVO</div>", unsafe_allow_html=True)
        st.markdown(render_lado(grupos_a, nomes_a, at), unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='report-header'>PASSIVO + PL</div>", unsafe_allow_html=True)
        st.markdown(render_lado(grupos_p, nomes_p, pas), unsafe_allow_html=True)
    botao_imprimir(menu, me, session)

# ==============================================================================
# DEMAIS MENUS (ESCOLAS, PROFESSORES, TURMAS, ALUNOS, ETC)
# ==============================================================================
elif menu == "Escolas":
    st.header("🏢 Escolas")
    st.subheader("➕ Cadastrar nova escola")
    with st.form("ne", clear_on_submit=True):
        n = st.text_input("Nome da escola")
        c = st.text_input("Cidade")
        if st.form_submit_button("💾 Salvar escola", type="primary", use_container_width=True):
            if n and c:
                session.add(Escola(nome=n, cidade=c)); session.commit()
                st.success(f"Escola '{n}' cadastrada!"); st.rerun()
            else:
                st.warning("Preencha nome e cidade.")
    st.divider()
    st.subheader("📋 Escolas cadastradas")
    for escola in session.exec(select(Escola)).all():
        col1, col2, col3 = st.columns([3, 2, 1])
        col1.write(f"**{escola.nome}**"); col1.caption(f"📍 {escola.cidade}")
        col2.caption(f"ID: {escola.id}")
        if col3.button("🗑️ Excluir", key=f"del_escola_{escola.id}", use_container_width=True):
            profs = session.exec(select(Usuario).where(Usuario.escola_id == escola.id).where(Usuario.perfil == 'professor')).all()
            if profs:
                st.error(f"Escola possui {len(profs)} professor(es) vinculado(s).")
            else:
                session.delete(escola); session.commit(); st.rerun()
        st.divider()

elif menu == "Professores":
    st.header("👨‍🏫 Professores")
    escolas = session.exec(select(Escola)).all()
    if not escolas:
        st.warning("⚠️ Cadastre uma escola antes de adicionar professores.")
    else:
        st.subheader("➕ Cadastrar novo professor")
        with st.form("np", clear_on_submit=True):
            n = st.text_input("Nome completo")
            u = st.text_input("Login de acesso")
            e = st.selectbox("Escola vinculada", escolas, format_func=lambda x: x.nome)
            st.caption("Senha inicial: **123** (será armazenada com segurança)")
            if st.form_submit_button("💾 Cadastrar professor", type="primary", use_container_width=True):
                if n and u:
                    if session.exec(select(Usuario).where(Usuario.username == u)).first():
                        st.error("❌ Login já em uso.")
                    else:
                        session.add(Usuario(nome=n, username=u, senha=hash_senha("123"), perfil="professor", escola_id=e.id, criado_por_id=me.id))
                        session.commit(); st.success(f"Professor '{n}' cadastrado!"); st.rerun()
                else:
                    st.warning("Preencha nome e login.")
    st.divider()
    st.subheader("📋 Professores cadastrados")
    profs = session.exec(select(Usuario).where(Usuario.perfil == 'professor')).all()
    if profs:
        escola_map = {e.id: e.nome for e in escolas}
        for prof in profs:
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            col1.write(f"**{prof.nome}**"); col1.caption(f"👤 @{prof.username}")
            col2.write(f"🏫 {escola_map.get(prof.escola_id, '—')}")
            turmas_prof = session.exec(select(Turma).where(Turma.professor_id == prof.id)).all()
            col3.caption(f"📚 {len(turmas_prof)} turma(s)")
            if col4.button("🗑️", key=f"del_prof_{prof.id}"):
                if turmas_prof:
                    st.error(f"Professor possui {len(turmas_prof)} turma(s).")
                else:
                    session.delete(prof); session.commit(); st.rerun()
            st.divider()
    else:
        st.info("Nenhum professor cadastrado.")

elif menu == "Turmas":
    st.header("🏫 Turmas")
    if me.perfil == 'admin':
        st.subheader("➕ Criar nova turma")
        professores_list = session.exec(select(Usuario).where(Usuario.perfil == 'professor')).all()
        with st.form("nt", clear_on_submit=True):
            n         = st.text_input("Nome da turma")
            a         = st.text_input("Ano letivo", value="2026")
            professor = st.selectbox("Professor responsável", professores_list, format_func=lambda x: x.nome)
            if st.form_submit_button("💾 Criar turma", type="primary", use_container_width=True):
                if n and a:
                    session.add(Turma(nome=n, ano_letivo=a, professor_id=professor.id, escola_id=professor.escola_id or 1))
                    session.commit(); st.success(f"Turma '{n}' criada!"); st.rerun()
                else:
                    st.warning("Preencha nome e ano letivo.")
        st.divider()
        st.subheader("📋 Turmas cadastradas")
        ts = session.exec(select(Turma)).all()
        if ts:
            professores_map = {p.id: p.nome for p in professores_list}
            for turma in ts:
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                col1.write(f"**{turma.nome}**"); col1.caption(f"📅 {turma.ano_letivo}")
                col2.write(f"👨‍🏫 {professores_map.get(turma.professor_id, '—')}")
                alunos_turma = session.exec(select(Usuario).where(Usuario.turma_id == turma.id)).all()
                col3.caption(f"🎓 {len(alunos_turma)} aluno(s)")
                if col4.button("🗑️", key=f"del_turma_{turma.id}"):
                    if alunos_turma:
                        st.error(f"Turma possui {len(alunos_turma)} aluno(s).")
                    else:
                        session.delete(turma); session.commit(); st.rerun()
                st.divider()
        else:
            st.info("Nenhuma turma cadastrada.")
    else:
        st.warning("Esta seção não está disponível para seu perfil.")

elif menu == "Alunos" or menu == "Meus Alunos":
    st.header("🎓 Alunos")
    turmas = session.exec(select(Turma)).all()
    if me.perfil == 'professor':
        turmas = session.exec(select(Turma).where(Turma.professor_id == me.id)).all()
    if not turmas:
        st.warning("⚠️ Cadastre uma turma antes de matricular alunos.")
    else:
        st.subheader("➕ Matricular novo aluno")
        with st.form("na", clear_on_submit=True):
            n = st.text_input("Nome completo do aluno")
            u = st.text_input("Login de acesso")
            t = st.selectbox("Turma", turmas, format_func=lambda x: f"{x.nome} ({x.ano_letivo})")
            st.caption("Senha inicial: **123** (será armazenada com segurança)")
            if st.form_submit_button("💾 Matricular aluno", type="primary", use_container_width=True):
                if n and u:
                    if session.exec(select(Usuario).where(Usuario.username == u)).first():
                        st.error("❌ Login já em uso.")
                    else:
                        session.add(Usuario(nome=n, username=u, senha=hash_senha("123"), perfil="aluno", turma_id=t.id, criado_por_id=me.id))
                        session.commit(); st.success(f"Aluno '{n}' matriculado!"); st.rerun()
                else:
                    st.warning("Preencha nome e login.")
        st.divider()
        st.subheader("📋 Alunos matriculados")
        turma_map = {t.id: f"{t.nome} ({t.ano_letivo})" for t in turmas}
        alunos = session.exec(select(Usuario).where(Usuario.perfil == 'aluno').where(Usuario.turma_id.in_([t.id for t in turmas]))).all()
        if alunos:
            for aluno in alunos:
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                col1.write(f"**{aluno.nome}**"); col1.caption(f"👤 @{aluno.username}")
                col2.write(f"📚 {turma_map.get(aluno.turma_id, '—')}")
                col3.caption(f"📅 {formatar_data_br(aluno.data_criacao)}")
                if col4.button("🗑️", key=f"del_aluno_{aluno.id}"):
                    for lanc in session.exec(select(Lancamento).where(Lancamento.usuario_id == aluno.id)).all():
                        session.delete(lanc)
                    session.delete(aluno); session.commit(); st.rerun()
                st.divider()
        else:
            st.info("Nenhum aluno matriculado.")

elif menu == "Postar Aulas":
    st.header("📹 Postar Aulas")
    if me.perfil == 'professor':
        minhas_turmas = session.exec(select(Turma).where(Turma.professor_id == me.id)).all()
        if not minhas_turmas:
            st.error("Você não tem turmas criadas.")
        else:
            with st.form("postar_aula", clear_on_submit=True):
                turma    = st.selectbox("Turma", minhas_turmas, format_func=lambda x: f"{x.nome} ({x.ano_letivo})")
                titulo   = st.text_input("Título da aula")
                descricao = st.text_area("Descrição / Conteúdo")
                arquivo  = st.file_uploader("Anexar arquivo", type=["pdf","doc","docx","ppt","pptx","xls","xlsx","txt","jpg","png"])
                if st.form_submit_button("📤 Postar Aula", type="primary", use_container_width=True):
                    if titulo and descricao:
                        arquivo_blob = arquivo.read() if arquivo else None
                        session.add(Aula(titulo=titulo, descricao=descricao, arquivo_blob=arquivo_blob,
                                         nome_arquivo=arquivo.name if arquivo else None,
                                         professor_id=me.id, turma_id=turma.id))
                        session.commit(); st.success("✅ Aula postada!"); st.rerun()
                    else:
                        st.warning("Preencha título e descrição.")
            st.divider()
            st.subheader("📚 Aulas Postadas")
            aulas = session.exec(select(Aula).where(Aula.professor_id == me.id)).all()
            if aulas:
                turmas_dict = {t.id: t.nome for t in minhas_turmas}
                for aula in reversed(aulas):
                    col1, col2 = st.columns([3, 1])
                    col1.write(f"**{aula.titulo}** — {turmas_dict.get(aula.turma_id, '?')}")
                    col1.write(f"*{aula.descricao[:100]}...*" if len(aula.descricao) > 100 else f"*{aula.descricao}*")
                    col1.caption(f"📅 {formatar_data_br(aula.data_postagem)}")
                    if aula.arquivo_blob and aula.nome_arquivo:
                        col2.download_button("⬇️ Download", data=aula.arquivo_blob, file_name=aula.nome_arquivo, key=f"dl_{aula.id}")
                    if col2.button("🗑️ Excluir", key=f"del_aula_{aula.id}"):
                        session.delete(aula); session.commit(); st.rerun()
                    st.divider()
            else:
                st.info("Nenhuma aula postada ainda.")
    else:
        st.warning("Esta seção é apenas para professores.")

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
                        col1.caption(f"📅 {formatar_data_br(aula.data_postagem)}")
                        if aula.arquivo_blob and aula.nome_arquivo:
                            col1.download_button("⬇️ Baixar Arquivo", data=aula.arquivo_blob, file_name=aula.nome_arquivo, key=f"dl_aluno_{aula.id}")
            else:
                st.info("Nenhuma aula disponível no momento.")
        else:
            st.warning("Você não está matriculado em nenhuma turma.")
    else:
        st.warning("Esta seção é apenas para alunos.")