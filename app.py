import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="ERP 5.1 DNA", layout="wide", page_icon="🚀")

SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyJiJlQIZeqvt3P09trAdfMecjutOFGVE1jsxPmcdh05nn2cKapdzVnJp8ASmIxCYfLQQ/exec"
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?output=csv"
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSc7YHdYRJZ4I92_cvu0xvHvpU9adHmHmY0RKFxm88NcpjppyA/formResponse"
URL_USUARIOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?gid=1188945197&single=true&output=csv"

IDs = {"cliente": "354575898", "vendedor": "1508368855", "tipo": "2051931448", "vencimento": "440689882", "valor_parc": "1010209945", "comissao": "1053130357", "status": "852082294", "valor_total": "1567666645", "data_base": "1443725489"}

if 'excluidos_sessao' not in st.session_state: st.session_state.excluidos_sessao = []

def carregar_dados():
    try:
        df = pd.read_csv(f"{CSV_URL}&cache={int(time.time())}")
        df.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissão', 'Status', 'Total', 'Data_Base']
        if st.session_state.excluidos_sessao:
            for ts in st.session_state.excluidos_sessao:
                df = df[df['TS'] != ts]
        return df
    except: return pd.DataFrame()

# --- LOGIN (Simplificado) ---
if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.title("🔐 Login")
    df_u = pd.read_csv(URL_USUARIOS)
    with st.form("login"):
        u_e = st.text_input("Email"); u_s = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            match = df_u[(df_u['email'] == u_e) & (df_u['senha'].astype(str) == u_s)]
            if not match.empty:
                st.session_state.logado = True; st.session_state.info = match.iloc[0].to_dict(); st.rerun()
    st.stop()

u = st.session_state.info
menu = st.sidebar.radio("Navegação", ["📝 Lançar & Gerir", "📊 Relatório"])

if menu == "📝 Lançar & Gerir":
    st.subheader("📝 Novo Contrato")
    with st.form("venda"):
        c1, c2 = st.columns(2)
        f_cli = c1.text_input("Cliente")
        f_data = c2.date_input("Data Base", format="DD/MM/YYYY")
        f_total = c1.number_input("Valor Total", min_value=0.0)
        f_parc = st.number_input("Parcelas", min_value=0, step=1)
        if st.form_submit_button("🚀 GRAVAR"):
            def enviar(tipo, valor, venc):
                p = {f"entry.{IDs['cliente']}": f_cli, f"entry.{IDs['vendedor']}": u['nome'], f"entry.{IDs['tipo']}": tipo, f"entry.{IDs['vencimento']}": venc.strftime('%Y-%m-%d'), f"entry.{IDs['valor_parc']}": str(round(valor, 2)).replace('.',','), f"entry.{IDs['status']}": "Pendente", f"entry.{IDs['valor_total']}": str(f_total).replace('.',','), f"entry.{IDs['data_base']}": f_data.strftime('%Y-%m-%d')}
                return requests.post(FORM_URL, data=p).status_code
            
            # Grava as parcelas (todas terão o mesmo TS no Google Forms pois são enviadas no mesmo bloco)
            if f_parc == 0: enviar("À Vista", f_total, f_data)
            else:
                v_p = f_total / f_parc
                for i in range(int(f_parc)): enviar(f"Parc {i+1}", v_p, f_data + relativedelta(months=i+1))
            st.success("Contrato Gravado!"); time.sleep(2); st.rerun()

    if u['cargo'] == "Admin":
        st.divider()
        st.subheader("🗑️ Excluir Contrato Específico")
        df_ex = carregar_dados()
        if not df_ex.empty:
            # Agrupamos pelo TS (Timestamp) para garantir que cada contrato seja único
            contratos = df_ex.groupby(['TS', 'Cliente', 'Total']).size().reset_index()
            # Mostramos a data/hora do lançamento para o Admin saber qual é qual
            opcoes = {f"{r['TS']} | {r['Cliente']} | R$ {r['Total']}": r['TS'] for i, r in contratos.iterrows()}
            
            sel_label = st.selectbox("Selecione o lançamento exato para remover:", ["Selecione..."] + list(opcoes.keys()))
            
            if sel_label != "Selecione..." and st.button("🔥 APAGAR LANÇAMENTO", type="primary"):
                ts_alvo = opcoes[sel_label]
                with st.spinner("Removendo do banco..."):
                    r = requests.get(SCRIPT_URL, params={"ts": ts_alvo, "action": "deleteContrato"})
                
                st.session_state.excluidos_sessao.append(ts_alvo)
                st.info(f"Retorno: {r.text}")
                time.sleep(2); st.rerun()

elif menu == "📊 Relatório":
    df = carregar_dados()
    if not df.empty:
        if u['cargo'] != "Admin": df = df[df['Vendedor'] == u['nome']]
        st.dataframe(df.sort_values('TS', ascending=False), use_container_width=True)