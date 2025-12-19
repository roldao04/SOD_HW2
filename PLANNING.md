# HW02.2 E-Procurement System - 2-Day Implementation Plan

**Team:** João Roldão & Hugo Castro
**Duration:** 2 full days (16 hours each)
**Timeline:** December 19-20, 2025

---

## Project Overview

### Current State
- ✅ Infrastructure running (MinIO, Dremio, Docker)
- ✅ 2 data sources implemented:
  - BASE Portugal (extractor + processor)
  - Open Contracting Partnership (11 publications)
- ✅ Bronze → Silver pipeline working
- ⚠️ Silver layer has data quality/validation issues
- ❌ Gold layer not implemented
- ❌ Chatbot/NLP system not started
- ❌ Frontend not implemented

### Target State (End of Day 2)
- ✅ 3-4 data sources integrated
- ✅ Clean Bronze → Silver → Gold pipeline
- ✅ Gemini-powered chatbot (SQL + Analytics agents)
- ✅ Streamlit frontend
- ✅ Deduplication working
- ✅ Basic orchestration
- ✅ Complete documentation/report

---

## Architecture

```
┌─────────────────────────────────────────┐
│   Single Frontend (Streamlit)          │
│          "Chat Interface"               │
└───────────────┬─────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│        Gemini Agent (Orchestrator)      │
│  - Intent classification                │
│  - Context management                   │
│  - Response generation                  │
└───────────────┬─────────────────────────┘
                ↓
        ┌───────┴───────┐
        ↓               ↓
┌──────────────┐  ┌─────────────────┐
│  SQL Tool    │  │ Analytics Tool  │
│ (Text→SQL)   │  │ (Insights)      │
└──────┬───────┘  └────────┬────────┘
       └──────────┬─────────┘
                  ↓
    ┌─────────────────────────────┐
    │  Dremio Query Engine        │
    │  - Execute SQL              │
    │  - Return results           │
    │  - Query optimization       │
    └─────────────┬───────────────┘
                  ↓
          ┌───────┴────────┐
          ↓                ↓
    ┌──────────┐    ┌──────────┐
    │  Silver  │    │   Gold   │
    │  (MinIO) │    │ (MinIO)  │
    └──────────┘    └──────────┘
```

### Key Design Decisions
- **Single chat interface** with multi-agent backend
- **Gemini API** for LLM (text-to-SQL + analytics)
- **Dremio as primary query engine** (maximize capabilities)
- **MVP-first approach** (working > perfect)

---

## Day 1: Fix Foundations + Start Advanced Features

### Morning Session (9:00 - 13:00) - 4 hours

#### BOTH: Fix Processors (Parallel Work)

**João's Tasks:**
- [ ] Fix BASE Portugal processor (`src/processing/base_portugal/`)
  - Debug data quality/validation issues
  - Review field mappings in `config.py`
  - Test data transformations in `transformer.py`
  - Verify validators in `validators.py`
  - Test parquet output with sample data
  - Verify Dremio can query the data

**Hugo's Tasks:**
- [ ] Fix Open Contracting processor (`src/processing/open_contracting_partnership/`)
  - Same validation/quality fixes
  - Ensure schema consistency with BASE Portugal
  - Test transformations
  - Verify parquet output quality
  - Test Dremio queries

**Sync Checkpoint (13:00):**
- Both processors producing clean parquet files
- Dremio can query Silver layer from both sources
- Schema is consistent across sources

---

### Afternoon Session (14:00 - 18:00) - 4 hours

#### João: Chatbot Foundation

**1. Dremio Python Integration (1.5 hours)**
- [ ] Install required libraries:
  ```bash
  pip install pyarrow dremio-client google-generativeai
  ```
- [ ] Create `src/api/dremio_client.py`:
  - Connection wrapper class
  - Execute SQL method
  - Fetch results as DataFrame/dict
  - Error handling
