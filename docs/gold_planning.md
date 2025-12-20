# Gold Layer Planning Document

**Date**: 2025-12-20
**Investigation Phase**: COMPLETE
**Status**: Ready for implementation

---

## Executive Summary

Phase 1 investigation revealed **CRITICAL data quality issues** that must be addressed before Gold layer implementation:

- ✅ **Schemas aligned**: All 3 sources use identical 27-field schema
- ❌ **TED country extraction broken**: ALL 16,846 records show `country: unknown`
- ❌ **Base Portugal data EMPTY**: All 213K records have blank titles, buyers, values
- ⚠️ **Future dates**: TED has records dated up to 2121
- ⚠️ **Category standardization needed**: Mix of English/Portuguese terms

---

## 1. Current Silver Layer State

### Data Inventory

| Source | Records | Countries | Date Range | File Location |
|--------|---------|-----------|------------|---------------|
| **OCP** | 462,226 | 7 (DE, UK, IT, HR, XK, AL, ES) | 2025-01-01 to 2025-12-10 | `data/silver/open_contracting_partnership/` |
| **TED** | 16,846 | **unknown** (bug) | 2016-02-20 to **2121-08-30** | `data/silver/ted/unknown/` |
| **Base Portugal** | 213,274 | portugal | **2025-01-01** (all same) | `data/silver/base_portugal/portugal/2025/01/` |
| **TOTAL** | **692,346** | 8+ (if TED fixed) | 2016 - 2025 | - |

### Schema Consistency

✅ **EXCELLENT NEWS**: All 3 sources share identical schema (27 fields):

```python
{
    'ocid', 'source_country', 'source_publication_id', 'tender_id',
    'tender_title', 'tender_value_amount', 'tender_value_currency',
    'tender_status', 'publication_date', 'tender_start_date',
    'tender_end_date', 'procurement_method', 'procurement_category',
    'buyer_id', 'buyer_name', 'supplier_ids', 'supplier_names',
    'award_date', 'award_amount', 'award_currency', 'num_lots',
    'num_tenderers', 'num_awards', 'document_urls', 'record_hash',
    'source_file', 'processing_timestamp'
}
```

---

## 2. CRITICAL ISSUE #1: TED Country Extraction Bug

### Problem Description

**All 16,846 TED records show `source_country: unknown`**

### Root Cause Analysis

Investigation of `src/processing/ted/transformer.py:64-95` (`extract_country_code()` function):

**TED Bronze Data Structure** (verified from `data/bronze/partner_data/andré/ted_contracts.parquet`):

```python
{
    'source': 'EU Tenders (TED)' | 'BASE.gov.pt' | 'Partner Team',
    'contracting_authorities': [
        {'country': 'DEU' | None, 'name': '...', 'nipc': '...'}
    ],
    'execution_location': 'Portugal, Aveiro, Espinho' | None,
    'execution_country': '' | None  # Always empty
}
```

**Bronze Data Distribution**:
- **EU Tenders (TED)**: 15,600 records (92%) - **HAS country codes** ('DEU', 'FRA', etc.)
- **BASE.gov.pt**: 1,250 records (7%) - **NO country**, but has `execution_location: "Portugal, City, Region"`
- **Partner Team**: 100 records (1%) - **NO country**, has `execution_location: "Lisboa, Portugal"`

### Current Transformer Logic (BROKEN)

```python
def extract_country_code(record: dict) -> str:
    # 1. Try contracting_authorities (works for 92%)
    authorities = record.get('contracting_authorities', [])
    if authorities and authorities[0].get('country'):
        country_code = authorities[0]['country']
        return COUNTRY_CODE_MAPPING.get(country_code, country_code.lower())

    # 2. Try execution_location (DOESN'T WORK - wrong parsing)
    exec_location = record.get('execution_location')
    if exec_location:
        country_part = exec_location.split('-')[0]  # ❌ Splits on "-", should split on ","
        # ... wrong logic

    # 3. Fallback
    return 'unknown'  # ❌ All 1,350 records end up here
```

