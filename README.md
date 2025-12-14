# SOD_HW2

## HW 2.2 E-Procurement System

### Team Members
- João Roldão (113920)
- Hugo Castro (113889)

## Overview

This system extracts, processes, and serves European procurement tender data from multiple sources, providing:
- **Data Lake** (MinIO) for scalable storage
- **SQL Query Engine** (Dremio) for analytics and querying
- **ETL Pipeline** for Bronze → Silver → Gold transformations

### Data Sources

Currently implemented:
- **Open Contracting Partnership**: 11 publications covering UK, Spain, Germany, Albania, Croatia, Italy, and Kosovo

### Repo Structure
```bash
  hw2/
  ├── README.md                          # Project overview
  │
  ├── infra/                             # Infrastructure
  │
  ├── data/                              # Local data (gitignored)
  │   ├── bronze/                        # Raw JSON by source
  │   ├── silver/                        # Cleaned Parquet
  │   └── gold/                          # Aggregates
  │
  ├── src/
  │   ├── api/                           # Application Programming Interface 
  │   ├── extractors/                    # Data source extractors
  │   ├── processing/                    # Data transformation
  │   ├── storage/                       # Storage layer
  │   ├── orchestration/                 # Scheduling & workflows (planned)
  │   └── frontend/                      # UI (planned)
  │
  ├── docs/                              # Documentation
  │
  ├── .env.example                       # Environment variables template
  └── Makefile                           # Common commands
```