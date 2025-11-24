# SOD_HW2

## HW 2.2 E-Procurement System

### Team Members
- João Roldão (113920)
- Hugo Castro (113889)

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
  │   ├── extractors/                    # Data source extractors
  │   ├── processing/                    # Data transformation
  │   ├── storage/                       # Storage layer
  │   ├── api/                           # FastAPI application
  │   ├── orchestration/                 # Scheduling & workflows
  │   └── frontend/                      # UI
  │
  ├── docs/                              # Documentation
  │
  ├── .env.example                       # Environment variables template
  └── Makefile                           # Common commands
```