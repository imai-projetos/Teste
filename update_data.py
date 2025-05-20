import pandas as pd
from pathlib import Path

def atualizar_dados() -> bool:
    """
    Como estamos utilizando um arquivo Excel estático, esta função
    simula uma atualização de dados recarregando o arquivo e salvando
    como parquet.
    
    Returns:
        Boolean indicando sucesso da operação
    """
    try:
        # Caminho do arquivo Excel
        arquivo_excel = Path('dados.xlsx')
        
        # Verifica se o arquivo existe
        if not arquivo_excel.exists():
            print(f"Erro: O arquivo {arquivo_excel} não foi encontrado.")
            return False
            
        # Carrega o arquivo Excel
        df = pd.read_excel(arquivo_excel)
        
        # Diretório para cache
        cache_dir = Path('data')
        cache_dir.mkdir(exist_ok=True)
        
        # Salva como parquet para cache
        df.to_parquet(cache_dir / 'dados.parquet', index=False)
        
        return True
    except Exception as e:
        print(f"Erro ao atualizar dados: {e}")
        return False