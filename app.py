import streamlit as st
import pandas as pd
import requests
import time
import re
import io
import plotly.express as px
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# Bibliotecas para o PDF (ReportLab)
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

st.set_page_config(page_title="ERP 14.7 FINAL", layout="wide", page_icon="📊")

# --- CONFIGURAÇÕES ---
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyJiJlQIZeqvt3P09trAdfMecjutOFGVE1jsxPmcdh05nn2cKapdzVnJp8ASmIxCYfLQQ/exec"
URL_USUARIOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?gid=1188945197&single=true&output=csv"

if 'logado' not in st.session_state: st.session_state.logado = False

def para_numero_puro(valor):
    if pd.isna(valor) or str(valor).strip() == "": return 0.0
    texto = re.sub(r'[^\d.,-]', '', str(valor))
    if not texto: return 0.0
    if ',' in texto and '.' in texto: texto = texto.replace('.', '').replace(',', '.')
    elif ',' in texto: texto = texto.replace(',', '.')
    try: return float(texto)
    except: return 0.0

def carregar_dados_realtime():
    try:
        r = requests.get(f"{SCRIPT_URL}?action=read&t={int(time.time())}", timeout=25)
        data = r.json()
        if len(data) <= 1: return pd.DataFrame()
        df = pd.DataFrame(data[1:], columns=['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissão', 'Status', 'Total', 'Data_Base', 'ID_Contrato'])
        df['Data_Base_DT'] = pd.to_datetime(df['Data_Base'], errors='coerce').dt.date
        df['Mes_Ano'] = pd.to_datetime(df['Data_Base'], errors='coerce').dt.strftime('%Y-%m')
        return df
    except: return pd.DataFrame()

# --- MOTOR DE PDF ---
def gerar_pdf_espelho(df_filtrado, metrics, period):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=25)
    elements = []
    styles = getSampleStyleSheet()
    cor_primaria = colors.HexColor("#1f4e79")
    cor_fundo = colors.HexColor("#f2f2f2")
    style_title = ParagraphStyle(name='TitleBR', parent=styles['Title'], fontSize=16, spaceAfter=15)
    style_h2 = ParagraphStyle(name='H2', parent=styles['Heading2'], fontSize=12, spaceBefore=10, spaceAfter=8, textColor=cor_primaria)

    elements.append(Paragraph(f"<b>RELATÓRIO DE DESEMPENHO COMERCIAL</b>", style_title))
    elements.append(Paragraph(f"<b>Período:</b> {period['inicio']} a {period['fim']} | <b>Emissão:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 15))

    elements.append(Paragraph("1. RESUMO FINANCEIRO", style_h2))
    m_data = [["TOTAL CONTRATADO", "ATINGIMENTO META", "JÁ EM CAIXA", "SALDO A RECEBER"],
              [metrics.get('total', '0'), metrics.get('atingimento', '0'), metrics.get('caixa', '0'), metrics.get('saldo', '0')]]
    tm = Table(m_data, colWidths=[135, 135, 135, 135])
    tm.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), cor_fundo), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,-1), 9)]))
    elements.append(tm)
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("2. SAÚDE DOS RECEBIMENTOS (POR STATUS)", style_h2))
    df_filtrado['V_Num'] = df_filtrado['Valor'].apply(para_numero_puro)
    status_df = df_filtrado.groupby('Status')['V_Num'].sum().reset_index()
    s_data = [["Status do Lançamento", "Valor Acumulado"]]
    for _, r in status_df.iterrows(): s_data.append([str(r['Status']), f"R$ {r['V_Num']:,.2f}"])
    ts = Table(s_data, colWidths=[270, 270])
    ts.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), cor_primaria), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke), ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('ALIGN', (1,0), (1,-1), 'RIGHT')]))
    elements.append(ts)
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("3. DETALHAMENTO DE CONTRATOS E PARCIAIS", style_h2))
    d_data = [["Cliente", "Tipo/Parc", "Vencimento", "Valor", "Status"]]
    df_sorted = df_filtrado.sort_values(['Data_Base', 'Cliente'], ascending=[False, True])
    for _, row in df_sorted.iterrows():
        d_data.append([str(row['Cliente'])[:25], str(row['Tipo']), pd.to_datetime(row['Vencimento']).strftime('%d/%m/%Y'), f"R$ {para_numero_puro(row['Valor']):,.2f}", str(row['Status'])])
    td = Table(d_data, repeatRows=1, colWidths=[160, 100, 80, 100, 100])
    td.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.grey), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke), ('FONTSIZE', (0,0), (-1,-1), 8), ('GRID', (0,0), (-1,-1), 0.2, colors.black), ('ROWBACKGROUNDS', (0, 1), (-1, -1), [cor_fundo, colors.white]), ('ALIGN', (3,1), (3,-1), 'RIGHT')]))
    elements.append(td)
    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- FUNÇÃO DE EXPORTAÇÃO CSV ---
