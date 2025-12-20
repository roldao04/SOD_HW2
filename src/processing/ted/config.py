"""
Configuration for TED (Tenders Electronic Daily) Silver layer processing.
Defines unified schema and TED-specific field mappings.
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

# TED country code mapping (ISO 3166-1 alpha-3 to lowercase country names)
COUNTRY_CODE_MAPPING = {
    'DEU': 'germany',
    'FRA': 'france',
    'SWE': 'sweden',
    'CZE': 'czech_republic',
    'CHE': 'switzerland',
    'BEL': 'belgium',
    'POL': 'poland',
    'NOR': 'norway',
    'AUT': 'austria',
    'HRV': 'croatia',
    'PRT': 'portugal',
    'ESP': 'spain',
    'ITA': 'italy',
    'NLD': 'netherlands',
    'DNK': 'denmark',
    'FIN': 'finland',
    'GRC': 'greece',
    'HUN': 'hungary',
    'IRL': 'ireland',
    'LUX': 'luxembourg',
    'ROU': 'romania',
    'SVK': 'slovakia',
    'SVN': 'slovenia',
    'GBR': 'united_kingdom',
    'ALB': 'albania',
    'BIH': 'bosnia_herzegovina',
    'XKX': 'kosovo',
    'MKD': 'north_macedonia',
    'MNE': 'montenegro',
    'SRB': 'serbia',
}

# Field path mappings for TED parquet data
# Format: 'unified_field': 'ted_field_name'
TED_FIELD_MAPPINGS = {
    # Core identification (ocid generated dynamically)
    'source_publication_id': 'source_id',
    'tender_id': 'source_id',

    # Tender information
    'tender_title': 'contract_object',
    'tender_value_amount': ['contract_price', 'effective_total_price'],  # Try contract_price first
    'tender_value_currency': 'currency',
    'tender_status': 'state',

    # Dates
    'publication_date': ['publication_date', 'closing_date'],  # Fallback to closing_date (82% coverage)
    'tender_start_date': 'contract_date',
    'tender_end_date': ['closing_date', 'execution_deadline'],  # Try closing_date first
    'award_date': 'contract_date',

    # Procurement classification
    'procurement_method': 'procedure_type',
    'procurement_category': 'contract_types',  # Extract first element from array

    # Parties (extracted from nested structures)
    'buyer_id': 'contracting_authorities',  # Extract [0].nipc
    'buyer_name': 'contracting_authorities',  # Extract [0].name
    'supplier_ids': 'contractors',  # Extract [*].nipc
    'supplier_names': 'contractors',  # Extract [*].name

    # Award information
    'award_amount': ['effective_total_price', 'contract_price'],  # Try effective first
    'award_currency': 'currency',

    # Counts (calculated from arrays)
    'num_lots': None,  # Not available in TED data
    'num_tenderers': 'contractors',  # len(contractors)
    'num_awards': 'contractors',  # len(contractors)

    # Documents
    'document_urls': ['procurement_documents_url', 'source_url'],  # Combine both
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
