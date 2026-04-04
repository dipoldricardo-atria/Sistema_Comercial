import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- CONFIGURAÇÕES MESTRAS (ARTHUR VALENTE - ENGENHARIA DE PRECISÃO) ---
st.set_page_config(page_title="ERP COMERCIAL PRO 3.6", layout="centered", page_icon="🚀")

# CHAVES DE CONEXÃO (ARQUIVADAS E BLINDADAS)
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSc7YHdYRJZ4I92_cvu0xvHvpU9adHmHmY0RKFxm88NcpjppyA/formResponse"
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?output=csv"
URL_USUARIOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vS2caIBTPvpKBGV1aITUlSrs5K0G8M5wRw3WURSqXMG-95bWK7PZG3HoILcdy9mvtwqYHl0EwVwW89V/pub?gid=1188945197&single=true&output=csv"
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyur81SkxrO0U4q-Qx_BnMqrm0N3ihp-wt7YNEYkOksjjfCNQwx8TDWbbHmPQHNsO5GDg/exec"

# MAPEAMENTO DE CAMPOS (INTEGRIDADE TOTAL)
IDs = {
    "cliente": "354575898", "vendedor": "1508368855", "tipo": "2051931448",
    "vencimento": "440689882", "valor_parc": "1010209945", "comissao": "1053130357",
    "status": "852082294", "valor_total": "1567666645", "data_base": "1443725489"
}

# --- FUNÇÕES DE ARQUITETURA DE DADOS ---
def carregar_dados(url):
    """Lê dados da planilha com timestamp para evitar cache (dados desatualizados)"""
    try:
        # Adiciona um marcador de tempo para forçar o Google a entregar o dado mais novo
        return pd.read_csv(f"{url}&t={int(time.time())}")
    except:
        return pd.DataFrame()

# --- MÓDULO DE SEGURANÇA (LOGIN) ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🔐 Login de Segurança")
    df_u = carregar_dados(URL_USUARIOS)
    
    with st.form("login"):
        user_email = st.text_input("E-mail Corporativo")
        user_pass = st.text_input("Senha", type="password")
        if st.form_submit_button("ACESSAR SISTEMA"):
            if not df_u.empty:
                # Validação Meticulosa (Email em minúsculo e Senha como Texto)
                match = df_u[(df_u['email'].str.lower() == user_email.lower().strip()) & 
                             (df_u['senha'].astype(str) == str(user_pass))]
                if not match.empty:
                    st.session_state.logado = True
                    st.session_state.info = match.iloc[0].to_dict()
                    st.success(f"Acesso autorizado: {st.session_state.info['nome']}")
                    time.sleep(1); st.rerun()
                else: 
                    st.error("Credenciais inválidas. Verifique e-mail e senha.")
            else: 
                st.error("Erro Crítico: Base de usuários não respondendo. Verifique a publicação da aba.")
    st.stop()

# --- INTERFACE PÓS-AUTENTICAÇÃO ---
u = st.session_state.info
st.sidebar.title(f"🚀 ERP - {u['cargo']}")
st.sidebar.write(f"Usuário: **{u['nome']}**")
if st.sidebar.button("Encerrar Sessão"):
    st.session_state.logado = False
    st.rerun()

menu = st.sidebar.radio("Navegação:", ["📝 Registrar Venda", "📊 Relatórios", "✅ Baixas Financeiras"])

