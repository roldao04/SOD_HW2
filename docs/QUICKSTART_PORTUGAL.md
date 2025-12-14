# 🚀 Quickstart: BASE Portugal Extractor

Guia rápido para testar a extração de dados de Portugal com integração MinIO/Dremio.

---

## ⚡ Setup Rápido (5 minutos)

### 1. Preparar Ambiente

```bash
# Navegar para o diretório do projeto
cd /home/roldao/Desktop/MEI/SOD/hw2

# Criar e ativar virtual environment + instalar dependências
make install

# Iniciar serviços Docker (MinIO + Dremio)
make up
```

### 2. Testar Conexão API

```bash
# Verificar se a API responde
python3 src/test_portugal_extractor.py
```

**Output esperado**: ✓ Extractor is ready to download data!

---

## 📥 Extração de Dados

### 🌟 Opção A: Makefile (Recomendado - Novo!)

```bash
# Extração automatizada (CLI mode)
make extract-portugal

# OU: Extração interativa
make extract-portugal-interactive
```

✅ Vantagens:
- Comando simples e consistente
- Sem necessidade de ativar venv manualmente
- Integrado com o workflow geral do projeto

### Opção B: CLI Direta

```bash
source venv/bin/activate

# Modo automatizado
python3 -m src.extractors.base_portugal.main --all

# OU: Modo interativo
python3 -m src.extractors.base_portugal.main
```

### Opção C: Script Python

```bash
source venv/bin/activate
python3 << 'EOF'
from src.extractors.base_portugal.extractor import BasePortugalExtractor

extractor = BasePortugalExtractor()
result = extractor.extract_all(year_filter=2025)

print(f"\n✓ Extraídos {result['total_records_saved']:,} contratos")
print(f"✓ Tempo: {result['duration_seconds']:.0f} segundos")
EOF
```

---

## 🔄 Processar para Silver Layer (com MinIO!)

### 🌟 Opção A: Makefile (Recomendado - Novo!)

```bash
# Processamento automatizado (CLI mode)
# ✅ Escreve em local + MinIO automaticamente
make process-portugal

# OU: Processamento interativo
make process-portugal-interactive
```

✅ **NOVO**: Dual-write automático!
- ✅ Escreve em `data/silver/base_portugal/` (local)
- ✅ Escreve em MinIO bucket `silver/base_portugal/` (objeto storage)
- ✅ Dremio pode aceder aos dados imediatamente

### Opção B: CLI Direta

```bash
source venv/bin/activate

# Modo automatizado (com MinIO)
python3 -m src.processing.base_portugal.main --all

# OU: Modo interativo
python3 -m src.processing.base_portugal.main
```

### Opção C: Script Python

```bash
source venv/bin/activate
python3 << 'EOF'
from src.processing.base_portugal.transformer import process_bronze_directory
from src.processing.base_portugal.parquet_writer import write_to_parquet
from src.storage import MinIOClient, StorageConfig

# Inicializar MinIO client
storage_client = MinIOClient(StorageConfig.from_env())

# Processar com dual-write (local + MinIO)
records = process_bronze_directory('data/bronze/base_portugal', 'portugal')
stats = write_to_parquet(
    records,
    'data/silver/base_portugal',
    partition_by_date=True,
    storage_client=storage_client  # ← Dual-write habilitado!
)

print(f"\n✓ Transformados {stats['records_written']:,} registos")
print(f"✓ Ficheiros criados: {stats['files_written']}")
EOF
```

---

## 📊 Análise Rápida

### Ver Estatísticas

```bash
source venv/bin/activate
python3 << 'EOF'
import pandas as pd

# Ler dados
df = pd.read_parquet('data/silver/base_portugal/portugal/2025/01/')

# Estatísticas
print(f"\nTotal contratos: {len(df):,}")
print(f"Valor total: €{df['tender_value_amount'].sum():,.2f}")
print(f"Valor médio: €{df['tender_value_amount'].mean():,.2f}")
print(f"Valor máximo: €{df['tender_value_amount'].max():,.2f}")

# Top 5 compradores
print("\nTop 5 Compradores:")
print(df['buyer_name'].value_counts().head(5))
EOF
```

### Exportar para CSV (opcional)

```bash
source venv/bin/activate
python3 << 'EOF'
import pandas as pd

df = pd.read_parquet('data/silver/base_portugal/portugal/2025/01/')
df.to_csv('portugal_contratos_2025.csv', index=False)

print(f"✓ Exportado {len(df):,} contratos para portugal_contratos_2025.csv")
EOF
```

---

## 🎯 Pipeline Completo (NOVO!)

### Usando Makefile (Recomendado)

```bash
# 1️⃣ Iniciar serviços
make up

# 2️⃣ Extrair dados
make extract-portugal

# 3️⃣ Processar → Silver (local + MinIO)
make process-portugal

# 4️⃣ Ver estatísticas
make stats

# 5️⃣ Configurar Dremio (primeira vez)
make dremio-setup

# 6️⃣ Abrir Dremio e executar queries SQL!
# → http://localhost:9047
```

### Script One-Liner (Alternativo)

Extração + Processamento + Análise numa só execução:

