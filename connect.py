import pandas as pd
from pathlib import Path

def buscar_dados(nome_tabela: str) -> pd.DataFrame:
    """
    Como estamos utilizando um arquivo Excel estático, esta função
    agora simplesmente retorna os dados desse arquivo.
    
    Args:
        nome_tabela: nome da tabela (não utilizado, mantido por compatibilidade)
        
    Returns:
        DataFrame com os dados
    """
    try:
        # Caminho do arquivo Excel
        arquivo_excel = Path('dados.xlsx')
        
        # Verifica se o arquivo existe
        if not arquivo_excel.exists():
            print(f"Erro: O arquivo {arquivo_excel} não foi encontrado.")
            return pd.DataFrame()
            
        # Carrega o arquivo Excel
        df = pd.read_excel(arquivo_excel)
        
        return df
    except Exception as e:
        print(f"Erro ao buscar dados: {e}")
        return pd.DataFrame()