import streamlit as st
import pandas as pd
import requests
import time
import random
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="ERP COMERCIAL 7.5", layout="wide", page_icon="🛡️")

# --- CONFIGURAÇÕES FIXAS ---
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyJiJlQIZeqvt3P09trAdfMecjutOFGVE1jsxPmcdh05nn2cKapdzVnJp8ASmIxCYfLQQ/exec"
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSc7YHdYRJZ4I92_cvu0xvHvpU9adHmHmY0RKFxm88NcpjppyA/formResponse"
URL_USUARIOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?gid=1188945197&single=true&output=csv"

IDs = {
    "cliente": "354575898", "vendedor": "1508368855", "tipo": "2051931448",
    "vencimento": "440689882", "valor_parc": "1010209945", "comissao": "1053130357",
    "status": "852082294", "valor_total": "1567666645", "data_base": "1443725489",
    "id_contrato": "921030482" 
}

# --- GESTÃO DE SESSÃO (PARA NÃO LOGAR TODA HORA) ---
if 'logado' not in st.session_state: st.session_state.logado = False
if 'usuario' not in st.session_state: st.session_state.usuario = None

def carregar_dados_realtime():
    try:
        r = requests.get(f"{SCRIPT_URL}?action=read")
        lista = r.json()
        df = pd.DataFrame(lista[1:], columns=['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissão', 'Status', 'Total', 'Data_Base', 'ID_Contrato'])
        return df
    except: return pd.DataFrame()

# --- TELA DE LOGIN ---
if not st.session_state.logado:
    st.title("🔐 Login Administrativo")
    with st.form("login"):
        u_e = st.text_input("E-mail")
        u_s = st.text_input("Senha", type="password")
        if st.form_submit_button("Acessar"):
            df_u = pd.read_csv(URL_USUARIOS)
            match = df_u[(df_u['email'].str.lower() == u_e.lower().strip()) & (df_u['senha'].astype(str) == u_s)]
            if not match.empty:
                st.session_state.logado = True
                st.session_state.usuario = match.iloc[0].to_dict()
                st.rerun()
            else: st.error("Dados incorretos.")
    st.stop()

# --- SE CHEGOU AQUI, ESTÁ LOGADO ---
u = st.session_state.usuario
st.sidebar.write(f"👤 **{u['nome']}** ({u['cargo']})")
if st.sidebar.button("🚪 Sair do Sistema"):
    st.session_state.logado = False
    st.rerun()

menu = st.sidebar.radio("Menu", ["📝 Lançar & Gerir", "📊 Relatório"])

if menu == "📝 Lançar & Gerir":
    st.subheader("📝 Novo Lançamento")
    with st.form("venda", clear_on_submit=True):
        c1, c2 = st.columns(2)
        f_cli = c1.text_input("Cliente")
        f_data = c2.date_input("Data Base")
        f_total = c1.number_input("Valor Total", min_value=0.0)
        f_entrada = c2.number_input("Valor de Entrada", min_value=0.0)
        f_parc = st.number_input("Parcelas (sem contar entrada)", min_value=0, step=1)
        
        if st.form_submit_button("🚀 GRAVAR CONTRATO"):
            id_gera = f"ID{int(time.time())}"
            def enviar(tipo, valor, venc):
                p = {f"entry.{IDs['cliente']}": f_cli, f"entry.{IDs['vendedor']}": u['nome'], f"entry.{IDs['tipo']}": tipo, f"entry.{IDs['vencimento']}": venc.strftime('%Y-%m-%d'), f"entry.{IDs['valor_parc']}": str(round(valor, 2)).replace('.', ','), f"entry.{IDs['status']}": "Pendente", f"entry.{IDs['valor_total']}": str(f_total).replace('.', ','), f"entry.{IDs['data_base']}": f_data.strftime('%Y-%m-%d'), f"entry.{IDs['id_contrato']}": id_gera}
                requests.post(FORM_URL, data=p)

            if f_entrada > 0: enviar("Entrada", f_entrada, f_data)
            restante = f_total - f_entrada
            if f_parc > 0 and restante > 0:
                v_p = restante / f_parc
                for i in range(int(f_parc)): enviar(f"Parc {i+1}", v_p, f_data + relativedelta(months=i+1))
            elif f_parc == 0 and f_entrada == 0: enviar("À Vista", f_total, f_data)
            st.success(f"Gravado com ID: {id_gera}")
            time.sleep(1); st.rerun()

    if u['cargo'] == "Admin":
        st.divider()
        st.subheader("🗑️ Área de Exclusão (Admin)")
        df_ex = carregar_dados_realtime()
        if not df_ex.empty:
            contratos = df_ex[df_ex['ID_Contrato'].astype(str).str.startswith("ID")].groupby(['ID_Contrato', 'Cliente', 'Total']).size().reset_index()
            opcoes = [f"{r['ID_Contrato']} | {r['Cliente']} | R$ {r['Total']}" for i, r in contratos.iterrows()]
            sel = st.selectbox("Escolha o contrato para apagar:", ["Selecione..."] + opcoes)
            if sel != "Selecione..." and st.button("🔥 APAGAR AGORA", type="primary"):
                id_alvo = sel.split(" | ")[0]
                requests.get(SCRIPT_URL, params={"id_contrato": id_alvo, "action": "deleteContrato"})
                st.warning("Apagado com sucesso!")
                time.sleep(1); st.rerun()

elif menu == "📊 Relatório":
    st.subheader("📊 Histórico em Tempo Real")
    df = carregar_dados_realtime()
    if not df.empty:
        if u['cargo'] != "Admin": df = df[df['Vendedor'] == u['nome']]
        st.dataframe(df.sort_values('TS', ascending=False), use_container_width=True)