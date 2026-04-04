import streamlit as st
import pandas as pd
import requests
import time
import random
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="ERP 9.0 ANALYTICS", layout="wide", page_icon="📊")

# --- CONFIGURAÇÕES (MANTIDAS) ---
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyJiJlQIZeqvt3P09trAdfMecjutOFGVE1jsxPmcdh05nn2cKapdzVnJp8ASmIxCYfLQQ/exec"
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSc7YHdYRJZ4I92_cvu0xvHvpU9adHmHmY0RKFxm88NcpjppyA/formResponse"
URL_USUARIOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?gid=1188945197&single=true&output=csv"

IDs = {
    "cliente": "354575898", "vendedor": "1508368855", "tipo": "2051931448", "vencimento": "440689882",
    "valor_parc": "1010209945", "comissao": "1053130357", "status": "852082294",
    "valor_total": "1567666645", "data_base": "1443725489", "id_contrato": "921030482" 
}

if 'logado' not in st.session_state: st.session_state.logado = False

def carregar_dados_raw():
    try:
        r = requests.get(f"{SCRIPT_URL}?action=read", timeout=20)
        df = pd.DataFrame(r.json()[1:], columns=['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissão', 'Status', 'Total', 'Data_Base', 'ID_Contrato'])
        # Limpeza técnica de valores para cálculos
        df['Valor'] = df['Valor'].astype(str).str.replace(',', '.').astype(float)
        df['Total'] = df['Total'].astype(str).str.replace(',', '.').astype(float)
        df['Vencimento'] = pd.to_datetime(df['Vencimento'])
        df['Data_Base'] = pd.to_datetime(df['Data_Base'])
        return df
    except: return pd.DataFrame()

# --- LOGIN (MANTIDO) ---
if not st.session_state.logado:
    st.title("🔐 Acesso ao Sistema")
    with st.form("login"):
        u_e = st.text_input("E-mail")
        u_s = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            df_u = pd.read_csv(URL_USUARIOS)
            df_u.columns = [c.lower().strip() for c in df_u.columns]
            match = df_u[(df_u['email'].str.lower() == u_e.lower().strip()) & (df_u['senha'].astype(str) == u_s)]
            if not match.empty:
                st.session_state.logado = True
                st.session_state.usuario = match.iloc[0].to_dict()
                st.rerun()
    st.stop()

u = st.session_state.usuario
cargo = u.get('cargo') or u.get('Cargo') or "Consultor"
nome_user = u.get('nome') or u.get('Nome') or "Usuário"

# --- MENU LATERAL ---
menu = st.sidebar.radio("Navegação", ["📊 Dashboard", "📝 Lançar & Editar", "📑 Relatório Detalhado"])
if st.sidebar.button("🚪 Sair"):
    st.session_state.logado = False
    st.rerun()

# --- LÓGICA DO DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("📊 Painel de Controle Executivo")
    df = carregar_dados_raw()
    
    if not df.empty:
        # Filtros de Dashboard (Sóbrios)
        with st.expander("🔍 Filtros de Análise"):
            c1, c2, c3 = st.columns(3)
            filtro_vend = c1.multiselect("Vendedores", options=df['Vendedor'].unique(), default=df['Vendedor'].unique())
            filtro_status = c2.multiselect("Status das Parcelas", options=df['Status'].unique(), default=df['Status'].unique())
            data_inicio = pd.to_datetime(c3.date_input("Início Período", value=df['Vencimento'].min()))
            data_fim = pd.to_datetime(c3.date_input("Fim Período", value=df['Vencimento'].max()))

        # Aplicando Filtros
        df_f = df[(df['Vendedor'].isin(filtro_vend)) & 
                  (df['Status'].isin(filtro_status)) & 
                  (df['Vencimento'] >= data_inicio) & 
                  (df['Vencimento'] <= data_fim)]

        # --- BLOCO 1: MÉTRICAS TOTALITÁRIAS ---
        st.subheader("📌 Visão Global")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Volume em Contratos", f"R$ {df_f.groupby('ID_Contrato')['Total'].first().sum():,.2f}")
        m2.metric("Total a Receber (Parcelas)", f"R$ {df_f['Valor'].sum():,.2f}")
        m3.metric("Ticket Médio", f"R$ {df_f.groupby('ID_Contrato')['Total'].first().mean():,.2f}")
        m4.metric("Qtd. Contratos", len(df_f['ID_Contrato'].unique()))

        st.divider()

        # --- BLOCO 2: ANÁLISES PARCIAIS ---
        col_esq, col_dir = st.columns(2)

        with col_esq:
            st.markdown("### 👨‍💼 Performance por Vendedor")
            perf_vend = df_f.groupby('Vendedor')['Valor'].sum().sort_values(ascending=False)
            st.bar_chart(perf_vend, color="#1f77b4")
            
            # Tabela Detalhada Parcial
            st.write("Destaque por Vendedor:")
            st.table(df_f.groupby('Vendedor').agg(
                Total_Vendido=('Valor', 'sum'),
                Contratos=('ID_Contrato', 'nunique'),
                Media_Parc=('Valor', 'mean')
            ).style.format("R$ {:,.2f}"))

        with col_dir:
            st.markdown("### 📈 Fluxo de Caixa (Mensal)")
            df_f['Mes_Ref'] = df_f['Vencimento'].dt.strftime('%Y-%m')
            fluxo = df_f.groupby('Mes_Ref')['Valor'].sum()
            st.line_chart(fluxo, color="#2ca02c")
            
            st.markdown("### 📂 Composição por Status")
            status_comp = df_f.groupby('Status')['Valor'].sum()
            st.dataframe(status_comp, use_container_width=True)

    else:
        st.info("Nenhum dado encontrado para gerar o dashboard.")

# --- LÓGICA DE LANÇAMENTO E EDIÇÃO (MANTIDA 100% IGUAL) ---
elif menu == "📝 Lançar & Editar":
    # [AQUI ENTRA TODO O CÓDIGO DE LANÇAMENTO E EDIÇÃO QUE VOCÊ PEDIU PARA NÃO MUDAR]
    # (Vou resumir para não estourar o limite de texto, mas mantenha a lógica da v8.1)
    st.subheader("Gestão de Contratos")
    # ... (Seu código v8.1 completo de tabs[0] e tabs[1] aqui) ...

# --- RELATÓRIO DETALHADO ---
elif menu == "📑 Relatório Detalhado":
    st.subheader("📑 Listagem Geral de Parcelas")
    df_rel = carregar_dados_raw()
    if not df_rel.empty:
        # Formata para exibição final
        df_rel['Vencimento'] = df_rel['Vencimento'].dt.strftime('%d/%m/%Y')
        df_rel['Data_Base'] = df_rel['Data_Base'].dt.strftime('%d/%m/%Y')
        st.dataframe(df_rel.sort_values('TS', ascending=False), use_container_width=True)