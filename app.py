import streamlit as st
import pd as pd # Alias para pandas
import pandas as pd
import requests
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- CONFIGURAÇÕES MESTRAS ---
st.set_page_config(page_title="ERP COMERCIAL 4.8", layout="wide", page_icon="🚀")

# SEU NOVO LINK DE SCRIPT JÁ INTEGRADO
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyJiJlQIZeqvt3P09trAdfMecjutOFGVE1jsxPmcdh05nn2cKapdzVnJp8ASmIxCYfLQQ/exec"

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?output=csv"
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSc7YHdYRJZ4I92_cvu0xvHvpU9adHmHmY0RKFxm88NcpjppyA/formResponse"
URL_USUARIOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?gid=1188945197&single=true&output=csv"

IDs = {"cliente": "354575898", "vendedor": "1508368855", "tipo": "2051931448", "vencimento": "440689882", "valor_parc": "1010209945", "comissao": "1053130357", "status": "852082294", "valor_total": "1567666645", "data_base": "1443725489"}

# --- GERENCIAMENTO DE ESTADO E DADOS ---
if 'excluidos_sessao' not in st.session_state:
    st.session_state.excluidos_sessao = []

def carregar_dados():
    t = int(time.time())
    try:
        df = pd.read_csv(f"{CSV_URL}&cache={t}")
        df.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissão', 'Status', 'Total', 'Data_Base']
        
        # Filtro imediato de 'fantasmas' na sessão do usuário
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
        u_e = st.text_input("E-mail")
        u_s = st.text_input("Senha", type="password")
        if st.form_submit_button("Acessar"):
            match = df_u[(df_u['email'].astype(str).str.lower() == u_e.lower().strip()) & (df_u['senha'].astype(str) == u_s)]
            if not match.empty:
                st.session_state.logado = True
                st.session_state.info = match.iloc[0].to_dict()
                st.rerun()
    st.stop()

u = st.session_state.info
menu = st.sidebar.radio("Navegação", ["📝 Lançar & Gerir", "📊 Relatório Completo"])

if menu == "📝 Lançar & Gerir":
    st.subheader("📝 Registro de Venda")
    with st.form("venda", clear_on_submit=True):
        c1, c2 = st.columns(2)
        f_cli = c1.text_input("Nome do Cliente")
        f_data = c2.date_input("Data do Contrato", format="DD/MM/YYYY")
        f_total = c1.number_input("Valor Total (R$)", min_value=0.0)
        f_parc = st.number_input("Nº de Parcelas (0 = à vista)", min_value=0, step=1)
        
        if st.form_submit_button("🚀 GRAVAR NO BANCO"):
            def enviar_linha(tipo, valor, venc):
                p = {f"entry.{IDs['cliente']}": f_cli, f"entry.{IDs['vendedor']}": u['nome'], f"entry.{IDs['tipo']}": tipo, f"entry.{IDs['vencimento']}": venc.strftime('%Y-%m-%d'), f"entry.{IDs['valor_parc']}": str(round(valor, 2)).replace('.',','), f"entry.{IDs['comissao']}": str(round(valor*0.05, 2)).replace('.',','), f"entry.{IDs['status']}": "Pendente", f"entry.{IDs['valor_total']}": str(f_total).replace('.',','), f"entry.{IDs['data_base']}": f_data.strftime('%Y-%m-%d')}
                return requests.post(FORM_URL, data=p).status_code
            
            status = []
            if f_parc == 0: status.append(enviar_linha("À Vista", f_total, f_data))
            else:
                v_p = f_total / f_parc
                for i in range(int(f_parc)):
                    status.append(enviar_linha(f"Parc {i+1}", v_p, f_data + relativedelta(months=i+1)))
            
            if all(s == 200 for s in status):
                st.success("✅ Contrato registrado!"); time.sleep(1); st.rerun()

    if u['cargo'] == "Admin":
        st.divider()
        st.subheader("🗑️ Excluir Contrato (Lote)")
        df_ex = carregar_dados()
        if not df_ex.empty:
            # Agrupa para mostrar o contrato como uma unidade única
            contratos = df_ex.groupby(['Cliente', 'Data_Base', 'Total']).size().reset_index()
            opcoes = [f"{r['Cliente']} | {r['Data_Base']} | R$ {r['Total']}" for i, r in contratos.iterrows()]
            
            sel = st.selectbox("Selecione o contrato para remover todas as parcelas:", ["Selecione..."] + opcoes)
            
            if sel != "Selecione..." and st.button("🔥 EXCLUIR DEFINITIVAMENTE", type="primary"):
                c_cli, c_data, c_total = sel.split(" | ")
                
                # 1. Envia comando de exclusão EM LOTE para o Apps Script
                with st.spinner("Limpando base de dados..."):
                    params = {"cli": c_cli, "dataBase": c_data, "action": "deleteContrato"}
                    r = requests.get(SCRIPT_URL, params=params)
                
                # 2. Registra na sessão para esconder imediatamente
                st.session_state.excluidos_sessao.append({'cli': c_cli, 'data': c_data})
                
                st.error(f"Sistema: {r.text}")
                time.sleep(2); st.rerun()

elif menu == "📊 Relatório Completo":
    st.subheader("📊 Histórico de Lançamentos")
    if st.button("🔄 Sincronizar Agora"):
        st.session_state.excluidos_sessao = [] # Limpa a lista de excluídos temporários
        st.rerun()

    df = carregar_dados()
    if not df.empty:
        if u['cargo'] != "Admin": df = df[df['Vendedor'] == u['nome']]
        # Formatação de exibição
        df['Vencimento'] = pd.to_datetime(df['Vencimento']).dt.strftime('%d/%m/%Y')
        df['Data_Base'] = pd.to_datetime(df['Data_Base']).dt.strftime('%d/%m/%Y')
        st.dataframe(df.sort_values('TS', ascending=False), use_container_width=True)