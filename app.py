import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="ERP 9.2 ADMIN FLOW", layout="wide", page_icon="⚡")

# --- CONFIGURAÇÕES ---
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyJiJlQIZeqvt3P09trAdfMecjutOFGVE1jsxPmcdh05nn2cKapdzVnJp8ASmIxCYfLQQ/exec"
URL_USUARIOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?gid=1188945197&single=true&output=csv"

if 'logado' not in st.session_state: st.session_state.logado = False

# --- MOTOR DE CONVERSÃO NUMÉRICA (CRÍTICO PARA RELATÓRIOS) ---
def forcar_numero(valor):
    try:
        if pd.isna(valor) or str(valor).strip() == "": return 0.0
        # Remove R$, espaços, pontos de milhar e troca vírgula por ponto
        v = str(valor).replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.').strip()
        return float(v)
    except:
        return 0.0

def carregar_dados_realtime():
    try:
        r = requests.get(f"{SCRIPT_URL}?action=read&t={int(time.time())}", timeout=25)
        df = pd.DataFrame(r.json()[1:], columns=['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissão', 'Status', 'Total', 'Data_Base', 'ID_Contrato'])
        return df
    except:
        return pd.DataFrame()

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
                    st.success("✅ Gravado!"); time.sleep(1); st.rerun()

    with tabs[1]:
        st.subheader("💸 Recebimento")
        df_f = carregar_dados_realtime()
        if not df_f.empty:
            pendentes = df_f[~df_f['Status'].astype(str).str.upper().isin(['PAGO', 'RECEBIDO'])]
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
                    e_tot = st.number_input("Total", value=forcar_numero(dados['Total']))
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
        # Se não for admin, vê apenas os seus dados
        if cargo != "Admin":
            df = df[df['Vendedor'] == nome_user]
        
        # Converte a coluna Comissão para números reais para garantir a soma correta
        df['Comissao_Real'] = df['Comissão'].apply(forcar_numero)
        
        # Define quais status são considerados "Recebidos/Pagos"
        # Incluímos variações para evitar erro de digitação na planilha
        status_pagos = ['PAGO', 'RECEBIDO', 'ENTRADA', 'À VISTA']
        
        # Filtra as linhas
        df_pagas = df[df['Status'].astype(str).str.upper().strip().isin(status_pagos)]
        df_pendentes = df[~df['Status'].astype(str).str.upper().strip().isin(status_pagos)]
        
        # Cálculos Finais
        total_pago = df_pagas['Comissao_Real'].sum()
        total_pendente = df_pendentes['Comissao_Real'].sum()
        total_geral = df['Comissao_Real'].sum()

        st.subheader("💰 Painel de Comissões")
        c1, c2, c3 = st.columns(3)
        c1.metric("Comissões Pagas (Realizado)", f"R$ {total_pago:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        c2.metric("Comissões Pendentes (Previsão)", f"R$ {total_pendente:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        c3.metric("Total Acumulado", f"R$ {total_geral:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        
        st.divider()
        st.write("### 📋 Detalhamento de Lançamentos")
        # Formata o DataFrame para exibição
        df_display = df.copy()
        df_display = df_display.sort_values('TS', ascending=False)
        st.dataframe(df_display, use_container_width=True)