import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="ERP COMERCIAL 5.2", layout="wide", page_icon="🚀")

# CONFIGURAÇÕES
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyJiJlQIZeqvt3P09trAdfMecjutOFGVE1jsxPmcdh05nn2cKapdzVnJp8ASmIxCYfLQQ/exec"
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?output=csv"
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSc7YHdYRJZ4I92_cvu0xvHvpU9adHmHmY0RKFxm88NcpjppyA/formResponse"
URL_USUARIOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?gid=1188945197&single=true&output=csv"

IDs = {"cliente": "354575898", "vendedor": "1508368855", "tipo": "2051931448", "vencimento": "440689882", "valor_parc": "1010209945", "comissao": "1053130357", "status": "852082294", "valor_total": "1567666645", "data_base": "1443725489"}

if 'removidos' not in st.session_state: st.session_state.removidos = []

def carregar_dados():
    try:
        df = pd.read_csv(f"{CSV_URL}&cache={int(time.time())}")
        df.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissão', 'Status', 'Total', 'Data_Base']
        # Filtra os contratos que acabamos de apagar (Filtro por minuto e cliente)
        for r in st.session_state.removidos:
            df = df[~((df['Cliente'] == r['cli']) & (df['TS'].str.contains(r['minuto'])))]
        return df
    except: return pd.DataFrame()

# --- LOGIN (Simplificado) ---
if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.title("🔐 Login")
    df_u = pd.read_csv(URL_USUARIOS)
    with st.form("login"):
        u_e = st.text_input("E-mail"); u_s = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            match = df_u[(df_u['email'] == u_e) & (df_u['senha'].astype(str) == u_s)]
            if not match.empty:
                st.session_state.logado = True; st.session_state.info = match.iloc[0].to_dict(); st.rerun()
    st.stop()

u = st.session_state.info
menu = st.sidebar.radio("Navegação", ["📝 Lançar & Gerir", "📊 Relatório"])

if menu == "📝 Lançar & Gerir":
    st.subheader("📝 Lançar Venda")
    with st.form("venda", clear_on_submit=True):
        c1, c2 = st.columns(2)
        f_cli = c1.text_input("Cliente")
        f_data = c2.date_input("Data Base", format="DD/MM/YYYY")
        f_total = c1.number_input("Valor Total", min_value=0.0)
        f_parc = st.number_input("Parcelas", min_value=0, step=1)
        if st.form_submit_button("🚀 GRAVAR"):
            def enviar(tipo, valor, venc):
                p = {f"entry.{IDs['cliente']}": f_cli, f"entry.{IDs['vendedor']}": u['nome'], f"entry.{IDs['tipo']}": tipo, f"entry.{IDs['vencimento']}": venc.strftime('%Y-%m-%d'), f"entry.{IDs['valor_parc']}": str(round(valor, 2)).replace('.',','), f"entry.{IDs['status']}": "Pendente", f"entry.{IDs['valor_total']}": str(f_total).replace('.',','), f"entry.{IDs['data_base']}": f_data.strftime('%Y-%m-%d')}
                return requests.post(FORM_URL, data=p).status_code
            if f_parc == 0: enviar("À Vista", f_total, f_data)
            else:
                v_p = f_total / f_parc
                for i in range(int(f_parc)): enviar(f"Parc {i+1}", v_p, f_data + relativedelta(months=i+1))
            st.success("Contrato Gravado!"); time.sleep(1); st.rerun()

    if u['cargo'] == "Admin":
        st.divider()
        st.subheader("🗑️ Área de Exclusão")
        df_ex = carregar_dados()
        if not df_ex.empty:
            # Agrupar para mostrar apenas UM registro por contrato (baseado no minuto e cliente)
            df_ex['Minuto'] = df_ex['TS'].str.substring(0, 16) if hasattr(df_ex['TS'], 'str') else df_ex['TS']
            contratos = df_ex.groupby(['Minuto', 'Cliente', 'Total']).size().reset_index()
            
            opcoes = [f"{r['Minuto']} | {r['Cliente']} | R$ {r['Total']}" for i, r in contratos.iterrows()]
            sel = st.selectbox("Selecione o contrato para remover INTEIRO:", ["Selecione..."] + opcoes)
            
            if sel != "Selecione..." and st.button("🔥 APAGAR TUDO DESTE LANÇAMENTO", type="primary"):
                minuto, cliente, total = sel.split(" | ")
                with st.spinner("Excluindo parcelas..."):
                    # Mandamos o TS completo para o Script tratar
                    r = requests.get(SCRIPT_URL, params={"cli": cliente, "ts": minuto, "action": "deleteContrato"})
                
                st.session_state.removidos.append({'cli': cliente, 'minuto': minuto})
                st.info(f"Retorno: {r.text}")
                time.sleep(2); st.rerun()

elif menu == "📊 Relatório":
    df = carregar_dados()
    if not df.empty:
        if u['cargo'] != "Admin": df = df[df['Vendedor'] == u['nome']]
        st.dataframe(df.sort_values('TS', ascending=False), use_container_width=True)