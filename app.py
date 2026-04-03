import streamlit as st
import pandas as pd
import requests
import time
import plotly.express as px
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. CONFIGURAÇÕES ---
st.set_page_config(page_title="ERP Comercial PRO", layout="wide")

URL_BASE = "https://docs.google.com/spreadsheets/d/1TUMWuy_EjuMgzMUuT3PUVCP3P-FQA8yDN0Hv4RK46SY/edit?usp=sharing"
GID_VENDAS = "1045730969"
GID_USUARIOS = "1357723875"

def carregar_dados(gid):
    url = f"https://docs.google.com/spreadsheets/d/1TUMWuy_EjuMgzMUuT3PUVCP3P-FQA8yDN0Hv4RK46SY/export?format=csv&gid={gid}&t={int(time.time())}"
    return pd.read_csv(url)

def limpar_financeiro(val):
    try:
        if isinstance(val, str): return float(val.replace('.', '').replace(',', '.'))
        return float(val)
    except: return 0.0

# --- 2. CÉREBRO DOS DADOS (AQUI ESTÁ A CORREÇÃO) ---
try:
    df_raw = carregar_dados(GID_VENDAS)
    # Ajustado exatamente para as 8 colunas que você tem hoje
    df_raw.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissao', 'Status']
    
    df_raw['Val_N'] = df_raw['Valor'].apply(limpar_financeiro)
    df_raw['Data_Venc'] = pd.to_datetime(df_raw['Vencimento'], dayfirst=True)
    
    # --- LÓGICA DE CONTRATO (VALOR TOTAL) ---
    # 1. Somamos todas as parcelas que possuem o mesmo ID (TS) para saber o Valor Total do Contrato
    df_total_contratos = df_raw.groupby('TS')['Val_N'].sum().reset_index().rename(columns={'Val_N': 'Valor_Total_Contrato'})
    
    # 2. Identificamos a Data Base (A menor data de vencimento de cada contrato é a data da venda)
    df_data_base = df_raw.groupby('TS')['Data_Venc'].min().reset_index().rename(columns={'Data_Venc': 'Data_Base'})
    
    # 3. Unimos essas informações em uma visão única de CONTRATOS (sem repetição de parcelas)
    df_contratos_unicos = pd.merge(df_total_contratos, df_data_base, on='TS')
    
    # Adicionamos o nome do cliente e vendedor para filtros
    df_info_extra = df_raw.drop_duplicates('TS')[['TS', 'Cliente', 'Vendedor']]
    df_contratos_unicos = pd.merge(df_contratos_unicos, df_info_extra, on='TS')
    
    # Criamos os períodos de faturamento (Mês da Data Base)
    df_contratos_unicos['Mes_Base'] = df_contratos_unicos['Data_Base'].dt.to_period('M')
    df_raw['Mes_Vencimento'] = df_raw['Data_Venc'].dt.to_period('M')

except Exception as e:
    st.error(f"Erro no processamento: {e}")
    df_raw = pd.DataFrame()
    df_contratos_unicos = pd.DataFrame()

# --- 3. DASHBOARD ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
# ... (supondo login já realizado)

if not st.session_state['logged_in']:
    # Bloco de login (simplificado para o exemplo)
    st.title("🚀 Portal de Vendas")
    if st.sidebar.button("Simular Login"): st.session_state['logged_in'] = True; st.rerun()
else:
    st.title("📊 Visão Geral do Faturado (Contratos)")
    
    if not df_contratos_unicos.empty:
        # Filtro de Período
        m_list = sorted(df_contratos_unicos['Mes_Base'].unique())
        m_sel = st.select_slider("Selecione o Mês da Venda", options=m_list, value=(m_list[0], m_list[-1]))
        
        # --- CÁLCULO DO FATURAMENTO REAL ---
        # Filtramos os contratos únicos pela Data Base dentro do período selecionado
        mask_contratos = (df_contratos_unicos['Mes_Base'] >= m_sel[0]) & (df_contratos_unicos['Mes_Base'] <= m_sel[1])
        faturamento_bruto = df_contratos_unicos[mask_contratos]['Valor_Total_Contrato'].sum()
        qtd_vendas = len(df_contratos_unicos[mask_contratos])

        # --- CÁLCULO DO CAIXA REALIZADO ---
        # Aqui olhamos para a planilha de parcelas (df_raw) buscando o que foi pago NO PERÍODO
        mask_caixa = (df_raw['Mes_Vencimento'] >= m_sel[0]) & (df_raw['Mes_Vencimento'] <= m_sel[1])
        total_recebido = df_raw[mask_caixa & (df_raw['Status'] == 'Pago')]['Val_N'].sum()

        # EXIBIÇÃO DOS INDICADORES
        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 Faturamento Bruto (Contratos)", f"R$ {faturamento_bruto:,.2f}")
        c2.metric("✅ Total Realizado (Caixa)", f"R$ {total_recebido:,.2f}")
        c3.metric("🤝 Novos Contratos", qtd_vendas)

        st.info(f"O Faturamento Bruto de **R$ {faturamento_bruto:,.2f}** representa o valor total dos contratos fechados entre {m_sel[0]} e {m_sel[1]}, independente do número de parcelas.")

        # Tabela de Contratos (O que o senhor sentiu falta)
        st.subheader("📝 Relação de Contratos Fechados")
        df_tabela = df_contratos_unicos[mask_contratos][['Data_Base', 'Cliente', 'Vendedor', 'Valor_Total_Contrato']]
        df_tabela['Data_Base'] = df_tabela['Data_Base'].dt.strftime('%d/%m/%Y')
        st.dataframe(df_tabela, use_container_width=True)