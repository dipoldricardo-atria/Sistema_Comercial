import streamlit as st
import pandas as pd
import requests
import time
import urllib.parse
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- 1. CONFIGURAÇÕES E LINKS ---
st.set_page_config(page_title="Sistema Comercial PRO", layout="wide")

URL_BASE = "https://docs.google.com/spreadsheets/d/1TUMWuy_EjuMgzMUuT3PUVCP3P-FQA8yDN0Hv4RK46SY/edit?usp=sharing"
GID_VENDAS = "1045730969"
GID_USUARIOS = "1357723875"
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScWLZzEh2KOp1aqdjKkhTelImUTL4EJ7KZRr-aryX3N-92aBg/formResponse"
# Use o link do seu Apps Script atualizado
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
            st.session_state['df_usuarios'] = df_u # Guarda para consulta de telefone
            st.rerun()
        else: st.error("Login inválido.")
else:
    user = st.session_state['user_info']
    perfil_admin = user['perfil'] == "Admin"
    
    st.sidebar.markdown(f"👤 **{user['nome']}**")
    st.sidebar.markdown(f"🏷️ `{user['perfil']}`")
    
    menu_opcoes = ["📊 Dashboard Performance", "📝 Lançar Venda", "✅ Baixas e Edições"]
    menu = st.sidebar.radio("Navegação", menu_opcoes)
    
    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()

    # --- 3. CARREGAR VENDAS ---
    try:
        df = carregar_dados(GID_VENDAS)
        df.columns = ['ID', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissao', 'Status']
        df['Val_N'] = df['Valor'].apply(limpar_financeiro)
        df['Com_N'] = df['Comissao'].apply(limpar_financeiro)
        df['Data_Venc'] = pd.to_datetime(df['Vencimento'], dayfirst=True)
    except: df = pd.DataFrame()

    # --- 4. TELA: DASHBOARD INTELIGENTE ---
    if menu == "📊 Dashboard Performance":
        st.title("📊 Indicadores Comerciais")
        if not df.empty:
            # Filtro Automático por Hierarquia
            df_base = df.copy() if perfil_admin else df[df['Vendedor'] == user['nome']]
            
            with st.container(border=True):
                c1, c2 = st.columns(2)
                if perfil_admin:
                    sel_v = c1.multiselect("Filtrar Vendedores", df_base['Vendedor'].unique())
                    if sel_v: df_base = df_base[df_base['Vendedor'].isin(sel_v)]
                
                meses = ["Todos"] + sorted(df_base['Data_Venc'].dt.strftime('%m/%Y').unique().tolist())
                sel_m = c2.selectbox("Mês de Referência", meses)
                if sel_m != "Todos":
                    df_base = df_base[df_base['Data_Venc'].dt.strftime('%m/%Y') == sel_m]

            m1, m2, m3 = st.columns(3)
            m1.metric("Faturamento", f"R$ {df_base['Val_N'].sum():,.2f}")
            m2.metric("Recebido (Pago)", f"R$ {df_base[df_base['Status']=='Pago']['Val_N'].sum():,.2f}")
            m3.metric("Comissões", f"R$ {df_base['Com_N'].sum():,.2f}")
            
            st.dataframe(df_base.drop(columns=['Val_N', 'Com_N', 'Data_Venc']), use_container_width=True)
        else: st.info("Sem dados.")

    # --- 5. TELA: LANÇAR VENDA ---
    elif menu == "📝 Lançar Venda":
        st.title("📝 Registro de Contrato")
        with st.form("f_venda", clear_on_submit=True):
            c1, c2 = st.columns(2)
            cli = c1.text_input("Nome do Cliente")
            
            if perfil_admin:
                vend_f = c2.selectbox("Dono da Venda", st.session_state['lista_vendedores'])
            else:
                vend_f = c2.text_input("Vendedor", value=user['nome'], disabled=True)
                
            total = c1.number_input("Valor Total", min_value=0.0)
            ent = c2.number_input("Entrada", min_value=0.0)
            parc = c1.number_input("Parcelas (0=Vista)", min_value=0, step=1)
            data_v = c2.date_input("Data da Venda")
            
            if st.form_submit_button("🚀 Salvar Venda"):
                if cli and total > 0:
                    itens = []
                    if parc == 0: itens.append({"t": "À Vista", "v": total, "m": 0})
                    else:
                        if ent > 0: itens.append({"t": "Entrada", "v": ent, "m": 0})
                        vp = (total - ent) / parc
                        for i in range(1, int(parc)+1): itens.append({"t": f"Parcela {i}/{int(parc)}", "v": vp, "m": i})
                    
                    for it in itens:
                        dv = data_v + relativedelta(months=it['m'])
                        pld = {"entry.1532857351": cli, "entry.1279554151": vend_f, "entry.1633578859": it['t'], "entry.366765493": dv.strftime('%d/%m/%Y'), "entry.1610537227": str(round(it['v'], 2)).replace('.', ','), "entry.1726017566": str(round(it['v']*0.05, 2)).replace('.', ','), "entry.622689505": "Pendente"}
                        requests.post(FORM_URL, data=pld)
                    st.success("Lançado com sucesso!"); time.sleep(1); st.rerun()

    # --- 6. TELA: BAIXAS, EDIÇÕES E WHATSAPP ---
    elif menu == "✅ Baixas e Edições":
        st.title("✅ Gestão de Recebimentos")
        
        # Só admin dá baixa. Vendedores só veem histórico.
        if perfil_admin:
            pendentes = df[df['Status'] == 'Pendente']
            if not pendentes.empty:
                for idx, row in pendentes.iterrows():
                    linha_google = idx + 2
                    with st.expander(f"💰 {row['Cliente']} | {row['Tipo']} | R$ {row['Valor']}"):
                        ca, cb = st.columns(2)
                        
                        # BOTAO BAIXA + WHATSAPP
                        if ca.button("Confirmar Pagamento", key=f"p_{idx}"):
                            r = requests.get(f"{SCRIPT_URL}?row={linha_google}&status=Pago")
                            if "Sucesso" in r.text:
                                st.success("Pago na Planilha!")
                                
                                # Busca Telefone do Vendedor
                                df_u = st.session_state['df_usuarios']
                                vendedor_data = df_u[df_u['nome'] == row['Vendedor']]
                                
                                if not vendedor_data.empty and 'telefone' in vendedor_data.columns:
                                    tel = str(vendedor_data.iloc[0]['telefone']).replace(".0", "")
                                    texto = urllib.parse.quote(f"✅ *PAGAMENTO CONFIRMADO!*\n\nCliente: {row['Cliente']}\nValor: R$ {row['Valor']}\nTipo: {row['Tipo']}\n\nO status já foi atualizado no portal. Boas vendas! 🚀")
                                    st.link_button(f"📲 Avisar {row['Vendedor']} no WhatsApp", f"https://api.whatsapp.com/send?phone={tel}&text={texto}")
                                else:
                                    st.warning("Vendedor sem telefone cadastrado.")
                                    time.sleep(2); st.rerun()
                        
                        # BOTAO EDIÇÃO
                        if cb.button("✏️ Editar Valor/Nome", key=f"e_{idx}"):
                            st.session_state[f"ed_{idx}"] = True
                        
                        if st.session_state.get(f"ed_{idx}", False):
                            with st.form(f"f_ed_{idx}"):
                                n_cli = st.text_input("Corrigir Nome", row['Cliente'])
                                n_val = st.text_input("Corrigir Valor", row['Valor'])
                                if st.form_submit_button("Salvar"):
                                    requests.get(f"{SCRIPT_URL}?row={linha_google}&cliente={n_cli}&valor={n_val}")
                                    st.success("Alterado!"); time.sleep(1)
                                    del st.session_state[f"ed_{idx}"]
                                    st.rerun()
            else: st.success("Nenhuma pendência!")
        else:
            st.info("Apenas CEO e Diretores podem realizar baixas. Confira seu extrato no Dashboard.")
            st.dataframe(df[df['Vendedor'] == user['nome']], use_container_width=True)