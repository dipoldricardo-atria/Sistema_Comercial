import streamlit as st
import pandas as pd
import requests
import time
import random
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="ERP 7.0 DIRECT-READ", layout="wide")

# --- CONFIGURAÇÕES ---
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyJiJlQIZeqvt3P09trAdfMecjutOFGVE1jsxPmcdh05nn2cKapdzVnJp8ASmIxCYfLQQ/exec"
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSc7YHdYRJZ4I92_cvu0xvHvpU9adHmHmY0RKFxm88NcpjppyA/formResponse"
URL_USUARIOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?gid=1188945197&single=true&output=csv"

IDs = {
    "cliente": "354575898", "vendedor": "1508368855", "tipo": "2051931448",
    "vencimento": "440689882", "valor_parc": "1010209945", "comissao": "1053130357",
    "status": "852082294", "valor_total": "1567666645", "data_base": "1443725489",
    "id_contrato": "921030482" 
}

# --- FUNÇÃO DE CARGA REAL-TIME (PULA O CACHE DO CSV) ---
def carregar_dados_realtime():
    try:
        # Pedimos ao Script para ler a planilha AGORA
        r = requests.get(f"{SCRIPT_URL}?action=read")
        lista_dados = r.json() # O script devolve uma lista de listas
        
        # Transformamos em DataFrame (Pula a primeira linha que é o cabeçalho)
        df = pd.DataFrame(lista_dados[1:], columns=['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissão', 'Status', 'Total', 'Data_Base', 'ID_Contrato'])
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

# --- LOGIN (Simplificado para o exemplo) ---
if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.title("🔐 Acesso Sistema")
    u_e = st.text_input("E-mail")
    u_s = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        df_u = pd.read_csv(URL_USUARIOS)
        match = df_u[(df_u['email'] == u_e) & (df_u['senha'].astype(str) == u_s)]
        if not match.empty:
            st.session_state.logado = True
            st.session_state.info = match.iloc[0].to_dict()
            st.rerun()
    st.stop()

u = st.session_state.info
menu = st.sidebar.radio("Navegação", ["📝 Lançar & Gerir", "📊 Relatório Completo"])

if menu == "📝 Lançar & Gerir":
    st.subheader(f"📝 Registro - {u['nome']}")
    with st.form("venda_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        f_cli = col1.text_input("Nome do Cliente")
        f_data = col2.date_input("Data Contrato")
        f_total = col1.number_input("Valor Total (R$)", min_value=0.0)
        f_entrada = col2.number_input("Valor de Entrada (R$)", min_value=0.0)
        f_parc = st.number_input("Parcelas Restantes", min_value=0, step=1)
        
        if st.form_submit_button("🚀 GRAVAR"):
            id_gera = f"ID{int(time.time())}"
            def enviar(tipo, valor, venc):
                p = {f"entry.{IDs['cliente']}": f_cli, f"entry.{IDs['vendedor']}": u['nome'], f"entry.{IDs['tipo']}": tipo, f"entry.{IDs['vencimento']}": venc.strftime('%Y-%m-%d'), f"entry.{IDs['valor_parc']}": str(round(valor, 2)).replace('.', ','), f"entry.{IDs['status']}": "Pendente", f"entry.{IDs['valor_total']}": str(f_total).replace('.', ','), f"entry.{IDs['data_base']}": f_data.strftime('%Y-%m-%d'), f"entry.{IDs['id_contrato']}": id_gera}
                requests.post(FORM_URL, data=p)

            if f_entrada > 0: enviar("Entrada", f_entrada, f_data)
            valor_restante = f_total - f_entrada
            if f_parc > 0 and valor_restante > 0:
                v_p = valor_restante / f_parc
                for i in range(int(f_parc)): enviar(f"Parc {i+1}", v_p, f_data + relativedelta(months=i+1))
            elif f_parc == 0 and f_entrada == 0: enviar("À Vista", f_total, f_data)
            st.success(f"Gravado! ID: {id_gera}")
            time.sleep(2); st.rerun()

    if u['cargo'] == "Admin":
        st.divider()
        st.subheader("🗑️ Cancelar Lançamento")
        df_ex = carregar_dados_realtime() # Busca dado fresquinho do Google
        if not df_ex.empty:
            contratos = df_ex.groupby(['ID_Contrato', 'Cliente', 'Total']).size().reset_index()
            opcoes = [f"{r['ID_Contrato']} | {r['Cliente']} | R$ {r['Total']}" for i, r in contratos.iterrows() if str(r['ID_Contrato']).startswith("ID")]
            sel = st.selectbox("Selecione o contrato:", ["Selecione..."] + opcoes)
            
            if sel != "Selecione..." and st.button("🔥 APAGAR TUDO"):
                id_alvo = sel.split(" | ")[0]
                r = requests.get(SCRIPT_URL, params={"id_contrato": id_alvo, "action": "deleteContrato"})
                st.warning(f"Resposta Google: {r.text}")
                time.sleep(2); st.rerun()

elif menu == "📊 Relatório Completo":
    st.subheader("📊 Histórico Real-Time")
    df = carregar_dados_realtime()
    if not df.empty:
        if u['cargo'] != "Admin": df = df[df['Vendedor'] == u['nome']]
        st.dataframe(df.sort_values('TS', ascending=False), use_container_width=True)