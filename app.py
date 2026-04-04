import streamlit as st
import pandas as pd
import requests
import time
import re
import io
import plotly.express as px
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# Bibliotecas para o PDF (Adicione 'reportlab' no seu requirements.txt)
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(page_title="ERP 13.1 FULL VISION", layout="wide", page_icon="📊")

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
        df['Data_Base_DT'] = pd.to_datetime(df['Data_Base'], errors='coerce').dt.date
        df['Mes_Ano'] = pd.to_datetime(df['Data_Base'], errors='coerce').dt.strftime('%Y-%m')
        return df
    except: return pd.DataFrame()

# --- MOTOR DE PDF ---
def gerar_pdf(df_filtrado, resumo_financeiro):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph(f"<b>RELATÓRIO COMERCIAL EXECUTIVO</b>", styles['Title']))
    elements.append(Paragraph(f"Emissão: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 15))
    elements.append(Paragraph(f"<b>RESUMO EXECUTIVO</b>", styles['Heading2']))
    for k, v in resumo_financeiro.items():
        elements.append(Paragraph(f"{k}: {v}", styles['Normal']))
    elements.append(Spacer(1, 20))
    data = [["Cliente", "Vencimento", "Valor", "Status"]]
    for _, row in df_filtrado.iterrows():
        data.append([str(row['Cliente'])[:25], pd.to_datetime(row['Vencimento']).strftime('%d/%m/%Y'), f"R$ {para_numero_puro(row['Valor']):,.2f}", str(row['Status'])])
    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke), ('FONTSIZE', (0, 0), (-1, -1), 8), ('GRID', (0, 0), (-1, -1), 0.5, colors.black)]))
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    return buffer

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

# --- FILTROS SIDEBAR ---
st.sidebar.header("🎯 Gestão & Metas")
meta_mensal = st.sidebar.number_input("Meta de Vendas (R$)", min_value=0.0, value=100000.0)
st.sidebar.divider()
df_raw = carregar_dados_realtime()

if not df_raw.empty:
    vendedores_lista = sorted(df_raw['Vendedor'].unique().tolist())
    vendedores_sel = st.sidebar.multiselect("Vendedores", vendedores_lista, default=vendedores_lista) if cargo == "Admin" else [nome_user]
    hoje = date.today()
    data_inicio = st.sidebar.date_input("Início", value=hoje - relativedelta(months=3), format="DD/MM/YYYY")
    data_fim = st.sidebar.date_input("Fim", value=hoje, format="DD/MM/YYYY")
    status_filtro = st.sidebar.selectbox("Status", ["Todos", "Pago", "Pendente"])
    lista_clientes_base = ["Todos"] + sorted(df_raw['Cliente'].unique().tolist())
    busca_cliente = st.sidebar.selectbox("🎯 Cliente", options=lista_clientes_base)

    df = df_raw.copy()
    df = df[df['Vendedor'].isin(vendedores_sel)]
    df = df[(df['Data_Base_DT'] >= data_inicio) & (df['Data_Base_DT'] <= data_fim)]
    if status_filtro != "Todos":
        pgs = ['PAGO', 'RECEBIDO', 'ENTRADA', 'À VISTA']; st_l = df['Status'].astype(str).str.upper().str.strip()
        df = df[st_l.isin(pgs)] if status_filtro == "Pago" else df[~st_l.isin(pgs)]
    if busca_cliente != "Todos": df = df[df['Cliente'] == busca_cliente]

# --- NAVEGAÇÃO ---
if st.sidebar.button("🚪 Sair"): st.session_state.logado = False; st.rerun()
menu = st.sidebar.radio("Navegação", ["📝 Lançar & Gestão", "📊 Dashboard Analytics"])

# --- MOTOR DE GRAVAÇÃO (INTACTO) ---
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

