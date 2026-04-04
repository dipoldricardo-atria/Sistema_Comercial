import streamlit as st
import pandas as pd
import requests
import time
import re
import io
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from fpdf import FPDF

st.set_page_config(page_title="ERP 11.0 BI SYSTEM", layout="wide", page_icon="📊")

# --- CONFIGURAÇÕES ---
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyJiJlQIZeqvt3P09trAdfMecjutOFGVE1jsxPmcdh05nn2cKapdzVnJp8ASmIxCYfLQQ/exec"
URL_USUARIOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?gid=1188945197&single=true&output=csv"

if 'logado' not in st.session_state: st.session_state.logado = False

# --- AUXILIARES ---
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
        # Tipagem de datas para filtros
        df['Data_Base_DT'] = pd.to_datetime(df['Data_Base']).dt.date
        df['Vencimento_DT'] = pd.to_datetime(df['Vencimento']).dt.date
        return df
    except: return pd.DataFrame()

# --- FUNÇÃO GERAR PDF ---
def gerar_pdf(df_filtrado):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, "Relatorio de Vendas e Comissoes", 0, 1, "C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(190, 10, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1, "R")
    pdf.ln(10)
    
    # Cabeçalho Tabela
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(40, 8, "Cliente", 1, 0, "C", 1)
    pdf.cell(40, 8, "Vendedor", 1, 0, "C", 1)
    pdf.cell(30, 8, "Vencimento", 1, 0, "C", 1)
    pdf.cell(30, 8, "Valor", 1, 0, "C", 1)
    pdf.cell(30, 8, "Comissao", 1, 0, "C", 1)
    pdf.cell(20, 8, "Status", 1, 1, "C", 1)

    for _, r in df_filtrado.iterrows():
        pdf.cell(40, 7, str(r['Cliente'])[:18], 1)
        pdf.cell(40, 7, str(r['Vendedor'])[:18], 1)
        pdf.cell(30, 7, str(r['Vencimento']), 1)
        pdf.cell(30, 7, f"R$ {para_numero_puro(r['Valor']):.2f}", 1)
        pdf.cell(30, 7, f"R$ {para_numero_puro(r['Comissão']):.2f}", 1)
        pdf.cell(20, 7, str(r['Status']), 1, 1)
    
    return pdf.output(dest='S').encode('latin-1')

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

# --- SIDEBAR FILTROS ---
st.sidebar.title("🔍 Filtros de Inteligência")

df_raw = carregar_dados_realtime()

if not df_raw.empty:
    # 1. Filtro de Vendedor (Múltiplo)
    vendedores_unicos = sorted(df_raw['Vendedor'].unique().tolist())
    if cargo == "Admin":
        vendedores_sel = st.sidebar.multiselect("Vendedores", vendedores_unicos, default=vendedores_unicos)
    else:
        vendedores_sel = [nome_user]
        st.sidebar.info(f"Vendedor: {nome_user}")

    # 2. Filtro de Período (Data Base - Contrato)
    st.sidebar.subheader("📅 Período do Contrato")
    d_inicio = st.sidebar.date_input("Início", value=date.today() - relativedelta(months=1))
    d_fim = st.sidebar.date_input("Fim", value=date.today())

    # 3. Filtro de Status
    status_opcoes = ["Todos", "Pago", "Pendente"]
    status_sel = st.sidebar.selectbox("Filtrar Status", status_opcoes)

    # 4. Busca por Cliente
    busca_cliente = st.sidebar.text_input("🎯 Buscar Cliente")

    # 5. Filtro de Tipo
    tipos_unicos = ["Todos"] + sorted(df_raw['Tipo'].unique().tolist())
    tipo_sel = st.sidebar.selectbox("Tipo de Lançamento", tipos_unicos)

    # --- APLICAÇÃO DOS FILTROS ---
    df = df_raw.copy()
    
    # Aplicar Vendedor
    df = df[df['Vendedor'].isin(vendedores_sel)]
    
    # Aplicar Data Base
    df = df[(df['Data_Base_DT'] >= d_inicio) & (df['Data_Base_DT'] <= d_fim)]
    
    # Aplicar Status
    if status_sel != "Todos":
        if status_sel == "Pago":
            df = df[df['Status'].astype(str).str.upper().str.strip().isin(['PAGO', 'RECEBIDO', 'ENTRADA', 'À VISTA'])]
        else:
            df = df[~df['Status'].astype(str).str.upper().str.strip().isin(['PAGO', 'RECEBIDO', 'ENTRADA', 'À VISTA'])]

    # Aplicar Busca Cliente
    if busca_cliente:
        df = df[df['Cliente'].str.contains(busca_cliente, case=False, na=False)]

    # Aplicar Tipo
    if tipo_sel != "Todos":
        df = df[df['Tipo'] == tipo_sel]

# --- NAVEGAÇÃO ---
menu = st.sidebar.radio("Navegação", ["📝 Lançar & Gestão", "📊 Relatórios Dinâmicos"])

if menu == "📝 Lançar & Gestão":
    # (Mantém toda a sua lógica de gravação e edição da 10.2 intacta aqui)
    st.info("Utilize as abas para lançar novos contratos ou gerir baixas.")
    # ... código de lançamento/baixas aqui ...

elif menu == "📊 Relatórios Dinâmicos":
    if df.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
    else:
        # Prepara números calculáveis
        df['C_Num'] = df['Comissão'].apply(para_numero_puro)
        df['V_Num'] = df['Valor'].apply(para_numero_puro)
        df['T_Num'] = df['Total'].apply(para_numero_puro)
        
        status_pagos = ['PAGO', 'RECEBIDO', 'ENTRADA', 'À VISTA']
        st_limpo = df['Status'].astype(str).str.upper().str.strip()

        # Métricas Recalculadas
        c_paga = df[st_limpo.isin(status_pagos)]['C_Num'].sum()
        c_pend = df[~st_limpo.isin(status_pagos)]['C_Num'].sum()
        
        # Faturamento Único (Respeitando filtros)
        df_unicos = df.drop_duplicates(subset=['ID_Contrato'])
        f_contratado = df_unicos['T_Num'].sum()
        f_recebido = df[st_limpo.isin(status_pagos)]['V_Num'].sum()
        f_pendente = df[~st_limpo.isin(status_pagos)]['V_Num'].sum()

        st.title("📊 BI de Performance Comercial")
        
        col_pdf, col_csv = st.columns([1,1])
        with col_csv:
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Exportar CSV", data=csv, file_name="relatorio_erp.csv", mime="text/csv")
        with col_pdf:
            try:
                pdf_data = gerar_pdf(df)
                st.download_button("📄 Gerar Relatório PDF", data=pdf_data, file_name="relatorio_erp.pdf", mime="application/pdf")
            except:
                st.error("Erro ao gerar PDF (caracteres especiais).")

        st.markdown("### 💰 Resumo Filtrado")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Contratado", f"R$ {f_contratado:,.2f}")
        m2.metric("Total Recebido", f"R$ {f_recebido:,.2f}")
        m3.metric("Comissão Realizada", f"R$ {c_paga:,.2f}")
        m4.metric("Comissão Pendente", f"R$ {c_pend:,.2f}")

        st.divider()
        st.write("### 📋 Detalhes dos Registros Filtrados")
        st.dataframe(df.sort_values('Data_Base', ascending=False), use_container_width=True)

if st.sidebar.button("🚪 Sair"):
    st.session_state.logado = False
    st.rerun()