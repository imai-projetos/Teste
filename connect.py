import pandas as pd
import psycopg2
import os

from dotenv import load_dotenv
load_dotenv()

# Informações de conexão
conn_info = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

def buscar_dados(tabela):
    """Retorna os dados de uma tabela como DataFrame, sem limite de linhas."""
    conn = None
    cursor = None
    
    try:
        # Estabelecendo a conexão
        conn = psycopg2.connect(**conn_info)
        print("Conexão bem-sucedida!")
        
        # Criando um cursor para executar consultas
        cursor = conn.cursor()
        
        # Executando a consulta SQL (sem limite)
        query = f'SELECT * FROM {tabela}' 
        cursor.execute(query)
        
        # Pegando o cabeçalho (nomes das colunas)
        colnames = [desc[0] for desc in cursor.description]
        
        # Pegando todos os dados da consulta
        rows = cursor.fetchall()
        
        # Criando um DataFrame
        df = pd.DataFrame(rows, columns=colnames)
        return df
    
    except Exception as e:
        print("Erro na conexão ou consulta:", e)
        return None
    
    finally:
        # Fechando a conexão com segurança
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()