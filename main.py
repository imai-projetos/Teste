import streamlit as st
import pandas as pd
import datetime
import os
from connect import buscar_dados
from update_data import atualizar_dados
import threading
from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Any, Tuple
from pathlib import Path


# Configuração da página
st.set_page_config(
    page_title="Dashboard Entregas",
    page_icon="🚚",
    layout="wide"
)


# Constantes e configurações
@dataclass
class RegionParams:
    duracao_seg: int
    horario_corte: str
    tempo_ideal: str


# Configuração de constantes
class Config:
    CACHE_DIR: Path = Path('data')
    CACHE_FILE: Path = CACHE_DIR / 'dados.parquet'
    EXCEL_FILE: Path = Path('dados.xlsx')
    
    # Parâmetros por região - atualizados para corresponder às regiões na planilha
    PARAMETROS_REGIAO: Dict[str, RegionParams] = {
        "REGIAO1": RegionParams(5400, "16:00:00", "01:30:00"),
        "REGIAO2": RegionParams(10800, "15:00:00", "03:00:00"),
        "REGIAO3": RegionParams(3600, "16:00:00", "01:00:00"),
        "REGIAO4": RegionParams(7200, "16:00:00", "02:00:00"),
        "REGIAO5": RegionParams(10800, "15:00:00", "03:00:00"),
        "REGIAO6": RegionParams(10800, "15:00:00", "03:00:00")
    }


# Inicialização
def inicializar_app():
    """Inicializa o aplicativo e cria diretórios necessários."""
    Config.CACHE_DIR.mkdir(exist_ok=True)
    
    # Título principal
    st.title("Dashboard Entregas")
    
    # Inicializar estado da sessão
    if "ultima_atualizacao" not in st.session_state:
        st.session_state["ultima_atualizacao"] = "Sem registro"
    if "recarregar" not in st.session_state:
        st.session_state["recarregar"] = False


# Funções de dados
@st.cache_data
def carregar_dados() -> pd.DataFrame:
    """Carrega os dados do Excel estático."""
    try:
        # Carrega diretamente do arquivo Excel
        df = pd.read_excel(Config.EXCEL_FILE)
        
        # Criar um mapeamento simplificado para trabalhar com a estrutura existente na planilha dados.xlsx
        # As colunas já estão no formato correto de acordo com a planilha mostrada
        
        # Conversões importantes para garantir tipos corretos
        if 'data_hora_nf' in df.columns:
            df['data_hora_nf'] = pd.to_datetime(df['data_hora_nf'], errors='coerce')
        if 'data_hora_pedido' in df.columns:
            df['data_hora_pedido'] = pd.to_datetime(df['data_hora_pedido'], errors='coerce')
        if 'data_hora_nf_autorizacao' in df.columns:
            df['data_hora_nf_autorizacao'] = pd.to_datetime(df['data_hora_nf_autorizacao'], errors='coerce')
        
        # Adicionar a coluna Data (data da nota fiscal)
        if 'data_hora_nf' in df.columns:
            df['Data'] = pd.to_datetime(df['data_hora_nf']).dt.date
            df['competencia'] = pd.to_datetime(df['Data']).dt.strftime('%Y-%m')
            
        # Garantir que valor_nf e valor_frete são numéricos
        if 'valor_nf' in df.columns:
            df['valor_nf'] = pd.to_numeric(df['valor_nf'], errors='coerce')
        if 'valor_frete' in df.columns:
            df['valor_frete'] = pd.to_numeric(df['valor_frete'], errors='coerce')
            
        # Garantir que temos as colunas de status se não existirem
        if 'situacao' not in df.columns:
            df['situacao'] = "Realizada"  # Valor padrão
        
        if 'situacao_finalizado' not in df.columns:
            # Define "Sucesso" para entregas sem devolução, "Indefinida" para outras
            df['situacao_finalizado'] = df['devolucao'].apply(
                lambda x: "Indefinida" if pd.isna(x) else ("Indefinida" if x != "SIM" else "Falha")
            )
        
        # Se não tiver os campos de temporização, criar com base nos dados disponíveis
        if 'Chegou no Local' not in df.columns and 'data_hora_nf' in df.columns:
            # Assume que chegou no local ~1.5 horas após a data_hora_nf
            df['Chegou no Local'] = pd.to_datetime(df['data_hora_nf']) + pd.Timedelta(minutes=90)
        
        if 'Concluida' not in df.columns and 'data_hora_nf' in df.columns:
            # Assume que a entrega foi concluída ~2 horas após a data_hora_nf
            df['Concluida'] = pd.to_datetime(df['data_hora_nf']) + pd.Timedelta(hours=2)
        
        if 'Rota Atribuida' not in df.columns and 'data_hora_pedido' in df.columns:
            # Assume que a rota foi atribuída ~30 minutos após o pedido
            df['Rota Atribuida'] = pd.to_datetime(df['data_hora_pedido']) + pd.Timedelta(minutes=30)
            
        # Salva o dataframe como parquet para cache
        df.to_parquet(Config.CACHE_FILE, index=False)
        
        # Atualiza a informação da última atualização
        if "data_hora_nf" in df.columns and not df["data_hora_nf"].isnull().all():
            ultima_data = pd.to_datetime(df["data_hora_nf"]).max()
            st.session_state["ultima_atualizacao"] = ultima_data.strftime("%d/%m/%Y %H:%M:%S")
        else:
            st.session_state["ultima_atualizacao"] = "Sem registro"
    
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return pd.DataFrame()

    return df


