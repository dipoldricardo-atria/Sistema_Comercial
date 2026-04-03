import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. CONFIGURAÇÕES MESTRAS (LINKS E IDs INJETADOS) ---
st.set_page_config(page_title="ERP COMERCIAL PRO 2.0", layout="wide", page_icon="🚀")

# Links da sua NOVA estrutura
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSc7YHdYRJZ4I92_cvu0xvHvpU9adHmHmY0RKFxm88NcpjppyA/formResponse"
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?output=csv"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzOSS05oMHIdC5mjafWE1XL8oQnaDIdUyQQ3rssrIIxu0tfdGxFZ2VHrErZ3lAliKJBzw/exec"

# Seus novos IDs mapeados do link que você enviou
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
        # Adicionamos um carimbo de tempo para o Google não entregar dados antigos (cache)
        url = f"{CSV_URL}&t={int(time.time())}"
        df = pd.read_csv(url)
        if df.empty: return pd.DataFrame()
        # Forçamos a leitura das 10 colunas padrão
        df = df.iloc[:, :10]
        df.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor_Parc', 'Comissao', 'Status', 'Valor_Total', 'Data_Base']
        return df
    except:
        return pd.DataFrame()

# --- 2. INTERFACE COMERCIAL ---
st.title("🚀 ERP Comercial - Nova Era")

menu = st.sidebar.radio("Menu de Gestão", ["📝 Lançar Nova Venda", "📊 Dashboard de Controle", "✅ Baixar Pagamentos"])

# --- 3. LANÇAMENTO DE VENDAS (LÓGICA BLINDADA) ---
if menu == "📝 Lançar Nova Venda":
    st.subheader("📝 Registro de Contrato")
    with st.form("venda_nova", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        f_cli = c1.text_input("Nome do Cliente")
        f_vend = c2.text_input("Vendedor")
        f_data = c3.date_input("Data do Fechamento (Data Base)")
        
        f_total = c1.number_input("Valor TOTAL do Contrato", min_value=0.0)
        f_entrada = c2.number_input("Valor da ENTRADA (0 se não houver)", min_value=0.0)
        f_parc = c3.number_input("Parcelas RESTANTES (0 = Recorrência)", min_value=0, value=1)
        
        if st.form_submit_button("🚀 FINALIZAR E GRAVAR NA BASE"):
            if not f_cli or f_total <= 0:
                st.error("Erro: Preencha o Cliente e o Valor Total.")
            else:
                success_count = 0
                saldo = f_total - f_entrada
                loops = 1 if f_parc == 0 else int(f_parc)
                v_p = saldo / loops if f_parc > 0 else f_total
                
                # Função interna de disparo para o Google
                def enviar_registro(tipo_mov, valor_mov, data_mov):
                    payload = {
                        f"entry.{IDs['cliente']}": f_cli,
                        f"entry.{IDs['vendedor']}": f_vend,
                        f"entry.{IDs['tipo']}": tipo_mov,
                        f"entry.{IDs['vencimento']}": data_mov,
                        f"entry.{IDs['valor_parc']}": str(round(valor_mov,2)).replace('.',','),
                        f"entry.{IDs['comissao']}": str(round(valor_mov*0.05,2)).replace('.',','), # 5% Comissão
                        f"entry.{IDs['status']}": "Pendente",
                        f"entry.{IDs['valor_total']}": str(round(f_total,2)).replace('.',','),
                        f"entry.{IDs['data_base']}": f_data.strftime('%d/%m/%Y')
                    }
                    r = requests.post(FORM_URL, data=payload)
                    return r.status_code == 200

                # 1. Grava a Entrada se existir
                if f_entrada > 0:
                    if enviar_registro("Entrada", f_entrada, f_data.strftime('%d/%m/%Y')):
                        success_count += 1
                
                # 2. Grava as Parcelas ou Mensalidade Recorrente
                for i in range(loops):
                    # Se tem entrada, a 1ª parcela vence em 30 dias. Se não, começa na data base.
                    venc_dt = f_data + relativedelta(months=i+1 if f_entrada > 0 else i)
                    t_txt = f"Parc {i+1}/{int(f_parc)}" if f_parc > 0 else "Mensalidade (Recorrente)"
                    if enviar_registro(t_txt, v_p, venc_dt.strftime('%d/%m/%Y')):
                        success_count += 1
                
                if success_count > 0:
                    st.success(f"✅ Sucesso! {success_count} registros inseridos na nova planilha.")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("Falha de comunicação com o Google. Verifique sua conexão.")

# --- 4. DASHBOARD (VISUALIZAÇÃO) ---
elif menu == "📊 Dashboard de Controle":
    st.subheader("📊 Acompanhamento de Resultados")
    df = carregar_dados()
    if df.empty:
        st.info("A base de dados ainda está vazia. Comece lançando uma venda.")
    else:
        st.write("Registros Encontrados:")
        st.dataframe(df, use_container_width=True)

# --- 5. BAIXAS (FINANCEIRO) ---
elif menu == "✅ Baixar Pagamentos":
    st.subheader("✅ Conciliação Financeira")
    df = carregar_dados()
    if not df.empty:
        # Filtra apenas o que não está pago (Status na coluna 8)
        pendentes = df[df['Status'].str.contains("Pendente", na=False, case=False)]
        if pendentes.empty:
            st.success("Tudo recebido! Nenhuma pendência encontrada.")
        else:
            for i, r in pendentes.iterrows():
                with st.expander(f"{r['Cliente']} - {r['Tipo']} (R$ {r['Valor_Parc']})"):
                    if st.button("Marcar como Pago", key=f"btn_{i}"):
                        # i+2 compensa o index 0 do Python e o cabeçalho do Google
                        requests.get(f"{SCRIPT_URL}?row={i+2}&status=Pago")
                        st.success(f"Pagamento de {r['Cliente']} baixado!")
                        time.sleep(1)
                        st.rerun()