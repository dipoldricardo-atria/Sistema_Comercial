import streamlit as st
import pandas as pd
import requests
import time
import re
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="ERP 10.0 - REBUILD", layout="wide", page_icon="📊")

# --- CONFIGURAÇÕES ---
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyJiJlQIZeqvt3P09trAdfMecjutOFGVE1jsxPmcdh05nn2cKapdzVnJp8ASmIxCYfLQQ/exec"
URL_USUARIOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?gid=1188945197&single=true&output=csv"

if 'logado' not in st.session_state: st.session_state.logado = False

# --- NOVA FUNÇÃO DE LIMPEZA NUMÉRICA (DO ZERO) ---
def para_numero_puro(valor):
    """Transforma qualquer texto sujo da planilha em um float calculável."""
    if pd.isna(valor) or str(valor).strip() == "":
        return 0.0
    # Remove tudo que não for dígito ou vírgula/ponto
    texto = re.sub(r'[^\d.,-]', '', str(valor))
    if not texto: return 0.0
    
    # Lógica para tratar padrão brasileiro (1.000,00) ou americano (1000.00)
    if ',' in texto and '.' in texto: # Tem os dois (ex: 1.250,50)
        texto = texto.replace('.', '').replace(',', '.')
    elif ',' in texto: # Só tem vírgula (ex: 1250,50)
        texto = texto.replace(',', '.')
        
    try:
        return float(texto)
    except:
        return 0.0

def carregar_dados():
    try:
        r = requests.get(f"{SCRIPT_URL}?action=read&t={int(time.time())}", timeout=25)
        # Cria o DataFrame pulando o cabeçalho
        df = pd.DataFrame(r.json()[1:], columns=['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissão', 'Status', 'Total', 'Data_Base', 'ID_Contrato'])
        
        # --- LIMPEZA DE DADOS IMEDIATA ---
        df['Comissão'] = df['Comissão'].apply(para_numero_puro)
        df['Valor'] = df['Valor'].apply(para_numero_puro)
        df['Total'] = df['Total'].apply(para_numero_puro)
        df['Status_Limpo'] = df['Status'].astype(str).str.upper().str.strip()
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar: {e}")
        return pd.DataFrame()

# --- LOGIN ---
if not st.session_state.logado:
    st.title("🔐 Acesso Restrito")
    with st.form("login"):
        u_e = st.text_input("E-mail").strip().lower()
        u_s = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            df_u = pd.read_csv(URL_USUARIOS)
            df_u.columns = [c.lower().strip() for c in df_u.columns]
            match = df_u[(df_u['email'].str.lower() == u_e) & (df_u['senha'].astype(str) == u_s)]
            if not match.empty:
                st.session_state.logado = True
                st.session_state.usuario = match.iloc[0].to_dict()
                st.rerun()
    st.stop()

u = st.session_state.usuario
cargo = u.get('cargo') or u.get('Cargo') or "Consultor"
nome_user = u.get('nome') or u.get('Nome') or "Usuário"

# --- MENU ---
menu = st.sidebar.radio("Menu Principal", ["📝 Gestão Comercial", "📊 Painel de Resultados"])

if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()

# --- ABA 1: GESTÃO ---
if menu == "📝 Gestão Comercial":
    t1, t2 = st.tabs(["Lançar Venda", "Baixas & Edição"])
    
    with t1:
        with st.form("f_venda", clear_on_submit=True):
            col1, col2 = st.columns(2)
            f_cli = col1.text_input("Cliente")
            f_tot = col1.number_input("Valor Total", min_value=0.0, format="%.2f")
            f_dat = col2.date_input("Data Contrato")
            f_par = col2.number_input("Parcelas", min_value=0, step=1)
            
            if st.form_submit_button("Gravar"):
                # Aqui você pode manter a sua função executar_gravacao (simplificada abaixo)
                params = {
                    "action": "create", "cliente": f_cli, "vendedor": nome_user, "tipo": "À Vista" if f_par == 0 else "Contrato",
                    "vencimento": f_dat.strftime('%Y-%m-%d'), "valor": f_tot, "comissao": f_tot*0.05,
                    "status": "Pendente", "total": f_tot, "data_base": f_dat.strftime('%Y-%m-%d'), "id_contrato": f"ID{int(time.time())}"
                }
                requests.get(SCRIPT_URL, params=params)
                st.success("Enviado!"); time.sleep(1); st.rerun()

    with t2:
        df = carregar_dados()
        if not df.empty:
            pendentes = df[~df['Status_Limpo'].isin(['PAGO', 'RECEBIDO'])]
            for i, r in pendentes.iterrows():
                with st.expander(f"{r['Cliente']} - R$ {r['Valor']}"):
                    if st.button("Marcar como Pago", key=f"pago_{i}"):
                        requests.get(SCRIPT_URL, params={"action": "marcarPago", "ts": str(r['TS']), "cliente": r['Cliente'], "valor": r['Valor']})
                        st.rerun()

# --- ABA 2: RELATÓRIOS (DO ZERO) ---
elif menu == "📊 Painel de Resultados":
    st.title("📊 Relatório de Performance")
    df = carregar_dados()
    
    if not df.empty:
        # Filtro de Hierarquia
        if cargo != "Admin":
            df = df[df['Vendedor'] == nome_user]
        
        # Lógica de Soma (Binária e Direta)
        status_pagos = ['PAGO', 'RECEBIDO', 'ENTRADA', 'À VISTA']
        
        realizado = df[df['Status_Limpo'].isin(status_pagos)]['Comissão'].sum()
        previsao = df[~df['Status_Limpo'].isin(status_pagos)]['Comissão'].sum()
        total_geral = df['Comissão'].sum()

        # Layout de KPIS
        k1, k2, k3 = st.columns(3)
        k1.metric("Comissão Realizada", f"R$ {realizado:,.2f}")
        k2.metric("Comissão Pendente", f"R$ {previsao:,.2f}")
        k3.metric("Total (Cenário Ideal)", f"R$ {total_geral:,.2f}")
        
        st.divider()
        st.write("### Detalhamento das Operações")
        st.dataframe(df[['TS', 'Cliente', 'Tipo', 'Vencimento', 'Comissão', 'Status']], use_container_width=True)