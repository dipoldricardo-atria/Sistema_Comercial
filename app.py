import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- 1. CONFIGURAÇÕES ---
st.set_page_config(page_title="Gestão Comercial", layout="wide")

URL_BASE = "https://docs.google.com/spreadsheets/d/1TUMWuy_EjuMgzMUuT3PUVCP3P-FQA8yDN0Hv4RK46SY/edit?usp=sharing"
GID_USUARIOS = "1357723875" 
GID_VENDAS = "1045730969"   
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScWLZzEh2KOp1aqdjKkhTelImUTL4EJ7KZRr-aryX3N-92aBg/formResponse"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbweRlD1BLcYkmwNCq3yJdttmtDaWlZkVu8kB837i9rSi97Wih9m_09SG_l3PSX_wzI/exec"

def get_sheet(gid):
    # Cache busting com timestamp para evitar dados velhos
    return f"https://docs.google.com/spreadsheets/d/1TUMWuy_EjuMgzMUuT3PUVCP3P-FQA8yDN0Hv4RK46SY/export?format=csv&gid={gid}&t={int(time.time())}"

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
    with st.sidebar:
        u_in = st.text_input("E-mail").strip().lower()
        s_in = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            df_u = pd.read_csv(get_sheet(GID_USUARIOS))
            user = df_u[(df_u['email'].str.lower() == u_in) & (df_u['senha'].astype(str) == s_in)]
            if not user.empty:
                st.session_state['logged_in'] = True
                st.session_state['user_info'] = user.iloc[0].to_dict()
                st.rerun()
            else: st.error("Erro de login.")
else:
    user = st.session_state['user_info']
    st.sidebar.success(f"Olá, {user['nome']}")
    menu = st.sidebar.radio("Menu", ["📊 Dashboard", "📝 Venda", "✅ Baixas"]) if user['perfil'] == "Admin" else st.sidebar.radio("Menu", ["💰 Comissões", "📝 Venda"])
    if st.sidebar.button("Sair"):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- 3. CARREGAR VENDAS ---
    try:
        df = pd.read_csv(get_sheet(GID_VENDAS))
        df.columns = ['ID', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissao', 'Status']
        df['Val_N'] = df['Valor'].apply(limpar_financeiro)
        df['Com_N'] = df['Comissao'].apply(limpar_financeiro)
    except: df = pd.DataFrame()

    # --- 4. TELAS ---
    if menu == "📊 Dashboard":
        st.title("Dashboard")
        if not df.empty:
            c1, c2 = st.columns(2)
            c1.metric("Faturamento", f"R$ {df['Val_N'].sum():,.2f}")
            c2.metric("Recebido", f"R$ {df[df['Status']=='Pago']['Val_N'].sum():,.2f}")
            st.dataframe(df.drop(columns=['Val_N', 'Com_N']), use_container_width=True)

    elif menu == "📝 Venda":
        st.title("Nova Venda")
        with st.form("venda"):
            cli = st.text_input("Cliente")
            tot = st.number_input("Total", min_value=0.0)
            ent = st.number_input("Entrada", min_value=0.0)
            parc = st.number_input("Parcelas (0=Vista)", min_value=0, step=1)
            dat = st.date_input("Data", format="DD/MM/YYYY")
            if st.form_submit_button("Salvar"):
                itens = [{"t": "À Vista", "v": tot, "m": 0}] if parc == 0 else []
                if parc > 0:
                    if ent > 0: itens.append({"t": "Entrada", "v": ent, "m": 0})
                    vp = (tot - ent) / parc
                    for i in range(1, int(parc)+1): itens.append({"t": f"Parcela {i}/{int(parc)}", "v": vp, "m": i})
                for it in itens:
                    dv = dat + relativedelta(months=it['m'])
                    payload = {"entry.1532857351": cli, "entry.1279554151": user['nome'], "entry.1633578859": it['t'], "entry.366765493": dv.strftime('%d/%m/%Y'), "entry.1610537227": str(round(it['v'], 2)).replace('.', ','), "entry.1726017566": str(round(it['v']*0.05, 2)).replace('.', ','), "entry.622689505": "Pendente"}
                    requests.post(FORM_URL, data=payload)
                st.success("Registrado!")
                time.sleep(1); st.rerun()

    elif menu == "✅ Baixas":
        st.title("Baixa de Pagamentos")
        pendentes = df[df['Status'] == 'Pendente']
        if not pendentes.empty:
            for idx, row in pendentes.iterrows():
                # O ID é o Timestamp da coluna 0
                id_venda = str(row['ID'])
                with st.expander(f"📌 {row['Cliente']} - {row['Tipo']} (R$ {row['Valor']})"):
                    if st.button(f"Confirmar Recebimento", key=f"btn_{idx}"):
                        # Envia o ID para o Script buscar a linha exata
                        res = requests.get(f"{SCRIPT_URL}?id={id_venda}&status=Pago")
                        if res.status_code == 200:
                            st.success("Atualizado!")
                            time.sleep(1); st.rerun()
                        else: st.error("Erro no Google.")
        else: st.success("Sem pendências.")