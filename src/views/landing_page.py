import streamlit as st

def render_landing_page():
    """
    Renderiza a Landing Page do Guriatã.
    Design moderno, focado em conversão para o login.
    """
    
    # --- CSS Personalizado para a Landing Page ---
    st.markdown("""
    <style>
        /* Hero Section */
        .hero-section {
            text-align: center;
            padding: 4rem 1rem;
            background: linear-gradient(135deg, #f0f4f8 0%, #ffffff 100%);
            border-radius: 20px;
            margin-bottom: 3rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        }
        .hero-title {
            font-size: 3.5rem;
            font-weight: 800;
            color: #1a202c;
            margin-bottom: 1rem;
            letter-spacing: -1px;
        }
        .hero-subtitle {
            font-size: 1.25rem;
            color: #4a5568;
            max-width: 700px;
            margin: 0 auto 2rem auto;
            line-height: 1.6;
        }
        .cta-button {
            display: inline-block;
            background-color: #2b6cb0;
            color: white !important;
            padding: 1rem 2.5rem;
            font-size: 1.1rem;
            font-weight: 600;
            border-radius: 50px;
            text-decoration: none;
            transition: all 0.3s ease;
            box-shadow: 0 4px 14px rgba(43, 108, 176, 0.4);
        }
        .cta-button:hover {
            background-color: #2c5282;
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(43, 108, 176, 0.6);
        }
        
        /* Features Grid */
        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            margin: 3rem 0;
        }
        .feature-card {
            background: white;
            padding: 2rem;
            border-radius: 15px;
            border: 1px solid #e2e8f0;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .feature-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            border-color: #2b6cb0;
        }
        .feature-icon {
            font-size: 2.5rem;
            margin-bottom: 1rem;
            display: block;
        }
        .feature-title {
            font-size: 1.25rem;
            font-weight: 700;
            color: #2d3748;
            margin-bottom: 0.5rem;
        }
        .feature-desc {
            color: #718096;
            font-size: 0.95rem;
            line-height: 1.5;
        }

        /* Audience Section */
        .audience-section {
            background-color: #edf2f7;
            padding: 3rem 2rem;
            border-radius: 20px;
            margin-top: 3rem;
            text-align: center;
        }
        .badge {
            display: inline-block;
            padding: 0.5rem 1rem;
            background-color: #bee3f8;
            color: #2b6cb0;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.9rem;
            margin: 0.5rem;
        }
        
        /* Footer */
        .footer {
            text-align: center;
            margin-top: 4rem;
            padding-top: 2rem;
            border-top: 1px solid #e2e8f0;
            color: #a0aec0;
            font-size: 0.9rem;
        }
        
        /* Responsividade */
        @media (max-width: 768px) {
            .hero-title { font-size: 2.5rem; }
            .features-grid { grid-template-columns: 1fr; }
        }
    </style>
    """, unsafe_allow_html=True)

    # --- Hero Section ---
    st.markdown("""
    <div class="hero-section">
        <h1 class="hero-title">🦅 Guriatã</h1>
        <p class="hero-subtitle">
            A plataforma definitiva para aprendizado prático de contabilidade. 
            Gerencie lançamentos, visualize razonetes automaticamente e gere demonstrativos financeiros em segundos.
        </p>
        <div style="margin-top: 2rem;">
            <a href="#login" id="start-btn" class="cta-button">Começar Agora →</a>
        </div>
        <p style="margin-top: 1rem; font-size: 0.9rem; color: #718096;">
            <i>Acesso gratuito para fins educacionais</i>
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Script para scroll suave até o login (hack simples para Streamlit)
    st.markdown(
        """
        <script>
            const btn = document.getElementById('start-btn');
            if(btn) {
                btn.addEventListener('click', () => {
                    document.querySelector('.stSidebar').scrollIntoView({ behavior: 'smooth' });
                });
            }
        </script>
        """, 
        unsafe_allow_html=True
    )

    # --- Features Section ---
    st.markdown("### 🚀 Por que usar o Guriatã?")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <span class="feature-icon">📊</span>
            <h3 class="feature-title">Razonetes Visuais</h3>
            <p class="feature-desc">Visualize o movimento de cada conta em formato T clássico, atualizado em tempo real a cada lançamento.</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        <div class="feature-card">
            <span class="feature-icon">📑</span>
            <h3 class="feature-title">Relatórios Automáticos</h3>
            <p class="feature-desc">Gere Balancetes, DRE (Demonstrativo de Resultado) e Balanço Patrimonial com um único clique.</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown("""
        <div class="feature-card">
            <span class="feature-icon">🛡️</span>
            <h3 class="feature-title">Segurança & Controle</h3>
            <p class="feature-desc">Sistema de login com níveis de acesso (Aluno, Professor, Admin) e histórico de operações.</p>
        </div>
        """, unsafe_allow_html=True)

    # --- Audience Section ---
    st.markdown("""
    <div class="audience-section">
        <h2 style="color: #2d3748; margin-bottom: 1.5rem;">Feito para Educação Contábil</h2>
        <div>
            <span class="badge">🎓 Estudantes</span>
            <span class="badge">👨‍🏫 Professores</span>
            <span class="badge">🏫 Instituições de Ensino</span>
        </div>
        <p style="margin-top: 1.5rem; color: #4a5568; max-width: 600px; margin-left: auto; margin-right: auto;">
            Ideal para aulas práticas de Introdução à Contabilidade, Análise das Demonstrações Financeiras e Laboratório de Contabilidade.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # --- Footer ---
    st.markdown("""
    <div class="footer">
        <p>© 2024 Guriatã - Sistema Educacional de Contabilidade.</p>
        <p>Desenvolvido com ❤️ e Python.</p>
    </div>
    """, unsafe_allow_html=True)

    # --- Ponto de Ancoragem para Login ---
    st.markdown("<div id='login'></div>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Instrução para o usuário
    st.info("👈 **Faça login na barra lateral** para acessar o sistema.")
