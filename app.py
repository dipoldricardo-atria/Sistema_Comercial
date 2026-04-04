import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- CONFIGURAÇÕES MESTRAS ---
st.set_page_config(page_title="ERP COMERCIAL 4.5", layout="wide", page_icon="🚀")

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSc7YHdYRJZ4I92_cvu0xvHvpU9adHmHmY0RKFxm88NcpjppyA/formResponse"
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?output=csv"
URL_USUARIOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?gid=1188945197&single=true&output=csv"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyur81SkxrO0U4q-Qx_BnMqrm0N3ihp-wt7YNEYkOksjjfCNQwx8TDWbbHmPQHNsO5GDg/exec"

IDs = {
    "cliente": "354575898", "vendedor": "1508368855", "tipo": "2051931448",
    "vencimento": "440689882", "valor_parc": "1010209945", "comissao": "1053130357",
    "status": "852082294", "valor_total": "1567666645", "data_base": "1443725489"
}

# Função de carga com Cache-Busting agressivo
def carregar_dados(url):
    # O parâmetro 't' com timestamp atual força o Google a não mandar uma versão de cache
    try: 
        return pd.read_csv(f"{url}&t={int(time.time())}")
    except: 
        return pd.DataFrame()

# --- LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.title("🔐 Login Administrativo")
    df_u = carregar_dados(URL_USUARIOS)
    with st.form("login"):
        user_email = st.text_input("E-mail")
        user_pass = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            if not df_u.empty:
                match = df_u[(df_u['email'].astype(str).str.lower() == user_email.lower().strip()) & (df_u['senha'].astype(str) == str(user_pass))]
                if not match.empty:
                    st.session_state.logado = True
                    st.session_state.info = match.iloc[0].to_dict()
                    st.rerun()
    st.stop()

u = st.session_state.info
df_vendedores = carregar_dados(URL_USUARIOS)
menu = st.sidebar.radio("Navegação", ["📝 Lançar & Gerir", "📊 Relatório Comercial"])

if menu == "📝 Lançar & Gerir":
    st.subheader("📝 Novo Contrato")
    with st.form("venda_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        f_cli = c1.text_input("Nome do Cliente")
        f_data = c2.date_input("Data do Contrato", value=datetime.now(), format="DD/MM/YYYY")
        vendedor_final = st.selectbox("Vendedor", df_vendedores['nome'].tolist()) if u['cargo'] == "Admin" else u['nome']
        f_total = c1.number_input("Valor Total (R$)", min_value=0.0, format="%.2f")
        f_entrada = c2.number_input("Entrada (R$)", min_value=0.0, format="%.2f")
        f_parc = st.number_input("Parcelas", min_value=0, step=1)
        
        if st.form_submit_button("🚀 GRAVAR CONTRATO"):
            def enviar(tipo, valor, venc):
                payload = {
                    f"entry.{IDs['cliente']}": str(f_cli),
                    f"entry.{IDs['vendedor']}": str(vendedor_final),
                    f"entry.{IDs['tipo']}": str(tipo),
                    f"entry.{IDs['vencimento']}": venc.strftime('%Y-%m-%d'),
                    f"entry.{IDs['valor_parc']}": str(round(valor, 2)).replace('.', ','),
                    f"entry.{IDs['comissao']}": str(round(valor * 0.05, 2)).replace('.', ','),
                    f"entry.{IDs['status']}": "Pendente",
                    f"entry.{IDs['valor_total']}": str(round(f_total, 2)).replace('.', ','),
                    f"entry.{IDs['data_base']}": f_data.strftime('%Y-%m-%d')
                }
                return requests.post(FORM_URL, data=payload).status_code

            resul = []
            if f_parc == 0: resul.append(enviar("À Vista", f_total, f_data))
            else:
                if f_entrada > 0: resul.append(enviar("Entrada", f_entrada, f_data))
                v_p = (f_total - f_entrada) / f_parc
                for i in range(int(f_parc)):
                    dv = f_data + relativedelta(months=i+1)
                    resul.append(enviar(f"Parc {i+1}/{int(f_parc)}", v_p, dv))
            
            if all(s == 200 for s in resul):
                st.success("✅ Gravado!")
                time.sleep(2); st.rerun()

    # --- SEÇÃO DE EXCLUSÃO (LIMPEZA AGRESSIVA) ---
    if u['cargo'] == "Admin":
        st.divider()
        st.subheader("🗑️ Gerenciar/Excluir Contratos")
        
        # Recarregar dados especificamente para a lista de exclusão
        df_ex = carregar_dados(CSV_URL)
        
        if not df_ex.empty:
            df_ex.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissão', 'Status', 'Total', 'Data_Base']
            
            # Agrupar para mostrar apenas contratos únicos
            contratos = df_ex.groupby(['Cliente', 'Data_Base', 'Total']).size().reset_index()
            opcoes = [f"{r['Cliente']} | {r['Data_Base']} | R$ {r['Total']}" for i, r in contratos.iterrows()]
            
            selecionado = st.selectbox("Escolha um contrato para REMOVER INTEIRO:", ["Selecione..."] + opcoes, key="del_box")
            
            if selecionado != "Selecione...":
                c_cli, c_data, c_total = selecionado.split(" | ")
                
                # Filtrar as linhas exatas
                linhas_idx = df_ex[(df_ex['Cliente'] == c_cli) & (df_ex['Data_Base'] == c_data)].index.tolist()
                linhas_reais = [i + 2 for i in linhas_idx]
                
                if st.button(f"⚠️ APAGAR CONTRATO ({len(linhas_reais)} lançamentos)", type="primary"):
                    linhas_reverse = sorted(linhas_reais, reverse=True)
                    
                    with st.spinner("Limpando base de dados..."):
                        for l in linhas_reverse:
                            requests.get(f"{SCRIPT_URL}?row={l}&action=delete")
                    
                    st.error("Contrato Removido!")
                    # Delay maior para o Google processar a exclusão física do arquivo
                    time.sleep(3) 
                    st.rerun()

elif menu == "📊 Relatório Comercial":
    st.subheader("📊 Relatório Comercial")
    df = carregar_dados(CSV_URL)
    if not df.empty:
        df.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissão', 'Status', 'Total', 'Data_Base']
        if u['cargo'] != "Admin": df = df[df['Vendedor'] == u['nome']]
        # Formatação visual para o relatório
        df['Vencimento'] = pd.to_datetime(df['Vencimento']).dt.strftime('%d/%m/%Y')
        df['Data_Base'] = pd.to_datetime(df['Data_Base']).dt.strftime('%d/%m/%Y')
        st.dataframe(df.sort_values('TS', ascending=False), use_container_width=True)