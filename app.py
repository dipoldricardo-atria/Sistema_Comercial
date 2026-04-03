import streamlit as st
import pandas as pd
import requests
import time
import plotly.express as px # Biblioteca para gráficos profissionais
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- 1. CONFIGURAÇÕES ---
st.set_page_config(page_title="Gestão Comercial Tech", layout="wide")

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

# --- 2. LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🚀 Portal Comercial - Login")
    u_in = st.sidebar.text_input("E-mail").lower().strip()
    s_in = st.sidebar.text_input("Senha", type="password")
    if st.sidebar.button("Entrar"):
        df_u = carregar_dados(GID_USUARIOS)
        user = df_u[(df_u['email'].str.lower() == u_in) & (df_u['senha'].astype(str) == s_in)]
        if not user.empty:
            st.session_state['logged_in'] = True
            st.session_state['user_info'] = user.iloc[0].to_dict()
            st.rerun()
        else: st.error("Login inválido.")
else:
    user = st.session_state['user_info']
    st.sidebar.markdown(f"👤 **{user['nome']}**")
    st.sidebar.markdown(f"🏷️ Perfil: `{user['perfil']}`")
    
    if user['perfil'] == "Admin":
        menu = st.sidebar.radio("Navegação", ["📊 Dashboard Estratégico", "📝 Nova Venda", "✅ Baixar Pagamentos"])
    else:
        menu = st.sidebar.radio("Navegação", ["💰 Minhas Comissões", "📝 Nova Venda"])
    
    if st.sidebar.button("Sair"):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- 3. PROCESSAMENTO DE DADOS ---
    try:
        df = carregar_dados(GID_VENDAS)
        df.columns = ['Timestamp', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissao', 'Status']
        df['Val_N'] = df['Valor'].apply(limpar_financeiro)
        df['Com_N'] = df['Comissao'].apply(limpar_financeiro)
        # Converte vencimento para data real para filtros
        df['Data_Venc'] = pd.to_datetime(df['Vencimento'], dayfirst=True)
    except: df = pd.DataFrame()

    # --- 4. TELA: DASHBOARD (ADMIN) ---
    if menu == "📊 Dashboard Estratégico":
        st.title("📊 Inteligência Comercial")
        
        if not df.empty:
            # Filtros Superiores
            with st.container(border=True):
                c1, c2, c3 = st.columns(3)
                vendedores = df['Vendedor'].unique().tolist()
                f_vend = c1.multiselect("Filtrar Vendedor", vendedores)
                
                # Filtro por Mês
                meses = df['Data_Venc'].dt.strftime('%m/%Y').unique().tolist()
                f_mes = c2.selectbox("Mês de Referência", ["Todos"] + meses)
                
                f_status = c3.multiselect("Status", ["Pendente", "Pago"], default=["Pendente", "Pago"])

            # Aplicando Filtros
            df_f = df.copy()
            if f_vend: df_f = df_f[df_f['Vendedor'].isin(f_vend)]
            if f_status: df_f = df_f[df_f['Status'].isin(f_status)]
            if f_mes != "Todos": df_f = df_f[df_f['Data_Venc'].dt.strftime('%m/%Y') == f_mes]

            # Cards de Resumo
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Previsto no Período", f"R$ {df_f['Val_N'].sum():,.2f}")
            m2.metric("Realizado (Pago)", f"R$ {df_f[df_f['Status']=='Pago']['Val_N'].sum():,.2f}")
            m3.metric("A Receber", f"R$ {df_f[df_f['Status']=='Pendente']['Val_N'].sum():,.2f}")
            m4.metric("Comissões", f"R$ {df_f['Com_N'].sum():,.2f}")

            # Gráficos
            st.divider()
            g1, g2 = st.columns([2, 1])
            
            with g1:
                st.subheader("Faturamento por Vendedor")
                fig_vend = px.bar(df_f.groupby('Vendedor')['Val_N'].sum().reset_index(), 
                                 x='Vendedor', y='Val_N', color='Vendedor', text_auto='.2s')
                st.plotly_chart(fig_vend, use_container_width=True)
            
            with g2:
                st.subheader("Saúde do Recebimento")
                fig_pizza = px.pie(df_f, values='Val_N', names='Status', color='Status',
                                  color_discrete_map={'Pago':'#2ecc71', 'Pendente':'#e74c3c'})
                st.plotly_chart(fig_pizza, use_container_width=True)

            st.subheader("Detalhamento dos Lançamentos")
            st.dataframe(df_f.drop(columns=['Val_N', 'Com_N', 'Data_Venc']), use_container_width=True)
        else:
            st.info("Sem dados para análise.")

    # --- 5. TELA: NOVA VENDA (A MESMA LÓGICA VITORIOSA) ---
    elif menu == "📝 Nova Venda":
        st.title("📝 Lançar Novo Contrato")
        # [Mantivemos a lógica de parcelas que já funciona perfeitamente]
        with st.form("venda_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            cli = col1.text_input("Nome do Cliente")
            tot = col1.number_input("Valor Total do Projeto", min_value=0.0)
            ent = col2.number_input("Valor da Entrada", min_value=0.0)
            parc = col1.number_input("Nº de Parcelas (0 = À Vista)", min_value=0, step=1)
            dat = col2.date_input("Data da Venda", format="DD/MM/YYYY")
            
            if st.form_submit_button("🚀 Registrar Contrato"):
                if cli and tot > 0:
                    itens = []
                    if parc == 0:
                        itens.append({"t": "À Vista", "v": tot, "m": 0})
                    else:
                        if ent > 0: itens.append({"t": "Entrada", "v": ent, "m": 0})
                        vp = (tot - ent) / parc
                        for i in range(1, int(parc)+1): itens.append({"t": f"Parcela {i}/{int(parc)}", "v": vp, "m": i})
                    
                    for it in itens:
                        dv = dat + relativedelta(months=it['m'])
                        pld = {"entry.1532857351": cli, "entry.1279554151": user['nome'], "entry.1633578859": it['t'], "entry.366765493": dv.strftime('%d/%m/%Y'), "entry.1610537227": str(round(it['v'], 2)).replace('.', ','), "entry.1726017566": str(round(it['v']*0.05, 2)).replace('.', ','), "entry.622689505": "Pendente"}
                        requests.post(FORM_URL, data=pld)
                    st.success("Contrato e parcelas geradas com sucesso!")
                    time.sleep(1); st.rerun()

    # --- 6. TELA: BAIXAS (O QUE CORRIGIMOS POR ÚLTIMO) ---
    elif menu == "✅ Baixar Pagamentos":
        st.title("✅ Baixa Financeira")
        pendentes = df[df['Status'] == 'Pendente'] if not df.empty else pd.DataFrame()
        
        if not pendentes.empty:
            for idx, row in pendentes.iterrows():
                linha_google = idx + 2
                with st.expander(f"💰 {row['Cliente']} | {row['Tipo']} | R$ {row['Valor']}"):
                    if st.button(f"Confirmar Recebimento", key=f"btn_{idx}"):
                        url_final = f"{SCRIPT_URL}?row={linha_google}&status=Pago"
                        r = requests.get(url_final)
                        if "Sucesso" in r.text:
                            st.success("Pago!")
                            time.sleep(1.5); st.rerun()
        else:
            st.success("Tudo recebido!")

    # --- 7. TELA: VENDEDOR (EXTRATO) ---
    elif menu == "💰 Minhas Comissões":
        st.title(f"💰 Extrato Comercial: {user['nome']}")
        if not df.empty:
            meu_df = df[df['Vendedor'] == user['nome']].copy()
            c1, c2 = st.columns(2)
            c1.metric("Comissões Pagas", f"R$ {meu_df[meu_df['Status'] == 'Pago']['Com_N'].sum():,.2f}")
            c2.metric("Comissões Pendentes", f"R$ {meu_df[meu_df['Status'] == 'Pendente']['Com_N'].sum():,.2f}")
            st.dataframe(meu_df.drop(columns=['Val_N', 'Com_N', 'Vendedor', 'Data_Venc']), use_container_width=True)