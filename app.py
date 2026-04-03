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

ID_VALOR_TOTAL = "1849135056"
ID_DATA_BASE = "925681697"

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

# --- 2. CONTROLE DE ACESSO ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'venda_baixada' not in st.session_state: st.session_state['venda_baixada'] = None

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
        else: st.error("Acesso negado.")
else:
    user = st.session_state['user_info']
    perfil_admin = user['perfil'] == "Admin"
    st.sidebar.markdown(f"👤 **{user['nome']}**")
    menu = st.sidebar.radio("Navegação", ["📊 Dashboard Executivo", "📝 Gestão de Vendas", "✅ Baixar Pagamentos"])
    if st.sidebar.button("Sair"): st.session_state.clear(); st.rerun()

    # --- 3. PROCESSAMENTO 10 COLUNAS ---
    try:
        df_raw = carregar_dados(GID_VENDAS)
        df = df_raw.iloc[:, :10].copy()
        df.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor_Parc', 'Comissao', 'Status', 'Valor_Total', 'Data_Base']
        
        df['Val_P_N'] = df['Valor_Parc'].apply(limpar_financeiro)
        df['Val_T_N'] = df['Valor_Total'].apply(limpar_financeiro)
        df['Com_N'] = df['Comissao'].apply(limpar_financeiro)
        
        df['DB_Date'] = pd.to_datetime(df['Data_Base'], dayfirst=True, errors='coerce')
        df['DV_Date'] = pd.to_datetime(df['Vencimento'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['DB_Date', 'DV_Date'])
        
        df['Mes_Base'] = df['DB_Date'].dt.to_period('M')
        df['Mes_Venc'] = df['DV_Date'].dt.to_period('M')
    except: df = pd.DataFrame()

    # --- 4. DASHBOARD EXECUTIVO ---
    if menu == "📊 Dashboard Executivo" and not df.empty:
        st.title("📊 Inteligência Comercial")
        df_dash = df.copy() if perfil_admin else df[df['Vendedor'] == user['nome']]
        
        with st.expander("🔍 Filtros de Análise", expanded=True):
            tipo_v = st.radio("Analisar por:", ["Mês de Fechamento (Data Base)", "Mês de Vencimento (Fluxo de Caixa)"], horizontal=True)
            col_data = 'Mes_Base' if tipo_v == "Mês de Fechamento (Data Base)" else 'Mes_Venc'
            m_list = sorted(df[col_data].unique())
            m_sel = st.select_slider("Selecione o Período", options=m_list, value=(m_list[0], m_list[-1]))
            df_filtrado = df_dash[(df_dash[col_data] >= m_sel[0]) & (df_dash[col_data] <= m_sel[1])]

        # KPIs Inteligentes (Faturamento Bruto Real)
        df_fat_real = df_filtrado.drop_duplicates('TS')
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("💰 Faturado (Total)", f"R$ {df_fat_real['Val_T_N'].sum():,.2f}")
        m2.metric("✅ Recebido (Caixa)", f"R$ {df_filtrado[df_filtrado['Status']=='Pago']['Val_P_N'].sum():,.2f}")
        m3.metric("⏳ A Receber", f"R$ {df_filtrado[df_filtrado['Status']=='Pendente']['Val_P_N'].sum():,.2f}")
        m4.metric("📈 Novos Contratos", len(df_fat_real))

        st.divider()
        c1, c2 = st.columns([2,1])
        with c1:
            df_mes = df_filtrado.groupby(['Mes_Venc', 'Status'])['Val_P_N'].sum().reset_index()
            df_mes['Mes_Venc'] = df_mes['Mes_Venc'].astype(str)
            st.plotly_chart(px.bar(df_mes, x='Mes_Venc', y='Val_P_N', color='Status', barmode='group', title="Fluxo de Caixa Mensal", color_discrete_map={'Pago':'#2E5A88','Pendente':'#A9A9A9'}), use_container_width=True)
        with c2:
            st.plotly_chart(px.pie(df_filtrado, values='Val_P_N', names='Status', hole=.5, title="Saúde Financeira", color='Status', color_discrete_map={'Pago':'#2E5A88','Pendente':'#E74C3C'}), use_container_width=True)

    # --- 5. GESTÃO DE VENDAS (AQUI ESTÁ A ENTRADA E RECORRÊNCIA!) ---
    elif menu == "📝 Gestão de Vendas":
        st.title("📝 Central de Lançamentos")
        aba = st.tabs(["🚀 Novo Contrato", "✏️ Editar/Corrigir"])

        with aba[0]:
            with st.form("venda_form", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                f_cli = c1.text_input("Nome do Cliente")
                f_vend = c2.selectbox("Vendedor", st.session_state['lista_vendedores']) if perfil_admin else c2.text_input("Vendedor", user['nome'], disabled=True)
                f_data = c3.date_input("Data do Fechamento (Data Base)")
                
                f_total = c1.number_input("Valor TOTAL do Contrato", min_value=0.0)
                f_entrada = c2.number_input("Valor da ENTRADA (0 se não houver)", min_value=0.0)
                f_parc = c3.number_input("Parcelas RESTANTES (0 = Recorrência)", min_value=0, value=1)
                
                if st.form_submit_button("🚀 Registrar Contrato"):
                    # 1. Lanço a Entrada (se houver)
                    if f_entrada > 0:
                        requests.post(FORM_URL, data={
                            "entry.1532857351": f_cli, "entry.1279554151": f_vend, "entry.1633578859": "Entrada",
                            "entry.366765493": f_data.strftime('%d/%m/%Y'), "entry.1610537227": str(round(f_entrada,2)).replace('.',','),
                            "entry.622689505": "Pendente", f"entry.{ID_VALOR_TOTAL}": str(round(f_total,2)).replace('.',','),
                            f"entry.{ID_DATA_BASE}": f_data.strftime('%d/%m/%Y')
                        })
                    
                    # 2. Lanço as Parcelas ou Recorrência
                    saldo = f_total - f_entrada
                    loops = 1 if f_parc == 0 else int(f_parc)
                    v_p = saldo / loops if f_parc > 0 else f_total # Se recorrente, v_p = total
                    
                    for i in range(loops):
                        venc = (f_data + relativedelta(months=i+1 if f_entrada > 0 else i)).strftime('%d/%m/%Y')
                        tipo_p = f"Parc {i+1}/{int(f_parc)}" if f_parc > 0 else "Mensalidade (Recorrente)"
                        requests.post(FORM_URL, data={
                            "entry.1532857351": f_cli, "entry.1279554151": f_vend, "entry.1633578859": tipo_p,
                            "entry.366765493": venc, "entry.1610537227": str(round(v_p,2)).replace('.',','),
                            "entry.622689505": "Pendente", f"entry.{ID_VALOR_TOTAL}": str(round(f_total,2)).replace('.',','),
                            f"entry.{ID_DATA_BASE}": f_data.strftime('%d/%m/%Y')
                        })
                    st.success("Venda registrada com sucesso!"); time.sleep(1); st.rerun()

        with aba[1]:
            busca = st.text_input("🔍 Buscar Cliente para editar")
            df_e = df[df['Cliente'].str.contains(busca, case=False, na=False)] if busca else df
            if not df_e.empty:
                idx = st.selectbox("Selecione a linha:", df_e.index, format_func=lambda x: f"L{x+2} | {df_e.loc[x,'Cliente']} | {df_e.loc[x,'Tipo']}")
                item = df_e.loc[idx]
                with st.form("edit_venda"):
                    ec1, ec2 = st.columns(2)
                    e_cli = ec1.text_input("Cliente", item['Cliente'])
                    e_tipo = ec2.text_input("Tipo", item['Tipo'])
                    e_val = ec1.text_input("Valor Parcela", item['Valor_Parc'])
                    e_venc = ec2.text_input("Vencimento", item['Vencimento'])
                    e_stat = st.selectbox("Status", ["Pendente", "Pago"], index=0 if item['Status']=="Pendente" else 1)
                    if st.form_submit_button("💾 Salvar Alterações"):
                        params = {"row": idx+2, "cliente": e_cli, "tipo": e_tipo, "valor": e_val, "vencimento": e_venc, "status": e_stat}
                        requests.get(SCRIPT_URL, params=params)
                        st.success("Alterado!"); time.sleep(1); st.rerun()

    # --- 6. BAIXAS ---
    elif menu == "✅ Baixar Pagamentos":
        st.title("✅ Conciliação Financeira")
        if not perfil_admin: st.error("Acesso restrito."); st.stop()

        if st.session_state['venda_baixada']:
            rb = st.session_state['venda_baixada']
            st.success(f"Confirmado: {rb['Cliente']} - {rb['Valor_Parc']}")
            v_info = st.session_state['df_usuarios'][st.session_state['df_usuarios']['nome'] == rb['Vendedor']]
            if not v_info.empty:
                tel = str(v_info.iloc[0]['telefone']).replace(".0","").replace("+","").strip()
                msg = urllib.parse.quote(f"✅ *PAGAMENTO CONFIRMADO!*\n*Cliente:* {rb['Cliente']}\n*Valor:* R$ {rb['Valor_Parc']}")
                st.markdown(f'<a href="https://api.whatsapp.com/send?phone={tel}&text={msg}" target="_blank" style="text-decoration:none;"><div style="background-color:#25D366;color:white;padding:15px;text-align:center;border-radius:10px;font-weight:bold;">🟢 NOTIFICAR VENDEDOR</div></a>', unsafe_allow_html=True)
            if st.button("Voltar"): st.session_state['venda_baixada'] = None; st.rerun()
            st.stop()

        pendentes = df[df['Status'] == 'Pendente']
        for i, r in pendentes.iterrows():
            with st.expander(f"{r['Cliente']} | {r['Tipo']} | R$ {r['Valor_Parc']}"):
                if st.button("Baixar Pagamento", key=f"bx_{i}"):
                    requests.get(f"{SCRIPT_URL}?row={i+2}&status=Pago")
                    st.session_state['venda_baixada'] = r.to_dict()
                    st.rerun()