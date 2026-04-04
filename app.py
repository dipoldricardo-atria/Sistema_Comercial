import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="ERP COMERCIAL PRO 4.1", layout="centered", page_icon="🚀")

# LINKS
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSc7YHdYRJZ4I92_cvu0xvHvpU9adHmHmY0RKFxm88NcpjppyA/formResponse"
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?output=csv"
URL_USUARIOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?gid=1188945197&single=true&output=csv"

# IDs REVISADOS
IDs = {
    "cliente": "354575898", "vendedor": "1508368855", "tipo": "2051931448",
    "vencimento": "440689882", "valor_parc": "1010209945", "comissao": "1053130357",
    "status": "852082294", "valor_total": "1567666645", "data_base": "1443725489"
}

def carregar_dados(url):
    try: return pd.read_csv(f"{url}&t={int(time.time())}")
    except: return pd.DataFrame()

if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    st.title("🔐 Login")
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

u = st.session_state.info
df_vendedores = carregar_dados(URL_USUARIOS)
menu = st.sidebar.radio("Navegação", ["📝 Lançar Venda", "📊 Relatórios"])

if menu == "📝 Lançar Venda":
    st.subheader("📝 Lançamento")
    with st.form("venda_form"):
        f_cli = st.text_input("Cliente")
        f_data = st.date_input("Data Contrato", value=datetime.now())
        vendedor_final = st.selectbox("Vendedor", df_vendedores['nome'].tolist()) if u['cargo'] == "Admin" else u['nome']
        f_total = st.number_input("Valor Total", min_value=0.0)
        f_parc = st.number_input("Parcelas (0=Vista)", min_value=0, step=1)
        
        if st.form_submit_button("🚀 GRAVAR"):
            def enviar(t, v, dt):
                # TESTE DE FORMATO: Usando strings simples sem formatação complexa
                payload = {
                    f"entry.{IDs['cliente']}": str(f_cli),
                    f"entry.{IDs['vendedor']}": str(vendedor_final),
                    f"entry.{IDs['tipo']}": str(t),
                    f"entry.{IDs['vencimento']}": dt.strftime('%Y-%m-%d'), # Formato padrão Google
                    f"entry.{IDs['valor_parc']}": str(round(v, 2)),
                    f"entry.{IDs['comissao']}": str(round(v * 0.05, 2)),
                    f"entry.{IDs['status']}": "Pendente",
                    f"entry.{IDs['valor_total']}": str(round(f_total, 2)),
                    f"entry.{IDs['data_base']}": f_data.strftime('%Y-%m-%d')
                }
                r = requests.post(FORM_URL, data=payload)
                if r.status_code != 200:
                    st.write(f"DEBUG: Falha no envio de {t}. Payload enviado:", payload)
                return r.status_code

            resul = []
            if f_parc == 0:
                resul.append(enviar("À Vista", f_total, f_data))
            else:
                v_p = f_total / f_parc
                for i in range(int(f_parc)):
                    dv = f_data + relativedelta(months=i)
                    resul.append(enviar(f"Parc {i+1}", v_p, dv))
            
            if all(s == 200 for s in resul):
                st.success("Gravado!")
                time.sleep(1); st.rerun()
            else:
                st.error(f"Erro {resul}. Veja o DEBUG acima para entender o campo rejeitado.")