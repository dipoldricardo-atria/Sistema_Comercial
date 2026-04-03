import streamlit as st
import pandas as pd
import requests
import time
import urllib.parse
import plotly.express as px
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. CONFIGURAÇÕES E IDs FIXOS ---
st.set_page_config(page_title="ERP Comercial PRO", layout="wide", page_icon="🚀")

# IDs das entradas do seu formulário (conforme identificado anteriormente)
ID_VALOR_TOTAL = "1849135056"
ID_DATA_BASE = "925681697"

URL_BASE = "https://docs.google.com/spreadsheets/d/1TUMWuy_EjuMgzMUuT3PUVCP3P-FQA8yDN0Hv4RK46SY/edit?usp=sharing"
GID_VENDAS = "1045730969"
GID_USUARIOS = "1357723875"
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScWLZzEh2KOp1aqdjKkhTelImUTL4EJ7KZRr-aryX3N-92aBg/formResponse"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwOR4tCPLwpmn28h4TqG-hz4HxM5APUhoZ00TgQ6SVz6rSs79r1rixjmw9K6CoRJFdI/exec"

def carregar_dados(gid):
    try:
        url = f"https://docs.google.com/spreadsheets/d/1TUMWuy_EjuMgzMUuT3PUVCP3P-FQA8yDN0Hv4RK46SY/export?format=csv&gid={gid}&t={int(time.time())}"
        return pd.read_csv(url)
    except:
        return pd.DataFrame()

def limpar_financeiro(val):
    try:
        if isinstance(val, str): return float(val.replace('.', '').replace(',', '.'))
        return float(val)
    except: return 0.0

# --- 2. CONTROLE DE ACESSO ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'venda_baixada' not in st.session_state: st.session_state['venda_baixada'] = None

if not st.session_state['logged_in']:
    st.title("🚀 Portal Comercial - Login")
    u_in = st.sidebar.text_input("E-mail").lower().strip()
    s_in = st.sidebar.text_input("Senha", type="password")
    if st.sidebar.button("Entrar"):
        df_u = carregar_dados(GID_USUARIOS)
        if not df_u.empty:
            user = df_u[(df_u['email'].str.lower() == u_in) & (df_u['senha'].astype(str) == s_in)]
            if not user.empty:
                st.session_state.update({'logged_in': True, 'user_info': user.iloc[0].to_dict(), 
                                        'lista_vendedores': df_u['nome'].unique().tolist(), 'df_usuarios': df_u})
                st.rerun()
            else: st.error("Acesso negado.")
        else: st.error("Erro ao carregar banco de usuários.")
