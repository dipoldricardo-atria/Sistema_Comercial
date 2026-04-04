import streamlit as st
import pandas as pd
import requests
import time
import random
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="ERP 6.1 ID-BLINDADO", layout="wide", page_icon="🛡️")

# --- CONFIGURAÇÕES TÉCNICAS ---
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyJiJlQIZeqvt3P09trAdfMecjutOFGVE1jsxPmcdh05nn2cKapdzVnJp8ASmIxCYfLQQ/exec"
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?output=csv"
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSc7YHdYRJZ4I92_cvu0xvHvpU9adHmHmY0RKFxm88NcpjppyA/formResponse"
URL_USUARIOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?gid=1188945197&single=true&output=csv"

# Seus IDs oficiais (incluindo o novo ID_Contrato)
IDs = {
    "cliente": "354575898", "vendedor": "1508368855", "tipo": "2051931448",
    "vencimento": "440689882", "valor_parc": "1010209945", "comissao": "1053130357",
    "status": "852082294", "valor_total": "1567666645", "data_base": "1443725489",
    "id_contrato": "921030482" 
}

def carregar_dados():
    try:
        # Forçamos o recarregamento do CSV
        df = pd.read_csv(f"{CSV_URL}&cache={int(time.time())}")
        # Ajustamos as colunas. O ID_Contrato será a última (coluna 11)
        df.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissão', 'Status', 'Total', 'Data_Base', 'ID_Contrato']
        return df
    except: return pd.DataFrame()

# --- LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.title("🔐 Login")
    df_u = pd.read_csv(URL_USUARIOS)
    with st.form("login"):
        u_e = st.text_input("E-mail"); u_s = st.text_input("Senha", type="password")
        if st.form_submit_button("Acessar"):
            match = df_u[(df_u['email'] == u_e) & (df_u['senha'].astype(str) == u_s)]
            if not match.empty:
                st.session_state.logado = True; st.session_state.info = match.iloc[0].to_dict(); st.rerun()
    st.stop()

u = st.session_state.info
menu = st.sidebar.radio("Navegação", ["📝 Lançar Contrato", "🗑️ Excluir Contrato", "📊 Relatórios"])

if menu == "📝 Lançar Contrato":
    st.subheader("📝 Registro de Nova Venda")
    with st.form("venda_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        f_cli = c1.text_input("Nome do Cliente")
        f_data = c2.date_input("Data do Contrato", format="DD/MM/YYYY")
        f_total = c1.number_input("Valor Total (R$)", min_value=0.0)
        f_parc = st.number_input("Número de Parcelas (0 = À Vista)", min_value=0, step=1)
        
        if st.form_submit_button("🚀 GRAVAR NO GOOGLE"):
            # GERA O "DNA" DO CONTRATO
            id_unico = f"CTR{int(time.time())}{random.randint(10,99)}"
            
            def enviar_ao_google(tipo, valor, venc):
                p = {
                    f"entry.{IDs['cliente']}": f_cli, f"entry.{IDs['vendedor']}": u['nome'],
                    f"entry.{IDs['tipo']}": tipo, f"entry.{IDs['vencimento']}": venc.strftime('%Y-%m-%d'),
                    f"entry.{IDs['valor_parc']}": str(round(valor, 2)).replace('.', ','),
                    f"entry.{IDs['status']}": "Pendente", f"entry.{IDs['valor_total']}": str(f_total).replace('.', ','),
                    f"entry.{IDs['data_base']}": f_data.strftime('%Y-%m-%d'),
                    f"entry.{IDs['id_contrato']}": id_unico # Carimba o ID em todas as parcelas
                }
                requests.post(FORM_URL, data=p)

            if f_parc == 0: enviar_ao_google("À Vista", f_total, f_data)
            else:
                v_p = f_total / f_parc
                for i in range(int(f_parc)):
                    enviar_ao_google(f"Parc {i+1}", v_p, f_data + relativedelta(months=i+1))
            st.success(f"Contrato registrado! ID gerado: {id_unico}")
            time.sleep(1); st.rerun()

elif menu == "🗑️ Excluir Contrato":
    if u['cargo'] != "Admin":
        st.warning("Acesso restrito a administradores.")
    else:
        st.subheader("🗑️ Cancelar Lançamento")
        df_ex = carregar_dados()
        if not df_ex.empty:
            # Agrupa pelo ID único para não mostrar parcelas repetidas
            contratos = df_ex.groupby(['ID_Contrato', 'Cliente', 'Total']).size().reset_index()
            opcoes = [f"{r['ID_Contrato']} | {r['Cliente']} | R$ {r['Total']}" for i, r in contratos.iterrows()]
            
            sel = st.selectbox("Selecione o contrato para remover todas as parcelas:", ["Selecione..."] + opcoes)
            
            if sel != "Selecione..." and st.button("🗑️ APAGAR DEFINITIVAMENTE", type="primary"):
                id_alvo = sel.split(" | ")[0]
                with st.spinner("Limpando base de dados..."):
                    r = requests.get(SCRIPT_URL, params={"id_contrato": id_alvo, "action": "deleteContrato"})
                st.info(f"Retorno do Google: {r.text}")
                time.sleep(2); st.rerun()

elif menu == "📊 Relatórios":
    df = carregar_dados()
    if not df.empty:
        if u['cargo'] != "Admin": df = df[df['Vendedor'] == u['nome']]
        st.dataframe(df.sort_values('TS', ascending=False), use_container_width=True)