import streamlit as st
import pandas as pd
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- CONFIGURAÇÕES ---
URL_BASE = "https://docs.google.com/spreadsheets/d/1TUMWuy_EjuMgzMUuT3PUVCP3P-FQA8yDN0Hv4RK46SY/edit?usp=sharing"
GID_USUARIOS = "1357723875"
GID_VENDAS = "0"

st.set_page_config(page_title="Gestão Comercial Tech", layout="wide")

def get_google_sheet(url, gid):
    base_url = url.split('/edit')[0]
    return f"{base_url}/export?format=csv&gid={gid}"

# --- LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🚀 Portal Comercial - Login")
    with st.sidebar:
        email_input = st.text_input("E-mail").strip().lower()
        senha_input = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            try:
                df_users = pd.read_csv(get_google_sheet(URL_BASE, GID_USUARIOS))
                df_users['email'] = df_users['email'].str.strip().str.lower()
                user = df_users[(df_users['email'] == email_input) & (df_users['senha'].astype(str) == str(senha_input))]
                if not user.empty:
                    st.session_state['logged_in'] = True
                    st.session_state['user_info'] = user.iloc[0]
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
            except Exception as e:
                st.error(f"Erro ao acessar base: {e}")
else:
    user = st.session_state['user_info']
    st.sidebar.success(f"Logado: {user['nome']}")
    
    if user['perfil'] == "Admin":
        menu = st.sidebar.radio("Navegação", ["Dashboard", "Cadastrar Venda"])
    else:
        menu = st.sidebar.radio("Navegação", ["Minhas Comissões"])

    if st.sidebar.button("Sair"):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- TELAS ---
    if menu == "Dashboard":
        st.title("📊 Painel de Controle (Diretoria)")
        st.divider()
        try:
            df_vendas = pd.read_csv(get_google_sheet(URL_BASE, GID_VENDAS))
            if not df_vendas.empty:
                c1, c2 = st.columns(2)
                c1.metric("Faturamento Total", f"R$ {df_vendas['valor'].sum():,.2f}")
                c2.metric("Comissões Totais", f"R$ {df_vendas['comissao'].sum():,.2f}")
                st.subheader("Lista Geral de Recebíveis")
                st.dataframe(df_vendas, use_container_width=True)
            else:
                st.info("Aba de vendas vazia.")
        except:
            st.error("Erro ao ler aba de vendas.")

    elif menu == "Cadastrar Venda":
        st.title("📝 Gerar Novo Contrato")
        with st.form("form_venda"):
            cliente = st.text_input("Nome do Cliente")
            v_total = st.number_input("Valor Total (R$)", min_value=0.0)
            v_entrada = st.number_input("Entrada (R$)", min_value=0.0)
            n_parc = st.number_input("Nº de Parcelas", min_value=1, step=1)
            data_v = st.date_input("Data da Venda", date.today())
            
            if st.form_submit_button("Gerar Cronograma"):
                valor_parc = (v_total - v_entrada) / n_parc
                dados = []
                if v_entrada > 0:
                    dados.append({"cliente": cliente, "vendedor": user['nome'], "tipo": "Entrada", "data": data_v.strftime('%d/%m/%Y'), "valor": v_entrada, "comissao": v_entrada*0.05, "status": "Pendente"})
                for i in range(1, int(n_parc) + 1):
                    dt = data_v + relativedelta(months=i)
                    dados.append({"cliente": cliente, "vendedor": user['nome'], "tipo": f"Parc {i}", "data": dt.strftime('%d/%m/%Y'), "valor": valor_parc, "comissao": valor_parc*0.05, "status": "Pendente"})
                st.success("Copiado! Cole na sua planilha:")
                st.dataframe(pd.DataFrame(dados))

    elif menu == "Minhas Comissões":
        st.title(f"💰 Extrato: {user['nome']}")
        try:
            df_vendas = pd.read_csv(get_google_sheet(URL_BASE, GID_VENDAS))
            meu_df = df_vendas[df_vendas['vendedor'] == user['nome']]
            st.metric("Minha Comissão Total", f"R$ {meu_df['comissao'].sum():,.2f}")
            st.dataframe(meu_df)
        except:
            st.error("Erro ao carregar dados.")