import streamlit as st
import pandas as pd
import requests
import time
import random
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="ERP 6.2 ULTRA-FAST", layout="wide", page_icon="🛡️")

# --- CONFIGURAÇÕES ---
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyJiJlQIZeqvt3P09trAdfMecjutOFGVE1jsxPmcdh05nn2cKapdzVnJp8ASmIxCYfLQQ/exec"
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?output=csv"
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSc7YHdYRJZ4I92_cvu0xvHvpU9adHmHmY0RKFxm88NcpjppyA/formResponse"
URL_USUARIOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?gid=1188945197&single=true&output=csv"

IDs = {
    "cliente": "354575898", "vendedor": "1508368855", "tipo": "2051931448",
    "vencimento": "440689882", "valor_parc": "1010209945", "comissao": "1053130357",
    "status": "852082294", "valor_total": "1567666645", "data_base": "1443725489",
    "id_contrato": "921030482" 
}

# --- MEMÓRIA TEMPORÁRIA DE EXCLUSÃO ---
if 'ids_excluidos_agora' not in st.session_state:
    st.session_state.ids_excluidos_agora = []

def carregar_dados():
    try:
        # Adicionamos um número aleatório no final da URL para tentar enganar o cache do Google
        df = pd.read_csv(f"{CSV_URL}&nocache={int(time.time())}")
        df.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissão', 'Status', 'Total', 'Data_Base', 'ID_Contrato']
        
        # AQUI ESTÁ O SEGREDO: Removemos da visualização os IDs que acabamos de apagar
        if st.session_state.ids_excluidos_agora:
            df = df[~df['ID_Contrato'].isin(st.session_state.ids_excluidos_agora)]
            
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
            id_unico = f"CTR{int(time.time())}{random.randint(10,99)}"
            def enviar_ao_google(tipo, valor, venc):
                p = {f"entry.{IDs['cliente']}": f_cli, f"entry.{IDs['vendedor']}": u['nome'], f"entry.{IDs['tipo']}": tipo, f"entry.{IDs['vencimento']}": venc.strftime('%Y-%m-%d'), f"entry.{IDs['valor_parc']}": str(round(valor, 2)).replace('.', ','), f"entry.{IDs['status']}": "Pendente", f"entry.{IDs['valor_total']}": str(f_total).replace('.', ','), f"entry.{IDs['data_base']}": f_data.strftime('%Y-%m-%d'), f"entry.{IDs['id_contrato']}": id_unico}
                requests.post(FORM_URL, data=p)

            if f_parc == 0: enviar_ao_google("À Vista", f_total, f_data)
            else:
                v_p = f_total / f_parc
                for i in range(int(f_parc)): enviar_ao_google(f"Parc {i+1}", v_p, f_data + relativedelta(months=i+1))
            st.success(f"Contrato registrado! ID: {id_unico}")
            time.sleep(1); st.rerun()

elif menu == "🗑️ Excluir Contrato":
    if u['cargo'] != "Admin":
        st.warning("Acesso restrito.")
    else:
        st.subheader("🗑️ Cancelar Lançamento")
        df_ex = carregar_dados()
        if not df_ex.empty:
            contratos = df_ex.groupby(['ID_Contrato', 'Cliente', 'Total']).size().reset_index()
            opcoes = [f"{r['ID_Contrato']} | {r['Cliente']} | R$ {r['Total']}" for i, r in contratos.iterrows()]
            sel = st.selectbox("Selecione o contrato:", ["Selecione..."] + opcoes)
            
            if sel != "Selecione..." and st.button("🗑️ APAGAR DEFINITIVAMENTE", type="primary"):
                id_alvo = sel.split(" | ")[0]
                
                # 1. Manda pro Google deletar
                requests.get(SCRIPT_URL, params={"id_contrato": id_alvo, "action": "deleteContrato"})
                
                # 2. COLOCA NA LISTA NEGRA LOCAL (Sumiço Instantâneo)
                st.session_state.ids_excluidos_agora.append(id_alvo)
                
                st.error(f"Contrato {id_alvo} removido com sucesso!")
                time.sleep(1)
                st.rerun()

elif menu == "📊 Relatórios":
    st.subheader("📊 Relatório de Vendas")
    # Botão para limpar a lista negra local e ver o que o Google realmente tem
    if st.button("🔄 Sincronizar com Planilha"):
        st.session_state.ids_excluidos_agora = []
        st.rerun()
        
    df = carregar_dados()
    if not df.empty:
        if u['cargo'] != "Admin": df = df[df['Vendedor'] == u['nome']]
        st.dataframe(df.sort_values('TS', ascending=False), use_container_width=True)