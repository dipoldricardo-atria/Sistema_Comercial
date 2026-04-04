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

# --- 2. INTERFACE ---
st.title("🚀 ERP Comercial - Gestão de Vendas")

menu = st.sidebar.radio("Navegação", ["📝 Lançar Venda", "📊 Dashboard", "✅ Baixar Pagamentos"])

if menu == "📝 Lançar Venda":
    st.subheader("📝 Registro de Contrato")
    with st.form("venda_blindada", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        f_cli = c1.text_input("Nome do Cliente")
        f_vend = c2.text_input("Vendedor")
        f_data = c3.date_input("Data do Contrato")
        
        f_total = c1.number_input("Valor TOTAL", min_value=0.0)
        f_entrada = c2.number_input("Valor de Entrada", min_value=0.0)
        f_parc = c3.number_input("Número de Parcelas (0 = À Vista)", min_value=0, value=0)
        
        if st.form_submit_button("🚀 GRAVAR NA PLANILHA"):
            if not f_cli or f_total <= 0:
                st.error("Erro: Preencha o Cliente e o Valor Total.")
            else:
                success_count = 0
                headers = {'User-Agent': 'Mozilla/5.0'}

                def enviar(t, v, dt):
                    payload = {
                        f"entry.{IDs['cliente']}": f_cli,
                        f"entry.{IDs['vendedor']}": f_vend,
                        f"entry.{IDs['tipo']}": t,
                        f"entry.{IDs['vencimento']}": dt,
                        f"entry.{IDs['valor_parc']}": str(round(v, 2)).replace('.', ','),
                        f"entry.{IDs['comissao']}": str(round(v * 0.05, 2)).replace('.', ','),
                        f"entry.{IDs['status']}": "Pendente",
                        f"entry.{IDs['valor_total']}": str(round(f_total, 2)).replace('.', ','),
                        f"entry.{IDs['data_base']}": f_data.strftime('%d/%m/%Y')
                    }
                    r = requests.post(FORM_URL, data=payload, headers=headers)
                    return r.status_code == 200

                # LÓGICA DE DECISÃO: À VISTA OU PARCELADO
                if f_parc == 0:
                    # VENDA À VISTA: Gera apenas um registro do valor total hoje
                    if enviar("À Vista", f_total, f_data.strftime('%d/%m/%Y')):
                        success_count += 1
                else:
                    # VENDA PARCELADA
                    # 1. Registra Entrada (se houver)
                    if f_entrada > 0:
                        if enviar("Entrada", f_entrada, f_data.strftime('%d/%m/%Y')):
                            success_count += 1
                    
                    # 2. Registra as Parcelas do saldo restante
                    saldo = f_total - f_entrada
                    v_p = saldo / f_parc
                    for i in range(int(f_parc)):
                        venc_dt = f_data + relativedelta(months=i+1 if f_entrada > 0 else i)
                        if enviar(f"Parc {i+1}/{int(f_parc)}", v_p, venc_dt.strftime('%d/%m/%Y')):
                            success_count += 1
                
                if success_count > 0:
                    st.success(f"✅ Registrado com sucesso! ({success_count} lançamentos)")
                    time.sleep(2)
                    st.rerun()

elif menu == "📊 Dashboard":
    df = carregar_dados()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Base vazia.")

elif menu == "✅ Baixar Pagamentos":
    df = carregar_dados()
    if not df.empty:
        pendentes = df[df['Status'].astype(str).str.contains("Pendente", case=False, na=False)]
        for i, r in pendentes.iterrows():
            with st.expander(f"{r['Cliente']} - {r['Tipo']} (R$ {r['Valor_Parc']})"):
                if st.button("Marcar como Pago", key=f"bx_{i}"):
                    requests.get(f"{SCRIPT_URL}?row={i+2}&status=Pago")
                    st.rerun()