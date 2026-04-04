import streamlit as st
import pandas as pd
import requests
import time
import random
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="ERP 8.5 FORECAST", layout="wide", page_icon="💰")

# --- CONFIGURAÇÕES FIXAS (MANTIDAS) ---
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyJiJlQIZeqvt3P09trAdfMecjutOFGVE1jsxPmcdh05nn2cKapdzVnJp8ASmIxCYfLQQ/exec"
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSc7YHdYRJZ4I92_cvu0xvHvpU9adHmHmY0RKFxm88NcpjppyA/formResponse"
URL_USUARIOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?gid=1188945197&single=true&output=csv"

IDs = {
    "cliente": "354575898", "vendedor": "1508368855", "tipo": "2051931448", "vencimento": "440689882",
    "valor_parc": "1010209945", "comissao": "1053130357", "status": "852082294",
    "valor_total": "1567666645", "data_base": "1443725489", "id_contrato": "921030482" 
}

if 'logado' not in st.session_state: st.session_state.logado = False

# --- FUNÇÃO DE LIMPEZA DE NÚMEROS (BLINDADA) ---
def limpar_valor(valor):
    try:
        if pd.isna(valor) or str(valor).strip() == "": return 0.0
        v = str(valor).replace('R$', '').replace('.', '').replace(',', '.').strip()
        return float(v)
    except: return 0.0

def carregar_dados_realtime():
    try:
        r = requests.get(f"{SCRIPT_URL}?action=read", timeout=25)
        df = pd.DataFrame(r.json()[1:], columns=['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissão', 'Status', 'Total', 'Data_Base', 'ID_Contrato'])
        return df
    except: return pd.DataFrame()

# --- LOGIN (MANTIDO) ---
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

# --- MENU ---
menu = st.sidebar.radio("Navegação", ["📝 Lançar & Editar", "📊 Relatório & Previsões"])

# [Lógica de Gravação e Edição mantida 100% igual à v8.4 conforme solicitado]
def executar_gravacao(f_cli, f_vendedor, f_data, f_total, f_entrada, f_parc, id_final):
    def enviar(tipo, venc, valor):
        comis_calc = valor * 0.05
        p = {f"entry.{IDs['cliente']}": f_cli, f"entry.{IDs['vendedor']}": f_vendedor, f"entry.{IDs['tipo']}": tipo, f"entry.{IDs['vencimento']}": venc.strftime('%Y-%m-%d'), f"entry.{IDs['valor_parc']}": str(round(valor, 2)).replace('.', ','), f"entry.{IDs['comissao']}": str(round(comis_calc, 2)).replace('.', ','), f"entry.{IDs['status']}": "Pendente", f"entry.{IDs['valor_total']}": str(f_total).replace('.', ','), f"entry.{IDs['data_base']}": f_data.strftime('%Y-%m-%d'), f"entry.{IDs['id_contrato']}": id_final}
        requests.post(FORM_URL, data=p)

    if f_entrada > 0: enviar("Entrada", f_data, f_entrada)
    restante = f_total - f_entrada
    if f_parc > 0 and restante > 0:
        v_p = restante / f_parc
        for i in range(int(f_parc)): enviar(f"Parc {i+1}", f_data + relativedelta(months=i+1), v_p)
    elif f_parc == 0 and f_entrada == 0: enviar("À Vista", f_data, f_total)