# 1. MÓDULO DE LANÇAMENTO (FOCADO EM ERRO ZERO)
if menu == "📝 Registrar Venda":
    st.subheader(f"📝 Novo Contrato | Vendedor: {u['nome']}")
    with st.form("venda_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        f_cli = c1.text_input("Nome do Cliente")
        f_data = c2.date_input("Data do Contrato", value=datetime.now())
        f_total = c1.number_input("Valor Total (R$)", min_value=0.0, format="%.2f")
        f_entrada = c2.number_input("Valor da Entrada (R$)", min_value=0.0, format="%.2f")
        f_parc = st.number_input("Quantidade de Parcelas (0 = À Vista)", min_value=0, step=1)
        
        if st.form_submit_button("🚀 GRAVAR NA PLANILHA"):
            if not f_cli or f_total <= 0:
                st.error("Atenção: Preencha o Cliente e o Valor Total para prosseguir.")
            else:
                def enviar(t, v, dt):
                    payload = {
                        f"entry.{IDs['cliente']}": f_cli.strip(),
                        f"entry.{IDs['vendedor']}": u['nome'],
                        f"entry.{IDs['tipo']}": t,
                        f"entry.{IDs['vencimento']}": dt.strftime('%Y-%m-%d'),
                        f"entry.{IDs['valor_parc']}": str(round(v, 2)).replace('.', ','),
                        f"entry.{IDs['comissao']}": str(round(v * 0.05, 2)).replace('.', ','),
                        f"entry.{IDs['status']}": "Pendente",
                        f"entry.{IDs['valor_total']}": str(round(f_total, 2)).replace('.', ','),
                        f"entry.{IDs['data_base']}": f_data.strftime('%d/%m/%Y')
                    }
                    return requests.post(FORM_URL, data=payload).status_code == 200

                # Lógica de Fragmentação de Lançamentos
                try:
                    if f_parc == 0:
                        enviar("À Vista", f_total, f_data)
                    else:
                        if f_entrada > 0: enviar("Entrada", f_entrada, f_data)
                        v_parc = (f_total - f_entrada) / f_parc
                        for i in range(int(f_parc)):
                            dt_venc = f_data + relativedelta(months=i+1 if f_entrada > 0 else i)
                            enviar(f"Parc {i+1}/{int(f_parc)}", v_parc, dt_venc)
                    st.success("✅ Protocolo de gravação concluído com sucesso!")
                    time.sleep(1); st.rerun()
                except Exception as e:
                    st.error(f"Erro na Gravação: {e}")

# 2. MÓDULO DE RELATÓRIOS (COM TRAVA DE HIERARQUIA)
elif menu == "📊 Relatórios":
    st.subheader("📊 Visualização de Contratos")
    df = carregar_dados(CSV_URL)
    if not df.empty:
        # Normalização de Colunas para Processamento
        df.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissão', 'Status', 'Total', 'Data_Base']
        
        # Filtro de Privacidade (O Coração da Hierarquia)
        if u['cargo'] != "Admin":
            st.info(f"Visão restrita: Exibindo apenas vendas de {u['nome']}")
            df = df[df['Vendedor'] == u['nome']]
        else:
            st.info("Visão Diretor: Exibindo dados consolidados da equipe.")
            
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("Nenhum registro encontrado na base de dados.")

# 3. MÓDULO DE BAIXAS (RESTRITO AO ADMIN)
elif menu == "✅ Baixas Financeiras":
    st.subheader("✅ Conciliação de Recebíveis")
    
    if u['cargo'] != "Admin":
        st.error("🚫 Acesso Negado: Apenas gestores com cargo 'Admin' podem processar baixas financeiras.")
    else:
        df = carregar_dados(CSV_URL)
        if not df.empty:
            df.columns = ['TS', 'Cliente', 'Vendedor', 'Tipo', 'Vencimento', 'Valor', 'Comissão', 'Status', 'Total', 'Data_Base']
            # Filtra apenas o que precisa de atenção
            pendentes = df[df['Status'].astype(str).str.contains("Pendente", case=False, na=False)]
            
            if pendentes.empty:
                st.success("Tudo em dia! Não há pendências para baixa.")
            else:
                for i, r in pendentes.iterrows():
                    with st.expander(f"🔹 {r['Cliente']} | {r['Tipo']} - R$ {r['Valor']}"):
                        if st.button(f"Confirmar Recebimento", key=f"btn_{i}"):
                            # O cálculo 'i+2' ajusta o índice do Pandas para a linha correta na Planilha
                            response = requests.get(f"{SCRIPT_URL}?row={i+2}&status=Pago")
                            if response.status_code == 200:
                                st.success("Baixa processada na planilha com sucesso!")
                                time.sleep(0.5); st.rerun()
                            else:
                                st.error("Falha na comunicação com o servidor de baixas.")