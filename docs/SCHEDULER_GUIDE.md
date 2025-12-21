#  **Guia de Orquestração - Automated Scheduler**

##  **Visão Geral**

Sistema de orquestração automática que:
-  Extrai novos dados de todas as fontes
-  Compara com dados existentes (via state management)
-  Adiciona apenas registos novos
-  Processa Bronze → Silver → Gold
-  Aplica deduplicação automática
-  Faz upload para MinIO

---

##  **Instalação**

### **1. Instalar dependências:**
```bash
pip install -r requirements.txt
```

A biblioteca `schedule>=1.2.0` já está incluída.

### **2. Verificar estrutura:**
```bash
src/scheduler/
├── __init__.py
├── auto_scheduler.py    # ⭐ Scheduler automático (USAR ESTE)
├── scheduler.py         # Pipeline orchestrator
├── config.py            # Configuração
└── pipeline.py          # (Opcional)
```

---

##  **Modos de Execução**

### **1⃣ MODO TESTE (Recomendado para desenvolvimento)**

Executa o pipeline **a cada 5 minutos** (configurável):

```bash
python -m src.scheduler.auto_scheduler test
```

**Output esperado:**
```
TEST SCHEDULER STARTED
Interval: Every 5 minutes
Logs directory: logs/scheduled_runs
Press Ctrl+C to stop
======================================================================
▶  Running FIRST execution immediately...
======================================================================
 SCHEDULED RUN STARTED: 20251221_143052
======================================================================

 PHASE 1: EXTRACTION (Bronze Layer)
======================================================================
▶ Running: Extract base_portugal
 Extract base_portugal completed in 45.2s
...

Next run scheduled for: 2025-12-21 14:35:52
```

**Características:**
-  Executa **imediatamente** na primeira vez
-  Depois repete a cada **5 minutos**
-  Logs em `logs/scheduled_runs/scheduler.log`
-  Para com `Ctrl+C`

---

### **2⃣ MODO PRODUÇÃO (Daily)**

Executa **1x por dia** às **02:00** (configurável):

```bash
python -m src.scheduler.auto_scheduler daily
```

**Para rodar em background (Linux/Mac):**
```bash
nohup python -m src.scheduler.auto_scheduler daily > scheduler.log 2>&1 &
```

**Verificar se está rodando:**
```bash
ps aux | grep auto_scheduler
```

**Parar o scheduler:**
```bash
pkill -f auto_scheduler
# ou encontrar PID e matar:
ps aux | grep auto_scheduler
kill <PID>
```

---

### **3⃣ MODO MANUAL (Once)**

Executa **1 vez** e termina:

```bash
python -m src.scheduler.auto_scheduler once
```

**Ideal para:**
-  Testar o pipeline completo
-  Debugging
-  Execuções pontuais

---

##  **Configuração**

### **Arquivo: `src/scheduler/config.py`**

```python
# Hora de execução diária (formato 24h)
DAILY_RUN_TIME = "02:00"  # 2 AM

# Intervalo de teste (minutos)
TEST_INTERVAL_MINUTES = 5

# Se True, continua pipeline mesmo se um extractor falhar
CONTINUE_ON_ERROR = True

# Se True, faz upload para MinIO após cada fase
UPLOAD_TO_MINIO = True
```

### **Arquivo: `src/scheduler/auto_scheduler.py`**

```python
# No topo do arquivo, podes alterar:
DAILY_RUN_TIME = "02:00"       # Hora da execução diária
TEST_INTERVAL_MINUTES = 5      # Intervalo de teste
```

---

##  **O que o Scheduler faz?**

### **Pipeline Completo:**

```
┌─────────────────────────────────────┐
│  PHASE 1: EXTRACTION (Bronze)       │
├─────────────────────────────────────┤
│   BASE Portugal (API)              │
│   Open Contracting (11 países)     │
│  ⊘ TED (sem extractor)              │
│  ⊘ H&M (dados estáticos)            │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│  PHASE 2: PROCESSING (Silver)       │
├─────────────────────────────────────┤
│   Transform Bronze → Silver        │
│   Data cleaning & validation       │
│   Deduplication                    │
│   Standardization                  │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│  PHASE 3: GOLD LAYER                │
├─────────────────────────────────────┤
│   Unified dataset (all sources)    │
│   Aggregates by country            │
│   Quality metrics                  │
│   Upload to MinIO                  │
└─────────────────────────────────────┘
```

### **State Management (Comparação com dados existentes):**

Cada extractor mantém um ficheiro JSON com o estado:
- **BASE Portugal**: `data/bronze/base_portugal/extraction_state.json`
- **OCP**: `data/bronze/open_contracting_partnership/extraction_state.json`

**O que é guardado:**
```json
{
  "last_extraction": "2025-12-21T14:30:52",
  "total_records": 58418,
  "last_record_id": "2024-02-05T12:34:56",
  "processed_files": [...]
}
```

