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

# Link de Envio do Formulário Publicado
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScWLZzEh2KOp1aqdjKkhTelImUTL4EJ7KZRr-aryX3N-92aBg/formResponse"

def get_google_sheet(url, gid):
    base_url = url.split('/edit')[0]
    return f"{base_url}/export?format=csv&gid={gid}"

def limpar_financeiro(val):
    try:
        if isinstance(val, str):
            # Trata formato brasileiro (1.500,50 -> 1500.50)
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
                    st.session_state['user_info'] = user.iloc[0].to_dict()
                    st.rerun()
                else: st.error("Usuário ou senha incorretos.")
            except Exception as e: st.error(f"Erro ao acessar base: {e}")
else:
    user = st.session_state['user_info']
    st.sidebar.success(f"Conectado: {user['nome']}")
    
    # Menu baseado no perfil
    if user['perfil'] == "Admin":
        menu = st.sidebar.radio("Navegação", ["📊 Dashboard", "📝 Cadastrar Venda", "✅ Baixa de Pagamentos"])
    else:
        menu = st.sidebar.radio("Navegação", ["💰 Minhas Comissões", "📝 Cadastrar Venda"])

    if st.sidebar.button("Sair"):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- 3. CARREGAMENTO DE DADOS (GLOBAL) ---
    try:
        df_vendas = pd.read_csv(get_google_sheet(URL_BASE, GID_VENDAS))
        # Força os nomes das colunas para garantir segurança
        df_vendas.columns = ['Timestamp', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissao', 'Status']
        df_vendas['Valor_Num'] = df_vendas['Valor'].apply(limpar_financeiro)
        df_vendas['Com_Num'] = df_vendas['Comissao'].apply(limpar_financeiro)
    except:
        df_vendas = pd.DataFrame()

    # --- 4. TELA: DASHBOARD (DIRETORIA) ---
    if menu == "📊 Dashboard":
        st.title("Painel de Controle Estratégico")
        st.divider()
        
        if not df_vendas.empty:
            # Filtros no Topo
            with st.expander("🔍 Filtros de Busca"):
                c1, c2, c3 = st.columns(3)
                vendedores = df_vendas['Vendedor'].unique().tolist()
                f_vendedor = c1.multiselect("Vendedor", vendedores)
                f_status = c2.multiselect("Status do Pagamento", ["Pendente", "Pago"])
                f_cliente = c3.text_input("Nome do Cliente")

            # Aplicação dos Filtros
            df_f = df_vendas.copy()
            if f_vendedor: df_f = df_f[df_f['Vendedor'].isin(f_vendedor)]
            if f_status: df_f = df_f[df_f['Status'].isin(f_status)]
            if f_cliente: df_f = df_f[df_f['Cliente'].str.contains(f_cliente, case=False)]

            # Métricas em Cards
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Faturamento Total", f"R$ {df_f['Valor_Num'].sum():,.2f}")
            m2.metric("Recebido (Pago)", f"R$ {df_f[df_f['Status']=='Pago']['Valor_Num'].sum():,.2f}", delta_color="normal")
            m3.metric("Comissões Totais", f"R$ {df_f['Com_Num'].sum():,.2f}")
            m4.metric("Contratos", len(df_f['Cliente'].unique()))

            st.subheader("Lista Detalhada de Recebíveis")
            st.dataframe(df_f.drop(columns=['Valor_Num', 'Com_Num', 'Timestamp']), use_container_width=True)
        else:
            st.info("Nenhuma venda encontrada na base de dados.")

    # --- 5. TELA: CADASTRAR VENDA ---
    elif menu == "📝 Cadastrar Venda":
        st.title("Novo Contrato de Venda")
        with st.form("form_venda", clear_on_submit=True):
            col1, col2 = st.columns(2)
            cliente = col1.text_input("Nome do Cliente")
            v_total = col1.number_input("Valor Total do Contrato (R$)", min_value=0.0, step=100.0)
            v_entrada = col2.number_input("Valor da Entrada (R$)", min_value=0.0, step=100.0)
            n_parc = col1.number_input("Número de Parcelas (0 = À Vista)", min_value=0, step=1)
            data_v = col2.date_input("Data da Venda", value=date.today(), format="DD/MM/YYYY")
            
            if st.form_submit_button("🚀 Enviar para Planilha"):
                if cliente and v_total > 0:
                    lista_itens = []
                    if n_parc == 0:
                        lista_itens.append({"tipo": "À Vista", "valor": v_total, "mes": 0})
                    else:
                        if v_entrada > 0:
                            lista_itens.append({"tipo": "Entrada", "valor": v_entrada, "mes": 0})
                        v_parcela = (v_total - v_entrada) / n_parc
                        for i in range(1, int(n_parc) + 1):
                            lista_itens.append({"tipo": f"Parcela {i}/{int(n_parc)}", "valor": v_parcela, "mes": i})

                    sucesso = True
                    for item in lista_itens:
                        dt_venc = data_v + relativedelta(months=item['mes'])
                        payload = {
                            "entry.1532857351": cliente,
                            "entry.1279554151": user['nome'],
                            "entry.1633578859": item['tipo'],
                            "entry.366765493": dt_venc.strftime('%d/%m/%Y'),
                            "entry.1610537227": str(round(item['valor'], 2)).replace('.', ','),
                            "entry.1726017566": str(round(item['valor'] * 0.05, 2)).replace('.', ','),
                            "entry.622689505": "Pendente"
                        }
                        try: requests.post(FORM_URL, data=payload)
                        except: sucesso = False

                    if sucesso:
                        st.success(f"Venda de {cliente} registrada!")
                        st.balloons()
                    else: st.error("Erro técnico no envio.")
                else: st.warning("Preencha os campos obrigatórios.")

    # --- 6. TELA: GESTÃO DE STATUS (ADMIN) ---
    elif menu == "✅ Baixa de Pagamentos":
        st.title("Controle Financeiro: Baixa de Status")
        st.warning("⚠️ O Google Sheets não permite que o Streamlit altere células diretamente sem uma configuração complexa (Apps Script).")
        st.markdown(f"""
        Para manter a segurança e simplicidade:
        1. [Clique aqui para abrir sua Planilha]({URL_BASE})
        2. Vá na aba de Vendas (GID: {GID_VENDAS}).
        3. Altere a coluna **Status** de 'Pendente' para **'Pago'** assim que confirmar o dinheiro na conta.
        4. O Dashboard do App atualizará automaticamente em segundos.
        """)

    # --- 7. TELA: VENDEDOR ---
    elif menu == "💰 Minhas Comissões":
        st.title(f"Extrato Comercial: {user['nome']}")
        if not df_vendas.empty:
            meu_df = df_vendas[df_vendas['Vendedor'] == user['nome']].copy()
            
            c1, c2, c3 = st.columns(3)
            pago = meu_df[meu_df['Status'] == 'Pago']['Com_Num'].sum()
            pendente = meu_df[meu_df['Status'] == 'Pendente']['Com_Num'].sum()
            
            c1.metric("Comissão Recebida", f"R$ {pago:,.2f}")
            c2.metric("Comissão Pendente", f"R$ {pendente:,.2f}")
            c3.metric("Total Geral", f"R$ {pago + pendente:,.2f}")

            st.subheader("Meus Lançamentos")
            st.dataframe(meu_df.drop(columns=['Valor_Num', 'Com_Num', 'Vendedor', 'Timestamp']), use_container_width=True)
        else:
            st.info("Nenhuma venda registrada no seu nome.")