# --- TELAS ---
if menu == "📝 Lançar & Editar":
    # [ABAS DE LANÇAMENTO E EDIÇÃO - MANTIDAS]
    tabs = st.tabs(["🆕 Novo Lançamento", "✏️ Gestão Admin"])
    with tabs[0]:
        with st.form("novo"):
            c1, c2 = st.columns(2)
            f_cli = c1.text_input("Cliente")
            f_data = c2.date_input("Data Base", format="DD/MM/YYYY")
            f_vend = st.selectbox("Vendedor", [nome_user]) # Simplificado para o exemplo
            f_tot = c1.number_input("Total (R$)", min_value=0.0)
            f_ent = c2.number_input("Entrada (R$)", min_value=0.0)
            f_pa = st.number_input("Parcelas", min_value=0, step=1)
            if st.form_submit_button("🚀 GRAVAR NOVO"):
                id_novo = f"ID{int(time.time())}"
                executar_gravacao(f_cli, f_vend, f_data, f_tot, f_ent, f_pa, id_novo)
                st.success("Gravado!"); time.sleep(1); st.rerun()

    with tabs[1]:
        if cargo != "Admin": st.warning("Acesso restrito."); st.stop()
        df_edit = carregar_dados_realtime()
        if not df_edit.empty:
            contratos = df_edit[df_edit['ID_Contrato'].astype(str).str.startswith("ID")].groupby(['ID_Contrato', 'Cliente', 'Total', 'Vendedor', 'Data_Base']).size().reset_index()
            opcoes = {f"{r['ID_Contrato']} | {r['Cliente']}": r for i, r in contratos.iterrows()}
            sel = st.selectbox("Contrato:", ["Selecione..."] + list(opcoes.keys()))
            if sel != "Selecione...":
                dados = opcoes[sel]
                col_ed, col_del = st.columns([2, 1])
                with col_ed:
                    with st.form("edicao"):
                        e_cli = st.text_input("Cliente", value=dados['Cliente'])
                        e_data = st.date_input("Data Base", value=pd.to_datetime(dados['Data_Base']), format="DD/MM/YYYY")
                        e_tot = st.number_input("Total", value=limpar_valor(dados['Total']))
                        e_ent = st.number_input("Entrada/Pago", min_value=0.0)
                        e_pa = st.number_input("Parcelas", min_value=0, step=1)
                        if st.form_submit_button("✅ SALVAR"):
                            requests.get(SCRIPT_URL, params={"id_contrato": dados['ID_Contrato'], "action": "deleteContrato"})
                            executar_gravacao(e_cli, dados['Vendedor'], e_data, e_tot, e_ent, e_pa, dados['ID_Contrato'])
                            st.success("OK!"); time.sleep(1); st.rerun()
                with col_del:
                    if st.button("🔥 APAGAR TUDO", type="primary"):
                        requests.get(SCRIPT_URL, params={"id_contrato": dados['ID_Contrato'], "action": "deleteContrato"})
                        st.rerun()

elif menu == "📊 Relatório & Previsões":
    df = carregar_dados_realtime()
    if not df.empty:
        if cargo != "Admin": df = df[df['Vendedor'] == nome_user]
        
        # Limpeza para cálculo
        df['V_Num'] = df['Valor'].apply(limpar_valor)
        df['C_Num'] = df['Comissão'].apply(limpar_valor)
        
        # Separação por Realizado vs Previsão
        status_pagos = ['Pago', 'Recebido', 'Entrada', 'PAGO', 'RECEBIDO', 'ENTRADA']
        realizado = df[df['Status'].isin(status_pagos)]
        previsao = df[~df['Status'].isin(status_pagos)]

        st.subheader("💰 Painel Financeiro de Comissões")
        m1, m2, m3 = st.columns(3)
        
        # 1. Realizado (O que já entrou)
        m1.metric("Comissões Pagas (Realizado)", f"R$ {realizado['C_Num'].sum():,.2f}")
        
        # 2. Previsão (O que está pendente no futuro)
        m2.metric("Comissão Futura (Previsão)", f"R$ {previsao['C_Num'].sum():,.2f}", help="Soma de todas as parcelas com status Pendente")
        
        # 3. Geral (O valor total do esforço de vendas)
        m3.metric("Potencial Total Acumulado", f"R$ {df['C_Num'].sum():,.2f}")
        
        st.divider()
        st.markdown("### 📑 Histórico Detalhado")
        st.dataframe(df.sort_values('TS', ascending=False), use_container_width=True)