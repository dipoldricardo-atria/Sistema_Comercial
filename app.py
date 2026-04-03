import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# --- 1. CONFIGURAÇÕES INICIAIS (MEMORIZADAS) ---
st.set_page_config(page_title="Gestão Comercial Tech", layout="wide")

# Seus links e GIDs fixos conforme solicitado
URL_BASE = "https://docs.google.com/spreadsheets/d/1TUMWuy_EjuMgzMUuT3PUVCP3P-FQA8yDN0Hv4RK46SY/edit?usp=sharing"
GID_USUARIOS = "1357723875" 
GID_VENDAS = "1045730969"   # ABA DE RESPOSTAS DO FORMULÁRIO

# URL de POST do seu Google Forms (Envio Silencioso)
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
                # Leitura da aba de usuários
                df_users = pd.read_csv(get_google_sheet(URL_BASE, GID_USUARIOS))
                df_users['email'] = df_users['email'].astype(str).str.strip().str.lower()
                
                # Validação
                user = df_users[(df_users['email'] == email_input) & (df_users['senha'].astype(str) == str(senha_input))]
                
                if not user.empty:
                    st.session_state['logged_in'] = True
                    st.session_state['user_info'] = user.iloc[0]
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
            except Exception as e:
                st.error(f"Erro ao acessar base de dados: {e}")
else:
    # --- 3. ÁREA LOGADA ---
    user = st.session_state['user_info']
    st.sidebar.success(f"Logado: {user['nome']}")
    
    if user['perfil'] == "Admin":
        menu = st.sidebar.radio("Navegação", ["Dashboard", "Cadastrar Venda"])
    else:
        menu = st.sidebar.radio("Navegação", ["Minhas Comissões"])

    if st.sidebar.button("Sair"):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- 4. TELA: DASHBOARD (DIRETORIA) ---
    if menu == "Dashboard":
        st.title("📊 Painel de Controle (Diretoria)")
        st.divider()
        try:
            df_vendas = pd.read_csv(get_google_sheet(URL_BASE, GID_VENDAS))
            if not df_vendas.empty:
                # O Google Forms cria a 1ª coluna como 'Carimbo de data/hora'
                # Os valores financeiros costumam vir como texto com vírgula (Ex: 1.000,50)
                # Vamos limpar os dados para garantir o cálculo das métricas
                def limpar_valor(val):
                    if isinstance(val, str):
                        return float(val.replace('.', '').replace(',', '.'))
                    return float(val)

                # Coluna 5 (Valor) e Coluna 6 (Comissão) baseadas na ordem do seu Forms
                df_vendas['valor_num'] = df_vendas.iloc[:, 5].apply(limpar_valor)
                df_vendas['com_num'] = df_vendas.iloc[:, 6].apply(limpar_valor)
                
                total_faturamento = df_vendas['valor_num'].sum()
                total_comissoes = df_vendas['com_num'].sum()
                
                c1, c2 = st.columns(2)
                c1.metric("Faturamento Total", f"R$ {total_faturamento:,.2f}")
                c2.metric("Comissões Totais", f"R$ {total_comissoes:,.2f}")
                
                st.subheader("Lista Geral de Recebíveis")
                st.dataframe(df_vendas, use_container_width=True)
            else:
                st.info("Aba de vendas vazia. Cadastre uma venda para ver os dados.")
        except Exception as e:
            st.error(f"Erro ao carregar Dashboard: {e}")

    # --- 5. TELA: CADASTRAR VENDA (AUTOMAÇÃO GOOGLE FORMS) ---
    elif menu == "Cadastrar Venda":
        st.title("📝 Gerar e Salvar Novo Contrato")
        with st.form("form_venda", clear_on_submit=True):
            col1, col2 = st.columns(2)
            cliente = col1.text_input("Nome do Cliente")
            v_total = col1.number_input("Valor Total do Contrato (R$)", min_value=0.0, step=100.0)
            v_entrada = col2.number_input("Valor da Entrada (R$)", min_value=0.0, step=100.0)
            n_parc = col1.number_input("Número de Parcelas Restantes", min_value=1, step=1)
            data_v = col2.date_input("Data do Fechamento/Entrada", date.today())
            
            if st.form_submit_button("🚀 Salvar na Nuvem"):
                if cliente != "" and v_total > 0:
                    valor_parcelado = (v_total - v_entrada) / n_parc
                    sucesso_geral = True
                    
                    # Envia a entrada e cada parcela individualmente para o Google
                    for i in range(int(n_parc) + 1):
                        tipo = "Entrada" if i == 0 else f"Parcela {i}/{int(n_parc)}"
                        valor_at = v_entrada if i == 0 else valor_parcelado
                        
                        # Pula a linha da entrada se o valor for R$ 0
                        if valor_at <= 0 and i == 0: continue 
                        
                        dt_at = data_v + relativedelta(months=i)
                        
                        # Mapeamento com os seus IDs específicos do Forms
                        payload = {
                            "entry.1532857351": cliente,
                            "entry.1279554151": user['nome'], # Nome do Admin/Vendedor logado
                            "entry.1633578859": tipo,
                            "entry.366765493": dt_at.strftime('%d/%m/%Y'),
                            "entry.1610537227": str(round(valor_at, 2)).replace('.', ','),
                            "entry.1726017566": str(round(valor_at * 0.05, 2)).replace('.', ','),
                            "entry.622689505": "Pendente"
                        }
                        
                        try:
                            r = requests.post(FORM_URL, data=payload)
                            if r.status_code != 200:
                                sucesso_geral = False
                        except:
                            sucesso_geral = False

                    if sucesso_geral:
                        st.success(f"✅ Venda de {cliente} registrada com sucesso na planilha!")
                        st.balloons()
                    else:
                        st.error("Erro ao enviar dados. Verifique se o formulário Google está aberto ao público.")
                else:
                    st.warning("Preencha o nome do cliente e o valor total.")

    # --- 6. TELA: VENDEDOR ---
    elif menu == "Minhas Comissões":
        st.title(f"💰 Extrato: {user['nome']}")
        try:
            df_vendas = pd.read_csv(get_google_sheet(URL_BASE, GID_VENDAS))
            # Filtra apenas as vendas do vendedor logado
            meu_df = df_vendas[df_vendas.iloc[:, 2] == user['nome']]
            st.dataframe(meu_df, use_container_width=True)
        except:
            st.error("Erro ao carregar seus dados.")