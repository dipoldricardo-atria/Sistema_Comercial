import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- CONFIGURAÇÕES MESTRAS (ARTHUR VALENTE - ENGENHARIA DE PRECISÃO) ---
st.set_page_config(page_title="ERP COMERCIAL PRO 3.9", layout="centered", page_icon="🚀")

# LINKS DE CONEXÃO (TRATADOS E VALIDADOS)
# O link foi convertido de 'viewform' para 'formResponse' para permitir gravação via sistema.
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSc7YHdYRJZ4I92_cvu0xvHvpU9adHmHmY0RKFxm88NcpjppyA/formResponse"
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?output=csv"
URL_USUARIOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?gid=1188945197&single=true&output=csv"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyur81SkxrO0U4q-Qx_BnMqrm0N3ihp-wt7YNEYkOksjjfCNQwx8TDWbbHmPQHNsO5GDg/exec"

# IDs DOS CAMPOS DO FORMULÁRIO (MAPEAMENTO TÉCNICO)
IDs = {
    "cliente": "354575898", "vendedor": "1508368855", "tipo": "2051931448",
    "vencimento": "440689882", "valor_parc": "1010209945", "comissao": "1053130357",
    "status": "852082294", "valor_total": "1567666645", "data_base": "1443725489"
}

def carregar_dados(url):
    """Garante a leitura dos dados mais recentes ignorando o cache do navegador"""
    try:
        return pd.read_csv(f"{url}&t={int(time.time())}")
    except:
        return pd.DataFrame()

# --- CONTROLE DE ACESSO (SEGURANÇA RBAC) ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🔐 Acesso Restrito")
    df_u = carregar_dados(URL_USUARIOS)
    with st.form("login_box"):
        user_email = st.text_input("E-mail Cadastrado")
        user_pass = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar no ERP"):
            if not df_u.empty:
                # Busca exata ignorando espaços e diferenciação de maiúsculas no e-mail
                match = df_u[(df_u['email'].astype(str).str.lower() == user_email.lower().strip()) & 
                             (df_u['senha'].astype(str) == str(user_pass))]
                if not match.empty:
                    st.session_state.logado = True
                    st.session_state.info = match.iloc[0].to_dict()
                    st.rerun()
                else: st.error("E-mail ou senha inválidos.")
            else: st.error("Falha ao conectar com o servidor de usuários.")
    st.stop()

# --- DASHBOARD PRINCIPAL ---
u = st.session_state.info
df_vendedores = carregar_dados(URL_USUARIOS)

st.sidebar.title(f"🚀 Nível: {u['cargo']}")
st.sidebar.info(f"Usuário: {u['nome']}")
if st.sidebar.button("Logoff"):
    st.session_state.logado = False
    st.rerun()

menu = st.sidebar.radio("Navegação", ["📝 Registro de Vendas", "📊 Relatório Comercial", "✅ Baixas de Pagamento"])