- [ ] Test basic SQL execution from Python
- [ ] Document connection settings in `.env`
- [ ] Create example queries script

**2. Chatbot Architecture Setup (2.5 hours)**
- [ ] Install Gemini SDK: `pip install google-generativeai`
- [ ] Create directory structure:
  ```
  src/chatbot/
  ├── __init__.py
  ├── gemini_client.py      # Gemini API wrapper
  ├── sql_agent.py          # Text-to-SQL agent
  ├── analytics_agent.py    # Analytics/insights agent
  ├── prompts.py            # Prompt templates
  └── utils.py              # Helper functions
  ```
- [ ] Implement basic Gemini connection in `gemini_client.py`
- [ ] Create schema introspection:
  - Query Dremio for table schemas
  - Format as context for prompts
  - Cache schema metadata
- [ ] Test simple text-to-SQL prompt:
  - "Show me all tenders in Portugal"
  - Verify SQL generation quality

**Deliverables:**
- Working Dremio Python client
- Gemini connected and responding
- Basic text-to-SQL prototype

---

#### Hugo: Gold Layer + New Data Source

**1. Add UK Contract Finders Data Source (2 hours)**
- [ ] Research UK Contract Finders API/data format
- [ ] Create extractor: `src/extractors/uk_contract_finders/`
  - `extractor.py` - fetch data
  - `config.py` - endpoints, auth
  - `main.py` - entry point
- [ ] Create processor: `src/processing/uk_contract_finders/`
  - Use same Silver schema as other sources
  - Field mappings for UK-specific fields
  - Validation logic
- [ ] Test end-to-end pipeline:
  - Extract → Bronze
  - Process → Silver
  - Verify in Dremio

**2. Start Gold Layer (2 hours)**
- [ ] Create directory: `src/processing/gold/`
- [ ] Implement basic aggregations:
  ```python
  # aggregations.py
  - Tenders by country (count, total value)
  - Tenders by month (time series)
  - Average tender value by procurement category
  - Top 10 buyers by volume
  ```
- [ ] Write aggregations to `data/gold/` as Parquet
- [ ] Configure Gold layer in Dremio:
  - Add MinIO Gold bucket as source
  - Create views/virtual datasets
  - Test queries

**Deliverables:**
- UK Contract Finders data in Silver layer
- Basic Gold layer aggregations
- Dremio can query Gold layer

---

### End of Day 1 Status Check

**Expected Deliverables:**
- ✅ Clean Silver layer from 3 sources (BASE, OCP, UK Contracts)
- ✅ Dremio accessible from Python
- ✅ Gemini chatbot foundation ready
- ✅ Basic Gold layer with aggregations
- ✅ All components tested individually

**Evening (Optional):**
- Review progress
- Adjust Day 2 plan if needed
- Prepare for integration work

---

## Day 2: Complete Advanced Features + Integration

### Morning Session (9:00 - 13:00) - 4 hours

#### João: Complete Chatbot System

**1. SQL Generation Agent (2 hours)**
- [ ] Implement `src/chatbot/sql_agent.py`:
  - Prompt engineering for text-to-SQL
  - Include schema context in prompts
  - Add example queries (few-shot learning)
  - SQL validation before execution
  - Execute via Dremio client
  - Error handling & retry logic
- [ ] Test queries:
  - "Show me all tenders over 1M euros"
  - "Count tenders by country"
  - "Find tenders in Spain published in 2025"
  - "List top 10 buyers by total procurement value"
- [ ] Handle edge cases:
  - Ambiguous queries
  - Invalid SQL generation
  - Empty results

**2. Analytics Agent (2 hours)**
- [ ] Implement `src/chatbot/analytics_agent.py`:
  - Insight generation from SQL results
  - Trend analysis (time series)
  - Aggregation summaries
  - Response formatting (tables, text)
  - Natural language explanations
- [ ] Test analytical queries:
  - "What's the trend in procurement spending this year?"
  - "Which country has the highest average tender value?"
  - "Show me statistics for infrastructure projects"
  - "What are the top procurement categories?"
