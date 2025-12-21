# Makefile for E-Procurement System (Docker-based)

# Python environment
VENV = venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip

.PHONY: help install up down restart logs extract extract-all extract-interactive extract-incremental process process-all process-interactive process-incremental stats validate quality-report clean-state gold-layer gold-unified gold-aggregates gold-quality gold-stats dremio-setup dremio-status rebuild clean

help:
	@echo "E-Procurement System - Docker Commands"
	@echo "======================================="
	@echo ""
	@echo "Quick Start:"
	@echo "  make up                  - Setup and start all services (auto-installs if needed)"
	@echo "  make extract             - Extract data from all sources"
	@echo "  make process             - Process all extracted data"
	@echo ""
	@echo "Setup:"
	@echo "  make install             - Install dependencies only (advanced)"
	@echo ""
	@echo "Infrastructure:"
	@echo "  make down                - Stop all Docker services"
	@echo "  make restart             - Restart all Docker services"
	@echo "  make rebuild             - Rebuild and restart containers"
	@echo "  make logs                - View all service logs (follow mode)"
	@echo ""
	@echo "Data Extraction (Bronze Layer):"
	@echo "  make extract-all         - Extract from ALL sources (auto-detects)"
	@echo "  make extract-incremental - Extract new data only (skips already extracted)"
	@echo "  make extract-interactive - Interactive menu to select one source"
	@echo "  make extract             - Alias for extract-all"
	@echo ""
	@echo "Data Processing (Silver Layer):"
	@echo "  make process-all         - Process ALL sources (auto-detects)"
	@echo "  make process-incremental - Process new Bronze files only (skips already processed)"
	@echo "  make process-interactive - Interactive menu to select one source"
	@echo "  make process             - Alias for process-all"
	@echo ""
	@echo "Utilities:"
	@echo "  make stats               - Show statistics for all sources"
	@echo "  make validate            - Validate data structure for all sources"
	@echo "  make quality-report      - Show latest quality validation reports"
	@echo "  make clean-state         - Remove state files (force full re-extraction/processing)"
	@echo ""
	@echo "Gold Layer (Analytics-Ready Data):"
	@echo "  make gold-layer          - Build complete gold layer (unified + aggregates + quality)"
	@echo "  make gold-unified        - Create unified dataset only"
	@echo "  make gold-aggregates     - Generate aggregate tables only"
	@echo "  make gold-quality        - Generate quality reports only"
	@echo "  make gold-stats          - Show gold layer statistics"
	@echo "  make gold-upload         - Upload gold layer to MinIO (for Dremio queries)"
	@echo ""
	@echo "Dremio (SQL Analytics):"
	@echo "  make dremio-setup        - Configure Dremio connection"
	@echo "  make dremio-status       - Check Dremio status"
	@echo ""
	@echo "NLP Chatbot API:"
	@echo "  make chatbot-logs        - View chatbot API logs"
	@echo "  make chatbot-restart     - Restart chatbot service"
	@echo "  make chatbot-rebuild     - Rebuild chatbot container"
	@echo "  make chatbot-shell       - Open shell in chatbot container"
	@echo ""
	@echo "Pipeline Orchestration:"
	@echo "  make orchestrate         - Run complete pipeline (extract + process + gold)"
	@echo "  make orchestrate-extract - Run all extractors only"
	@echo "  make orchestrate-process - Run all processors only"
	@echo "  make orchestrate-gold    - Run gold layer generation only"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean               - Remove all containers and volumes (destructive!)"
	@echo ""
	@echo "Services available at:"
	@echo "  - MinIO Console: http://localhost:9001 (minioadmin/minioadmin)"
	@echo "  - Dremio UI:     http://localhost:9047"
	@echo "  - Chatbot API:   http://localhost:8000/docs"
	@echo ""
	@echo "Note: Ensure GEMINI_API_KEY is set in infra/.env"
	@echo "      Get your free key at: https://ai.google.dev/"
	@echo ""

