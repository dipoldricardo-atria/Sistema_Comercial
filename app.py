import streamlit as st
from streamlit_gsheets import GSheetsConnection

# 1. Configuração de Tela
st.set_page_config(page_title="Gestão Comercial Tech", layout="wide")

# 2. Conexão com a Planilha (COLE SEU LINK AQUI)
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1TUMWuy_EjuMgzMUuT3PUVCP3P-FQA8yDN0Hv4RK46SY/edit?usp=sharing"

st.title("🚀 Sistema Comercial - Teste de Conexão")

try:
    # Cria a ponte com o Google Sheets
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Tenta ler a aba de usuários
    df_usuarios = conn.read(spreadsheet=URL_PLANILHA, worksheet="usuarios")
    
    st.success("✅ Conexão com o Google Sheets estabelecida!")
    st.subheader("Lista de Usuários Cadastrados:")
    st.dataframe(df_usuarios)
    
except Exception as e:
    st.error("❌ Erro na conexão.")
    st.write(f"Detalhes: {e}")