else:
    user = st.session_state['user_info']
    perfil_admin = user['perfil'] == "Admin"
    st.sidebar.markdown(f"👤 **{user['nome']}**")
    menu = st.sidebar.radio("Navegação", ["📊 Dashboard Executivo", "📝 Gestão de Vendas", "✅ Baixar Pagamentos"])
    if st.sidebar.button("Sair"): st.session_state.clear(); st.rerun()

    # --- 3. PROCESSAMENTO 10 COLUNAS ---
    df_raw = carregar_dados(GID_VENDAS)
    if not df_raw.empty and len(df_raw.columns) >= 10:
        df = df_raw.iloc[:, :10].copy()
        df.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor_Parc', 'Comissao', 'Status', 'Valor_Total', 'Data_Base']
        df['Val_P_N'] = df['Valor_Parc'].apply(limpar_financeiro)
        df['Val_T_N'] = df['Valor_Total'].apply(limpar_financeiro)
        df['DB_Date'] = pd.to_datetime(df['Data_Base'], dayfirst=True, errors='coerce')
        df['DV_Date'] = pd.to_datetime(df['Vencimento'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['DB_Date', 'DV_Date'])
        df['Mes_Base'] = df['DB_Date'].dt.to_period('M')
        df['Mes_Venc'] = df['DV_Date'].dt.to_period('M')
    else:
        df = pd.DataFrame()

    # --- 4. DASHBOARD EXECUTIVO ---
    if menu == "📊 Dashboard Executivo":
        st.title("📊 Inteligência Comercial")
        if df.empty:
            st.info("Nenhuma venda encontrada. Comece registrando uma nova venda na aba 'Gestão de Vendas'.")
        else:
            df_dash = df.copy() if perfil_admin else df[df['Vendedor'] == user['nome']]
            tipo_v = st.radio("Visão por:", ["Mês de Fechamento (Data Base)", "Mês de Vencimento (Fluxo de Caixa)"], horizontal=True)
            col_data = 'Mes_Base' if tipo_v == "Mês de Fechamento (Data Base)" else 'Mes_Venc'
            m_list = sorted(df[col_data].unique())
            m_sel = st.select_slider("Selecione o Período", options=m_list, value=(m_list[0], m_list[-1]))
            df_filtrado = df_dash[(df_dash[col_data] >= m_sel[0]) & (df_dash[col_data] <= m_sel[1])]

            df_fat_real = df_filtrado.drop_duplicates('TS')
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("💰 Faturado (Total)", f"R$ {df_fat_real['Val_T_N'].sum():,.2f}")
            m2.metric("✅ Recebido (Caixa)", f"R$ {df_filtrado[df_filtrado['Status']=='Pago']['Val_P_N'].sum():,.2f}")
            m3.metric("⏳ A Receber", f"R$ {df_filtrado[df_filtrado['Status']=='Pendente']['Val_P_N'].sum():,.2f}")
            m4.metric("📈 Novos Contratos", len(df_fat_real))

    # --- 5. GESTÃO DE VENDAS ---
    elif menu == "📝 Gestão de Vendas":
        st.title("📝 Central de Lançamentos")
        aba = st.tabs(["🚀 Novo Contrato", "✏️ Editar/Corrigir"])

        with aba[0]:
            with st.form("venda_form", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                f_cli = c1.text_input("Nome do Cliente")
                f_vend = c2.selectbox("Vendedor", st.session_state['lista_vendedores']) if perfil_admin else c2.text_input("Vendedor", user['nome'], disabled=True)
                f_data = c3.date_input("Data do Fechamento (Data Base)")
                
                f_total = c1.number_input("Valor TOTAL do Contrato", min_value=0.0, step=100.0)
                f_entrada = c2.number_input("Valor da ENTRADA", min_value=0.0, step=100.0)
                f_parc = c3.number_input("Parcelas RESTANTES (0 = Recorrência)", min_value=0, value=1)
                
                if st.form_submit_button("🚀 Registrar Contrato"):
                    # Processamento da Entrada
                    if f_entrada > 0:
                        pld_e = {
                            "entry.1532857351": f_cli, "entry.1279554151": f_vend, "entry.1633578859": "Entrada",
                            "entry.366765493": f_data.strftime('%d/%m/%Y'), 
                            "entry.1610537227": str(round(f_entrada,2)).replace('.',','),
                            "entry.622689505": "Pendente",
                            f"entry.{ID_VALOR_TOTAL}": str(round(f_total,2)).replace('.',','),
                            f"entry.{ID_DATA_BASE}": f_data.strftime('%d/%m/%Y')
                        }
                        requests.post(FORM_URL, data=pld_e)
                    
                    # Processamento das Parcelas
                    saldo = f_total - f_entrada
                    loops = 1 if f_parc == 0 else int(f_parc)
                    v_p = saldo / loops if f_parc > 0 else f_total
                    
                    for i in range(loops):
                        # Se houver entrada, a primeira parcela vence no mês seguinte. Se não, no mês atual.
                        venc_dt = f_data + relativedelta(months=i+1 if f_entrada > 0 else i)
                        tipo_p = f"Parc {i+1}/{int(f_parc)}" if f_parc > 0 else "Mensalidade (Recorrente)"
                        
                        pld_p = {
                            "entry.1532857351": f_cli, "entry.1279554151": f_vend, "entry.1633578859": tipo_p,
                            "entry.366765493": venc_dt.strftime('%d/%m/%Y'), 
                            "entry.1610537227": str(round(v_p,2)).replace('.',','),
                            "entry.622689505": "Pendente",
                            f"entry.{ID_VALOR_TOTAL}": str(round(f_total,2)).replace('.',','),
                            f"entry.{ID_DATA_BASE}": f_data.strftime('%d/%m/%Y')
                        }
                        requests.post(FORM_URL, data=pld_p)
                    
                    st.success("🎉 Contrato enviado com sucesso! Aguarde alguns segundos para a planilha atualizar.")
                    time.sleep(2)
                    st.rerun()

    # --- 6. BAIXAS ---
    elif menu == "✅ Baixar Pagamentos":
        st.title("✅ Conciliação Financeira")
        if not perfil_admin: st.error("Acesso restrito."); st.stop()

        if not df.empty:
            pendentes = df[df['Status'] == 'Pendente']
            if pendentes.empty:
                st.write("Não há pagamentos pendentes.")
            else:
                for i, r in pendentes.iterrows():
                    with st.expander(f"{r['Cliente']} | {r['Tipo']} | R$ {r['Valor_Parc']}"):
                        if st.button("Confirmar Baixa", key=f"bx_{i}"):
                            requests.get(f"{SCRIPT_URL}?row={i+2}&status=Pago")
                            st.success(f"Baixa realizada para {r['Cliente']}")
                            time.sleep(1)
                            st.rerun()