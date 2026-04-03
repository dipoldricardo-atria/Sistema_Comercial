import streamlit as st
import pandas as pd

# --- CONFIGURAÇÃO ---
URL_BASE = "https://docs.google.com/spreadsheets/d/1TUMWuy_EjuMgzMUuT3PUVCP3P-FQA8yDN0Hv4RK46SY/edit?usp=sharing"

# INSIRA AQUI OS GIDs QUE VOCÊ ENCONTROU NA URL DA PLANILHA
GID_USUARIOS = "1357723875" 
GID_VENDAS = "0" # Geralmente a primeira aba é 0, mas confirme na URL

def get_google_sheet(url, gid):
    # Esta função garante que o Python foque na aba correta
    base_url = url.split('/edit')[0]
    return f"{base_url}/export?format=csv&gid={gid}"

# --- SISTEMA DE LOGIN ATUALIZADO ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

def tela_login():
    st.title("🚀 Portal Comercial - Empresa Tech")
    with st.sidebar:
        st.subheader("Login de Acesso")
        email_input = st.text_input("E-mail").strip().lower() # Remove espaços e deixa minúsculo
        senha_input = st.text_input("Senha", type="password")
        
        if st.button("Entrar"):
            try:
                # Lendo especificamente a aba de usuários usando o GID
                link_usuarios = get_google_sheet(URL_BASE, GID_USUARIOS)
                df_users = pd.read_csv(link_usuarios)
                
                # Limpeza de dados para evitar erro de comparação
                df_users['email'] = df_users['email'].str.strip().str.lower()
                df_users['senha'] = df_users['senha'].astype(str).str.strip()
                
                user = df_users[(df_users['email'] == email_input) & (df_users['senha'] == str(senha_input))]
                
                if not user.empty:
                    st.session_state['logged_in'] = True
                    st.session_state['user_info'] = user.iloc[0]
                    st.rerun()
                else:
                    st.error("Usuário ou senha não encontrados na aba 'usuarios'.")
            except Exception as e:
                st.error(f"Erro técnico: {e}")
                st.info("Verifique se o nome das colunas na aba 'usuarios' são: email, senha, nome, perfil")

if not st.session_state['logged_in']:
    tela_login()
# ... (restante do código segue igual)
else:
    user = st.session_state['user_info']
    st.sidebar.success(f"Olá, {user['nome']}")
    if st.sidebar.button("Sair"):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- 3. MENU DE NAVEGAÇÃO (ADMIN vs VENDEDOR) ---
    if user['perfil'] == "Admin":
        menu = st.sidebar.radio("Navegação", ["Dashboard", "Nova Venda", "Baixa de Pagamentos"])
    else:
        menu = st.sidebar.radio("Navegação", ["Minhas Comissões"])

    # --- ABA: DASHBOARD (DENTRO DO IF PERFIL == "ADMIN") ---
if menu == "Dashboard":
    st.title("📊 Painel de Controle Estratégico")
    st.divider()

    try:
        # Lendo a aba de Vendas (Certifique-se de usar o GID da aba vendas)
        df_vendas = pd.read_csv(get_google_sheet(URL_BASE, GID_VENDAS))
        
        if not df_vendas.empty:
            # Cálculos Rápidos
            total_contratado = df_vendas['valor'].sum()
            recebido = df_vendas[df_vendas['status'] == 'Pago']['valor'].sum()
            pendente = df_vendas[df_vendas['status'] == 'Pendente']['valor'].sum()
            comissoes_pagar = df_vendas[df_vendas['status'] == 'Pago']['comissao'].sum()

            # Métricas em Colunas
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total em Contratos", f"R$ {total_contratado:,.2f}")
            c2.metric("Total Recebido", f"R$ {recebido:,.2f}", delta="Fluxo de Caixa")
            c3.metric("Comissões a Pagar", f"R$ {comissoes_pagar:,.2f}", delta_color="inverse")
            c4.error(f"Pendente: R$ {pendente:,.2f}")

            st.divider()
            
            # Tabela Interativa com Destaque
            st.subheader("📋 Detalhamento de Recebíveis")
            
            # Formatação visual: Se status for Pago fica verde, se Pendente fica padrão
            def color_status(val):
                color = 'green' if val == 'Pago' else 'orange'
                return f'color: {color}'

            st.dataframe(df_vendas.style.applymap(color_status, subset=['status']), use_container_width=True)
            
        else:
            st.info("Sua planilha de vendas está vazia. Comece cadastrando um projeto!")
            
    except Exception as e:
        st.error(f"Erro ao carregar dashboard: {e}")

# --- ABA: MINHAS COMISSÕES (VISÃO DO VENDEDOR) ---
elif menu == "Minhas Comissões":
    st.title(f"💰 Extrato de Comissões: {user['nome']}")
    df_vendas = pd.read_csv(get_google_sheet(URL_BASE, GID_VENDAS))
    
    # Filtra apenas as vendas deste vendedor logado
    meus_dados = df_vendas[df_vendas['vendedor'] == user['nome']]
    
    a_receber = meus_dados[meus_dados['status'] == 'Pago']['comissao'].sum()
    st.metric("Minha Comissão Disponível (Pagos)", f"R$ {a_receber:,.2f}")
    
    st.subheader("Histórico de Parcelas")
    st.dataframe(meus_dados)