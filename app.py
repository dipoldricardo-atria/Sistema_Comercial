import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- 1. CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="Sistema de Gestão Comercial", layout="wide")

# Coordenadas do Banco de Dados
URL_BASE = "https://docs.google.com/spreadsheets/d/1TUMWuy_EjuMgzMUuT3PUVCP3P-FQA8yDN0Hv4RK46SY/edit?usp=sharing"
GID_USUARIOS = "1357723875" 
GID_VENDAS = "1045730969"   

# URL do Formulário para Cadastrar Novas Vendas
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScWLZzEh2KOp1aqdjKkhTelImUTL4EJ7KZRr-aryX3N-92aBg/formResponse"

# URL do seu Apps Script para dar Baixa (Status)
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbweRlD1BLcYkmwNCq3yJdttmtDaWlZkVu8kB837i9rSi97Wih9m_09SG_l3PSX_wzI/exec"

def get_google_sheet(url, gid):
    base_url = url.split('/edit')[0]
    return f"{base_url}/export?format=csv&gid={gid}"

def limpar_financeiro(val):
    try:
        if isinstance(val, str):
            # Converte formato BR (1.500,50) para float (1500.50)
            return float(val.replace('.', '').replace(',', '.'))
        return float(val)
    except: return 0.0

# --- 2. LÓGICA DE LOGIN ---
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
                df_users['email'] = df_users['email'].astype(str).str.strip().str.lower()
                user = df_users[(df_users['email'] == email_input) & (df_users['senha'].astype(str) == str(senha_input))]
                if not user.empty:
                    st.session_state['logged_in'] = True
                    st.session_state['user_info'] = user.iloc[0].to_dict()
                    st.rerun()
                else: st.error("Usuário ou senha incorretos.")
            except Exception as e: st.error(f"Erro ao acessar base: {e}")
else:
    user = st.session_state['user_info']
    st.sidebar.success(f"Conectado: {user['nome']}")
    
    # Menu dinâmico por perfil
    if user['perfil'] == "Admin":
        menu = st.sidebar.radio("Navegação", ["📊 Dashboard", "📝 Cadastrar Venda", "✅ Baixa de Pagamentos"])
    else:
        menu = st.sidebar.radio("Navegação", ["💰 Minhas Comissões", "📝 Cadastrar Venda"])

    if st.sidebar.button("Sair"):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- 3. CARREGAMENTO GLOBAL DE DADOS ---
    try:
        df_vendas = pd