import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- 1. CONFIGURAÇÕES INICIAIS (MEMORIZADAS) ---
st.set_page_config(page_title="Gestão Comercial Tech", layout="wide")

# Coordenadas do Banco de Dados (Google Sheets)
URL_BASE = "https://docs.google.com/spreadsheets/d/1TUMWuy_EjuMgzMUuT3PUVCP3P-FQA8yDN0Hv4RK46SY/edit?usp=sharing"
GID_USUARIOS = "1357723875" 
GID_VENDAS = "1045730969"   

# URL do Formulário Publicado
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScWLZzEh2KOp1aqdjKkhTelImUTL4EJ7KZRr-aryX3N-92aBg/formResponse"

def get_google_sheet(url, gid):
    base_url = url.split('/edit')[0]
    return f"{base_url}/export?format=csv&gid={gid}"

# --- 2. LÓGICA DE LOGIN ---
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
                df_users['email'] = df_users['email'].astype(str).str.strip().str.lower()
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

    # --- 3. TELA: DASHBOARD (ADMIN) ---
    if menu == "Dashboard":
        st.title("📊 Painel de Controle (Diretoria)")
        st.divider()
        try:
            df_vendas = pd.read_csv(get_google_sheet(URL_BASE, GID_VENDAS))
            if not df_vendas.empty:
                def limpar_financeiro(val):
                    try:
                        if isinstance(val, str):
                            return float(val.replace('.', '').replace(',', '.'))
                        return float(val)
                    except: return 0.0

                # No Google Forms: Col 0=Timestamp, 1=Cliente, 2=Vendedor, 3=Tipo, 4=Data, 5=Valor, 6=Comissão
                df_vendas['valor_num'] = df_vendas.iloc[:, 5].apply(limpar_financeiro)
                df_vendas['com_num'] = df_vendas.iloc[:, 6].apply(limpar_financeiro)
                
                c1, c2 = st.columns(2)
                c1.metric("Faturamento Total", f"R$ {df_vendas['valor_num'].sum():,.2f}")
                c2.metric("Comissões Totais", f"R$ {df_vendas['com_num'].sum():,.2f}")
                
                st.subheader("Lista Geral de Lançamentos")
                st.dataframe(df_vendas, use_container_width=True)
            else:
                st.info("Aba de vendas vazia no Google Sheets.")
        except Exception as e:
            st.error(f"Erro ao carregar Dashboard: {e}")

    # --- 4. TELA: CADASTRAR VENDA (COM DATA BR) ---
    elif menu == "Cadastrar Venda":
        st.title("📝 Gerar e Salvar Novo Contrato")
        with st.form("form_venda", clear_on_submit=True):
            col1, col2 = st.columns(2)
            cliente = col1.text_input("Nome do Cliente")
            v_total = col1.number_input("Valor Total (R$)", min_value=0.0)
            v_entrada = col2.number_input("Entrada (R$)", min_value=0.0)
            n_parc = col1.number_input("Nº de Parcelas", min_value=1, step=1)
            
            # CORREÇÃO DO FORMATO DE DATA NA INTERFACE (DD/MM/AAAA)
            data_v = col2.date_input("Data da Venda", value=date.today(), format="DD/MM/YYYY")
            
            if st.form_submit_button("🚀 Salvar na Nuvem"):
                if cliente != "" and v_total > 0:
                    valor_parcelado = (v_total - v_entrada) / n_parc
                    sucesso_envio = True
                    
                    for i in range(int(n_parc) + 1):
                        tipo = "Entrada" if i == 0 else f"Parcela {i}/{int(n_parc)}"
                        valor_at = v_entrada if i == 0 else valor_parcelado
                        if valor_at <= 0 and i == 0: continue 
                        
                        dt_at = data_v + relativedelta(months=i)
                        
                        payload = {
                            "entry.1532857351": cliente,
                            "entry.1279554151": user['nome'],
                            "entry.1633578859": tipo,
                            "entry.366765493": dt_at.strftime('%d/%m/%Y'),
                            "entry.1610537227": str(round(valor_at, 2)).replace('.', ','),
                            "entry.1726017566": str(round(valor_at * 0.05, 2)).replace('.', ','),
                            "entry.622689505": "Pendente"
                        }
                        
                        try:
                            r = requests.post(FORM_URL, data=payload)
                            if r.status_code != 200:
                                sucesso_envio = False
                        except:
                            sucesso_envio = False

                    if sucesso_envio:
                        st.success(f"✅ Venda de {cliente} salva com sucesso!")
                        st.balloons()
                    else:
                        st.error("Erro ao registrar. Verifique a conexão.")
                else:
                    st.warning("Preencha o nome do cliente e o valor total.")

    # --- 5. TELA: VENDEDOR ---
    elif menu == "Minhas Comissões":
        st.title(f"💰 Extrato: {user['nome']}")
        try:
            df_vendas = pd.read_csv(get_google_sheet(URL_BASE, GID_VENDAS))
            meu_df = df_vendas[df_vendas.iloc[:, 2] == user['nome']]
            st.dataframe(meu_df, use_container_width=True)
        except:
            st.error("Erro ao carregar dados.")