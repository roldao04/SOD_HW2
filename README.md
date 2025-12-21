# E-Procurement Data Pipeline

## HW 2.2 - European Public Procurement Multi-Source Data Integration

### Team Members
- João Roldão (113920)
- Hugo Castro (113889)

---

## Overview

A comprehensive data engineering system that extracts, processes, and analyzes European public procurement tender data from multiple sources. Built using modern data lake architecture with medallion pattern (Bronze → Silver → Gold layers).

### Key Features

- **Multi-Source Integration**: Aggregates procurement data from 3+ European data sources
- **Scalable Data Lake**: MinIO-based object storage for petabyte-scale data
- **Distributed SQL Analytics**: Dremio query engine for high-performance analytics
- **Medallion Architecture**: Bronze (raw) → Silver (cleaned) → Gold (aggregated) layers
- **Unified Schema**: Standardized OCDS-based schema across all sources
- **Data Quality Pipeline**: Validation, deduplication, and quality reporting

---

## Current Status

### Data Sources Implemented

| Source | Countries | Records | Status |
|--------|-----------|---------|--------|
| **Open Contracting Partnership** | 7 (DE, UK, IT, HR, XK, AL, ES) | 462K+ | ✅ Production |
| **BASE Portugal** | Portugal | 213K+ | ✅ Production |
| **TED (Partner Data)** | EU-wide | 17K+ | ✅ Production |
| **TOTAL** | **8+** | **~537K** | **✅ Operational** |

### Pipeline Statistics

- **Bronze Layer**: 2,447 JSON files (raw data)
- **Silver Layer**: 1,097 Parquet files (cleaned, normalized)
- **Gold Layer**: 6 datasets (unified + 5 aggregates)
- **Total Records**: ~536,778 tenders
- **Date Range**: 2016-2025
- **Storage Format**: Apache Parquet (Snappy compression)

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  DATA SOURCES (Open Contracting, BASE, TED, etc.)      │
└──────────────────────┬──────────────────────────────────┘
                       ↓
           ┌───────────────────────┐
           │   EXTRACTORS          │
           │  (Python + Requests)  │
           └───────────┬───────────┘
                       ↓
┌─────────────────────────────────────────────────────────┐
│  BRONZE LAYER (MinIO Data Lake)                         │
│  • Raw JSON files                                       │
│  • Source-specific schemas                              │
│  • Partitioned by: source/country/year/month/day        │
└──────────────────────┬──────────────────────────────────┘
                       ↓
           ┌───────────────────────┐
           │  PROCESSORS           │
           │  (Pandas + PyArrow)   │
           └───────────┬───────────┘
                       ↓
┌─────────────────────────────────────────────────────────┐
│  SILVER LAYER (MinIO Data Lake)                         │
│  • Cleaned Parquet files                                │
│  • Unified 27-field schema                              │
│  • Validated & normalized                               │
│  • Partitioned by: source/country/year/month            │
└──────────────────────┬──────────────────────────────────┘
                       ↓
           ┌───────────────────────┐
           │  GOLD PROCESSOR       │
           │  (Unifier + Aggregator)│
           └───────────┬───────────┘
                       ↓
┌─────────────────────────────────────────────────────────┐
│  GOLD LAYER (MinIO Data Lake)                           │
│  • unified/all_tenders.parquet (536K records)           │
│  • aggregates/ (country, monthly, categories, etc.)     │
│  • quality/ (quality reports)                           │
└──────────────────────┬──────────────────────────────────┘
                       ↓
           ┌───────────────────────┐
           │    DREMIO             │
           │  (Query Engine)       │
           └───────────┬───────────┘
                       ↓
           ┌───────────────────────┐
           │  API / FRONTEND       │
           │  (Planned)            │
           └───────────────────────┘
```

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.10+
- 8GB+ RAM (for Dremio)

### 1. Start Infrastructure

```bash
cd infra
docker-compose up -d
```

Services:
- **MinIO Console**: http://localhost:9001 (minioadmin / minioadmin)
- **Dremio UI**: http://localhost:9047 (admin / password123)

### 2. Setup Python Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run Data Pipeline

```bash
# Extract data from sources (Bronze layer)
make extract

# Process to Silver layer
make process

# Generate Gold layer
make gold-layer

