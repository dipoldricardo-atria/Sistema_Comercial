import streamlit as st
import pandas as pd
import requests
import time
import random
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="ERP 8.1 MASTER TOTAL", layout="wide", page_icon="⚡")

# --- CONFIGURAÇÕES ---
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyJiJlQIZeqvt3P09trAdfMecjutOFGVE1jsxPmcdh05nn2cKapdzVnJp8ASmIxCYfLQQ/exec"
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSc7YHdYRJZ4I92_cvu0xvHvpU9adHmHmY0RKFxm88NcpjppyA/formResponse"
URL_USUARIOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?gid=1188945197&single=true&output=csv"

IDs = {
    "cliente": "354575898", "vendedor": "1508368855", "tipo": "2051931448", "vencimento": "440689882",
    "valor_parc": "1010209945", "comissao": "1053130357", "status": "852082294",
    "valor_total": "1567666645", "data_base": "1443725489", "id_contrato": "921030482" 
}

if 'logado' not in st.session_state: st.session_state.logado = False

def carregar_dados_realtime():
    try:
        r = requests.get(f"{SCRIPT_URL}?action=read", timeout=20)
        df = pd.DataFrame(r.json()[1:], columns=['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissão', 'Status', 'Total', 'Data_Base', 'ID_Contrato'])
        # Formatação de Datas para o padrão BR na exibição
        for col in ['Vencimento', 'Data_Base']:
            df[col] = pd.to_datetime(df[col]).dt.strftime('%d/%m/%Y')
        return df
    except: return pd.DataFrame()

# --- LOGIN ---
if not st.session_state.logado:
    st.title("🔐 Login Master")
    with st.form("login"):
        u_e = st.text_input("E-mail")
        u_s = st.text_input("Senha", type="password")
        if st.form_submit_button("Acessar"):
            df_u = pd.read_csv(URL_USUARIOS)
            df_u.columns = [c.lower().strip() for c in df_u.columns]
            match = df_u[(df_u['email'].str.lower() == u_e.lower().strip()) & (df_u['senha'].astype(str) == u_s)]
            if not match.empty:
                st.session_state.logado = True
                st.session_state.usuario = match.iloc[0].to_dict()
                st.rerun()
    st.stop()

u = st.session_state.usuario
cargo = u.get('cargo') or u.get('Cargo') or "Consultor"
nome_user = u.get('nome') or u.get('Nome') or "Usuário"

if st.sidebar.button("🚪 Sair"):
    st.session_state.logado = False
    st.rerun()

menu = st.sidebar.radio("Navegação", ["📝 Lançar & Editar", "📊 Relatório"])

try:
    df_v = pd.read_csv(URL_USUARIOS)
    df_v.columns = [c.lower().strip() for c in df_v.columns]
    lista_vendedores = sorted(df_v['nome'].unique().tolist())
except: lista_vendedores = [nome_user]

def executar_gravacao(f_cli, f_vendedor, f_data, f_total, f_entrada, f_parc, id_final):
    def enviar(tipo, venc, valor):
        p = {f"entry.{IDs['cliente']}": f_cli, f"entry.{IDs['vendedor']}": f_vendedor, f"entry.{IDs['tipo']}": tipo, f"entry.{IDs['vencimento']}": venc.strftime('%Y-%m-%d'), f"entry.{IDs['valor_parc']}": str(round(valor, 2)).replace('.', ','), f"entry.{IDs['status']}": "Pendente", f"entry.{IDs['valor_total']}": str(f_total).replace('.', ','), f"entry.{IDs['data_base']}": f_data.strftime('%Y-%m-%d'), f"entry.{IDs['id_contrato']}": id_final}
        requests.post(FORM_URL, data=p)

    if f_entrada > 0: enviar("Entrada", f_data, f_entrada)
    restante = f_total - f_entrada
    if f_parc > 0 and restante > 0:
        v_p = restante / f_parc
        for i in range(int(f_parc)): enviar(f"Parc {i+1}", f_data + relativedelta(months=i+1), v_p)
    elif f_parc == 0 and f_entrada == 0: enviar("À Vista", f_data, f_total)

