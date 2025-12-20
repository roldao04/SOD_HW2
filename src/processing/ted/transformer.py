"""
Core transformation logic for TED (Tenders Electronic Daily) Bronze to Silver layer.
"""
import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

try:
    import pandas as pd
    import pyarrow.parquet as pq
    import numpy as np
    PARQUET_AVAILABLE = True
except ImportError:
    PARQUET_AVAILABLE = False
    pd = None
    pq = None
    np = None

from .config import COUNTRY_CODE_MAPPING, TED_FIELD_MAPPINGS, DEFAULT_VALUES
from .validators import clean_record, validate_record, extract_year_month
from src.common import StateManager
from src.storage import MinIOClient

logger = logging.getLogger(__name__)


def check_parquet_dependencies():
    """Check if parquet dependencies are available."""
    if not PARQUET_AVAILABLE:
        raise ImportError(
            "Parquet dependencies not installed. "
            "Install with: pip install pandas pyarrow"
        )


def get_value_from_ted_field(record: dict, ted_field: Any) -> Any:
    """
    Extract value from TED record based on field mapping.

    Args:
        record: TED record dictionary
        ted_field: Field name or list of field names to try

    Returns:
        Extracted value or None
    """
    if ted_field is None:
        return None

    if isinstance(ted_field, list):
        # Try multiple fields in order
        for field in ted_field:
            value = record.get(field)
            if value is not None:
                return value
        return None
    else:
        # Single field
        return record.get(ted_field)


def extract_country_code(record: dict) -> str:
    """
    Extract and normalize country code from TED record.

    TED uses ISO 3166-1 alpha-3 codes (DEU, FRA, etc.) which we map
    to lowercase country names (germany, france, etc.).

    Args:
        record: TED record dictionary

    Returns:
        Normalized country code or 'unknown'
    """
    # Try contracting_authorities first
    authorities = record.get('contracting_authorities', [])
    if authorities and isinstance(authorities, list) and len(authorities) > 0:
        country_code = authorities[0].get('country')
        if country_code:
            # Map ISO alpha-3 to lowercase name
            return COUNTRY_CODE_MAPPING.get(country_code, country_code.lower())

    # Try execution_location as fallback
    exec_location = record.get('execution_location')
    if exec_location:
        # execution_location might be like "PT-11" (Portugal-region)
        country_part = exec_location.split('-')[0]
        # Try to map from alpha-2 or alpha-3
        for code, name in COUNTRY_CODE_MAPPING.items():
            if code.startswith(country_part) or country_part == code[:2]:
                return name

    return 'unknown'


def extract_buyer_info(record: dict) -> tuple:
    """
    Extract buyer ID and name from contracting_authorities array.

    Args:
        record: TED record dictionary

    Returns:
        Tuple of (buyer_id, buyer_name)
    """
    authorities = record.get('contracting_authorities', [])

    # Convert numpy array to list if needed
    if isinstance(authorities, np.ndarray):
        authorities = authorities.tolist()

    if authorities and isinstance(authorities, list) and len(authorities) > 0:
        first_auth = authorities[0]
        buyer_id = first_auth.get('nipc', '')
        buyer_name = first_auth.get('name', '')
        return buyer_id, buyer_name

    return '', ''


def extract_supplier_info(record: dict) -> tuple:
    """
    Extract supplier IDs and names from contractors array.

    Args:
        record: TED record dictionary

    Returns:
        Tuple of (supplier_ids: List[str], supplier_names: List[str])
    """
    contractors = record.get('contractors', [])

    # Convert numpy array to list if needed
    if isinstance(contractors, np.ndarray):
        contractors = contractors.tolist()

    if not contractors or not isinstance(contractors, list):
        return [], []

    supplier_ids = []
    supplier_names = []

    for contractor in contractors:
        if isinstance(contractor, dict):
            nipc = contractor.get('nipc', '')
            name = contractor.get('name', '')
            if nipc:
                supplier_ids.append(str(nipc))
            if name:
                supplier_names.append(str(name))

    return supplier_ids, supplier_names


def extract_document_urls(record: dict) -> List[str]:
    """
    Extract document URLs from TED record.

    Combines procurement_documents_url and source_url if available.

    Args:
        record: TED record dictionary

    Returns:
        List of document URLs
    """
    urls = []

    doc_url = record.get('procurement_documents_url')
    if doc_url:
        urls.append(str(doc_url))

    source_url = record.get('source_url')
    if source_url:
        urls.append(str(source_url))

    return urls


