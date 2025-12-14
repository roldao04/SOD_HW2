# 🚀 Quickstart: BASE Portugal Extractor

Guia rápido para testar a extração de dados de Portugal.

---

## ⚡ Setup Rápido (5 minutos)

### 1. Preparar Ambiente

```bash
# Navegar para o diretório do projeto
cd /home/ugo/Desktop/UA/4ano/1semestre/SOD/HW2/SOD_HW2

# Criar e ativar virtual environment
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
pip install openpyxl
```

### 2. Testar Conexão API

```bash
# Verificar se a API responde
python3 src/test_portugal_extractor.py
```

**Output esperado**: ✓ Extractor is ready to download data!

---

## 📥 Extração de Dados

### Opção A: CLI Interativa (Recomendado)

```bash
source venv/bin/activate
python3 -m src.extractors.base_portugal.main
```

1. Menu aparece
2. Digite `1` para extrair
3. Digite `2025` para o ano
4. Aguarde ~2 minutos
5. ✓ Dados salvos em `data/bronze/base_portugal/`

### Opção B: Script Python

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

## 🔄 Processar para Silver Layer

### Opção A: CLI Interativa

```bash
source venv/bin/activate
python3 -m src.processing.base_portugal.main
```

1. Menu aparece
2. Digite `1` para processar Portugal
3. Aguarde ~15 segundos
4. ✓ Parquet criado em `data/silver/base_portugal/`

### Opção B: Script Python

```bash
source venv/bin/activate
python3 << 'EOF'
from src.processing.base_portugal.transformer import process_bronze_directory
from src.processing.base_portugal.parquet_writer import write_to_parquet

# Processar
records = process_bronze_directory('data/bronze/base_portugal', 'portugal')
stats = write_to_parquet(records, 'data/silver/base_portugal', partition_by_date=True)

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

## 🎯 One-Liner Completo

Extração + Processamento + Análise numa só execução:

```bash
source venv/bin/activate && python3 << 'EOF'
from src.extractors.base_portugal.extractor import BasePortugalExtractor
from src.processing.base_portugal.transformer import process_bronze_directory
from src.processing.base_portugal.parquet_writer import write_to_parquet
import pandas as pd

print("1️⃣ Extraindo dados...")
extractor = BasePortugalExtractor()
result = extractor.extract_all(2025)
print(f"   ✓ {result['total_records_saved']:,} contratos extraídos")

print("\n2️⃣ Processando para Silver...")
records = process_bronze_directory('data/bronze/base_portugal', 'portugal')
stats = write_to_parquet(records, 'data/silver/base_portugal', partition_by_date=True)
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

## ✅ Checklist de Teste

- [ ] Virtual environment criado e ativado
- [ ] Dependências instaladas (requests, pandas, pyarrow, openpyxl)
- [ ] Teste de API executado com sucesso
- [ ] Extração completada (~2 min, 209k contratos)
- [ ] Bronze layer criado em `data/bronze/base_portugal/`
- [ ] Transformação completada (~15 seg)
- [ ] Silver layer criado em `data/silver/base_portugal/`
- [ ] Ficheiro Parquet tem ~11 MB
- [ ] Análise rápida mostra dados corretos

---

**Tempo total estimado**: 5-10 minutos (dependendo da velocidade da internet)

**Questões?** Consulta a documentação completa em [docs/portugal_implementation.md](docs/portugal_implementation.md)
