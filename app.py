import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. CONFIGURAÇÕES TÉCNICAS (IDs REAIS DO SEU LINK) ---
st.set_page_config(page_title="ERP COMERCIAL 2.0", layout="wide", page_icon="🚀")

# URLs DA NOVA ESTRUTURA (Substitua pelos seus novos links)
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSc7YHdYRJZ4I92_cvu0xvHvpU9adHmHmY0RKFxm88NcpjppyA/formResponse"
CSV_URL = "SUA_URL_DE_EXPORT_CSV_DA_NOVA_PLANILHA" 
SCRIPT_URL = "SUA_URL_DO_NOVO_APPS_SCRIPT"

# IDs MAPEADOS DO SEU LINK PREENCHIDO
IDs = {
    "cliente": "354575898",
    "vendedor": "1508368855",
    "tipo": "2051931448",
    "vencimento": "440689882",
    "valor_parc": "1010209945",
    "comissao": "1053130357",
    "status": "852082294",
    "valor_total": "1567666645",
    "data_base": "1443725489"
}

def carregar_dados():
    try:
        # Forçamos a atualização com o timestamp no final
        url = f"{CSV_URL}&t={int(time.time())}"
        df = pd.read_csv(url)
        if df.empty: return pd.DataFrame()
        # Ajuste de colunas para o padrão de 10 colunas
        df = df.iloc[:, :10]
        df.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor_Parc', 'Comissao', 'Status', 'Valor_Total', 'Data_Base']
        return df
    except:
        return pd.DataFrame()

# --- 2. INTERFACE ---
st.title("🚀 ERP Comercial - Nova Era")

menu = st.sidebar.radio("Navegação", ["📝 Lançar Venda", "📊 Dashboard", "✅ Baixar Pagamento"])

if menu == "📝 Lançar Venda":
    st.subheader("Novo Registro (Base Zerada)")
    with st.form("venda_nova", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        f_cli = c1.text_input("Nome do Cliente")
        f_vend = c2.text_input("Vendedor")
        f_data = c3.date_input("Data do Contrato (Data Base)")
        
        f_total = c1.number_input("Valor Total do Contrato", min_value=0.0)
        f_entrada = c2.number_input("Valor da Entrada", min_value=0.0)
        f_parc = c3.number_input("Parcelas Restantes (0 = Recorrência)", min_value=0, value=1)
        
        if st.form_submit_button("🚀 GRAVAR NA NOVA PLANILHA"):
            if not f_cli or f_total <= 0:
                st.warning("Preencha cliente e valor total!")
            else:
                success = 0
                # Cálculo de valores
                saldo = f_total - f_entrada
                loops = 1 if f_parc == 0 else int(f_parc)
                v_p = saldo / loops if f_parc > 0 else f_total
                
                def enviar(tipo_mov, valor_mov, data_mov):
                    payload = {
                        f"entry.{IDs['cliente']}": f_cli,
                        f"entry.{IDs['vendedor']}": f_vend,
                        f"entry.{IDs['tipo']}": tipo_mov,
                        f"entry.{IDs['vencimento']}": data_mov,
                        f"entry.{IDs['valor_parc']}": str(round(valor_mov,2)).replace('.',','),
                        f"entry.{IDs['comissao']}": str(round(valor_mov*0.05,2)).replace('.',','),
                        f"entry.{IDs['status']}": "Pendente",
                        f"entry.{IDs['valor_total']}": str(round(f_total,2)).replace('.',','),
                        f"entry.{IDs['data_base']}": f_data.strftime('%Y-%m-%d')
                    }
                    r = requests.post(FORM_URL, data=payload)
                    return r.status_code == 200

                # 1. Grava Entrada
                if f_entrada > 0:
                    if enviar("Entrada", f_entrada, f_data.strftime('%Y-%m-%d')): success += 1
                
                # 2. Grava Parcelas ou Recorrência
                for i in range(loops):
                    # Se tem entrada, a 1ª parcela é em 30 dias. Se não, começa hoje.
                    venc_dt = f_data + relativedelta(months=i+1 if f_entrada > 0 else i)
                    t_txt = f"Parc {i+1}/{int(f_parc)}" if f_parc > 0 else "Recorrência"
                    if enviar(t_txt, v_p, venc_dt.strftime('%Y-%m-%d')): success += 1
                
                if success > 0:
                    st.success(f"✅ Sucesso! {success} registros enviados.")
                    time.sleep(2)
                    st.rerun()

elif menu == "📊 Dashboard":
    df = carregar_dados()
    if df.empty:
        st.info("Aguardando o primeiro lançamento na nova planilha.")
    else:
        st.write("### Dados Atuais")
        st.dataframe(df)

elif menu == "✅ Baixar Pagamento":
    df = carregar_dados()
    if not df.empty:
        pendentes = df[df['Status'].str.contains("Pendente", na=False)]
        for i, r in pendentes.iterrows():
            with st.expander(f"{r['Cliente']} - R$ {r['Valor_Parc']}"):
                if st.button("Confirmar Recebimento", key=i):
                    requests.get(f"{SCRIPT_URL}?row={i+2}&status=Pago")
                    st.rerun()