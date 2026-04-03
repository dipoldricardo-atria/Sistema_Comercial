import streamlit as st
import pandas as pd
import requests
import time
import urllib.parse
import plotly.express as px
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. CONFIGURAÇÕES DE AMBIENTE ---
st.set_page_config(page_title="ERP Comercial PRO", layout="wide", page_icon="🚀")

# IDs fixos das colunas do Google Forms (conforme passado anteriormente)
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

# --- 2. LOGIN E SESSÃO ---
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
            st.session_state.update({
                'logged_in': True, 
                'user_info': user.iloc[0].to_dict(), 
                'lista_vendedores': df_u['nome'].unique().tolist(),
                'df_usuarios': df_u
            })
            st.rerun()
        else: st.error("Login inválido.")
else:
    user = st.session_state['user_info']
    perfil_admin = user['perfil'] == "Admin"
    st.sidebar.markdown(f"👤 **{user['nome']}**")
    menu = st.sidebar.radio("Navegação", ["📊 Dashboard Executivo", "📝 Gestão de Vendas", "✅ Baixar Pagamentos"])
    if st.sidebar.button("Sair"): st.session_state.clear(); st.rerun()

    # --- 3. PROCESSAMENTO 10 COLUNAS (BLINDADO) ---
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

    # --- 4. DASHBOARD EXECUTIVO (COMPLETO) ---
    if menu == "📊 Dashboard Executivo":
        st.title("📊 Painel de Performance Comercial")
        
        if not df.empty:
            df_dash = df.copy() if perfil_admin else df[df['Vendedor'] == user['nome']]
            
            with st.expander("🔍 Filtros Avançados", expanded=True):
                tipo_f = st.radio("Visão por:", ["Data Base (Fechamento)", "Vencimento (Caixa)"], horizontal=True)
                col_data = 'Mes_Base' if tipo_f == "Data Base (Fechamento)" else 'Mes_Venc'
                
                f1, f2 = st.columns(2)
                v_sel = f1.multiselect("Vendedores", df_dash['Vendedor'].unique())
                if v_sel: df_dash = df_dash[df_dash['Vendedor'].isin(v_sel)]
                
                m_list = sorted(df[col_data].unique())
                m_sel = f2.select_slider("Período", options=m_list, value=(m_list[0], m_list[-1]))
                df_filtrado = df_dash[(df_dash[col_data] >= m_sel[0]) & (df_dash[col_data] <= m_sel[1])]

            # Faturamento: Contratos Únicos no período (Baseado na Data Base)
            df_fat_real = df_filtrado.drop_duplicates('TS')
            
            st.divider()
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("💰 Faturado (Total)", f"R$ {df_fat_real['Val_T_N'].sum():,.2f}")
            m2.metric("✅ Recebido (Caixa)", f"R$ {df_filtrado[df_filtrado['Status']=='Pago']['Val_P_N'].sum():,.2f}")
            m3.metric("⏳ Pendente", f"R$ {df_filtrado[df_filtrado['Status']=='Pendente']['Val_P_N'].sum():,.2f}")
            m4.metric("🤝 Novos Contratos", len(df_fat_real))

            st.divider()
            c1, c2 = st.columns([2, 1])
            with c1:
                st.subheader("📈 Provisão Mensal")
                df_bar = df_filtrado.groupby(['Mes_Venc', 'Status'])['Val_P_N'].sum().reset_index()
                df_bar['Mes_Venc'] = df_bar['Mes_Venc'].astype(str)
                st.plotly_chart(px.bar(df_bar, x='Mes_Venc', y='Val_P_N', color='Status', barmode='group',
                                       color_discrete_map={'Pago':'#2E5A88','Pendente':'#A9A9A9'}), use_container_width=True)
            with c2:
                st.subheader("📉 Saúde das Parcelas")
                st.plotly_chart(px.pie(df_filtrado, values='Val_P_N', names='Status', hole=.5,
                                       color='Status', color_discrete_map={'Pago':'#2E5A88','Pendente':'#E74C3C'}), use_container_width=True)

            st.subheader("📋 Detalhamento dos Lançamentos")
            st.dataframe(df_filtrado.drop(columns=['Val_P_N','Val_T_N','Com_N','DB_Date','DV_Date','Mes_Base','Mes_Venc']), use_container_width=True)

    # --- 5. GESTÃO DE VENDAS (NOVO + RECORRÊNCIA + EDIÇÃO) ---
    elif menu == "📝 Gestão de Vendas":
        st.title("📝 Central de Operações")
        aba = st.tabs(["🚀 Novo Contrato", "✏️ Editar Lançamento"])

        with aba[0]:
            with st.form("form_venda", clear_on_submit=True):
                c1, c2 = st.columns(2)
                f_cli = c1.text_input("Cliente")
                f_vend = c2.selectbox("Vendedor", st.session_state['lista_vendedores']) if perfil_admin else c2.text_input("Vendedor", user['nome'], disabled=True)
                f_total = c1.number_input("Valor Total do Contrato", min_value=0.0)
                f_parc = c2.number_input("Parcelas (0 = Mensalidade/Recorrência)", min_value=0, value=1)
                f_data = st.date_input("Data Base (Fechamento)")
                
                if st.form_submit_button("Lançar"):
                    # LÓGICA DE RECORRÊNCIA (Parcelas = 0)
                    qtd_loops = 1 if f_parc == 0 else int(f_parc)
                    tipo_desc = "Mensalidade (Recorrente)" if f_parc == 0 else f"Parc 1/{int(f_parc)}"
                    v_parc = f_total / qtd_loops
                    
                    for i in range(qtd_loops):
                        venc = (f_data + relativedelta(months=i)).strftime('%d/%m/%Y')
                        desc = f"Parc {i+1}/{int(f_parc)}" if f_parc > 0 else tipo_desc
                        pld = {
                            "entry.1532857351": f_cli, "entry.1279554151": f_vend,
                            "entry.1633578859": desc, "entry.366765493": venc,
                            "entry.1610537227": str(round(v_parc,2)).replace('.',','),
                            "entry.1726017566": str(round(v_parc*0.05,2)).replace('.',','),
                            "entry.622689505": "Pendente",
                            f"entry.{ID_VALOR_TOTAL}": str(round(f_total,2)).replace('.',','),
                            f"entry.{ID_DATA_BASE}": f_data.strftime('%d/%m/%Y')
                        }
                        requests.post(FORM_URL, data=pld)
                    st.success("Contrato processado!"); time.sleep(1); st.rerun()

        with aba[1]:
            busca = st.text_input("🔍 Buscar Cliente para editar")
            df_e = df[df['Cliente'].str.contains(busca, case=False, na=False)] if busca else df
            if not df_e.empty:
                idx = st.selectbox("Selecione a linha:", df_e.index, format_func=lambda x: f"Linha {x+2} | {df_e.loc[x,'Cliente']} | {df_e.loc[x,'Tipo']}")
                item = df_e.loc[idx]
                with st.form("edit_venda"):
                    ec1, ec2 = st.columns(2)
                    e_cli = ec1.text_input("Cliente", item['Cliente'])
                    e_tipo = ec2.text_input("Tipo", item['Tipo'])
                    e_val = ec1.text_input("Valor Parcela", item['Valor_Parc'])
                    e_venc = ec2.text_input("Vencimento", item['Vencimento'])
                    e_stat = st.selectbox("Status", ["Pendente", "Pago"], index=0 if item['Status']=="Pendente" else 1)
                    if st.form_submit_button("Salvar Alterações"):
                        params = {"row": idx+2, "cliente": e_cli, "tipo": e_tipo, "valor": e_val, "vencimento": e_venc, "status": e_stat}
                        requests.get(SCRIPT_URL, params=params)
                        st.success("Alterado!"); time.sleep(1); st.rerun()

    # --- 6. BAIXAS E WHATSAPP ---
    elif menu == "✅ Baixar Pagamentos":
        st.title("✅ Baixas Financeiras")
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
            with st.expander(f"{r['Cliente']} | {r['Vendedor']} | R$ {r['Valor_Parc']}"):
                if st.button("Confirmar", key=f"bx_{i}"):
                    requests.get(f"{SCRIPT_URL}?row={i+2}&status=Pago")
                    st.session_state['venda_baixada'] = r.to_dict()
                    st.rerun()