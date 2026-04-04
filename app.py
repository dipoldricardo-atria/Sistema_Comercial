import streamlit as st
import pandas as pd
import requests
import time
import re
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="ERP 10.2 ADMIN FLOW", layout="wide", page_icon="📈")

# --- CONFIGURAÇÕES ---
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyJiJlQIZeqvt3P09trAdfMecjutOFGVE1jsxPmcdh05nn2cKapdzVnJp8ASmIxCYfLQQ/exec"
URL_USUARIOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?gid=1188945197&single=true&output=csv"

if 'logado' not in st.session_state: st.session_state.logado = False

# --- MOTOR DE LIMPEZA ---
def para_numero_puro(valor):
    if pd.isna(valor) or str(valor).strip() == "": return 0.0
    texto = re.sub(r'[^\d.,-]', '', str(valor))
    if not texto: return 0.0
    if ',' in texto and '.' in texto:
        texto = texto.replace('.', '').replace(',', '.')
    elif ',' in texto:
        texto = texto.replace(',', '.')
    try: return float(texto)
    except: return 0.0

def carregar_dados_realtime():
    try:
        r = requests.get(f"{SCRIPT_URL}?action=read&t={int(time.time())}", timeout=25)
        df = pd.DataFrame(r.json()[1:], columns=['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissão', 'Status', 'Total', 'Data_Base', 'ID_Contrato'])
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

try:
    df_v = pd.read_csv(URL_USUARIOS)
    df_v.columns = [c.lower().strip() for c in df_v.columns]
    lista_vendedores = sorted(df_v['nome'].unique().tolist())
except:
    lista_vendedores = [nome_user]

if st.sidebar.button("🚪 Sair"):
    st.session_state.logado = False
    st.rerun()

menu = st.sidebar.radio("Navegação", ["📝 Lançar & Gestão", "📊 Relatório & Previsões"])

def executar_gravacao(f_cli, f_vendedor, f_data, f_total, f_entrada, f_parc, id_final):
    def enviar(tipo, venc, valor):
        comis_calc = valor * 0.05
        params = {
            "action": "create", "cliente": f_cli, "vendedor": f_vendedor, "tipo": tipo,
            "vencimento": venc.strftime('%Y-%m-%d'), "valor": round(valor, 2),
            "comissao": round(comis_calc, 2), "status": "Pendente", "total": f_total,
            "data_base": f_data.strftime('%Y-%m-%d'), "id_contrato": id_final
        }
        requests.get(SCRIPT_URL, params=params)

    if f_entrada > 0: enviar("Entrada", f_data, f_entrada)
    restante = f_total - f_entrada
    if f_parc > 0 and restante > 0:
        v_p = restante / f_parc
        for i in range(int(f_parc)): enviar(f"Parc {i+1}", f_data + relativedelta(months=i+1), v_p)
    elif f_parc == 0 and f_entrada == 0: enviar("À Vista", f_data, f_total)