# --- TELAS ---
if menu == "📝 Lançar & Editar":
    tabs = st.tabs(["🆕 Novo Lançamento", "✏️ Gestão Admin (Editar/Apagar)"])
    
    with tabs[0]:
        with st.form("novo"):
            c1, c2 = st.columns(2)
            f_cli = c1.text_input("Cliente")
            f_data = c2.date_input("Data Base", format="DD/MM/YYYY")
            f_vend = st.selectbox("Vendedor", lista_vendedores, index=lista_vendedores.index(nome_user) if nome_user in lista_vendedores else 0)
            f_tot = c1.number_input("Total (R$)", min_value=0.0)
            f_ent = c2.number_input("Entrada (R$)", min_value=0.0)
            f_pa = st.number_input("Parcelas", min_value=0, step=1)
            if st.form_submit_button("🚀 GRAVAR NOVO"):
                id_novo = f"ID{int(time.time())}"
                executar_gravacao(f_cli, f_vend, f_data, f_tot, f_ent, f_pa, id_novo)
                st.success("Gravado!"); time.sleep(1); st.rerun()

    with tabs[1]:
        if cargo != "Admin": st.warning("Acesso restrito ao Administrador."); st.stop()
        df_edit = carregar_dados_realtime()
        if not df_edit.empty:
            # Agrupa para mostrar os contratos disponíveis
            contratos = df_edit[df_edit['ID_Contrato'].astype(str).str.startswith("ID")].groupby(['ID_Contrato', 'Cliente', 'Total', 'Vendedor', 'Data_Base']).size().reset_index()
            opcoes = {f"{r['ID_Contrato']} | {r['Cliente']}": r for i, r in contratos.iterrows()}
            sel = st.selectbox("Selecione o contrato para gerenciar:", ["Selecione..."] + list(opcoes.keys()))
            
            if sel != "Selecione...":
                dados = opcoes[sel]
                st.divider()
                
                col_ed, col_del = st.columns([2, 1])
                
                with col_ed:
                    st.markdown("### ✏️ Editar Dados")
                    with st.form("edicao"):
                        e_cli = st.text_input("Cliente", value=dados['Cliente'])
                        # Converter string DD/MM/AAAA de volta para data para o componente
                        e_data_ini = datetime.strptime(dados['Data_Base'], '%d/%m/%Y')
                        e_data = st.date_input("Data Base", value=e_data_ini, format="DD/MM/YYYY")
                        e_vend = st.selectbox("Vendedor", lista_vendedores, index=lista_vendedores.index(dados['Vendedor']) if dados['Vendedor'] in lista_vendedores else 0)
                        e_tot = st.number_input("Total (R$)", value=float(str(dados['Total']).replace(',','.')))
                        e_ent = st.number_input("Valor de Entrada/Pago (R$)", min_value=0.0)
                        e_pa = st.number_input("Número de Parcelas", min_value=0, step=1)
                        
                        if st.form_submit_button("✅ SALVAR ALTERAÇÕES"):
                            requests.get(SCRIPT_URL, params={"id_contrato": dados['ID_Contrato'], "action": "deleteContrato"})
                            executar_gravacao(e_cli, e_vend, e_data, e_tot, e_ent, e_pa, dados['ID_Contrato'])
                            st.success("Atualizado!"); time.sleep(1); st.rerun()

                with col_del:
                    st.markdown("### 🗑️ Exclusão em Lote")
                    st.warning("Esta ação apaga todas as parcelas deste contrato.")
                    if st.button("🔥 APAGAR TUDO AGORA", type="primary"):
                        r = requests.get(SCRIPT_URL, params={"id_contrato": dados['ID_Contrato'], "action": "deleteContrato"})
                        st.error(f"Sistema: {r.text}")
                        time.sleep(2); st.rerun()

elif menu == "📊 Relatório":
    st.subheader("📊 Histórico Geral (Datas em DD/MM/AAAA)")
    df = carregar_dados_realtime()
    if not df.empty:
        if cargo != "Admin": df = df[df['Vendedor'] == nome_user]
        st.dataframe(df.sort_values('TS', ascending=False), use_container_width=True)