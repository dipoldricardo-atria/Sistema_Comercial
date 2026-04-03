import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- 1. CONFIGURAÇÕES ---
st.set_page_config(page_title="Sistema Comercial", layout="wide")

# Dados da Planilha
URL_BASE = "https://docs.google.com/spreadsheets/d/1TUMWuy_EjuMgzMUuT3PUVCP3P-FQA8yDN0Hv4RK46SY/edit?usp=sharing"
GID_VENDAS = "1045730969"
GID_USUARIOS = "1357723875"

# Endereços de Comunicação
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScWLZzEh2KOp1aqdjKkhTelImUTL4EJ7KZRr-aryX3N-92aBg/formResponse"
# SEU NOVO LINK AQUI:
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwOR4tCPLwpmn28h4TqG-hz4HxM5APUhoZ00TgQ6SVz6rSs79r1rixjmw9K6CoRJFdI/exec"

def carregar_dados(gid):
    # O carimbo de tempo (t) força o Google a entregar o dado MAIS NOVO, sem cache.
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
    st.sidebar.write(f"Usuário: **{user['nome']}**")
    
    # Menu Administrativo vs Vendedor
    if user['perfil'] == "Admin":
        menu = st.sidebar.radio("Navegação", ["📊 Dashboard", "📝 Nova Venda", "✅ Baixar Pagamentos"])
    else:
        menu = st.sidebar.radio("Navegação", ["💰 Minhas Comissões", "📝 Nova Venda"])
    
    if st.sidebar.button("Sair"):
        st.session_state['logged_in'] = False
        st.rerun()

    # Carregamento de Vendas (Atualizado em tempo real)
    try:
        df = carregar_dados(GID_VENDAS)
        df.columns = ['ID', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissao', 'Status']
        df['Val_N'] = df['Valor'].apply(limpar_financeiro)
    except: df = pd.DataFrame()

    # --- TELA: BAIXAS (O CORAÇÃO DO SISTEMA AGORA) ---
    if menu == "✅ Baixar Pagamentos":
        st.title("Gestão de Recebíveis")
        pendentes = df[df['Status'] == 'Pendente']
        
        if not pendentes.empty:
            st.info(f"Você tem {len(pendentes)} pagamentos aguardando baixa.")
            for idx, row in pendentes.iterrows():
                # A linha real na planilha (Cabeçalho + Index 0 do Pandas = idx + 2)
                linha_google = idx + 2
                
                with st.expander(f"📍 {row['Cliente']} | {row['Tipo']} | R$ {row['Valor']}"):
                    if st.button(f"Confirmar Pagamento", key=f"btn_{idx}"):
                        with st.spinner("Atualizando planilha do Google..."):
                            try:
                                # Chama o Script passando a linha e o novo status
                                url_final = f"{SCRIPT_URL}?row={linha_google}&status=Pago"
                                response = requests.get(url_final, timeout=15)
                                
                                if "Sucesso" in response.text:
                                    st.success(f"Baixa realizada! {row['Cliente']} agora está PAGO.")
                                    time.sleep(2) # Espera o Google processar o salvamento
                                    st.rerun()
                                else:
                                    st.error(f"O Google recebeu mas deu erro: {response.text}")
                            except Exception as e:
                                st.error(f"Erro de conexão com o Google: {e}")
        else:
            st.success("Tudo em dia! Nenhuma pendência encontrada.")

    # --- TELA: NOVA VENDA (CORRIGIDA) ---
    elif menu == "📝 Nova Venda":
        st.title("Lançar Venda")
        with st.form("venda_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            cli = col1.text_input("Cliente")
            tot = col1.number_input("Valor Total", min_value=0.0)
            ent = col2.number_input("Entrada", min_value=0.0)
            parc = col1.number_input("Parcelas (0=Vista)", min_value=0, step=1)
            dat = col2.date_input("Data", format="DD/MM/YYYY")
            
            if st.form_submit_button("🚀 Salvar Venda"):
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
                st.success("Contrato salvo com sucesso!")
                time.sleep(1); st.rerun()

    # --- TELA: DASHBOARD ---
    elif menu == "📊 Dashboard":
        st.title("Indicadores Gerenciais")
        if not df.empty:
            m1, m2 = st.columns(2)
            m1.metric("Faturamento Geral", f"R$ {df['Val_N'].sum():,.2f}")
            m2.metric("Total em Aberto", f"R$ {df[df['Status']=='Pendente']['Val_N'].sum():,.2f}")
            st.dataframe(df.drop(columns=['Val_N']), use_container_width=True)