- [ ] Create response templates in `prompts.py`

**Deliverables:**
- Fully functional SQL agent
- Analytics agent providing insights
- Tested with 10+ query types

---

#### Hugo: Gold Layer + Deduplication

**1. Complete Gold Layer (1.5 hours)**
- [ ] Add advanced aggregations:
  ```python
  - Upcoming deadlines (next 30 days)
  - Top suppliers by award count
  - Regional statistics (if location data available)
  - Procurement trends (month-over-month growth)
  - Category distribution (pie chart data)
  ```
- [ ] Optimize partitioning:
  - Partition by year/month
  - Appropriate file sizes
- [ ] Create Dremio views:
  - `gold.tenders_by_country`
  - `gold.monthly_trends`
  - `gold.top_buyers`
  - `gold.upcoming_deadlines`
- [ ] Verify query performance

**2. Deduplication Logic (2.5 hours)**
- [ ] Create `src/processing/deduplication/` module:
  ```python
  deduplication/
  ├── __init__.py
  ├── blocking.py       # Grouping logic
  ├── matching.py       # Fuzzy matching
  ├── merger.py         # Merge duplicate records
  └── main.py           # Orchestration
  ```
- [ ] Implement blocking strategy:
  - Group by: buyer_name + publication_date (within 7 days)
  - Reduce comparison space
- [ ] Implement fuzzy matching:
  - Use RapidFuzz on tender_title
  - Similarity threshold > 0.85
  - Compare tender values (within 10% range)
- [ ] Merge duplicate records:
  - Keep most complete record
  - Add `is_duplicate` flag
  - Track all source IDs
- [ ] Test with known duplicates from BASE + OCP
- [ ] Write deduplicated data to Gold layer

**Deliverables:**
- Complete Gold layer with 8-10 aggregations
- Working deduplication system
- Test cases showing duplicates found

---

### Sync Checkpoint (13:00)

**Demo session:**
- João: Show chatbot answering SQL + analytical queries
- Hugo: Show Gold layer aggregations + deduplication results
- Discuss integration points

---

### Afternoon Session (14:00 - 18:00) - 4 hours

#### João: Streamlit Frontend

**1. Chat Interface (4 hours)**
- [ ] Create `src/frontend/app.py`:
  ```python
  import streamlit as st
  from chatbot import sql_agent, analytics_agent
  ```
- [ ] Implement UI components:
  - Chat message history (session state)
  - Text input box
  - Send button
  - Loading indicators
- [ ] Connect to chatbot agents:
  - Route user input to appropriate agent
  - Display SQL queries (expandable section)
  - Show results as tables using `st.dataframe()`
  - Show insights as formatted text
- [ ] Add basic filters (sidebar):
  - Country selection (multiselect)
  - Date range picker
  - Value range slider
  - Apply filters to queries
- [ ] Styling & UX:
  - Clean layout
  - Error messages
  - Example queries
  - Help text

**MVP Goal:** Working chat interface, doesn't need to be perfect

**Test scenarios:**
- User asks simple query → See SQL → See results
- User asks analytical question → See insights
- User applies filters → Results update

**Deliverables:**
- Functional Streamlit app
- Chat history working
- Results displayed properly
- Basic filters functional

---

#### Hugo: Data Sources + Orchestration

**1. Add Data Europa Source (2 hours)**
- [ ] Research EU Open Data Portal API
- [ ] Implement extractor: `src/extractors/data_europa/`
  - API calls
  - Data parsing
  - Bronze layer output
- [ ] Implement processor: `src/processing/data_europa/`
  - Schema mapping
  - Validation
  - Silver layer output
- [ ] Test pipeline
- [ ] **FALLBACK:** If Data Europa too complex, implement ComprasPT instead

