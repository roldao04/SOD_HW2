"""
Core transformation logic for BASE Portugal Bronze to Silver layer.
"""
import json
import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

from .config import COUNTRY_MAPPINGS, DEFAULT_VALUES
from .validators import clean_record, validate_record, extract_year_month

logger = logging.getLogger(__name__)


def get_nested_value(data: dict, path: str) -> Any:
    """
    Extract value from nested dictionary using dot notation path.
    Supports array indexing (e.g., 'awards.0.value')
    and wildcard extraction (e.g., 'awards.*.id')

    Args:
        data: Dictionary to extract from
        path: Dot-notation path (e.g., 'tender.value.amount')

    Returns:
        Extracted value or None
    """
    if not data or not path:
        return None

    keys = path.split('.')
    current = data

    for key in keys:
        if current is None:
            return None

        # Handle array wildcard (e.g., 'suppliers.*.id')
        if key == '*':
            if isinstance(current, list):
                # This is handled by extract_array_values
                return current
            return None

        # Handle array indexing (e.g., 'awards.0')
        if key.isdigit():
            try:
                idx = int(key)
                if isinstance(current, list) and idx < len(current):
                    current = current[idx]
                else:
                    return None
            except (ValueError, TypeError):
                return None
        else:
            # Regular dictionary key
            if isinstance(current, dict):
                current = current.get(key)
            else:
                return None

    return current


def extract_array_values(data: dict, path: str) -> List[Any]:
    """
    Extract array of values using wildcard path.
    Example: 'awards.*.suppliers.*.id' -> list of all supplier IDs

    Args:
        data: Dictionary to extract from
        path: Path with wildcard (*)

    Returns:
        List of extracted values
    """
    if '*' not in path:
        return []

    parts = path.split('.')
    results = []

    def recursive_extract(obj, remaining_parts):
        if not remaining_parts:
            if obj is not None:
                results.append(obj)
            return

        part = remaining_parts[0]
        rest = remaining_parts[1:]

        if part == '*':
            if isinstance(obj, list):
                for item in obj:
                    recursive_extract(item, rest)
            elif isinstance(obj, dict):
                for value in obj.values():
                    recursive_extract(value, rest)
        else:
            if isinstance(obj, dict) and part in obj:
                recursive_extract(obj[part], rest)
            elif part.isdigit() and isinstance(obj, list):
                idx = int(part)
                if idx < len(obj):
                    recursive_extract(obj[idx], rest)

    recursive_extract(data, parts)
    return results


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
    bronze_record: dict,
    source_country: str,
    source_file: str,
    source_publication_id: str = ''
) -> Optional[Dict]:
    """
    Transform a single OCDS record from Bronze to Silver schema.

    Args:
        bronze_record: Raw OCDS record from Bronze layer
        source_country: Country code
        source_file: Path to source Bronze file
        source_publication_id: Publication ID

    Returns:
        Transformed record dictionary or None if transformation fails
    """
    try:
        # Get country-specific field mappings
        field_mappings = COUNTRY_MAPPINGS.get(source_country.lower())
        if not field_mappings:
            logger.error(f"No field mappings for country: {source_country}")
            return None

        # Initialize transformed record
        transformed = {}

        # Extract scalar fields
        for silver_field, bronze_paths in field_mappings.items():
            if isinstance(bronze_paths, str):
                bronze_paths = [bronze_paths]

            value = None
            for path in bronze_paths:
                if '*' in path:
                    # Handle array extraction
                    values = extract_array_values(bronze_record, path)
                    if values:
                        value = values
                        break
                else:
                    # Handle scalar extraction
                    value = get_nested_value(bronze_record, path)
                    if value is not None:
                        break

            # Handle special cases
            if silver_field in ['num_lots', 'num_tenderers', 'num_awards']:
                # Count array length
                if isinstance(value, list):
                    value = len(value)
                else:
                    value = 0

            # Set value with default if None
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

        # Add metadata fields
        transformed['source_country'] = source_country
        transformed['source_publication_id'] = source_publication_id
        transformed['source_file'] = source_file
        transformed['processing_timestamp'] = datetime.utcnow().isoformat() + 'Z'

        # Calculate num_awards from awards array if not already set
        if transformed.get('num_awards', 0) == 0:
            if 'awards' in bronze_record:
                transformed['num_awards'] = len(bronze_record['awards'])
            elif 'award' in bronze_record:
                transformed['num_awards'] = len(bronze_record['award']) if isinstance(bronze_record['award'], list) else 1

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
        logger.error(f"Error transforming record: {e}", exc_info=True)
        return None


def process_bronze_file(
    bronze_file_path: str,
    source_country: str = None,
    source_publication_id: str = ''
) -> List[Dict]:
    """
    Process a single Bronze layer JSON file.

    Args:
        bronze_file_path: Path to Bronze JSON file
        source_country: Country code (auto-detected from path if not provided)
        source_publication_id: Publication ID

    Returns:
        List of transformed records
    """
    bronze_path = Path(bronze_file_path)

    if not bronze_path.exists():
        logger.error(f"Bronze file not found: {bronze_file_path}")
        return []

    # Auto-detect country from path if not provided
    if not source_country:
        try:
            # Path format: .../bronze/base_portugal/{country}/{year}/{month}/{day}/...
            parts = bronze_path.parts
            base_portugal_idx = parts.index('base_portugal') + 1
            source_country = parts[base_portugal_idx]
        except (ValueError, IndexError):
            logger.error(f"Could not determine country from path: {bronze_file_path}")
            return []

    try:
        with open(bronze_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        records = data.get('records', [])
        if not records:
            logger.warning(f"No records found in file: {bronze_file_path}")
            return []

        transformed_records = []
        for record in records:
            transformed = transform_record(
                record,
                source_country,
                str(bronze_file_path),
                source_publication_id
            )
            if transformed:
                transformed_records.append(transformed)

        logger.info(f"Transformed {len(transformed_records)}/{len(records)} records from {bronze_file_path}")
        return transformed_records

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in file {bronze_file_path}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error processing file {bronze_file_path}: {e}", exc_info=True)
        return []


def process_bronze_directory(bronze_dir: str, country: str = None) -> List[Dict]:
    """
    Process all Bronze JSON files in a directory (recursively).

    Args:
        bronze_dir: Path to Bronze directory
        country: Country code to filter (optional)

    Returns:
        List of all transformed records
    """
    bronze_path = Path(bronze_dir)

    if not bronze_path.exists():
        logger.error(f"Bronze directory not found: {bronze_dir}")
        return []

    # Find all JSON files
    if country:
        pattern = f"{country}/**/records_*.json"
    else:
        pattern = "**/records_*.json"

    json_files = list(bronze_path.glob(pattern))
    logger.info(f"Found {len(json_files)} Bronze files to process")

    all_transformed = []
    for json_file in json_files:
        transformed = process_bronze_file(str(json_file), country)
        all_transformed.extend(transformed)

    logger.info(f"Total transformed records: {len(all_transformed)}")
    return all_transformed
