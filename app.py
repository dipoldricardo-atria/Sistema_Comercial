import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="ERP 9.0 SISTEMA", layout="wide", page_icon="💰")

# --- CONFIGURAÇÕES ---
SCRIPT_URL = "SUA_URL_DO_SCRIPT_AQUI" 
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSc7YHdYRJZ4I92_cvu0xvHvpU9adHmHmH0RKFxm88NcpjppyA/formResponse"
URL_USUARIOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?gid=1188945197&single=true&output=csv"

IDs = {
    "cliente": "354575898", "vendedor": "1508368855", "tipo": "2051931448", "vencimento": "440689882",
    "valor_parc": "1010209945", "comissao": "1053130357", "status": "852082294",
    "valor_total": "1567666645", "data_base": "1443725489", "id_contrato": "921030482" 
}

if 'logado' not in st.session_state: st.session_state.logado = False

# --- FUNÇÕES ---
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
    st.title("🔐 Login Administrativo")
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
except: lista_vendedores = [nome_user]

menu = st.sidebar.radio("Navegação", ["📝 Lançar & Gestão", "📊 Relatórios"])
if st.sidebar.button("🚪 Sair"):
    st.session_state.logado = False
    st.rerun()

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
    tabs = st.tabs(["🆕 Novo Lançamento", "💰 Dar Baixa (Financeiro)", "✏️ Editar/Apagar"])
    
    with tabs[0]:
        with st.form("novo_venda", clear_on_submit=True):
            c1, c2 = st.columns(2)
            f_cli = c1.text_input("Cliente")
            f_data = c2.date_input("Data", format="DD/MM/YYYY")
            f_vend = st.selectbox("Vendedor", lista_vendedores, index=lista_vendedores.index(nome_user) if nome_user in lista_vendedores else 0)
            f_tot = c1.number_input("Total (R$)", min_value=0.0)
            f_ent = c2.number_input("Entrada (R$)", min_value=0.0)
            f_pa = st.number_input("Parcelas", min_value=0, step=1)
            if st.form_submit_button("🚀 GRAVAR CONTRATO"):
                id_novo = f"ID{int(time.time())}"
                executar_gravacao(f_cli, f_vend, f_data, f_tot, f_ent, f_pa, id_novo)
                st.success("Gravado!"); time.sleep(1); st.rerun()

    with tabs[1]:
        st.markdown("### 💸 Baixa de Pagamentos")
        df_baixa = carregar_dados_realtime()
        if not df_baixa.empty:
            # Pega TUDO que não contém "PAGO" ou "RECEBIDO" no status
            pendentes = df_baixa[~df_baixa['Status'].astype(str).str.upper().isin(['PAGO', 'RECEBIDO'])]
            
            if not pendentes.empty:
                contratos = pendentes.groupby(['ID_Contrato', 'Cliente']).size().reset_index()
                opcoes_c = {f"{r['Cliente']} ({r['ID_Contrato']})": r['ID_Contrato'] for i, r in contratos.iterrows()}
                sel_c = st.selectbox("Selecione o Contrato para Baixa:", ["Selecione..."] + list(opcoes_c.keys()))
                
                if sel_c != "Selecione...":
                    id_sel = opcoes_c[sel_c]
                    parcelas = df_baixa[df_baixa['ID_Contrato'] == id_sel]
                    
                    for i, row in parcelas.iterrows():
                        col1, col2, col3 = st.columns([2, 2, 1])
                        col1.write(f"**{row['Tipo']}** - {row['Vencimento']}")
                        col2.write(f"R$ {row['Valor']}")
                        
                        st_atual = str(row['Status']).upper()
                        if st_atual not in ['PAGO', 'RECEBIDO']:
                            if col3.button(f"Dar Baixa", key=f"btn_{row['TS']}_{i}"):
                                requests.get(SCRIPT_URL, params={"ts": str(row['TS']), "action": "marcarPago"})
                                st.success("Efetuado!")
                                time.sleep(0.5)
                                st.rerun()
                        else:
                            col3.write("✅ Pago")
            else:
                st.info("Nenhuma parcela pendente encontrada.")

    with tabs[2]:
        if cargo != "Admin": st.warning("Acesso restrito."); st.stop()
        df_edit = carregar_dados_realtime()
        if not df_edit.empty:
            contratos_ed = df_edit.groupby(['ID_Contrato', 'Cliente', 'Total', 'Vendedor', 'Data_Base']).size().reset_index()
            opcoes_ed = {f"{r['ID_Contrato']} | {r['Cliente']}": r for i, r in contratos_ed.iterrows()}
            sel_ed = st.selectbox("Editar Contrato:", ["Selecione..."] + list(opcoes_ed.keys()))
            if sel_ed != "Selecione...":
                d = opcoes_ed[sel_ed]
                with st.form("edicao"):
                    e_cli = st.text_input("Cliente", value=d['Cliente'])
                    e_tot = st.number_input("Total", value=limpar_valor(d['Total']))
                    if st.form_submit_button("✅ SALVAR"):
                        requests.get(SCRIPT_URL, params={"id_contrato": d['ID_Contrato'], "action": "deleteContrato"})
                        executar_gravacao(e_cli, d['Vendedor'], pd.to_datetime(d['Data_Base']), e_tot, 0, 0, d['ID_Contrato'])
                        st.rerun()
                if st.button("🔥 EXCLUIR TUDO"):
                    requests.get(SCRIPT_URL, params={"id_contrato": d['ID_Contrato'], "action": "deleteContrato"})
                    st.rerun()

elif menu == "📊 Relatórios":
    df = carregar_dados_realtime()
    if not df.empty:
        df['C_Num'] = df['Comissão'].apply(limpar_valor)
        st_pagos = ['PAGO', 'RECEBIDO', 'ENTRADA']
        realizado = df[df['Status'].astype(str).str.upper().isin(st_pagos)]
        previsao = df[~df['Status'].astype(str).str.upper().isin(st_pagos)]

        st.subheader("💰 Resumo")
        m1, m2, m3 = st.columns(3)
        m1.metric("Recebidas", f"R$ {realizado['C_Num'].sum():,.2f}")
        m2.metric("Previsão", f"R$ {previsao['C_Num'].sum():,.2f}")
        m3.metric("Total", f"R$ {df['C_Num'].sum():,.2f}")
        st.divider()
        st.dataframe(df.sort_values('TS', ascending=False), use_container_width=True)