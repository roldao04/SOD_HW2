"""
Configuration for BASE Portugal Silver layer processing.
Defines unified schema and Portugal-specific field mappings.
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

# Field path mappings for Portugal OCDS implementation
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

# Portugal-specific mappings (BASE portal via dados.gov.pt)
# Uses standard OCDS format similar to UK/EU structure
PORTUGAL_FIELD_MAPPINGS = {
    **COMMON_FIELD_MAPPINGS,
    'tender_value_amount': ['tender.value.amount'],
    'tender_value_currency': ['tender.value.currency'],
    'buyer_id': ['buyer.id', 'parties.0.id'],
    'buyer_name': ['buyer.name', 'parties.0.name'],
    'award_date': ['awards.0.date'],  # awards is array
    'award_amount': ['awards.0.value.amount'],
    'award_currency': ['awards.0.value.currency'],
    'supplier_ids': ['awards.*.suppliers.*.id', 'awards.0.suppliers.*.id'],
    'supplier_names': ['awards.*.suppliers.*.name', 'awards.0.suppliers.*.name'],
    'num_lots': ['tender.lots'],  # Count array length
    'num_tenderers': ['tender.numberOfTenderers', 'bids.statistics'],
    'document_urls': ['tender.documents.*.url'],
}

# Country to mapping configuration
COUNTRY_MAPPINGS = {
    'portugal': PORTUGAL_FIELD_MAPPINGS,
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
