# NLP Chatbot Implementation

Natural language query interface for the E-Procurement Data Pipeline.

---

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Core Components](#core-components)
4. [Technology Stack](#technology-stack)
5. [API Endpoints](#api-endpoints)
6. [Prompt Engineering](#prompt-engineering)
7. [Security & Validation](#security--validation)
8. [Configuration](#configuration)
9. [Docker Deployment](#docker-deployment)
10. [Usage Examples](#usage-examples)
11. [Extension Points](#extension-points)
12. [References](#references)

---

## Overview

The NLP Chatbot API provides a natural language interface to the European procurement data stored in the Gold layer. It enables users to query complex procurement data using plain English instead of SQL, and generates insights automatically.

### Key Features

- **Natural Language to SQL**: Convert questions like "Show me top 10 countries by tender count" into validated SQL queries
- **Automated Analytics**: Execute queries and generate insights, trends, and visualization suggestions
- **Schema-Aware**: Dynamically adapts to database schema changes
- **Safety First**: SQL injection protection, query complexity limits, forbidden keyword filtering
- **RESTful API**: FastAPI-based REST interface with automatic OpenAPI documentation
- **LLM-Powered**: Google Gemini API for state-of-the-art language understanding

### Use Cases

1. **Business Analysts**: Query procurement data without SQL knowledge
2. **Data Scientists**: Rapid prototyping of analytical queries
3. **Executives**: Quick insights from natural language questions
4. **Researchers**: Exploratory data analysis with conversational interface

---

## System Architecture

### Position in Overall System

The chatbot sits at the **Application Layer**, consuming data from the **Gold Layer** via **Dremio**:

```
┌─────────────────────────────────────────────────────┐
│  GOLD LAYER (MinIO)                                 │
│  • unified/all_tenders.parquet (536K records)       │
│  • aggregates/ (pre-computed summaries)             │
└───────────────────────┬─────────────────────────────┘
                        ↓
            ┌───────────────────────┐
            │  Dremio Query Engine  │
            │  (SQL Interface)      │
            └───────────┬───────────┘
                        ↓
        ┌───────────────────────────────┐
        │  NLP CHATBOT API (FastAPI)    │
        │  ┌─────────────────────────┐  │
        │  │  Query Creator Bot      │  │  Natural Language → SQL
        │  │  (Gemini 2.0 Flash)     │  │
        │  └─────────────────────────┘  │
        │  ┌─────────────────────────┐  │
        │  │  Analytics Bot          │  │  SQL Results → Insights
        │  │  (Gemini 2.5 Pro)       │  │
        │  └─────────────────────────┘  │
        └───────────────┬───────────────┘
                        ↓
            ┌───────────────────────┐
            │  User Applications    │
            │  • cURL, Python, etc. │
            └───────────────────────┘
```

### Component Architecture

```
src/api/
├── main.py                    # FastAPI application entry point
├── config.py                  # Settings and environment variables
├── dependencies.py            # Dependency injection container
│
├── bots/                      # LLM-powered chatbots
│   ├── query_creator.py       # Natural language → SQL
│   └── analytics_bot.py       # SQL results → Insights
│
├── services/                  # Business logic layer
│   ├── llm_service.py         # Gemini API integration
│   ├── dremio_client.py       # Dremio connection (Arrow Flight)
│   ├── query_executor.py      # SQL execution + result formatting
│   └── schema_inspector.py    # Database schema introspection
│
├── routes/                    # API endpoints
│   ├── chat.py                # Chatbot endpoints
│   └── schema.py              # Schema inspection endpoints
│
├── models/                    # Pydantic data models
│   ├── requests.py            # API request schemas
│   └── responses.py           # API response schemas
│
├── prompts/                   # LLM prompt templates
│   ├── sql_prompts.py         # SQL generation prompts
│   └── analytics_prompts.py   # Analytics generation prompts
│
└── utils/                     # Utilities
    ├── sql_validator.py       # SQL security & validation
    └── formatters.py          # Result formatting helpers
```

---

## Core Components

### 1. Query Creator Bot

**Purpose**: Converts natural language questions into safe, validated SQL queries.

**Location**: `src/api/bots/query_creator.py`

**Process**:
1. User submits natural language question
2. Schema Inspector retrieves relevant tables based on keywords
3. Prompt Engineer constructs context-rich prompt with schema
4. Gemini 2.0 Flash generates SQL query
5. SQL Validator checks for security issues
6. If valid: return SQL + explanation
7. If invalid: retry up to 3 times with refined prompts

**Key Features**:
- Schema-aware generation (knows table/column names)
- Retry logic with increasing context on failures
- Confidence scoring based on complexity
- Query explanation generation
- Domain-specific hints (e.g., "Try filtering by country")

**Example Flow**:
```
User: "Show me the top 10 countries by number of tenders"
  ↓
Schema Inspector: Returns minio.gold.unified table with columns
  ↓
Prompt: "Generate SQL for: top 10 countries... Tables available: ..."
  ↓
Gemini 2.0 Flash: "SELECT source_country, COUNT(*) as count ..."
  ↓
SQL Validator: ✅ PASS (no forbidden keywords, valid syntax)
  ↓
Response: {sql: "SELECT...", confidence: 0.95, explanation: "..."}
```

### 2. Analytics Bot

**Purpose**: Executes SQL queries and generates insights, trends, and visualization suggestions.

**Location**: `src/api/bots/analytics_bot.py`

**Process**:
1. Receives SQL query + optional user focus message
2. Query Executor runs SQL via Dremio
3. Result formatter converts to structured data
4. Gemini 2.5 Pro analyzes results for patterns
5. Generates insights, trends, anomalies
6. Suggests appropriate visualizations

**Key Features**:
- Automatic insight generation (trends, outliers, patterns)
- Visualization recommendations (chart types, axes)
- Focus-based analysis (user can guide what to look for)
- Handles large result sets (up to 10,000 rows)
- Statistical summaries

**Example Flow**:
```
SQL: "SELECT source_country, COUNT(*) ... ORDER BY count DESC LIMIT 10"
Message: "Focus on European trends"
  ↓
Query Executor: Runs query, returns 10 rows
  ↓
Prompt: "Analyze these results: [10 countries]... Focus: European trends"
  ↓
Gemini 2.5 Pro: Generates insights, identifies patterns
  ↓
Response: {
  insights: "Portugal leads with 42% of tenders...",
  visualizations: [{type: "bar_chart", x: "country", y: "count"}],
  trends: ["Southern Europe dominates", ...]
}
```

### 3. LLM Service

**Purpose**: Unified interface to Google Gemini API for both query creation and analytics.

**Location**: `src/api/services/llm_service.py`

**Models Used**:
- **Gemini 2.0 Flash** (Query Creator): Fast, cost-effective for SQL generation
- **Gemini 2.5 Pro** (Analytics): Advanced reasoning for complex analysis

**Features**:
- Async initialization (loaded on startup)
- Separate generation configs per model (temperature, max_tokens)
- Error handling and retry logic
- Resource cleanup on shutdown

**Configuration**:
```python
# Query Creator (deterministic SQL)
Temperature: 0.1  # Low for consistency
Max Tokens: 1024

# Analytics (creative insights)
Temperature: 0.7  # Higher for diverse outputs
Max Tokens: 2048
```

### 4. Dremio Client

**Purpose**: Connects to Dremio query engine via Arrow Flight protocol.

**Location**: `src/api/services/dremio_client.py`

**Features**:
- Arrow Flight connection (high-performance binary protocol)
- Authentication with username/password
- Query execution with timeouts
- Result streaming for large datasets
- Connection pooling and reuse

**Connection Details**:
```python
Host: dremio (Docker network) / localhost (local dev)
Port: 32010 (Arrow Flight)
Protocol: gRPC
Authentication: Basic (username/password)
```

### 5. Schema Inspector

**Purpose**: Introspects database schema to provide context for SQL generation.

**Location**: `src/api/services/schema_inspector.py`

**Features**:
- Caches schema metadata (1 hour TTL)
- Retrieves table/column information from Dremio
- Keyword-based table relevance scoring
- Provides sample values for better context

**Cached Information**:
```python
TableInfo:
  - full_name: "minio.gold.unified"
  - description: "Unified procurement dataset"
  - columns: [{name, type, description}, ...]
  - row_count: 536778
  - sample_values: {column: [values]}
```

### 6. SQL Validator

**Purpose**: Ensures generated SQL is safe and within acceptable complexity limits.

**Location**: `src/api/utils/sql_validator.py`

**Validation Checks**:
1. **Forbidden Keywords**: Blocks `DROP`, `DELETE`, `INSERT`, `UPDATE`, `TRUNCATE`, `ALTER`, `CREATE`, `EXEC`
2. **Required Keywords**: Must contain `SELECT`, `FROM`
3. **Complexity Limits**:
   - Max 5 `JOIN` operations
   - Max 3 subquery depth levels
4. **Syntax Validation**: Uses `sqlparse` for parsing
5. **Query Explanation**: Extracts tables, columns, filters, aggregations

**Example Validation**:
```python
# Valid
"SELECT * FROM minio.gold.unified LIMIT 100"  # ✅

# Invalid - forbidden keyword
"DROP TABLE minio.gold.unified"  # ❌ Blocked

# Invalid - too complex
"SELECT * FROM t1 JOIN t2 JOIN t3 JOIN t4 JOIN t5 JOIN t6"  # ❌ Too many joins
```

---

## Technology Stack

### Backend Framework
- **FastAPI 0.109.0**: Modern Python web framework
  - Automatic OpenAPI/Swagger documentation
  - Pydantic integration for validation
  - Async/await support
  - Type hints for better IDE support

### LLM Integration
- **google-generativeai 0.7.2**: Official Gemini API client
  - Gemini 2.0 Flash for SQL generation
  - Gemini 2.5 Pro for analytics
  - Streaming and non-streaming modes

### Data Layer
- **pyarrow 12.0+**: Dremio Arrow Flight integration
  - High-performance binary protocol
  - Zero-copy data transfer
  - Efficient result serialization

### Validation & Parsing
- **pydantic 2.6.0**: Request/response validation
- **pydantic-settings 2.1.0**: Environment variable management
- **sqlparse 0.4.4**: SQL parsing and formatting

### Server
- **uvicorn 0.27.0**: ASGI server
  - Production-ready performance
  - Graceful shutdown
  - Auto-reload in development

---

## API Endpoints

### Base URL

- **Local Development**: `http://localhost:8000`
- **Docker**: `http://localhost:8000`
- **Interactive Docs**: `http://localhost:8000/docs` (Swagger UI)

### 1. Health Check

**Endpoint**: `GET /api/health`

**Description**: Check API and service status.

**Response**:
```json
{
  "status": "ok",
  "api_version": "1.0.0",
  "services": {
    "llm_models_loaded": true,
    "dremio_connected": true
  },
  "models": {
    "query_creator": "models/gemini-2.0-flash",
    "analytics": "models/gemini-2.5-pro"
  }
}
```

### 2. Query Creator (Natural Language → SQL)

**Endpoint**: `POST /api/chat/query-creator`

**Description**: Convert natural language question to SQL query.

**Request Body**:
```json
{
  "message": "Show me the top 10 countries by number of tenders",
  "include_explanation": true,
  "max_attempts": 3
}
```

**Response**:
```json
{
  "success": true,
  "sql": "SELECT source_country, COUNT(*) as tender_count FROM minio.gold.unified GROUP BY source_country ORDER BY tender_count DESC LIMIT 10",
  "explanation": "This query groups tenders by country and counts them, returning the top 10.",
  "confidence": 0.95,
  "tables_used": ["minio.gold.unified"],
  "hints": ["Filter by date range for recent trends", "Add HAVING clause for minimum thresholds"]
}
```

**Error Response**:
```json
{
  "success": false,
  "error": "No relevant tables found for this query",
  "hints": ["Try mentioning 'tenders', 'procurement', or 'buyers'"]
}
```

### 3. Analytics Bot (SQL → Insights)

**Endpoint**: `POST /api/chat/analytics`

**Description**: Execute SQL and generate analytical insights.

**Request Body**:
```json
{
  "sql": "SELECT source_country, COUNT(*) as count FROM minio.gold.unified GROUP BY source_country ORDER BY count DESC LIMIT 10",
  "message": "Focus on European procurement trends",
  "include_visualizations": true
}
```

**Response**:
```json
{
  "success": true,
  "results": {
    "columns": ["source_country", "count"],
    "rows": [
      ["Portugal", 213450],
      ["United Kingdom", 156780],
      ...
    ],
    "row_count": 10,
    "execution_time_ms": 1245
  },
  "insights": "Portugal leads European procurement with 42% of total tenders. Southern European countries (Portugal, Italy, Spain) represent 68% of the dataset, indicating strong data coverage in this region. Notable trend: UK tender count decreased 15% year-over-year, possibly due to post-Brexit administrative changes.",
  "visualizations": [
    {
      "type": "bar_chart",
      "title": "Top 10 Countries by Tender Count",
      "x_axis": "source_country",
      "y_axis": "count",
      "recommended_library": "plotly"
    }
  ],
  "trends": [
    "Southern Europe dominates with 68% of tenders",
    "UK shows declining trend (-15% YoY)",
    "Portugal and Italy combined exceed 50% of total"
  ],
  "execution_time": 1.8
}
```

### 4. Direct SQL Execution

**Endpoint**: `POST /api/execute-sql`

**Description**: Execute SQL directly without analytics generation.

**Request Body**:
```json
{
  "sql": "SELECT COUNT(*) FROM minio.gold.unified",
  "validate": true,
  "include_stats": true
}
```

**Response**:
```json
{
  "success": true,
  "columns": ["COUNT"],
  "rows": [[536778]],
  "row_count": 1,
  "execution_time_ms": 432,
  "stats": {
    "bytes_read": 102400,
    "rows_scanned": 536778
  }
}
```

### 5. Refine SQL Query

**Endpoint**: `POST /api/chat/refine`

**Description**: Refine an existing SQL query based on feedback.

**Request Body**:
```json
{
  "original_query": "Show me tenders",
  "original_sql": "SELECT * FROM minio.gold.unified LIMIT 100",
  "feedback": "Only show tenders from Portugal with value > 1M EUR"
}
```

**Response**:
```json
{
  "success": true,
  "sql": "SELECT * FROM minio.gold.unified WHERE source_country = 'Portugal' AND tender_value_amount > 1000000 AND tender_value_currency = 'EUR' LIMIT 100",
  "explanation": "Refined query to filter Portugal tenders over 1M EUR",
  "confidence": 0.85
}
```

### 6. Validate SQL

**Endpoint**: `POST /api/validate-sql`

**Description**: Validate SQL without executing.

**Request Body**:
```json
{
  "sql": "SELECT * FROM minio.gold.unified WHERE tender_value > 0"
}
```

**Response**:
```json
{
  "success": true,
  "sql": "SELECT * FROM minio.gold.unified WHERE tender_value > 0",
  "explanation": {
    "tables": ["minio.gold.unified"],
    "columns": ["*"],
    "filters": ["tender_value > 0"],
    "aggregations": [],
    "joins": 0
  }
}
```

### 7. Schema Inspection

**Endpoint**: `GET /api/schema`

**Description**: Retrieve database schema information.

**Response**:
```json
{
  "success": true,
  "tables": [
    {
      "name": "minio.gold.unified",
      "description": "Unified procurement dataset",
      "columns": 27,
      "rows": 536778,
      "sample_columns": [
        {"name": "ocid", "type": "string"},
        {"name": "tender_title", "type": "string"},
        {"name": "tender_value_amount", "type": "double"},
        ...
      ]
    }
  ]
}
```

---

## Prompt Engineering

### SQL Generation Prompts

**Location**: `src/api/prompts/sql_prompts.py`

**Strategy**: Few-shot learning with schema context

**Prompt Structure**:
```
You are an expert SQL query generator for European procurement data.

DATABASE SCHEMA:
{table_schemas}

EXAMPLE QUERIES:
- "Top 10 buyers": SELECT buyer_name, COUNT(*) FROM ... GROUP BY buyer_name ORDER BY COUNT(*) DESC LIMIT 10
- "Tenders over 1M": SELECT * FROM ... WHERE tender_value_amount > 1000000

USER QUESTION:
"{user_query}"

INSTRUCTIONS:
1. Generate a valid SQL query for the question
2. Use only columns that exist in the schema
3. Add appropriate filters, GROUP BY, ORDER BY, LIMIT clauses
4. Optimize for readability
5. Return ONLY the SQL query, no explanations

SQL QUERY:
```

**Key Techniques**:
1. **Schema Injection**: Dynamically includes relevant table schemas
2. **Few-Shot Examples**: Provides 3-5 example query pairs
3. **Constraint Enforcement**: Explicitly states requirements (valid columns, syntax)
4. **Domain Hints**: Includes procurement-specific terminology
5. **Iterative Refinement**: On failures, adds error messages to prompt for retry

### Analytics Prompts

**Location**: `src/api/prompts/analytics_prompts.py`

**Strategy**: Chain-of-thought reasoning with result context

**Prompt Structure**:
```
You are a data analyst specializing in European public procurement.

QUERY EXECUTED:
{sql_query}

RESULTS:
{formatted_results}

USER FOCUS:
"{user_message}"

ANALYZE THE DATA:
1. Identify key trends and patterns
2. Highlight outliers or anomalies
3. Provide actionable insights
4. Suggest visualizations

RESPOND IN JSON FORMAT:
{
  "insights": "2-3 paragraph summary",
  "trends": ["trend 1", "trend 2", ...],
  "visualizations": [{"type": "...", "title": "...", ...}]
}
```

**Key Techniques**:
1. **Result Contextualization**: Includes actual query results
2. **User Focus Integration**: Incorporates user's analytical goals
3. **Structured Output**: Enforces JSON response format
4. **Domain Knowledge**: References procurement metrics (CPV codes, procedures)
5. **Visualization Guidance**: Suggests appropriate chart types

---

## Security & Validation

### SQL Injection Prevention

**Layers of Protection**:

1. **Keyword Blacklist**: Blocks dangerous SQL operations
   ```python
   FORBIDDEN = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'TRUNCATE',
                'ALTER', 'CREATE', 'EXEC', 'EXECUTE']
   ```

2. **Read-Only Enforcement**: Only `SELECT` statements allowed
   ```python
   if 'SELECT' not in sql.upper():
       raise ValidationError("Only SELECT queries allowed")
   ```

3. **Parameterized Queries**: Dremio client uses prepared statements

4. **User Permissions**: Dremio account has read-only access to Gold layer

### Query Complexity Limits

**Configuration** (`src/api/config.py`):
```python
MAX_QUERY_TIMEOUT: int = 30  # seconds
MAX_RESULT_ROWS: int = 10000
MAX_JOINS: int = 5
MAX_SUBQUERY_DEPTH: int = 3
```

**Enforcement**:
- Timeout: Dremio cancels queries exceeding 30 seconds
- Joins: Validator counts JOIN keywords, rejects if > 5
- Subqueries: Parser checks nesting depth, rejects if > 3
- Results: Query executor limits rows returned

### API Rate Limiting

**Current Implementation**: None (development mode)

**Production Recommendations**:
```python
# Using slowapi
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/chat/query-creator")
@limiter.limit("10/minute")  # 10 requests per minute
async def query_creator(...):
    ...
```

### LLM API Key Security

- **Storage**: Environment variable (`GEMINI_API_KEY`)
- **Docker**: Loaded via `env_file`, never baked into image
- **Access**: Only accessible within service layer
- **Rotation**: Supports key updates via environment reload

---

## Configuration

### Environment Variables

**Location**: `infra/.env` (created from `infra/.env.example`)

**Required Variables**:

```bash
# Gemini API (REQUIRED)
GEMINI_API_KEY=your_gemini_api_key_here  # Get from https://ai.google.dev/

# Query Creator Bot
QUERY_CREATOR_MODEL=models/gemini-2.0-flash
QUERY_CREATOR_TEMPERATURE=0.1
QUERY_CREATOR_MAX_TOKENS=1024

# Analytics Bot
ANALYTICS_MODEL=models/gemini-2.5-pro
ANALYTICS_TEMPERATURE=0.7
ANALYTICS_MAX_TOKENS=2048

# Dremio Connection
DREMIO_HOST=localhost  # Changed to "dremio" in Docker
DREMIO_PORT=32010
DREMIO_USERNAME=admin
DREMIO_PASSWORD=password123
DREMIO_TIMEOUT=30

# Query Limits
MAX_QUERY_TIMEOUT=30
MAX_RESULT_ROWS=10000
MAX_JOINS=5
MAX_SUBQUERY_DEPTH=3

# API Server
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true  # Set to false in production
LOG_LEVEL=INFO
```

### Model Selection

**Gemini 2.0 Flash** (Query Creator):
- **Speed**: ~500ms response time
- **Cost**: $0.075 per 1M input tokens
- **Use Case**: Deterministic SQL generation
- **Temperature**: 0.1 (low for consistency)

**Gemini 2.5 Pro** (Analytics):
- **Intelligence**: Advanced reasoning capabilities
- **Cost**: $1.25 per 1M input tokens
- **Use Case**: Complex analytical insights
- **Temperature**: 0.7 (higher for creative analysis)

**Alternative Models** (configurable):
- `gemini-1.5-flash`: Lower cost, slightly less capable
- `gemini-1.5-pro`: Previous generation Pro model
- `gemini-2.0-flash-exp`: Experimental cutting-edge features

---

## Docker Deployment

### Service Configuration

**File**: `infra/docker-compose.yml`

```yaml
chatbot-api:
  build:
    context: ..
    dockerfile: infra/dockerfile/chatbot-api/Dockerfile
  container_name: sod-chatbot-api
  ports:
    - "8000:8000"
  env_file:
    - .env
  environment:
    DREMIO_HOST: dremio  # Override for Docker network
  volumes:
    - ../src:/app/src:ro  # Read-only source mount
  networks:
    - sod-network
  depends_on:
    dremio:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "python", "-c", "import httpx; httpx.get('http://localhost:8000/api/health')"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 30s
  restart: unless-stopped
```

### Dockerfile

**File**: `infra/dockerfile/chatbot-api/Dockerfile`

**Multi-stage Build**:
1. **Base**: Python 3.11 slim image
2. **Dependencies**: Install Python packages from `infra/requirements.txt`
3. **Application**: Copy source code, expose port 8000

**Key Features**:
- Minimal image size (no CUDA, no unnecessary packages)
- Environment variables loaded at runtime (not baked in)
- Health check for container orchestration
- Non-root user (security best practice)

### Deployment Commands

```bash
# Start all services (MinIO, Dremio, Chatbot)
make up

# Build and restart chatbot only
make chatbot-rebuild

# View logs
make chatbot-logs

# Test API
make chatbot-test

# Open shell in container
make chatbot-shell

# Run comprehensive tests
make chatbot-test-all
```

### Networking

**Internal Docker Network**: `sod-network`

**Service Communication**:
- `chatbot-api` → `dremio:32010` (Arrow Flight)
- `dremio` → `minio:9000` (S3 API)

**External Access**:
- Chatbot API: `localhost:8000`
- API Docs: `localhost:8000/docs`
- Dremio UI: `localhost:9047`
- MinIO Console: `localhost:9001`

---

## Usage Examples

### Example 1: Basic Query Generation

```bash
curl -X POST http://localhost:8000/api/chat/query-creator \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me the top 10 countries by number of tenders",
    "include_explanation": true
  }'
```

**Response**:
```json
{
  "success": true,
  "sql": "SELECT source_country, COUNT(*) as tender_count FROM minio.gold.unified GROUP BY source_country ORDER BY tender_count DESC LIMIT 10",
  "explanation": "Groups tenders by country, counts them, and returns top 10",
  "confidence": 0.95
}
```

### Example 2: Analytics with Insights

```bash
curl -X POST http://localhost:8000/api/chat/analytics \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT source_country, COUNT(*) as count FROM minio.gold.unified GROUP BY source_country ORDER BY count DESC LIMIT 5",
    "message": "Focus on top countries and trends",
    "include_visualizations": true
  }'
```

**Response**:
```json
{
  "success": true,
  "results": {
    "columns": ["source_country", "count"],
    "rows": [["Portugal", 213450], ["United Kingdom", 156780], ...],
    "row_count": 5
  },
  "insights": "Portugal leads with 40% of all tenders...",
  "visualizations": [
    {
      "type": "bar_chart",
      "title": "Top 5 Countries by Tender Count",
      "x_axis": "source_country",
      "y_axis": "count"
    }
  ],
  "trends": ["Southern Europe dominates", ...]
}
```

### Example 3: Python Client

```python
import requests

class ProcurementChatbot:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url

    def ask(self, question: str) -> dict:
        """Ask a question and get SQL + results + insights."""
        # Step 1: Generate SQL
        sql_response = requests.post(
            f"{self.base_url}/api/chat/query-creator",
            json={"message": question, "include_explanation": True}
        ).json()

        if not sql_response["success"]:
            return {"error": sql_response["error"]}

        # Step 2: Execute and analyze
        analytics_response = requests.post(
            f"{self.base_url}/api/chat/analytics",
            json={
                "sql": sql_response["sql"],
                "message": f"Analyze: {question}",
                "include_visualizations": True
            }
        ).json()

        return {
            "sql": sql_response["sql"],
            "explanation": sql_response["explanation"],
            "results": analytics_response["results"],
            "insights": analytics_response["insights"],
            "visualizations": analytics_response["visualizations"]
        }

# Usage
chatbot = ProcurementChatbot()
result = chatbot.ask("What are the top 5 procurement categories?")
print(result["insights"])
```

### Example 4: Query Refinement Workflow

```bash
# Initial query
curl -X POST http://localhost:8000/api/chat/query-creator \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me tenders from 2024"}'

# Returns: SELECT * FROM minio.gold.unified WHERE year = 2024 LIMIT 100

# Refine the query
curl -X POST http://localhost:8000/api/chat/refine \
  -H "Content-Type: application/json" \
  -d '{
    "original_query": "Show me tenders from 2024",
    "original_sql": "SELECT * FROM minio.gold.unified WHERE year = 2024 LIMIT 100",
    "feedback": "Only show high-value tenders over 1 million EUR"
  }'

# Returns: SELECT * FROM minio.gold.unified WHERE year = 2024
#          AND tender_value_amount > 1000000
#          AND tender_value_currency = 'EUR' LIMIT 100
```

---

## Extension Points

### Adding a New Bot

**Example**: Creating a "Compliance Checker Bot" that validates tender data quality.

1. **Create Bot Class** (`src/api/bots/compliance_bot.py`):
   ```python
   class ComplianceBot:
       def __init__(self, llm_service: LLMService, dremio_client: DremioClient):
           self.llm = llm_service
           self.dremio = dremio_client

       def check_compliance(self, tender_id: str) -> dict:
           # Fetch tender data
           # Analyze with LLM
           # Return compliance report
           pass
   ```

2. **Add to Dependencies** (`src/api/dependencies.py`):
   ```python
   def get_compliance_bot() -> ComplianceBot:
       return ComplianceBot(
           llm_service=get_llm_service(),
           dremio_client=get_dremio_client()
       )
   ```

3. **Create Endpoint** (`src/api/routes/compliance.py`):
   ```python
   @router.post("/compliance/check")
   async def check_compliance(
       tender_id: str,
       bot = Depends(get_compliance_bot)
   ):
       return bot.check_compliance(tender_id)
   ```

4. **Register Router** (`src/api/main.py`):
   ```python
   from src.api.routes import compliance
   app.include_router(compliance.router, prefix="/api", tags=["Compliance"])
   ```

### Customizing Prompts

**Location**: `src/api/prompts/sql_prompts.py`

**Example**: Adding domain-specific examples

```python
def create_sql_generation_prompt(
    user_query: str,
    relevant_tables: List[TableInfo],
    include_all_schema: bool = False
) -> str:
    # Add custom examples
    custom_examples = """
    DOMAIN-SPECIFIC EXAMPLES:
    - "CPV code analysis": SELECT procurement_category_cpv, COUNT(*) ...
    - "Supplier diversity": SELECT COUNT(DISTINCT supplier_name) ...
    """

    prompt = f"""
    {custom_examples}

    USER QUESTION: {user_query}

    GENERATE SQL:
    """
    return prompt
```

### Adding New Validators

**Location**: `src/api/utils/sql_validator.py`

**Example**: Adding a custom validator for business rules

```python
class CustomSQLValidator(SQLValidator):
    def validate_business_rules(self, sql: str) -> Tuple[bool, str]:
        """Enforce business-specific SQL rules."""
        # Example: Require date filters for large tables
        if "minio.gold.unified" in sql.lower():
            if "WHERE" not in sql.upper():
                return False, "Queries on unified table must include WHERE clause"

        return True, ""

    def validate(self, sql: str) -> Tuple[bool, str]:
        # Run parent validation
        is_valid, error = super().validate(sql)
        if not is_valid:
            return is_valid, error

        # Run custom validation
        return self.validate_business_rules(sql)
```

### Integrating New LLM Providers

**Example**: Adding support for OpenAI GPT-4

1. **Update LLM Service** (`src/api/services/llm_service.py`):
   ```python
   from openai import OpenAI

   class LLMService:
       def __init__(self):
           self._gemini_client = None
           self._openai_client = None

       def _initialize_openai(self):
           self._openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

       def generate(self, prompt: str, model_type: ModelType, provider: str = "gemini"):
           if provider == "openai":
               return self._openai_client.chat.completions.create(...)
           else:
               return self._gemini_client.generate_content(...)
   ```

2. **Add Configuration** (`src/api/config.py`):
   ```python
   OPENAI_API_KEY: Optional[str] = None
   OPENAI_MODEL: str = "gpt-4-turbo"
   ```

---

## References

### External Documentation

- [Google Gemini API](https://ai.google.dev/docs) - Official Gemini documentation
- [FastAPI Documentation](https://fastapi.tiangolo.com/) - FastAPI framework guide
- [Dremio Arrow Flight](https://docs.dremio.com/cloud/reference/api/flight/) - Arrow Flight client reference
- [Pydantic](https://docs.pydantic.dev/) - Data validation library

### Internal Documentation

- [System Architecture](architecture.md) - Overall system design and data pipeline
- [Data Layers](data_layers.md) - Bronze/Silver/Gold layer specifications
- [Development Guide](development_guide.md) - Setup and development workflow

### API Documentation

- **Interactive Docs**: http://localhost:8000/docs (Swagger UI)
- **ReDoc**: http://localhost:8000/redoc (Alternative documentation)
- **OpenAPI JSON**: http://localhost:8000/openapi.json (Machine-readable spec)

### Prompt Engineering Resources

- [Google AI Prompt Engineering Guide](https://ai.google.dev/docs/prompt_best_practices)
- [Few-Shot Prompting](https://www.promptingguide.ai/techniques/fewshot)
- [Chain-of-Thought Reasoning](https://www.promptingguide.ai/techniques/cot)

---

## Future Enhancements

### Planned Features

1. **Conversation History**: Track multi-turn conversations for context
2. **Query Caching**: Cache common SQL queries for faster responses
3. **Real-time Streaming**: Stream LLM responses for better UX
4. **Multi-language Support**: Accept questions in Portuguese, Spanish, etc.
5. **Advanced Analytics**: Predictive modeling, anomaly detection
6. **Export Functionality**: Export results to CSV, Excel, PDF
7. **Scheduled Reports**: Auto-generate periodic insights

### Performance Optimizations

1. **Async Processing**: Full async/await throughout the stack
2. **Connection Pooling**: Reuse Dremio connections
3. **Result Pagination**: Handle larger result sets efficiently
4. **Schema Caching**: Longer TTL for stable schemas
5. **LLM Response Caching**: Cache identical prompts

### Security Enhancements

1. **API Key Authentication**: Require API keys for access
2. **Rate Limiting**: Per-user/IP rate limits
3. **Audit Logging**: Track all queries and users
4. **RBAC**: Role-based access control for data
5. **TLS/SSL**: Encrypt all API traffic

---

**Last Updated**: 2024-12-21
**Version**: 1.0
**Maintained By**: E-Procurement Data Pipeline Team
