import streamlit as st
import pandas as pd
import requests
import time
import plotly.express as px
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="ERP Comercial PRO", layout="wide")

URL_BASE = "https://docs.google.com/spreadsheets/d/1TUMWuy_EjuMgzMUuT3PUVCP3P-FQA8yDN0Hv4RK46SY/edit?usp=sharing"
GID_VENDAS = "1045730969"
GID_USUARIOS = "1357723875"
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScWLZzEh2KOp1aqdjKkhTelImUTL4EJ7KZRr-aryX3N-92aBg/formResponse"

def carregar_dados(gid):
    url = f"https://docs.google.com/spreadsheets/d/1TUMWuy_EjuMgzMUuT3PUVCP3P-FQA8yDN0Hv4RK46SY/export?format=csv&gid={gid}&t={int(time.time())}"
    return pd.read_csv(url)

def limpar_financeiro(val):
    try:
        if isinstance(val, str): return float(val.replace('.', '').replace(',', '.'))
        return float(val)
    except: return 0.0

# --- PROCESSAMENTO ---
try:
    df_raw = carregar_dados(GID_VENDAS)
    # Supondo que a estrutura da planilha tenha o Valor Total e a Data Base
    # TS é usado como ID único do contrato para evitar duplicidade na soma do valor total
    df_raw.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor_Parcela', 'Comissao', 'Status', 'Valor_Total_Contrato', 'Data_Base']
    
    df_raw['Val_Parcela_N'] = df_raw['Valor_Parcela'].apply(limpar_financeiro)
    df_raw['Val_Total_N'] = df_raw['Valor_Total_Contrato'].apply(limpar_financeiro)
    df_raw['Data_Venc'] = pd.to_datetime(df_raw['Vencimento'], dayfirst=True)
    df_raw['Data_Base_DT'] = pd.to_datetime(df_raw['Data_Base'], dayfirst=True)
    
    # Criamos períodos para filtros
    df_raw['Mes_Base'] = df_raw['Data_Base_DT'].dt.to_period('M')
    df_raw['Mes_Vencimento'] = df_raw['Data_Venc'].dt.to_period('M')

    # TABELA DE CONTRATOS ÚNICOS (1 linha por contrato/TS)
    # Aqui pegamos o valor total direto do campo, sem somar parcelas
    df_contratos = df_raw.drop_duplicates(subset=['TS'])
except Exception as e:
    st.error(f"Erro ao processar colunas: {e}")
    df_raw = pd.DataFrame()
    df_contratos = pd.DataFrame()

# --- DASHBOARD ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
# ... (lógica de login permanece a mesma)

if st.session_state['logged_in']:
    menu = st.sidebar.radio("Navegação", ["📊 Dashboard Executivo", "📝 Gestão de Vendas"])

    if menu == "📊 Dashboard Executivo":
        st.title("📊 Painel de Controle Gerencial")
        
        m_list = sorted(df_raw['Mes_Base'].unique())
        m_sel = st.select_slider("Selecione o Mês de Referência (Data Base)", options=m_list, value=(m_list[0], m_list[-1]))

        # KPI 1: FATURAMENTO (Baseado no campo Valor Total do Contrato e Data Base)
        faturamento_total = df_contratos[
            (df_contratos['Mes_Base'] >= m_sel[0]) & 
            (df_contratos['Mes_Base'] <= m_sel[1])
        ]['Val_Total_N'].sum()

        # KPI 2: RECEBIDO (Baseado no vencimento e status das parcelas)
        total_pago = df_raw[
            (df_raw['Mes_Vencimento'] >= m_sel[0]) & 
            (df_raw['Mes_Vencimento'] <= m_sel[1]) & 
            (df_raw['Status'] == 'Pago')
        ]['Val_Parcela_N'].sum()

        col1, col2 = st.columns(2)
        col1.metric("💰 Faturamento Bruto (Contratos Fechados)", f"R$ {faturamento_total:,.2f}")
        col2.metric("✅ Caixa Realizado (Parcelas Pagas)", f"R$ {total_pago:,.2f}")

        st.info("O Faturamento Bruto considera o valor integral dos contratos assinados no período selecionado.")

    elif menu == "📝 Gestão de Vendas":
        # No formulário de lançamento, passamos a salvar o Valor Total em uma coluna fixa
        with st.form("venda_form"):
            # ... campos de entrada ...
            # Ao salvar, o script enviará o 'valor_total' para todas as linhas de parcelas daquele contrato
            # permitindo que o drop_duplicates('TS') funcione corretamente no Dashboard.
            pass