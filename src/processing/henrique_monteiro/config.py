"""
Configuration for Henrique & Monteiro processor

Schema mapping from H&M partner data to unified Silver schema.
"""

# Source configuration
SOURCE_NAME = "henrique_monteiro"
SOURCE_DISPLAY_NAME = "Henrique & Monteiro (Partner Data)"

# Paths
INPUT_PATH = "data/bronze/partner_data/henrique&monteiro"
OUTPUT_BASE_PATH = "data/silver/henrique_monteiro"

# Silver layer schema (27 fields)
SILVER_SCHEMA_FIELDS = [
    'tender_id',
    'source',
    'source_country',
    'tender_title',
    'tender_description',
    'tender_status',
    'tender_value_amount',
    'tender_value_currency',
    'publication_date',
    'deadline_date',
    'award_date',
    'contract_start_date',
    'contract_end_date',
    'buyer_id',
    'buyer_name',
    'buyer_type',
    'supplier_id',
    'supplier_name',
    'supplier_country',
    'procurement_method',
    'procurement_category',
    'cpv_code',
    'cpv_description',
    'contract_type',
    'is_framework_agreement',
    'number_of_offers',
    'extraction_date'
]

# Field mappings from H&M to Silver
# Format: 'silver_field': ('hm_table', 'hm_field', default_value)
FIELD_MAPPINGS = {
    'tender_id': ('tenders', 'tender_id', None),
    'source': (None, None, SOURCE_NAME),
    'source_country': (None, None, 'PT'),  # H&M data is from Portugal
    'tender_title': ('tenders', 'tender_title', None),
    'tender_description': ('tenders', 'tender_supplyType', None),  # Use supplyType as description
    'tender_status': ('lots', 'lot_status', None),  # From related lot
    'tender_value_amount': ('tenders', 'tender_estimatedPrice', 0.0),
    'tender_value_currency': (None, None, 'EUR'),
    'publication_date': ('tenders', 'publication_date', None),
    'deadline_date': ('tenders', 'tender_bidDeadline', None),
    'award_date': (None, None, None),
    'contract_start_date': (None, None, None),
    'contract_end_date': (None, None, None),
    'buyer_id': ('buyers', 'buyer_id', None),  # Via relationship
    'buyer_name': ('buyers', 'buyer_name', None),  # Via relationship
    'buyer_type': ('buyers', 'buyer_buyerType', None),  # Via relationship
    'supplier_id': (None, None, None),
    'supplier_name': (None, None, None),
    'supplier_country': (None, None, None),
    'procurement_method': ('tenders', 'tender_procedureType', None),
    'procurement_category': ('tenders', 'main_nature', None),
    'cpv_code': ('tenders', 'tender_mainCpv', None),
    'cpv_description': (None, None, None),
    'contract_type': ('tenders', 'tender_supplyType', None),
    'is_framework_agreement': (None, None, False),
    'number_of_offers': (None, None, None),
    'extraction_date': ('tenders', 'ingestion_timestamp', None)
}

# Data quality rules
REQUIRED_FIELDS = [
    'tender_id',
    'tender_title',
    'publication_date'
]

# Deduplication key
DEDUPLICATION_KEY = 'tender_id'
