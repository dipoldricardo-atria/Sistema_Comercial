import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="ERP COMERCIAL 4.8.2", layout="wide", page_icon="🚀")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyJiJlQIZeqvt3P09trAdfMecjutOFGVE1jsxPmcdh05nn2cKapdzVnJp8ASmIxCYfLQQ/exec"
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?output=csv"
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSc7YHdYRJZ4I92_cvu0xvHvpU9adHmHmY0RKFxm88NcpjppyA/formResponse"
URL_USUARIOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?gid=1188945197&single=true&output=csv"

IDs = {"cliente": "354575898", "vendedor": "1508368855", "tipo": "2051931448", "vencimento": "440689882", "valor_parc": "1010209945", "comissao": "1053130357", "status": "852082294", "valor_total": "1567666645", "data_base": "1443725489"}

if 'excluidos_sessao' not in st.session_state: st.session_state.excluidos_sessao = []

def carregar_dados():
    t = int(time.time())
    try:
        df = pd.read_csv(f"{CSV_URL}&cache={t}")
        df.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissão', 'Status', 'Total', 'Data_Base']
        if st.session_state.excluidos_sessao:
            for ex in st.session_state.excluidos_sessao:
                df = df[~((df['Cliente'] == ex['cli']) & (df['Data_Base'] == ex['data']))]
        return df
    except: return pd.DataFrame()

# --- LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.title("🔐 Login Administrativo")
    df_u = pd.read_csv(URL_USUARIOS)
    with st.form("login"):
        u_e = st.text_input("E-mail"); u_s = st.text_input("Senha", type="password")
        if st.form_submit_button("Acessar"):
            match = df_u[(df_u['email'].astype(str).str.lower() == u_e.lower().strip()) & (df_u['senha'].astype(str) == u_s)]
            if not match.empty:
                st.session_state.logado = True; st.session_state.info = match.iloc[0].to_dict(); st.rerun()
    st.stop()

u = st.session_state.info
menu = st.sidebar.radio("Navegação", ["📝 Lançar & Gerir", "📊 Relatório"])

if menu == "📝 Lançar & Gerir":
    st.subheader("📝 Registro de Venda")
    with st.form("venda", clear_on_submit=True):
        c1, c2 = st.columns(2)
        f_cli = c1.text_input("Cliente")
        f_data = c2.date_input("Data", format="DD/MM/YYYY")
        f_total = c1.number_input("Total", min_value=0.0)
        f_parc = st.number_input("Parcelas", min_value=0, step=1)
        if st.form_submit_button("🚀 GRAVAR"):
            def enviar(tipo, valor, venc):
                p = {f"entry.{IDs['cliente']}": f_cli, f"entry.{IDs['vendedor']}": u['nome'], f"entry.{IDs['tipo']}": tipo, f"entry.{IDs['vencimento']}": venc.strftime('%Y-%m-%d'), f"entry.{IDs['valor_parc']}": str(round(valor, 2)).replace('.',','), f"entry.{IDs['status']}": "Pendente", f"entry.{IDs['valor_total']}": str(f_total).replace('.',','), f"entry.{IDs['data_base']}": f_data.strftime('%Y-%m-%d')}
                return requests.post(FORM_URL, data=p).status_code
            res = []
            if f_parc == 0: res.append(enviar("À Vista", f_total, f_data))
            else:
                v_p = f_total / f_parc
                for i in range(int(f_parc)): res.append(enviar(f"Parc {i+1}", v_p, f_data + relativedelta(months=i+1)))
            st.success("✅ Gravado!"); time.sleep(1); st.rerun()

    if u['cargo'] == "Admin":
        st.divider()
        st.subheader("🗑️ Excluir Contrato")
        df_ex = carregar_dados()
        if not df_ex.empty:
            contratos = df_ex.groupby(['Cliente', 'Data_Base', 'Total']).size().reset_index()
            opcoes = [f"{r['Cliente']} | {r['Data_Base']} | R$ {r['Total']}" for i, r in contratos.iterrows()]
            sel = st.selectbox("Selecione o contrato:", ["Selecione..."] + opcoes)
            if sel != "Selecione..." and st.button("🔥 EXCLUIR CONTRATO", type="primary"):
                c_cli, c_data, c_total = sel.split(" | ")
                with st.spinner("Excluindo..."):
                    r = requests.get(SCRIPT_URL, params={"cli": c_cli, "dataBase": c_data, "action": "deleteContrato"})
                st.session_state.excluidos_sessao.append({'cli': c_cli, 'data': c_data})
                st.info(f"Retorno: {r.text}")
                time.sleep(2); st.rerun()

elif menu == "📊 Relatório":
    if st.button("🔄 Sincronizar"): st.session_state.excluidos_sessao = []; st.rerun()
    df = carregar_dados()
    if not df.empty:
        if u['cargo'] != "Admin": df = df[df['Vendedor'] == u['nome']]
        df['Vencimento'] = pd.to_datetime(df['Vencimento']).dt.strftime('%d/%m/%Y')
        df['Data_Base'] = pd.to_datetime(df['Data_Base']).dt.strftime('%d/%m/%Y')
        st.dataframe(df.sort_values('TS', ascending=False), use_container_width=True)