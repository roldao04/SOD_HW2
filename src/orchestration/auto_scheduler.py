"""
Automated Scheduler with Daily Runs

Implementa scheduling automático com:
- Execuções diárias em horário configurado
- Modo teste com execuções frequentes
- Comparação com dados existentes (via state management)
- Deduplicação automática
"""
import schedule
import time
import logging
from datetime import datetime
from pathlib import Path

from .scheduler import PipelineOrchestrator

# ============================================================
# CONFIGURATION
# ============================================================

# Horário de execução diária (formato 24h)
DAILY_RUN_TIME = "2:00"  # 2 AM

# Intervalo para testes (minutos)
TEST_INTERVAL_MINUTES = 5

# Logging
LOGS_DIR = Path('logs/scheduled_runs')
LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / 'scheduler.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('auto_scheduler')


# ============================================================
# SCHEDULED JOB
# ============================================================

def scheduled_pipeline_run():
    """
    Job agendado que executa o pipeline completo.
    
    Processo:
    1. Extrai novos dados de todas as fontes
    2. State management compara com dados existentes
    3. Adiciona apenas registos novos
    4. Processa Bronze → Silver → Gold
    5. Aplica deduplicação
    """
    run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    logger.info("=" * 70)
    logger.info(f"SCHEDULED RUN STARTED: {run_id}")
    logger.info("=" * 70)
    logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Cria orchestrator
        orchestrator = PipelineOrchestrator()
        
        # Executa pipeline completo
        # O state management em cada extractor já compara com dados existentes
        # e extrai apenas novos
        success = orchestrator.run_full_pipeline(sources=None)  # None = todas as fontes
        
        if success:
            logger.info("Scheduled run completed SUCCESSFULLY")
        else:
            logger.error("Scheduled run completed WITH ERRORS")
            
        logger.info("=" * 70)
        
        return success
        
    except Exception as e:
        logger.error(f"Scheduled run CRASHED: {e}")
        import traceback
        logger.error(traceback.format_exc())
        logger.info("=" * 70)
        return False


# ============================================================
# SCHEDULER MODES
# ============================================================

def run_daily_scheduler():
    """
    MODO PRODUÇÃO: Executa diariamente no horário configurado.
    
    Use este modo para produção. Pipeline roda automaticamente
    todos os dias às {DAILY_RUN_TIME}.
    
    Como rodar em background (Linux):
        nohup python -m src.orchestration.auto_scheduler daily > scheduler.log 2>&1 &
    """
    logger.info("DAILY SCHEDULER STARTED")
    logger.info(f"Scheduled time: {DAILY_RUN_TIME} (daily)")
    logger.info(f"Logs directory: {LOGS_DIR}")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 70)
    
    # Agenda execução diária
    schedule.every().day.at(DAILY_RUN_TIME).do(scheduled_pipeline_run)
    
    # Mostra próxima execução
    next_run = schedule.next_run()
    logger.info(f"Next run scheduled for: {next_run}")
    
    # Loop infinito
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check a cada minuto
            
    except KeyboardInterrupt:
        logger.info("\nScheduler stopped by user")


def run_test_scheduler():
    """
    MODO TESTE: Executa a cada N minutos para desenvolvimento.
    
    Use este modo para testar o scheduler. Pipeline roda
    a cada {TEST_INTERVAL_MINUTES} minutos.
    
    Executa imediatamente na primeira vez.
    """
    logger.info("TEST SCHEDULER STARTED")
    logger.info(f"Interval: Every {TEST_INTERVAL_MINUTES} minutes")
    logger.info(f"Logs directory: {LOGS_DIR}")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 70)
    
    # Executa imediatamente
    logger.info("Running FIRST execution immediately...")
    scheduled_pipeline_run()
    
    # Agenda execuções periódicas
    schedule.every(TEST_INTERVAL_MINUTES).minutes.do(scheduled_pipeline_run)
    
    # Mostra próxima execução
    next_run = schedule.next_run()
    logger.info(f"\nNext run scheduled for: {next_run}")
    
    # Loop infinito
    try:
        while True:
            schedule.run_pending()
            time.sleep(30)  # Check a cada 30 segundos
            
    except KeyboardInterrupt:
        logger.info("\nScheduler stopped by user")


def run_once():
    """
    MODO MANUAL: Executa uma vez e termina.
    
    Use este modo para execuções manuais ou testes únicos.
    """
    logger.info("MANUAL EXECUTION (run once)")
    logger.info("=" * 70)
    
    success = scheduled_pipeline_run()
    
    if success:
        logger.info("Manual execution completed SUCCESSFULLY")
        return 0
    else:
        logger.error("Manual execution completed WITH ERRORS")
        return 1


# ============================================================
# CLI ENTRY POINT
# ============================================================

def main():
    """Entry point com seleção de modo"""
    import sys
    
    print("\n" + "=" * 70)
    print(" E-PROCUREMENT PIPELINE AUTO-SCHEDULER")
    print("=" * 70)
    
    if len(sys.argv) < 2:
        print("\nERROR: Mode not specified\n")
        print("Usage: python -m src.orchestration.auto_scheduler <mode>\n")
        print("Modes:")
        print("  daily  - Run daily at configured time (PRODUCTION)")
        print("  test   - Run every N minutes (DEVELOPMENT)")
        print("  once   - Run once and exit (MANUAL)\n")
        print("Examples:")
        print("  python -m src.orchestration.auto_scheduler daily")
        print("  python -m src.orchestration.auto_scheduler test")
        print("  python -m src.orchestration.auto_scheduler once\n")
        print(f"Configuration:")
        print(f"  Daily run time: {DAILY_RUN_TIME}")
        print(f"  Test interval: {TEST_INTERVAL_MINUTES} minutes")
        print(f"  Logs directory: {LOGS_DIR}\n")
        sys.exit(1)
    
    mode = sys.argv[1].lower()
    
    print(f"\n✓ Mode selected: {mode.upper()}\n")
    
    if mode == 'daily':
        run_daily_scheduler()
    elif mode == 'test':
        run_test_scheduler()
    elif mode == 'once':
        exit_code = run_once()
        sys.exit(exit_code)
    else:
        print(f"ERROR: Unknown mode '{mode}'")
        print("Valid modes: daily, test, once\n")
        sys.exit(1)


if __name__ == '__main__':
    main()
