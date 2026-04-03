import streamlit as st
import pandas as pd
import requests
import time
import urllib.parse
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- 1. CONFIGURAÇÕES ---
st.set_page_config(page_title="Sistema Comercial PRO", layout="wide")

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

    # Carregamento e Tratamento de Dados
    try:
        df = carregar_dados(GID_VENDAS)
        df.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissao', 'Status']
        df['Val_N'] = df['Valor'].apply(limpar_financeiro)
        df['Com_N'] = df['Comissao'].apply(limpar_financeiro)
        df['Data_Venc'] = pd.to_datetime(df['Vencimento'], dayfirst=True)
        df['Mes_Ano'] = df['Data_Venc'].dt.strftime('%m/%Y')
        df['Data_Sort'] = df['Data_Venc'].dt.to_period('M')
    except: df = pd.DataFrame()

    # --- 3. DASHBOARD EXECUTIVO ---
    if menu == "📊 Dashboard Executivo":
        st.title("📊 Indicadores de Performance")
        
        if not df.empty:
            df_dash = df.copy() if perfil_admin else df[df['Vendedor'] == user['nome']]
            
            # FILTROS SUPERIORES
            with st.expander("🔍 Filtros de Relatório", expanded=True):
                f1, f2 = st.columns(2)
                if perfil_admin:
                    v_sel = f1.multiselect("Vendedor", df_dash['Vendedor'].unique())
                    if v_sel: df_dash = df_dash[df_dash['Vendedor'].isin(v_sel)]
                
                m_list = sorted(df['Data_Sort'].unique())
                m_sel = f2.select_slider("Período de Análise", options=m_list, value=(m_list[0], m_list[-1]))
                df_dash = df_dash[(df_dash['Data_Sort'] >= m_sel[0]) & (df_dash['Data_Sort'] <= m_sel[1])]

            # KPIs SÓBRIOS
            st.markdown("### Resumo Financeiro")
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Provisionado Total", f"R$ {df_dash['Val_N'].sum():,.2f}")
            k2.metric("Recebido (Pago)", f"R$ {df_dash[df_dash['Status']=='Pago']['Val_N'].sum():,.2f}", delta_color="normal")
            k3.metric("Futuro (Pendente)", f"R$ {df_dash[df_dash['Status']=='Pendente']['Val_N'].sum():,.2f}")
            k4.metric("Comissões", f"R$ {df_dash['Com_N'].sum():,.2f}")

            st.divider()

            # GRÁFICOS PROFISSIONAIS
            c1, c2 = st.columns([2, 1])
            
            # Gráfico de Provisão Mensal (Provisionado vs Recebido)
            df_mes = df_dash.groupby(['Mes_Ano', 'Status', 'Data_Sort'])['Val_N'].sum().reset_index().sort_values('Data_Sort')
            fig_bar = px.bar(df_mes, x='Mes_Ano', y='Val_N', color='Status', 
                             title="Previsão de Recebimento Mensal",
                             color_discrete_map={'Pago': '#1f77b4', 'Pendente': '#d3d3d3'},
                             barmode='group', text_auto='.2s')
            fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#555")
            c1.plotly_chart(fig_bar, use_container_width=True)

            # Distribuição por Tipo de Contrato
            fig_pie = px.pie(df_dash, values='Val_N', names='Tipo', hole=0.5, 
                             title="Mix de Contratos",
                             color_discrete_sequence=px.colors.qualitative.Prism)
            fig_pie.update_layout(showlegend=False)
            c2.plotly_chart(fig_pie, use_container_width=True)

            st.markdown("### Detalhamento das Transações")
            st.dataframe(df_dash.drop(columns=['Val_N', 'Com_N', 'Data_Venc', 'Data_Sort', 'Mes_Ano']), use_container_width=True)
        else:
            st.info("Nenhum dado encontrado.")

    # --- 4. GESTÃO DE VENDAS ---
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
                dt_v = c2.date_input("Data Base")
                
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
                    st.success("Enviado com sucesso!"); time.sleep(1); st.rerun()
        else:
            busca = st.text_input("🔍 Buscar Cliente para editar...")
            df_edit = df.copy() if perfil_admin else df[df['Vendedor'] == user['nome']]
            if busca: df_edit = df_edit[df_edit['Cliente'].str.contains(busca, case=False, na=False)]
            
            if not df_edit.empty:
                escolha = st.selectbox("Selecione o registro:", df_edit.index, format_func=lambda x: f"L{x+2} | {df_edit.loc[x, 'Cliente']} | {df_edit.loc[x, 'Tipo']}")
                item = df_edit.loc[escolha]
                with st.form("edit_form"):
                    c1, c2 = st.columns(2)
                    e_cli = c1.text_input("Cliente", item['Cliente'])
                    e_vend = c2.selectbox("Vendedor", st.session_state['lista_vendedores'], index=st.session_state['lista_vendedores'].index(item['Vendedor']) if item['Vendedor'] in st.session_state['lista_vendedores'] else 0) if perfil_admin else c2.text_input("Vendedor", item['Vendedor'], disabled=True)
                    e_tipo = c1.text_input("Tipo", item['Tipo'])
                    e_venc = c2.text_input("Vencimento (DD/MM/YYYY)", item['Vencimento'])
                    e_val = c1.text_input("Valor", item['Valor'])
                    e_com = c2.text_input("Comissão", item['Comissao'])
                    e_stat = st.selectbox("Status", ["Pendente", "Pago"], index=0 if item['Status']=="Pendente" else 1)
                    if st.form_submit_button("💾 Salvar Alterações"):
                        params = {"row": escolha+2, "cliente": e_cli, "vendedor": e_vend, "tipo": e_tipo, "vencimento": e_venc, "valor": e_val, "comissao": e_com, "status": e_stat}
                        requests.get(SCRIPT_URL, params=params)
                        st.success("Atualizado!"); time.sleep(1); st.rerun()

    # --- 5. BAIXAS E WHATSAPP ---
    elif menu == "✅ Baixar Pagamentos":
        st.title("✅ Baixas Financeiras")
        if not perfil_admin: st.error("Acesso restrito."); st.stop()

        if st.session_state['venda_baixada']:
            row_r = st.session_state['venda_baixada']
            st.success(f"📌 Pagamento de {row_r['Cliente']} confirmado!")
            v_info = st.session_state['df_usuarios'][st.session_state['df_usuarios']['nome'] == row_r['Vendedor']]
            
            if not v_info.empty:
                tel = str(v_info.iloc[0]['telefone']).replace(".0", "").replace("+", "").strip()
                msg = urllib.parse.quote(f"✅ *PAGAMENTO CONFIRMADO!*\n\n*Cliente:* {row_r['Cliente']}\n*Valor:* R$ {row_r['Valor']}\n*Tipo:* {row_r['Tipo']}\n\nStatus atualizado. 🚀")
                link = f"https://api.whatsapp.com/send?phone={tel}&text={msg}"
                st.markdown(f'<a href="{link}" target="_blank" style="text-decoration:none;"><div style="background-color:#25D366;color:white;padding:18px;text-align:center;border-radius:12px;font-weight:bold;font-size:22px;">🟢 ENVIAR WHATSAPP PARA {row_r["Vendedor"]}</div></a>', unsafe_allow_html=True)
            
            if st.button("🔙 Voltar para Lista"):
                st.session_state['venda_baixada'] = None
                st.rerun()
            st.stop()

        pendentes = df[df['Status'] == 'Pendente'] if not df.empty else pd.DataFrame()
        for idx, row in pendentes.iterrows():
            with st.expander(f"{row['Cliente']} | {row['Tipo']} | R$ {row['Valor']}"):
                if st.button("Confirmar Recebimento", key=f"p_{idx}"):
                    if "Sucesso" in requests.get(f"{SCRIPT_URL}?row={idx+2}&status=Pago").text:
                        st.session_state['venda_baixada'] = row.to_dict()
                        st.rerun()