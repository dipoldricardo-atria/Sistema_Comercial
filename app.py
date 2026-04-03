import streamlit as st
import pandas as pd
import requests
import time
import urllib.parse
import plotly.express as px
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. CONFIGURAÇÕES ---
st.set_page_config(page_title="ERP Comercial PRO", layout="wide")

GID_VENDAS = "1045730969"
GID_USUARIOS = "1357723875"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwOR4tCPLwpmn28h4TqG-hz4HxM5APUhoZ00TgQ6SVz6rSs79r1rixjmw9K6CoRJFdI/exec"
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScWLZzEh2KOp1aqdjKkhTelImUTL4EJ7KZRr-aryX3N-92aBg/formResponse"

def carregar_dados(gid):
    url = f"https://docs.google.com/spreadsheets/d/1TUMWuy_EjuMgzMUuT3PUVCP3P-FQA8yDN0Hv4RK46SY/export?format=csv&gid={gid}&t={int(time.time())}"
    return pd.read_csv(url)

def limpar_financeiro(val):
    try:
        if isinstance(val, str): return float(val.replace('.', '').replace(',', '.'))
        return float(val)
    except: return 0.0

# --- 2. CONTROLE DE SESSÃO E LOGIN ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🚀 Portal Comercial - Login")
    u_in = st.sidebar.text_input("E-mail").lower().strip()
    s_in = st.sidebar.text_input("Senha", type="password")
    if st.sidebar.button("Entrar"):
        df_u = carregar_dados(GID_USUARIOS)
        user = df_u[(df_u['email'].str.lower() == u_in) & (df_u['senha'].astype(str) == s_in)]
        if not user.empty:
            st.session_state.update({'logged_in': True, 'user_info': user.iloc[0].to_dict(), 
                                    'lista_vendedores': df_u['nome'].unique().tolist(), 'df_usuarios': df_u})
            st.rerun()
        else: st.error("Login inválido.")