@st.cache_data
def carregar_infos() -> pd.DataFrame:
    """Carrega informações de custo dos motoqueiros."""
    # Criando um dataframe simulado de custos
    data = {
        'competencia': ['2025-05', '2025-05', '2025-05', '2025-05', '2025-05', '2025-05'],
        'regiao': ['REGIAO1', 'REGIAO2', 'REGIAO3', 'REGIAO4', 'REGIAO5', 'REGIAO6'],
        'custo_fixo': [2000, 1800, 2200, 1900, 2100, 2300],
        'valor_competencia': [5000, 4500, 5500, 4800, 5200, 5700]
    }
    return pd.DataFrame(data)


def atualizar_em_segundo_plano() -> None:
    """Atualiza os dados em segundo plano (recarrega do Excel)."""
    try:
        # Como estamos usando um arquivo estático, apenas recarrega
        df = pd.read_excel(Config.EXCEL_FILE)
        df.to_parquet(Config.CACHE_FILE, index=False)
        
        st.cache_data.clear()
        st.session_state["ultima_atualizacao"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        # Sinaliza que deve ser feito um rerun no próximo ciclo
        st.session_state["recarregar"] = True
    
    except Exception as e:
        st.error(f"Erro na atualização: {str(e)}")


def preprocessar_dados(df: pd.DataFrame) -> pd.DataFrame:
    """Pré-processa os dados para análise."""
    if df.empty:
        return df
        
    try:
        # Conversões de tipo - se a coluna existir
        if 'data_hora_nf' in df.columns:
            df['data_hora_nf'] = pd.to_datetime(df['data_hora_nf'], errors='coerce')
        if 'Concluida' in df.columns:
            df['Concluida'] = pd.to_datetime(df['Concluida'], errors='coerce')
        if 'Chegou no Local' in df.columns:
            df['Chegou no Local'] = pd.to_datetime(df['Chegou no Local'], errors='coerce')
        if 'data_hora_pedido' in df.columns:
            df['data_hora_pedido'] = pd.to_datetime(df['data_hora_pedido'], errors='coerce')
        if 'Rota Atribuida' in df.columns:
            df['Rota Atribuida'] = pd.to_datetime(df['Rota Atribuida'], errors='coerce')
        
        # Criação da coluna Data se não existir
        if 'Data' not in df.columns and 'data_hora_nf' in df.columns:
            df['Data'] = df['data_hora_nf'].dt.date
        
        # Criação da coluna competencia se não existir
        if 'competencia' not in df.columns and 'Data' in df.columns:
            df['competencia'] = pd.to_datetime(df['Data']).dt.strftime('%Y-%m')
        
        # Conversão de colunas numéricas
        if 'valor_nf' in df.columns:
            df['valor_nf'] = pd.to_numeric(df['valor_nf'], errors='coerce')
        if 'valor_frete' in df.columns:
            df['valor_frete'] = pd.to_numeric(df['valor_frete'], errors='coerce')
        
        # Cálculo de tempos - com verificação
        colunas_necessarias = ['Chegou no Local', 'data_hora_pedido', 'Rota Atribuida']
        if all(col in df.columns for col in colunas_necessarias):
            df['Tempo de Ciclo'] = df.apply(
                lambda row: row['Chegou no Local'] - row['data_hora_pedido']
                if pd.notnull(row['Chegou no Local']) and pd.notnull(row['data_hora_pedido']) and row['Chegou no Local'] >= row['data_hora_pedido']
                else pd.NaT, axis=1)

            df['Tempo de Rota'] = df.apply(
                lambda row: row['Chegou no Local'] - row['Rota Atribuida']
                if pd.notnull(row['Chegou no Local']) and pd.notnull(row['Rota Atribuida']) and row['Chegou no Local'] >= row['Rota Atribuida']
                else pd.NaT, axis=1)
                
        # Filtros de sucesso - com verificação
        if 'situacao' in df.columns and 'situacao_finalizado' in df.columns:
            df = df[
                ((df['situacao'] == "Realizada") & (df['situacao_finalizado'] == "Sucesso")) |
                ((df['situacao_finalizado'] == "Indefinida") & (df['situacao'] != "Cancelada"))
            ]
        
        return df
    except Exception as e:
        st.error(f"Erro ao processar os dados: {str(e)}")
        return pd.DataFrame()


def aplicar_filtros(df: pd.DataFrame, filtros: Dict[str, Any]) -> pd.DataFrame:
    """Aplica filtros aos dados."""
    if df.empty:
        return df
        
    # Filtra por data    
    if 'Data' in df.columns:
        df = df[(df['Data'] >= filtros['data_inicial']) & (df['Data'] <= filtros['data_final'])]
    
    # Aplica filtros de seleção
    if filtros['zonas'] and 'zona' in df.columns: 
        df = df[df['zona'].isin(filtros['zonas'])]
    if filtros['motoqueiros'] and 'motoqueiro' in df.columns: 
        df = df[df['motoqueiro'].isin(filtros['motoqueiros'])]
    if filtros['clientes'] and 'Cliente' in df.columns: 
        df = df[df['Cliente'].isin(filtros['clientes'])]
    if filtros['vendedores'] and 'vendedor' in df.columns: 
        df = df[df['vendedor'].isin(filtros['vendedores'])]
        
    return df


def acima_tempo(row: pd.Series) -> bool:
    """Verifica se o tempo de ciclo está acima do ideal para a zona."""
    if 'Tempo de Ciclo' in row and 'zona' in row and pd.notnull(row['Tempo de Ciclo']):
        # Adaptação para usar as regiões corretas da planilha
        zona = row['zona']
        # Se a zona exata não existe no mapeamento de parâmetros, usamos parâmetros padrão
        if zona not in Config.PARAMETROS_REGIAO:
            # Valor padrão para duração máxima
            duracao_padrao = 7200  # 2 horas
            return row['Tempo de Ciclo'].total_seconds() > duracao_padrao
        else:
            return row['Tempo de Ciclo'].total_seconds() > Config.PARAMETROS_REGIAO[zona].duracao_seg
    return False


# Funções para cálculos
def calcular_indicadores(df: pd.DataFrame, df_motoqueiros: pd.DataFrame, data_final: datetime.date) -> Dict[str, Any]:
    """Calcula os indicadores principais do dashboard."""
    if df.empty:
        return {"erro": "Sem dados para calcular indicadores"}
        
    # Contadores básicos
    entregas = df.shape[0]
    viagens = df['rota_nome'].nunique() if 'rota_nome' in df.columns else 0
    viagens_3p = df.groupby('rota_nome').filter(lambda x: len(x) > 3)['rota_nome'].nunique() if 'rota_nome' in df.columns else 0
    
    # Frete grátis - conta entregas onde valor_frete é zero
    frete_gratis = df[df['valor_frete'] == 0].shape[0] if 'valor_frete' in df.columns else 0
    frete_gratis_perc = frete_gratis / entregas * 100 if entregas else 0
    
    # Devoluções - conta entregas onde devolucao é "SIM"
    devolucoes = df[df['devolucao'] == "SIM"].shape[0] if 'devolucao' in df.columns else 0
    devolucoes_perc = (devolucoes / entregas * 100) if entregas > 0 else 0
    
    # Valores
    valor_nf_total = df['valor_nf'].sum() if 'valor_nf' in df.columns else 0
    valor_frete_total = df['valor_frete'].sum() if 'valor_frete' in df.columns else 0
    
    # Entregas viradas
    entregas_viradas = 0
    if 'Concluida' in df.columns and 'Data' in df.columns:
        entregas_viradas = df[df['Concluida'].dt.date > df['Data']].shape[0]
    entregas_viradas_perc = entregas_viradas / entregas * 100 if entregas else 0
    
    # % Acima tempo ideal
    entregas_acima = 0
    perc_acima = 0
    if 'Concluida' in df.columns and 'Data' in df.columns:
        entregas_validas = df[df['Concluida'].dt.date == df['Data']]
        entregas_acima = entregas_validas.apply(acima_tempo, axis=1).sum()
        perc_acima = (entregas_acima / len(entregas_validas) * 100) if len(entregas_validas) else 0
    
    # Indicadores adicionais
    ticket_medio = valor_nf_total / entregas if entregas else 0
    receita_media_viagem = valor_nf_total / viagens if viagens else 0
    entregas_por_viagem = entregas / viagens if viagens else 0
    motoqueiros_count = df['motoqueiro'].nunique() if 'motoqueiro' in df.columns else 0
    entregas_por_motoqueiro = entregas / motoqueiros_count if motoqueiros_count else 0
    
    # Custo por entrega - com verificação
    custo_total = 0
    resultado_projetado = 0
    resultado = 0
    
    if not df_motoqueiros.empty and 'competencia' in df_motoqueiros.columns:
        df_motoqueiros['competencia'] = pd.to_datetime(df_motoqueiros['competencia'], format='%Y-%m', errors='coerce').dt.strftime('%Y-%m')
        competencia = pd.to_datetime(data_final).strftime('%Y-%m')
        if 'valor_competencia' in df_motoqueiros.columns:
            custo_total = df_motoqueiros[df_motoqueiros['competencia'] == competencia]['valor_competencia'].sum()
            resultado_projetado = float(valor_frete_total) - float(custo_total)
            resultado = (float(valor_frete_total) / float(custo_total) * 100) if float(custo_total) > 0 else 0
    
    custo_por_entrega = round(custo_total / entregas, 1) if entregas else 0
    
    # Formatação tempo médio
    def formatar(td):
        if pd.isnull(td): return "Não definido"
        s = int(td.total_seconds())
        return f"{s // 3600:02}:{(s % 3600) // 60:02}:{s % 60:02}"
    
    tempo_ciclo_medio = "Não definido"
    tempo_rota_medio = "Não definido"
    
    if 'Tempo de Ciclo' in df.columns:
        tempo_ciclo_medio = formatar(df['Tempo de Ciclo'].dropna().mean())
    if 'Tempo de Rota' in df.columns:
        tempo_rota_medio = formatar(df['Tempo de Rota'].dropna().mean())
        
    return {
        "entregas": entregas,
        "viagens": viagens,
        "viagens_3p": viagens_3p,
        "frete_gratis": frete_gratis,
        "frete_gratis_perc": frete_gratis_perc,
        "devolucoes": devolucoes,
        "devolucoes_perc": devolucoes_perc,
        "valor_nf_total": valor_nf_total,
        "valor_frete_total": valor_frete_total,
        "entregas_viradas": entregas_viradas,
        "entregas_viradas_perc": entregas_viradas_perc,
        "entregas_acima": entregas_acima,
        "perc_acima": perc_acima,
        "ticket_medio": ticket_medio,
        "receita_media_viagem": receita_media_viagem,
        "entregas_por_viagem": entregas_por_viagem,
        "motoqueiros_count": motoqueiros_count,
        "entregas_por_motoqueiro": entregas_por_motoqueiro,
        "custo_total": custo_total,
        "resultado_projetado": resultado_projetado,
        "resultado": resultado,
        "custo_por_entrega": custo_por_entrega,
        "tempo_ciclo_medio": tempo_ciclo_medio,
        "tempo_rota_medio": tempo_rota_medio
    }


# Componentes de UI
def render_cartao(titulo: str, valor: Union[str, float, int], moeda: bool = True, percentual: bool = False) -> str:
    """Renderiza um cartão de indicador."""
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


def sidebar_filtros(df: pd.DataFrame) -> Dict[str, Any]:
    """Renderiza a barra lateral com filtros."""
    st.sidebar.title("Dashboard Entregas")
    
    # Mostra última atualização
    st.sidebar.info(f"🕒 Última atualização: {st.session_state.get('ultima_atualizacao', 'Sem registro')}")

    # Botão de atualização
    if st.sidebar.button("🔄 Atualizar Dados", type="primary"):
        with st.spinner("Atualizando os dados em segundo plano..."):
            atualizar_em_segundo_plano()
            st.sidebar.success("Dados atualizados!")

    # Filtros
    st.sidebar.header("Filtros")
    
    # Datas - uso das datas da planilha, se disponíveis
    data_minima = datetime.date(2025, 5, 14)  # Data padrão
    data_maxima = datetime.date(2025, 5, 15)  # Data padrão
    
    if not df.empty and 'Data' in df.columns:
        dates = pd.to_datetime(df['Data']).dropna()
        if not dates.empty:
            data_minima = dates.min().date()
            data_maxima = dates.max().date()
    
    data_inicial = st.sidebar.date_input("Data Inicial", data_minima)
    data_final = st.sidebar.date_input("Data Final", data_maxima)
    
    # Filtros dinâmicos - com verificação de existência de colunas
    zonas = []
    motoqueiros = []
    clientes = []
    vendedores = []

    if not df.empty:
        if 'zona' in df.columns:
            zonas = sorted(df['zona'].dropna().unique().tolist())
        if 'motoqueiro' in df.columns:
            motoqueiros = sorted(df['motoqueiro'].dropna().unique())
        if 'Cliente' in df.columns:
            clientes = sorted(df['Cliente'].dropna().unique())
        if 'vendedor' in df.columns:
            vendedores = sorted(df['vendedor'].dropna().unique())

    zonas_sel = st.sidebar.multiselect("Zona:", zonas)
    motoqueiros_sel = st.sidebar.multiselect("Motoqueiro:", motoqueiros)
    clientes_sel = st.sidebar.multiselect("Cliente:", clientes)
    vendedores_sel = st.sidebar.multiselect("Vendedor:", vendedores)
    
    return {
        "data_inicial": data_inicial,
        "data_final": data_final,
        "zonas": zonas_sel,
        "motoqueiros": motoqueiros_sel,
        "clientes": clientes_sel,
        "vendedores": vendedores_sel
    }


def exibir_painel_indicadores(indicadores: Dict[str, Any], zonas_sel: List[str]) -> None:
    """Exibe os painéis de indicadores."""
    # Indicadores Gerais
    st.subheader("Indicadores Gerais")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(render_cartao("Entregas", indicadores["entregas"], False), unsafe_allow_html=True)
        st.markdown(render_cartao("Viagens", indicadores["viagens"], False), unsafe_allow_html=True)
    with col2:
        st.markdown(render_cartao("Faturamento", indicadores["valor_nf_total"]), unsafe_allow_html=True)
        st.markdown(render_cartao("Receita Frete", indicadores["valor_frete_total"]), unsafe_allow_html=True)
    with col3:          
        st.markdown(render_cartao("Frete Grátis (%)", f"{indicadores['frete_gratis_perc']:.1f}%", False), unsafe_allow_html=True)
        st.markdown(render_cartao("Devoluções (%)", f"{indicadores['devolucoes_perc']:.1f}%", False), unsafe_allow_html=True)
    with col4:
        st.markdown(render_cartao("Entregas Viradas (%)", f"{indicadores['entregas_viradas_perc']:.1f}%", False), unsafe_allow_html=True)
        st.markdown(render_cartao("Entregas Acima do Tempo (%)", f"{indicadores['perc_acima']:.1f}%", False), unsafe_allow_html=True)

    # Indicadores de Desempenho
    st.subheader("Indicadores de Desempenho")
    col5, col6, col7, col8 = st.columns(4)

    with col5:
        st.markdown(render_cartao("Entregas p/ Viagem", indicadores["entregas_por_viagem"], False), unsafe_allow_html=True)
        st.markdown(render_cartao("Viagens com +3 Entregas", indicadores["viagens_3p"], False), unsafe_allow_html=True)
    with col6:
        st.markdown(render_cartao("Ticket Médio", indicadores["ticket_medio"]), unsafe_allow_html=True)
        st.markdown(render_cartao("Custo por Entrega", f"R$ {indicadores['custo_por_entrega']:,.1f}".replace(",", "X").replace(".", ",").replace("X", "."), True), unsafe_allow_html=True)
    with col7:
        st.markdown(render_cartao("Receita Média p/ Viagem", indicadores["receita_media_viagem"]), unsafe_allow_html=True)
        st.markdown(render_cartao("Resultado Projetado", indicadores["resultado_projetado"], True), unsafe_allow_html=True)
    with col8:
        st.markdown(render_cartao("Entregas p/ Motoqueiro", indicadores["entregas_por_motoqueiro"], False), unsafe_allow_html=True)
        st.markdown(render_cartao("Resultado (%)", f"{indicadores['resultado']:.1f}%", False), unsafe_allow_html=True)

    # Parâmetros por Região
    st.subheader("Parâmetros por Região")
    if len(zonas_sel) == 1 and zonas_sel[0] in Config.PARAMETROS_REGIAO:
        zona_info = Config.PARAMETROS_REGIAO[zonas_sel[0]]
        tempo_ideal = zona_info.tempo_ideal
        horario_corte = zona_info.horario_corte
    else:
        tempo_ideal = "Não definido"
        horario_corte = "Não definido"

    col9, col10, col11, col12 = st.columns(4)
    with col9:
        st.markdown(render_cartao("Tempo de Ciclo", indicadores["tempo_ciclo_medio"], False), unsafe_allow_html=True)
    with col10:
        st.markdown(render_cartao("Tempo Parametrizado", tempo_ideal, False), unsafe_allow_html=True)
    with col11:
        st.markdown(render_cartao("Tempo de Rota", indicadores["tempo_rota_medio"], False), unsafe_allow_html=True)
    with col12:
        st.markdown(render_cartao("Horário Corte", horario_corte, False), unsafe_allow_html=True)


def main():
    """Função principal que executa o aplicativo."""
    # Inicialização
    inicializar_app()
    
    # Recarrega a página se a atualização foi concluída
    if st.session_state.get("recarregar", False):
        st.session_state["recarregar"] = False  # reseta
        st.rerun()
    
    # Carrega dados
    df_entregas = carregar_dados()
    df_motoqueiros = carregar_infos()
    
    # Sidebar com filtros
    filtros = sidebar_filtros(df_entregas)
    
    # Verificar se há dados para processar
    if df_entregas.empty:
        st.warning("Não há dados disponíveis para exibir. Verifique se o arquivo 'dados.xlsx' está na raiz do projeto.")
        st.stop()
    
    # Pré-processamento dos dados
    df_entregas = preprocessar_dados(df_entregas)
    
    # Aplicação de filtros
    df_filtrado = aplicar_filtros(df_entregas, filtros)
    
    # Cálculo de indicadores
    indicadores = calcular_indicadores(df_filtrado, df_motoqueiros, filtros["data_final"])
    
    # Exibição do dashboard
    exibir_painel_indicadores(indicadores, filtros["zonas"])
    
    # Adiciona visualização da tabela de dados para debug
    if st.checkbox("Mostrar dados brutos"):
        st.subheader("Dados Brutos")
        st.dataframe(df_filtrado)


if __name__ == "__main__":
    main()