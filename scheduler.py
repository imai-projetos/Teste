import schedule
import time
import threading
from update_data import atualizar_dados
from datetime import datetime, timedelta

# Variáveis globais
proxima_execucao = None
ultima_atualizacao = None

def job():
    global proxima_execucao, ultima_atualizacao
    print("🔄 Atualizando dados em segundo plano...")
    
    # Executa a atualização dos dados
    atualizar_dados()
    
    # Atualiza os horários de controle
    ultima_atualizacao = datetime.now().replace(second=0, microsecond=0)
    proxima_execucao = ultima_atualizacao + timedelta(days=1)
    
    print(f"✅ Atualização concluída! Próxima execução agendada para: {proxima_execucao.strftime('%d/%m/%Y %H:%M')}")

# Definindo o agendamento diário
schedule.clear()  # Limpa agendamentos anteriores
schedule.every().day.at("08:30").do(job)

# Inicializa o horário de controle
proxima_execucao = datetime.now().replace(hour=8, minute=30, second=0, microsecond=0)
if proxima_execucao < datetime.now():
    proxima_execucao += timedelta(days=1)

# Função para rodar em segundo plano
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)

# Inicia a thread do agendador
t = threading.Thread(target=run_scheduler, daemon=True)
t.start()

# Funções de interface
def get_proxima_atualizacao():
    return proxima_execucao

def get_ultima_atualizacao():
    return ultima_atualizacao