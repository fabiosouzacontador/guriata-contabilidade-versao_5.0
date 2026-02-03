import streamlit as st
import pandas as pd
import numpy as np
from datetime import date
from sqlmodel import SQLModel, Field, select, desc, text, create_engine, Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
# BIBLIOTECA EXTERNA REMOVIDA PARA EVITAR ERROS
import warnings
import time

# ==============================================================================
# 1. CONFIGURAÇÕES & DESIGN
# ==============================================================================
warnings.filterwarnings("ignore")
st.set_page_config(page_title="Guriatã Contabilidade", layout="wide", page_icon="🦅")

st.markdown("""
<style>
    /* FONTE UNIFICADA */
    html, body, [class*="css"], .stDataFrame, .kpi-val, .razonete-body, .col-debito, .col-credito {
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important;
    }

    /* Layout Geral */
    .block-container { padding-top: 2rem !important; padding-bottom: 3rem !important; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    
    /* Inputs Modernos */
    .stTextInput>div>div, .stSelectbox>div>div, .stNumberInput>div>div, .stDateInput>div>div, .stTextArea>div>div { 
        border-radius: 8px; border: 1px solid #e0e0e0;
    }
    
    /* CENTRALIZAÇÃO DE LOGO */
    div[data-testid="stImage"] { 
        display: flex; 
        justify-content: center; 
        align-items: center; 
        width: 100%; 
        margin-bottom: 20px; 
    }
    img { object-fit: contain; }

    /* Cards KPI */
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
    
    /* Tabelas */
    .stDataFrame { border: 1px solid #f0f0f0; border-radius: 8px; overflow: hidden; }
    
    /* Razonetes */
    .razonete-container { 
        background: white; border: 1px solid #e0e0e0; border-radius: 8px; 
        margin-bottom: 20px; overflow: hidden; page-break-inside: avoid; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .razonete-header { 
        text-align: center; font-weight: 600; font-size: 0.95em; 
        color: white; background-color: #004b8d; padding: 10px; 
    }
    .razonete-body { display: flex; min-height: 120px; font-size: 1.1em; font-weight: 500; }
    .col-debito { width: 50%; border-right: 1px solid #ddd; text-align: right; padding: 12px; color: #c0392b; }
    .col-credito { width: 50%; text-align: left; padding: 12px; color: #27ae60; }
    
    /* Cabeçalhos */
    .report-header { 
        background-color: #f8f9fa; color: #004b8d; 
        padding: 12px; border-radius: 8px; text-align: center; 
        font-weight: 700; margin-bottom: 15px; border: 1px solid #e9ecef;
    }
    
    /* Aviso Legal */
    .legal-box {
        background-color: #fff3cd; border: 1px solid #ffeeba; color: #856404;
        padding: 20px; border-radius: 8px; font-size: 0.9em; text-align: justify;
        margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }

    /* Impressão */
    @media print {
        [data-testid="stSidebar"] { display: none; }
        .stButton, .stForm, .stSelectbox, .stTextInput, .stNumberInput, .stDateInput, .stTextArea { display: none !important; }
        .imprimir-btn { display: none !important; }
        .block-container { padding-top: 0 !important; }
        .stDataFrame, .razonete-container { display: block !important; width: 100% !important; }
    }
</style>
""", unsafe_allow_html=True)

def botao_imprimir():
    st.markdown("""<div style="text-align: center; margin-top: 30px; margin-bottom: 30px;"><button onclick="window.print()" class="imprimir-btn" style="background-color:#004b8d; color:white; padding:10px 24px; border:none; border-radius:6px; cursor:pointer; font-weight:600; font-size:14px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">🖨️ Imprimir Relatório</button></div>""", unsafe_allow_html=True)

# ==============================================================================
# 2. BANCO DE DADOS & PLANO DE CONTAS MASTER
# ==============================================================================
sqlite_file_name = "database.db"
engine = create_engine(f"sqlite:///{sqlite_file_name}", connect_args={"check_same_thread": False})

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
    # Verifica se já existe o admin
    if not session.exec(select(Usuario).where(Usuario.username=="admin")).first():
        # Verifica se já existe a escola para não duplicar
        esc = session.exec(select(Escola).where(Escola.nome=="Sede Administrativa")).first()
        if not esc:
            esc = Escola(nome="Sede Administrativa", cidade="Matriz")
            session.add(esc)
            session.commit()
            session.refresh(esc)
        
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
        for c, n, t, nat in contas: session.add(ContaContabil(codigo=c, nome=n, tipo=t, natureza=nat))
        session.commit()