**2. Basic Orchestration (2 hours)**
- [ ] Create `src/orchestration/scheduler.py`:
  ```python
  # Run all extractors in sequence
  # Run all processors
  # Handle errors gracefully
  # Log results
  ```
- [ ] Implement orchestration logic:
  - List all available extractors
  - Execute each with error handling
  - Process Bronze → Silver for each source
  - Generate summary report
- [ ] Add logging:
  - Records extracted per source
  - Records processed
  - Errors encountered
  - Execution time
- [ ] Create simple CLI:
  ```bash
  python -m src.orchestration.scheduler --sources all
  python -m src.orchestration.scheduler --sources base_portugal
  ```
- [ ] **Alternative:** Simple bash script if Python scheduler too complex

**Deliverables:**
- 4th data source integrated (Data Europa or ComprasPT)
- Orchestration script that runs full pipeline
- Execution logs

---

### End of Day 2 (18:00) - Feature Complete

**Deliverables:**
- ✅ Working chatbot with SQL + Analytics agents
- ✅ Streamlit frontend
- ✅ Gold layer with aggregations
- ✅ Deduplication working
- ✅ 4 data sources total
- ✅ Basic orchestration

---

### Evening Session (18:00 - 22:00) - 4 hours

#### BOTH: Report Writing

**Report Structure:**

1. **Introduction** (Hugo - 30min)
   - Problem statement: E-procurement transparency challenges
   - Project objectives: Multi-source data aggregation + AI-powered search
   - Scope: Data sources, architecture, features

2. **Architecture** (João - 45min)
   - System design diagram (create with draw.io or similar)
   - Medallion pattern explanation (Bronze/Silver/Gold)
   - Technology stack:
     - Storage: MinIO (S3-compatible data lake)
     - Query: Dremio (distributed SQL engine)
     - Processing: Python (pandas, pyarrow)
     - AI: Google Gemini API
     - Frontend: Streamlit
   - Component interactions
   - Data flow diagram

3. **Implementation** (Split - 1.5h total)

   **João writes (45min):**
   - Chatbot System:
     - SQL Agent (text-to-SQL with Gemini)
     - Analytics Agent (insights generation)
     - Prompt engineering techniques
     - Dremio integration
   - Frontend:
     - Streamlit interface design
     - User interaction flow
     - Query visualization

   **Hugo writes (45min):**
   - Data Sources:
     - Source descriptions
     - Extraction strategies
     - Data formats
   - Data Processing:
     - Bronze → Silver transformations
     - Schema unification
     - Data validation
   - Gold Layer:
     - Aggregation types
     - Use cases
   - Deduplication:
     - Blocking strategy
     - Fuzzy matching algorithm
     - Merge logic

4. **Results & Evaluation** (Both - 45min)
   - Demo screenshots:
     - Chatbot conversations
     - Sample queries & results
     - Deduplication examples
     - Gold layer aggregations
   - Data statistics:
     - Total tenders ingested
     - Sources integrated
     - Duplicates found
   - Performance metrics:
     - Query response times
     - Storage sizes
     - Processing times
   - Challenges encountered & solutions

5. **Conclusion & Future Work** (João - 30min)
   - Achievements summary
   - Master's project contribution:
     - Modern data engineering practices
     - AI/LLM integration
     - Distributed systems
     - Real-world problem solving
   - Limitations
   - Future enhancements:
     - More data sources
     - Vector embeddings for semantic search
     - User profiles & recommendations
     - Automated alerts
     - Performance optimizations

**Report Tools:**
- Markdown → Pandoc → PDF
- **OR** Overleaf LaTeX (if template required)
- Include architecture diagrams (draw.io, Mermaid)
- Code snippets for key algorithms

**Work Division:**
- Hugo: Sections 1, 3 (Data parts)
- João: Sections 2, 3 (Chatbot/Frontend), 5
- Both: Section 4 (collaborate on results)

---

## Task Summary by Person

### João's Responsibilities (16 hours)

