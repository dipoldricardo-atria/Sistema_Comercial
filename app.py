import streamlit as st
import pandas as pd

# --- CONFIGURAÇÃO ---
URL_BASE = "https://docs.google.com/spreadsheets/d/1TUMWuy_EjuMgzMUuT3PUVCP3P-FQA8yDN0Hv4RK46SY/edit?usp=sharing"

# INSIRA AQUI OS GIDs QUE VOCÊ ENCONTROU NA URL DA PLANILHA
GID_USUARIOS = "1357723875" 
GID_VENDAS = "0" # Geralmente a primeira aba é 0, mas confirme na URL

def get_google_sheet(url, gid):
    # Esta função garante que o Python foque na aba correta
    base_url = url.split('/edit')[0]
    return f"{base_url}/export?format=csv&gid={gid}"

# --- SISTEMA DE LOGIN ATUALIZADO ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

def tela_login():
    st.title("🚀 Portal Comercial - Empresa Tech")
    with st.sidebar:
        st.subheader("Login de Acesso")
        email_input = st.text_input("E-mail").strip().lower() # Remove espaços e deixa minúsculo
        senha_input = st.text_input("Senha", type="password")
        
        if st.button("Entrar"):
            try:
                # Lendo especificamente a aba de usuários usando o GID
                link_usuarios = get_google_sheet(URL_BASE, GID_USUARIOS)
                df_users = pd.read_csv(link_usuarios)
                
                # Limpeza de dados para evitar erro de comparação
                df_users['email'] = df_users['email'].str.strip().str.lower()
                df_users['senha'] = df_users['senha'].astype(str).str.strip()
                
                user = df_users[(df_users['email'] == email_input) & (df_users['senha'] == str(senha_input))]
                
                if not user.empty:
                    st.session_state['logged_in'] = True
                    st.session_state['user_info'] = user.iloc[0]
                    st.rerun()
                else:
                    st.error("Usuário ou senha não encontrados na aba 'usuarios'.")
            except Exception as e:
                st.error(f"Erro técnico: {e}")
                st.info("Verifique se o nome das colunas na aba 'usuarios' são: email, senha, nome, perfil")

if not st.session_state['logged_in']:
    tela_login()
# ... (restante do código segue igual)
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