def inicializar_banco():
    # Cria as tabelas SE não existirem
    SQLModel.metadata.create_all(engine)
    session = get_session()
    # AQUI: Removi o bloco de 'try/except' que tentava alterar colunas manualmente. 
    # Isso evita o IntegrityError. O create_all já garante a estrutura correta.
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
        resultado[k] = {
            'nome': mapa_nome.get(k, k),
            'natureza': nat,
            'total_debito': v['deb'],
            'total_credito': v['cred'],
            'saldo': saldo
        }
    return resultado

def gerar_demonstrativos(uid):
    mov = calcular_movimentacao(uid)
    lista_balanco = []
    
    rec_bruta = 0.0; deducoes = 0.0; custos = 0.0; despesas_op = 0.0; rec_financ = 0.0; desp_financ = 0.0
    ativo_total = 0.0; passivo_total = 0.0
    
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
            lista_balanco.append({"Conta": f"{conta} - {d['nome']}", "Saldo": saldo, "Grupo": "1"})
        elif conta.startswith('2'):
            passivo_total += saldo
            lista_balanco.append({"Conta": f"{conta} - {d['nome']}", "Saldo": saldo, "Grupo": "2"})

    rec_liquida = rec_bruta - deducoes
    lucro_bruto = rec_liquida - custos
    res_operacional = lucro_bruto - despesas_op
    res_liquido = res_operacional + rec_financ - desp_financ
    
    if res_liquido != 0:
        passivo_total += res_liquido
        lista_balanco.append({"Conta": "Resultado do Exercício", "Saldo": res_liquido, "Grupo": "2"})
    
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

    df_geral = pd.DataFrame(lista_balanco)
    if not df_geral.empty:
        df_a = df_geral[df_geral["Grupo"] == "1"].copy()
        df_p = df_geral[df_geral["Grupo"] == "2"].copy()
    else:
        df_a = pd.DataFrame(columns=["Conta", "Saldo"])
        df_p = pd.DataFrame(columns=["Conta", "Saldo"])
        
    return ativo_total, passivo_total, rec_bruta, res_liquido, df_a, df_p, df_dre

# ==============================================================================
# 4. LOGIN (LOGO 100% CENTRALIZADA)
# ==============================================================================
def login():
    s = get_session()
    u = st.session_state.get("u_log", "").strip()
    p = st.session_state.get("u_pass", "").strip()
    user = s.exec(select(Usuario).where(Usuario.username==u).where(Usuario.senha==p)).first()
    if user: st.session_state["user"] = user; st.rerun()
    else: st.error("Dados incorretos.")

def logout(): st.session_state["user"] = None; st.rerun()

if "user" not in st.session_state or not st.session_state["user"]:
    st.write(""); st.write("")
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        try: st.image("assets/logo.png", width=160) 
        except: pass
        with st.form("login_form", clear_on_submit=True):
            st.text_input("Usuário", key="u_log", placeholder="Usuario")
            st.text_input("Senha", type="password", key="u_pass", placeholder="Senha")
            st.write("") 
            if st.form_submit_button("ENTRAR", type="primary", use_container_width=True): login()
        st.markdown("<div style='text-align: center; color: #bbb; font-size: 0.7em; margin-top: 25px;'>© 2026 Guriatã Educacional</div>", unsafe_allow_html=True)
    st.stop()

session = get_session()
try: me = session.get(Usuario, st.session_state["user"].id)
except: logout(); st.stop()

