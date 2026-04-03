import streamlit as st
import pandas as pd
import requests
import time
import urllib.parse
import plotly.express as px
from datetime import datetime, date
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

if not st.session_state['logged_in']:
    st.title("🚀 Portal Comercial - Login")
    u_in = st.sidebar.text_input("E-mail").lower().strip()
    s_in = st.sidebar.text_input("Senha", type="password")
    if st.sidebar.button("Entrar"):
        df_u = carregar_dados(GID_USUARIOS)
        user = df_u[(df_u['email'].str.lower() == u_in) & (df_u['senha'].astype(str) == s_in)]
        if not user.empty:
            st.session_state.update({'logged_in': True, 'user_info': user.iloc[0].to_dict(), 
                                    'lista_vendedores': df_u['nome'].unique().tolist()})
            st.rerun()
        else: st.error("Login inválido.")
else:
    user = st.session_state['user_info']
    perfil_admin = user['perfil'] == "Admin"
    st.sidebar.markdown(f"👤 **{user['nome']}**")
    menu = st.sidebar.radio("Navegação", ["📊 Dashboard Executivo", "📝 Gestão de Vendas", "✅ Baixar Pagamentos"])

    # --- 3. PROCESSAMENTO DE DADOS (CÉREBRO DO SISTEMA) ---
    try:
        df_raw = carregar_dados(GID_VENDAS)
        df_raw.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissao', 'Status']
        df_raw['Val_N'] = df_raw['Valor'].apply(limpar_financeiro)
        df_raw['Com_N'] = df_raw['Comissao'].apply(limpar_financeiro)
        df_raw['Data_Venc'] = pd.to_datetime(df_raw['Vencimento'], dayfirst=True)
        
        # DEFINIÇÃO DA DATA DO CONTRATO (Mínima data de vencimento por ID de venda/TS)
        df_raw['Data_Contrato'] = df_raw.groupby('TS')['Data_Venc'].transform('min')
        df_raw['Mes_Contrato'] = df_raw['Data_Contrato'].dt.to_period('M')
        df_raw['Mes_Vencimento'] = df_raw['Data_Venc'].dt.to_period('M')

        # CRIAÇÃO DA TABELA DE CONTRATOS ÚNICOS (Para o KPI não errar nunca)
        # Aqui somamos todas as parcelas de um mesmo TS para ter o valor total do contrato fechado naquela data
        df_contratos_raiz = df_raw.groupby(['TS', 'Mes_Contrato', 'Vendedor', 'Cliente']).agg({'Val_N': 'sum'}).reset_index()
    except: 
        df_raw = pd.DataFrame()
        df_contratos_raiz = pd.DataFrame()

    if menu == "📊 Dashboard Executivo":
        st.title("📊 Painel de Controle Gerencial")
        
        if not df_raw.empty:
            # Filtro de Vendedor (Admin vê tudo, Vendedor vê o dele)
            df_view_raw = df_raw.copy() if perfil_admin else df_raw[df_raw['Vendedor'] == user['nome']]
            df_view_raiz = df_contratos_raiz.copy() if perfil_admin else df_contratos_raiz[df_contratos_raiz['Vendedor'] == user['nome']]
            
            with st.expander("🔍 Filtros de Data e Vendedor", expanded=True):
                # O filtro agora rege as duas métricas simultaneamente de forma correta
                m_list = sorted(df_raw['Mes_Contrato'].unique())
                m_sel = st.select_slider("Selecione o Mês de Referência", options=m_list, value=(m_list[0], m_list[-1]))
                
                if perfil_admin:
                    v_sel = st.multiselect("Filtrar Vendedores", df_view_raiz['Vendedor'].unique())
                    if v_sel:
                        df_view_raw = df_view_raw[df_view_raw['Vendedor'].isin(v_sel)]
                        df_view_raiz = df_view_raiz[df_view_raiz['Vendedor'].isin(v_sel)]

            # --- CÁLCULO DOS KPIs ---
            # 1. Faturamento Total: Soma o valor INTEGRAL dos contratos fechados no período selecionado
            faturamento_bruto = df_view_raiz[(df_view_raiz['Mes_Contrato'] >= m_sel[0]) & (df_view_raiz['Mes_Contrato'] <= m_sel[1])]['Val_N'].sum()
            
            # 2. Caixa e Parcelas: Filtra as parcelas que vencem ou foram pagas no período
            df_parcelas_periodo = df_view_raw[(df_view_raw['Mes_Vencimento'] >= m_sel[0]) & (df_view_raw['Mes_Vencimento'] <= m_sel[1])]
            total_pago = df_parcelas_periodo[df_parcelas_periodo['Status'] == 'Pago']['Val_N'].sum()
            total_pendente = df_parcelas_periodo[df_parcelas_periodo['Status'] == 'Pendente']['Val_N'].sum()

            st.divider()
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("💰 Faturamento Total (Contratos)", f"R$ {faturamento_bruto:,.2f}", help="Soma total dos contratos assinados com Data Base no período.")
            k2.metric("✅ Recebido (Caixa)", f"R$ {total_pago:,.2f}", help="O que efetivamente entrou no mês.")
            k3.metric("⏳ Pendente (A Receber)", f"R$ {total_pendente:,.2f}", help="Parcelas vencendo no período que ainda não foram baixadas.")
            k4.metric("📈 Volume de Vendas", len(df_view_raiz[(df_view_raiz['Mes_Contrato'] >= m_sel[0]) & (df_view_raiz['Mes_Contrato'] <= m_sel[1])]))

            # GRÁFICOS
            st.divider()
            c1, c2 = st.columns([2, 1])
            with c1:
                st.markdown("### 📈 Fluxo de Caixa (Vencimentos no Período)")
                df_bar = df_parcelas_periodo.groupby([df_parcelas_periodo['Data_Venc'].dt.strftime('%m/%Y'), 'Status', 'Mes_Vencimento'])['Val_N'].sum().reset_index().sort_values('Mes_Vencimento')
                fig_bar = px.bar(df_bar, x='Data_Venc', y='Val_N', color='Status', barmode='group',
                                 color_discrete_map={'Pago': '#2E5A88', 'Pendente': '#A9A9A9'}, text_auto='.2s')
                st.plotly_chart(fig_bar, use_container_width=True)
            
            with c2:
                st.markdown("### 🍕 Mix de Contratos (Faturamento)")
                # Mix baseado no faturamento bruto filtrado
                df_mix = df_view_raw[(df_view_raw['Mes_Contrato'] >= m_sel[0]) & (df_view_raw['Mes_Contrato'] <= m_sel[1])]
                fig_mix = px.pie(df_mix, values='Val_N', names='Tipo', hole=0.4)
                st.plotly_chart(fig_mix, use_container_width=True)

            st.markdown("### 📋 Tabela de Parcelas do Período")
            st.dataframe(df_parcelas_periodo.drop(columns=['Val_N', 'Com_N', 'Data_Venc', 'Mes_Contrato', 'Mes_Vencimento', 'Data_Contrato']), use_container_width=True)

    # --- ABA DE GESTÃO DE VENDAS ---
    elif menu == "📝 Gestão de Vendas":
        st.title("📝 Lançamento de Contratos")
        with st.form("novo_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            cli = c1.text_input("Nome do Cliente")
            vend = c2.selectbox("Vendedor", st.session_state['lista_vendedores']) if perfil_admin else c2.text_input("Vendedor", user['nome'], disabled=True)
            val_t = c1.number_input("Valor Total do Contrato", min_value=0.0)
            ent = c2.number_input("Valor da Entrada", min_value=0.0)
            parc = c1.number_input("Número de Parcelas (após entrada)", 0, 120)
            dt_v = c2.date_input("Data Base (Data do Fechamento)") 
            
            if st.form_submit_button("🚀 Registrar Venda"):
                # Geração de parcelas conforme o que o senhor pediu
                itens = []
                if parc == 0:
                    itens.append({"t": "À Vista", "v": val_t, "m": 0})
                else:
                    if ent > 0: itens.append({"t": "Entrada", "v": ent, "m": 0})
                    v_p = (val_t - ent) / parc
                    for i in range(1, int(parc)+1): itens.append({"t": f"Parcela {i}/{int(parc)}", "v": v_p, "m": i})
                
                # Envio para o Google Sheets
                for it in itens:
                    venc = (dt_v + relativedelta(months=it['m'])).strftime('%d/%m/%Y')
                    pld = {"entry.1532857351": cli, "entry.1279554151": vend, "entry.1633578859": it['t'], "entry.366765493": venc, "entry.1610537227": str(round(it['v'],2)).replace('.',','), "entry.1726017566": str(round(it['v']*0.05,2)).replace('.',','), "entry.622689505": "Pendente"}
                    requests.post(FORM_URL, data=pld)
                st.success("Venda registrada com sucesso!"); time.sleep(1); st.rerun()

    elif menu == "✅ Baixar Pagamentos":
        st.title("✅ Baixa Financeira")
        if not perfil_admin: st.error("Acesso apenas para Administradores."); st.stop()
        pendentes = df_raw[df_raw['Status'] == 'Pendente']
        for idx, row in pendentes.iterrows():
            with st.expander(f"🔹 {row['Cliente']} - {row['Tipo']} (R$ {row['Valor']})"):
                if st.button("Confirmar Pagamento", key=f"btn_{idx}"):
                    requests.get(f"{SCRIPT_URL}?row={idx+2}&status=Pago")
                    st.success("Status atualizado!"); time.sleep(0.5); st.rerun()