**Como funciona:**
1. Scheduler invoca extractor
2. Extractor lê `extraction_state.json`
3. API query filtra apenas records **após** `last_record_id`
4. Apenas **novos records** são extraídos
5. State é atualizado com novo `last_record_id`

**Resultado:** Apenas dados novos são processados! 

---

## **Logs e Reports**

### **Logs do Scheduler:**
```
logs/scheduled_runs/
└── scheduler.log    # Log consolidado de todas execuções
```

**Conteúdo:**
```
2025-12-21 14:30:52 - INFO - SCHEDULED RUN STARTED: 20251221_143052
2025-12-21 14:30:52 - INFO - Running: Extract base_portugal
2025-12-21 14:31:37 - INFO - Extract base_portugal completed in 45.2s
...
2025-12-21 14:45:21 - INFO - Scheduled run completed SUCCESSFULLY
```

### **Pipeline Execution Report:**
```
data/pipeline_execution_report.txt
```

**Conteúdo:**
```
======================================================================
 PIPELINE EXECUTION REPORT
======================================================================

Timestamp: 2025-12-21 14:45:21
Duration: 893.2s (14.9 min)

EXTRACTORS:
  - base_portugal: success
  - open_contracting: success

PROCESSORS:
  - base_portugal: success
  - open_contracting: success
  - ted: success
  - henrique_monteiro: success

GOLD LAYER:
  - generation: success
  - upload: success

WARNINGS (0):

ERRORS (0):
```

---

##  **Testes e Debugging**

### **1. Testar pipeline manualmente:**
```bash
# Execução única com logs detalhados
python -m src.scheduler.auto_scheduler once
```

### **2. Testar apenas extraction:**
```bash
python -m src.scheduler.scheduler --extract-only
```

### **3. Testar apenas processing:**
```bash
python -m src.scheduler.scheduler --process-only
```

### **4. Testar apenas Gold layer:**
```bash
python -m src.scheduler.scheduler --gold-only
```

### **5. Testar fontes específicas:**
```bash
python -m src.scheduler.scheduler --sources base_portugal henrique_monteiro
```

---

##  **Monitorização**

### **Verificar última execução:**
```bash
tail -20 logs/scheduled_runs/scheduler.log
```

### **Verificar próxima execução (modo daily):**
O scheduler imprime no log:
```
Next run scheduled for: 2025-12-22 02:00:00
```

### **Estatísticas de execução:**
```bash
# Ver report completo
cat data/pipeline_execution_report.txt

# Verificar Gold layer
python3 << 'EOF'
import pandas as pd
df = pd.read_parquet('data/gold/unified/all_tenders.parquet')
print(f"Total records: {len(df):,}")
print(f"\nRecords por fonte:")
print(df['source'].value_counts())
EOF
```

---

##  **Workflow Recomendado**

### **Para DESENVOLVIMENTO:**
```bash
# 1. Teste inicial (execução única)
python -m src.scheduler.auto_scheduler once

# 2. Se funcionou, teste com scheduler de 5 min
python -m src.scheduler.auto_scheduler test

# 3. Deixar rodar 2-3 ciclos para validar
# 4. Para com Ctrl+C quando validado
```

### **Para PRODUÇÃO:**
```bash
# 1. Configurar horário em config.py
# DAILY_RUN_TIME = "02:00"

# 2. Rodar em background
nohup python -m src.scheduler.auto_scheduler daily > scheduler_prod.log 2>&1 &

# 3. Guardar PID
echo $! > scheduler.pid

# 4. Monitorizar logs
tail -f logs/scheduled_runs/scheduler.log

# 5. Para parar (quando necessário)
kill $(cat scheduler.pid)
```

---

##  **Referências**

- **Scheduler library**: https://schedule.readthedocs.io/
- **Pipeline orchestrator**: `src/scheduler/scheduler.py`
- **Config**: `src/scheduler/config.py`
- **Logs**: `logs/scheduled_runs/scheduler.log`

---

##  **Checklist de Setup**

- [ ] Dependências instaladas (`pip install -r requirements.txt`)
- [ ] MinIO rodando (`docker-compose up -d`)
- [ ] Credenciais configuradas (`.env`)
- [ ] Teste manual funciona (`auto_scheduler once`)
- [ ] Teste com scheduler funciona (`auto_scheduler test`)
- [ ] Logs estão sendo criados (`logs/scheduled_runs/`)
- [ ] Gold layer gerado com sucesso
- [ ] Dremio mostra dados corretos

---

##  **Próximos Passos**

1. **Testar agora**: `python -m src.scheduler.auto_scheduler once`
2. **Se funcionar**: `python -m src.scheduler.auto_scheduler test`
3. **Validar**: Deixar rodar 2-3 ciclos de 5 minutos
4. **Produção**: Configurar `daily` e rodar em background

**Dúvidas?** Consulta os logs em `logs/scheduled_runs/scheduler.log` 
