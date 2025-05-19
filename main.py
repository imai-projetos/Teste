import streamlit as st
import pandas as pd
import datetime
import os
from connect import buscar_dados
from update_data import atualizar_dados
import threading

st.title("Dashboard Entregas")

# Caminho para cache
CACHE_DIR = 'data'
CACHE_FILE = f'{CACHE_DIR}/dados.parquet'

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

@st.cache_data
def carregar_dados():
    try:
        df = pd.read_parquet(CACHE_FILE)
    except (FileNotFoundError, ValueError):
        # Caso o arquivo não exista, busca os dados e salva
        df = buscar_dados('vw_entregas_vuupt')
        df.to_parquet(CACHE_FILE, index=False)

    # Sempre tenta atualizar a última atualização com base no campo data_hora_nf
    if "data_hora_nf" in df.columns and not df["data_hora_nf"].isnull().all():
        ultima_data = df["data_hora_nf"].max()
        st.session_state["ultima_atualizacao"] = ultima_data.strftime("%d/%m/%Y %H:%M:%S")
    else:
        st.session_state["ultima_atualizacao"] = "Sem registro"

    return df

df_entregas = carregar_dados()

# Recarrega a página se a atualização foi concluída
if st.session_state.get("recarregar", False):
    st.session_state["recarregar"] = False  # reseta
    st.rerun()

@st.cache_data
def carregar_infos():
    return buscar_dados('vw_custo_motoqueiros')