| Task | Duration | Status |
|------|----------|--------|
| Fix BASE Portugal processor | 4h | Day 1 AM |
| Dremio Python integration | 1.5h | Day 1 PM |
| Chatbot foundation setup | 2.5h | Day 1 PM |
| SQL Generation Agent | 2h | Day 2 AM |
| Analytics Agent | 2h | Day 2 AM |
| Streamlit Frontend | 4h | Day 2 PM |
| **Total** | **16h** | |

**Report Sections:** Architecture, Chatbot Implementation, Frontend, Conclusion

---

### Hugo's Responsibilities (16 hours)

| Task | Duration | Status |
|------|----------|--------|
| Fix OCP processor | 4h | Day 1 AM |
| UK Contract Finders extractor | 2h | Day 1 PM |
| Gold layer (basic) | 2h | Day 1 PM |
| Gold layer (complete) | 1.5h | Day 2 AM |
| Deduplication system | 2.5h | Day 2 AM |
| Data Europa/ComprasPT extractor | 2h | Day 2 PM |
| Orchestration | 2h | Day 2 PM |
| **Total** | **16h** | |

**Report Sections:** Introduction, Data Sources, Processing, Gold Layer, Deduplication

---

## Risk Mitigation

| Risk | Impact | Mitigation Strategy |
|------|--------|---------------------|
| Gemini API issues | High | Keep OpenAI API key as backup |
| Data source blocked/unavailable | Medium | Use cached/sample data; prioritize working sources |
| Dremio connection problems | High | Fallback to direct Pandas queries on Parquet files |
| Deduplication too complex | Low | Start with exact match, fuzzy match if time allows |
| Frontend takes too long | Medium | Use Gradio instead (faster setup than Streamlit) |
| Time overruns | High | Focus on MVP, cut nice-to-have features |
| Integration issues | Medium | Test components individually before integration |
| Report writing rushed | Medium | Start documentation during implementation |

---

## Minimum Viable Deliverables (Critical Path)

### Must Have (Core Requirements)
- ✅ 3 data sources minimum (BASE, OCP, UK Contracts)
- ✅ Working Silver layer with clean data
- ✅ Basic Gold layer (at least 3 aggregations)
- ✅ Chatbot with SQL generation working
- ✅ Simple frontend (terminal or basic Streamlit)
- ✅ Deduplication demo (even on small dataset)
- ✅ Dremio querying data lake
- ✅ Report with architecture + results

### Nice to Have (Time Permitting)
- ⭐ 4th data source
- ⭐ Analytics agent (beyond SQL)
- ⭐ Fancy UI with filters
- ⭐ Automated orchestration
- ⭐ Advanced deduplication metrics
- ⭐ Performance benchmarks

---

## Success Criteria (Master's Project)

### Technical Excellence
- ✅ Multi-source data integration (demonstrates ETL skills)
- ✅ Medallion architecture (industry best practice)
- ✅ Distributed query engine (Dremio - advanced tech)
- ✅ AI/LLM integration (cutting-edge)
- ✅ Clean code & documentation

### Innovation
- ✅ **LLM-powered SQL generation** (unique differentiator)
- ✅ **Natural language interface** for procurement data
- ✅ **Data lake + query engine** architecture (modern approach)

### Practical Value
- ✅ Real-world problem (procurement transparency)
- ✅ Scalable solution (data lake architecture)
- ✅ Usable demo (working frontend)

### Academic Rigor
- ✅ Well-documented architecture
- ✅ Evaluation metrics
- ✅ Challenges & solutions discussed
- ✅ Future work identified

---

## Daily Schedule Template

### Day Structure (8:00 - 18:00)

```
08:00 - 09:00  Setup / Sync
09:00 - 11:00  Deep work session 1
11:00 - 11:15  Coffee break
11:15 - 13:00  Deep work session 2
13:00 - 14:00  Lunch + sync checkpoint
14:00 - 16:00  Deep work session 3
16:00 - 16:15  Coffee break
16:15 - 18:00  Deep work session 4
18:00 - 18:30  Day review + planning
```

