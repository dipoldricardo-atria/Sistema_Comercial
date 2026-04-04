import streamlit as st
import pandas as pd
import requests
import time
import re
import plotly.express as px # Biblioteca para gráficos profissionais
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="ERP 12.0 VISION", layout="wide", page_icon="📊")

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
meta_mensal = st.sidebar.number_input("Definir Meta de Vendas (R$)", min_value=0.0, value=100000.0, step=5000.0)

st.sidebar.divider()
st.sidebar.header("🔍 Filtros de Busca")
df_raw = carregar_dados_realtime()

if not df_raw.empty:
    vendedores_lista = sorted(df_raw['Vendedor'].unique().tolist())
    vendedores_sel = st.sidebar.multiselect("Vendedores", vendedores_lista, default=vendedores_lista) if cargo == "Admin" else [nome_user]
    
    hoje = date.today()
    data_inicio = st.sidebar.date_input("Início", hoje - relativedelta(months=3)) # Aumentei pra 3 meses para os gráficos ficarem melhores
    data_fim = st.sidebar.date_input("Fim", hoje)

    status_filtro = st.sidebar.selectbox("Status", ["Todos", "Pago", "Pendente"])
    busca_cliente = st.sidebar.text_input("🎯 Cliente")

    # APLICAÇÃO FILTROS
    df = df_raw.copy()
    df = df[df['Vendedor'].isin(vendedores_sel)]
    df = df[(df['Data_Base_DT'] >= data_inicio) & (df['Data_Base_DT'] <= data_fim)]
    
    if status_filtro != "Todos":
        pgs = ['PAGO', 'RECEBIDO', 'ENTRADA', 'À VISTA']
        st_l = df['Status'].astype(str).str.upper().str.strip()
        df = df[st_l.isin(pgs)] if status_filtro == "Pago" else df[~st_l.isin(pgs)]
    
    if busca_cliente:
        df = df[df['Cliente'].str.contains(busca_cliente, case=False, na=False)]

# --- NAVEGAÇÃO ---
if st.sidebar.button("🚪 Sair"):
    st.session_state.logado = False
    st.rerun()

menu = st.sidebar.radio("Navegação", ["📝 Lançar & Gestão", "📊 Dashboard Analytics"])

# --- LÓGICA DE GRAVAÇÃO (MANTIDA INTEGRALMENTE DO CHECKPOINT 11.3) ---
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
            f_data = c2.date_input("Data do Contrato (Base)", format="DD/MM/YYYY")
            v_sel = st.selectbox("Vendedor", vendedores_lista if cargo == "Admin" else [nome_user])
            f_tot = c1.number_input("Valor Total (R$)", min_value=0.0)
            f_ent = c2.number_input("Entrada (R$)", min_value=0.0)
            f_pa = st.number_input("Parcelas", min_value=0, step=1)
            if st.form_submit_button("🚀 GRAVAR CONTRATO"):
                if f_cli and f_tot > 0:
                    executar_gravacao(f_cli, v_sel, f_data, f_tot, f_ent, f_pa, f"ID{int(time.time())}")
                    st.success("✅ Gravado com Sucesso!"); time.sleep(1); st.rerun()

    # (Tabs de Baixa e Edição mantidas iguais ao Checkpoint 11.3)
    with tabs[1]:
        st.subheader("💸 Recebimento")
        if not df_raw.empty:
            pendentes = df_raw[~df_raw['Status'].astype(str).str.upper().str.strip().isin(['PAGO', 'RECEBIDO'])]
            if cargo != "Admin": pendentes = pendentes[pendentes['Vendedor'] == nome_user]
            if not pendentes.empty:
                for i, row in pendentes.iterrows():
                    with st.expander(f"📌 {row['Cliente']} | {row['Tipo']} | R$ {row['Valor']}"):
                        if st.button(f"Confirmar Pagamento", key=f"bx_{i}"):
                            requests.get(SCRIPT_URL, params={"action": "marcarPago", "ts": str(row['TS']), "cliente": str(row['Cliente']), "valor": str(row['Valor'])})
                            st.rerun()
            else: st.info("Sem pendências.")

    with tabs[2]:
        if cargo != "Admin": st.warning("Restrito."); st.stop()
        if not df_raw.empty:
            contratos = df_raw[df_raw['ID_Contrato'].astype(str).str.startswith("ID")].groupby(['ID_Contrato', 'Cliente', 'Total', 'Vendedor', 'Data_Base']).size().reset_index()
            opcoes = {f"{r['ID_Contrato']} | {r['Cliente']}": r for i, r in contratos.iterrows()}
            sel = st.selectbox("Editar/Apagar:", ["Selecione..."] + list(opcoes.keys()))
            if sel != "Selecione...":
                dados = opcoes[sel]
                with st.form("edicao"):
                    e_cli = st.text_input("Cliente", value=dados['Cliente'])
                    e_data = st.date_input("Data Base", value=pd.to_datetime(dados['Data_Base']).date())
                    e_vend = st.selectbox("Vendedor", vendedores_lista, index=vendedores_lista.index(dados['Vendedor']) if dados['Vendedor'] in vendedores_lista else 0)
                    e_tot = st.number_input("Total", value=para_numero_puro(dados['Total']))
                    if st.form_submit_button("✅ SALVAR"):
                        requests.get(SCRIPT_URL, params={"id_contrato": dados['ID_Contrato'], "action": "deleteContrato"})
                        executar_gravacao(e_cli, e_vend, e_data, e_tot, 0, 0, dados['ID_Contrato'])
                        st.rerun()
                if st.button("🔥 EXCLUIR", type="primary"):
                    requests.get(SCRIPT_URL, params={"id_contrato": dados['ID_Contrato'], "action": "deleteContrato"})
                    st.rerun()