# 1. MÓDULO DE LANÇAMENTO (FOCO EM INTEGRIDADE DE DADOS)
if menu == "📝 Registro de Vendas":
    st.subheader("📝 Lançamento de Novo Contrato")
    with st.form("form_venda", clear_on_submit=True):
        c1, c2 = st.columns(2)
        f_cli = c1.text_input("Nome Completo do Cliente")
        f_data = c2.date_input("Data do Contrato", value=datetime.now())
        
        # Como Diretor (Admin), você tem o seletor de todos os vendedores ativos.
        if u['cargo'] == "Admin" and not df_vendedores.empty:
            vendedor_resp = st.selectbox("Vendedor Responsável", df_vendedores['nome'].tolist())
        else:
            vendedor_resp = u['nome']
            st.info(f"Lançando como: {vendedor_resp}")

        f_total = c1.number_input("Valor Bruto Total (R$)", min_value=0.0, format="%.2f")
        f_entrada = c2.number_input("Valor de Entrada (R$)", min_value=0.0, format="%.2f")
        f_parc = st.number_input("Nº de Parcelas (0 para Pagamento à Vista)", min_value=0, step=1)
        
        if st.form_submit_button("🚀 PROCESSAR E GRAVAR"):
            if not f_cli or f_total <= 0:
                st.error("Preenchimento obrigatório: Cliente e Valor Total.")
            else:
                def persistir_no_google(tipo, valor, vencimento):
                    """Envia os dados para o Google Forms de forma automatizada"""
                    payload = {
                        f"entry.{IDs['cliente']}": f_cli.strip(),
                        f"entry.{IDs['vendedor']}": vendedor_resp,
                        f"entry.{IDs['tipo']}": tipo,
                        f"entry.{IDs['vencimento']}": vencimento.strftime('%Y-%m-%d'),
                        f"entry.{IDs['valor_parc']}": str(round(valor, 2)).replace('.', ','),
                        f"entry.{IDs['comissao']}": str(round(valor * 0.05, 2)).replace('.', ','),
                        f"entry.{IDs['status']}": "Pendente",
                        f"entry.{IDs['valor_total']}": str(round(f_total, 2)).replace('.', ','),
                        f"entry.{IDs['data_base']}": f_data.strftime('%d/%m/%Y')
                    }
                    r = requests.post(FORM_URL, data=payload)
                    return r.status_code

                # Lógica de Fragmentação por Parcelas
                retornos = []
                if f_parc == 0:
                    retornos.append(persistir_no_google("À Vista", f_total, f_data))
                else:
                    if f_entrada > 0:
                        retornos.append(persistir_no_google("Entrada", f_entrada, f_data))
                    
                    valor_cada = (f_total - f_entrada) / f_parc
                    for i in range(int(f_parc)):
                        venc = f_data + relativedelta(months=i+1 if f_entrada > 0 else i)
                        retornos.append(persistir_no_google(f"Parc {i+1}/{int(f_parc)}", valor_cada, venc))
                
                # Validação de Erro Zero
                if all(res == 200 for res in retornos):
                    st.success("✅ Venda registrada com sucesso em nossa base de dados!")
                    time.sleep(1); st.rerun()
                else:
                    st.error(f"❌ Erro de Sincronização. Códigos de Resposta: {retornos}")
                    st.info("Arthur recomenda: Verifique as permissões de acesso do Formulário.")

# 2. MÓDULO DE RELATÓRIO
elif menu == "📊 Relatório Comercial":
    df = carregar_dados(CSV_URL)
    if not df.empty:
        df.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissão', 'Status', 'Total', 'Data_Base']
        if u['cargo'] != "Admin":
            df = df[df['Vendedor'] == u['nome']]
        st.dataframe(df, use_container_width=True)

# 3. MÓDULO FINANCEIRO (ADMIN APENAS)
elif menu == "✅ Baixas de Pagamento":
    if u['cargo'] != "Admin":
        st.error("🚫 Acesso restrito ao nível de Diretoria.")
    else:
        df = carregar_dados(CSV_URL)
        if not df.empty:
            df.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissão', 'Status', 'Total', 'Data_Base']
            pendentes = df[df['Status'].astype(str).str.contains("Pendente", case=False, na=False)]
            
            if pendentes.empty:
                st.success("Não há pagamentos pendentes no momento.")
            else:
                for idx, row in pendentes.iterrows():
                    with st.expander(f"💰 {row['Cliente']} | {row['Tipo']} - R$ {row['Valor']}"):
                        if st.button(f"Confirmar Recebimento", key=f"bx_{idx}"):
                            # O script usa row=idx+2 para alinhar com a linha da planilha (contando cabeçalho)
                            res = requests.get(f"{SCRIPT_URL}?row={idx+2}&status=Pago")
                            if res.status_code == 200:
                                st.success("Status atualizado!"); time.sleep(0.5); st.rerun()
                            else:
                                st.error("Erro ao processar baixa via Apps Script.")