def atualizar_em_segundo_plano():
    atualizar_dados()
    st.cache_data.clear()

    df_atualizado = pd.read_parquet(CACHE_FILE)
    if "data_hora_nf" in df_atualizado.columns and not df_atualizado["data_hora_nf"].isnull().all():
        ultima_data = df_atualizado["data_hora_nf"].max()
        st.session_state["ultima_atualizacao"] = ultima_data.strftime("%d/%m/%Y %H:%M:%S")
    else:
        st.session_state["ultima_atualizacao"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    # Sinaliza que deve ser feito um rerun no próximo ciclo
    st.session_state["recarregar"] = True

with st.sidebar:
    st.info(f"🕒 Última atualização: {st.session_state.get('ultima_atualizacao', 'Sem registro')}")

    if st.button("🔄 Atualizar"):
        with st.spinner("Atualizando os dados em segundo plano..."):
            threading.Thread(target=atualizar_em_segundo_plano).start()
            st.success("Atualização iniciada em segundo plano!")
            st.success("Atualização leva aproximadamente 10 minutos!")

# 🔎 **Filtros**
st.sidebar.header("Filtros")
primeiro_dia_mes = datetime.date.today().replace(day=1)
data_inicial = st.sidebar.date_input("Data Inicial", primeiro_dia_mes)
data_final = st.sidebar.date_input("Data Final", datetime.date.today())

# Carregar os dados atualizados
dados = carregar_dados()
dados_motoqueiros = carregar_infos()

# Conversões comuns
dados['data_hora_nf'] = pd.to_datetime(dados['data_hora_nf'])
dados['Concluida'] = pd.to_datetime(dados['Concluida'])
dados['Chegou no Local'] = pd.to_datetime(dados['Chegou no Local'], errors='coerce')
dados['data_hora_pedido'] = pd.to_datetime(dados['data_hora_pedido'], errors='coerce')
dados['Rota Atribuida'] = pd.to_datetime(dados['Rota Atribuida'], errors='coerce')
dados['Data'] = dados['data_hora_nf'].dt.date
dados['competencia'] = pd.to_datetime(dados['Data']).dt.strftime('%Y-%m')
dados['valor_nf'] = pd.to_numeric(dados['valor_nf'], errors='coerce')
dados['valor_frete'] = pd.to_numeric(dados['valor_frete'], errors='coerce')

# Filtros dinâmicos
zonas = sorted(dados['zona'].dropna().unique().tolist())
motoqueiros = sorted(dados['motoqueiro'].dropna().unique())
clientes = sorted(dados['Cliente'].dropna().unique())
vendedores = sorted(dados['vendedor'].dropna().unique())

zonas_sel = st.sidebar.multiselect("Zona:", zonas)
motoqueiros_sel = st.sidebar.multiselect("Motoqueiro:", motoqueiros)
clientes_sel = st.sidebar.multiselect("Cliente:", clientes)
vendedores_sel = st.sidebar.multiselect("Vendedor:", vendedores)

# Aplicar filtros
dados = dados[(dados['Data'] >= data_inicial) & (dados['Data'] <= data_final)]
if zonas_sel: dados = dados[dados['zona'].isin(zonas_sel)]
if motoqueiros_sel: dados = dados[dados['motoqueiro'].isin(motoqueiros_sel)]
if clientes_sel: dados = dados[dados['Cliente'].isin(clientes_sel)]
if vendedores_sel: dados = dados[dados['vendedor'].isin(vendedores_sel)]

# Parâmetros por região
parametros_regiao = {
    "PAULISTA - ABREU E LIMA": {"duracao_seg": 5400, "horario_corte": "16:00:00", "tempo_ideal": "01:30:00"},
    "IGARASSU": {"duracao_seg": 10800, "horario_corte": "15:00:00", "tempo_ideal": "03:00:00"},
    "RECIFE - OLINDA": {"duracao_seg": 3600, "horario_corte": "16:00:00", "tempo_ideal": "01:00:00"},
    "PRAIA SUL": {"duracao_seg": 7200, "horario_corte": "16:00:00", "tempo_ideal": "02:00:00"},
    "JABOATÃO": {"duracao_seg": 10800, "horario_corte": "15:00:00", "tempo_ideal": "03:00:00"},
    "CAMARAGIBE - SÃO LOURENÇO": {"duracao_seg": 10800, "horario_corte": "15:00:00", "tempo_ideal": "03:00:00"}
}

# Cálculo de tempos
dados['Tempo de Ciclo'] = dados.apply(
    lambda row: row['Chegou no Local'] - row['data_hora_pedido']
    if pd.notnull(row['Chegou no Local']) and pd.notnull(row['data_hora_pedido']) and row['Chegou no Local'].date() == row['data_hora_pedido'].date()
    else pd.NaT, axis=1)

dados['Tempo de Rota'] = dados.apply(
    lambda row: row['Chegou no Local'] - row['Rota Atribuida']
    if pd.notnull(row['Chegou no Local']) and pd.notnull(row['Rota Atribuida']) and row['Chegou no Local'].date() == row['Rota Atribuida'].date()
    else pd.NaT, axis=1)

# Filtros de sucesso
dados = dados[
    ((dados['situacao'] == "Realizada") & (dados['situacao_finalizado'] == "Sucesso")) |
    ((dados['situacao_finalizado'] == "Indefinida") & (dados['situacao'] != "Cancelada"))
]

# Indicadores
entregas = dados.shape[0]
viagens = dados['rota_nome'].nunique()
viagens_3p = dados.groupby('rota_nome').filter(lambda x: len(x) > 3)['rota_nome'].nunique()
frete_gratis = len(dados[dados['valor_frete'] == 0]['servico_titulo'].unique())
frete_gratis_perc = frete_gratis / entregas * 100 if entregas else 0
devolucoes = len(dados[dados['devolucao'] == "SIM"])
devolucoes_perc = (devolucoes / entregas * 100) if entregas > 0 else 0
valor_nf_total = dados['valor_nf'].sum()
valor_frete_total = dados['valor_frete'].sum()
entregas_viradas = dados[dados['Concluida'].dt.date > dados['Data']].shape[0]
entregas_viradas_perc = entregas_viradas / entregas * 100 if entregas else 0

# % Acima tempo ideal
def acima_tempo(row):
    if pd.notnull(row['Tempo de Ciclo']) and row['zona'] in parametros_regiao:
        return row['Tempo de Ciclo'].total_seconds() > parametros_regiao[row['zona']]['duracao_seg']
    return False

entregas_validas = dados[dados['Concluida'].dt.date == dados['Data']]
entregas_acima = entregas_validas.apply(acima_tempo, axis=1).sum()
perc_acima = (entregas_acima / len(entregas_validas) * 100) if len(entregas_validas) else 0

# Indicadores adicionais
ticket_medio = valor_nf_total / entregas if entregas else 0
receita_media_viagem = valor_nf_total / viagens if viagens else 0
entregas_por_viagem = entregas / viagens if viagens else 0
motoqueiros = dados['motoqueiro'].nunique()
entregas_por_motoqueiro = entregas / motoqueiros if motoqueiros else 0

# Custo por entrega
dados_motoqueiros['competencia'] = pd.to_datetime(dados_motoqueiros['competencia'], format='%Y/%m').dt.strftime('%Y-%m')
competencia = pd.to_datetime(data_final).strftime('%Y-%m')
custo_total = dados_motoqueiros[dados_motoqueiros['competencia'] == competencia]['valor_competencia'].sum()
custo_por_entrega = round(custo_total / entregas, 1) if entregas else 0
custo_por_entrega = f"R$ {custo_por_entrega:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
resultado_projetado = float(valor_frete_total) - float(custo_total)
resultado = (float(valor_frete_total) / float(custo_total) * 100) if float(custo_total) > 0 else 0

# Formatação tempo médio
def formatar(td):
    if pd.isnull(td): return "Não definido"
    s = int(td.total_seconds())
    return f"{s // 3600:02}:{(s % 3600) // 60:02}:{s % 60:02}"

tempo_ciclo_medio = formatar(dados['Tempo de Ciclo'].dropna().mean())
tempo_rota_medio = formatar(dados['Tempo de Rota'].dropna().mean())

# Render cards
def render_cartao(titulo, valor, moeda=True, percentual=False):
    if isinstance(valor, (float, int)):
        valor = f"{valor:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
        valor = f"R$ {valor}" if moeda else f"{valor}%" if percentual else valor
    return f"""
    <div style="width: 100%; max-width: 250px; height: 100px; margin: 10px;
                background-color: #1239FF; color: white; font-size: 15px;
                font-weight: bold; border-radius: 10px; display: flex;
                flex-direction: column; align-items: center; justify-content: center;
                text-align: center; box-shadow: 2px 2px 8px rgba(0, 0, 0, 0.15);">
        <div>{titulo}</div>
        <div style="font-size: 22px; margin-top: 4px;">{valor}</div>
    </div>"""

# Layout
st.subheader("Indicadores Gerais")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(render_cartao("Entregas", entregas, False), unsafe_allow_html=True)
    st.markdown(render_cartao("Viagens", viagens, False), unsafe_allow_html=True)
with col2:
    st.markdown(render_cartao("Faturamento", valor_nf_total), unsafe_allow_html=True)
    st.markdown(render_cartao("Receita Frete", valor_frete_total), unsafe_allow_html=True)
with col3:          
    st.markdown(render_cartao("Frete Grátis (%)", f"{frete_gratis_perc:.1f}%", False), unsafe_allow_html=True)
    st.markdown(render_cartao("Devoluções (%)", f"{devolucoes_perc:.1f}%", False), unsafe_allow_html=True)
with col4:
    st.markdown(render_cartao("Entregas Viradas (%)", f"{entregas_viradas_perc:.1f}%", False), unsafe_allow_html=True)
    st.markdown(render_cartao("Entregas Acima do Tempo (%)", f"{perc_acima:.1f}%", False), unsafe_allow_html=True)

st.subheader("Indicadores de Desempenho")
col5, col6, col7, col8 = st.columns(4)

with col5:
    st.markdown(render_cartao("Entregas p/ Viagem", entregas_por_viagem, False), unsafe_allow_html=True)
    st.markdown(render_cartao("Viagens com +3 Entregas", viagens_3p, False), unsafe_allow_html=True)
with col6:
    st.markdown(render_cartao("Ticket Médio", ticket_medio), unsafe_allow_html=True)
    st.markdown(render_cartao("Custo por Entrega", custo_por_entrega, True), unsafe_allow_html=True)
with col7:
    st.markdown(render_cartao("Receita Média p/ Viagem", receita_media_viagem), unsafe_allow_html=True)
    st.markdown(render_cartao("Resultado Projetado", resultado_projetado, True), unsafe_allow_html=True)
with col8:
    st.markdown(render_cartao("Entregas p/ Motoqueiro", entregas_por_motoqueiro, False), unsafe_allow_html=True)
    st.markdown(render_cartao("Resultado (%)", f"{resultado:.1f}%", False), unsafe_allow_html=True)

st.subheader("Parâmetros por Região")
if len(zonas_sel) == 1 and zonas_sel[0] in parametros_regiao:
    zona_info = parametros_regiao[zonas_sel[0]]
    tempo_ideal = zona_info["tempo_ideal"]
    horario_corte = zona_info["horario_corte"]
else:
    tempo_ideal = "Não definido"
    horario_corte = "Não definido"

col9, col10, col11, col12 = st.columns(4)
with col9:
    st.markdown(render_cartao("Tempo de Ciclo", tempo_ciclo_medio, False), unsafe_allow_html=True)
with col10:
    st.markdown(render_cartao("Tempo Parametrizado", tempo_ideal, False), unsafe_allow_html=True)
with col11:
    st.markdown(render_cartao("Tempo de Rota", tempo_rota_medio, False), unsafe_allow_html=True)
with col12:
    st.markdown(render_cartao("Horário Corte", horario_corte, False), unsafe_allow_html=True)
