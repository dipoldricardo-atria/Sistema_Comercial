import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- 1. CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="Sistema de Gestão Comercial", layout="wide")

URL_BASE = "https://docs.google.com/spreadsheets/d/1TUMWuy_EjuMgzMUuT3PUVCP3P-FQA8yDN0Hv4RK46SY/edit?usp=sharing"
GID_USUARIOS = "1357723875" 
GID_VENDAS = "1045730969"   

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScWLZzEh2KOp1aqdjKkhTelImUTL4EJ7KZRr-aryX3N-92aBg/formResponse"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbweRlD1BLcYkmwNCq3yJdttmtDaWlZkVu8kB837i9rSi97Wih9m_09SG_l3PSX_wzI/exec"

def get_google_sheet(url, gid):
    base_url = url.split('/edit')[0]
    # Adicionamos um carimbo de tempo (t) para forçar o Google a ignorar o cache
    return f"{base_url}/export?format=csv&gid={gid}&t={int(time.time())}"

def limpar_financeiro(val):
    try:
        if isinstance(val, str):
            return float(val.replace('.', '').replace(',', '.'))
        return float(val)
    except:
        return 0.0

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
                # Login sempre puxa dados frescos
                df_users = pd.read_csv(get_google_sheet(URL_BASE, GID_USUARIOS))
                df_users['email'] = df_users['email'].astype(str).str.strip().str.lower()
                user = df_users[(df_users['email'] == email_input) & (df_users['senha'].astype(str) == str(senha_input))]
                if not user.empty:
                    st.session_state['logged_in'] = True
                    st.session_state['user_info'] = user.iloc[0].to_dict()
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
            except Exception as e:
                st.error(f"Erro de conexão: {e}")
else:
    user = st.session_state['user_info']
    st.sidebar.success(f"Conectado: {user['nome']}")
    
    if user['perfil'] == "Admin":
        menu = st.sidebar.radio("Navegação", ["📊 Dashboard", "📝 Cadastrar Venda", "✅ Baixa de Pagamentos"])
    else:
        menu = st.sidebar.radio("Navegação", ["💰 Minhas Comissões", "📝 Cadastrar Venda"])

    if st.sidebar.button("Sair"):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- 3. CARREGAMENTO DE DADOS COM REFRESH FORÇADO ---
    df_vendas = pd.DataFrame()
    try:
        # Puxa os dados da planilha de vendas
        df_vendas = pd.read_csv(get_google_sheet(URL_BASE, GID_VENDAS))
        df_vendas.columns = ['Timestamp', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissao', 'Status']
        df_vendas['Valor_Num'] = df_vendas['Valor'].apply(limpar_financeiro)
        df_vendas['Com_Num'] = df_vendas['Comissao'].apply(limpar_financeiro)
    except:
        st.sidebar.info("Carregando base de dados...")

    # --- 4. DASHBOARD ---
    if menu == "📊 Dashboard":
        st.title("Painel de Gestão")
        if not df_vendas.empty:
            m1, m2, m3 = st.columns(3)
            m1.metric("Faturamento Total", f"R$ {df_vendas['Valor_Num'].sum():,.2f}")
            m2.metric("Recebido (Pago)", f"R$ {df_vendas[df_vendas['Status']=='Pago']['Valor_Num'].sum():,.2f}")
            m3.metric("Pendente", f"R$ {df_vendas[df_vendas['Status']=='Pendente']['Valor_Num'].sum():,.2f}")
            st.dataframe(df_vendas.drop(columns=['Valor_Num', 'Com_Num', 'Timestamp']), use_container_width=True)

    # --- 5. CADASTRAR VENDA ---
    elif menu == "📝 Cadastrar Venda":
        st.title("Novo Contrato")
        with st.form("form_venda", clear_on_submit=True):
            col1, col2 = st.columns(2)
            cliente = col1.text_input("Nome do Cliente")
            v_total = col1.number_input("Valor Total (R$)", min_value=0.0)
            v_entrada = col2.number_input("Valor da Entrada (R$)", min_value=0.0)
            n_parc = col1.number_input("Nº de Parcelas (0 = Vista)", min_value=0, step=1)
            data_v = col2.date_input("Data da Venda", value=date.today(), format="DD/MM/YYYY")
            
            if st.form_submit_button("🚀 Salvar"):
                if cliente and v_total > 0:
                    lista = []
                    if n_parc == 0:
                        lista.append({"tipo": "À Vista", "valor": v_total, "mes": 0})
                    else:
                        if v_entrada > 0:
                            lista.append({"tipo": "Entrada", "valor": v_entrada, "mes": 0})
                        v_p = (v_total - v_entrada) / n_parc
                        for i in range(1, int(n_parc) + 1):
                            lista.append({"tipo": f"Parcela {i}/{int(n_parc)}", "valor": v_p, "mes": i})

                    for item in lista:
                        dt = data_v + relativedelta(months=item['mes'])
                        payload = {
                            "entry.1532857351": cliente,
                            "entry.1279554151": user['nome'],
                            "entry.1633578859": item['tipo'],
                            "entry.366765493": dt.strftime('%d/%m/%Y'),
                            "entry.1610537227": str(round(item['valor'], 2)).replace('.', ','),
                            "entry.1726017566": str(round(item['valor'] * 0.05, 2)).replace('.', ','),
                            "entry.622689505": "Pendente"
                        }
                        requests.post(FORM_URL, data=payload)
                    st.success("Venda registrada!")
                    time.sleep(1)
                    st.rerun()

    # --- 6. BAIXA DE PAGAMENTOS (COM REDIRECIONAMENTO DE SEGURANÇA) ---
    elif menu == "✅ Baixa de Pagamentos":
        st.title("Controle Financeiro")
        if not df_vendas.empty:
            pendentes = df_vendas[df_vendas['Status'] == 'Pendente']
            if not pendentes.empty:
                for index, row in pendentes.iterrows():
                    with st.expander(f"📌 {row['Cliente']} | {row['Tipo']} | R$ {row['Valor']}"):
                        linha_real = index + 2
                        if st.button(f"Confirmar Pagamento", key=f"btn_{index}"):
                            with st.spinner("Atualizando planilha..."):
                                try:
                                    # O 'allow_redirects=True' é fundamental para o Google Script
                                    r = requests.get(f"{SCRIPT_URL}?row={linha_real}&status=Pago", allow_redirects=True)
                                    if r.status_code == 200:
                                        st.success("Pago com sucesso!")
                                        time.sleep(1.5)
                                        st.rerun()
                                    else:
                                        st.error(f"Erro {r.status_code} no Google.")
                                except Exception as e:
                                    st.error(f"Falha: {e}")
            else:
                st.success("Nenhuma pendência!")
        else:
            st.info("Nenhum dado para exibir.")

    # --- 7. VENDEDOR ---
    elif menu == "💰 Minhas Comissões":
        st.title(f"Extrato: {user['nome']}")
        if not df_vendas.empty:
            meu_df = df_vendas[df_vendas['Vendedor'] == user['nome']].copy()
            st.dataframe(meu_df.drop(columns=['Valor_Num', 'Com_Num', 'Vendedor', 'Timestamp']), use_container_width=True)