install:
	@echo "Creating virtual environment..."
	@test -d $(VENV) || python3 -m venv $(VENV)
	@echo "Installing dependencies..."
	@$(PIP) install --upgrade pip
	@$(PIP) install -r infra/requirements.txt
	@echo ""
	@echo "✓ Virtual environment created and dependencies installed"
	@echo ""

up:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Virtual environment not found. Running install..."; \
		echo ""; \
		$(MAKE) install; \
		echo ""; \
	fi
	@echo "Starting all Docker services..."
	cd infra && docker compose up -d
	@echo ""
	@echo "✓ Services starting in background"
	@echo ""
	@echo "Waiting for services to be ready..."
	@sleep 8
	@echo ""
	@echo "✓ Services ready!"
	@echo ""
	@echo "Access points:"
	@echo "  - MinIO Console: http://localhost:9001"
	@echo "  - Dremio UI:     http://localhost:9047"
	@echo "  - Chatbot API:   http://localhost:8000/docs"
	@echo ""
	@echo "Next: Run 'make extract' to extract data"
	@echo "      Run 'make chatbot-test' to test chatbot API"
	@echo "      Run 'make logs' to view all logs"

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
	@echo "Extracting from all sources..."
	@echo "This will extract data to local data/bronze/ directory"
	@echo ""
	@found=0; \
	for dir in src/extractors/*/; do \
		extractor=$$(basename $$dir); \
		if [ "$$extractor" != "__pycache__" ] && [ -f "$$dir/main.py" ]; then \
			echo "→ Running $$extractor extractor..."; \
			$(PYTHON) -m src.extractors.$$extractor.main --all || echo "  ✗ $$extractor failed (continuing...)"; \
			echo ""; \
			found=$$((found + 1)); \
		fi \
	done; \
	if [ $$found -eq 0 ]; then \
		echo "No extractors found!"; \
		exit 1; \
	fi
	@echo "✓ All extractions complete!"

extract-interactive:
	@echo "Available extractors:"; \
	echo ""; \
	i=1; \
	extractors=""; \
	for dir in src/extractors/*/; do \
		extractor=$$(basename $$dir); \
		if [ "$$extractor" != "__pycache__" ] && [ -f "$$dir/main.py" ]; then \
			echo "  $$i) $$extractor"; \
			extractors="$$extractors $$extractor"; \
			i=$$((i + 1)); \
		fi \
	done; \
	if [ $$i -eq 1 ]; then \
		echo "No extractors found!"; \
		exit 1; \
	fi; \
	echo ""; \
	read -p "Select extractor (1-$$((i - 1))): " choice; \
	j=1; \
	selected=""; \
	for ext in $$extractors; do \
		if [ $$j -eq $$choice ]; then \
			selected=$$ext; \
			break; \
		fi; \
		j=$$((j + 1)); \
	done; \
	if [ -z "$$selected" ]; then \
		echo "Invalid selection!"; \
		exit 1; \
	fi; \
	echo ""; \
	echo "Running $$selected extractor..."; \
	echo ""; \
	$(PYTHON) -m src.extractors.$$selected.main

extract: extract-all

# Incremental extraction (NEW)
extract-incremental:
	@echo "Extracting NEW data only (incremental mode)..."
	@echo "This will skip already-extracted publications"
	@echo ""
	@found=0; \
	for dir in src/extractors/*/; do \
		extractor=$$(basename $$dir); \
		if [ "$$extractor" != "__pycache__" ] && [ -f "$$dir/main.py" ]; then \
			echo "→ Running $$extractor extractor (incremental)..."; \
			ENABLE_INCREMENTAL=true $(PYTHON) -m src.extractors.$$extractor.main --all || echo "  ✗ $$extractor failed (continuing...)"; \
			echo ""; \
			found=$$((found + 1)); \
		fi \
	done; \
	if [ $$found -eq 0 ]; then \
		echo "No extractors found!"; \
		exit 1; \
	fi
	@echo "✓ All incremental extractions complete!"

# Processing targets
process-all:
	@echo "Processing all sources..."
	@echo "This will process Bronze → Silver (local + MinIO)"
	@echo ""
	@found=0; \
	for dir in src/processing/*/; do \
		processor=$$(basename $$dir); \
		if [ "$$processor" != "__pycache__" ] && [ -f "$$dir/main.py" ]; then \
			echo "→ Running $$processor processor..."; \
			$(PYTHON) -m src.processing.$$processor.main --all || echo "  ✗ $$processor failed (continuing...)"; \
			echo ""; \
			found=$$((found + 1)); \
		fi \
	done; \
	if [ $$found -eq 0 ]; then \
		echo "No processors found!"; \
		exit 1; \
	fi
	@echo "✓ All processing complete!"