# --- TELAS ---
if menu == "📝 Lançar & Gestão":
    tabs = st.tabs(["🆕 Novo Lançamento", "💰 Dar Baixa (Financeiro)", "✏️ Gestão Admin"])
    
    with tabs[0]:
        with st.form("novo_venda", clear_on_submit=True):
            c1, c2 = st.columns(2)
            f_cli = c1.text_input("Nome do Cliente")
            f_data = c2.date_input("Data do Contrato", format="DD/MM/YYYY")
            v_sel = st.selectbox("Vendedor", lista_vendedores, index=lista_vendedores.index(nome_user) if nome_user in lista_vendedores else 0)
            f_tot = c1.number_input("Valor Total (R$)", min_value=0.0)
            f_ent = c2.number_input("Entrada (R$)", min_value=0.0)
            f_pa = st.number_input("Parcelas", min_value=0, step=1)
            if st.form_submit_button("🚀 GRAVAR CONTRATO"):
                if f_cli and f_tot > 0:
                    executar_gravacao(f_cli, v_sel, f_data, f_tot, f_ent, f_pa, f"ID{int(time.time())}")
                    st.success("✅ Gravado com Sucesso!"); time.sleep(1); st.rerun()

    with tabs[1]:
        st.subheader("💸 Recebimento")
        df_f = carregar_dados_realtime()
        if not df_f.empty:
            pendentes = df_f[~df_f['Status'].astype(str).str.upper().str.strip().isin(['PAGO', 'RECEBIDO'])]
            if not pendentes.empty:
                for i, row in pendentes.iterrows():
                    with st.expander(f"📌 {row['Cliente']} | {row['Tipo']} | R$ {row['Valor']}"):
                        if st.button(f"Confirmar Pagamento", key=f"bx_{i}"):
                            requests.get(SCRIPT_URL, params={"action": "marcarPago", "ts": str(row['TS']), "cliente": str(row['Cliente']), "valor": str(row['Valor'])})
                            st.rerun()
            else: st.info("Sem pendências.")

    with tabs[2]:
        if cargo != "Admin": st.warning("Restrito."); st.stop()
        df_edit = carregar_dados_realtime()
        if not df_edit.empty:
            contratos = df_edit[df_edit['ID_Contrato'].astype(str).str.startswith("ID")].groupby(['ID_Contrato', 'Cliente', 'Total', 'Vendedor', 'Data_Base']).size().reset_index()
            opcoes = {f"{r['ID_Contrato']} | {r['Cliente']}": r for i, r in contratos.iterrows()}
            sel = st.selectbox("Editar/Apagar:", ["Selecione..."] + list(opcoes.keys()))
            if sel != "Selecione...":
                dados = opcoes[sel]
                with st.form("edicao"):
                    e_cli = st.text_input("Cliente", value=dados['Cliente'])
                    e_data = st.date_input("Data Base", value=pd.to_datetime(dados['Data_Base']))
                    e_vend = st.selectbox("Vendedor", lista_vendedores, index=lista_vendedores.index(dados['Vendedor']) if dados['Vendedor'] in lista_vendedores else 0)
                    e_tot = st.number_input("Total", value=para_numero_puro(dados['Total']))
                    if st.form_submit_button("✅ SALVAR"):
                        requests.get(SCRIPT_URL, params={"id_contrato": dados['ID_Contrato'], "action": "deleteContrato"})
                        executar_gravacao(e_cli, e_vend, e_data, e_tot, 0, 0, dados['ID_Contrato'])
                        st.rerun()
                if st.button("🔥 EXCLUIR", type="primary"):
                    requests.get(SCRIPT_URL, params={"id_contrato": dados['ID_Contrato'], "action": "deleteContrato"})
                    st.rerun()

elif menu == "📊 Relatório & Previsões":
    df = carregar_dados_realtime()
    if not df.empty:
        if cargo != "Admin": df = df[df['Vendedor'] == nome_user]
        
        # --- PREPARAÇÃO DE NÚMEROS ---
        df['C_Num'] = df['Comissão'].apply(para_numero_puro)
        df['V_Num'] = df['Valor'].apply(para_numero_puro)
        df['T_Num'] = df['Total'].apply(para_numero_puro)
        
        status_limpo = df['Status'].astype(str).str.upper().str.strip()
        status_pagos = ['PAGO', 'RECEBIDO', 'ENTRADA', 'À VISTA']
        
        # --- CÁLCULO DE COMISSÕES (EXISTENTE) ---
        comis_paga = df[status_limpo.isin(status_pagos)]['C_Num'].sum()
        comis_pend = df[~status_limpo.isin(status_pagos)]['C_Num'].sum()

        # --- NOVA LÓGICA: FATURAMENTO DE PROJETOS ---
        # 1. Total Contratado (Pega apenas 1 linha por ID_Contrato para não duplicar o total)
        df_contratos únicos = df.drop_duplicates(subset=['ID_Contrato'])
        total_contratado = df_contratos únicos['T_Num'].sum()
        
        # 2. Total Recebido (Soma dos valores das parcelas pagas)
        total_recebido = df[status_limpo.isin(status_pagos)]['V_Num'].sum()
        
        # 3. Total a Receber (Soma dos valores das parcelas pendentes)
        total_a_receber = df[~status_limpo.isin(status_pagos)]['V_Num'].sum()

        # --- INTERFACE ---
        st.subheader("💰 Resumo de Comissões (Seu Ganho)")
        m1, m2, m3 = st.columns(3)
        m1.metric("Comissões Pagas", f"R$ {comis_paga:,.2f}")
        m2.metric("Comissões a Receber", f"R$ {comis_pend:,.2f}")
        m3.metric("Total Comissões", f"R$ {comis_paga + comis_pend:,.2f}")

        st.divider()
        
        st.subheader("🏢 Faturamento de Projetos (Valor de Venda)")
        f1, f2, f3 = st.columns(3)
        f1.metric("Total Contratado", f"R$ {total_contratado:,.2f}", help="Soma do valor total de todos os contratos fechados.")
        f2.metric("Total já Recebido", f"R$ {total_recebido:,.2f}", help="Soma das entradas e parcelas já pagas.")
        f3.metric("Saldo a Receber", f"R$ {total_a_receber:,.2f}", help="Soma de todas as parcelas que ainda constam como Pendente.")

        st.divider()
        st.write("### 📋 Listagem Geral")
        st.dataframe(df.sort_values('TS', ascending=False), use_container_width=True)