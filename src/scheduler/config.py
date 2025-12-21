"""
Orchestration Configuration
Configuração de scheduling e pipeline
"""
from pathlib import Path
from typing import Dict, Any

# ============================================================
# SCHEDULING CONFIG
# ============================================================

# Hora de execução diária (formato 24h)
DAILY_RUN_TIME = "02:00"  # 2 AM - evita horário de pico

# Intervalo de teste (em minutos) - para desenvolvimento/teste
TEST_INTERVAL_MINUTES = 5

# ============================================================
# PIPELINE CONFIG
# ============================================================

# Ordem de execução dos extractors
EXTRACTOR_ORDER = [
    'base_portugal',              # Primeiro: dados nacionais
    'open_contracting_partnership',  # Segundo: dados internacionais
    'ted',                         # Terceiro: dados europeus
    # henrique_monteiro não tem extractor (dados estáticos)
]

# Ordem de execução dos processors
PROCESSOR_ORDER = [
    'base_portugal',
    'open_contracting_partnership', 
    'ted',
    'henrique_monteiro',
]

# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs" / "orchestration"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# EXECUTION FLAGS
# ============================================================

# Se True, continua pipeline mesmo se um extractor falhar
CONTINUE_ON_ERROR = True

# Se True, executa deduplicação após cada fonte
DEDUPLICATE_PER_SOURCE = True

# Se True, faz upload para MinIO após cada fase
UPLOAD_TO_MINIO = True

# ============================================================
# NOTIFICATIONS (Opcional - para futuro)
# ============================================================

ENABLE_EMAIL_NOTIFICATIONS = False
ENABLE_SLACK_NOTIFICATIONS = False

# ============================================================
# RETRY CONFIG
# ============================================================

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 60  # 1 minuto entre retries