process-interactive:
	@echo "Available processors:"; \
	echo ""; \
	i=1; \
	processors=""; \
	for dir in src/processing/*/; do \
		processor=$$(basename $$dir); \
		if [ "$$processor" != "__pycache__" ] && [ -f "$$dir/main.py" ]; then \
			echo "  $$i) $$processor"; \
			processors="$$processors $$processor"; \
			i=$$((i + 1)); \
		fi \
	done; \
	if [ $$i -eq 1 ]; then \
		echo "No processors found!"; \
		exit 1; \
	fi; \
	echo ""; \
	read -p "Select processor (1-$$((i - 1))): " choice; \
	j=1; \
	selected=""; \
	for proc in $$processors; do \
		if [ $$j -eq $$choice ]; then \
			selected=$$proc; \
			break; \
		fi; \
		j=$$((j + 1)); \
	done; \
	if [ -z "$$selected" ]; then \
		echo "Invalid selection!"; \
		exit 1; \
	fi; \
	echo ""; \
	echo "Running $$selected processor..."; \
	echo ""; \
	$(PYTHON) -m src.processing.$$selected.main

process: process-all

# Individual source processing
process-hm:
	@echo "Processing Henrique & Monteiro partner data..."
	$(PYTHON) -m src.processing.henrique_monteiro.main

# Incremental processing (NEW)
process-incremental:
	@echo "Processing NEW Bronze files only (incremental mode)..."
	@echo "This will skip already-processed files"
	@echo ""
	@found=0; \
	for dir in src/processing/*/; do \
		processor=$$(basename $$dir); \
		if [ "$$processor" != "__pycache__" ] && [ -f "$$dir/main.py" ]; then \
			echo "→ Running $$processor processor (incremental)..."; \
			ENABLE_INCREMENTAL=true $(PYTHON) -m src.processing.$$processor.main --all || echo "  ✗ $$processor failed (continuing...)"; \
			echo ""; \
			found=$$((found + 1)); \
		fi \
	done; \
	if [ $$found -eq 0 ]; then \
		echo "No processors found!"; \
		exit 1; \
	fi
	@echo "✓ All incremental processing complete!"

# Utility targets
stats:
	@echo "Showing Silver layer statistics..."
	@echo ""
	@for dir in src/processing/*/; do \
		processor=$$(basename $$dir); \
		if [ "$$processor" != "__pycache__" ] && [ -f "$$dir/main.py" ]; then \
			echo "=== $$processor ==="; \
			$(PYTHON) -m src.processing.$$processor.main --stats || true; \
			echo ""; \
		fi \
	done

validate:
	@echo "Validating Bronze layer structure..."
	@echo ""
	@for dir in src/processing/*/; do \
		processor=$$(basename $$dir); \
		if [ "$$processor" != "__pycache__" ] && [ -f "$$dir/main.py" ]; then \
			echo "=== $$processor ==="; \
			$(PYTHON) -m src.processing.$$processor.main --validate || true; \
			echo ""; \
		fi \
	done

