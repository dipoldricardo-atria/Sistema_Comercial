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

# Links de Integração (Mantenha seus GIDs e URLs)
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

# --- 2. CONTROLE DE LOGIN E SESSÃO ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'venda_baixada' not in st.session_state:
    st.session_state['venda_baixada'] = None

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
    st.sidebar.markdown(f"🏷️ `{user['perfil']}`")
    
    menu = st.sidebar.radio("Navegação", ["📊 Dashboard", "📝 Gestão de Vendas", "✅ Baixar Pagamentos"])
    
    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()

    # Processamento Global de Dados das Vendas
    try:
        df = carregar_dados(GID_VENDAS)
        df.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissao', 'Status']
        df['Val_N'] = df['Valor'].apply(limpar_financeiro)
        df['Com_N'] = df['Comissao'].apply(limpar_financeiro)
        df['Data_Venc'] = pd.to_datetime(df['Vencimento'], dayfirst=True)
    except:
        df = pd.DataFrame()

    # --- 3. TELA: DASHBOARD (VISÃO POR PERFIL) ---
    if menu == "📊 Dashboard":
        st.title("📊 Painel de Performance Comercial")
        if not df.empty:
            df_dash = df.copy() if perfil_admin else df[df['Vendedor'] == user['nome']]
            
            with st.container(border=True):
                c1, c2 = st.columns(2)
                if perfil_admin:
                    sel_v = c1.multiselect("Vendedores", df_dash['Vendedor'].unique())
                    if sel_v: df_dash = df_dash[df_dash['Vendedor'].isin(sel_v)]
                
                meses = ["Todos"] + sorted(df_dash['Data_Venc'].dt.strftime('%m/%Y').unique().tolist())
                sel_m = c2.selectbox("Mês de Referência", meses)
                if sel_m != "Todos":
                    df_dash = df_dash[df_dash['Data_Venc'].dt.strftime('%m/%Y') == sel_m]

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Faturamento Total", f"R$ {df_dash['Val_N'].sum():,.2f}")
            m2.metric("Total Recebido", f"R$ {df_dash[df_dash['Status']=='Pago']['Val_N'].sum():,.2f}")
            m3.metric("A Receber (Pendente)", f"R$ {df_dash[df_dash['Status']=='Pendente']['Val_N'].sum():,.2f}")
            m4.metric("Comissões Brutas", f"R$ {df_dash['Com_N'].sum():,.2f}")

            st.divider()
            g1, g2 = st.columns(2)
            if perfil_admin:
                fig_v = px.bar(df_dash.groupby('Vendedor')['Val_N'].sum().reset_index(), x='Vendedor', y='Val_N', title="Vendas por Vendedor", color='Vendedor')
                g1.plotly_chart(fig_v, use_container_width=True)
            else:
                fig_e = px.line(df_dash.groupby('Data_Venc')['Val_N'].sum().reset_index(), x='Data_Venc', y='Val_N', title="Minha Evolução Temporal")
                g1.plotly_chart(fig_e, use_container_width=True)
            
            fig_p = px.pie(df_dash, values='Val_N', names='Status', title="Saúde dos Recebimentos", color='Status', color_discrete_map={'Pago':'#2ecc71', 'Pendente':'#e74c3c'})
            g2.plotly_chart(fig_p, use_container_width=True)
            
            st.dataframe(df_dash.drop(columns=['Val_N', 'Com_N', 'Data_Venc']), use_container_width=True)
        else:
            st.warning("Nenhum dado de venda encontrado na planilha.")

    # --- 4. TELA: GESTÃO DE VENDAS (NOVO E EDIÇÃO TOTAL) ---
    elif menu == "📝 Gestão de Vendas":
        st.title("📝 Central de Contratos")
        acao = st.radio("Selecione a operação:", ["Novo Lançamento", "Editar/Corrigir Lançamento"], horizontal=True)

        if acao == "Novo Lançamento":
            with st.form("novo_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                cli = c1.text_input("Nome do Cliente")
                vend = c2.selectbox("Vendedor Responsável", st.session_state['lista_vendedores']) if perfil_admin else c2.text_input("Vendedor", user['nome'], disabled=True)
                val_t = c1.number_input("Valor Total do Contrato", min_value=0.0)
                ent = c2.number_input("Valor de Entrada", min_value=0.0)
                parc = c1.number_input("Nº de Parcelas (0 = À Vista)", 0, 120)
                dt_v = c2.date_input("Data do Primeiro Pagamento/Base")
                
                if st.form_submit_button("🚀 Gerar e Enviar para Planilha"):
                    itens = [{"t": "À Vista", "v": val_t, "m": 0}] if parc == 0 else []
                    if parc > 0:
                        if ent > 0: itens.append({"t": "Entrada", "v": ent, "m": 0})
                        v_p = (val_t - ent) / parc
                        for i in range(1, int(parc)+1): itens.append({"t": f"Parcela {i}/{int(parc)}", "v": v_p, "m": i})
                    
                    for it in itens:
                        venc = (dt_v + relativedelta(months=it['m'])).strftime('%d/%m/%Y')
                        pld = {"entry.1532857351": cli, "entry.1279554151": vend, "entry.1633578859": it['t'], "entry.366765493": venc, "entry.1610537227": str(round(it['v'],2)).replace('.',','), "entry.1726017566": str(round(it['v']*0.05,2)).replace('.',','), "entry.622689505": "Pendente"}
                        requests.post(FORM_URL, data=pld)
                    st.success("Contrato processado com sucesso!"); time.sleep(1); st.rerun()

        else:
            st.subheader("🔍 Localizar e Editar")
            busca = st.text_input("Digite o nome do cliente...")
            df_edit = df.copy() if perfil_admin else df[df['Vendedor'] == user['nome']]
            if busca: 
                df_edit = df_edit[df_edit['Cliente'].str.contains(busca, case=False, na=False)]
            
            if not df_edit.empty:
                escolha = st.selectbox("Selecione o registro específico:", df_edit.index, format_func=lambda x: f"L{x+2} | {df_edit.loc[x, 'Cliente']} | {df_edit.loc[x, 'Tipo']} | R$ {df_edit.loc[x, 'Valor']}")
                item = df_edit.loc[escolha]
                
                with st.form("edit_full_form"):
                    st.warning(f"Você está editando o registro na linha {escolha + 2}")
                    c1, c2 = st.columns(2)
                    e_cli = c1.text_input("Cliente", item['Cliente'])
                    e_vend = c2.selectbox("Vendedor", st.session_state['lista_vendedores'], index=st.session_state['lista_vendedores'].index(item['Vendedor']) if item['Vendedor'] in st.session_state['lista_vendedores'] else 0) if perfil_admin else c2.text_input("Vendedor", item['Vendedor'], disabled=True)
                    e_tipo = c1.text_input("Tipo/Descrição", item['Tipo'])
                    e_venc = c2.text_input("Vencimento (DD/MM/YYYY)", item['Vencimento'])
                    e_val = c1.text_input("Valor Bruto (Ex: 1500,00)", item['Valor'])
                    e_com = c2.text_input("Comissão (Ex: 75,00)", item['Comissao'])
                    e_stat = st.selectbox("Status Atual", ["Pendente", "Pago"], index=0 if item['Status'] == "Pendente" else 1)
                    
                    if st.form_submit_button("💾 Salvar Alterações Totais"):
                        params = {"row": escolha + 2, "cliente": e_cli, "vendedor": e_vend, "tipo": e_tipo, "vencimento": e_venc, "valor": e_val, "comissao": e_com, "status": e_stat}
                        resp = requests.get(SCRIPT_URL, params=params)
                        if "Sucesso" in resp.text:
                            st.success("Planilha atualizada!"); time.sleep(1); st.rerun()
            else: st.info("Nenhum registro encontrado para este filtro.")

    # --- 5. TELA: BAIXAS + WHATSAPP (COM TRAVA DE SEGURANÇA) ---
    elif menu == "✅ Baixar Pagamentos":
        st.title("✅ Conciliação e Baixas")
        if not perfil_admin: 
            st.error("Acesso exclusivo para Diretoria e CEO."); st.stop()
        
        # Se uma venda acabou de ser baixada, mostra o botão de Zap e trava a tela
        if st.session_state['venda_baixada']:
            row_recibo = st.session_state['venda_baixada']
            st.success(f"📌 Pagamento de {row_recibo['Cliente']} confirmado!")
            
            v_info = st.session_state['df_usuarios'][st.session_state['df_usuarios']['nome'] == row_recibo['Vendedor']]
            
            c_zap, c_voltar = st.columns(2)
            if not v_info.empty and 'telefone' in v_info.columns:
                tel = str(v_info.iloc[0]['telefone']).replace(".0", "").replace("+", "").strip()
                texto_zap = urllib.parse.quote(f"✅ *PAGAMENTO RECEBIDO!*\n\n*Cliente:* {row_recibo['Cliente']}\n*Valor:* R$ {row_recibo['Valor']}\n*Tipo:* {row_recibo['Tipo']}\n\nO status já foi atualizado no sistema comercial. Parabéns! 🚀")
                c_zap.link_button(f"📲 Avisar {row_recibo['Vendedor']} agora", f"https://api.whatsapp.com/send?phone={tel}&text={texto_zap}")
            else:
                c_zap.warning("Telefone do vendedor não cadastrado.")
            
            if c_voltar.button("🔙 Concluir e Voltar para Lista"):
                st.session_state['venda_baixada'] = None
                st.rerun()
            st.stop() # Mantém a tela de recibo até o usuário clicar em voltar

        # Listagem normal para baixas
        pendentes = df[df['Status'] == 'Pendente'] if not df.empty else pd.DataFrame()
        if not pendentes.empty:
            for idx, row in pendentes.iterrows():
                with st.expander(f"💰 {row['Cliente']} | {row['Tipo']} | R$ {row['Valor']}"):
                    if st.button(f"Confirmar Recebimento", key=f"pay_btn_{idx}"):
                        res_baixa = requests.get(f"{SCRIPT_URL}?row={idx+2}&status=Pago")
                        if "Sucesso" in res_baixa.text:
                            st.session_state['venda_baixada'] = row.to_dict()
                            st.rerun()
        else:
            st.success("Parabéns! Não existem recebimentos pendentes no momento.")