### Communication Protocol
- **Sync checkpoints:** 13:00 each day (mandatory)
- **Ad-hoc sync:** Use chat for blockers, don't wait
- **Code sharing:** Push to git frequently
- **Pair programming:** If stuck for >30min, pair up

---

## Development Environment Setup

### Required Dependencies

```bash
# Core data processing
pip install pandas pyarrow fastparquet

# Dremio integration
pip install dremio-client pyarrow-flight

# AI/LLM
pip install google-generativeai

# Frontend
pip install streamlit gradio  # Install both, choose one

# Deduplication
pip install rapidfuzz

# Utilities
pip install python-dotenv requests beautifulsoup4

# Development
pip install pytest black flake8
```

### Environment Variables (.env)

```bash
# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# Dremio
DREMIO_ENDPOINT=localhost:9047
DREMIO_USERNAME=admin
DREMIO_PASSWORD=password123

# Gemini API
GEMINI_API_KEY=your_api_key_here

# Paths
BRONZE_DIR=./data/bronze
SILVER_DIR=./data/silver
GOLD_DIR=./data/gold
```

---

## Testing Checklist

### Before Integration
- [ ] Each extractor produces valid Bronze JSON
- [ ] Each processor produces valid Silver Parquet
- [ ] Dremio can query all Silver sources
- [ ] Gold aggregations return correct results
- [ ] Chatbot generates valid SQL
- [ ] Frontend displays results correctly

### Integration Testing
- [ ] End-to-end pipeline: Extract → Bronze → Silver → Gold
- [ ] Chatbot query → Dremio → Results → Frontend
- [ ] Deduplication finds known duplicates
- [ ] Orchestrator runs all sources successfully
- [ ] Error handling works (simulate failures)

### Demo Preparation
- [ ] Prepare 5-10 example queries
- [ ] Load sample data for all sources
- [ ] Test on clean environment
- [ ] Record screenshots/videos
- [ ] Prepare failure scenarios (show robustness)

---

## Report Checklist

### Content
- [ ] Abstract/Executive Summary
- [ ] Introduction with problem statement
- [ ] Architecture diagrams
- [ ] Implementation details
- [ ] Code snippets for key algorithms
- [ ] Results with metrics/screenshots
- [ ] Evaluation & discussion
- [ ] Conclusion & future work
- [ ] References

### Formatting
- [ ] Consistent heading styles
- [ ] Figure captions
- [ ] Code syntax highlighting
- [ ] Page numbers
- [ ] Table of contents
- [ ] Appendix (if needed)

### Review
- [ ] Spell check
- [ ] Grammar check
- [ ] Technical accuracy
- [ ] Peer review (swap sections)

---

## Quick Reference Commands

### Start Infrastructure
```bash
cd infra
docker-compose up -d
# MinIO: http://localhost:9001
# Dremio: http://localhost:9047
```

### Run Extractors
```bash
python -m src.extractors.base_portugal.main
python -m src.extractors.open_contracting_partnership.main
python -m src.extractors.uk_contract_finders.main
```

### Run Processors
```bash
python -m src.processing.base_portugal.main
python -m src.processing.open_contracting_partnership.main
```

### Run Chatbot (Backend)
```bash
python -m src.chatbot.sql_agent
```

### Run Frontend
```bash
streamlit run src/frontend/app.py
```

### Run Full Pipeline
```bash
python -m src.orchestration.scheduler --sources all
```

---

## Notes & Adjustments

### Day 1 End Review
- What worked well?
- What took longer than expected?
- Adjustments needed for Day 2?

### Day 2 End Review
- All deliverables complete?
- What to prioritize in report?
- Any last-minute fixes needed?

---

**Last Updated:** 2025-12-19
**Status:** Planning Phase
**Next Action:** Start Day 1 - Fix processors