def converter_para_csv(df):
    return df.to_csv(index=False, sep=';', encoding='utf-8-sig')

def executar_gravacao(f_cli, f_vendedor, f_data, f_total, f_entrada, f_parc, id_final):
    def enviar(tipo, venc, valor):
        comis_calc = valor * 0.05
        params = {"action": "create", "cliente": f_cli, "vendedor": f_vendedor, "tipo": tipo, "vencimento": venc.strftime('%Y-%m-%d'), "valor": round(valor, 2), "comissao": round(comis_calc, 2), "status": "Pendente", "total": f_total, "data_base": f_data.strftime('%Y-%m-%d'), "id_contrato": id_final}
        requests.get(SCRIPT_URL, params=params)
    if f_entrada > 0: enviar("Entrada", f_data, f_entrada)
    restante = f_total - f_entrada
    if f_parc > 0 and restante > 0:
        v_p = restante / f_parc
        for i in range(int(f_parc)): enviar(f"Parc {i+1}", f_data + relativedelta(months=i+1), v_p)
    elif f_parc == 0 and f_entrada == 0: enviar("À Vista", f_data, f_total)

# --- LOGIN ---
if not st.session_state.logado:
    st.title("🔐 Login Master")
    with st.form("login"):
        u_e = st.text_input("E-mail"); u_s = st.text_input("Senha", type="password")
        if st.form_submit_button("Acessar"):
            df_u = pd.read_csv(URL_USUARIOS)
            df_u.columns = [c.lower().strip() for c in df_u.columns]
            match = df_u[(df_u['email'].str.lower() == u_e.lower().strip()) & (df_u['senha'].astype(str) == u_s)]
            if not match.empty:
                st.session_state.logado = True; st.session_state.usuario = match.iloc[0].to_dict(); st.rerun()
    st.stop()

u = st.session_state.usuario
cargo = u.get('cargo') or u.get('Cargo') or "Consultor"
nome_user = u.get('nome') or u.get('Nome') or "Usuário"

# --- INICIALIZAÇÃO ---
df_raw = carregar_dados_realtime()
vendedores_lista = sorted(df_raw['Vendedor'].unique().tolist()) if not df_raw.empty else [nome_user]

# --- SIDEBAR ---
st.sidebar.header("🎯 Gestão & Metas")
meta_mensal = st.sidebar.number_input("Meta Mensal (R$)", min_value=0.0, value=100000.0)
st.sidebar.divider()

if not df_raw.empty:
    vendedores_sel = st.sidebar.multiselect("Vendedores", vendedores_lista, default=vendedores_lista) if cargo == "Admin" else [nome_user]
    hoje = date.today()
    data_inicio = st.sidebar.date_input("Início", value=hoje - relativedelta(months=1), format="DD/MM/YYYY")
    data_fim = st.sidebar.date_input("Fim", value=hoje, format="DD/MM/YYYY")
    status_filtro = st.sidebar.selectbox("Status", ["Todos", "Pago", "Pendente"])
    busca_cliente = st.sidebar.selectbox("🎯 Cliente", options=["Todos"] + sorted(df_raw['Cliente'].unique().tolist()))

    df = df_raw.copy()
    df = df[df['Vendedor'].isin(vendedores_sel)]
    df = df[(df['Data_Base_DT'] >= data_inicio) & (df['Data_Base_DT'] <= data_fim)]
    if status_filtro != "Todos":
        pgs = ['PAGO', 'RECEBIDO', 'ENTRADA', 'À VISTA']; st_l = df['Status'].astype(str).str.upper().str.strip()
        df = df[st_l.isin(pgs)] if status_filtro == "Pago" else df[~st_l.isin(pgs)]
    if busca_cliente != "Todos": df = df[df['Cliente'] == busca_cliente]
else:
    df = pd.DataFrame()

menu = st.sidebar.radio("Navegação", ["📝 Lançar & Gestão", "📊 Dashboard Analytics"])

