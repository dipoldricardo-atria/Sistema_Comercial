import streamlit as st
import pandas as pd
from datetime import datetime, date

# --- 1. CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Gestão Comercial Tech", layout="wide")

# --- 2. CONFIGURAÇÃO DOS LINKS E GIDs (AJUSTE AQUI) ---
URL_BASE = "https://docs.google.com/spreadsheets/d/1TUMWuy_EjuMgzMUuT3PUVCP3P-FQA8yDN0Hv4RK46SY/edit?usp=sharing"
GID_USUARIOS = "1357723875" 
GID_VENDAS = "0"

def get_google_sheet(url, gid):
    base_url = url.split('/edit')[0]
    return f"{base_url}/export?format=csv&gid={gid}"

# --- 3. LÓGICA DE LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🚀 Portal Comercial - Login")
    with st.sidebar:
        email_input = st.text_input("E-mail").strip().lower()
        senha_input = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            try:
                df_users = pd.read_csv(get_google_sheet(URL_BASE, GID_USUARIOS))
                df_users['email'] = df_users['email'].str.strip().str.lower()
                user = df_users[(df_users['email'] == email_input) & (df_users['senha'].astype(str) == str(senha_input))]
                
                if not user.empty:
                    st.session_state['logged_in'] = True
                    st.session_state['user_info'] = user.iloc[0]
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
            except Exception as e:
                st.error(f"Erro ao acessar base: {e}")
else:
    # --- 4. ÁREA LOGADA ---
    user = st.session_state['user_info']
    st.sidebar.success(f"Logado: {user['nome']}")
    
    # Criamos a variável menu aqui para garantir que ela sempre exista
    if user['perfil'] == "Admin":
        menu = st.sidebar.radio("Navegação", ["Dashboard", "Cadastrar Venda", "Baixa de Pagamentos"])
    else:
        menu = st.sidebar.radio("Navegação", ["Minhas Comissões"])

    if st.sidebar.button("Sair"):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- 5. TELAS DO SISTEMA ---
    if menu == "Dashboard":
        st.title("📊 Painel de Controle (Diretoria)")
        st.divider()
        try:
            df_vendas = pd.read_csv(get_google_sheet(URL_BASE, GID_VENDAS))
            if not df_vendas.empty:
                # Métricas Rápidas
                c1, c2, c3 = st.columns(3)
                c1.metric("Faturamento Total", f"R$ {df_vendas['valor'].sum():,.2f}")
                c2.metric("Comissões Totais", f"R$ {df_vendas['comissao'].sum():,.2f}")
                c3.info(f"Total de {len(df_vendas)} parcelas geradas.")
                
                st.subheader("Lista Geral de Recebíveis")
                st.dataframe(df_vendas, use_container_width=True)
            else:
                st.info("Aba de vendas vazia.")
        except:
            st.error("Erro ao ler aba de vendas. Verifique o GID_VENDAS.")

    elif menu == "Cadastrar Venda":
        st.title("📝 Novo Contrato")
        st.info("Preencha os dados e o sistema gerará o cronograma para você colar na planilha.")
        # ... (O formulário que enviamos anteriormente pode ser colado aqui)

    elif menu == "Minhas Comissões":
        st.title(f"💰 Extrato: {user['nome']}")
        # Lógica para o vendedor ver apenas o dele