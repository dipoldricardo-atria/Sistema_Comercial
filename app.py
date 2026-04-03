import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- 1. CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="Sistema de Gestão Comercial", layout="wide")

# Coordenadas do Banco de Dados
URL_BASE = "https://docs.google.com/spreadsheets/d/1TUMWuy_EjuMgzMUuT3PUVCP3P-FQA8yDN0Hv4RK46SY/edit?usp=sharing"
GID_USUARIOS = "1357723875" 
GID_VENDAS = "1045730969"   

# URL do Formulário para Cadastrar Novas Vendas
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScWLZzEh2KOp1aqdjKkhTelImUTL4EJ7KZRr-aryX3N-92aBg/formResponse"

# URL do seu Apps Script para dar Baixa (Status)
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbweRlD1BLcYkmwNCq3yJdttmtDaWlZkVu8kB837i9rSi97Wih9m_09SG_l3PSX_wzI/exec"

def get_google_sheet(url, gid):
    base_url = url.split('/edit')[0]
    return f"{base_url}/export?format=csv&gid={gid}"

def limpar_financeiro(val):
    try:
        if isinstance(val, str):
            # Converte formato BR (1.500,50) para float (1500.50)
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
                st.error(f"Erro ao acessar base de usuários: {e}")
else:
    # --- ÁREA LOGADA ---
    user = st.session_state['user_info']
    st.sidebar.success(f"Conectado: {user['nome']}")
    
    # Menu dinâmico por perfil
    if user['perfil'] == "Admin":
        menu = st.sidebar.radio("Navegação", ["📊 Dashboard", "📝 Cadastrar Venda", "✅ Baixa de Pagamentos"])
    else:
        menu = st.sidebar.radio("Navegação", ["💰 Minhas Comissões", "📝 Cadastrar Venda"])

    if st.sidebar.button("Sair"):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- 3. CARREGAMENTO GLOBAL DE DADOS (DENTRO DA ÁREA LOGADA) ---
    df_vendas = pd.DataFrame()
    try:
        df_vendas = pd.read_csv(get_google_sheet(URL_BASE, GID_VENDAS))
        # Mapeia as colunas do Google Forms para nomes amigáveis
        df_vendas.columns = ['Timestamp', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissao', 'Status']
        df_vendas['Valor_Num'] = df_vendas['Valor'].apply(limpar_financeiro)
        df_vendas['Com_Num'] = df_vendas['Comissao'].apply(limpar_financeiro)
    except Exception as e:
        st.sidebar.warning("Aguardando lançamentos na planilha...")

    # --- 4. TELA: DASHBOARD (ADMIN) ---
    if menu == "📊 Dashboard":
        st.title("Painel de Gestão Estratégica")
        st.divider()
        
        if not df_vendas.empty:
            with st.expander("🔍 Filtros Avançados"):
                c1, c2, c3 = st.columns(3)
                f_vendedor = c1.multiselect("Vendedor", df_vendas['Vendedor'].unique())
                f_status = c2.multiselect("Status", ["Pendente", "Pago"])
                f_cliente = c3.text_input("Buscar Cliente")

            df_f = df_vendas.copy()
            if f_vendedor: df_f = df_f[df_f['Vendedor'].isin(f_vendedor)]
            if f_status: df_f = df_f[df_f['Status'].isin(f_status)]
            if f_cliente: df_f = df_f[df_f['Cliente'].str.contains(f_cliente, case=False)]

            m1, m2, m3 = st.columns(3)
            m1.metric("Faturamento Total", f"R$ {df_f['Valor_Num'].sum():,.2f}")
            m2.metric("Total Recebido (Pago)", f"R$ {df_f[df_f['Status']=='Pago']['Valor_Num'].sum():,.2f}")
            m3.metric("Comissões Totais", f"R$ {df_f['Com_Num'].sum():,.2f}")

            st.subheader("Lista Geral de Recebíveis")
            st.dataframe(df_f.drop(columns=['Valor_Num', 'Com_Num', 'Timestamp']), use_container_width=True)
        else:
            st.info("Nenhum dado encontrado na planilha de vendas.")

    # --- 5. TELA: CADASTRAR VENDA ---
    elif menu == "📝 Cadastrar Venda":
        st.title("Novo Contrato")
        with st.form("form_venda", clear_on_submit=True):
            col1, col2 = st.columns(2)
            cliente = col1.text_input("Nome do Cliente")
            v_total = col1.number_input("Valor Total (R$)", min_value=0.0)
            v_entrada = col2.number_input("Valor da Entrada (R$)", min_value=0.0)
            n_parc = col1.number_input("Nº de Parcelas (0 = À Vista)", min_value=0, step=1)
            data_v = col2.date_input("Data da Venda", value=date.today(), format="DD/MM/YYYY")
            
            if st.form_submit_button("🚀 Salvar na Nuvem"):
                if cliente and v_total > 0:
                    lista_envio = []
                    if n_parc == 0:
                        lista_envio.append({"tipo": "À Vista", "valor": v_total, "mes": 0})
                    else:
                        if v_entrada > 0:
                            lista_envio.append({"tipo": "Entrada", "valor": v_entrada, "mes": 0})
                        v_parcela = (v_total - v_entrada) / n_parc
                        for i in range(1, int(n_parc) + 1):
                            lista_envio.append({"tipo": f"Parcela {i}/{int(n_parc)}", "valor": v_parcela, "mes": i})

                    sucesso = True
                    for item in lista_envio:
                        dt_at = data_v + relativedelta(months=item['mes'])
                        payload = {
                            "entry.1532857351": cliente,
                            "entry.1279554151": user['nome'],
                            "entry.1633578859": item['tipo'],
                            "entry.366765493": dt_at.strftime('%d/%m/%Y'),
                            "entry.1610537227": str(round(item['valor'], 2)).replace('.', ','),
                            "entry.1726017566": str(round(item['valor'] * 0.05, 2)).replace('.', ','),
                            "entry.622689505": "Pendente"
                        }
                        try:
                            requests.post(FORM_URL, data=payload)
                        except:
                            sucesso = False

                    if sucesso:
                        st.success(f"Venda de {cliente} registrada!")
                        st.balloons()
                    else:
                        st.error("Erro ao enviar dados.")
                else:
                    st.warning("Preencha cliente e valor total.")

    # --- 6. TELA: BAIXA DE PAGAMENTOS ---
    elif menu == "✅ Baixa de Pagamentos":
        st.title("Baixa Financeira")
        st.divider()
        
        if not df_vendas.empty:
            pendentes = df_vendas[df_vendas['Status'] == 'Pendente']
            if not pendentes.empty:
                st.info(f"Existem {len(pendentes)} lançamentos pendentes.")
                for index, row in pendentes.iterrows():
                    with st.expander(f"📌 {row['Cliente']} | {row['Tipo']} | R$ {row['Valor']}"):
                        linha_real = index + 2
                        if st.button(f"Confirmar Recebimento", key=f"btn_{index}"):
                            try:
                                url_final = f"{SCRIPT_URL}?row={linha_real}&status=Pago"
                                r = requests.get(url_final)
                                if r.status_code == 200:
                                    st.success(f"Status atualizado!")
                                    st.rerun()
                                else:
                                    st.error("Erro no script do Google.")
                            except Exception as e:
                                st.error(f"Erro: {e}")
            else:
                st.success("Tudo em dia! Sem pendências.")
        else:
            st.info("Nenhuma venda carregada para dar baixa.")

    # --- 7. TELA: VENDEDOR ---
    elif menu == "💰 Minhas Comissões":
        st.title(f"Extrato Comercial: {user['nome']}")
        if not df_vendas.empty:
            meu_df = df_vendas[df_vendas['Vendedor'] == user['nome']].copy()
            c1, c2 = st.columns(2)
            c1.metric("Comissão Recebida", f"R$ {meu_df[meu_df['Status'] == 'Pago']['Com_Num'].sum():,.2f}")
            c2.metric("Comissão Pendente", f"R$ {meu_df[meu_df['Status'] == 'Pendente']['Com_Num'].sum():,.2f}")
            st.dataframe(meu_df.drop(columns=['Valor_Num', 'Com_Num', 'Vendedor', 'Timestamp']), use_container_width=True)
        else:
            st.info("Nenhuma venda registrada no seu nome.")