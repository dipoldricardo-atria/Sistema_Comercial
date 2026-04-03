import streamlit as st
import pandas as pd
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- 1. CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Gestão Comercial Tech", layout="wide")

# COLE O LINK DA SUA PLANILHA AQUI (Certifique-se que termina em /edit?usp=sharing)
URL_BASE = "https://docs.google.com/spreadsheets/d/1TUMWuy_EjuMgzMUuT3PUVCP3P-FQA8yDN0Hv4RK46SY/edit?usp=sharing"

# Função para converter link do Google em link de leitura direta (CSV)
def get_google_sheet(url, gid="0"):
    return url.replace('/edit?usp=sharing', f'/export?format=csv&gid={gid}')

# --- 2. SISTEMA DE LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

def tela_login():
    st.title("🚀 Portal Comercial - Empresa Tech")
    with st.sidebar:
        st.subheader("Acesso Interno")
        email_input = st.text_input("E-mail")
        senha_input = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            try:
                # GID da aba 'usuarios' (normalmente a segunda aba tem um GID diferente, 
                # mas vamos tentar ler a principal para validar o acesso)
                df_users = pd.read_csv(get_google_sheet(URL_BASE))
                user = df_users[(df_users['email'] == email_input) & (df_users['senha'].astype(str) == senha_input)]
                
                if not user.empty:
                    st.session_state['logged_in'] = True
                    st.session_state['user_info'] = user.iloc[0]
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
            except:
                st.error("Erro ao acessar base de usuários. Verifique a planilha.")

if not st.session_state['logged_in']:
    tela_login()
else:
    user = st.session_state['user_info']
    st.sidebar.success(f"Olá, {user['nome']}")
    if st.sidebar.button("Sair"):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- 3. MENU DE NAVEGAÇÃO (ADMIN vs VENDEDOR) ---
    if user['perfil'] == "Admin":
        menu = st.sidebar.radio("Navegação", ["Dashboard", "Nova Venda", "Baixa de Pagamentos"])
    else:
        menu = st.sidebar.radio("Navegação", ["Minhas Comissões"])

    # --- ABA: DASHBOARD ---
    if menu == "Dashboard":
        st.title("📊 Visão do Diretor")
        st.divider()
        st.info("Abaixo você visualiza o resumo de todas as vendas e parcelas.")
        
        # Simulando a leitura das vendas
        try:
            df_vendas = pd.read_csv(get_google_sheet(URL_BASE)) # Aqui você usaria o GID da aba vendas
            st.dataframe(df_vendas, use_container_width=True)
        except:
            st.warning("Aba de vendas ainda não populada.")

    # --- ABA: NOVA VENDA ---
    elif menu == "Nova Venda":
        st.title("📝 Cadastrar Novo Projeto")
        with st.form("form_venda"):
            cliente = st.text_input("Nome do Cliente")
            v_total = st.number_input("Valor Total (R$)", min_value=0.0)
            v_entrada = st.number_input("Entrada (R$)", min_value=0.0)
            n_parc = st.number_input("Nº de Parcelas", min_value=1, step=1)
            data_v = st.date_input("Data da Venda", date.today())
            
            if st.form_submit_button("Gerar Plano de Recebimento"):
                # Cálculo das parcelas
                restante = (v_total - v_entrada) / n_parc
                cronograma = []
                # Entrada
                cronograma.append({"Tipo": "Entrada", "Data": data_v, "Valor": v_entrada, "Comissão (5%)": v_entrada*0.05})
                # Mensalidades
                for i in range(1, n_parc + 1):
                    dt = data_v + relativedelta(months=i)
                    cronograma.append({"Tipo": f"Parcela {i}/{n_parc}", "Data": dt, "Valor": restante, "Comissão (5%)": restante*0.05})
                
                st.write("### Plano Gerado:")
                st.table(pd.DataFrame(cronograma))
                st.warning("⚠️ Copie os dados acima e cole na sua planilha 'vendas' para salvar.")