elif menu == "📊 Dashboard Analytics":
    if not df.empty:
        df['V_Num'] = df['Valor'].apply(para_numero_puro)
        df['T_Num'] = df['Total'].apply(para_numero_puro)
        df_unicos = df.drop_duplicates(subset=['ID_Contrato'])
        
        total_contratado = df_unicos['T_Num'].sum()
        atingimento = (total_contratado / meta_mensal * 100) if meta_mensal > 0 else 0
        
        st.title("🚀 Business Intelligence")
        
        # --- LINHA 1: MÉTRICAS E META ---
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Faturamento Filtrado", f"R$ {total_contratado:,.2f}")
        c2.metric("Meta Definida", f"R$ {meta_mensal:,.2f}")
        c3.metric("Atingimento de Meta", f"{atingimento:.1f}%")
        c4.progress(min(atingimento/100, 1.0), text=f"Progresso: {atingimento:.1f}%")

        st.divider()

        # --- LINHA 2: GRÁFICOS ---
        g1, g2 = st.columns([2, 1])

        with g1:
            st.subheader("📅 Evolução Mensal (Data Base)")
            df_vendas_mes = df_unicos.groupby('Mes_Ano')['T_Num'].sum().reset_index()
            fig_evol = px.line(df_vendas_mes, x='Mes_Ano', y='T_Num', markers=True, 
                               labels={'T_Num': 'Total Contratado (R$)', 'Mes_Ano': 'Mês de Referência'},
                               color_discrete_sequence=['#00CC96'])
            st.plotly_chart(fig_evol, use_container_width=True)

        with g2:
            st.subheader("👥 Share por Vendedor")
            fig_pizza = px.pie(df_unicos, values='T_Num', names='Vendedor', hole=.4)
            st.plotly_chart(fig_pizza, use_container_width=True)

        st.divider()

        # --- LINHA 3: SAÚDE FINANCEIRA ---
        st.subheader("🏦 Saúde dos Recebimentos")
        df_status = df.groupby('Status')['V_Num'].sum().reset_index()
        fig_status = px.bar(df_status, x='Status', y='V_Num', color='Status', 
                            labels={'V_Num': 'Valor (R$)'}, text_auto='.2s')
        st.plotly_chart(fig_status, use_container_width=True)

        # Exportação rápida
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Baixar Base Filtrada (CSV)", data=csv, file_name="bi_export.csv", mime="text/csv")
        
    else:
        st.warning("Sem dados para gerar gráficos com os filtros atuais.")