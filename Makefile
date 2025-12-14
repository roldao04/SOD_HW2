# Makefile for E-Procurement System (Docker-based)

# Python environment
VENV = venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip

.PHONY: help install setup up down restart logs extract extract-all extract-interactive process process-all process-interactive stats validate dremio-setup dremio-status dremio-query rebuild clean

help:
	@echo "E-Procurement System - Docker Commands"
	@echo "======================================="
	@echo ""
	@echo "Setup (First Time):"
	@echo "  make install             - Create virtual environment and install dependencies"
	@echo "  make setup               - Complete setup (install + start services)"
	@echo ""
	@echo "Infrastructure:"
	@echo "  make up                  - Start all Docker services (MinIO, Dremio)"
	@echo "  make down                - Stop all Docker services"
	@echo "  make restart             - Restart all Docker services"
	@echo "  make rebuild             - Rebuild and restart containers"
	@echo "  make logs                - View all service logs (follow mode)"
	@echo ""
	@echo "Data Extraction (Bronze Layer):"
	@echo "  make extract-all         - Extract all publications (automated)"
	@echo "  make extract-interactive - Interactive extraction menu"
	@echo "  make extract             - Alias for extract-all"
	@echo ""
	@echo "Data Processing (Silver Layer):"
	@echo "  make process-all         - Process all countries (automated)"
	@echo "  make process-interactive - Interactive processing menu"
	@echo "  make process             - Alias for process-all"
	@echo ""
	@echo "Utilities:"
	@echo "  make stats               - Show Silver layer statistics"
	@echo "  make validate            - Validate Bronze layer structure"
	@echo ""
	@echo "Dremio (SQL Analytics):"
	@echo "  make dremio-setup        - Configure Dremio to connect to MinIO"
	@echo "  make dremio-status       - Check Dremio status"
	@echo "  make dremio-query        - Run test SQL query"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean               - Remove all containers and volumes (destructive!)"
	@echo ""
	@echo "Services will be available at:"
	@echo "  - MinIO Console: http://localhost:9001 (minioadmin/minioadmin)"
	@echo "  - Dremio UI:     http://localhost:9047"
	@echo ""

install:
	@echo "Creating virtual environment..."
	@test -d $(VENV) || python3 -m venv $(VENV)
	@echo "Installing dependencies..."
	@$(PIP) install --upgrade pip
	@$(PIP) install -r requirements.txt
	@echo ""
	@echo "✓ Virtual environment created and dependencies installed"
	@echo ""
	@echo "Next steps:"
	@echo "  - Run 'make up' to start Docker services"
	@echo "  - Run 'make extract' to extract data"

setup: install up
	@echo ""
	@echo "✓ Complete setup finished!"
	@echo ""
	@echo "Services running:"
	@echo "  - MinIO Console: http://localhost:9001"
	@echo "  - Dremio UI:     http://localhost:9047"
	@echo ""
	@echo "Next: Run 'make extract' to extract data"

up:
	@echo "Starting all Docker services..."
	cd infra && docker compose up -d
	@echo ""
	@echo "✓ Services starting in background"
	@echo ""
	@echo "Waiting for services to be ready..."
	@sleep 8
	@echo ""
	@echo "✓ Services should be ready!"
	@echo ""
	@echo "Access points:"
	@echo "  - MinIO Console: http://localhost:9001"
	@echo "  - Dremio UI:     http://localhost:9047"
	@echo ""
	@echo "Run 'make logs' to view logs"

down:
	@echo "Stopping all Docker services..."
	cd infra && docker compose down
	@echo "✓ All services stopped"

restart:
	@echo "Restarting all Docker services..."
	cd infra && docker compose restart
	@echo "✓ Services restarted"

rebuild:
	@echo "Rebuilding and restarting containers..."
	cd infra && docker compose up -d --build
	@echo "✓ Containers rebuilt and restarted"

logs:
	@echo "Showing logs for all services (Ctrl+C to exit)..."
	@echo ""
	cd infra && docker compose logs -f

# Extraction targets
extract-all:
	@echo "Extracting all publications (year 2025)..."
	@echo "This will extract data to local data/bronze/ directory"
	@echo ""
	$(PYTHON) -m src.extractors.open_contracting_partnership.main --all
	@echo ""
	@echo "✓ Extraction complete!"

extract-interactive:
	@echo "Starting interactive extraction menu..."
	@echo ""
	$(PYTHON) -m src.extractors.open_contracting_partnership.main

extract: extract-all

# Processing targets
process-all:
	@echo "Processing all countries..."
	@echo "This will process Bronze → Silver (local + MinIO)"
	@echo ""
	$(PYTHON) -m src.processing.open_contracting_partnership.main --all
	@echo ""
	@echo "✓ Processing complete!"

process-interactive:
	@echo "Starting interactive processing menu..."
	@echo ""
	$(PYTHON) -m src.processing.open_contracting_partnership.main

process: process-all

# Utility targets
stats:
	@echo "Showing Silver layer statistics..."
	@echo ""
	$(PYTHON) -m src.processing.open_contracting_partnership.main --stats

validate:
	@echo "Validating Bronze layer structure..."
	@echo ""
	$(PYTHON) -m src.processing.open_contracting_partnership.main --validate

# Dremio targets
dremio-setup:
	@echo "Configuring Dremio to connect to MinIO..."
	@echo ""
	@echo "This will:"
	@echo "  1. Create MinIO S3 source in Dremio"
	@echo "  2. Configure connection properties"
	@echo "  3. Promote silver/open_contracting_partnership dataset"
	@echo ""
	$(PYTHON) infra/scripts/configure_dremio.py
	@echo ""
	@echo "See infra/dremio-setup.md for usage guide"

dremio-status:
	@echo "Checking Dremio status..."
	@echo ""
	@if docker ps --filter "name=sod-dremio" --format "{{.Status}}" | grep -q "Up"; then \
		echo "Dremio container is running"; \
		echo ""; \
		if curl -s http://localhost:9047 > /dev/null 2>&1; then \
			echo "Dremio UI is accessible at http://localhost:9047"; \
			echo ""; \
			echo "Next steps:"; \
			echo "  1. If this is first time, create admin account at http://localhost:9047"; \
			echo "  2. Run: make dremio-setup"; \
		else \
			echo "Dremio is starting... (wait ~60 seconds)"; \
			echo "Run 'docker logs sod-dremio' to check progress"; \
		fi \
	else \
		echo "Dremio container is not running"; \
		echo "Run: make up"; \
	fi

dremio-query:
	@echo "Running test SQL query on Dremio..."
	@echo ""
	@echo "Query: SELECT source_country, COUNT(*) as total FROM minio.silver.open_contracting_partnership GROUP BY source_country"
	@echo ""
	@echo "Note: This requires Dremio to be configured (run 'make dremio-setup' first)"
	@echo ""
	@echo "For interactive queries, open http://localhost:9047 and use SQL Runner"

# Cleanup
clean:
	@echo "Deleting all data and volumes!"
	cd infra && docker compose down -v
	@echo "All containers and volumes removed"