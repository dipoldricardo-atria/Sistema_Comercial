import streamlit as st
import pandas as pd
import requests
import time
import re
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="ERP 11.3 BI FLOW", layout="wide", page_icon="📈")

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
        # AQUI ESTÁ A CHAVE: Transformamos a Data_Base em objeto de data para o filtro funcionar
        df['Data_Base_DT'] = pd.to_datetime(df['Data_Base'], errors='coerce').dt.date
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

# --- FILTROS SIDEBAR (BASEADOS NA DATA DE FECHAMENTO) ---
st.sidebar.header("🔍 Filtros Dinâmicos")
df_raw = carregar_dados_realtime()

if not df_raw.empty:
    # 1. Filtro de Vendedores
    vendedores_lista = sorted(df_raw['Vendedor'].unique().tolist())
    vendedores_sel = st.sidebar.multiselect("Vendedores", vendedores_lista, default=vendedores_lista) if cargo == "Admin" else [nome_user]
    
    # 2. Filtro de Período (DATA BASE DO CONTRATO)
    hoje = date.today()
    st.sidebar.subheader("📅 Data de Fechamento")
    data_inicio = st.sidebar.date_input("Início", hoje - relativedelta(months=1))
    data_fim = st.sidebar.date_input("Fim", hoje)

    # 3. Status e Busca
    status_filtro = st.sidebar.selectbox("Status Geral", ["Todos", "Apenas Pagos", "Apenas Pendentes"])
    busca_cliente = st.sidebar.text_input("🎯 Buscar Cliente")

    # --- APLICAÇÃO DOS FILTROS ---
    df = df_raw.copy()
    df = df[df['Vendedor'].isin(vendedores_sel)]
    # Filtro aplicado estritamente sobre a Data_Base
    df = df[(df['Data_Base_DT'] >= data_inicio) & (df['Data_Base_DT'] <= data_fim)]
    
    if status_filtro != "Todos":
        pgs = ['PAGO', 'RECEBIDO', 'ENTRADA', 'À VISTA']
        st_l = df['Status'].astype(str).str.upper().str.strip()
        df = df[st_l.isin(pgs)] if status_filtro == "Apenas Pagos" else df[~st_l.isin(pgs)]
    
    if busca_cliente:
        df = df[df['Cliente'].str.contains(busca_cliente, case=False, na=False)]

# --- NAVEGAÇÃO ---
if st.sidebar.button("🚪 Sair"):
    st.session_state.logado = False
    st.rerun()

menu = st.sidebar.radio("Navegação", ["📝 Lançar & Gestão", "📊 Relatórios Dinâmicos"])

# --- MOTOR DE GRAVAÇÃO (SEM ALTERAÇÃO NA LÓGICA) ---
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
                    e_vend = st.selectbox("Vendedor", lista_vendedores, index=lista_vendedores.index(dados['Vendedor']) if dados['Vendedor'] in lista_vendedores else 0)
                    e_tot = st.number_input("Total", value=para_numero_puro(dados['Total']))
                    if st.form_submit_button("✅ SALVAR"):
                        requests.get(SCRIPT_URL, params={"id_contrato": dados['ID_Contrato'], "action": "deleteContrato"})
                        executar_gravacao(e_cli, e_vend, e_data, e_tot, 0, 0, dados['ID_Contrato'])
                        st.rerun()
                if st.button("🔥 EXCLUIR", type="primary"):
                    requests.get(SCRIPT_URL, params={"id_contrato": dados['ID_Contrato'], "action": "deleteContrato"})
                    st.rerun()

elif menu == "📊 Relatórios Dinâmicos":
    if not df.empty:
        df['C_Num'] = df['Comissão'].apply(para_numero_puro)
        df['V_Num'] = df['Valor'].apply(para_numero_puro)
        df['T_Num'] = df['Total'].apply(para_numero_puro)
        
        st_l = df['Status'].astype(str).str.upper().str.strip()
        pgs = ['PAGO', 'RECEBIDO', 'ENTRADA', 'À VISTA']
        
        c_paga = df[st_l.isin(pgs)]['C_Num'].sum()
        c_pend = df[~st_l.isin(pgs)]['C_Num'].sum()
        df_u = df.drop_duplicates(subset=['ID_Contrato'])
        f_cont = df_u['T_Num'].sum()
        f_rec = df[st_l.isin(pgs)]['V_Num'].sum()

        st.title("📊 BI Performance Comercial")
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Exportar Dados Filtrados (CSV)", data=csv, file_name=f"vendas_{data_inicio}.csv", mime="text/csv")

        st.subheader(f"💰 Resumo de {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}")
        m1, m2, m3 = st.columns(3)
        m1.metric("Comissões Pagas", f"R$ {c_paga:,.2f}")
        m2.metric("Comissões A Receber", f"R$ {c_pend:,.2f}")
        m3.metric("Faturamento Contratado", f"R$ {f_cont:,.2f}")

        st.divider()
        st.subheader("🏢 Faturamento de Projetos")
        f1, f2, f3 = st.columns(3)
        f1.metric("Total já Recebido", f"R$ {f_rec:,.2f}")
        f2.metric("Saldo em Aberto", f"R$ {f_cont - f_rec:,.2f}")
        f3.metric("Conversão (Recebido %)", f"{ (f_rec/f_cont*100) if f_cont > 0 else 0:.1f}%")

        st.divider()
        st.write("### 📋 Listagem de Contratos no Período")
        st.dataframe(df.sort_values('Data_Base', ascending=False), use_container_width=True)
    else:
        st.warning("Nenhum contrato encontrado para o período de fechamento selecionado.")