def extract_procurement_category(record: dict) -> str:
    """
    Extract first contract type from contract_types array.

    Args:
        record: TED record dictionary

    Returns:
        First contract type or empty string
    """
    contract_types = record.get('contract_types', [])

    # Convert numpy array to list if needed
    if isinstance(contract_types, np.ndarray):
        contract_types = contract_types.tolist()

    if contract_types and isinstance(contract_types, list) and len(contract_types) > 0:
        return str(contract_types[0])

    return ''


def compute_record_hash(record: dict) -> str:
    """
    Compute MD5 hash of key fields for deduplication.

    Args:
        record: Transformed record

    Returns:
        MD5 hash string
    """
    key_fields = [
        record.get('ocid', ''),
        record.get('tender_id', ''),
        record.get('publication_date', ''),
        record.get('buyer_name', ''),
    ]

    hash_input = '|'.join(str(f) for f in key_fields)
    return hashlib.md5(hash_input.encode()).hexdigest()


def transform_record(
    ted_record: dict,
    source_file: str
) -> Optional[Dict]:
    """
    Transform a single TED record from Bronze to Silver schema.

    Args:
        ted_record: Raw TED record from Bronze parquet
        source_file: Path to source Bronze file

    Returns:
        Transformed record dictionary or None if transformation fails
    """
    try:
        # Extract country code
        source_country = extract_country_code(ted_record)

        # Initialize transformed record
        transformed = {}

        # Extract fields using TED mappings
        for silver_field, ted_field in TED_FIELD_MAPPINGS.items():
            # Handle special fields
            if silver_field == 'buyer_id' or silver_field == 'buyer_name':
                buyer_id, buyer_name = extract_buyer_info(ted_record)
                transformed['buyer_id'] = buyer_id
                transformed['buyer_name'] = buyer_name
                continue

            elif silver_field == 'supplier_ids' or silver_field == 'supplier_names':
                supplier_ids, supplier_names = extract_supplier_info(ted_record)
                transformed['supplier_ids'] = supplier_ids
                transformed['supplier_names'] = supplier_names
                continue

            elif silver_field == 'document_urls':
                transformed['document_urls'] = extract_document_urls(ted_record)
                continue

            elif silver_field == 'procurement_category':
                transformed['procurement_category'] = extract_procurement_category(ted_record)
                continue

            elif silver_field == 'num_lots':
                # Not available in TED data
                transformed['num_lots'] = 0
                continue

            elif silver_field == 'num_tenderers':
                # Count contractors
                contractors = ted_record.get('contractors', [])
                transformed['num_tenderers'] = len(contractors) if isinstance(contractors, list) else 0
                continue

            elif silver_field == 'num_awards':
                # Count contractors (same as num_tenderers in TED)
                contractors = ted_record.get('contractors', [])
                transformed['num_awards'] = len(contractors) if isinstance(contractors, list) else 0
                continue

            # Extract regular fields
            value = get_value_from_ted_field(ted_record, ted_field)

            # Apply defaults if value is None
            if value is None:
                field_type = 'string'  # Default
                if silver_field.endswith('_amount'):
                    field_type = 'float'
                elif silver_field.startswith('num_'):
                    field_type = 'int'
                elif silver_field.endswith('_ids') or silver_field.endswith('_names') or silver_field == 'document_urls':
                    field_type = 'list[string]'
                value = DEFAULT_VALUES.get(field_type, '')

            transformed[silver_field] = value

        # Generate OCID (Open Contracting ID)
        source_id = ted_record.get('source_id', '')
        transformed['ocid'] = f"ocds-ted-{source_id}"

        # Add metadata fields
        transformed['source_country'] = source_country
        transformed['source_file'] = source_file
        transformed['processing_timestamp'] = datetime.utcnow().isoformat() + 'Z'

        # Clean the record
        transformed = clean_record(transformed)

        # Compute record hash
        transformed['record_hash'] = compute_record_hash(transformed)

        # Validate record
        if not validate_record(transformed):
            logger.warning(f"Record validation failed for OCID: {transformed.get('ocid', 'unknown')}")
            return None

        return transformed

    except Exception as e:
        logger.error(f"Error transforming TED record: {e}", exc_info=True)
        return None


