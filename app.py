import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- CONFIGURAÇÕES MESTRAS (ARTHUR VALENTE) ---
st.set_page_config(page_title="ERP COMERCIAL PRO 3.7", layout="centered", page_icon="🚀")

# LINKS DE CONEXÃO
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSc7YHdYRJZ4I92_cvu0xvHvpU9adHmHmY0RKFxm88NcpjppyA/formResponse"
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?output=csv"
URL_USUARIOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?gid=1188945197&single=true&output=csv"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyur81SkxrO0U4q-Qx_BnMqrm0N3ihp-wt7YNEYkOksjjfCNQwx8TDWbbHmPQHNsO5GDg/exec"

# IDs DOS CAMPOS (VERIFICADOS)
IDs = {
    "cliente": "354575898", "vendedor": "1508368855", "tipo": "2051931448",
    "vencimento": "440689882", "valor_parc": "1010209945", "comissao": "1053130357",
    "status": "852082294", "valor_total": "1567666645", "data_base": "1443725489"
}

def carregar_dados(url):
    try:
        return pd.read_csv(f"{url}&t={int(time.time())}")
    except:
        return pd.DataFrame()

# --- LOGIN ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🔐 Login")
    df_u = carregar_dados(URL_USUARIOS)
    with st.form("login"):
        user_email = st.text_input("E-mail")
        user_pass = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            if not df_u.empty:
                match = df_u[(df_u['email'].str.lower() == user_email.lower().strip()) & (df_u['senha'].astype(str) == str(user_pass))]
                if not match.empty:
                    st.session_state.logado = True
                    st.session_state.info = match.iloc[0].to_dict()
                    st.rerun()
                else: st.error("Erro de credenciais.")
    st.stop()

# --- INTERFACE ---
u = st.session_state.info
df_usuarios = carregar_dados(URL_USUARIOS) # Carrega para a lista de vendedores

st.sidebar.title(f"🚀 {u['cargo']}")
menu = st.sidebar.radio("Menu", ["📝 Lançar Venda", "📊 Relatórios", "✅ Baixas"])

# 1. LANÇAMENTO
if menu == "📝 Lançar Venda":
    st.subheader("📝 Novo Registro")
    with st.form("venda_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        f_cli = c1.text_input("Cliente")
        f_data = c2.date_input("Data Contrato", value=datetime.now())
        
        # Lógica Arthur Valente: Se for Admin, escolhe. Se for Usuario, trava no dele.
        if u['cargo'] == "Admin" and not df_usuarios.empty:
            vendedor_final = st.selectbox("Escolha o Vendedor", df_usuarios['nome'].tolist())
        else:
            vendedor_final = u['nome']
            st.info(f"Vendedor: {vendedor_final}")

        f_total = c1.number_input("Valor Total (R$)", min_value=0.0)
        f_entrada = c2.number_input("Entrada (R$)", min_value=0.0)
        f_parc = st.number_input("Parcelas (0=À Vista)", min_value=0, step=1)
        
        if st.form_submit_button("🚀 EXECUTAR GRAVAÇÃO"):
            if not f_cli or f_total <= 0:
                st.error("Dados incompletos!")
            else:
                # Função interna de envio com tratamento de erro
                def enviar_dados(t, v, dt):
                    payload = {
                        f"entry.{IDs['cliente']}": f_cli,
                        f"entry.{IDs['vendedor']}": vendedor_final,
                        f"entry.{IDs['tipo']}": t,
                        f"entry.{IDs['vencimento']}": dt.strftime('%Y-%m-%d'),
                        f"entry.{IDs['valor_parc']}": str(round(v, 2)).replace('.', ','),
                        f"entry.{IDs['comissao']}": str(round(v * 0.05, 2)).replace('.', ','),
                        f"entry.{IDs['status']}": "Pendente",
                        f"entry.{IDs['valor_total']}": str(round(f_total, 2)).replace('.', ','),
                        f"entry.{IDs['data_base']}": f_data.strftime('%d/%m/%Y')
                    }
                    try:
                        r = requests.post(FORM_URL, data=payload, timeout=10)
                        return r.status_code == 200
                    except:
                        return False

                # Execução da Lógica de Parcelamento
                sucesso = False
                if f_parc == 0:
                    sucesso = enviar_dados("À Vista", f_total, f_data)
                else:
                    if f_entrada > 0: enviar_dados("Entrada", f_entrada, f_data)
                    v_p = (f_total - f_entrada) / f_parc
                    for i in range(int(f_parc)):
                        dv = f_data + relativedelta(months=i+1 if f_entrada > 0 else i)
                        sucesso = enviar_dados(f"Parc {i+1}/{int(f_parc)}", v_p, dv)
                
                if sucesso:
                    st.success("✅ Gravado com sucesso na Planilha!")
                    time.sleep(1); st.rerun()
                else:
                    st.error("❌ Falha crítica na gravação. Verifique a internet ou o link do Form.")

# (Restante do código de Relatórios e Baixas mantido igual para estabilidade)
elif menu == "📊 Relatórios":
    df = carregar_dados(CSV_URL)
    if not df.empty:
        df.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissão', 'Status', 'Total', 'Data_Base']
        if u['cargo'] != "Admin": df = df[df['Vendedor'] == u['nome']]
        st.dataframe(df)

elif menu == "✅ Baixas":
    if u['cargo'] != "Admin": st.error("Acesso negado.")
    else:
        df = carregar_dados(CSV_URL)
        if not df.empty:
            df.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissão', 'Status', 'Total', 'Data_Base']
            pendentes = df[df['Status'].astype(str).str.contains("Pendente", case=False, na=False)]
            for i, r in pendentes.iterrows():
                if st.button(f"Baixar {r['Cliente']} - {r['Tipo']}", key=i):
                    requests.get(f"{SCRIPT_URL}?row={i+2}&status=Pago")
                    st.rerun()