from connect import buscar_dados
import pandas as pd
import os

CACHE_DIR = 'data'
CACHE_FILE = f'{CACHE_DIR}/dados.parquet'

def atualizar_dados():
    """Função para atualizar os dados de forma incremental."""
    print("🔄 Atualizando dados do Data Lake...")

    # Verifica se o diretório existe
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

    # Verifica se o arquivo existe para identificar o último registro
    if os.path.exists(CACHE_FILE):
        dados_atuais = pd.read_parquet(CACHE_FILE)
        if not dados_atuais.empty:
            ultima_data = dados_atuais['data_hora_nf'].max()
            print(f"Última data encontrada: {ultima_data}")
        else:
            ultima_data = None
    else:
        dados_atuais = pd.DataFrame()
        ultima_data = None

    # Consulta incremental: busca apenas dados novos
    if ultima_data:
        query = f"""
        vw_entregas_vuupt WHERE data_hora_nf > '{ultima_data}'
        """
        novos_dados = buscar_dados(query)
    else:
        # Caso não exista parquet, busca tudo
        novos_dados = buscar_dados('vw_entregas_vuupt')

    if novos_dados is None or novos_dados.empty:
        print("⚠️ Nenhum dado novo encontrado para atualizar.")
        return
    
    print(f"✅ Novos registros encontrados: {len(novos_dados)}")

    # Concatena os dados novos com os antigos e remove duplicidades
    dados_atualizados = pd.concat([dados_atuais, novos_dados]).drop_duplicates()
    
    # Salva no Parquet
    dados_atualizados.to_parquet(CACHE_FILE, index=False)
    print("✅ Atualização incremental concluída com sucesso!")