### Solution: Enhanced Country Extraction

**Fix `src/processing/ted/transformer.py:extract_country_code()`:**

```python
def extract_country_code(record: dict) -> str:
    """
    Extract country from TED record using 4-tier fallback strategy.
    """
    # Tier 1: contracting_authorities[0].country (works for EU TED data)
    authorities = record.get('contracting_authorities', [])
    if authorities and isinstance(authorities, list) and len(authorities) > 0:
        country_code = authorities[0].get('country')
        if country_code:
            return COUNTRY_CODE_MAPPING.get(country_code, country_code.lower())

    # Tier 2: execution_location parsing
    # Format: "Portugal, City, Region" or "City, Country"
    exec_location = record.get('execution_location')
    if exec_location and isinstance(exec_location, str):
        parts = exec_location.split(',')
        if parts:
            # Check first part (usually country for BASE.gov.pt data)
            first_part = parts[0].strip().lower()
            if first_part == 'portugal':
                return 'portugal'
            # Check last part (for "City, Country" format)
            if len(parts) > 1:
                last_part = parts[-1].strip().lower()
                if last_part == 'portugal':
                    return 'portugal'

    # Tier 3: Source field mapping
    source = record.get('source', '')
    SOURCE_COUNTRY_MAP = {
        'BASE.gov.pt': 'portugal',
        'TED.europa.eu': 'unknown',  # Multi-country
    }
    for key, country in SOURCE_COUNTRY_MAP.items():
        if key in source:
            return country

    # Tier 4: Buyer name pattern matching (last resort)
    buyer_name = ''
    if authorities and len(authorities) > 0:
        buyer_name = authorities[0].get('name', '')

    # Portuguese entity patterns
    if any(word in buyer_name.lower() for word in ['município', 'câmara', 'junta', 'governo']):
        return 'portugal'

    return 'unknown'
```

### Expected Impact

- ✅ Fix **1,350 records** (BASE.gov.pt + Partner Team) → `country: portugal`
- ✅ Keep **15,600 records** working with existing DEU/FRA/etc. mapping
- ✅ Reduce unknown from **100%** to **~0%**

### Files to Modify

1. `src/processing/ted/transformer.py` - replace `extract_country_code()` function
2. `src/processing/ted/config.py` - add `SOURCE_COUNTRY_MAP` constant

---

## 3. CRITICAL ISSUE #2: Base Portugal Data Completely Empty

### Problem Description

**All 213,274 Portugal records have BLANK data**:
- ❌ `tender_title`: "" (0% complete)
- ❌ `buyer_name`: "" (0% complete)
- ❌ `tender_value_amount`: 0.0 (0% complete)
- ❌ `procurement_category`: "" (0% complete)
- ✅ `publication_date`: "2025-01-01" (100% complete, but ALL same date)
- ✅ `tender_value_currency`: "EUR" (100% complete)

### Root Cause: Extraction Bug

Traced to **Bronze layer** - the issue originates in extraction, NOT processing:

**Bronze Data** (`data/bronze/base_portugal/portugal/2025/01/01/records_20251220_053842.json`):
```json
{
  "ocid": "ocds-base-pt-2025-11123021",
  "date": "2025-01-01",
  "tender": {
    "id": "11123021",
    "title": "",
    "status": "active",
    "value": {
      "amount": 0.0,
      "currency": "EUR"
    }
  },
  "buyer": {
    "id": "",
    "name": ""
  },
  "awards": []
}
```

### Affected Code

`src/extractors/base_portugal/extractor.py:240-320` (`_row_to_ocds()` method):

```python
def _row_to_ocds(self, row: Dict, year: int) -> Optional[Dict]:
    """Convert Excel row to OCDS format."""
    # ... field mapping logic ...

    ocds_record = {
        'tender': {
            'title': row.get('Objeto do Contrato') or row.get('Descrição') or '',  # ❌ Column names wrong?
            # ...
        },
        'buyer': {
            'name': row.get('Adjudicante') or row.get('Entidade Adjudicante') or ''  # ❌ Column names wrong?
        }
    }
```

