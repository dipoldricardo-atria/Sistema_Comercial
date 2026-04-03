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
        else: st.error("Login inválido.")
else:
    user = st.session_state['user_info']
    perfil_admin = user['perfil'] == "Admin"
    st.sidebar.markdown(f"👤 **{user['nome']}**")
    menu = st.sidebar.radio("Navegação", ["📊 Dashboard Executivo", "📝 Gestão de Vendas", "✅ Baixar Pagamentos"])
    if st.sidebar.button("Sair"): st.session_state.clear(); st.rerun()

    # --- 3. PROCESSAMENTO DE DADOS ---
    try:
        df_raw = carregar_dados(GID_VENDAS)
        df_raw.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissao', 'Status']
        df_raw['Val_N'] = df_raw['Valor'].apply(limpar_financeiro)
        df_raw['Com_N'] = df_raw['Comissao'].apply(limpar_financeiro)
        df_raw['Data_Venc'] = pd.to_datetime(df_raw['Vencimento'], dayfirst=True)
        
        # Lógica de Data Base (O contrato pertence ao mês da sua primeira parcela/entrada)
        df_raw['Data_Contrato'] = df_raw.groupby('TS')['Data_Venc'].transform('min')
        df_raw['Mes_Contrato'] = df_raw['Data_Contrato'].dt.to_period('M')
        df_raw['Mes_Vencimento'] = df_raw['Data_Venc'].dt.to_period('M')
    except: df_raw = pd.DataFrame()

    if menu == "📊 Dashboard Executivo":
        st.title("📊 Dashboard de Performance")
        
        if not df_raw.empty:
            df_view = df_raw.copy() if perfil_admin else df_raw[df_raw['Vendedor'] == user['nome']]
            
            with st.expander("🔍 Filtros de Análise", expanded=True):
                tipo_f = st.radio("Base de Cálculo:", ["Faturamento (Mês do Fechamento)", "Caixa (Mês do Recebimento)"], horizontal=True)
                col_ref = 'Mes_Contrato' if "Faturamento" in tipo_f else 'Mes_Vencimento'
                
                m_list = sorted(df_view[col_ref].unique())
                m_sel = st.select_slider("Período", options=m_list, value=(m_list[0], m_list[-1]))
                
                # Filtragem Principal
                df_filtrado = df_view[(df_view[col_ref] >= m_sel[0]) & (df_view[col_ref] <= m_sel[1])]

            # --- CÁLCULO DE FATURAMENTO (AQUI ESTAVA O ERRO) ---
            # Precisamos somar o valor total de todos os contratos (TS) que iniciaram no período, 
            # independente se as parcelas vencem depois.
            contratos_no_periodo = df_view[(df_view['Mes_Contrato'] >= m_sel[0]) & (df_view['Mes_Contrato'] <= m_sel[1])]
            faturamento_total = contratos_no_periodo['Val_N'].sum()

            # KPIs
            st.divider()
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Faturamento Bruto", f"R$ {faturamento_total:,.2f}", help="Total assinado em contratos no período.")
            k2.metric("Total Pago", f"R$ {df_filtrado[df_filtrado['Status']=='Pago']['Val_N'].sum():,.2f}")
            k3.metric("Total Pendente", f"R$ {df_filtrado[df_filtrado['Status']=='Pendente']['Val_N'].sum():,.2f}")
            k4.metric("Comissões", f"R$ {df_filtrado['Com_N'].sum():,.2f}")

            # GRÁFICOS
            st.divider()
            c1, c2 = st.columns([2, 1])
            
            with c1:
                st.markdown("### 📈 Evolução de Recebimentos")
                df_bar = df_filtrado.groupby([df_filtrado['Data_Venc'].dt.strftime('%m/%Y'), 'Status', 'Mes_Vencimento'])['Val_N'].sum().reset_index().sort_values('Mes_Vencimento')
                fig_bar = px.bar(df_bar, x='Data_Venc', y='Val_N', color='Status', barmode='group',
                                 color_discrete_map={'Pago': '#2E5A88', 'Pendente': '#A9A9A9'}, text_auto='.2s')
                st.plotly_chart(fig_bar, use_container_width=True)

            with c2:
                st.markdown("### 🍕 Saúde da Carteira")
                # Mostra o quanto do que foi filtrado já foi pago
                fig_pizza = px.pie(df_filtrado, values='Val_N', names='Status', hole=0.5,
                                   color='Status', color_discrete_map={'Pago': '#2E5A88', 'Pendente': '#E74C3C'})
                st.plotly_chart(fig_pizza, use_container_width=True)

            st.divider()
            st.markdown("### 🎯 Mix de Contratos")
            fig_mix = px.pie(df_filtrado, values='Val_N', names='Tipo', hole=0.4)
            st.plotly_chart(fig_mix, use_container_width=True)

            st.markdown("### 📋 Detalhes das Parcelas")
            st.dataframe(df_filtrado.drop(columns=['Val_N', 'Com_N', 'Data_Venc', 'Mes_Contrato', 'Mes_Vencimento', 'Data_Contrato']), use_container_width=True)

    # --- RESTANTE DO CÓDIGO (GESTÃO E BAIXAS) MANTIDO ---
    elif menu == "📝 Gestão de Vendas":
        st.title("📝 Central de Contratos")
        acao = st.radio("Operação:", ["Novo Lançamento", "Editar/Corrigir"], horizontal=True)

        if acao == "Novo Lançamento":
            with st.form("novo_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                cli = c1.text_input("Cliente")
                vend = c2.selectbox("Vendedor", st.session_state['lista_vendedores']) if perfil_admin else c2.text_input("Vendedor", user['nome'], disabled=True)
                val_t = c1.number_input("Valor Total", min_value=0.0)
                ent = c2.number_input("Entrada", min_value=0.0)
                parc = c1.number_input("Parcelas (0=Vista)", 0, 120)
                dt_v = c2.date_input("Data Base (Competência)") 
                
                if st.form_submit_button("🚀 Lançar Contrato"):
                    itens = [{"t": "À Vista", "v": val_t, "m": 0}] if parc == 0 else []
                    if parc > 0:
                        if ent > 0: itens.append({"t": "Entrada", "v": ent, "m": 0})
                        v_p = (val_t - ent) / parc
                        for i in range(1, int(parc)+1): itens.append({"t": f"Parcela {i}/{int(parc)}", "v": v_p, "m": i})
                    
                    for it in itens:
                        venc = (dt_v + relativedelta(months=it['m'])).strftime('%d/%m/%Y')
                        pld = {"entry.1532857351": cli, "entry.1279554151": vend, "entry.1633578859": it['t'], "entry.366765493": venc, "entry.1610537227": str(round(it['v'],2)).replace('.',','), "entry.1726017566": str(round(it['v']*0.05,2)).replace('.',','), "entry.622689505": "Pendente"}
                        requests.post(FORM_URL, data=pld)
                    st.success("Sucesso!"); time.sleep(1); st.rerun()

        elif acao == "Editar/Corrigir":
            busca = st.text_input("🔍 Buscar Cliente...")
            df_edit = df_raw.copy() if perfil_admin else df_raw[df_raw['Vendedor'] == user['nome']]
            if busca: df_edit = df_edit[df_edit['Cliente'].str.contains(busca, case=False, na=False)]
            if not df_edit.empty:
                escolha = st.selectbox("Selecione:", df_edit.index, format_func=lambda x: f"L{x+2} | {df_edit.loc[x, 'Cliente']} | {df_edit.loc[x, 'Tipo']}")
                item = df_edit.loc[escolha]
                with st.form("edit_form"):
                    c1, c2 = st.columns(2)
                    e_cli = c1.text_input("Cliente", item['Cliente'])
                    e_vend = c2.text_input("Vendedor", item['Vendedor'], disabled=True)
                    e_tipo = c1.text_input("Tipo", item['Tipo'])
                    e_venc = c2.text_input("Vencimento", item['Vencimento'])
                    e_val = c1.text_input("Valor", item['Valor'])
                    e_com = c2.text_input("Comissão", item['Comissao'])
                    e_stat = st.selectbox("Status", ["Pendente", "Pago"], index=0 if item['Status']=="Pendente" else 1)
                    if st.form_submit_button("💾 Salvar"):
                        params = {"row": escolha+2, "cliente": e_cli, "vendedor": e_vend, "tipo": e_tipo, "vencimento": e_venc, "valor": e_val, "comissao": e_com, "status": e_stat}
                        requests.get(SCRIPT_URL, params=params)
                        st.success("Atualizado!"); time.sleep(1); st.rerun()

    elif menu == "✅ Baixar Pagamentos":
        st.title("✅ Conciliação Financeira")
        if not perfil_admin: st.error("Acesso restrito."); st.stop()
        pendentes = df_raw[df_raw['Status'] == 'Pendente']
        for idx, row in pendentes.iterrows():
            with st.expander(f"{row['Cliente']} | {row['Tipo']} | R$ {row['Valor']}"):
                if st.button("Confirmar", key=f"p_{idx}"):
                    requests.get(f"{SCRIPT_URL}?row={idx+2}&status=Pago")
                    st.success("Baixado!"); time.sleep(1); st.rerun()