# Quality reporting (NEW)
quality-report:
	@echo "Showing latest quality validation reports..."
	@echo ""
	@echo "=== Open Contracting Partnership ==="
	@if [ -d "data/silver/open_contracting_partnership/quality_reports" ]; then \
		latest=$$(ls -t data/silver/open_contracting_partnership/quality_reports/*.json 2>/dev/null | head -1); \
		if [ -n "$$latest" ]; then \
			echo "Report: $$latest"; \
			$(PYTHON) -c "import json; report=json.load(open('$$latest')); print(f\"Completeness: {report['completeness_score']:.2%}\"); print(f\"Passed: {report['validation_passed']}, Failed: {report['validation_failed']}\"); print(f\"Warnings: {len(report['summary']['warnings'])}\")"; \
		else \
			echo "No reports found"; \
		fi; \
	else \
		echo "No quality reports directory"; \
	fi
	@echo ""
	@echo "=== Base Portugal ==="
	@if [ -d "data/silver/base_portugal/quality_reports" ]; then \
		latest=$$(ls -t data/silver/base_portugal/quality_reports/*.json 2>/dev/null | head -1); \
		if [ -n "$$latest" ]; then \
			echo "Report: $$latest"; \
			$(PYTHON) -c "import json; report=json.load(open('$$latest')); print(f\"Completeness: {report['completeness_score']:.2%}\"); print(f\"Passed: {report['validation_passed']}, Failed: {report['validation_failed']}\"); print(f\"Warnings: {len(report['summary']['warnings'])}\")"; \
		else \
			echo "No reports found"; \
		fi; \
	else \
		echo "No quality reports directory"; \
	fi

# Clean state files (NEW)
clean-state:
	@echo "Removing state files (this will force full re-extraction/processing)..."
	@echo ""
	@read -p "Are you sure? This will remove extraction and processing state files (y/N): " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		find data -name '*_state.json' -delete 2>/dev/null || true; \
		echo "✓ State files removed"; \
	else \
		echo "Cancelled"; \
	fi

# Gold Layer targets (NEW)
gold-layer:
	@echo "Building complete Gold layer (unified + aggregates + quality)..."
	@echo ""
	$(PYTHON) -m src.gold_layer.main --all
	@echo ""
	@echo "✓ Gold layer build complete!"
	@echo "  - Unified dataset: data/gold/unified/all_tenders.parquet"
	@echo "  - Aggregates: data/gold/aggregates/"
	@echo "  - Quality reports: data/gold/quality/"

gold-unified:
	@echo "Creating unified Gold dataset..."
	@echo ""
	$(PYTHON) -m src.gold_layer.main --unified
	@echo ""
	@echo "✓ Unified dataset created: data/gold/unified/all_tenders.parquet"

gold-aggregates:
	@echo "Generating Gold layer aggregates..."
	@echo ""
	$(PYTHON) -m src.gold_layer.main --aggregates
	@echo ""
	@echo "✓ Aggregates generated: data/gold/aggregates/"

gold-quality:
	@echo "Generating Gold layer quality reports..."
	@echo ""
	$(PYTHON) -m src.gold_layer.main --quality
	@echo ""
	@echo "✓ Quality reports generated: data/gold/quality/"

gold-stats:
	@echo "Showing Gold layer statistics..."
	@echo ""
	$(PYTHON) -m src.gold_layer.main --stats

gold-upload:
	@echo "Uploading Gold layer to MinIO..."
	@echo ""
	$(PYTHON) -m src.gold_layer.upload_to_minio
	@echo ""
	@echo "✓ Gold layer uploaded to MinIO"
	@echo "  Next: Configure Dremio (see docs/dremio_gold_layer_guide.md)"

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
			echo "  3. Use SQL Runner in Dremio UI for queries"; \
		else \
			echo "Dremio is starting... (wait ~60 seconds)"; \
			echo "Run 'docker logs sod-dremio' to check progress"; \
		fi \
	else \
		echo "Dremio container is not running"; \
		echo "Run: make up"; \
	fi

# Orchestration targets
orchestrate:
	@echo "Running complete pipeline orchestration..."
	@echo ""
	$(PYTHON) -m src.orchestration.scheduler
	@echo ""
	@echo "✓ Pipeline orchestration complete"

orchestrate-extract:
	@echo "Running extractors orchestration..."
	@echo ""
	$(PYTHON) -m src.orchestration.scheduler --extract-only
	@echo ""
	@echo "✓ Extraction orchestration complete"

orchestrate-process:
	@echo "Running processors orchestration..."
	@echo ""
	$(PYTHON) -m src.orchestration.scheduler --process-only
	@echo ""
	@echo "✓ Processing orchestration complete"

orchestrate-gold:
	@echo "Running gold layer orchestration..."
	@echo ""
	$(PYTHON) -m src.orchestration.scheduler --gold-only
	@echo ""
	@echo "✓ Gold layer orchestration complete"

orchestrate-sources:
	@echo "Running orchestration for specific sources: $(SOURCES)..."
	@echo ""
	$(PYTHON) -m src.orchestration.scheduler --sources $(SOURCES)
	@echo ""
	@echo "✓ Source orchestration complete"

# Cleanup
clean:
	@echo "Deleting all data and volumes!"
	cd infra && docker compose down -v
	@echo "All containers and volumes removed"

# ===================================================
# NLP Chatbot API Targets (Docker-integrated)
# ===================================================

chatbot-logs:
	@echo "Showing chatbot API logs (Ctrl+C to exit)..."
	@echo ""
	cd infra && docker compose logs -f chatbot-api

chatbot-restart:
	@echo "Restarting chatbot API service..."
	cd infra && docker compose restart chatbot-api
	@echo "✓ Chatbot API restarted"
	@echo "View logs with: make chatbot-logs"

chatbot-rebuild:
	@echo "Rebuilding chatbot API container..."
	cd infra && docker compose up -d --build chatbot-api
	@echo "✓ Chatbot API rebuilt and restarted"
	@echo "View logs with: make chatbot-logs"

chatbot-shell:
	@echo "Opening shell in chatbot API container..."
	cd infra && docker compose exec chatbot-api /bin/bash

chatbot-test:
	@echo "Testing NLP Chatbot API..."
	@echo ""
	@echo "1. Testing health endpoint..."
	@curl -s http://localhost:8000/api/health 2>/dev/null | python3 -m json.tool || echo "⚠️  API not responding. Check: make chatbot-logs"
	@echo ""
	@echo "2. Testing schema endpoint..."
	@curl -s http://localhost:8000/api/schema 2>/dev/null | python3 -m json.tool | head -30 || true
	@echo ""
	@echo "For full API docs, visit: http://localhost:8000/docs"
	@echo "Run 'make chatbot-test-query' to test SQL generation"
	@echo "Run 'make chatbot-test-analytics' to test analytics (requires Dremio)"
	@echo ""

chatbot-test-query:
	@echo "Testing Query Creator Bot (SQL Generation)..."
	@echo ""
	@echo "Sending natural language query: 'Show me the top 10 countries by number of tenders'"
	@echo ""
	@curl -s -X POST http://localhost:8000/api/chat/query-creator \
		-H "Content-Type: application/json" \
		-d '{"message": "Show me the top 10 countries by number of tenders", "include_explanation": true}' \
		2>/dev/null | python3 -m json.tool || echo "⚠️  Query Creator test failed. Check: make chatbot-logs"
	@echo ""

chatbot-test-analytics:
	@echo "Testing Analytics Bot (Query Execution + Insights)..."
	@echo ""
	@echo "Executing sample SQL query and generating insights..."
	@echo ""
	@curl -s -X POST http://localhost:8000/api/chat/analytics \
		-H "Content-Type: application/json" \
		-d '{"sql": "SELECT source_country, COUNT(*) as tender_count FROM minio.gold.unified GROUP BY source_country ORDER BY tender_count DESC LIMIT 5", "message": "Focus on top countries and trends", "include_visualizations": true}' \
		2>/dev/null | python3 -m json.tool || echo "⚠️  Analytics test failed. Dremio may not be connected. Check: make chatbot-logs"
	@echo ""

chatbot-test-all:
	@echo "Running comprehensive chatbot tests..."
	@echo ""
	$(MAKE) chatbot-test
	@echo ""
	$(MAKE) chatbot-test-query
	@echo ""
	$(MAKE) chatbot-test-analytics

.PHONY: chatbot-logs chatbot-restart chatbot-rebuild chatbot-shell chatbot-test chatbot-test-query chatbot-test-analytics chatbot-test-all