# --- TELAS ---
if menu == "📝 Lançar & Gestão":
    tabs = st.tabs(["🆕 Novo Lançamento", "💰 Dar Baixa", "✏️ Gestão Admin"])
    # (Logica das Tabs mantida igual ao Checkpoint 12.2)
    with tabs[0]:
        with st.form("novo_venda", clear_on_submit=True):
            c1, c2 = st.columns(2); f_cli = c1.text_input("Cliente"); f_data = c2.date_input("Data Base", format="DD/MM/YYYY")
            v_sel = st.selectbox("Vendedor", vendedores_lista if cargo == "Admin" else [nome_user])
            f_tot = c1.number_input("Total", min_value=0.0); f_ent = c2.number_input("Entrada", min_value=0.0); f_pa = st.number_input("Parcelas", min_value=0)
            if st.form_submit_button("🚀 GRAVAR"): executar_gravacao(f_cli, v_sel, f_data, f_tot, f_ent, f_pa, f"ID{int(time.time())}"); st.rerun()
    with tabs[1]:
        if not df_raw.empty:
            pendentes = df_raw[~df_raw['Status'].astype(str).str.upper().str.strip().isin(['PAGO', 'RECEBIDO'])]
            for i, row in pendentes.iterrows():
                with st.expander(f"{row['Cliente']} | {row['Tipo']} | R$ {row['Valor']}"):
                    if st.button("Confirmar Pagamento", key=f"bx_{i}"): requests.get(SCRIPT_URL, params={"action": "marcarPago", "ts": str(row['TS']), "cliente": str(row['Cliente']), "valor": str(row['Valor'])}); st.rerun()

elif menu == "📊 Dashboard Analytics":
    if not df.empty:
        df['V_Num'] = df['Valor'].apply(para_numero_puro); df['T_Num'] = df['Total'].apply(para_numero_puro)
        df_unicos = df.drop_duplicates(subset=['ID_Contrato'])
        total_contratado = df_unicos['T_Num'].sum(); atingimento = (total_contratado / meta_mensal * 100) if meta_mensal > 0 else 0
        
        st.title("🚀 Business Intelligence Executivo")
        
        # Botões de Exportação
        c1, c2 = st.columns(2)
        with c1: st.download_button("📥 Exportar CSV", data=df.to_csv(index=False).encode('utf-8'), file_name="bi_dados.csv", mime="text/csv", use_container_width=True)
        with c2:
            res_pdf = {"Faturamento": f"R$ {total_contratado:,.2f}", "Meta": f"R$ {meta_mensal:,.2f}", "Atingimento": f"{atingimento:.1f}%", "Vendedor(es)": ", ".join(vendedores_sel)}
            st.download_button("📄 Baixar Relatório PDF", data=gerar_pdf(df, res_pdf), file_name=f"Relatorio_{date.today()}.pdf", mime="application/pdf", use_container_width=True)

        st.divider()
        # --- MÉTRICAS DE TOPO ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Contratado", f"R$ {total_contratado:,.2f}")
        m2.metric("Atingimento Meta", f"{atingimento:.1f}%")
        
        # Lógica de Recebidos vs Saldo (Recuperada da 12.2)
        pgs = ['PAGO', 'RECEBIDO', 'ENTRADA', 'À VISTA']; st_l = df['Status'].astype(str).str.upper().str.strip()
        valor_recebido = df[st_l.isin(pgs)]['V_Num'].sum()
        m3.metric("Já em Caixa", f"R$ {valor_recebido:,.2f}")
        m4.metric("Saldo a Receber", f"R$ {total_contratado - valor_recebido:,.2f}")
        st.progress(min(atingimento/100, 1.0))

        st.divider()
        # --- GRÁFICOS ---
        g1, g2 = st.columns([2, 1])
        with g1:
            st.subheader("📅 Evolução Mensal")
            st.plotly_chart(px.line(df_unicos.groupby('Mes_Ano')['T_Num'].sum().reset_index(), x='Mes_Ano', y='T_Num', markers=True, color_discrete_sequence=['#00CC96']), use_container_width=True)
        with g2:
            st.subheader("👥 Share Vendedores")
            st.plotly_chart(px.pie(df_unicos, values='T_Num', names='Vendedor', hole=.4), use_container_width=True)

        st.divider()
        # --- GRÁFICO DE SAÚDE FINANCEIRA (RECUPERADO) ---
        st.subheader("🏦 Saúde dos Recebimentos (Status)")
        df_status = df.groupby('Status')['V_Num'].sum().reset_index()
        st.plotly_chart(px.bar(df_status, x='Status', y='V_Num', color='Status', text_auto='.2s', labels={'V_Num': 'Valor Acumulado (R$)'}), use_container_width=True)

        st.divider()
        st.subheader("📋 Detalhamento do Período")
        st.dataframe(df.sort_values('Data_Base', ascending=False), use_container_width=True)
    else:
        st.warning("Sem dados para os filtros selecionados.")