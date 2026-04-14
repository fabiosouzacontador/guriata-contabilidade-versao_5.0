import streamlit as st
import pandas as pd
import numpy as np
from datetime import date
from sqlmodel import SQLModel, Field, select, desc, text, create_engine, Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
import base64
from pathlib import Path
import warnings
import time

# ==============================================================================
# 1. CONFIGURAÇÕES & DESIGN
# ==============================================================================
warnings.filterwarnings("ignore")
st.set_page_config(
    page_title="Contabilidade",
    layout="centered",
    page_icon="🦅",
    initial_sidebar_state="expanded"
)

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

def slugify(text):
    safe = text.lower()
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
        html_t = "<table><tr>"
        for h in cabecalhos:
            html_t += f"<th>{h}</th>"
        html_t += "</tr>"
        for linha in linhas:
            html_t += "<tr>"
            for v in linha:
                html_t += f"<td>{v}</td>"
            html_t += "</tr>"
        html_t += "</table>"
        return html_t

    def formatar_conta_row(conta, dados):
        return [f"{conta} - {dados['nome']}", fmt_moeda(dados['total_debito']), fmt_moeda(dados['total_credito']), fmt_moeda(dados['saldo'])]

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
                linhas.append([l.data_lancamento, f"{l.conta_debito} - {mapa_nomes.get(l.conta_debito, l.conta_debito)}", f"{l.conta_credito} - {mapa_nomes.get(l.conta_credito, l.conta_credito)}", fmt_moeda(l.valor), l.historico or "—"])
            html += "<h2>Diário de Lançamentos</h2>"
            html += tabela_html(["Data", "Débito", "Crédito", "Valor", "Histórico"], linhas)
        else:
            html += "<p>Nenhum lançamento registrado.</p>"
    elif menu == "Razonetes":
        mov = calcular_movimentacao(me.id)
        html += "<h2>Razonetes</h2>"
        for conta, v in sorted(mov.items()):
            html += f"<h3>{conta} - {v['nome']}</h3>"
            html += tabela_html(["Total Débito", "Total Crédito", "Saldo"], [[fmt_moeda(v['total_debito']), fmt_moeda(v['total_credito']), fmt_moeda(v['saldo'])]])
    elif menu == "Balancete":
        mov = calcular_movimentacao(me.id)
        html += "<h2>Balancete completo</h2>"
        if mov:
            linhas = [formatar_conta_row(k, v) for k, v in sorted(mov.items())]
            html += tabela_html(["Conta", "Débito", "Crédito", "Saldo"], linhas)
        else:
            html += "<p>Nenhuma movimentação encontrada.</p>"
    elif menu == "DRE":
        _, _, rec_bruta, _, _, _, _, _, _ = gerar_demonstrativos(me.id)
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
                html += f"<h3>{titulo}</h3>"
                html += tabela_html(["Conta", "Valor"], [[f"{conta} - {mov[conta]['nome']}", fmt_moeda(valor)] for conta, valor in linhas])
                subtotal = sum(v for _, v in linhas)
                html += f"<p><strong>Subtotal {titulo}:</strong> {fmt_moeda(subtotal)}</p>"
        rec_liquida = sum(v for _, v in grupos["Receitas Operacionais Brutas"]) + sum(v for _, v in grupos["Deduções de Receita"])
        lucro_bruto = rec_liquida + sum(v for _, v in grupos["Custos (CMV / CSP)"])
        resultado_operacional = lucro_bruto + sum(v for _, v in grupos["Despesas Operacionais"])
        resultado_final = resultado_operacional + sum(v for _, v in grupos["Receitas Financeiras"]) + sum(v for _, v in grupos["Despesas Financeiras"])
        html += "<h3>Resumo</h3>"
        html += tabela_html(["Descrição", "Valor"], [
            ["Receita Operacional Bruta", fmt_moeda(sum(v for _, v in grupos["Receitas Operacionais Brutas"]))],
            ["Deduções da Receita", fmt_moeda(sum(v for _, v in grupos["Deduções de Receita"]))],
            ["Receita Líquida", fmt_moeda(rec_liquida)],
            ["Custos", fmt_moeda(sum(v for _, v in grupos["Custos (CMV / CSP)"]))],
            ["Lucro Bruto", fmt_moeda(lucro_bruto)],
            ["Despesas Operacionais", fmt_moeda(sum(v for _, v in grupos["Despesas Operacionais"]))],
            ["Receitas Financeiras", fmt_moeda(sum(v for _, v in grupos["Receitas Financeiras"]))],
            ["Despesas Financeiras", fmt_moeda(sum(v for _, v in grupos["Despesas Financeiras"]))],
            ["Resultado Líquido", fmt_moeda(resultado_final)]
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
import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_1ZQMkSRiK6pc@ep-damp-recipe-an7lkxz4-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
)

engine = create_engine(DATABASE_URL)
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
        session.add(Usuario(username="admin", senha="123", nome="Administrador Geral", perfil="admin", termos_aceitos=True, escola_id=esc.id))
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
    mapa_nat = {c.codigo: c.natureza for c in s.exec(select(ContaContabil)).all()}
    mapa_nome = {c.codigo: c.nome for c in s.exec(select(ContaContabil)).all()}
    for l in lancs:
        if l.conta_debito not in dados: dados[l.conta_debito] = {'deb': 0.0, 'cred': 0.0}
        dados[l.conta_debito]['deb'] += l.valor
        if l.conta_credito not in dados: dados[l.conta_credito] = {'deb': 0.0, 'cred': 0.0}
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
    user = s.exec(select(Usuario).where(Usuario.username == u).where(Usuario.senha == p)).first()
    if user:
        st.session_state["user"] = user
        st.rerun()
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
        [data-testid="stAppViewContainer"] { background: #f5f5f5 !important; }
        [data-testid="stHeader"] { background: transparent !important; box-shadow: none !important; }
        [data-testid="stSidebar"] { display: none !important; }
        .block-container { padding-top: 4rem !important; max-width: 420px !important; }
        .login-card {
            background: white;
            border-radius: 16px;
            padding: 40px 36px 32px 36px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.10);
            margin: 0 auto;
        }
        .login-logo {
            text-align: center;
            margin-bottom: 24px;
        }
        .login-label {
            color: #475569; font-size: 0.72em; font-weight: 700;
            letter-spacing: 1px; margin: 10px 0 3px 0;
            text-transform: uppercase;
        }
        .stTextInput > div > div > input {
            border-radius: 10px !important;
            border: 1.5px solid #d0d0d0 !important;
            height: 46px !important;
        }
        .stFormSubmitButton > button {
            height: 50px !important;
            font-size: 1em !important;
            font-weight: 700 !important;
            border-radius: 10px !important;
            background: #e74c3c !important;
            border: none !important;
            letter-spacing: 0.8px !important;
        }
        .stFormSubmitButton > button:hover {
            background: #c0392b !important;
        }
    </style>
    """, unsafe_allow_html=True)

    logo_b64 = get_image_base64("assets/logo.png")
    if logo_b64:
        img_tag = f"<img src='data:image/png;base64,{logo_b64}' style='width:130px;'>"
    else:
        img_tag = "<div style='font-size:5rem;'>🦅</div>"

    st.markdown(f"""
    <div class='login-card'>
        <div class='login-logo'>
            {img_tag}
            <div style='color:#2c3e50;font-weight:700;font-size:1.1em;margin-top:8px;'>Guriátã</div>
            <div style='color:#666;font-size:0.85em;'>Gestão Contábil</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form", clear_on_submit=True):
        st.markdown("<div class='login-label'>👤 &nbsp;USUÁRIO</div>", unsafe_allow_html=True)
        st.text_input("usr", key="u_log",
                      placeholder="Digite seu usuário",
                      label_visibility="collapsed")
        st.markdown("<div class='login-label'>🔒 &nbsp;SENHA</div>", unsafe_allow_html=True)
        st.text_input("pwd", type="password", key="u_pass",
                      placeholder="Mínimo 3 caracteres",
                      label_visibility="collapsed")
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        submitted = st.form_submit_button("ENTRAR", type="primary", use_container_width=True)
        if submitted:
            login()

    st.markdown("""
    <div style='text-align:center;margin-top:20px;color:#888;font-size:0.82em;'>
        Plataforma para o ensino da contabilidade.<br>
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
        c2.markdown(f"<div class='kpi-card'><div class='kpi-title'>Total de Alunos</div><div class='kpi-val' style='color:#3498db'>{total_alunos}</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='kpi-card'><div class='kpi-title'>Aulas Postadas</div><div class='kpi-val' style='color:#e74c3c'>{total_aulas}</div></div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='kpi-card'><div class='kpi-title'>Instituição</div><div class='kpi-val' style='font-size:0.9rem'>{escola_nome[:15]}...</div></div>", unsafe_allow_html=True)
        
        st.divider()
        st.subheader("🎯 Suas Turmas")
        
        if minhas_turmas:
            col1, col2 = st.columns(2)
            for idx, turma in enumerate(minhas_turmas):
                alunos_na_turma = session.exec(select(Usuario).where(Usuario.turma_id == turma.id)).all()
                aulas_turma = session.exec(select(Aula).where(Aula.turma_id == turma.id)).all()
                
                if idx % 2 == 0:
                    col = col1
                else:
                    col = col2
                
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
                    st.caption(f"📚 {turma_aula.nome if turma_aula else '?'} • 📅 {aula.data_postagem}")
                    st.write(f"_{aula.descricao[:80]}..._" if len(aula.descricao) > 80 else f"_{aula.descricao}_")
        else:
            st.info("Você ainda não postou nenhuma aula. Acesse 'Postar Aulas' para começar!")
        
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
        s = st.text_input("Minha Senha", value=me.senha, type="password")
        
        # Mostrar escola vinculada para professores
        if me.perfil == 'professor' and me.escola_id:
            escola = session.get(Escola, me.escola_id)
            st.selectbox("Escola vinculada", [escola], format_func=lambda x: x.nome, disabled=True)
        
        if st.form_submit_button("💾 Atualizar", type="primary", use_container_width=True):
            me.nome, me.senha = n, s
            session.add(me); session.commit()
            st.success("Perfil atualizado!")
            st.rerun()

elif menu == "Minhas Turmas":
    st.header("🏫 Minhas Turmas")
    if me.perfil == 'professor':
        st.subheader("➕ Criar Nova Turma")
        with st.form("nova_turma_professor", clear_on_submit=True):
            n = st.text_input("Nome da turma", placeholder="Ex: 3º Ano A — Contabilidade")
            a = st.text_input("Ano letivo", value="2026", placeholder="Ex: 2026")
            salvar = st.form_submit_button("📌 Criar Turma", type="primary", use_container_width=True)
        if salvar:
            if n and a:
                session.add(Turma(nome=n, ano_letivo=a, professor_id=me.id, escola_id=me.escola_id or 1))
                session.commit()
                st.success(f"Turma '{n}' criada com sucesso!"); st.rerun()
            else:
                st.warning("Preencha o nome e o ano letivo antes de salvar.")
        
        st.divider()
        st.subheader("📚 Suas Turmas")
        minhas_turmas = session.exec(select(Turma).where(Turma.professor_id == me.id)).all()
        if minhas_turmas:
            for t in minhas_turmas:
                col1, col2 = st.columns([3, 1])
                col1.subheader(f"📚 {t.nome} ({t.ano_letivo})")
                alunos_turma = session.exec(select(Usuario).where(Usuario.turma_id == t.id)).all()
                col2.metric("Alunos", len(alunos_turma))
                st.caption(f"ID da Turma: {t.id}")
                st.divider()
        else:
            st.info("Você ainda não tem turmas criadas. Crie uma usando o formulário acima!")
    else:
        st.warning("Esta seção é apenas para professores.")

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
                salvar = st.form_submit_button("✅ Matricular Aluno", type="primary", use_container_width=True)
            if salvar:
                if n and u:
                    session.add(Usuario(nome=n, username=u, senha="123", perfil="aluno", turma_id=t.id, criado_por_id=me.id))
                    session.commit()
                    st.success(f"Aluno '{n}' matriculado com sucesso!"); st.rerun()
                else:
                    st.warning("Preencha o nome e o login antes de salvar.")
            
            st.divider()
            st.subheader("📋 Seus Alunos")
            turmas_dict = {t.id: t.nome for t in minhas_turmas}
            alunos = session.exec(select(Usuario).where(Usuario.perfil == 'aluno').where(Usuario.turma_id.in_([t.id for t in minhas_turmas]))).all()
            
            if alunos:
                df_alunos = pd.DataFrame([{
                    "Nome": a.nome,
                    "Login": a.username,
                    "Turma": turmas_dict.get(a.turma_id, "—"),
                    "XP": a.xp,
                    "Data Cadastro": a.data_criacao
                } for a in alunos])
                st.dataframe(df_alunos, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum aluno matriculado em suas turmas. Use o formulário acima para adicionar alunos!")
    else:
        st.warning("Esta seção é apenas para professores.")

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
                
                if st.form_submit_button("📤 Postar Aula", type="primary", use_container_width=True):
                    if titulo and descricao:
                        arquivo_blob = None
                        if arquivo:
                            try:
                                arquivo_blob = arquivo.read()
                            except Exception as e:
                                st.error(f"Erro ao processar arquivo: {str(e)}")
                                arquivo_blob = None
                        
                        aula = Aula(
                            titulo=titulo,
                            descricao=descricao,
                            arquivo_blob=arquivo_blob,
                            nome_arquivo=arquivo.name if arquivo else None,
                            professor_id=me.id,
                            turma_id=turma.id
                        )
                        session.add(aula)
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
                    col1.caption(f"📅 Postada em: {aula.data_postagem}")
                    
                    if aula.arquivo_blob and aula.nome_arquivo:
                        try:
                            col2.download_button(
                                label="⬇️ Download",
                                data=aula.arquivo_blob,
                                file_name=aula.nome_arquivo,
                                key=f"download_aula_{aula.id}"
                            )
                        except Exception as e:
                            col2.error(f"Erro: arquivo inválido")
                    
                    if col2.button("🗑️ Excluir", key=f"del_aula_{aula.id}"):
                        session.delete(aula)
                        session.commit()
                        st.rerun()
                    st.divider()
            else:
                st.info("Você ainda não postou nenhuma aula.")
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
                        col1.caption(f"📅 Postada em: {aula.data_postagem}")
                        
                        if aula.arquivo_blob and aula.nome_arquivo:
                            try:
                                col1.download_button(
                                    label="⬇️ Baixar Arquivo",
                                    data=aula.arquivo_blob,
                                    file_name=aula.nome_arquivo,
                                    key=f"download_aula_aluno_{aula.id}"
                                )
                            except Exception as e:
                                col1.error(f"Erro ao baixar arquivo: arquivo inválido")
            else:
                st.info("Nenhuma aula disponível no momento. Seu professor em breve postará aulas aqui!")
        else:
            st.warning("Você não está matriculado em nenhuma turma.")
    else:
        st.warning("Esta seção é apenas para alunos.")

elif menu == "Escolas":
    st.header("🏢 Escolas")
    st.subheader("Cadastrar nova escola")
    with st.form("ne", clear_on_submit=True):
        n = st.text_input("Nome da escola", placeholder="Ex: Escola Estadual Dom Pedro II")
        c = st.text_input("Cidade", placeholder="Ex: São Luís")
        salvar = st.form_submit_button("💾 Salvar escola", type="primary", use_container_width=True)
    if salvar:
        if n and c:
            session.add(Escola(nome=n, cidade=c)); session.commit()
            st.success(f"Escola '{n}' cadastrada com sucesso!"); st.rerun()
        else:
            st.warning("Preencha o nome e a cidade antes de salvar.")
    st.divider()
    st.subheader("Escolas cadastradas")
    escolas_lista = session.exec(select(Escola)).all()
    if escolas_lista:
        st.dataframe(pd.DataFrame([{"ID": e.id, "Nome da Escola": e.nome, "Cidade": e.cidade} for e in escolas_lista]), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma escola cadastrada ainda.")

elif menu == "Professores":
    st.header("👨‍🏫 Professores")
    escolas = session.exec(select(Escola)).all()
    st.subheader("Cadastrar novo professor")
    with st.form("np", clear_on_submit=True):
        n = st.text_input("Nome completo", placeholder="Ex: Maria da Silva Santos")
        u = st.text_input("Login de acesso", placeholder="Ex: maria.santos")
        e = st.selectbox("Escola vinculada", escolas, format_func=lambda x: x.nome)
        st.caption("A senha inicial será **123**. O professor poderá alterá-la no primeiro acesso.")
        salvar = st.form_submit_button("💾 Cadastrar professor", type="primary", use_container_width=True)
    if salvar:
        if n and u:
            session.add(Usuario(nome=n, username=u, senha="123", perfil="professor", escola_id=e.id))
            session.commit()
            st.success(f"Professor '{n}' cadastrado com sucesso!"); st.rerun()
        else:
            st.warning("Preencha o nome e o login antes de salvar.")
    st.divider()
    st.subheader("Professores cadastrados")
    profs = session.exec(select(Usuario).where(Usuario.perfil == 'professor')).all()
    if profs:
        escola_map = {e.id: e.nome for e in escolas}
        st.dataframe(pd.DataFrame([{"Nome": p.nome, "Login": p.username, "Escola": escola_map.get(p.escola_id, "—")} for p in profs]), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum professor cadastrado ainda.")

elif menu == "Turmas":
    st.header("🏫 Turmas")
    st.subheader("Criar nova turma")
    with st.form("nt", clear_on_submit=True):
        n = st.text_input("Nome da turma", placeholder="Ex: 3º Ano A — Contabilidade")
        a = st.text_input("Ano letivo", value="2026", placeholder="Ex: 2026")
        salvar = st.form_submit_button("💾 Criar turma", type="primary", use_container_width=True)
    if salvar:
        if n and a:
            session.add(Turma(nome=n, ano_letivo=a, professor_id=me.id, escola_id=me.escola_id or 1))
            session.commit()
            st.success(f"Turma '{n}' criada com sucesso!"); st.rerun()
        else:
            st.warning("Preencha o nome e o ano letivo antes de salvar.")
    st.divider()
    st.subheader("Turmas cadastradas")
    ts = session.exec(select(Turma)).all()
    if ts:
        st.dataframe(pd.DataFrame([{"Nome da Turma": t.nome, "Ano Letivo": t.ano_letivo} for t in ts]), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma turma cadastrada ainda.")

elif menu == "Alunos":
    st.header("🎓 Alunos")
    turmas = session.exec(select(Turma)).all()
    st.subheader("Matricular novo aluno")
    with st.form("na", clear_on_submit=True):
        n = st.text_input("Nome completo do aluno", placeholder="Ex: João Pedro Oliveira")
        u = st.text_input("Login de acesso", placeholder="Ex: joao.pedro")
        t = st.selectbox("Turma", turmas, format_func=lambda x: f"{x.nome} ({x.ano_letivo})")
        st.caption("A senha inicial será **123**. O aluno poderá alterá-la no primeiro acesso.")
        salvar = st.form_submit_button("💾 Matricular aluno", type="primary", use_container_width=True)
    if salvar:
        if n and u:
            session.add(Usuario(nome=n, username=u, senha="123", perfil="aluno", turma_id=t.id, criado_por_id=me.id))
            session.commit()
            st.success(f"Aluno '{n}' matriculado com sucesso!"); st.rerun()
        else:
            st.warning("Preencha o nome e o login antes de salvar.")
    st.divider()
    st.subheader("Alunos matriculados")
    alunos = session.exec(select(Usuario).where(Usuario.perfil == 'aluno')).all()
    if alunos:
        turma_map = {t.id: f"{t.nome} ({t.ano_letivo})" for t in turmas}
        st.dataframe(pd.DataFrame([{"Nome": a.nome, "Login": a.username, "Turma": turma_map.get(a.turma_id, "—")} for a in alunos]), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum aluno matriculado ainda.")

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
            st.success("Lançamento gravado!"); st.rerun()
        else:
            st.warning("Selecione as contas de Débito e Crédito antes de gravar.")

    lancs = session.exec(select(Lancamento).where(Lancamento.usuario_id == me.id)).all()
    if lancs:
        mapa_nomes = get_mapa_nomes()
        st.divider()
        st.subheader("📋 Lançamentos registrados")
        cab = st.columns([1.2, 2.5, 2.5, 1.5, 2.5, 1.2])
        for col, label in zip(cab, ["Data", "Débito", "Crédito", "Valor", "Histórico", ""]):
            col.markdown(f"<div style='font-size:0.78em;font-weight:700;color:#004b8d;padding-bottom:4px;'>{label}</div>", unsafe_allow_html=True)
        st.markdown("<hr style='margin:0 0 6px 0;border-color:#e0e0e0;'>", unsafe_allow_html=True)
        for l in lancs:
            cols = st.columns([1.2, 2.5, 2.5, 1.5, 2.5, 1.2])
            cols[0].markdown(f"<div style='font-size:0.8em;padding:4px 0;'>{l.data_lancamento}</div>", unsafe_allow_html=True)
            cols[1].markdown(f"<div style='font-size:0.78em;padding:4px 0;color:#c0392b;'>{l.conta_debito} - {mapa_nomes.get(l.conta_debito, l.conta_debito)}</div>", unsafe_allow_html=True)
            cols[2].markdown(f"<div style='font-size:0.78em;padding:4px 0;color:#27ae60;'>{l.conta_credito} - {mapa_nomes.get(l.conta_credito, l.conta_credito)}</div>", unsafe_allow_html=True)
            cols[3].markdown(f"<div style='font-size:0.8em;padding:4px 0;font-weight:600;'>{fmt_moeda(l.valor)}</div>", unsafe_allow_html=True)
            cols[4].markdown(f"<div style='font-size:0.78em;padding:4px 0;color:#555;'>{l.historico or '—'}</div>", unsafe_allow_html=True)
            if cols[5].button("🗑️", key=f"del_{l.id}", help="Excluir lançamento"):
                session.delete(session.get(Lancamento, l.id)); session.commit(); st.rerun()
    botao_imprimir(menu, me, session)

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

elif menu == "Balancete":
    st.header("⚖️ Balancete")
    mov = calcular_movimentacao(me.id)
    if mov:
        st.dataframe(pd.DataFrame([{"Conta": f"{k} - {v['nome']}", "Débito": v['total_debito'], "Crédito": v['total_credito'], "Saldo": v['saldo']} for k, v in mov.items()]), use_container_width=True, hide_index=True)
    botao_imprimir(menu, me, session)

elif menu == "DRE":
    st.header("📉 Demonstração do Resultado do Exercício")
    mov = calcular_movimentacao(me.id)
    rec_bruta_v = deducoes_v = rec_financ_v = custos_v = despesas_v = desp_financ_v = 0.0
    linhas_rec_bruta = []; linhas_deducoes = []; linhas_custos = []
    linhas_despesas = []; linhas_rec_fin = []; linhas_desp_fin = []

    for conta, d in mov.items():
        s = d['saldo']
        nome = f"{conta} - {d['nome']}"
        if conta.startswith('3.1'):
            rec_bruta_v += s; linhas_rec_bruta.append((nome, s))
        elif conta.startswith('3.2'):
            deducoes_v += s; linhas_deducoes.append((nome, s * -1))
        elif conta.startswith('3.3'):
            rec_financ_v += s; linhas_rec_fin.append((nome, s))
        elif conta.startswith('4'):
            custos_v += s; linhas_custos.append((nome, s * -1))
        elif conta.startswith('5'):
            despesas_v += s; linhas_despesas.append((nome, s * -1))
        elif conta.startswith('6.1'):
            desp_financ_v += s; linhas_desp_fin.append((nome, s * -1))

    rec_liquida = rec_bruta_v - deducoes_v
    lucro_bruto = rec_liquida - custos_v
    res_op = lucro_bruto - despesas_v
    res_liq = res_op + rec_financ_v - desp_financ_v

    def bloco_dre(titulo, linhas, subtotal):
        rows = f"<tr><td colspan='2' style='background:#e8f0fe;font-weight:700;font-size:0.82em;padding:7px 10px;color:#004b8d;border-top:2px solid #c5d8f6;'>{titulo}</td></tr>"
        for nome, val in linhas:
            cor_val = "#c0392b" if val < 0 else "#222"
            rows += f"<tr><td style='padding:4px 10px 4px 20px;font-size:0.8em;color:#444;'>{nome}</td><td style='text-align:right;padding:4px 10px;font-size:0.8em;color:{cor_val};white-space:nowrap;'>{fmt_moeda(val)}</td></tr>"
        cor_sub = "#27ae60" if subtotal >= 0 else "#c0392b"
        rows += f"<tr style='background:#f0f4fb;'><td style='text-align:right;padding:3px 10px;font-size:0.78em;color:#555;font-style:italic;'>Subtotal</td><td style='text-align:right;padding:3px 10px;font-size:0.8em;font-weight:600;color:{cor_sub};white-space:nowrap;border-top:1px solid #c5d8f6;'>{fmt_moeda(subtotal)}</td></tr>"
        return rows

    def linha_resultado(label, valor):
        cor = "#27ae60" if valor >= 0 else "#c0392b"
        return f"<tr style='background:#dbeafe;'><td style='padding:6px 10px;font-size:0.83em;font-weight:700;color:#1e40af;'>{label}</td><td style='text-align:right;padding:6px 10px;font-size:0.85em;font-weight:700;color:{cor};white-space:nowrap;'>{fmt_moeda(valor)}</td></tr>"

    rows = ""
    rows += bloco_dre("(+) Receita Operacional Bruta", linhas_rec_bruta, rec_bruta_v)
    rows += bloco_dre("(-) Deduções da Receita", linhas_deducoes, deducoes_v * -1)
    rows += linha_resultado("(=) Receita Operacional Líquida", rec_liquida)
    rows += bloco_dre("(-) Custos (CMV / CSP)", linhas_custos, custos_v * -1)
    rows += linha_resultado("(=) Lucro Bruto", lucro_bruto)
    rows += bloco_dre("(-) Despesas Operacionais", linhas_despesas, despesas_v * -1)
    rows += bloco_dre("(+) Receitas Financeiras", linhas_rec_fin, rec_financ_v)
    rows += bloco_dre("(-) Despesas Financeiras", linhas_desp_fin, desp_financ_v * -1)

    cor_rf = "#27ae60" if res_liq >= 0 else "#c0392b"
    label_final = "LUCRO LÍQUIDO DO EXERCÍCIO" if res_liq >= 0 else "PREJUÍZO DO EXERCÍCIO"
    rows += f"<tr style='background:#004b8d;'><td style='padding:9px 10px;font-size:0.86em;font-weight:700;color:white;'>(=) {label_final}</td><td style='text-align:right;padding:9px 10px;font-size:0.9em;font-weight:700;color:white;white-space:nowrap;'>{fmt_moeda(res_liq)}</td></tr>"

    st.markdown(f"<table style='width:100%;border-collapse:collapse;border:1px solid #dde4f0;border-radius:8px;overflow:hidden;'>{rows}</table>", unsafe_allow_html=True)
    botao_imprimir(menu, me, session)

elif menu == "Balanço":
    st.header("🏛️ Balanço Patrimonial")
    at, pas, _, _, grupos_a, grupos_p, _, nomes_a, nomes_p = gerar_demonstrativos(me.id)

    def render_lado(grupos, nomes_grupos, total_geral):
        rows = ""
        for pfx in sorted(grupos.keys()):
            linhas = grupos[pfx]
            if not linhas: continue
            subtotal = sum(l["Saldo"] for l in linhas)
            nome_grupo = nomes_grupos.get(pfx, pfx)
            rows += f"<tr><td colspan='2' style='background:#e8f0fe;font-weight:700;font-size:0.82em;padding:6px 10px;color:#004b8d;border-top:2px solid #c5d8f6;'>{nome_grupo}</td></tr>"
            for l in linhas:
                rows += f"<tr><td style='padding:4px 10px 4px 20px;font-size:0.8em;color:#444;'>{l['Conta']}</td><td style='text-align:right;padding:4px 10px;font-size:0.8em;color:#222;white-space:nowrap;'>{fmt_moeda(l['Saldo'])}</td></tr>"
            rows += f"<tr style='background:#f0f4fb;'><td style='text-align:right;padding:3px 10px;font-size:0.78em;color:#555;font-style:italic;'>Subtotal</td><td style='text-align:right;padding:3px 10px;font-size:0.8em;font-weight:700;color:#004b8d;white-space:nowrap;border-top:1px solid #c5d8f6;'>{fmt_moeda(subtotal)}</td></tr>"
        rows += f"<tr style='background:#004b8d;'><td style='padding:8px 10px;font-size:0.85em;font-weight:700;color:white;'>TOTAL GERAL</td><td style='text-align:right;padding:8px 10px;font-size:0.88em;font-weight:700;color:white;white-space:nowrap;'>{fmt_moeda(total_geral)}</td></tr>"
        return f"<table style='width:100%;border-collapse:collapse;border:1px solid #dde4f0;border-radius:8px;overflow:hidden;'>{rows}</table>"

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div class='report-header'>ATIVO</div>", unsafe_allow_html=True)
        st.markdown(render_lado(grupos_a, nomes_a, at), unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='report-header'>PASSIVO + PL</div>", unsafe_allow_html=True)
        st.markdown(render_lado(grupos_p, nomes_p, pas), unsafe_allow_html=True)
    botao_imprimir(menu, me, session)