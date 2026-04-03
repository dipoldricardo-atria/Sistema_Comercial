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
    if menu == "📊 Dashboard Executivo":
        st.title("📊 Dashboard de Performance Real")
        
        if not df.empty:
            df_dash = df.copy() if perfil_admin else df[df['Vendedor'] == user['nome']]
            
            with st.expander("🔍 Critérios de Filtragem", expanded=True):
                tipo_filtro = st.radio("Analisar por:", ["Mês de Fechamento (Data Base)", "Mês de Vencimento (Fluxo de Caixa)"], horizontal=True)
                
                f1, f2 = st.columns(2)
                if perfil_admin:
                    v_sel = f1.multiselect("Vendedores", df_dash['Vendedor'].unique())
                    if v_sel: df_dash = df_dash[df_dash['Vendedor'].isin(v_sel)]
                
                col_data = 'Mes_Base' if tipo_filtro == "Mês de Fechamento (Data Base)" else 'Mes_Venc'
                m_list = sorted(df[col_data].unique())
                m_sel = f2.select_slider("Selecione o Período", options=m_list, value=(m_list[0], m_list[-1]))
                
                df_filtrado = df_dash[(df_dash[col_data] >= m_sel[0]) & (df_dash[col_data] <= m_sel[1])]

            # Faturamento Real: 1 linha por contrato (TS) no período da Data Base
            df_faturamento = df_filtrado.drop_duplicates('TS')
            faturamento_bruto = df_faturamento['Val_T_N'].sum()

            st.markdown(f"### 💎 Resultados do Período ({m_sel[0]} a {m_sel[1]})")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Valor Faturado (Contratos)", f"R$ {faturamento_bruto:,.2f}") 
            m2.metric("Recebido (Caixa)", f"R$ {df_filtrado[df_filtrado['Status']=='Pago']['Val_P_N'].sum():,.2f}")
            m3.metric("Pendente (A Receber)", f"R$ {df_filtrado[df_filtrado['Status']=='Pendente']['Val_P_N'].sum():,.2f}")
            m4.metric("Comissões Totais", f"R$ {df_filtrado['Com_N'].sum():,.2f}")

            st.divider()

            c1, c2 = st.columns([2, 1])
            with c1:
                st.markdown("### 📈 Provisão Mensal de Recebimentos")
                df_mes = df_filtrado.groupby(['Mes_Venc', 'Status'])['Val_P_N'].sum().reset_index()
                df_mes['Mes_Venc'] = df_mes['Mes_Venc'].astype(str)
                fig_bar = px.bar(df_mes, x='Mes_Venc', y='Val_P_N', color='Status', 
                                 color_discrete_map={'Pago': '#2E5A88', 'Pendente': '#A9A9A9'},
                                 barmode='group', text_auto='.2s', height=400)
                st.plotly_chart(fig_bar, use_container_width=True)

            with c2:
                st.markdown("### 📉 Saúde Financeira")
                fig_saude = px.pie(df_filtrado, values='Val_P_N', names='Status', hole=0.5,
                                   color='Status', color_discrete_map={'Pago': '#2E5A88', 'Pendente': '#E74C3C'})
                st.plotly_chart(fig_saude, use_container_width=True)

            st.divider()
            st.markdown("### 📋 Composição da Receita (Mix)")
            fig_mix = px.pie(df_filtrado, values='Val_P_N', names='Tipo', hole=0.4)
            st.plotly_chart(fig_mix, use_container_width=True)
            
            st.markdown("### 📋 Tabela Detalhada")
            st.dataframe(df_filtrado.drop(columns=['Val_P_N', 'Val_T_N', 'Com_N', 'DB_Date', 'DV_Date', 'Mes_Base', 'Mes_Venc']), use_container_width=True)

    # --- 5. GESTÃO DE VENDAS ---
    elif menu == "📝 Gestão de Vendas":
        st.title("📝 Central de Contratos")
        acao = st.radio("Operação:", ["Novo Lançamento", "Editar/Corrigir"], horizontal=True)

        if acao == "Novo Lançamento":
            with st.form("novo_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                cli = c1.text_input("Cliente")
                vend = c2.selectbox("Vendedor", st.session_state['lista_vendedores']) if perfil_admin else c2.text_input("Vendedor", user['nome'], disabled=True)
                val_t = c1.number_input("Valor Total do Contrato", min_value=0.0)
                parc = c1.number_input("Parcelas", 1, 120)
                dt_b = c2.date_input("Data do Fechamento (Data Base)")
                
                if st.form_submit_button("🚀 Lançar Contrato"):
                    v_p = val_t / parc
                    for i in range(int(parc)):
                        venc = (dt_b + relativedelta(months=i)).strftime('%d/%m/%Y')
                        pld = {
                            "entry.1532857351": cli, "entry.1279554151": vend, 
                            "entry.1633578859": f"Parc {i+1}/{int(parc)}", "entry.366765493": venc, 
                            "entry.1610537227": str(round(v_p,2)).replace('.',','), "entry.1726017566": str(round(v_p*0.05,2)).replace('.',','), 
                            "entry.622689505": "Pendente",
                            "entry.1849135056": str(round(val_t,2)).replace('.',','), "entry.925681697": dt_b.strftime('%d/%m/%Y')
                        }
                        requests.post(FORM_URL, data=pld)
                    st.success("Lançamento concluído!"); time.sleep(1); st.rerun()
        
        elif acao == "Editar/Corrigir":
            busca = st.text_input("🔍 Buscar Cliente...")
            df_edit = df.copy() if perfil_admin else df[df['Vendedor'] == user['nome']]
            if busca: df_edit = df_edit[df_edit['Cliente'].str.contains(busca, case=False, na=False)]
            
            if not df_edit.empty:
                escolha = st.selectbox("Selecione:", df_edit.index, format_func=lambda x: f"L{x+2} | {df_edit.loc[x, 'Cliente']} | {df_edit.loc[x, 'Tipo']}")
                item = df_edit.loc[escolha]
                with st.form("edit_form"):
                    c1, c2 = st.columns(2)
                    e_cli = c1.text_input("Cliente", item['Cliente'])
                    e_vend = c2.text_input("Vendedor", item['Vendedor'], disabled=not perfil_admin)
                    e_tipo = c1.text_input("Tipo", item['Tipo'])
                    e_venc = c2.text_input("Vencimento (DD/MM/YYYY)", item['Vencimento'])
                    e_val = c1.text_input("Valor Parcela", item['Valor_Parc'])
                    e_stat = st.selectbox("Status", ["Pendente", "Pago"], index=0 if item['Status']=="Pendente" else 1)
                    if st.form_submit_button("💾 Salvar Alterações"):
                        params = {"row": escolha+2, "cliente": e_cli, "vendedor": e_vend, "tipo": e_tipo, "vencimento": e_venc, "valor": e_val, "status": e_stat}
                        requests.get(SCRIPT_URL, params=params)
                        st.success("Atualizado!"); time.sleep(1); st.rerun()

    # --- 6. BAIXAS E WHATSAPP ---
    elif menu == "✅ Baixar Pagamentos":
        st.title("✅ Conciliação Financeira")
        if not perfil_admin: st.error("Acesso restrito."); st.stop()

        if st.session_state['venda_baixada']:
            row_r = st.session_state['venda_baixada']
            st.success(f"📌 Pagamento de {row_r['Cliente']} confirmado!")
            v_info = st.session_state['df_usuarios'][st.session_state['df_usuarios']['nome'] == row_r['Vendedor']]
            if not v_info.empty:
                tel = str(v_info.iloc[0]['telefone']).replace(".0", "").replace("+", "").strip()
                msg = urllib.parse.quote(f"✅ *PAGAMENTO RECEBIDO!*\n\n*Cliente:* {row_r['Cliente']}\n*Valor:* R$ {row_r['Valor_Parc']}")
                link = f"https://api.whatsapp.com/send?phone={tel}&text={msg}"
                st.markdown(f'<a href="{link}" target="_blank" style="text-decoration:none;"><div style="background-color:#25D366;color:white;padding:18px;text-align:center;border-radius:12px;font-weight:bold;">🟢 ENVIAR WHATSAPP PARA {row_r["Vendedor"]}</div></a>', unsafe_allow_html=True)
            if st.button("🔙 Voltar"): st.session_state['venda_baixada'] = None; st.rerun()
            st.stop()

        pendentes = df[df['Status'] == 'Pendente'] if not df.empty else pd.DataFrame()
        for idx, row in pendentes.iterrows():
            with st.expander(f"{row['Cliente']} | {row['Tipo']} | R$ {row['Valor_Parc']}"):
                if st.button("Confirmar Recebimento", key=f"p_{idx}"):
                    requests.get(f"{SCRIPT_URL}?row={idx+2}&status=Pago")
                    st.session_state['venda_baixada'] = row.to_dict()
                    st.rerun()