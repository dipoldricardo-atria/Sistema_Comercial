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

URL_BASE = "https://docs.google.com/spreadsheets/d/1TUMWuy_EjuMgzMUuT3PUVCP3P-FQA8yDN0Hv4RK46SY/edit?usp=sharing"
GID_VENDAS = "1045730969"
GID_USUARIOS = "1357723875"
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScWLZzEh2KOp1aqdjKkhTelImUTL4EJ7KZRr-aryX3N-92aBg/formResponse"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwOR4tCPLwpmn28h4TqG-hz4HxM5APUhoZ00TgQ6SVz6rSs79r1rixjmw9K6CoRJFdI/exec"

def carregar_dados(gid):
    url = f"https://docs.google.com/spreadsheets/d/1TUMWuy_EjuMgzMUuT3PUVCP3P-FQA8yDN0Hv4RK46SY/export?format=csv&gid={gid}&t={int(time.time())}"
    return pd.read_csv(url)

def limpar_financeiro(val):
    try:
        if isinstance(val, str): return float(val.replace('.', '').replace(',', '.'))
        return float(val)
    except: return 0.0

# --- 2. CONTROLE DE SESSÃO ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'venda_baixada' not in st.session_state: st.session_state['venda_baixada'] = None

if not st.session_state['logged_in']:
    st.title("🚀 Portal Comercial - Login")
    u_in = st.sidebar.text_input("E-mail").lower().strip()
    s_in = st.sidebar.text_input("Senha", type="password")
    if st.sidebar.button("Entrar"):
        df_u = carregar_dados(GID_USUARIOS)
        user_db = df_u[(df_u['email'].str.lower() == u_in) & (df_u['senha'].astype(str) == s_in)]
        if not user_db.empty:
            st.session_state.update({
                'logged_in': True, 
                'user_info': user_db.iloc[0].to_dict(), 
                'lista_vendedores': df_u['nome'].unique().tolist(),
                'df_usuarios': df_u
            })
            st.rerun()
        else: st.error("Acesso negado.")
