import streamlit as st
import pandas as pd
import requests
import time
import urllib.parse
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. CONFIGURAÇÕES CRÍTICAS ---
st.set_page_config(page_title="ERP COMERCIAL - RECUPERAÇÃO", layout="wide")

# IDs das colunas que você me passou
ID_VALOR_TOTAL = "1849135056"
ID_DATA_BASE = "925681697"

URL_BASE = "https://docs.google.com/spreadsheets/d/1TUMWuy_EjuMgzMUuT3PUVCP3P-FQA8yDN0Hv4RK46SY/edit?usp=sharing"
GID_VENDAS = "1045730969"
GID_USUARIOS = "1357723875"
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLScWLZzEh2KOp1aqdjKkhTelImUTL4EJ7KZRr-aryX3N-92aBg/formResponse"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwOR4tCPLwpmn28h4TqG-hz4HxM5APUhoZ00TgQ6SVz6rSs79r1rixjmw9K6CoRJFdI/exec"

def carregar_dados(gid):
    try:
        url = f"https://docs.google.com/spreadsheets/d/1TUMWuy_EjuMgzMUuT3PUVCP3P-FQA8yDN0Hv4RK46SY/export?format=csv&gid={gid}&cache={int(time.time())}"
        df = pd.read_csv(url)
        return df
    except Exception as e:
        st.error(f"Erro ao acessar aba {gid}: {e}")
        return pd.DataFrame()

def limpar_financeiro(val):
    try:
        if pd.isna(val): return 0.0
        if isinstance(val, str): return float(val.replace('.', '').replace(',', '.'))
        return float(val)
    except: return 0.0

# --- 2. LOGIN ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔑 Sistema Comercial - Reset")
    u = st.text_input("E-mail")
    s = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        df_u = carregar_dados(GID_USUARIOS)
        if not df_u.empty:
            user = df_u[(df_u['email'].str.lower() == u.lower().strip()) & (df_u['senha'].astype(str) == s)]
            if not user.empty:
                st.session_state.update({'logged_in': True, 'user': user.iloc[0].to_dict(), 'vendedores': df_u['nome'].tolist()})
                st.rerun()
            else: st.error("Dados incorretos.")
else:
    user = st.session_state['user']
    st.sidebar.success(f"Olá, {user['nome']}")
    menu = st.sidebar.radio("Menu", ["📝 Gestão de Vendas", "📊 Dashboard"])

    # --- 3. GESTÃO DE VENDAS (FOCO NO REGISTRO) ---
    if menu == "📝 Gestão de Vendas":
        st.title("📝 Novo Registro de Venda")
        with st.form("form_fênix", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            f_cli = c1.text_input("Cliente")
            f_vend = c2.selectbox("Vendedor", st.session_state['vendedores']) if user['perfil'] == 'Admin' else c2.text_input("Vendedor", user['nome'], disabled=True)
            f_data = c3.date_input("Data Base (Contrato)")
            
            f_total = c1.number_input("Valor Bruto", min_value=0.0)
            f_entrada = c2.number_input("Entrada", min_value=0.0)
            f_parc = c3.number_input("Parcelas (0 para Mensalidade)", min_value=0, value=1)
            
            if st.form_submit_button("🚀 GRAVAR NA PLANILHA"):
                if not f_cli or f_total <= 0:
                    st.warning("Preencha cliente e valor total!")
                else:
                    success_count = 0
                    
                    # 1. ENTRADA
                    if f_entrada > 0:
                        payload = {
                            "entry.1532857351": f_cli, "entry.1279554151": f_vend, "entry.1633578859": "Entrada",
                            "entry.366765493": f_data.strftime('%d/%m/%Y'), 
                            "entry.1610537227": str(round(f_entrada,2)).replace('.',','),
                            "entry.622689505": "Pendente",
                            f"entry.{ID_VALOR_TOTAL}": str(round(f_total,2)).replace('.',','),
                            f"entry.{ID_DATA_BASE}": f_data.strftime('%d/%m/%Y')
                        }
                        r = requests.post(FORM_URL, data=payload)
                        if r.status_code == 200: success_count += 1
                    
                    # 2. PARCELAS / RECORRÊNCIA
                    saldo = f_total - f_entrada
                    loops = 1 if f_parc == 0 else int(f_parc)
                    v_p = saldo / loops if f_parc > 0 else f_total
                    
                    for i in range(loops):
                        venc = (f_data + relativedelta(months=i+1 if f_entrada > 0 else i)).strftime('%d/%m/%Y')
                        tipo_p = f"Parc {i+1}/{int(f_parc)}" if f_parc > 0 else "Mensalidade (Recorrente)"
                        payload = {
                            "entry.1532857351": f_cli, "entry.1279554151": f_vend, "entry.1633578859": tipo_p,
                            "entry.366765493": venc, "entry.1610537227": str(round(v_p,2)).replace('.',','),
                            "entry.622689505": "Pendente",
                            f"entry.{ID_VALOR_TOTAL}": str(round(f_total,2)).replace('.',','),
                            f"entry.{ID_DATA_BASE}": f_data.strftime('%d/%m/%Y')
                        }
                        r = requests.post(FORM_URL, data=payload)
                        if r.status_code == 200: success_count += 1
                    
                    if success_count > 0:
                        st.success(f"Sucesso! {success_count} linhas enviadas para o Google.")
                        time.sleep(3)
                        st.rerun()
                    else:
                        st.error("Falha ao enviar para o Google. Verifique o FORM_URL.")

    # --- 4. DASHBOARD (FOCO NA LEITURA) ---
    elif menu == "📊 Dashboard":
        st.title("📊 Análise de Dados")
        df = carregar_dados(GID_VENDAS)
        
        if df.empty:
            st.warning("A planilha está vazia ou inacessível. Faça um lançamento primeiro.")
        else:
            # Forçar nomes de colunas
            try:
                df = df.iloc[:, :10]
                df.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor_Parc', 'Comissao', 'Status', 'Valor_Total', 'Data_Base']
                df['Val_T'] = df['Valor_Total'].apply(limpar_financeiro)
                
                # KPIs rápidos
                total_fat = df.drop_duplicates('TS')['Val_T'].sum()
                st.metric("Faturamento Acumulado (10 colunas)", f"R$ {total_fat:,.2f}")
                st.dataframe(df)
            except Exception as e:
                st.error(f"Erro ao processar colunas: {e}")
                st.write("Colunas encontradas:", list(df.columns))