else:
    user = st.session_state['user_info']
    perfil_admin = user['perfil'] == "Admin"
    st.sidebar.markdown(f"👤 **{user['nome']}**")
    menu = st.sidebar.radio("Navegação", ["📊 Dashboard Executivo", "📝 Gestão de Vendas", "✅ Baixar Pagamentos"])
    if st.sidebar.button("Sair"): st.session_state.clear(); st.rerun()

    # --- 3. PROCESSAMENTO DOS DADOS (CÁLCULO DE FATURAMENTO) ---
    try:
        df_raw = carregar_dados(GID_VENDAS)
        df_raw.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissao', 'Status']
        df_raw['Val_N'] = df_raw['Valor'].apply(limpar_financeiro)
        df_raw['Data_Venc'] = pd.to_datetime(df_raw['Vencimento'], dayfirst=True)
        
        # AGREGADOR DE CONTRATOS: Agrupamos pelo TS (ID único da venda)
        # O Faturamento Total de um contrato é a soma de suas parcelas (Valor Total do Contrato)
        # A Data Base é a data do primeiro vencimento daquele TS
        df_vendas_consolidadas = df_raw.groupby('TS').agg({
            'Val_N': 'sum',
            'Data_Venc': 'min',
            'Cliente': 'first',
            'Vendedor': 'first',
            'Tipo': 'first'
        }).reset_index().rename(columns={'Val_N': 'Valor_Total_Contrato', 'Data_Venc': 'Data_Base'})
        
        df_vendas_consolidadas['Mes_Base'] = df_vendas_consolidadas['Data_Base'].dt.to_period('M')
        df_raw['Mes_Vencimento'] = df_raw['Data_Venc'].dt.to_period('M')
    except: df_raw = pd.DataFrame(); df_vendas_consolidadas = pd.DataFrame()

    # --- 4. DASHBOARD EXECUTIVO ---
    if menu == "📊 Dashboard Executivo":
        st.title("📊 Gestão Comercial e Financeira")
        
        if not df_vendas_consolidadas.empty:
            # Filtros
            with st.expander("🔍 Filtros do Dashboard", expanded=True):
                m_list = sorted(df_vendas_consolidadas['Mes_Base'].unique())
                m_sel = st.select_slider("Período de Fechamento (Data Base)", options=m_list, value=(m_list[0], m_list[-1]))
                
                df_contratos_f = df_vendas_consolidadas[(df_vendas_consolidadas['Mes_Base'] >= m_sel[0]) & (df_vendas_consolidadas['Mes_Base'] <= m_sel[1])]
                df_parcelas_f = df_raw[(df_raw['Mes_Vencimento'] >= m_sel[0]) & (df_raw['Mes_Vencimento'] <= m_sel[1])]
                
                if not perfil_admin:
                    df_contratos_f = df_contratos_f[df_contratos_f['Vendedor'] == user['nome']]
                    df_parcelas_f = df_parcelas_f[df_parcelas_f['Vendedor'] == user['nome']]

            # KPIs
            st.divider()
            k1, k2, k3 = st.columns(3)
            # AQUI ESTÁ O QUE O SENHOR PEDIU: Soma do Valor Total dos Contratos no período da Data Base
            k1.metric("💰 Faturamento Total (Contratos)", f"R$ {df_contratos_f['Valor_Total_Contrato'].sum():,.2f}")
            k2.metric("✅ Recebido (Caixa)", f"R$ {df_parcelas_f[df_parcelas_f['Status']=='Pago']['Val_N'].sum():,.2f}")
            k3.metric("⏳ Pendente no Período", f"R$ {df_parcelas_f[df_parcelas_f['Status']=='Pendente']['Val_N'].sum():,.2f}")

            # TABELA DE CONTRATOS REAIS
            st.subheader("📝 Contratos Fechados no Período")
            st.dataframe(df_contratos_f[['Data_Base', 'Cliente', 'Vendedor', 'Valor_Total_Contrato', 'Tipo']], use_container_width=True)

            # GRÁFICO DE FLUXO
            st.subheader("📈 Provisão de Recebimentos")
            fig = px.bar(df_parcelas_f.groupby(['Mes_Vencimento', 'Status'])['Val_N'].sum().reset_index(), 
                         x='Mes_Vencimento', y='Val_N', color='Status', barmode='group',
                         color_discrete_map={'Pago': '#2E5A88', 'Pendente': '#A9A9A9'})
            st.plotly_chart(fig, use_container_width=True)

    # --- 5. GESTÃO DE VENDAS (LANÇAMENTO) ---
    elif menu == "📝 Gestão de Vendas":
        st.title("📝 Lançamento de Novos Contratos")
        with st.form("form_venda", clear_on_submit=True):
            c1, c2 = st.columns(2)
            f_cli = c1.text_input("Cliente")
            f_vend = c2.selectbox("Vendedor", st.session_state['lista_vendedores']) if perfil_admin else c2.text_input("Vendedor", user['nome'], disabled=True)
            f_valor = c1.number_input("Valor Total do Contrato", min_value=0.0)
            f_ent = c2.number_input("Entrada", min_value=0.0)
            f_parc = c1.number_input("Parcelas", 0, 60)
            f_data = c2.date_input("Data Base (Data da Venda)")
            
            if st.form_submit_button("🚀 Registrar Contrato"):
                # Lógica de parcelamento
                parcelas = []
                if f_parc == 0: parcelas.append({"t": "À Vista", "v": f_valor, "m": 0})
                else:
                    if f_ent > 0: parcelas.append({"t": "Entrada", "v": f_ent, "m": 0})
                    v_p = (f_valor - f_ent) / f_parc
                    for i in range(1, int(f_parc)+1): parcelas.append({"t": f"Parc {i}/{int(f_parc)}", "v": v_p, "m": i})
                
                for p in parcelas:
                    venc = (f_data + relativedelta(months=p['m'])).strftime('%d/%m/%Y')
                    dados = {"entry.1532857351": f_cli, "entry.1279554151": f_vend, "entry.1633578859": p['t'], "entry.366765493": venc, "entry.1610537227": str(round(p['v'],2)).replace('.',','), "entry.1726017566": "0", "entry.622689505": "Pendente"}
                    requests.post(FORM_URL, data=dados)
                st.success("Venda registrada!"); time.sleep(1); st.rerun()

    # --- 6. BAIXAS ---
    elif menu == "✅ Baixar Pagamentos":
        st.title("✅ Baixa de Parcelas")
        if not perfil_admin: st.error("Acesso restrito"); st.stop()
        df_p = df_raw[df_raw['Status'] == 'Pendente']
        for i, r in df_p.iterrows():
            if st.button(f"Baixar: {r['Cliente']} - {r['Tipo']} (R$ {r['Valor']})", key=f"b_{i}"):
                requests.get(f"{SCRIPT_URL}?row={i+2}&status=Pago")
                st.success("OK!"); time.sleep(0.5); st.rerun()