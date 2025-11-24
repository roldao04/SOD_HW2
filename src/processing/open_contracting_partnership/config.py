"""
Configuration for Open Contracting Partnership Silver layer processing.
Defines unified schema and country-specific field mappings.
"""

# Unified Silver layer schema (Parquet output)
SILVER_SCHEMA = {
    'ocid': 'string',
    'source_country': 'string',
    'source_publication_id': 'string',
    'tender_id': 'string',
    'tender_title': 'string',
    'tender_value_amount': 'float',
    'tender_value_currency': 'string',
    'tender_status': 'string',
    'publication_date': 'string',  # ISO format YYYY-MM-DD
    'tender_start_date': 'string',
    'tender_end_date': 'string',
    'procurement_method': 'string',
    'procurement_category': 'string',
    'buyer_id': 'string',
    'buyer_name': 'string',
    'supplier_ids': 'list[string]',  # Array of supplier IDs
    'supplier_names': 'list[string]',  # Array of supplier names
    'award_date': 'string',
    'award_amount': 'float',
    'award_currency': 'string',
    'num_lots': 'int',
    'num_tenderers': 'int',
    'num_awards': 'int',
    'document_urls': 'list[string]',  # Array of document URLs
    'record_hash': 'string',  # MD5 hash for deduplication
    'source_file': 'string',  # Path to source Bronze file
    'processing_timestamp': 'string',  # ISO timestamp
}

# Field path mappings for different country OCDS implementations
# Format: 'unified_field': ['path.to.field', 'alternative.path']

# Common fields across all countries
COMMON_FIELD_MAPPINGS = {
    'ocid': ['ocid'],
    'tender_id': ['tender.id', 'id'],
    'tender_title': ['tender.title'],
    'tender_status': ['tender.status'],
    'publication_date': ['date'],
    'tender_start_date': ['tender.tenderPeriod.startDate'],
    'tender_end_date': ['tender.tenderPeriod.endDate'],
    'procurement_method': ['tender.procurementMethod'],
    'procurement_category': ['tender.mainProcurementCategory'],
}

# Kosovo-specific mappings (uses 'award' singular, different structure)
KOSOVO_FIELD_MAPPINGS = {
    **COMMON_FIELD_MAPPINGS,
    'tender_value_amount': ['tender.value.amount'],
    'tender_value_currency': ['tender.value.currency'],
    'buyer_id': ['tender.procuringEntity.party.id'],
    'buyer_name': ['tender.procuringEntity.party.name'],
    'award_date': ['award.0.date'],  # award is array
    'award_amount': ['award.0.value.amount'],
    'award_currency': ['award.0.value.currency'],
    'supplier_ids': ['award.0.suppliers.*.party.id'],  # Extract from suppliers array
    'supplier_names': ['award.0.suppliers.*.party.name'],
    'num_lots': ['tender.lots'],  # Count array length
    'num_tenderers': ['tender.tenderers'],  # Count array length
    'document_urls': ['tender.documents.*.url'],
}

# UK-specific mappings (uses 'awards' plural, has 'buyer' at root)
UK_FIELD_MAPPINGS = {
    **COMMON_FIELD_MAPPINGS,
    'tender_value_amount': ['tender.value.amount'],
    'tender_value_currency': ['tender.value.currency'],
    'buyer_id': ['buyer.id'],
    'buyer_name': ['buyer.name'],
    'award_date': ['awards.0.date'],  # awards is array
    'award_amount': ['awards.0.value.amount'],
    'award_currency': ['awards.0.value.currency'],
    'supplier_ids': ['awards.0.suppliers.*.id'],
    'supplier_names': ['awards.0.suppliers.*.name'],
    'num_lots': ['tender.lots'],
    'num_tenderers': ['bids.statistics'],  # Different structure
    'document_urls': ['tender.documents.*.url'],
}

# Germany, Italy, Croatia, Albania - similar to UK structure
STANDARD_EU_FIELD_MAPPINGS = UK_FIELD_MAPPINGS

# Spain - similar to UK structure
SPAIN_FIELD_MAPPINGS = UK_FIELD_MAPPINGS

# Country to mapping configuration
COUNTRY_MAPPINGS = {
    'kosovo': KOSOVO_FIELD_MAPPINGS,
    'uk': UK_FIELD_MAPPINGS,
    'germany': STANDARD_EU_FIELD_MAPPINGS,
    'italy': STANDARD_EU_FIELD_MAPPINGS,
    'croatia': STANDARD_EU_FIELD_MAPPINGS,
    'albania': STANDARD_EU_FIELD_MAPPINGS,
    'spain': SPAIN_FIELD_MAPPINGS,
}

# Default values for missing fields
DEFAULT_VALUES = {
    'string': '',
    'float': 0.0,
    'int': 0,
    'list[string]': [],
}

# Parquet output configuration
PARQUET_CONFIG = {
    'compression': 'snappy',  # Good balance of speed and compression
    'row_group_size': 10000,
    'partition_cols': ['source_country', 'year', 'month'],
}

# Processing configuration
PROCESSING_CONFIG = {
    'batch_size': 1000,  # Records per batch
    'max_workers': 4,  # Parallel processing workers
    'log_level': 'INFO',
}
