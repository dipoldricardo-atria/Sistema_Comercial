import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="ERP 8.7 ADMIN FLOW", layout="wide", page_icon="⚡")

# --- CONFIGURAÇÕES FIXAS ---
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyJiJlQIZeqvt3P09trAdfMecjutOFGVE1jsxPmcdh05nn2cKapdzVnJp8ASmIxCYfLQQ/exec"
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSc7YHdYRJZ4I92_cvu0xvHvpU9adHmHmH0RKFxm88NcpjppyA/formResponse"
URL_USUARIOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?gid=1188945197&single=true&output=csv"

IDs = {
    "cliente": "354575898", "vendedor": "1508368855", "tipo": "2051931448", "vencimento": "440689882",
    "valor_parc": "1010209945", "comissao": "1053130357", "status": "852082294",
    "valor_total": "1567666645", "data_base": "1443725489", "id_contrato": "921030482" 
}

if 'logado' not in st.session_state: st.session_state.logado = False

# --- FUNÇÕES DE SUPORTE ---
def limpar_valor(valor):
    try:
        if pd.isna(valor) or str(valor).strip() == "": return 0.0
        v = str(valor).replace('R$', '').replace('.', '').replace(',', '.').strip()
        return float(v)
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
        p = {
            f"entry.{IDs['cliente']}": f_cli, f"entry.{IDs['vendedor']}": f_vendedor, 
            f"entry.{IDs['tipo']}": tipo, f"entry.{IDs['vencimento']}": venc.strftime('%Y-%m-%d'), 
            f"entry.{IDs['valor_parc']}": str(round(valor, 2)).replace('.', ','), 
            f"entry.{IDs['comissao']}": str(round(comis_calc, 2)).replace('.', ','), 
            f"entry.{IDs['status']}": "Pendente", f"entry.{IDs['valor_total']}": str(f_total).replace('.', ','), 
            f"entry.{IDs['data_base']}": f_data.strftime('%Y-%m-%d'), f"entry.{IDs['id_contrato']}": id_final
        }
        requests.post(FORM_URL, data=p)

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
            vendedor_selecionado = st.selectbox("Vendedor Responsável", lista_vendedores, index=lista_vendedores.index(nome_user) if nome_user in lista_vendedores else 0)
            f_tot = c1.number_input("Valor Total (R$)", min_value=0.0)
            f_ent = c2.number_input("Entrada (R$)", min_value=0.0)
            f_pa = st.number_input("Quantidade de Parcelas", min_value=0, step=1)
            if st.form_submit_button("🚀 GRAVAR NOVO CONTRATO"):
                if f_cli and f_tot > 0:
                    id_novo = f"ID{int(time.time())}"
                    executar_gravacao(f_cli, vendedor_selecionado, f_data, f_tot, f_ent, f_pa, id_novo)
                    st.success("✅ Gravado!")
                    time.sleep(1); st.rerun()

    with tabs[1]:
        st.subheader("💸 Recebimento de Parcelas")
        df_f = carregar_dados_realtime()
        if not df_f.empty:
            # Filtro para ignorar o que já está Pago ou Recebido
            pendentes = df_f[~df_f['Status'].astype(str).str.upper().isin(['PAGO', 'RECEBIDO'])]
            if not pendentes.empty:
                for i, row in pendentes.iterrows():
                    with st.expander(f"📌 {row['Cliente']} | {row['Tipo']} | R$ {row['Valor']}"):
                        st.write(f"Vencimento Original: {row['Vencimento']}")
                        # Chave do botão ÚNICA (TS + índice) para evitar erro de duplicidade
                        if st.button(f"Confirmar Pagamento", key=f"baixa_{row['TS']}_{i}"):
                            ts_limpo = str(row['TS']).strip()
                            # Chamada direta para o Script do Google
                            res = requests.get(f"{SCRIPT_URL}?action=marcarPago&ts={ts_limpo}")
                            if "Sucesso" in res.text:
                                st.success("Status atualizado na planilha!")
                                time.sleep(0.5); st.rerun()
                            else:
                                st.error(f"Erro ao comunicar com a planilha: {res.text}")
            else: st.info("Tudo em dia! Sem pendências.")

    with tabs[2]:
        if cargo != "Admin": st.warning("Acesso restrito."); st.stop()
        df_edit = carregar_dados_realtime()
        if not df_edit.empty:
            contratos = df_edit[df_edit['ID_Contrato'].astype(str).str.startswith("ID")].groupby(['ID_Contrato', 'Cliente', 'Total', 'Vendedor', 'Data_Base']).size().reset_index()
            opcoes = {f"{r['ID_Contrato']} | {r['Cliente']}": r for i, r in contratos.iterrows()}
            sel = st.selectbox("Selecione para Editar/Apagar:", ["Selecione..."] + list(opcoes.keys()))
            if sel != "Selecione...":
                dados = opcoes[sel]
                with st.form("edicao_venda"):
                    e_cli = st.text_input("Cliente", value=dados['Cliente'])
                    e_data = st.date_input("Data Base", value=pd.to_datetime(dados['Data_Base']), format="DD/MM/YYYY")
                    e_vend = st.selectbox("Vendedor", lista_vendedores, index=lista_vendedores.index(dados['Vendedor']) if dados['Vendedor'] in lista_vendedores else 0)
                    e_tot = st.number_input("Total", value=limpar_valor(dados['Total']))
                    if st.form_submit_button("✅ SALVAR ALTERAÇÕES"):
                        requests.get(SCRIPT_URL, params={"id_contrato": dados['ID_Contrato'], "action": "deleteContrato"})
                        executar_gravacao(e_cli, e_vend, e_data, e_tot, 0, 0, dados['ID_Contrato'])
                        st.success("Alterado!"); time.sleep(1); st.rerun()
                if st.button("🔥 EXCLUIR CONTRATO", type="primary", key="del_final"):
                    requests.get(SCRIPT_URL, params={"id_contrato": dados['ID_Contrato'], "action": "deleteContrato"})
                    st.success("Excluído!"); time.sleep(1); st.rerun()

elif menu == "📊 Relatório & Previsões":
    df = carregar_dados_realtime()
    if not df.empty:
        if cargo != "Admin": df = df[df['Vendedor'] == nome_user]
        df['C_Num'] = df['Comissão'].apply(limpar_valor)
        st_pagos = ['PAGO', 'RECEBIDO', 'ENTRADA']
        realizado = df[df['Status'].astype(str).str.upper().isin(st_pagos)]
        previsao = df[~df['Status'].astype(str).str.upper().isin(st_pagos)]
        st.subheader("💰 Painel de Comissões")
        m1, m2, m3 = st.columns(3)
        m1.metric("Realizado (Pagas)", f"R$ {realizado['C_Num'].sum():,.2f}")
        m2.metric("Previsão (Pendentes)", f"R$ {previsao['C_Num'].sum():,.2f}")
        m3.metric("Total Acumulado", f"R$ {df['C_Num'].sum():,.2f}")
        st.divider()
        st.dataframe(df.sort_values('TS', ascending=False), use_container_width=True)