if menu == "📊 Dashboard Analytics":
    if not df.empty:
        df['V_Num'] = df['Valor'].apply(para_numero_puro)
        df['T_Num'] = df['Total'].apply(para_numero_puro)
        df_unicos = df.drop_duplicates(subset=['ID_Contrato'])
        t_contratado = df_unicos['T_Num'].sum()
        atingimento = (t_contratado / meta_mensal * 100) if meta_mensal > 0 else 0
        pgs = ['PAGO', 'RECEBIDO', 'ENTRADA', 'À VISTA']; st_l = df['Status'].astype(str).str.upper().str.strip()
        v_recebido = df[st_l.isin(pgs)]['V_Num'].sum()
        
        st.title("🚀 Business Intelligence Executivo")
        
        res_metrics = {"total": f"R$ {t_contratado:,.2f}", "atingimento": f"{atingimento:.1f}%", "caixa": f"R$ {v_recebido:,.2f}", "saldo": f"R$ {t_contratado - v_recebido:,.2f}"}
        periodo = {"inicio": data_inicio.strftime('%d/%m/%Y'), "fim": data_fim.strftime('%d/%m/%Y')}
        
        # BOTÕES DE EXPORTAÇÃO
        c_pdf, c_csv = st.columns(2)
        with c_pdf:
            st.download_button("📄 BAIXAR RELATÓRIO PDF", data=gerar_pdf_espelho(df, res_metrics, periodo), file_name=f"Fechamento_{date.today()}.pdf", mime="application/pdf", use_container_width=True)
        with c_csv:
            csv_data = converter_para_csv(df)
            st.download_button("📂 EXPORTAR PARA EXCEL (CSV)", data=csv_data, file_name=f"Dados_ERP_{date.today()}.csv", mime="text/csv", use_container_width=True)

        st.divider()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Contratado", res_metrics['total'])
        c2.metric("Atingimento Meta", res_metrics['atingimento'])
        c3.metric("Já em Caixa", res_metrics['caixa'])
        c4.metric("Saldo a Receber", res_metrics['saldo'])
        
        st.divider()
        g1, g2 = st.columns([2, 1])
        with g1:
            st.subheader("📅 Evolução Mensal")
            st.plotly_chart(px.line(df_unicos.groupby('Mes_Ano')['T_Num'].sum().reset_index(), x='Mes_Ano', y='T_Num', markers=True), use_container_width=True)
        with g2:
            st.subheader("👥 Share Vendedores")
            st.plotly_chart(px.pie(df_unicos, values='T_Num', names='Vendedor', hole=.4), use_container_width=True)

        st.subheader("🏦 Saúde dos Recebimentos")
        st.plotly_chart(px.bar(df.groupby('Status')['V_Num'].sum().reset_index(), x='Status', y='V_Num', color='Status', text_auto='.2s'), use_container_width=True)

        st.subheader("📋 Detalhamento das Operações")
        st.dataframe(df.sort_values('Data_Base', ascending=False), use_container_width=True)
    else:
        st.warning("Sem dados para os filtros selecionados.")

elif menu == "📝 Lançar & Gestão":
    tabs = st.tabs(["🆕 Novo Lançamento", "💰 Dar Baixa (Financeiro)", "✏️ Gestão Admin"])
    with tabs[0]:
        with st.form("novo_venda", clear_on_submit=True):
            c1, c2 = st.columns(2)
            f_cli = c1.text_input("Nome do Cliente")
            f_data = c2.date_input("Data do Contrato", format="DD/MM/YYYY")
            v_sel = st.selectbox("Vendedor", vendedores_lista)
            f_tot = c1.number_input("Valor Total", min_value=0.0)
            f_ent = c2.number_input("Entrada", min_value=0.0)
            f_pa = st.number_input("Parcelas", min_value=0, step=1)
            if st.form_submit_button("🚀 GRAVAR CONTRATO"):
                if f_cli and f_tot > 0:
                    executar_gravacao(f_cli, v_sel, f_data, f_tot, f_ent, f_pa, f"ID{int(time.time())}")
                    st.success("✅ Gravado com Sucesso!"); time.sleep(1); st.rerun()

    with tabs[1]:
        st.subheader("💸 Dar Baixa em Pagamentos")
        if not df_raw.empty:
            pendentes = df_raw[~df_raw['Status'].astype(str).str.upper().str.strip().isin(['PAGO', 'RECEBIDO'])]
            if cargo != "Admin": pendentes = pendentes[pendentes['Vendedor'] == nome_user]
            for i, row in pendentes.iterrows():
                with st.expander(f"📌 {row['Cliente']} | {row['Tipo']} | R$ {row['Valor']}"):
                    if st.button("Confirmar Pagamento", key=f"bx_{i}"):
                        requests.get(SCRIPT_URL, params={"action": "marcarPago", "ts": str(row['TS']), "cliente": str(row['Cliente']), "valor": str(row['Valor'])})
                        st.success("Baixa realizada!"); time.sleep(0.5); st.rerun()

    with tabs[2]:
        if cargo == "Admin":
            st.subheader("✏️ Administração de Contratos")
            if not df_raw.empty:
                contratos = df_raw[df_raw['ID_Contrato'].astype(str).str.startswith("ID")].groupby(['ID_Contrato', 'Cliente', 'Total']).size().reset_index()
                sel = st.selectbox("Selecione para Excluir:", ["Selecione..."] + [f"{r['ID_Contrato']} | {r['Cliente']}" for i, r in contratos.iterrows()])
                if sel != "Selecione..." and st.button("🔥 EXCLUIR CONTRATO", type="primary"):
                    id_excluir = sel.split(" | ")[0]
                    requests.get(SCRIPT_URL, params={"id_contrato": id_excluir, "action": "deleteContrato"})
                    st.warning("Excluído!"); time.sleep(1); st.rerun()
        else:
            st.error("Acesso restrito.")