# View statistics
make stats
```

### 4. Query with Dremio

1. Open http://localhost:9047
2. Refresh MinIO source metadata
3. Format gold/unified and gold/aggregates as Parquet
4. Run SQL queries:

```sql
-- Total tenders
SELECT COUNT(*) FROM minio.gold.unified;

-- Top 5 countries
SELECT source_country, COUNT(*) as count
FROM minio.gold.unified
GROUP BY source_country
ORDER BY count DESC
LIMIT 5;
```

---

## Repository Structure

```
hw2/
├── README.md                          # This file
├── Makefile                           # Common commands
├── .env.example                       # Environment template
│
├── infra/                             # Infrastructure
│   ├── docker-compose.yml             # MinIO + Dremio setup
│   └── dremio-setup.md                # Dremio configuration guide
│
├── data/                              # Local data (gitignored)
│   ├── bronze/                        # Raw JSON (2,447 files)
│   ├── silver/                        # Cleaned Parquet (1,097 files)
│   └── gold/                          # Aggregates (6 files)
│
├── src/
│   ├── extractors/                    # Data source extractors
│   │   ├── open_contracting_partnership/
│   │   └── base_portugal/
│   ├── processing/                    # Bronze → Silver transformers
│   │   ├── open_contracting_partnership/
│   │   ├── base_portugal/
│   │   └── ted/
│   ├── gold_layer/                    # Silver → Gold aggregation
│   │   ├── unifier.py                 # Merge sources
│   │   ├── aggregator.py              # Pre-computed aggregates
│   │   └── quality.py                 # Quality reports
│   ├── storage/                       # MinIO client
│   ├── common/                        # Shared utilities
│   └── api/                           # API (planned)
│
└── docs/                              # Documentation
    ├── data_sources_european.md       # European source validation
    ├── data_sources_portugal.md       # Portugal source details
    ├── development_guide.md           # Development workflow
    ├── architecture.md                # System architecture
    └── data_layers.md                 # Bronze/Silver/Gold specs
```

---

## Technology Stack

### Infrastructure
- **MinIO**: S3-compatible object storage (data lake)
- **Dremio**: Distributed SQL query engine
- **Docker Compose**: Container orchestration

### Data Processing
- **Python 3.10+**: Primary language
- **Pandas**: Data manipulation
- **PyArrow**: Parquet I/O and schema enforcement
- **Requests**: HTTP API calls

### Data Formats
- **Bronze**: JSON (OCDS format)
- **Silver**: Apache Parquet (Snappy compression)
- **Gold**: Apache Parquet (partitioned)

---

## Available Commands

```bash
# Infrastructure
make infra-up              # Start MinIO + Dremio
make infra-down            # Stop infrastructure
make infra-clean           # Clean all data

# Data Extraction (Bronze Layer)
make extract               # Extract from all sources
make extract-ocp           # Extract Open Contracting Partnership
make extract-portugal      # Extract BASE Portugal

# Data Processing (Silver Layer)
make process               # Process all sources
make process-incremental   # Process only new data

# Gold Layer
make gold-layer            # Generate unified dataset + aggregates
make gold-stats            # Show gold layer statistics

# Utilities
make stats                 # Show pipeline statistics
make quality-report        # Generate data quality report
make help                  # Show all commands
```

---

## Documentation

- **[Architecture](docs/architecture.md)**: System design, components, and data flow
- **[Data Layers](docs/data_layers.md)**: Bronze/Silver/Gold layer specifications
- **[Data Sources - European](docs/data_sources_european.md)**: European source validation
- **[Data Sources - Portugal](docs/data_sources_portugal.md)**: Portugal-specific sources
- **[Development Guide](docs/development_guide.md)**: Development workflow and phases

---

## Project Goals

1. **Multi-Source Integration**: Aggregate procurement data from diverse European sources
2. **Data Standardization**: Unified schema for cross-country analysis
3. **Scalable Architecture**: Support millions of records with medallion pattern
4. **Analytics Ready**: Enable SQL queries and business intelligence
5. **Data Quality**: Validation, deduplication, and quality reporting

---

## License

Academic project for MEI/SOD course. Data sources may have individual licenses (see docs/).

---

## Contact

- João Roldão - 113920
- Hugo Castro - 113889

**Course**: Data Storage and Processing (SOD)
**Institution**: University of Aveiro
**Year**: 2024/2025