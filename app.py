import streamlit as st
import pandas as pd
import requests
import time
import plotly.express as px
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
            st.session_state['lista_vendedores'] = df_u['nome'].unique().tolist()
            st.rerun()
        else: st.error("Login inválido.")
else:
    user = st.session_state['user_info']
    perfil_admin = user['perfil'] == "Admin"
    
    st.sidebar.markdown(f"👤 **{user['nome']}**")
    st.sidebar.markdown(f"🏷️ `{user['perfil']}`")
    
    # MENU AGORA É IGUAL PARA TODOS, MAS OS DADOS DENTRO SÃO DIFERENTES
    abas = ["📊 Meu Dashboard", "📝 Lançar Venda"]
    if perfil_admin:
        abas.append("✅ Baixar Pagamentos")
    
    menu = st.sidebar.radio("Navegação", abas)
    
    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()

    # --- 3. PROCESSAMENTO DE DADOS ---
    try:
        df = carregar_dados(GID_VENDAS)
        df.columns = ['Timestamp', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissao', 'Status']
        df['Val_N'] = df['Valor'].apply(limpar_financeiro)
        df['Com_N'] = df['Comissao'].apply(limpar_financeiro)
        df['Data_Venc'] = pd.to_datetime(df['Vencimento'], dayfirst=True)
    except: df = pd.DataFrame()

    # --- 4. TELA: DASHBOARD INTELIGENTE (FILTRADO POR PERFIL) ---
    if menu == "📊 Meu Dashboard":
        titulo = "📊 Dashboard de Performance" if not perfil_admin else "📊 Painel de Controle Estratégico"
        st.title(titulo)
        
        if not df.empty:
            # LÓGICA DE FILTRO DE SEGURANÇA
            if perfil_admin:
                df_base = df.copy() # Admin vê tudo
            else:
                df_base = df[df['Vendedor'] == user['nome']].copy() # Vendedor só vê o dele

            # Filtros de Topo
            with st.container(border=True):
                c1, c2 = st.columns(2)
                if perfil_admin:
                    f_vend = c1.multiselect("Vendedor", df_base['Vendedor'].unique())
                    if f_vend: df_base = df_base[df_base['Vendedor'].isin(f_vend)]
                
                meses = df_base['Data_Venc'].dt.strftime('%m/%Y').unique().tolist()
                f_mes = c2.selectbox("Mês de Referência", ["Todos"] + meses)
                if f_mes != "Todos":
                    df_base = df_base[df_base['Data_Venc'].dt.strftime('%m/%Y') == f_mes]

            # Indicadores Dinâmicos
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Previsto (Total)", f"R$ {df_base['Val_N'].sum():,.2f}")
            m2.metric("Realizado (Pago)", f"R$ {df_base[df_base['Status']=='Pago']['Val_N'].sum():,.2f}")
            m3.metric("Pendente (A Receber)", f"R$ {df_base[df_base['Status']=='Pendente']['Val_N'].sum():,.2f}")
            m4.metric("Minhas Comissões" if not perfil_admin else "Total Comissões", f"R$ {df_base['Com_N'].sum():,.2f}")

            # Gráficos de Visualização
            st.divider()
            g1, g2 = st.columns(2)
            
            with g1:
                # Se for Admin, mostra ranking. Se for Vendedor, mostra faturamento por mês dele.
                if perfil_admin:
                    fig = px.bar(df_base.groupby('Vendedor')['Val_N'].sum().reset_index(), x='Vendedor', y='Val_N', title="Ranking de Vendas")
                else:
                    fig = px.area(df_base.groupby('Data_Venc')['Val_N'].sum().reset_index(), x='Data_Venc', y='Val_N', title="Minha Evolução de Vendas")
                st.plotly_chart(fig, use_container_width=True)
            
            with g2:
                fig_p = px.pie(df_base, values='Val_N', names='Status', title="Status dos Meus Recebimentos", color='Status',
                              color_discrete_map={'Pago':'#2ecc71', 'Pendente':'#e74c3c'})
                st.plotly_chart(fig_p, use_container_width=True)

            st.subheader("Lista Detalhada")
            st.dataframe(df_base.drop(columns=['Val_N', 'Com_N', 'Data_Venc']), use_container_width=True)
        else:
            st.info("Aguardando lançamentos para gerar estatísticas.")

    # --- 5. TELA: LANÇAR VENDA (MANTÉM HIERARQUIA DE ATRIBUIÇÃO) ---
    elif menu == "📝 Lançar Venda":
        st.title("📝 Registro de Novo Contrato")
        with st.form("venda_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            cli = col1.text_input("Cliente")
            
            if perfil_admin:
                lista_v = st.session_state.get('lista_vendedores', [user['nome']])
                vendedor_final = col2.selectbox("Atribuir Vendedor", lista_v)
            else:
                vendedor_final = col2.text_input("Vendedor", value=user['nome'], disabled=True)
            
            tot = col1.number_input("Valor Total", min_value=0.0)
            ent = col2.number_input("Entrada", min_value=0.0)
            parc = col1.number_input("Nº de Parcelas", min_value=0, step=1)
            dat = col2.date_input("Data", format="DD/MM/YYYY")
            
            if st.form_submit_button("🚀 Salvar"):
                # [Lógica das parcelas mantida aqui]
                if cli and tot > 0:
                    itens = []
                    if parc == 0: itens.append({"t": "À Vista", "v": tot, "m": 0})
                    else:
                        if ent > 0: itens.append({"t": "Entrada", "v": ent, "m": 0})
                        vp = (tot - ent) / parc
                        for i in range(1, int(parc)+1): itens.append({"t": f"Parcela {i}/{int(parc)}", "v": vp, "m": i})
                    for it in itens:
                        dv = dat + relativedelta(months=it['m'])
                        pld = {"entry.1532857351": cli, "entry.1279554151": vendedor_final, "entry.1633578859": it['t'], "entry.366765493": dv.strftime('%d/%m/%Y'), "entry.1610537227": str(round(it['v'], 2)).replace('.', ','), "entry.1726017566": str(round(it['v']*0.05, 2)).replace('.', ','), "entry.622689505": "Pendente"}
                        requests.post(FORM_URL, data=pld)
                    st.success(f"Venda registrada!"); time.sleep(1); st.rerun()

    # --- 6. TELA: BAIXAS (RESTRITO A ADMIN) ---
    elif menu == "✅ Baixar Pagamentos":
        st.title("✅ Conciliação Financeira")
        if not df.empty:
            pendentes = df[df['Status'] == 'Pendente']
            for idx, row in pendentes.iterrows():
                linha_google = idx + 2
                with st.expander(f"💰 {row['Cliente']} | {row['Tipo']} | R$ {row['Valor']}"):
                    if st.button(f"Confirmar Recebimento", key=f"btn_{idx}"):
                        r = requests.get(f"{SCRIPT_URL}?row={linha_google}&status=Pago")
                        if "Sucesso" in r.text: st.success("Pago!"); time.sleep(1); st.rerun()