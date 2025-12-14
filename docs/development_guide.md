# HW02.2 E-Procurement System - Development Guide

## Phase 0: Data Source Validation
**Goal:** Verify we have enough accessible data sources

### Tasks
1. **Divide sources between partners**
   - Partner H: BASE, VORTAL, AcinGov, ComprasPT, Open Tender Portugal
   - Partner J: EU Tenders, AnoGov, AMT, UK Contracts Finder, Open Tender France, EU Open Data Portal

2. **For each source, check:**
   - Can access without login?
   - Has API / scraping possible?
   - Find 10-20 sample tenders
   - Document fields available (title, value, deadline, etc.)

3. **Decision criteria:**
   - ✅ Proceed if ≥3 sources have good data
   - ❌ Pivot to HW02.1 if <3 sources

---

## Phase 1: Single Source MVP (2 weeks)
**Goal:** Complete pipeline for one source (Bronze → Silver → Query)

### Ingestion + Storage
```bash
# 1. Setup infrastructure (Docker Compose)
- MinIO (data lake)
- PostgreSQL (metadata)
- Dremio (query engine)

# 2. Build first extractor
- Choose easiest source (probably BASE)
- Extract tenders to JSON
- Save to Bronze layer (/bronze/SOURCE/YYYY/MM/DD/)

# 3. Validate
- Run extractor, verify JSON in MinIO
```

### Processing + Query
```bash
# 4. Silver processing
- Read Bronze JSON
- Normalize schema (common fields across sources)
- Clean data (dates, values, text)
- Save as Parquet (/silver/tenders/)

# 5. Configure Dremio
- Add MinIO source
- Create view over Silver layer
- Test SQL queries

# 6. Simple API (FastAPI)
- GET /tenders (with filters)
- GET /tenders/{id}
```

**Deliverable:** Working end-to-end for one source

---

## Phase 2: Multi-Source + Deduplication

### Add More Sources
```bash
# 7. Implement 3-4 more extractors
- Each partner: 2 extractors
- Same pattern as first extractor
- All output common JSON schema

# 8. Orchestration
- Simple scheduler (run every 6 hours)
- Error handling per source
```

### Deduplication
```bash
# 9. Object matching
- Blocking: group by date + authority
- Fuzzy matching: title + description similarity
- Merge duplicates in Silver layer

# 10. Gold layer
- Aggregates: tenders by category, region
- Analytics: upcoming deadlines, statistics
```

**Deliverable:** Multi-source system with clean, deduplicated data

---

## Phase 3: Search + Recommendations

```bash
# 11. Enhanced search API
- Filters: category, value range, deadline, region
- Keyword search in title/description
- Sort by relevance/date

# 12. User profiles (PostgreSQL)
- Store: interested categories, regions, value ranges
- API: create/update profile

# 13. Recommendation engine
- Score tenders against user profile
- GET /users/{id}/recommendations

# 14. Daily digest (optional)
- Scheduled job
- Email top recommendations

# 15. Vector embeddings for semantic search (optional enhancement)
- Generate embeddings for tender titles + descriptions
- Use sentence-transformers or OpenAI embeddings
- Store in vector database (ChromaDB/Qdrant)

# 16. RAG query endpoint (optional enhancement)
- POST /query - Natural language questions
- "Find infrastructure projects in Spain over 2M euros"
- Vector search → Retrieve from Dremio → LLM summarization
- LangChain or LlamaIndex integration

# 17. Semantic deduplication (optional enhancement)
- Find similar tenders via embedding similarity
- Cosine similarity > 0.9 → potential duplicates
- LLM validation for duplicate confirmation
- Show in Gold layer

# 18. Frontend interface (optional enhancement)
- Chat-based UI (Streamlit or React)
- Natural language query input
- Display AI responses + tender cards
- Interactive filters and results

# 19. LLM integration (optional enhancement)
- OpenAI GPT-4 or Claude API
- Query understanding and response generation
- Summarization of multiple tenders
```

**Deliverable:** Intelligent search and personalization (+ optional RAG/NLP system)

---

## Phase 4: Documentation + Polish 

```bash
# 15. Documentation
- Architecture diagram (layers, components)
- API documentation (endpoints, examples)
- Deployment instructions (Docker setup)

# 16. Testing
- Validate data quality
- Test API endpoints
- Performance checks

# 17. Demo preparation
- Sample queries
- Show deduplication working
- Present architecture
```

**Deliverable:** Complete documented system

---

## Architecture (Medallion Pattern)

```
DATA SOURCES → EXTRACTORS → BRONZE (raw JSON)
                              ↓
                           SILVER (cleaned Parquet)
                              ↓
                           GOLD (aggregates)
                              ↓
                           DREMIO (SQL queries)
                              ↓
                    ┌─────────┴─────────┐
                    ↓                   ↓
                 API              VECTOR DB + LLM (optional)
              (REST/CRUD)         (RAG/Semantic Search)
                    ↓                   ↓
                    └─────────┬─────────┘
                              ↓
                          FRONTEND
                            (User)
```

---

## Key Technologies

- **Storage:** MinIO (data lake), PostgreSQL (metadata)
- **Query:** Dremio (distributed SQL engine)
- **Processing:** Python (pandas, pyarrow)
- **Extraction:** requests, BeautifulSoup, Selenium
- **Deduplication:** RapidFuzz (fuzzy matching)
- **API:** FastAPI
- **Orchestration:** schedule / APScheduler

---

## Success Metrics

1. ✅ ≥3 data sources integrated
2. ✅ Bronze/Silver/Gold layers implemented
3. ✅ Deduplication working (show same tender from 2 sources)
4. ✅ Dremio querying data lake
5. ✅ Search API functional
6. ✅ Clear documentation
7. ⭐ RAG/NLP query interface working (optional enhancement)
8. ⭐ Frontend with natural language search (optional enhancement)

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Sources inaccessible | Phase 0 validates early → pivot to HW02.1 |
| Scraping blocked | Use delays, focus on API sources first |
| Scope too large | Start with 2-3 sources, add incrementally |
| Deduplication complex | Start simple (exact match), improve later |