if not me.termos_aceitos:
    st.write(""); st.write("")
    c1, c2, c3 = st.columns([1, 4, 1])
    with c2:
        st.markdown("""
        <div class="legal-box">
            <h4>⚠️ POLÍTICA DE USO E PRIVACIDADE</h4>
            <p>Este sistema (<b>Guriatã Contabilidade</b>) é um ambiente de simulação acadêmica (Sandbox), desenvolvido estritamente para fins pedagógicos.</p>
            <p><b>1. Dados Proibidos:</b> Em conformidade com a Lei Geral de Proteção de Dados (<b>LGPD - Lei nº 13.709/2018</b>), é terminantemente <b>PROIBIDA</b> a inserção de dados verídicos que identifiquem pessoas físicas ou jurídicas (CPFs, RGs, CNPJs reais, endereços ou dados bancários).</p>
            <p><b>2. Segurança:</b> Este ambiente não utiliza criptografia de nível bancário. O usuário assume total responsabilidade pelo uso de dados fictícios.</p>
            <p>Ao clicar abaixo, você concorda que utilizará apenas dados simulados para suas atividades contábeis.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("✅ Li e Concordo com os Termos", type="primary", use_container_width=True): me.termos_aceitos=True; session.add(me); session.commit(); st.rerun()
    st.stop()

# ==============================================================================
# 5. MENU (MENU NATIVO - SEM ERROS)
# ==============================================================================
with st.sidebar:
    try: st.image("assets/logo.png", width=100)
    except: pass
    st.write(f"Olá, **{me.nome.split()[0]}**")
    st.caption(f"Perfil: {me.perfil.replace('admin', 'Administrador').upper()}")
    
    opts = ["Dashboard", "Meu Perfil"]
    
    if me.perfil == 'admin':
        opts.extend(["Escolas", "Professores", "Turmas", "Alunos"])
        opts.extend(["Escrituração e Diário", "Razonetes", "Balancete", "DRE", "Balanço"]) 

    elif me.perfil == 'professor':
        opts.extend(["Minhas Turmas", "Meus Alunos", "Postar Aulas"])
        opts.extend(["Escrituração e Diário", "Razonetes", "Balancete", "DRE", "Balanço"])
        
    elif me.perfil == 'aluno':
        opts.extend(["Minhas Aulas", "Escrituração e Diário", "Razonetes", "Balancete", "DRE", "Balanço"])
        
    menu = st.sidebar.radio("Navegação", opts, label_visibility="collapsed")
    
    if st.button("Sair do Sistema"): logout()
    
    st.markdown("---")
    if st.button("⚠️ REINICIAR BANCO DE DADOS", type="primary", use_container_width=True):
        st.cache_data.clear()
        SQLModel.metadata.drop_all(engine)
        SQLModel.metadata.create_all(engine)
        session_temp = Session(engine)
        carregar_dados_padrao(session_temp)
        session_temp.close()
        st.success("BANCO RESETADO!")
        time.sleep(1)
        st.rerun()

# ==============================================================================
# 6. CONTEÚDO
# ==============================================================================

if menu == "Dashboard":
    st.title("📊 Painel de Controle")
    if me.perfil == 'admin':
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"<div class='kpi-card'><div class='kpi-title'>Escolas</div><div class='kpi-val'>{len(session.exec(select(Escola)).all())}</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='kpi-card'><div class='kpi-title'>Professores</div><div class='kpi-val'>{len(session.exec(select(Usuario).where(Usuario.perfil=='professor')).all())}</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='kpi-card'><div class='kpi-title'>Alunos</div><div class='kpi-val'>{len(session.exec(select(Usuario).where(Usuario.perfil=='aluno')).all())}</div></div>", unsafe_allow_html=True)
    elif me.perfil == 'professor':
        c1, c2 = st.columns(2)
        nt = len(session.exec(select(Turma).where(Turma.professor_id==me.id)).all())
        na = len(session.exec(select(Usuario).where(Usuario.criado_por_id==me.id)).all())
        c1.markdown(f"<div class='kpi-card'><div class='kpi-title'>Minhas Turmas</div><div class='kpi-val'>{nt}</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='kpi-card'><div class='kpi-title'>Meus Alunos</div><div class='kpi-val'>{na}</div></div>", unsafe_allow_html=True)
    elif me.perfil == 'aluno':
        _, _, rec, luc, _, _, _ = gerar_demonstrativos(me.id)
        c1, c2 = st.columns(2)
        c1.markdown(f"<div class='kpi-card'><div class='kpi-title'>Receita Bruta</div><div class='kpi-val' style='color:green'>{fmt_moeda(rec)}</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='kpi-card'><div class='kpi-title'>Resultado Líquido</div><div class='kpi-val' style='color:{'blue' if luc >=0 else 'red'}'>{fmt_moeda(luc)}</div></div>", unsafe_allow_html=True)

    st.write(""); st.write(""); st.divider()
    st.subheader("📚 Plano de Contas Geral")
    contas_db = session.exec(select(ContaContabil).order_by(ContaContabil.codigo)).all()
    df_contas = pd.DataFrame([{"Código": c.codigo, "Nome": c.nome, "Tipo": "Analítica" if c.tipo=='A' else "Sintética", "Natureza": c.natureza} for c in contas_db])
    st.dataframe(df_contas, use_container_width=True, hide_index=True)

# --- MEU PERFIL (SEGURANÇA ALUNO) ---
elif menu == "Meu Perfil":
    st.header("👤 Meu Perfil")
    with st.form("myprofile"):
        n = st.text_input("Meu Nome", value=me.nome)
        s = st.text_input("Minha Senha", value=me.senha, type="password")
        if me.perfil == 'aluno':
            if st.form_submit_button("💾 Atualizar Senha/Dados"):
                me.nome = n; me.senha = s; session.add(me); session.commit(); st.success("Atualizado!"); time.sleep(1); st.rerun()
        else:
            c1, c2 = st.columns(2)
            if c1.form_submit_button("💾 Atualizar Dados"):
                me.nome = n; me.senha = s; session.add(me); session.commit(); st.success("Atualizado!"); time.sleep(1); st.rerun()
            if c2.form_submit_button("🗑️ Excluir Minha Conta", type="primary"):
                session.delete(me); session.commit(); logout()

# --- GESTÃO ---
elif menu == "Escolas" and me.perfil == 'admin':
    st.header("🏢 Gestão de Escolas")
    tab1, tab2 = st.tabs(["➕ Cadastrar", "⚙️ Gerenciar"])
    with tab1:
        with st.form("ne", clear_on_submit=True):
            n = st.text_input("Nome da Escola"); c = st.text_input("Cidade")
            if st.form_submit_button("Salvar", type="primary"): session.add(Escola(nome=n, cidade=c)); session.commit(); st.success("Salvo!"); st.rerun()
        st.divider(); st.caption("Lista:"); st.dataframe(pd.DataFrame([e.model_dump() for e in session.exec(select(Escola)).all()]), use_container_width=True, hide_index=True)
    with tab2:
        escolas = session.exec(select(Escola)).all()
        esc = st.selectbox("Selecione:", escolas, format_func=lambda x:x.nome)
        if esc:
            with st.form("edte", clear_on_submit=True):
                nn = st.text_input("Nome", value=esc.nome); nc = st.text_input("Cidade", value=esc.cidade)
                c1, c2 = st.columns(2)
                if c1.form_submit_button("💾 Salvar"): e=session.get(Escola, esc.id); e.nome=nn; e.cidade=nc; session.add(e); session.commit(); st.success("Ok!"); st.rerun()
                if c2.form_submit_button("🗑️ Excluir", type="primary"):
                    if session.exec(select(Usuario).where(Usuario.escola_id==esc.id)).first(): st.error("Erro: Vínculos existem.")
                    else: e=session.get(Escola, esc.id); session.delete(e); session.commit(); st.success("Excluído!"); st.rerun()

elif menu == "Professores" and me.perfil == 'admin':
    st.header("👨‍🏫 Gestão de Professores")
    escolas = session.exec(select(Escola)).all()
    tab1, tab2 = st.tabs(["➕ Cadastrar", "⚙️ Gerenciar"])
    with tab1:
        with st.form("np", clear_on_submit=True):
            n = st.text_input("Nome"); u = st.text_input("Login"); s = st.text_input("Senha", type="password"); e = st.selectbox("Escola", escolas, format_func=lambda x:x.nome)
            if st.form_submit_button("Salvar", type="primary"): session.add(Usuario(nome=n, username=u, senha=s, perfil="professor", escola_id=e.id, criado_por_id=me.id)); session.commit(); st.success("Ok!"); st.rerun()
        st.divider(); st.caption("Professores:"); st.dataframe(pd.DataFrame([{"Nome": p.nome, "Login": p.username} for p in session.exec(select(Usuario).where(Usuario.perfil=='professor')).all()]), use_container_width=True, hide_index=True)
    with tab2:
        profs = session.exec(select(Usuario).where(Usuario.perfil=='professor')).all()
        p_sel = st.selectbox("Selecione:", profs, format_func=lambda x:x.nome)
        if p_sel:
            with st.form("edtp", clear_on_submit=True):
                nn = st.text_input("Nome", value=p_sel.nome)
                c1, c2 = st.columns(2)
                if c1.form_submit_button("💾 Salvar"): p=session.get(Usuario, p_sel.id); p.nome=nn; session.add(p); session.commit(); st.success("Ok!"); st.rerun()
                if c2.form_submit_button("🗑️ Excluir", type="primary"):
                    if session.exec(select(Turma).where(Turma.professor_id==p_sel.id)).first(): st.error("Erro: Professor tem turmas.")
                    else: p=session.get(Usuario, p_sel.id); session.delete(p); session.commit(); st.success("Excluído!"); st.rerun()

elif (menu == "Turmas" and me.perfil == 'admin') or (menu == "Minhas Turmas" and me.perfil == 'professor'):
    st.header("🏫 Gestão de Turmas")
    tab1, tab2 = st.tabs(["➕ Cadastrar", "⚙️ Gerenciar"])
    with tab1:
        with st.form("nt", clear_on_submit=True):
            n = st.text_input("Nome Turma"); a = st.text_input("Ano", value="2026")
            if st.form_submit_button("Criar", type="primary"): session.add(Turma(nome=n, ano_letivo=a, professor_id=me.id, escola_id=me.escola_id or 1)); session.commit(); st.success("Criado!"); st.rerun()
    with tab2:
        ts = session.exec(select(Turma).where(Turma.professor_id==me.id) if me.perfil=='professor' else select(Turma)).all()
        if ts: st.dataframe(pd.DataFrame([{"Turma": t.nome, "Ano": t.ano_letivo} for t in ts]), use_container_width=True, hide_index=True)
        t_sel = st.selectbox("Selecione:", ts, format_func=lambda x:x.nome) if ts else None
        if t_sel:
            with st.form("edtt", clear_on_submit=True):
                nn = st.text_input("Nome", value=t_sel.nome)
                c1,c2=st.columns(2)
                if c1.form_submit_button("💾 Salvar"): t=session.get(Turma, t_sel.id); t.nome=nn; session.add(t); session.commit(); st.success("Ok!"); st.rerun()
                if c2.form_submit_button("🗑️ Excluir", type="primary"):
                    if session.exec(select(Usuario).where(Usuario.turma_id==t_sel.id)).first(): st.error("Erro: Turma tem alunos.")
                    else: t=session.get(Turma, t_sel.id); session.delete(t); session.commit(); st.success("Excluído!"); st.rerun()

elif (menu == "Alunos" and me.perfil == 'admin') or (menu == "Meus Alunos" and me.perfil == 'professor'):
    st.header("🎓 Gestão de Alunos")
    turmas = session.exec(select(Turma).where(Turma.professor_id==me.id) if me.perfil=='professor' else select(Turma)).all()
    tab1, tab2 = st.tabs(["➕ Matricular", "⚙️ Gerenciar"])
    with tab1:
        with st.form("na", clear_on_submit=True):
            n = st.text_input("Nome"); u = st.text_input("Login"); s = st.text_input("Senha", type="password"); t = st.selectbox("Turma", turmas, format_func=lambda x:x.nome)
            if st.form_submit_button("Matricular", type="primary"): session.add(Usuario(nome=n, username=u, senha=s, perfil="aluno", turma_id=t.id, criado_por_id=me.id)); session.commit(); st.success("Ok!"); st.rerun()
    with tab2:
        alus = session.exec(select(Usuario).where(Usuario.perfil=='aluno')).all()
        if alus: st.dataframe(pd.DataFrame([{"Nome": a.nome, "Login": a.username} for a in alus]), use_container_width=True, hide_index=True)
        a_sel = st.selectbox("Selecione:", alus, format_func=lambda x:x.nome) if alus else None
        if a_sel:
            with st.form("edta", clear_on_submit=True):
                nn = st.text_input("Nome", value=a_sel.nome)
                c1,c2=st.columns(2)
                if c1.form_submit_button("💾 Salvar"): a=session.get(Usuario, a_sel.id); a.nome=nn; session.add(a); session.commit(); st.success("Ok!"); st.rerun()
                if c2.form_submit_button("🗑️ Excluir", type="primary"):
                    if session.exec(select(Lancamento).where(Lancamento.usuario_id==a_sel.id)).first(): st.error("Erro: Aluno tem lançamentos.")
                    else: a=session.get(Usuario, a_sel.id); session.delete(a); session.commit(); st.success("Excluído!"); st.rerun()

elif menu == "Postar Aulas":
    st.header("📤 Gestão de Aulas")
    turmas = session.exec(select(Turma).where(Turma.professor_id==me.id)).all()
    tab1, tab2 = st.tabs(["➕ Publicar", "⚙️ Gerenciar"])
    with tab1:
        with st.form("pa", clear_on_submit=True):
            ti=st.text_input("Título"); de=st.text_area("Descrição"); tu=st.selectbox("Turma", turmas, format_func=lambda x:x.nome); fl=st.file_uploader("PDF", type=['pdf'])
            if st.form_submit_button("Publicar", type="primary"): session.add(Aula(titulo=ti, descricao=de, turma_id=tu.id, professor_id=me.id, arquivo_blob=fl.read() if fl else None)); session.commit(); st.success("Publicado!"); st.rerun()
    with tab2:
        aulas = session.exec(select(Aula).where(Aula.professor_id==me.id)).all()
        au = st.selectbox("Selecione:", aulas, format_func=lambda x:x.titulo) if aulas else None
        if au:
            with st.form("edtau", clear_on_submit=True):
                t = st.text_input("Título", value=au.titulo); d = st.text_area("Desc", value=au.descricao)
                c1,c2=st.columns(2)
                if c1.form_submit_button("💾 Salvar"): a=session.get(Aula, au.id); a.titulo=t; a.descricao=d; session.add(a); session.commit(); st.success("Ok!"); st.rerun()
                if c2.form_submit_button("🗑️ Excluir", type="primary"): a=session.get(Aula, au.id); session.delete(a); session.commit(); st.success("Excluído!"); st.rerun()

elif menu == "Minhas Aulas":
    st.header("📚 Sala de Aula")
    if not me.turma_id: st.warning("Sem turma.")
    else:
        for a in session.exec(select(Aula).where(Aula.turma_id==me.turma_id).order_by(desc(Aula.id))).all():
            with st.expander(f"📅 {a.data_postagem} - {a.titulo}", expanded=True):
                st.write(a.descricao)
                if a.arquivo_blob: st.download_button("Baixar PDF", data=a.arquivo_blob, file_name="aula.pdf")

# --- CONTABILIDADE (INTEGRADA COM ID VIRTUAL E FORMATAÇÃO BR) ---

elif menu == "Escrituração e Diário":
    st.header("📝 Escrituração e Diário")
    mapa = get_contas_analiticas(); contas = sorted(list(mapa.values()))
    
    st.subheader("Novo Lançamento")
    with st.form("lanc", clear_on_submit=True):
        ce, cd = st.columns(2)
        with ce:
            d = st.date_input("Data", value=date.today(), format="DD/MM/YYYY")
            db = st.selectbox("Débito", contas, index=None); cr = st.selectbox("Crédito", contas, index=None)
        with cd:
            v = st.number_input("Valor (R$)", min_value=0.01, step=10.0, format="%.2f")
            h = st.text_area("Histórico", height=107)
        if st.form_submit_button("Gravar Lançamento", type="primary", use_container_width=True):
            if db and cr and v>0: session.add(Lancamento(data_lancamento=d, valor=v, historico=h, conta_debito=db.split(" - ")[0], conta_credito=cr.split(" - ")[0], usuario_id=me.id)); session.commit(); st.success("Gravado!"); st.rerun()

    st.markdown("---")
    st.subheader("📖 Livro Diário")
    lancs = session.exec(select(Lancamento).where(Lancamento.usuario_id==me.id).order_by(Lancamento.id)).all()
    if lancs:
        mapa_nomes = get_mapa_nomes()
        data_display = []
        for idx, l in enumerate(lancs, start=1):
            # FORMATO BRASILEIRO NO DIARIO
            data_display.append({"ID": idx, "Real_ID": l.id, "Data": l.data_lancamento.strftime("%d/%m/%Y"), 
                                 "Débito": f"{l.conta_debito} - {mapa_nomes.get(l.conta_debito, '')}", 
                                 "Crédito": f"{l.conta_credito} - {mapa_nomes.get(l.conta_credito, '')}", 
                                 "Valor": fmt_moeda(l.valor), "Histórico": l.historico})
        df = pd.DataFrame(data_display)
        st.dataframe(df.drop(columns=["Real_ID"]), use_container_width=True, hide_index=True)
        c1, c2 = st.columns([3, 1])
        with c1: id_selecionado = st.selectbox("Selecione o ID para Excluir:", df["ID"].tolist())
        with c2: 
            st.write(""); st.write("")
            if st.button("🗑️ Excluir Lançamento", type="primary", use_container_width=True): 
                real_id = df.loc[df["ID"] == id_selecionado, "Real_ID"].values[0]
                session.delete(session.get(Lancamento, int(real_id))); session.commit(); st.rerun()
    else: st.info("Nenhum lançamento realizado.")
    botao_imprimir()

elif menu == "Razonetes":
    st.header("🗂️ Razonetes")
    mov = calcular_movimentacao(me.id)
    if not mov: st.info("Sem lançamentos.")
    else:
        cols = st.columns(3); i=0
        for k, v in mov.items():
            titulo = f"{k} - {v['nome']}"
            html = f"""<div class='razonete-container'><div class='razonete-header'>{titulo}</div><div class='razonete-body'><div class='col-debito'>{fmt_moeda(v['total_debito'])}</div><div class='col-credito'>{fmt_moeda(v['total_credito'])}</div></div></div>"""
            cols[i%3].markdown(html, unsafe_allow_html=True); i+=1
    botao_imprimir()

elif menu == "Balancete":
    st.header("⚖️ Balancete de Verificação")
    mov = calcular_movimentacao(me.id)
    if not mov: st.info("Sem dados.")
    else:
        lista = []
        for k, v in mov.items():
            lista.append({"Conta": f"{k} - {v['nome']}", "Total Débitos": fmt_moeda(v['total_debito']), "Total Créditos": fmt_moeda(v['total_credito']), "Saldo Final": fmt_moeda(v['saldo']), "Natureza": v['natureza']})
        st.dataframe(pd.DataFrame(lista), use_container_width=True, hide_index=True)
    botao_imprimir()

elif menu == "DRE":
    st.header("📉 DRE - Demonstração do Resultado")
    _, _, _, _, _, _, df_dre = gerar_demonstrativos(me.id)
    st.dataframe(df_dre[["Descrição", "Valor"]], use_container_width=True, hide_index=True)
    botao_imprimir()

elif menu == "Balanço":
    st.header("🏛️ Balanço Patrimonial")
    at, pas, _, _, df_a, df_p, _ = gerar_demonstrativos(me.id)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div class='report-header'>ATIVO</div>", unsafe_allow_html=True)
        if not df_a.empty:
            df_a["Saldo"] = df_a["Saldo"].apply(fmt_moeda)
            st.dataframe(df_a[["Conta", "Saldo"]], use_container_width=True, hide_index=True)
        st.info(f"TOTAL ATIVO: {fmt_moeda(at)}")
    with c2:
        st.markdown("<div class='report-header'>PASSIVO + PL</div>", unsafe_allow_html=True)
        if not df_p.empty:
            df_p["Saldo"] = df_p["Saldo"].apply(fmt_moeda)
            st.dataframe(df_p[["Conta", "Saldo"]], use_container_width=True, hide_index=True)
        st.warning(f"TOTAL PASSIVO: {fmt_moeda(pas)}")
    botao_imprimir()