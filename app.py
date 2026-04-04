import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- CONFIGURAÇÕES MESTRAS ---
st.set_page_config(page_title="ERP COMERCIAL PRO 4.2", layout="centered", page_icon="🚀")

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSc7YHdYRJZ4I92_cvu0xvHvpU9adHmHmY0RKFxm88NcpjppyA/formResponse"
CSV_URL = "https://docs.google.com/spreadsheets/d/e/PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?output=csv"
URL_USUARIOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?gid=1188945197&single=true&output=csv"

IDs = {
    "cliente": "354575898", "vendedor": "1508368855", "tipo": "2051931448",
    "vencimento": "440689882", "valor_parc": "1010209945", "comissao": "1053130357",
    "status": "852082294", "valor_total": "1567666645", "data_base": "1443725489"
}

def carregar_dados(url):
    try: return pd.read_csv(f"{url}&t={int(time.time())}")
    except: return pd.DataFrame()

# --- LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    st.title("🔐 Acesso Restrito")
    df_u = carregar_dados(URL_USUARIOS)
    with st.form("login"):
        user_email = st.text_input("E-mail")
        user_pass = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            if not df_u.empty:
                match = df_u[(df_u['email'].astype(str).str.lower() == user_email.lower().strip()) & (df_u['senha'].astype(str) == str(user_pass))]
                if not match.empty:
                    st.session_state.logado = True
                    st.session_state.info = match.iloc[0].to_dict()
                    st.rerun()
    st.stop()

# --- SISTEMA ---
u = st.session_state.info
df_vendedores = carregar_dados(URL_USUARIOS)
menu = st.sidebar.radio("Navegação", ["📝 Lançar Venda", "📊 Relatório Comercial"])

if menu == "📝 Lançar Venda":
    st.subheader("📝 Registro de Novo Contrato")
    with st.form("venda_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        f_cli = c1.text_input("Nome do Cliente")
        f_data = c2.date_input("Data do Contrato", value=datetime.now())
        
        vendedor_final = st.selectbox("Vendedor", df_vendedores['nome'].tolist()) if u['cargo'] == "Admin" else u['nome']
        
        f_total = c1.number_input("Valor Total (R$)", min_value=0.0, format="%.2f")
        f_entrada = c2.number_input("Entrada (R$)", min_value=0.0, format="%.2f")
        f_parc = st.number_input("Número de Parcelas (após entrada)", min_value=0, step=1)
        
        if st.form_submit_button("🚀 PROCESSAR E GRAVAR"):
            def enviar(tipo, valor, venc):
                payload = {
                    f"entry.{IDs['cliente']}": str(f_cli),
                    f"entry.{IDs['vendedor']}": str(vendedor_final),
                    f"entry.{IDs['tipo']}": str(tipo),
                    f"entry.{IDs['vencimento']}": venc.strftime('%Y-%m-%d'),
                    f"entry.{IDs['valor_parc']}": str(round(valor, 2)).replace('.', ','),
                    f"entry.{IDs['comissao']}": str(round(valor * 0.05, 2)).replace('.', ','),
                    f"entry.{IDs['status']}": "Pendente",
                    f"entry.{IDs['valor_total']}": str(round(f_total, 2)).replace('.', ','),
                    f"entry.{IDs['data_base']}": f_data.strftime('%Y-%m-%d')
                }
                return requests.post(FORM_URL, data=payload).status_code

            resul = []
            # Caso 1: Venda À Vista
            if f_parc == 0:
                resul.append(enviar("À Vista", f_total, f_data))
            # Caso 2: Venda Parcelada
            else:
                if f_entrada > 0:
                    resul.append(enviar("Entrada", f_entrada, f_data))
                
                valor_cada = (f_total - f_entrada) / f_parc
                for i in range(int(f_parc)):
                    # A primeira parcela vence 30 dias após a data base
                    data_venc = f_data + relativedelta(months=i+1)
                    resul.append(enviar(f"Parc {i+1}/{int(f_parc)}", valor_cada, data_venc))
            
            if all(s == 200 for s in resul):
                st.success("✅ Venda e parcelas registradas com sucesso!")
                time.sleep(1); st.rerun()
            else:
                st.error(f"❌ Falha parcial na sincronização. Status: {resul}")

elif menu == "📊 Relatório Comercial":
    st.subheader("📊 Histórico de Lançamentos")
    df = carregar_dados(CSV_URL)
    if not df.empty:
        # Renomeação dinâmica para garantir visualização limpa
        try:
            df.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissão', 'Status', 'Total', 'Data_Base']
            if u['cargo'] != "Admin": df = df[df['Vendedor'] == u['nome']]
            st.dataframe(df.sort_values('TS', ascending=False), use_container_width=True)
        except:
            st.dataframe(df)