else:
    user = st.session_state['user_info']
    perfil_admin = user['perfil'] == "Admin"
    st.sidebar.markdown(f"👤 **{user['nome']}**")
    menu = st.sidebar.radio("Navegação", ["📊 Dashboard Executivo", "📝 Gestão de Vendas", "✅ Baixar Pagamentos"])
    if st.sidebar.button("Sair"): st.session_state.clear(); st.rerun()

    # --- 3. PROCESSAMENTO 10 COLUNAS (BLINDADO) ---
    try:
        df_raw = carregar_dados(GID_VENDAS)
        # Forçamos a leitura apenas das primeiras 10 colunas (A até J)
        df = df_raw.iloc[:, :10].copy()
        df.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor_Parc', 'Comissao', 'Status', 'Valor_Total', 'Data_Base']
        
        df['Val_P_N'] = df['Valor_Parc'].apply(limpar_financeiro)
        df['Val_T_N'] = df['Valor_Total'].apply(limpar_financeiro)
        
        # Datas com tratamento de erro para evitar crash
        df['DB_Date'] = pd.to_datetime(df['Data_Base'], dayfirst=True, errors='coerce')
        df['DV_Date'] = pd.to_datetime(df['Vencimento'], dayfirst=True, errors='coerce')
        
        # Remove linhas fantasmas vazias
        df = df.dropna(subset=['DB_Date', 'DV_Date'])
        
        df['Mes_Base'] = df['DB_Date'].dt.to_period('M')
        df['Mes_Venc'] = df['DV_Date'].dt.to_period('M')
    except Exception as e:
        st.error(f"Erro na Planilha: Verifique se as 10 colunas (A até J) estão preenchidas.")
        df = pd.DataFrame()

    # --- 4. DASHBOARD EXECUTIVO ---
    if menu == "📊 Dashboard Executivo" and not df.empty:
        st.title("📊 Painel de Performance Gerencial")
        df_dash = df.copy() if perfil_admin else df[df['Vendedor'] == user['nome']]
        
        with st.expander("🔍 Filtros de Período", expanded=True):
            m_list = sorted(df['Mes_Base'].unique())
            m_sel = st.select_slider("Selecione o Mês da Data Base", options=m_list, value=(m_list[0], m_list[-1]))
            
            # Faturamento: 1 linha por contrato (TS) no período Data Base
            df_faturamento = df_dash[(df_dash['Mes_Base'] >= m_sel[0]) & (df_dash['Mes_Base'] <= m_sel[1])].drop_duplicates('TS')
            # Caixa: Todas as parcelas vencendo no período
            df_caixa = df_dash[(df_dash['Mes_Venc'] >= m_sel[0]) & (df_dash['Mes_Venc'] <= m_sel[1])]

        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 Faturado (Total Contratos)", f"R$ {df_faturamento['Val_T_N'].sum():,.2f}")
        c2.metric("✅ Recebido (Caixa)", f"R$ {df_caixa[df_caixa['Status']=='Pago']['Val_P_N'].sum():,.2f}")
        c3.metric("🤝 Novos Contratos", len(df_faturamento))

        st.subheader("📋 Tabela de Contratos Fechados")
        st.dataframe(df_faturamento[['Data_Base', 'Cliente', 'Vendedor', 'Valor_Total', 'Tipo']], use_container_width=True)

    # --- 5. GESTÃO DE VENDAS ---
    elif menu == "📝 Gestão de Vendas":
        st.title("📝 Registro de Novos Contratos")
        with st.form("form_venda", clear_on_submit=True):
            col1, col2 = st.columns(2)
            f_cli = col1.text_input("Nome do Cliente")
            f_vend = col2.selectbox("Vendedor", st.session_state['lista_vendedores']) if perfil_admin else col2.text_input("Vendedor", user['nome'], disabled=True)
            f_total = col1.number_input("Valor Total do Contrato", min_value=0.0)
            f_parc = col2.number_input("Número de Parcelas", min_value=1, value=1)
            f_data = st.date_input("Data do Fechamento (Data Base)")
            
            if st.form_submit_button("🚀 Finalizar Lançamento"):
                v_parcela = f_total / f_parc
                for i in range(int(f_parc)):
                    venc_dt = (f_data + relativedelta(months=i)).strftime('%d/%m/%Y')
                    payload = {
                        "entry.1532857351": f_cli,
                        "entry.1279554151": f_vend,
                        "entry.1633578859": f"Parc {i+1}/{int(f_parc)}",
                        "entry.366765493": venc_dt,
                        "entry.1610537227": str(round(v_parcela,2)).replace('.',','),
                        "entry.622689505": "Pendente",
                        "entry.1849135056": str(round(f_total,2)).replace('.',','), # VALOR TOTAL
                        "entry.925681697": f_data.strftime('%d/%m/%Y')             # DATA BASE
                    }
                    requests.post(FORM_URL, data=payload)
                st.success("Lançamento concluído!"); time.sleep(1); st.rerun()

    # --- 6. BAIXAS ---
    elif menu == "✅ Baixar Pagamentos":
        st.title("✅ Conciliação e Baixas")
        if not perfil_admin: st.error("Acesso restrito."); st.stop()
        
        if st.session_state['venda_baixada']:
            row_r = st.session_state['venda_baixada']
            st.success(f"Confirmado: {row_r['Cliente']}")
            v_info = st.session_state['df_usuarios'][st.session_state['df_usuarios']['nome'] == row_r['Vendedor']]
            if not v_info.empty:
                tel = str(v_info.iloc[0]['telefone']).replace(".0", "").replace("+", "").strip()
                msg = urllib.parse.quote(f"✅ *PAGAMENTO RECEBIDO!*\n\n*Cliente:* {row_r['Cliente']}\n*Valor:* R$ {row_r['Valor_Parc']}")
                st.markdown(f'<a href="https://api.whatsapp.com/send?phone={tel}&text={msg}" target="_blank" style="text-decoration:none;"><div style="background-color:#25D366;color:white;padding:15px;text-align:center;border-radius:10px;font-weight:bold;">🟢 NOTIFICAR VENDEDOR</div></a>', unsafe_allow_html=True)
            if st.button("Voltar"): st.session_state['venda_baixada'] = None; st.rerun()
            st.stop()

        pendentes = df[df['Status'] == 'Pendente'] if not df.empty else pd.DataFrame()
        for idx, row in pendentes.iterrows():
            with st.expander(f"{row['Cliente']} | R$ {row['Valor_Parc']}"):
                if st.button("Baixar", key=f"b_{idx}"):
                    requests.get(f"{SCRIPT_URL}?row={idx+2}&status=Pago")
                    st.session_state['venda_baixada'] = row.to_dict()
                    st.rerun()