def process_bronze_file(
    bronze_file_path: str,
    storage_client: Optional[MinIOClient] = None,
    is_s3_path: bool = False
) -> List[Dict]:
    """
    Process a single Bronze layer Parquet file containing TED data.

    Args:
        bronze_file_path: Path to Bronze Parquet file (local or S3 object path)
        storage_client: Optional MinIOClient for reading from object storage
        is_s3_path: Whether bronze_file_path is an S3 object path

    Returns:
        List of transformed records
    """
    check_parquet_dependencies()

    try:
        # Read parquet data from storage
        if is_s3_path and storage_client:
            parquet_bytes = storage_client.read_parquet('bronze', bronze_file_path)
            from io import BytesIO
            df = pd.read_parquet(BytesIO(parquet_bytes))
        else:
            # Local file
            bronze_path = Path(bronze_file_path)
            if not bronze_path.exists():
                logger.error(f"Bronze file not found: {bronze_file_path}")
                return []
            df = pd.read_parquet(bronze_path)

        # Convert DataFrame to list of dicts
        records = df.to_dict(orient='records')

        if not records:
            logger.warning(f"No records found in file: {bronze_file_path}")
            return []

        transformed_records = []
        for record in records:
            transformed = transform_record(record, str(bronze_file_path))
            if transformed:
                transformed_records.append(transformed)

        logger.info(f"Transformed {len(transformed_records)}/{len(records)} TED records from {bronze_file_path}")
        return transformed_records

    except Exception as e:
        logger.error(f"Error processing TED file {bronze_file_path}: {e}", exc_info=True)
        return []


def process_bronze_directory(
    bronze_dir: str,
    storage_client: Optional[MinIOClient] = None,
    incremental: bool = True
) -> List[Dict]:
    """
    Process all TED Bronze Parquet files in partner_data directory.

    Args:
        bronze_dir: Path to Bronze directory (local fallback)
        storage_client: Optional MinIOClient for reading from object storage
        incremental: Whether to use incremental processing (skip already processed files)

    Returns:
        List of all transformed records
    """
    all_transformed = []

    # Initialize state manager for incremental processing
    state_manager = None
    processing_state = None
    if incremental:
        state_manager = StateManager(
            source_name='ted',
            base_dir=bronze_dir,
            storage_client=storage_client
        )
        processing_state = state_manager.load_processing_state()
        logger.info(f"Loaded processing state: {processing_state.total_files_processed} files already processed")

    # Try MinIO first, fallback to local
    parquet_files = []
    use_s3_path = False

    if storage_client:
        # Try MinIO storage
        try:
            # List all Parquet files in TED partner data
            prefix = "partner_data/andré/"

            parquet_files = storage_client.list_objects('bronze', prefix)
            parquet_files = [f for f in parquet_files if f.endswith('.parquet') and not f.endswith('_state.parquet')]
            use_s3_path = True
            logger.info(f"Found {len(parquet_files)} TED Bronze files in MinIO")

        except Exception as e:
            logger.warning(f"Failed to read from MinIO: {e}. Falling back to local storage")
            storage_client = None  # Disable for this run

    if not parquet_files:
        # Fallback to local filesystem
        bronze_path = Path(bronze_dir) / "partner_data" / "andré"

        if not bronze_path.exists():
            logger.error(f"Bronze directory not found: {bronze_path}")
            return []

        # Find all Parquet files
        parquet_files = [str(f) for f in bronze_path.glob("*.parquet")]
        use_s3_path = False
        logger.info(f"Found {len(parquet_files)} TED Bronze files in local storage")

    # Process files
    files_processed = 0
    files_skipped = 0

    for parquet_file in parquet_files:
        # Check if already processed (incremental mode)
        if incremental and processing_state and state_manager:
            if state_manager.should_process_file(parquet_file, processing_state):
                # Process the file
                transformed = process_bronze_file(
                    str(parquet_file),
                    storage_client=storage_client,
                    is_s3_path=use_s3_path
                )
                all_transformed.extend(transformed)
                files_processed += 1

                # Update state
                processing_state.processed_bronze_files.append(parquet_file)
            else:
                files_skipped += 1
                logger.debug(f"Skipping already processed file: {parquet_file}")
        else:
            # Process without state tracking
            transformed = process_bronze_file(
                str(parquet_file),
                storage_client=storage_client,
                is_s3_path=use_s3_path
            )
            all_transformed.extend(transformed)
            files_processed += 1

    logger.info(f"Processed {files_processed} files, skipped {files_skipped} (already processed)")
    logger.info(f"Total transformed TED records: {len(all_transformed)}")

    # Save processing state (will be completed after writing to Silver)
    if incremental and processing_state and state_manager:
        processing_state.total_files_processed += files_processed
        processing_state.total_records_processed += len(all_transformed)
        # Don't save yet - will save after Silver write in parquet_writer

    return all_transformed
