import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. CONFIGURAÇÕES MESTRAS ---
st.set_page_config(page_title="ERP COMERCIAL PRO 2.0", layout="wide", page_icon="🚀")

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSc7YHdYRJZ4I92_cvu0xvHvpU9adHmHmY0RKFxm88NcpjppyA/formResponse"
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?output=csv"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzOSS05oMHIdC5mjafWE1XL8oQnaDIdUyQQ3rssrIIxu0tfdGxFZ2VHrErZ3lAliKJBzw/exec"

IDs = {
    "cliente": "354575898", "vendedor": "1508368855", "tipo": "2051931448",
    "vencimento": "440689882", "valor_parc": "1010209945", "comissao": "1053130357",
    "status": "852082294", "valor_total": "1567666645", "data_base": "1443725489"
}

def carregar_dados():
    try:
        url = f"{CSV_URL}&t={int(time.time())}"
        df = pd.read_csv(url)
        if df.empty: return pd.DataFrame()
        df = df.iloc[:, :10]
        df.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor_Parc', 'Comissao', 'Status', 'Valor_Total', 'Data_Base']
        return df
    except:
        return pd.DataFrame()

# --- INTERFACE ---
st.title("🚀 ERP Comercial - Nova Era")

menu = st.sidebar.radio("Navegação", ["📝 Lançar Venda", "📊 Dashboard", "✅ Baixar Pagamentos"])

if menu == "📝 Lançar Venda":
    with st.form("venda_blindada", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        f_cli = c1.text_input("Cliente")
        f_vend = c2.text_input("Vendedor")
        f_data = c3.date_input("Data Base")
        f_total = c1.number_input("Valor Total", min_value=0.0)
        f_entrada = c2.number_input("Entrada", min_value=0.0)
        f_parc = c3.number_input("Parcelas (0=Recorrência)", min_value=0, value=1)
        
        if st.form_submit_button("🚀 GRAVAR"):
            if not f_cli or f_total <= 0:
                st.warning("Preencha os campos.")
            else:
                success = 0
                saldo = f_total - f_entrada
                loops = 1 if f_parc == 0 else int(f_parc)
                v_p = saldo / loops if f_parc > 0 else f_total
                
                def enviar(t, v, dt):
                    # Limpeza rigorosa: Texto puro e valores com vírgula para o Sheets
                    payload = {
                        f"entry.{IDs['cliente']}": str(f_cli).strip(),
                        f"entry.{IDs['vendedor']}": str(f_vend).strip(),
                        f"entry.{IDs['tipo']}": str(t),
                        f"entry.{IDs['vencimento']}": dt,
                        f"entry.{IDs['valor_parc']}": str(round(v, 2)).replace('.', ','),
                        f"entry.{IDs['comissao']}": str(round(v*0.05, 2)).replace('.', ','),
                        f"entry.{IDs['status']}": "Pendente",
                        f"entry.{IDs['valor_total']}": str(round(f_total, 2)).replace('.', ','),
                        f"entry.{IDs['data_base']}": f_data.strftime('%Y-%m-%d')
                    }
                    try:
                        r = requests.post(FORM_URL, data=payload, timeout=10)
                        return r.status_code == 200
                    except: return False

                if f_entrada > 0:
                    if enviar("Entrada", f_entrada, f_data.strftime('%Y-%m-%d')): success += 1
                
                for i in range(loops):
                    v_dt = (f_data + relativedelta(months=i+1 if f_entrada > 0 else i)).strftime('%Y-%m-%d')
                    t_txt = f"Parc {i+1}/{int(f_parc)}" if f_parc > 0 else "Mensalidade"
                    if enviar(t_txt, v_p, v_dt): success += 1
                
                if success > 0:
                    st.success(f"🚀 {success} registros enviados!")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("Falha ao gravar. Verifique se o Forms está aberto para respostas públicas.")

elif menu == "📊 Dashboard":
    df = carregar_dados()
    if not df.empty: st.dataframe(df)
    else: st.info("Vazio.")

elif menu == "✅ Baixar Pagamentos":
    df = carregar_dados()
    if not df.empty:
        # Busca por Pendente de forma segura
        pendentes = df[df['Status'].astype(str).str.contains("Pendente", case=False, na=False)]
        for i, r in pendentes.iterrows():
            if st.button(f"Baixar {r['Cliente']} - R$ {r['Valor_Parc']}", key=i):
                requests.get(f"{SCRIPT_URL}?row={i+2}&status=Pago")
                st.rerun()