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

# --- 2. LOGIN ---
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
    menu = st.sidebar.radio("Navegação", ["📊 Dashboard", "📝 Gestão de Vendas", "✅ Baixar Pagamentos"])
    if st.sidebar.button("Sair"): st.session_state.clear(); st.rerun()

    # Processamento Global de Dados
    try:
        df = carregar_dados(GID_VENDAS)
        df.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissao', 'Status']
        df['Val_N'] = df['Valor'].apply(limpar_financeiro)
        df['Com_N'] = df['Comissao'].apply(limpar_financeiro)
        df['Data_Venc'] = pd.to_datetime(df['Vencimento'], dayfirst=True)
    except: df = pd.DataFrame()

    # --- 3. TELA: DASHBOARD (RESTAURADO) ---
    if menu == "📊 Dashboard":
        st.title("📊 Painel de Performance")
        if not df.empty:
            df_dash = df.copy() if perfil_admin else df[df['Vendedor'] == user['nome']]
            
            with st.container(border=True):
                c1, c2 = st.columns(2)
                if perfil_admin:
                    sel_v = c1.multiselect("Vendedores", df_dash['Vendedor'].unique())
                    if sel_v: df_dash = df_dash[df_dash['Vendedor'].isin(sel_v)]
                
                meses = ["Todos"] + sorted(df_dash['Data_Venc'].dt.strftime('%m/%Y').unique().tolist())
                sel_m = c2.selectbox("Mês Referência", meses)
                if sel_m != "Todos": df_dash = df_dash[df_dash['Data_Venc'].dt.strftime('%m/%Y') == sel_m]

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Previsto", f"R$ {df_dash['Val_N'].sum():,.2f}")
            m2.metric("Recebido", f"R$ {df_dash[df_dash['Status']=='Pago']['Val_N'].sum():,.2f}")
            m3.metric("Pendente", f"R$ {df_dash[df_dash['Status']=='Pendente']['Val_N'].sum():,.2f}")
            m4.metric("Comissões", f"R$ {df_dash['Com_N'].sum():,.2f}")

            st.divider()
            g1, g2 = st.columns(2)
            if perfil_admin:
                fig_v = px.bar(df_dash.groupby('Vendedor')['Val_N'].sum().reset_index(), x='Vendedor', y='Val_N', title="Faturamento por Vendedor")
                g1.plotly_chart(fig_v, use_container_width=True)
            else:
                fig_e = px.area(df_dash.groupby('Data_Venc')['Val_N'].sum().reset_index(), x='Data_Venc', y='Val_N', title="Minha Evolução")
                g1.plotly_chart(fig_e, use_container_width=True)
            
            fig_p = px.pie(df_dash, values='Val_N', names='Status', title="Saúde dos Recebimentos", color='Status', color_discrete_map={'Pago':'#2ecc71', 'Pendente':'#e74c3c'})
            g2.plotly_chart(fig_p, use_container_width=True)
            
            st.dataframe(df_dash.drop(columns=['Val_N', 'Com_N', 'Data_Venc']), use_container_width=True)

    # --- 4. TELA: GESTÃO DE VENDAS (LANÇAR E EDITAR TUDO) ---
    elif menu == "📝 Gestão de Vendas":
        st.title("📝 Central de Contratos")
        acao = st.radio("O que deseja fazer?", ["Novo Lançamento", "Editar/Corrigir Lançamento"], horizontal=True)

        if acao == "Novo Lançamento":
            with st.form("novo_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                cli = c1.text_input("Cliente")
                vend = c2.selectbox("Vendedor", st.session_state['lista_vendedores']) if perfil_admin else c2.text_input("Vendedor", user['nome'], disabled=True)
                val_t = c1.number_input("Valor Total", min_value=0.0)
                ent = c2.number_input("Entrada", min_value=0.0)
                parc = c1.number_input("Parcelas (0=Vista)", 0, 120)
                dt_v = c2.date_input("Data Base")
                
                if st.form_submit_button("🚀 Gerar Contrato"):
                    itens = [{"t": "À Vista", "v": val_t, "m": 0}] if parc == 0 else []
                    if parc > 0:
                        if ent > 0: itens.append({"t": "Entrada", "v": ent, "m": 0})
                        v_p = (val_t - ent) / parc
                        for i in range(1, int(parc)+1): itens.append({"t": f"Parcela {i}/{int(parc)}", "v": v_p, "m": i})
                    
                    for it in itens:
                        venc = (dt_v + relativedelta(months=it['m'])).strftime('%d/%m/%Y')
                        pld = {"entry.1532857351": cli, "entry.1279554151": vend, "entry.1633578859": it['t'], "entry.366765493": venc, "entry.1610537227": str(round(it['v'],2)).replace('.',','), "entry.1726017566": str(round(it['v']*0.05,2)).replace('.',','), "entry.622689505": "Pendente"}
                        requests.post(FORM_URL, data=pld)
                    st.success("Lançado!"); time.sleep(1); st.rerun()

        else:
            busca = st.text_input("🔍 Buscar Cliente para editar...")
            df_edit = df.copy() if perfil_admin else df[df['Vendedor'] == user['nome']]
            if busca: df_edit = df_edit[df_edit['Cliente'].str.contains(busca, case=False)]
            
            if not df_edit.empty:
                escolha = st.selectbox("Selecione o lançamento:", df_edit.index, format_func=lambda x: f"Linha {x+2}: {df_edit.loc[x, 'Cliente']} - {df_edit.loc[x, 'Tipo']}")
                item = df_edit.loc[escolha]
                
                with st.form("edit_full_form"):
                    st.warning(f"Editando Registro na Linha {escolha + 2}")
                    c1, c2 = st.columns(2)
                    e_cli = c1.text_input("Cliente", item['Cliente'])
                    e_vend = c2.selectbox("Vendedor", st.session_state['lista_vendedores'], index=st.session_state['lista_vendedores'].index(item['Vendedor']) if item['Vendedor'] in st.session_state['lista_vendedores'] else 0) if perfil_admin else c2.text_input("Vendedor", item['Vendedor'], disabled=True)
                    e_tipo = c1.text_input("Tipo", item['Tipo'])
                    e_venc = c2.text_input("Vencimento (DD/MM/YYYY)", item['Vencimento'])
                    e_val = c1.text_input("Valor (Ex: 1000,00)", item['Valor'])
                    e_com = c2.text_input("Comissão", item['Comissao'])
                    e_stat = st.selectbox("Status", ["Pendente", "Pago"], index=0 if item['Status'] == "Pendente" else 1)
                    
                    if st.form_submit_button("💾 Salvar Alterações"):
                        params = {"row": escolha + 2, "cliente": e_cli, "vendedor": e_vend, "tipo": e_tipo, "vencimento": e_venc, "valor": e_val, "comissao": e_com, "status": e_stat}
                        if "Sucesso" in requests.get(SCRIPT_URL, params=params).text:
                            st.success("Alterado!"); time.sleep(1); st.rerun()

    # --- 5. TELA: BAIXAS + WHATSAPP (RESTAURADO) ---
    elif menu == "✅ Baixar Pagamentos":
        st.title("✅ Conciliação Financeira")
        if not perfil_admin: st.error("Acesso restrito."); st.stop()
        
        pendentes = df[df['Status'] == 'Pendente'] if not df.empty else pd.DataFrame()
        if not pendentes.empty:
            for idx, row in pendentes.iterrows():
                with st.expander(f"💰 {row['Cliente']} | {row['Tipo']} | R$ {row['Valor']}"):
                    if st.button(f"Confirmar Recebimento", key=f"pay_{idx}"):
                        if "Sucesso" in requests.get(f"{SCRIPT_URL}?row={idx+2}&status=Pago").text:
                            st.success("Pago na Planilha!")
                            # Busca Telefone do Vendedor
                            v_data = st.session_state['df_usuarios'][st.session_state['df_usuarios']['nome'] == row['Vendedor']]
                            if not v_data.empty and 'telefone' in v_data.columns:
                                tel = str(v_data.iloc[0]['telefone']).replace(".0", "")
                                msg = urllib.parse.quote(f"✅ *PAGAMENTO CONFIRMADO!*\n\nCliente: {row['Cliente']}\nValor: R$ {row['Valor']}\nTipo: {row['Tipo']}\n\nO status já foi atualizado. 🚀")
                                st.link_button(f"📲 Avisar {row['Vendedor']} no WhatsApp", f"https://api.whatsapp.com/send?phone={tel}&text={msg}")
                            time.sleep(2); st.rerun()
        else: st.success("Nenhuma pendência!")