import streamlit as st
import pandas as pd
import requests
import time
import random
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="ERP COMERCIAL 6.5", layout="wide", page_icon="🚀")

# --- CONFIGURAÇÕES ---
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyJiJlQIZeqvt3P09trAdfMecjutOFGVE1jsxPmcdh05nn2cKapdzVnJp8ASmIxCYfLQQ/exec"
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?output=csv"
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSc7YHdYRJZ4I92_cvu0xvHvpU9adHmHmY0RKFxm88NcpjppyA/formResponse"
URL_USUARIOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?gid=1188945197&single=true&output=csv"

# Seus IDs Oficiais
IDs = {
    "cliente": "354575898", "vendedor": "1508368855", "tipo": "2051931448",
    "vencimento": "440689882", "valor_parc": "1010209945", "comissao": "1053130357",
    "status": "852082294", "valor_total": "1567666645", "data_base": "1443725489",
    "id_contrato": "921030482" 
}

if 'excluidos_local' not in st.session_state:
    st.session_state.excluidos_local = []

def carregar_dados():
    try:
        df = pd.read_csv(f"{CSV_URL}&nocache={int(time.time())}")
        # Mapeia as 11 colunas exatamente como estão na planilha
        df.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissão', 'Status', 'Total', 'Data_Base', 'ID_Contrato']
        # Filtro imediato para sumir da tela do Admin após apagar
        if st.session_state.excluidos_local:
            df = df[~df['ID_Contrato'].isin(st.session_state.excluidos_local)]
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
            match = df_u[(df_u['email'] == u_e) & (df_u['senha'].astype(str) == u_s)]
            if not match.empty:
                st.session_state.logado = True; st.session_state.info = match.iloc[0].to_dict(); st.rerun()
    st.stop()

u = st.session_state.info
menu = st.sidebar.radio("Navegação", ["📝 Lançar & Gerir", "📊 Relatório Completo"])

if menu == "📝 Lançar & Gerir":
    st.subheader(f"📝 Registro de Venda - {u['nome']}")
    with st.form("venda_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        f_cli = col1.text_input("Nome do Cliente")
        f_data = col2.date_input("Data do Contrato", format="DD/MM/YYYY")
        
        f_total = col1.number_input("Valor Total do Contrato (R$)", min_value=0.0)
        f_entrada = col2.number_input("Valor de Entrada (R$)", min_value=0.0)
        
        f_parc = st.number_input("Número de Parcelas Restantes", min_value=0, step=1)
        
        if st.form_submit_button("🚀 GRAVAR NO BANCO"):
            id_gera = f"ID{int(time.time())}{random.randint(10,99)}"
            
            def enviar(tipo, valor, venc):
                comissao = valor * 0.05 # Exemplo de 5%
                p = {
                    f"entry.{IDs['cliente']}": f_cli, f"entry.{IDs['vendedor']}": u['nome'],
                    f"entry.{IDs['tipo']}": tipo, f"entry.{IDs['vencimento']}": venc.strftime('%Y-%m-%d'),
                    f"entry.{IDs['valor_parc']}": str(round(valor, 2)).replace('.', ','),
                    f"entry.{IDs['comissao']}": str(round(comissao, 2)).replace('.', ','),
                    f"entry.{IDs['status']}": "Pendente", f"entry.{IDs['valor_total']}": str(f_total).replace('.', ','),
                    f"entry.{IDs['data_base']}": f_data.strftime('%Y-%m-%d'),
                    f"entry.{IDs['id_contrato']}": id_gera
                }
                requests.post(FORM_URL, data=p)

            # 1. Grava a Entrada (se houver)
            if f_entrada > 0:
                enviar("Entrada", f_entrada, f_data)
            
            # 2. Grava as Parcelas
            valor_restante = f_total - f_entrada
            if f_parc > 0 and valor_restante > 0:
                v_p = valor_restante / f_parc
                for i in range(int(f_parc)):
                    enviar(f"Parc {i+1}", v_p, f_data + relativedelta(months=i+1))
            elif f_parc == 0 and f_entrada == 0:
                enviar("À Vista", f_total, f_data)
                
            st.success(f"✅ Contrato {id_gera} gravado com sucesso!")
            time.sleep(1); st.rerun()

    if u['cargo'] == "Admin":
        st.divider()
        st.subheader("🗑️ Cancelar Contrato (Lote)")
        df_ex = carregar_dados()
        if not df_ex.empty:
            contratos = df_ex.groupby(['ID_Contrato', 'Cliente', 'Total']).size().reset_index()
            opcoes = [f"{r['ID_Contrato']} | {r['Cliente']} | R$ {r['Total']}" for i, r in contratos.iterrows()]
            sel = st.selectbox("Selecione o contrato para remover:", ["Selecione..."] + opcoes)
            
            if sel != "Selecione..." and st.button("🔥 APAGAR DEFINITIVAMENTE", type="primary"):
                id_alvo = sel.split(" | ")[0]
                # Envia comando de exclusão
                r = requests.get(SCRIPT_URL, params={"id_contrato": id_alvo, "action": "deleteContrato"})
                # Adiciona na lista de "sumiço imediato"
                st.session_state.excluidos_local.append(id_alvo)
                st.error(f"Sistema: {r.text}")
                time.sleep(2); st.rerun()

elif menu == "📊 Relatório Completo":
    st.subheader("📊 Histórico Geral")
    if st.button("🔄 Sincronizar Agora"):
        st.session_state.excluidos_local = []
        st.rerun()
    
    df = carregar_dados()
    if not df.empty:
        if u['cargo'] != "Admin": df = df[df['Vendedor'] == u['nome']]
        st.dataframe(df.sort_values('TS', ascending=False), use_container_width=True)