import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. CONFIGURAÇÕES MESTRAS (TOTALMENTE CONFIGURADO) ---
st.set_page_config(page_title="ERP COMERCIAL PRO 2.0", layout="wide", page_icon="🚀")

# LINKS DA ESTRUTURA NOVA
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSc7YHdYRJZ4I92_cvu0xvHvpU9adHmHmY0RKFxm88NcpjppyA/formResponse"
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?output=csv"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzOSS05oMHIdC5mjafWE1XL8oQnaDIdUyQQ3rssrIIxu0tfdGxFZ2VHrErZ3lAliKJBzw/exec"

# ABA DE USUÁRIOS (VENDEDORES)
URL_USUARIOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?gid=1188945197&single=true&output=csv"

# IDs DO FORMULÁRIO (MAPEADOS)
IDs_FORM = {
    "cliente": "354575898", "vendedor": "1508368855", "tipo": "2051931448",
    "vencimento": "440689882", "valor_parc": "1010209945", "comissao": "1053130357",
    "status": "852082294", "valor_total": "1567666645", "data_base": "1443725489"
}

# --- FUNÇÕES DE DADOS ---
def carregar_vendedores():
    try:
        df_u = pd.read_csv(f"{URL_USUARIOS}&t={int(time.time())}")
        if 'nome' in df_u.columns:
            return sorted(df_u['nome'].dropna().unique().tolist())
        return []
    except:
        return []

def carregar_dados_principais():
    try:
        url = f"{CSV_URL}&t={int(time.time())}"
        df = pd.read_csv(url)
        if df.empty: return pd.DataFrame()
        df = df.iloc[:, :10]
        df.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor_Parc', 'Comissao', 'Status', 'Valor_Total', 'Data_Base']
        return df
    except:
        return pd.DataFrame()

# --- 2. INTERFACE ---
st.title("🚀 ERP Comercial - Controle Total")

menu = st.sidebar.radio("Navegação", ["📝 Lançar Venda", "📊 Dashboard", "✅ Baixar Pagamentos"])

if menu == "📝 Lançar Venda":
    st.subheader("📝 Registro de Contrato")
    
    # Carrega vendedores da aba USUARIOS
    vendedores = carregar_vendedores()
    
    with st.form("venda_blindada", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        f_cli = c1.text_input("Nome do Cliente")
        
        if vendedores:
            f_vend = c2.selectbox("Selecione o Vendedor", vendedores)
        else:
            f_vend = c2.text_input("Vendedor (Digite o nome)")
            
        f_data = c3.date_input("Data do Contrato", value=datetime.now())
        
        f_total = c1.number_input("Valor TOTAL", min_value=0.0, format="%.2f")
        f_entrada = c2.number_input("Valor de Entrada", min_value=0.0, format="%.2f")
        f_parc = c3.number_input("Número de Parcelas (0 = À Vista)", min_value=0, value=0, step=1)
        
        if st.form_submit_button("🚀 GRAVAR NA PLANILHA"):
            if not f_cli or f_total <= 0:
                st.error("Erro: Preencha o Cliente e o Valor Total.")
            else:
                success_count = 0
                headers = {'User-Agent': 'Mozilla/5.0'}

                def enviar(t, v, dt):
                    payload = {
                        f"entry.{IDs_FORM['cliente']}": str(f_cli).strip(),
                        f"entry.{IDs_FORM['vendedor']}": str(f_vend).strip(),
                        f"entry.{IDs_FORM['tipo']}": t,
                        f"entry.{IDs_FORM['vencimento']}": dt.strftime('%Y-%m-%d'),
                        f"entry.{IDs_FORM['valor_parc']}": str(round(v, 2)).replace('.', ','),
                        f"entry.{IDs_FORM['comissao']}": str(round(v * 0.05, 2)).replace('.', ','),
                        f"entry.{IDs_FORM['status']}": "Pendente",
                        f"entry.{IDs_FORM['valor_total']}": str(round(f_total, 2)).replace('.', ','),
                        f"entry.{IDs_FORM['data_base']}": f_data.strftime('%Y-%m-%d')
                    }
                    r = requests.post(FORM_URL, data=payload, headers=headers)
                    return r.status_code == 200

                # LÓGICA DE REGISTRO
                if f_parc == 0:
                    # À VISTA
                    if enviar("À Vista", f_total, f_data): success_count += 1
                else:
                    # PARCELADO
                    if f_entrada > 0:
                        if enviar("Entrada", f_entrada, f_data): success_count += 1
                    
                    saldo_restante = f_total - f_entrada
                    valor_da_parcela = saldo_restante / f_parc
                    for i in range(int(f_parc)):
                        data_venc = f_data + relativedelta(months=i+1 if f_entrada > 0 else i)
                        if enviar(f"Parc {i+1}/{int(f_parc)}", valor_da_parcela, data_venc):
                            success_count += 1
                
                if success_count > 0:
                    st.success(f"✅ Registrado com sucesso para {f_vend}!")
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.error("Erro ao gravar. Verifique o formulário.")

elif menu == "📊 Dashboard":
    st.subheader("📊 Visualização de Dados")
    df = carregar_dados_principais()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Planilha vazia ou aguardando dados.")

elif menu == "✅ Baixar Pagamentos":
    st.subheader("✅ Financeiro")
    df = carregar_dados_principais()
    if not df.empty:
        pendentes = df[df['Status'].astype(str).str.contains("Pendente", case=False, na=False)]
        if pendentes.empty:
            st.success("Tudo em dia!")
        else:
            for i, r in pendentes.iterrows():
                with st.expander(f"{r['Cliente']} - {r['Tipo']} | R$ {r['Valor_Parc']}"):
                    if st.button("Baixar Pagamento", key=f"btn_{i}"):
                        requests.get(f"{SCRIPT_URL}?row={i+2}&status=Pago")
                        st.success("Pago!")
                        time.sleep(1)
                        st.rerun()