### Investigation Needed

**Before fixing**, need to verify:

1. **XLSX column names** - Do actual source files use these column names?
   - Check: Download sample XLSX from `https://dados.gov.pt/api/1/datasets/{dataset_id}/`
   - Verify: Header row matches expected names

2. **Excel reading logic** - Is `openpyxl` reading correctly?
   - File: `src/extractors/base_portugal/extractor.py:198-238` (`_convert_xlsx_to_ocds`)

3. **Data quality** - Are source XLSX files actually empty?
   - Manual inspection of downloaded XLSX needed

### Recommendation

🛑 **DO NOT include Base Portugal in Gold layer until extraction is fixed**

**Options**:
1. **Fix extractor** (2-4 hours investigation + 2 hours fix)
2. **Exclude from Gold** (use only OCP + TED data: 479K records)
3. **Mark as placeholder** (include but flag as low-quality)

**Decision needed**: This is a prerequisite issue blocking Gold layer value.

---

## 4. Data Quality Issue: Future Dates

### Problem Description

TED data contains **impossible future dates**:
- Date range: `2016-02-20` to `2121-08-30` (**96 years in the future!**)
- Root cause: `closing_date` used as fallback for `publication_date`

### Source

`src/processing/ted/config.py:85`:
```python
'publication_date': ['publication_date', 'closing_date'],  # ❌ Fallback causes future dates
```

Many tenders have `publication_date: null` but `closing_date: 2030-XX-XX` (tender deadline), which gets incorrectly used as publication date.

### Solution: Add Flag Instead of Filter

**Gold layer approach** (per user decision):

```python
# Add derived field
df['is_future_date'] = df['publication_date'] > '2025-12-31'

# Keep records but flag them
df['date_quality_flag'] = df.apply(
    lambda row: 'future' if row['is_future_date']
                else 'past' if row['publication_date'] < '2016-01-01'
                else 'valid',
    axis=1
)
```

**Analytics queries can then filter**:
```sql
SELECT * FROM gold.all_tenders
WHERE date_quality_flag = 'valid'  -- Excludes future dates
```

### Expected Impact

- ~2,000 records with future dates (rough estimate)
- Keep data for transparency, let analysts decide

---

## 5. Category Standardization Issue

### Problem Description

Procurement categories mixed across languages:

**OCP**: English categories
- `'services'` (155K), `'goods'` (85K), `'works'` (79K)
- Also has empty: `''` (141K records)

**TED**: Portuguese categories (from BASE.gov.pt subset)
- `'Empreitada de obras públicas'` (works)
- `'Aquisição de serviços'` (services)
- `'Aquisição de bens móveis'` (goods)

**Base Portugal**: Empty (due to extraction bug)

### Solution: Standardization Map

```python
CATEGORY_STANDARDIZATION_MAP = {
    # Portuguese to English
    'Empreitada de obras públicas': 'works',
    'Aquisição de serviços': 'services',
    'Aquisição de bens móveis': 'goods',
    'Locação de bens móveis': 'goods',
    'Concessão de serviços públicos': 'services',
    'Concessão de obras públicas': 'works',

    # Albanian (from Kosovo data)
    'Punë': 'works',
    'Shërbime': 'services',
    'Mallra': 'goods',

    # Already English (pass-through)
    'works': 'works',
    'services': 'services',
    'goods': 'goods',

    # Edge cases
    '': '',  # Keep empty as-is
    None: '',
}

# Apply in Gold layer
df['procurement_category_standardized'] = df['procurement_category'].map(CATEGORY_STANDARDIZATION_MAP)
df['procurement_category_original'] = df['procurement_category']  # Preserve original
```

---

## 6. Gold Layer Implementation Plan (REVISED)

### Pre-Requisites (BLOCKERS)

**Must complete BEFORE Gold layer**:

1. ✅ **Fix TED country extraction** - `src/processing/ted/transformer.py`
   - Effort: 2 hours
   - Impact: Fixes 16,846 records
   - Re-run: `make process-incremental`

2. 🛑 **Fix Base Portugal extraction** - `src/extractors/base_portugal/extractor.py`
   - Effort: 4-6 hours (investigation + fix)
   - Impact: Fixes 213,274 records OR decides to exclude
   - Re-run: `make extract` + `make process`

**Decision Point**: Proceed with Gold layer using only OCP + TED (479K records) OR wait for Portugal fix?

### Phase 1: Data Quality Fixes (PRIORITY)

**Tasks**:
1. Fix TED transformer country extraction ✅
2. Re-process TED Silver layer
3. Investigate Base Portugal extractor bug
4. Decision: Fix Portugal OR exclude from Gold

**Timeline**: 6-10 hours

### Phase 2: Gold Layer Structure

**Directory layout**:
```
src/gold_layer/
├── __init__.py
├── config.py           # Constants, mappings, schema
├── unifier.py          # Merge Silver sources
├── aggregator.py       # Pre-computed aggregates
├── quality.py          # Quality reports
├── main.py             # CLI entry point
└── utils.py            # Helpers

data/gold/
├── unified/
│   └── all_tenders.parquet        # Master dataset
├── aggregates/
│   ├── country_summary.parquet
│   ├── monthly_trends.parquet
│   ├── category_analysis.parquet
│   ├── top_buyers.parquet
│   └── top_suppliers.parquet
└── quality/
    ├── deduplication_report.json
    ├── coverage_report.json
    └── validation_report.json
```

### Phase 3: Unified Dataset (`unifier.py`)

**Transformation pipeline**:

```python
def create_unified_dataset():
    """Merge all Silver sources into Gold unified dataset."""

    # 1. Load Silver data
    ocp_df = load_silver('open_contracting_partnership')
    ted_df = load_silver('ted')
    portugal_df = load_silver('base_portugal')  # IF FIXED

    # 2. Add source tag
    ocp_df['source'] = 'ocp'
    ted_df['source'] = 'ted'
    portugal_df['source'] = 'base_portugal'

    # 3. Standardize categories
    for df in [ocp_df, ted_df, portugal_df]:
        df['procurement_category_original'] = df['procurement_category']
        df['procurement_category'] = df['procurement_category'].map(CATEGORY_STANDARDIZATION_MAP)

    # 4. Add derived fields
    for df in [ocp_df, ted_df, portugal_df]:
        df['year'] = pd.to_datetime(df['publication_date']).dt.year
        df['month'] = pd.to_datetime(df['publication_date']).dt.month
        df['quarter'] = pd.to_datetime(df['publication_date']).dt.quarter
        df['is_future_date'] = df['publication_date'] > '2025-12-31'
        df['has_value'] = df['tender_value_amount'] > 0
        df['has_award'] = df['award_amount'] > 0
        df['data_quality_score'] = calculate_completeness_score(df)

    # 5. Combine
    combined = pd.concat([ocp_df, ted_df, portugal_df], ignore_index=True)

    # 6. Deduplicate by OCID + source_publication_id
    combined_dedup = combined.drop_duplicates(
        subset=['ocid', 'source_publication_id'],
        keep='first'
    )

    # 7. Write partitioned Parquet
    combined_dedup.to_parquet(
        'data/gold/unified/all_tenders.parquet',
        partition_cols=['source_country', 'year', 'month'],
        compression='snappy'
    )

    return combined_dedup
```

**Schema** (30 fields = 27 Silver + 3 new):
- Added: `source`, `year`, `month`, `quarter`, `is_future_date`, `has_value`, `has_award`, `data_quality_score`, `procurement_category_original`

### Phase 4: Aggregates (`aggregator.py`)

**5 pre-computed tables**:

1. **`country_summary.parquet`** - Per-country stats
2. **`monthly_trends.parquet`** - Time-series
3. **`category_analysis.parquet`** - Procurement type breakdown
4. **`top_buyers.parquet`** - Top 100 buyers
5. **`top_suppliers.parquet`** - Top 100 suppliers

