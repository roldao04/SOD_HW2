# Data Layers - Medallion Architecture

This document describes the **Bronze → Silver → Gold** medallion architecture pattern used in the E-Procurement Data Pipeline.

---

## Table of Contents

1. [Overview](#overview)
2. [Bronze Layer (Raw Data)](#bronze-layer-raw-data)
3. [Silver Layer (Cleaned Data)](#silver-layer-cleaned-data)
4. [Gold Layer (Analytics-Ready)](#gold-layer-analytics-ready)
5. [Schema Definitions](#schema-definitions)
6. [Data Quality](#data-quality)
7. [Partitioning Strategy](#partitioning-strategy)

---

## Overview

The **medallion architecture** organizes data into three progressive layers, each adding more value and refinement:

```
┌─────────────────────────────────────────────────────────────┐
│  BRONZE LAYER                                               │
│  Purpose: Raw data preservation                             │
│  Format:  JSON                                              │
│  Quality: As-is from source (no transformation)             │
│  Use:     Data lineage, reprocessing, debugging             │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  SILVER LAYER                                               │
│  Purpose: Cleaned, validated, normalized data               │
│  Format:  Parquet (columnar)                                │
│  Quality: Validated, unified schema, cleaned                │
│  Use:     Data science, analytics, reporting                │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  GOLD LAYER                                                 │
│  Purpose: Business-ready aggregates & analytics             │
│  Format:  Parquet (optimized)                               │
│  Quality: Deduplicated, enriched, aggregated                │
│  Use:     Dashboards, ML models, business intelligence      │
└─────────────────────────────────────────────────────────────┘
```

### Benefits of Medallion Architecture

1. **Data Lineage**: Raw data preserved in Bronze for reprocessing
2. **Incremental Processing**: Process only new data in each layer
3. **Quality Gates**: Each layer improves data quality
4. **Performance**: Optimized formats (Parquet) at higher layers
5. **Flexibility**: Can rebuild Silver/Gold if logic changes

---

## Bronze Layer (Raw Data)

### Purpose

**Immutable storage of raw data** exactly as received from sources, with minimal transformation.

### Location

- **Local**: `data/bronze/`
- **MinIO**: `s3://bronze/`

### Directory Structure

```
bronze/
├── open_contracting_partnership/
│   ├── germany/
│   │   └── 2025/
│   │       └── 01/
│   │           └── 15/
│   │               └── records_20251220_143052.json
│   ├── uk/
│   ├── italy/
│   ├── croatia/
│   ├── kosovo/
│   ├── albania/
│   └── spain/
├── base_portugal/
│   └── portugal/
│       └── 2024/
│           └── 12/
│               └── 20/
│                   └── records_20251220_214501.json
└── partner_data/
    └── andré&abel/
        └── ted.parquet
```

**Path Pattern**:
```
bronze/{source}/{country}/{year}/{month}/{day}/records_{timestamp}.json
```

### File Format

**JSON** files containing OCDS-formatted procurement records.

**Structure**:
```json
{
  "source": "open_contracting_partnership",
  "publication_id": "119",
  "extraction_timestamp": "2025-12-20T14:30:52Z",
  "total_records": 1500,
  "records": [
    {
      "ocid": "ocds-h6vhtk-26cc5a",
      "date": "2025-01-15",
      "tender": {
        "id": "26cc5a",
        "title": "Road Maintenance Services",
        "status": "active",
        "value": {
          "amount": 250000.0,
          "currency": "EUR"
        },
        "tenderPeriod": {
          "startDate": "2025-01-15",
          "endDate": "2025-02-15"
        },
        "procurementMethod": "open",
        "mainProcurementCategory": "services"
      },
      "buyer": {
        "id": "DE-123456",
        "name": "Municipality of Berlin"
      },
      "awards": [
        {
          "id": "award-001",
          "date": "2025-02-20",
          "value": {
            "amount": 245000.0,
            "currency": "EUR"
          },
          "suppliers": [
            {
              "id": "DE-SUP-789",
              "name": "Road Services GmbH"
            }
          ]
        }
      ]
    }
  ]
}
```

### Characteristics

| Property | Value |
|----------|-------|
| **Format** | JSON |
| **Compression** | None (human-readable) |
| **Schema** | Source-specific OCDS |
| **Validation** | Minimal (extraction errors only) |
| **Partitioning** | By source/country/date |
| **Mutability** | Immutable (append-only) |
| **Retention** | Permanent (for reprocessing) |

### Current Statistics

- **Total Files**: ~2,447 JSON files
- **Date Range**: 2016-02-20 to 2025-12-15
- **Sources**: 3 (OCP, BASE Portugal, TED)
- **Countries**: 8+ (DE, UK, IT, PT, HR, XK, AL, ES, etc.)

---

## Silver Layer (Cleaned Data)

### Purpose

**Normalized, validated, and cleaned data** in a unified schema ready for analysis.

### Location

- **Local**: `data/silver/`
- **MinIO**: `s3://silver/`

### Directory Structure

```
silver/
├── open_contracting_partnership/
│   ├── germany/
│   │   └── 2025/
│   │       └── 01/
│   │           └── tenders_20251220_151234.parquet
│   ├── uk/
│   │   └── 2025/01/tenders_20251220_151234.parquet
│   ├── italy/
│   ├── croatia/
│   ├── kosovo/
│   ├── albania/
│   └── spain/
├── base_portugal/
│   └── portugal/
│       └── 2024/
│           ├── 08/
│           │   └── tenders_20251220_215122.parquet
│           └── 12/
│               └── tenders_20251220_215122.parquet
└── ted/
    └── unknown/
        └── 2025/01/tenders_20251220_160045.parquet
```

**Path Pattern**:
```
silver/{source}/{country}/{year}/{month}/tenders_{timestamp}.parquet
```

### File Format

**Apache Parquet** with Snappy compression.

### Unified Schema (27 Fields)

All sources are transformed to this common schema:

```python
{
    # Identifiers
    'ocid': 'string',                      # Unique tender ID (OCDS format)
    'source_country': 'string',            # Country code (e.g., 'germany', 'portugal')
    'source_publication_id': 'string',     # Source publication/dataset ID
    'tender_id': 'string',                 # Source-specific tender ID

    # Tender Information
    'tender_title': 'string',              # Tender title/description
    'tender_value_amount': 'float',        # Estimated tender value
    'tender_value_currency': 'string',     # Currency (EUR, GBP, etc.)
    'tender_status': 'string',             # Status (active, complete, etc.)

    # Dates
    'publication_date': 'string',          # Publication date (ISO 8601: YYYY-MM-DD)
    'tender_start_date': 'string',         # Tender period start
    'tender_end_date': 'string',           # Tender deadline
    'award_date': 'string',                # Award announcement date

    # Procurement Details
    'procurement_method': 'string',        # Method (open, restricted, etc.)
    'procurement_category': 'string',      # Category (goods, services, works)

    # Buyer Information
    'buyer_id': 'string',                  # Buyer organization ID
    'buyer_name': 'string',                # Buyer organization name

    # Supplier Information (Arrays)
    'supplier_ids': 'list[string]',        # List of awarded supplier IDs
    'supplier_names': 'list[string]',      # List of awarded supplier names

    # Award Details
    'award_amount': 'float',               # Actual award amount
    'award_currency': 'string',            # Award currency

    # Metrics
    'num_lots': 'int',                     # Number of tender lots
    'num_tenderers': 'int',                # Number of bidders
    'num_awards': 'int',                   # Number of awards

    # Documents
    'document_urls': 'list[string]',       # List of document URLs

    # Metadata
    'record_hash': 'string',               # MD5 hash for deduplication
    'source_file': 'string',               # Path to source Bronze file
    'processing_timestamp': 'string',      # Processing timestamp (ISO 8601)
}
```

### Transformation Pipeline

**Bronze → Silver transformation** (example from `src/processing/base_portugal/transformer.py`):

```python
def transform_record(bronze_record, source_country, source_file):
    """
    Transform Bronze OCDS record to Silver unified schema.
    """
    # 1. Extract fields using path mappings
    transformed = {}

    # Simple field extraction
    transformed['ocid'] = get_nested_value(bronze_record, 'ocid')
    transformed['tender_id'] = get_nested_value(bronze_record, 'tender.id')
    transformed['tender_title'] = get_nested_value(bronze_record, 'tender.title')

    # Nested field extraction
    transformed['tender_value_amount'] = get_nested_value(
        bronze_record, 'tender.value.amount'
    )
    transformed['tender_value_currency'] = get_nested_value(
        bronze_record, 'tender.value.currency'
    )

    # Array field extraction (suppliers)
    suppliers = extract_array_values(
        bronze_record, 'awards.*.suppliers.*.name'
    )
    transformed['supplier_names'] = suppliers

    # 2. Clean data
    transformed = clean_record(transformed)  # Strip whitespace, normalize

    # 3. Validate required fields
    if not validate_record(transformed):
        return None  # Skip invalid records

    # 4. Compute metadata
    transformed['record_hash'] = compute_hash(transformed)
    transformed['source_country'] = source_country
    transformed['source_file'] = source_file
    transformed['processing_timestamp'] = datetime.utcnow().isoformat() + 'Z'

    return transformed
```

### Data Quality Rules

**Validation** (in `validators.py`):

1. **Required Fields**:
   - `ocid`: Must be present and non-empty
   - `tender_id`: Must be present
   - `publication_date` OR `closing_date`: At least one date required

2. **Data Types**:
   - Amounts must be numeric (float)
   - Dates must be ISO 8601 format (YYYY-MM-DD)
   - Arrays must be lists

3. **Data Cleaning**:
   - Strip leading/trailing whitespace
   - Normalize empty strings to `""`
   - Normalize null amounts to `0.0`
   - Remove invalid dates (e.g., "1900-01-01")

### Characteristics

| Property | Value |
|----------|-------|
| **Format** | Apache Parquet |
| **Compression** | Snappy |
| **Schema** | Unified 27-field schema |
| **Validation** | Required fields, types, formats |
| **Partitioning** | By source/country/year/month |
| **Mutability** | Can be rebuilt from Bronze |
| **Deduplication** | Hash-based (not yet applied) |

### Current Statistics

- **Total Files**: ~1,097 Parquet files
- **Total Records**: ~692,000 records
- **Schema Consistency**: ✅ All sources use same schema
- **Compression Ratio**: ~10:1 (vs. JSON)

---

## Gold Layer (Analytics-Ready)

### Purpose

**Business-ready datasets** with multi-source unification, deduplication, enrichment, and pre-computed aggregates.

### Location

- **Local**: `data/gold/`
- **MinIO**: `s3://gold/`

### Directory Structure

```
gold/
├── unified/
│   └── all_tenders.parquet         # Master dataset (536,778 records)
├── aggregates/
│   ├── country_summary.parquet     # Per-country statistics
│   ├── monthly_trends.parquet      # Time-series data
│   ├── category_analysis.parquet   # Procurement categories
│   ├── top_buyers.parquet          # Top 100 buyers
│   └── top_suppliers.parquet       # Top 100 suppliers
└── quality/
    └── quality_report_20251220_224904.json
```

### 1. Unified Dataset

**File**: `gold/unified/all_tenders.parquet`

**Schema**: Silver schema (27 fields) + 11 derived fields = **38 fields**

**New Fields**:

```python
{
    # Source Tracking
    'source': 'string',                          # Source name (ocp, base_portugal, ted)

    # Date Partitioning
    'year': 'int',                               # Extracted from publication_date
    'month': 'int',                              # Month (1-12)
    'quarter': 'int',                            # Quarter (1-4)

    # Standardization
    'procurement_category_original': 'string',   # Original category value
    'procurement_category_standardized': 'string', # Standardized to English

    # Quality Flags
    'is_future_date': 'bool',                    # Publication date > today
    'date_quality_flag': 'string',               # 'valid', 'future', 'past'
    'has_value': 'bool',                         # tender_value_amount > 0
    'has_award': 'bool',                         # award_amount > 0

    # Quality Score
    'data_completeness_score': 'float',          # 0.0-1.0 (% of fields populated)
}
```

**Processing Steps** (in `src/gold_layer/unifier.py`):

```python
def create_unified_dataset():
    # 1. Load all Silver sources
    ocp_df = load_silver_source('open_contracting_partnership')
    portugal_df = load_silver_source('base_portugal')
    ted_df = load_silver_source('ted')

    # 2. Tag with source
    ocp_df['source'] = 'ocp'
    portugal_df['source'] = 'base_portugal'
    ted_df['source'] = 'ted'

    # 3. Standardize categories
    for df in [ocp_df, portugal_df, ted_df]:
        df['procurement_category_original'] = df['procurement_category']
        df['procurement_category_standardized'] = df['procurement_category'].map(
            CATEGORY_STANDARDIZATION_MAP
        )

    # 4. Add derived fields
    for df in [ocp_df, portugal_df, ted_df]:
        df['year'] = pd.to_datetime(df['publication_date']).dt.year
        df['month'] = pd.to_datetime(df['publication_date']).dt.month
        df['quarter'] = pd.to_datetime(df['publication_date']).dt.quarter
        df['is_future_date'] = df['publication_date'] > '2025-12-31'
        df['has_value'] = df['tender_value_amount'] > 0
        df['has_award'] = df['award_amount'] > 0
        df['data_completeness_score'] = calculate_completeness(df)

    # 5. Merge all sources
    combined = pd.concat([ocp_df, portugal_df, ted_df], ignore_index=True)

    # 6. Deduplicate by OCID + source
    deduplicated = combined.drop_duplicates(
        subset=['ocid', 'source_publication_id'],
        keep='first'
    )

    # 7. Write to Gold layer
    deduplicated.to_parquet(
        'data/gold/unified/all_tenders.parquet',
        compression='snappy',
        index=False
    )

    return deduplicated
```

**Category Standardization Map**:

```python
CATEGORY_STANDARDIZATION_MAP = {
    # Portuguese → English
    'Empreitada de obras públicas': 'works',
    'Aquisição de serviços': 'services',
    'Aquisição de bens móveis': 'goods',
    'Locação de bens móveis': 'goods',
    'Concessão de serviços públicos': 'services',
    'Concessão de obras públicas': 'works',

    # Albanian → English
    'Punë': 'works',
    'Shërbime': 'services',
    'Mallra': 'goods',

    # Already English
    'works': 'works',
    'services': 'services',
    'goods': 'goods',

    # Empty
    '': '',
    None: '',
}
```

**Statistics**:
- **Total Records**: 536,778 tenders
- **Countries**: 8+ (Germany, UK, Italy, Portugal, Croatia, Kosovo, Albania, Spain, etc.)
- **Date Range**: 2016-02-20 to 2025-12-15
- **File Size**: ~73 MB (compressed Parquet)

### 2. Aggregates

**Purpose**: Pre-computed analytics for fast dashboard queries.

#### Country Summary

**File**: `gold/aggregates/country_summary.parquet`

**Schema**:
```python
{
    'country': 'string',
    'tender_count': 'int',
    'total_value': 'float',
    'avg_value': 'float',
    'max_value': 'float',
    'tenders_with_value': 'int',
    'tenders_with_award': 'int',
    'unique_buyers': 'int',
    'unique_suppliers': 'int',
}
```

**Sample Data**:
| country | tender_count | total_value | avg_value |
|---------|--------------|-------------|-----------|
| germany | 223,113 | 45.2B EUR | 202K EUR |
| uk | 116,323 | 28.5B GBP | 245K GBP |
| italy | 107,891 | 22.1B EUR | 205K EUR |
| portugal | 59,718 | 12.3B EUR | 206K EUR |

#### Monthly Trends

**File**: `gold/aggregates/monthly_trends.parquet`

**Schema**:
```python
{
    'year': 'int',
    'month': 'int',
    'tender_count': 'int',
    'total_value': 'float',
    'avg_value': 'float',
}
```

**Use Case**: Time-series visualization of procurement trends.

#### Category Analysis

**File**: `gold/aggregates/category_analysis.parquet`

**Schema**:
```python
{
    'country': 'string',
    'category': 'string',  # services, goods, works
    'tender_count': 'int',
    'total_value': 'float',
}
```

#### Top Buyers

**File**: `gold/aggregates/top_buyers.parquet`

**Schema**:
```python
{
    'buyer_name': 'string',
    'country': 'string',
    'tender_count': 'int',
    'total_value': 'float',
}
```

**Sample**:
| buyer_name | country | tender_count | total_value |
|------------|---------|--------------|-------------|
| Municipality of Berlin | germany | 1,523 | 2.3B EUR |
| NHS England | uk | 1,245 | 1.8B GBP |

#### Top Suppliers

**File**: `gold/aggregates/top_suppliers.parquet`

**Schema**:
```python
{
    'supplier_name': 'string',
    'country': 'string',
    'award_count': 'int',
    'total_awards': 'float',
}
```

### 3. Quality Reports

**File**: `gold/quality/quality_report_{timestamp}.json`

**Content**:
```json
{
  "generation_timestamp": "2025-12-20T22:49:04Z",
  "total_records": 536778,
  "sources": {
    "ocp": 462226,
    "base_portugal": 57657,
    "ted": 16895
  },
  "countries": {
    "germany": 223113,
    "uk": 116323,
    "italy": 107891,
    "portugal": 59718,
    "croatia": 11961,
    "kosovo": 7396,
    ...
  },
  "completeness": {
    "has_tender_title": 0.89,
    "has_buyer_name": 0.92,
    "has_tender_value": 0.67,
    "has_publication_date": 1.0,
    "has_award_info": 0.45
  },
  "quality_flags": {
    "valid_dates": 536746,
    "future_dates": 32,
    "has_value": 359823,
    "has_award": 241456
  },
  "date_range": {
    "min": "2016-02-20",
    "max": "2025-12-15"
  }
}
```

### Characteristics

| Property | Value |
|----------|-------|
| **Format** | Apache Parquet (datasets), JSON (reports) |
| **Compression** | Snappy |
| **Schema** | Extended Silver schema + derived fields |
| **Deduplication** | ✅ Applied (by OCID + source) |
| **Enrichment** | Category standardization, quality flags |
| **Aggregation** | 5 pre-computed aggregate datasets |
| **Mutability** | Rebuilt nightly/weekly |

### Current Statistics

- **Total Datasets**: 6 Parquet files + 1 JSON report
- **Unified Dataset**: 536,778 records (~73 MB)
- **Aggregates**: <5 MB total
- **Storage**: ~78 MB total

---

## Schema Definitions

### Field-Level Details

#### Required Fields

These fields **must** be present for a record to pass validation:

- `ocid`: Open Contracting ID (unique identifier)
- `tender_id`: Source-specific tender ID
- `publication_date` OR `closing_date`: At least one date field

#### Optional But Important Fields

High-value fields for analytics:

- `tender_title`: Critical for search/filtering
- `buyer_name`: Key for buyer analysis
- `tender_value_amount`: Essential for value-based queries
- `procurement_category`: Used for categorization

#### Metadata Fields

System-generated fields:

- `record_hash`: MD5 hash of key fields (for deduplication)
- `source_file`: Lineage tracking to Bronze source
- `processing_timestamp`: When Silver record was created

### Data Type Constraints

| Field Type | Constraints |
|------------|-------------|
| **string** | Max 500 chars (titles), 200 chars (names) |
| **float** | Non-negative for amounts |
| **int** | Non-negative for counts |
| **list[string]** | Max 100 items (for suppliers/documents) |
| **date** | ISO 8601 format (YYYY-MM-DD) |

---

## Data Quality

### Quality Metrics

**Completeness Score** (Gold layer):

```python
def calculate_completeness_score(record):
    """
    Calculate 0-1 score based on field population.
    """
    important_fields = [
        'tender_title',
        'buyer_name',
        'tender_value_amount',
        'publication_date',
        'procurement_category',
        'award_amount',
    ]

    filled = sum(1 for f in important_fields if record[f] not in ['', 0, None, []])
    return filled / len(important_fields)
```

**Quality Flags**:

- `date_quality_flag`:
  - `'valid'`: 2016-01-01 to 2025-12-31
  - `'future'`: > 2025-12-31 (likely data errors)
  - `'past'`: < 2016-01-01 (likely data errors)

### Known Data Quality Issues

1. **BASE Portugal**: Some records have empty titles/buyers (extraction bug - being fixed)
2. **TED**: ~2,000 records with future dates (closing_date used as publication_date)
3. **Empty Categories**: ~30% of records missing procurement category

### Deduplication Strategy

**Current Approach** (in Gold layer):

```python
# Deduplicate by OCID + source publication ID
df_dedup = df.drop_duplicates(
    subset=['ocid', 'source_publication_id'],
    keep='first'  # Keep first occurrence
)
```

**Future Enhancement** (planned):

- Fuzzy matching on title + buyer + date
- Link same tender across multiple sources
- Create `duplicate_group_id` field

---

## Partitioning Strategy

### Bronze Layer Partitioning

**By**: Source → Country → Year → Month → Day

**Benefits**:
- Efficient incremental extraction (process only new dates)
- Easy to identify source/country data
- Supports date-range filtering

**Drawbacks**:
- Many small files (can be inefficient for reads)

### Silver Layer Partitioning

**By**: Source → Country → Year → Month

**Benefits**:
- Fewer files than Bronze (daily → monthly)
- Supports common query patterns (country + date range)
- Efficient for analytics

**Partitioning in Parquet**:
```python
df.to_parquet(
    'data/silver/base_portugal/',
    partition_cols=['source_country', 'year', 'month'],
    compression='snappy'
)
```

Resulting structure:
```
silver/base_portugal/
├── source_country=portugal/
│   ├── year=2024/
│   │   ├── month=08/
│   │   │   └── part-0.parquet
│   │   └── month=12/
│   │       └── part-0.parquet
│   └── year=2025/
│       └── month=01/
│           └── part-0.parquet
```

### Gold Layer Partitioning

**Unified Dataset**: Single file (no partitioning)
- Reason: Small enough (~73 MB) to load entirely
- Future: Partition by country if dataset grows > 1 GB

**Aggregates**: No partitioning (very small files)

---

## Performance Considerations

### File Sizes

| Layer | Format | Avg File Size | Total Size |
|-------|--------|---------------|------------|
| **Bronze** | JSON | ~500 KB | ~1.2 GB |
| **Silver** | Parquet | ~1-5 MB | ~350 MB |
| **Gold** | Parquet | ~73 MB (unified) | ~78 MB |

### Query Performance

**Dremio Query Times** (536K records):

- Simple count: ~1-2 seconds (first run), <500ms (cached)
- Aggregation (10 groups): ~2-3 seconds
- Complex filter + join: ~5-10 seconds

**Optimization Strategies**:
- **Columnar Format**: Parquet allows reading only needed columns
- **Compression**: Snappy reduces I/O by ~10x vs. JSON
- **Partitioning**: Predicate pushdown skips irrelevant partitions
- **Caching**: Dremio caches query results

---

## Example Workflows

### Workflow 1: Adding New Data

```bash
# 1. Extract new data → Bronze
make extract-portugal

# 2. Process Bronze → Silver (incremental)
make process-incremental

# 3. Rebuild Gold layer (includes new Silver data)
make gold-layer

# 4. Refresh Dremio metadata
# (Manual step in Dremio UI)
```

### Workflow 2: Reprocessing After Bug Fix

```bash
# 1. Fix processor logic (e.g., src/processing/base_portugal/transformer.py)

# 2. Delete Silver layer for source
rm -rf data/silver/base_portugal/

# 3. Reprocess from Bronze
make process-portugal

# 4. Rebuild Gold layer
make gold-layer
```

### Workflow 3: Querying Data

```sql
-- Query Silver layer (single source)
SELECT COUNT(*) FROM minio.silver.base_portugal.portugal;

-- Query Gold layer (all sources unified)
SELECT source_country, COUNT(*) as count
FROM minio.gold.unified
GROUP BY source_country
ORDER BY count DESC;

-- Query Gold aggregates
SELECT * FROM minio.gold.aggregates
WHERE country = 'portugal';
```

---

## References

### Internal Documentation
- [Architecture](architecture.md) - System design and components
- [Data Sources - European](data_sources_european.md)
- [Data Sources - Portugal](data_sources_portugal.md)

### External Standards
- [OCDS Standard](https://standard.open-contracting.org/) - Open Contracting Data Standard
- [Apache Parquet](https://parquet.apache.org/docs/) - Parquet format specification
- [Medallion Architecture](https://www.databricks.com/glossary/medallion-architecture) - Databricks guide

### Code References
- Bronze → Silver: `src/processing/{source}/transformer.py`
- Silver → Gold: `src/gold_layer/unifier.py`
- Schema definitions: `src/processing/{source}/config.py`

---

**Last Updated**: 2024-12-21
**Version**: 1.0
**Status**: ✅ All layers operational
