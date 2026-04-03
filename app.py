import streamlit as st
import pandas as pd

st.title("🔍 Teste de Conexão Direta")

# COLE O SEU LINK AQUI
URL = "https://docs.google.com/spreadsheets/d/1TUMWuy_EjuMgzMUuT3PUVCP3P-FQA8yDN0Hv4RK46SY/edit?usp=sharing"

# Comando para transformar o link normal em um link de download de dados
try:
    csv_url = URL.replace('/edit?usp=sharing', '/export?format=csv&gid=0')
    # Se a aba 'usuarios' não for a primeira, precisaremos do GID dela, 
    # mas vamos testar com a primeira aba primeiro.
    
    df = pd.read_csv(csv_url)
    st.success("✅ Conexão Direta Funcionou!")
    st.write("Dados encontrados na primeira aba:")
    st.dataframe(df)

except Exception as e:
    st.error("❌ A conexão falhou novamente.")
    st.write(f"O erro técnico é: {e}")
    st.info("Dica: Verifique se o link da planilha está como 'Qualquer pessoa com o link'.")