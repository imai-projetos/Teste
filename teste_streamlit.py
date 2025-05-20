import streamlit as st

# Configuração da página
st.set_page_config(
    page_title="Teste Dashboard",
    page_icon="🚚",
    layout="wide"
)

# Conteúdo simples
st.title("Dashboard de Teste")
st.write("Este é um teste simples para verificar se o Streamlit está funcionando corretamente.")

# Botão de teste
if st.button("Clique em mim"):
    st.success("O botão foi clicado com sucesso!")

# Exibir informações sobre a versão do Streamlit
st.info(f"Versão do Streamlit: {st.__version__}")