### Phase 5: Makefile Integration

```makefile
# Add to Makefile
gold-layer:          # Build complete Gold layer
	$(PYTHON) -m src.gold_layer.main --all

gold-unified:        # Create unified dataset only
	$(PYTHON) -m src.gold_layer.unifier

gold-aggregates:     # Generate aggregates only
	$(PYTHON) -m src.gold_layer.aggregator

gold-quality:        # Run quality reports
	$(PYTHON) -m src.gold_layer.quality

gold-stats:          # Show Gold layer statistics
	$(PYTHON) -m src.gold_layer.main --stats
```

---

## 7. Revised Timeline

**Assuming TED fix only** (Portugal excluded):

| Phase | Tasks | Effort | Blockers |
|-------|-------|--------|----------|
| **Phase 0** | Fix TED country extraction | 2 hours | None |
| **Phase 1** | Re-process TED Silver | 30 mins | Phase 0 |
| **Phase 2** | Create Gold structure | 3 hours | Phase 1 |
| **Phase 3** | Unified dataset (OCP+TED) | 4 hours | Phase 2 |
| **Phase 4** | Generate aggregates | 3 hours | Phase 3 |
| **Phase 5** | Makefile integration | 1 hour | Phase 4 |
| **Phase 6** | Quality reports | 2 hours | Phase 5 |

**Total**: **15.5 hours** (OCP + TED only, ~479K records)

**If Portugal is fixed**: Add 6-10 hours for extraction fix + re-processing

---

## 8. Expected Gold Layer Output

**Dataset sizes** (OCP + TED only):

| Table | Estimated Records | Estimated Size |
|-------|------------------|----------------|
| `unified/all_tenders.parquet` | ~475,000 (after dedup) | ~120 MB |
| `aggregates/country_summary.parquet` | ~8 rows | < 1 MB |
| `aggregates/monthly_trends.parquet` | ~12 rows (2025 months) | < 1 MB |
| `aggregates/category_analysis.parquet` | ~24 rows (8 countries × 3 categories) | < 1 MB |
| `aggregates/top_buyers.parquet` | 100 rows | < 1 MB |
| `aggregates/top_suppliers.parquet` | 100 rows | < 1 MB |

**Country coverage** (after TED fix):
- Germany: ~218K
- UK: ~116K
- Italy: ~107K
- Croatia: ~11K
- Kosovo: ~7K
- Albania: ~700
- Spain: ~100
- **+ EU countries from TED**: France, Sweden, Czech Republic, Austria, Poland, etc. (15,600 records distributed)

---

## 9. Recommendations

### Immediate Actions

1. ✅ **Fix TED transformer** (`src/processing/ted/transformer.py`)
   - Use 4-tier fallback strategy
   - Test with Bronze data samples
   - Re-run processing: `make process-incremental`

2. 🔍 **Investigate Base Portugal**
   - Download sample XLSX manually
   - Verify column names
   - Fix or decide to exclude

3. 📋 **Document decision**
   - Include Portugal (if fixed) OR
   - Proceed with OCP+TED only

### Gold Layer Strategy

**Recommended approach**:

1. **Phase 0**: Fix TED (2 hours) ← **START HERE**
2. **Decision Gate**: Portugal status
   - If fixable in < 6 hours → fix
   - If not → proceed without Portugal
3. **Phase 2-6**: Build Gold layer (13.5 hours)

**Total**: 15.5 hours (without Portugal) or 21.5 hours (with Portugal)

---

## 10. Next Steps

1. **Immediate**:
   - ✅ Create this documentation
   - 🔧 Fix TED transformer
   - 🔧 Fix Base Portugal extractor
   - ♻️ Re-process Silver layers

2. **After fixes validated**:
   - Create Gold layer structure
   - Implement unified dataset
   - Generate aggregates
   - Update Makefile

---

**Status**: ✅ Documentation complete, proceeding with fixes