```bash
source venv/bin/activate && python3 << 'EOF'
from src.extractors.base_portugal.extractor import BasePortugalExtractor
from src.processing.base_portugal.transformer import process_bronze_directory
from src.processing.base_portugal.parquet_writer import write_to_parquet
from src.storage import MinIOClient, StorageConfig
import pandas as pd

print("1️⃣ Extraindo dados...")
extractor = BasePortugalExtractor()
result = extractor.extract_all(2025)
print(f"   ✓ {result['total_records_saved']:,} contratos extraídos")

print("\n2️⃣ Processando para Silver (local + MinIO)...")
storage_client = MinIOClient(StorageConfig.from_env())
records = process_bronze_directory('data/bronze/base_portugal', 'portugal')
stats = write_to_parquet(
    records,
    'data/silver/base_portugal',
    partition_by_date=True,
    storage_client=storage_client
)
print(f"   ✓ {stats['records_written']:,} registos transformados")

print("\n3️⃣ Análise rápida...")
df = pd.read_parquet('data/silver/base_portugal/portugal/2025/01/')
print(f"   Total: {len(df):,} contratos")
print(f"   Valor: €{df['tender_value_amount'].sum():,.2f}")
print(f"\n✅ Pipeline completo executado com sucesso!")
EOF
```

---

## 📁 Verificar Resultados

### Local

```bash
# Ver estrutura criada
tree -L 5 data/

# Ver tamanho dos ficheiros
du -h data/bronze/base_portugal/portugal/2025/01/01/*.json
du -h data/silver/base_portugal/portugal/2025/01/*.parquet

# Contar registos no Bronze
cat data/bronze/base_portugal/portugal/2025/01/01/records_*.json | jq '.count'

# Ver schema do Parquet
pip install parquet-tools
parquet-tools schema data/silver/base_portugal/portugal/2025/01/tenders_*.parquet
```

### MinIO (Novo!)

```bash
# Abrir MinIO Console
# → http://localhost:9001
# Login: minioadmin / minioadmin

# Ou usar MinIO CLI
docker exec sod-minio mc ls myminio/silver/base_portugal/portugal/
```

### Dremio (Novo!)

```SQL
-- Abrir Dremio UI: http://localhost:9047
-- Executar queries SQL diretamente!

-- Exemplo: Top 10 compradores portugueses
SELECT
    buyer_name,
    COUNT(*) as num_contracts,
    SUM(tender_value_amount) as total_value
FROM minio.silver.base_portugal.portugal
WHERE year = '2025'
GROUP BY buyer_name
ORDER BY total_value DESC
LIMIT 10;
```

---

## ❓ Troubleshooting Rápido

### Erro: "No module named 'openpyxl'"
```bash
source venv/bin/activate
pip install openpyxl
```

### Erro: "ModuleNotFoundError: No module named 'src'"
```bash
# Certifica-te que estás no diretório correto
cd /home/ugo/Desktop/UA/4ano/1semestre/SOD/HW2/SOD_HW2
source venv/bin/activate
```

### Erro: "Failed to fetch dataset resources"
```bash
# Verifica conexão internet
curl -I https://dados.gov.pt

# Tenta novamente com mais timeout
# Editar src/extractors/base_portugal/config.py
# REQUEST_CONFIG['timeout'] = 120
```

### Dados não aparecem
```bash
# Verificar se Bronze foi criado
ls -lh data/bronze/base_portugal/portugal/2025/01/01/

# Verificar logs
python3 -m src.extractors.base_portugal.main 2>&1 | grep -i error
```

---

## 📖 Documentação Completa

Para mais detalhes, consulta:
- **[docs/portugal_implementation.md](docs/portugal_implementation.md)** - Documentação técnica completa
- **[docs/data_sources_portugal.md](docs/data_sources_portugal.md)** - Pesquisa de fontes de dados

---

## ✅ Checklist de Teste (Atualizado)

### Setup Inicial
- [ ] Virtual environment criado (`make install`)
- [ ] Docker services iniciados (`make up`)
- [ ] MinIO acessível em http://localhost:9001
- [ ] Dremio acessível em http://localhost:9047

### Pipeline Bronze Layer
- [ ] Extração completada (`make extract-portugal`)
- [ ] Bronze layer criado em `data/bronze/base_portugal/`
- [ ] ~209k contratos extraídos (~2 min)

### Pipeline Silver Layer
- [ ] Transformação completada (`make process-portugal`)
- [ ] ✅ Silver layer LOCAL criado em `data/silver/base_portugal/`
- [ ] ✅ **NOVO**: Silver layer MinIO criado em `silver/base_portugal/` (verificar console MinIO)
- [ ] Ficheiro Parquet tem ~11 MB
- [ ] Dual-write funcionou (local + MinIO)

### Analytics & Querying
- [ ] Dremio configurado (`make dremio-setup`)
- [ ] ✅ **NOVO**: Queries SQL funcionam no Dremio
- [ ] ✅ **NOVO**: Dados acessíveis via `minio.silver.base_portugal`
- [ ] Estatísticas visíveis (`make stats`)

---

**Tempo total estimado**: 10-15 minutos (incluindo setup Docker)

**Workflow recomendado**:
1. `make install && make up` (setup inicial)
2. `make extract-portugal` (extração)
3. `make process-portugal` (processamento → MinIO)
4. `make dremio-setup` (configurar Dremio - apenas 1ª vez)
5. Abrir http://localhost:9047 e executar queries SQL!

**Questões?** Consulta a documentação completa em [docs/portugal_implementation.md](docs/portugal_implementation.md)
