"""
Configuration for Gold Layer processing.

Defines:
- Category standardization mappings
- Gold layer schema
- Quality thresholds
- Default values
"""

from typing import Dict, List

# ============================================================================
# CATEGORY STANDARDIZATION
# ============================================================================

# Map various category names to standardized English categories
CATEGORY_STANDARDIZATION_MAP: Dict[str, str] = {
    # Portuguese (from TED BASE.gov.pt data)
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

    # Croatian
    'Radovi': 'works',
    'Usluge': 'services',
    'Roba': 'goods',

    # Already English (pass-through)
    'works': 'works',
    'services': 'services',
    'goods': 'goods',
    'supplies': 'goods',  # Alternate term

    # Edge cases
    '': '',
    None: '',
}

# ============================================================================
# GOLD LAYER SCHEMA
# ============================================================================

# Fields from Silver layer (27 fields)
SILVER_FIELDS = [
    'publication_date',
    'tender_start_date',
    'tender_end_date',
    'award_date',
    'tender_value_amount',
    'award_amount',
    'tender_value_currency',
    'award_currency',
    'ocid',
    'source_country',
    'source_publication_id',
    'tender_id',
    'tender_title',
    'tender_status',
    'procurement_method',
    'procurement_category',
    'buyer_id',
    'buyer_name',
    'record_hash',
    'source_file',
    'processing_timestamp',
    'supplier_ids',
    'supplier_names',
    'document_urls',
    'num_lots',
    'num_tenderers',
    'num_awards',
]

# New derived fields for Gold layer
DERIVED_FIELDS = [
    'source',  # Source system: 'ocp', 'ted', 'base_portugal'
    'year',  # Extracted from publication_date
    'month',  # Extracted from publication_date
    'quarter',  # Extracted from publication_date (Q1-Q4)
    'procurement_category_original',  # Preserve original before standardization
    'procurement_category_standardized',  # Standardized category
    'is_future_date',  # Flag for dates > current date
    'has_value',  # Flag for tender_value_amount > 0
    'has_award',  # Flag for award_amount > 0
    'data_completeness_score',  # 0-1 score based on field completeness
    'date_quality_flag',  # 'valid', 'future', 'past', 'missing'
]

# Complete Gold schema (Silver + Derived)
GOLD_SCHEMA = SILVER_FIELDS + DERIVED_FIELDS

# ============================================================================
# QUALITY THRESHOLDS
# ============================================================================

# Fields considered "required" for quality scoring
REQUIRED_FIELDS = [
    'ocid',
    'publication_date',
    'tender_title',
    'buyer_name',
    'source_country',
]

# Fields considered "important" for quality scoring (weighted 0.5)
IMPORTANT_FIELDS = [
    'tender_value_amount',
    'procurement_category',
    'procurement_method',
    'tender_status',
]

# Date boundaries for quality flagging
MIN_VALID_DATE = '2000-01-01'
MAX_VALID_DATE = '2030-12-31'  # Conservative future limit

# ============================================================================
# AGGREGATION CONFIGURATIONS
# ============================================================================

# Top N items for aggregate tables
TOP_N_BUYERS = 100
TOP_N_SUPPLIERS = 100

# ============================================================================
# DEFAULT VALUES
# ============================================================================

DEFAULT_VALUES = {
    'string': '',
    'float': 0.0,
    'int': 0,
    'bool': False,
    'list': [],
}

# ============================================================================
# FILE PATHS
# ============================================================================

# Default paths (relative to project root)
DEFAULT_SILVER_DIR = 'data/silver'
DEFAULT_GOLD_DIR = 'data/gold'

# Gold subdirectories
GOLD_UNIFIED_DIR = 'data/gold/unified'
GOLD_AGGREGATES_DIR = 'data/gold/aggregates'
GOLD_QUALITY_DIR = 'data/gold/quality'

# ============================================================================
# PARTITION CONFIGURATION
# ============================================================================

# Partitioning columns for unified dataset
# Reduced to country + year to stay under 1024 partition limit
PARTITION_COLS = ['source_country', 'year']

# Compression algorithm
COMPRESSION = 'snappy'  # Fast compression, good for analytics

# ============================================================================
# AGGREGATE TABLE DEFINITIONS
# ============================================================================

AGGREGATE_TABLES = {
    'country_summary': {
        'filename': 'country_summary.parquet',
        'description': 'Per-country aggregated statistics',
        'group_by': ['source_country'],
    },
    'monthly_trends': {
        'filename': 'monthly_trends.parquet',
        'description': 'Time-series trends by month',
        'group_by': ['year', 'month'],
    },
    'category_analysis': {
        'filename': 'category_analysis.parquet',
        'description': 'Procurement category breakdown',
        'group_by': ['source_country', 'procurement_category_standardized'],
    },
    'top_buyers': {
        'filename': 'top_buyers.parquet',
        'description': f'Top {TOP_N_BUYERS} buyers by transaction count',
        'limit': TOP_N_BUYERS,
    },
    'top_suppliers': {
        'filename': 'top_suppliers.parquet',
        'description': f'Top {TOP_N_SUPPLIERS} suppliers by transaction count',
        'limit': TOP_N_SUPPLIERS,
    },
}

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = 'INFO'
