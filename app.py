import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- 1. CONFIGURAÇÕES INICIAIS (FIXAS) ---
st.set_page_config(page_title="Gestão Comercial Tech", layout="wide")

URL_BASE = "https://docs.google.com/spreadsheets/d/1TUMWuy_EjuMgzMUuT3PUVCP3P-FQA8yDN0Hv4RK46SY/edit?usp=sharing"
GID_USUARIOS = "1357723875" 
GID_VENDAS = "1045730969"   

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScWLZzEh2KOp1aqdjKkhTelImUTL4EJ7KZRr-aryX3N-92aBg/formResponse"

def get_google_sheet(url, gid):
    base_url = url.split('/edit')[0]
    return f"{base_url}/export?format=csv&gid={gid}"

def limpar_financeiro(val):
    try:
        if isinstance(val, str):
            return float(val.replace('.', '').replace(',', '.'))
        return float(val)
    except: return 0.0

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
                else: st.error("Usuário ou senha incorretos.")
            except Exception as e: st.error(f"Erro ao acessar base: {e}")
else:
    user = st.session_state['user_info']
    st.sidebar.success(f"Logado: {user['nome']}")
    
    if user['perfil'] == "Admin":
        menu = st.sidebar.radio("Navegação", ["Dashboard", "Cadastrar Venda", "Gestão de Status"])
    else:
        menu = st.sidebar.radio("Navegação", ["Minhas Comissões"])

    if st.sidebar.button("Sair"):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- 3. TELA: DASHBOARD ---
    if menu == "Dashboard":
        st.title("📊 Painel de Controle (Diretoria)")
        st.divider()
        try:
            df_vendas = pd.read_csv(get_google_sheet(URL_BASE, GID_VENDAS))
            if not df_vendas.empty:
                df_vendas.columns = ['Timestamp', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissao', 'Status']
                df_vendas['Valor_Num'] = df_vendas['Valor'].apply(limpar_financeiro)
                df_vendas['Com_Num'] = df_vendas['Comissao'].apply(limpar_financeiro)
                
                with st.expander("🔍 Filtros Avançados"):
                    c1, c2, c3 = st.columns(3)
                    f_vendedor = c1.multiselect("Filtrar Vendedor", df_vendas['Vendedor'].unique())
                    f_status = c2.multiselect("Filtrar Status", df_vendas['Status'].unique())
                    f_cliente = c3.text_input("Buscar Cliente")

                df_filtrado = df_vendas.copy()
                if f_vendedor: df_filtrado = df_filtrado[df_filtrado['Vendedor'].isin(f_vendedor)]
                if f_status: df_filtrado = df_filtrado[df_filtrado['Status'].isin(f_status)]
                if f_cliente: df_filtrado = df_filtrado[df_filtrado['Cliente'].str.contains(f_cliente, case=False)]

                c1, c2, c3 = st.columns(3)
                c1.metric("Faturamento Total", f"R$ {df_filtrado['Valor_Num'].sum():,.2f}")
                c2.metric("Comissões Totais", f"R$ {df_filtrado['Com_Num'].sum():,.2f}")
                c3.metric("Lançamentos", len(df_filtrado))
                
                st.dataframe(df_filtrado.drop(columns=['Valor_Num', 'Com_Num']), use_container_width=True)
            else: st.info("Aba de vendas vazia.")
        except Exception as e: st.error(f"Erro no Dashboard: {e}")

    # --- 4. TELA: CADASTRAR VENDA (CORRIGIDA) ---
    elif menu == "Cadastrar Venda":
        st.title("📝 Novo Contrato")
        with st.form("form_venda", clear_on_submit=True):
            col1, col2 = st.columns(2)
            cliente = col1.text_input("Nome do Cliente")
            v_total = col1.number_input("Valor Total (R$)", min_value=0.0)
            
            # Ajuste: Se for à vista, entrada é o total e parcelas é 0
            v_entrada = col2.number_input("Entrada (R$)", min_value=0.0)
            n_parc = col1.number_input("Nº de Parcelas (Coloque 0 para À Vista)", min_value=0, step=1)
            data_v = col2.date_input("Data da Venda", value=date.today(), format="DD/MM/YYYY")
            
            if st.form_submit_button("🚀 Salvar na Nuvem"):
                if cliente != "" and v_total > 0:
                    lista_envio = []
                    
                    # LÓGICA DE PARCELAMENTO CORRIGIDA
                    if n_parc == 0:
                        # Venda À Vista: Apenas 1 linha com o valor total
                        lista_envio.append({"tipo": "À Vista", "valor": v_total, "mes": 0})
                    else:
                        # Venda Parcelada: Entrada + Parcelas
                        if v_entrada > 0:
                            lista_envio.append({"tipo": "Entrada", "valor": v_entrada, "mes": 0})
                        
                        valor_parcelado = (v_total - v_entrada) / n_parc
                        for i in range(1, int(n_parc) + 1):
                            lista_envio.append({"tipo": f"Parcela {i}/{int(n_parc)}", "valor": valor_parcelado, "mes": i})

                    sucesso_geral = True
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
                        try: requests.post(FORM_URL, data=payload)
                        except: sucesso_geral = False

                    if sucesso_geral:
                        st.success(f"✅ Venda de {cliente} registrada!")
                        st.balloons()
                    else: st.error("Erro ao salvar.")
                else: st.warning("Preencha os campos obrigatórios.")

    # --- 5. TELA: VENDEDOR ---
    elif menu == "Minhas Comissões":
        st.title(f"💰 Extrato: {user['nome']}")
        try:
            df_vendas = pd.read_csv(get_google_sheet(URL_BASE, GID_VENDAS))
            df_vendas.columns = ['Timestamp', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissao', 'Status']
            meu_df = df_vendas[df_vendas['Vendedor'] == user['nome']]
            st.dataframe(meu_df, use_container_width=True)
        except: st.error("Erro ao carregar dados.")