import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="ERP TURBO 4.6", layout="wide", page_icon="🚀")

# --- URLs ---
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSc7YHdYRJZ4I92_cvu0xvHvpU9adHmHmY0RKFxm88NcpjppyA/formResponse"
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?output=csv"
URL_USUARIOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?gid=1188945197&single=true&output=csv"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyur81SkxrO0U4q-Qx_BnMqrm0N3ihp-wt7YNEYkOksjjfCNQwx8TDWbbHmPQHNsO5GDg/exec"

IDs = {
    "cliente": "354575898", "vendedor": "1508368855", "tipo": "2051931448",
    "vencimento": "440689882", "valor_parc": "1010209945", "comissao": "1053130357",
    "status": "852082294", "valor_total": "1567666645", "data_base": "1443725489"
}

# --- FUNÇÕES DE DADOS COM CONTROLE DE CACHE ---
def carregar_dados(url):
    try:
        df = pd.read_csv(f"{url}&t={int(time.time())}")
        # Se houver uma lista de "excluídos recentemente" na sessão, filtramos aqui
        if 'excluidos' in st.session_state:
            for ex in st.session_state.excluidos:
                df = df[~((df.iloc[:, 1] == ex['cli']) & (df.iloc[:, 9] == ex['data']))]
        return df
    except: return pd.DataFrame()

# Inicia lista de excluídos para evitar "fantasmas"
if 'excluidos' not in st.session_state: st.session_state.excluidos = []

# --- LOGIN (Simplificado para o exemplo) ---
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
menu = st.sidebar.radio("Navegação", ["📝 Lançar & Gerir", "📊 Relatório"])

if menu == "📝 Lançar & Gerir":
    st.subheader("📝 Registro de Contrato")
    with st.form("venda_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        f_cli = c1.text_input("Nome do Cliente")
        f_data = c2.date_input("Data do Contrato", value=datetime.now(), format="DD/MM/YYYY")
        vendedor_final = st.selectbox("Vendedor", df_vendedores['nome'].tolist()) if u['cargo'] == "Admin" else u['nome']
        f_total = c1.number_input("Valor Total (R$)", min_value=0.0)
        f_entrada = c2.number_input("Entrada (R$)", min_value=0.0)
        f_parc = st.number_input("Parcelas", min_value=0, step=1)
        
        if st.form_submit_button("🚀 GRAVAR"):
            def enviar(tipo, valor, venc):
                payload = {
                    f"entry.{IDs['cliente']}": str(f_cli), f"entry.{IDs['vendedor']}": str(vendedor_final),
                    f"entry.{IDs['tipo']}": str(tipo), f"entry.{IDs['vencimento']}": venc.strftime('%Y-%m-%d'),
                    f"entry.{IDs['valor_parc']}": str(round(valor, 2)).replace('.', ','),
                    f"entry.{IDs['comissao']}": str(round(valor * 0.05, 2)).replace('.', ','),
                    f"entry.{IDs['status']}": "Pendente", f"entry.{IDs['valor_total']}": str(round(f_total, 2)).replace('.', ','),
                    f"entry.{IDs['data_base']}": f_data.strftime('%Y-%m-%d')
                }
                return requests.post(FORM_URL, data=payload).status_code
            
            res = []
            if f_parc == 0: res.append(enviar("À Vista", f_total, f_data))
            else:
                if f_entrada > 0: res.append(enviar("Entrada", f_entrada, f_data))
                v_p = (f_total - f_entrada) / f_parc
                for i in range(int(f_parc)):
                    res.append(enviar(f"Parc {i+1}/{int(f_parc)}", v_p, f_data + relativedelta(months=i+1)))
            if all(s == 200 for s in res):
                st.success("Gravado!"); time.sleep(1); st.rerun()

    if u['cargo'] == "Admin":
        st.divider()
        st.subheader("🗑️ Excluir Contrato Inteiro (Instantâneo)")
        df_ex = carregar_dados(CSV_URL)
        if not df_ex.empty:
            df_ex.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissão', 'Status', 'Total', 'Data_Base']
            contratos = df_ex.groupby(['Cliente', 'Data_Base', 'Total']).size().reset_index()
            opcoes = [f"{r['Cliente']} | {r['Data_Base']} | R$ {r['Total']}" for i, r in contratos.iterrows()]
            
            selecionado = st.selectbox("Selecione para remover todas as parcelas:", ["Selecione..."] + opcoes)
            
            if selecionado != "Selecione..." and st.button("🗑️ APAGAR AGORA", type="primary"):
                c_cli, c_data, c_total = selecionado.split(" | ")
                
                # 1. Comando ÚNICO para o Google (Rápido)
                with st.spinner("Limpando base..."):
                    requests.get(f"{SCRIPT_URL}?cli={c_cli}&dataBase={c_data}&action=deleteContrato")
                
                # 2. Filtro Local Imediato (Evita Fantasmas)
                st.session_state.excluidos.append({'cli': c_cli, 'data': c_data})
                
                st.error(f"Contrato de {c_cli} removido!")
                time.sleep(1); st.rerun()

elif menu == "📊 Relatório":
    st.subheader("📊 Relatório Comercial")
    df = carregar_dados(CSV_URL)
    if not df.empty:
        df.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissão', 'Status', 'Total', 'Data_Base']
        if u['cargo'] != "Admin": df = df[df['Vendedor'] == u['nome']]
        df['Vencimento'] = pd.to_datetime(df['Vencimento']).dt.strftime('%d/%m/%Y')
        df['Data_Base'] = pd.to_datetime(df['Data_Base']).dt.strftime('%d/%m/%Y')
        st.dataframe(df.sort_values('TS', ascending=False), use_container_width=True)