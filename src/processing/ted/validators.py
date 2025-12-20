"""
Data validation and cleaning utilities for TED records.
"""
import re
from datetime import datetime
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


def clean_date(date_value: Any) -> Optional[str]:
    """
    Clean and normalize date to ISO format (YYYY-MM-DD).
    Removes timezone information.

    Args:
        date_value: Date string or datetime object

    Returns:
        ISO formatted date string or None
    """
    if not date_value:
        return None

    if isinstance(date_value, datetime):
        return date_value.strftime('%Y-%m-%d')

    if not isinstance(date_value, str):
        return None

    # Fix Italy's malformed dates: "2025-07-14 16:31:02.112T12:00:00Z"
    # Pattern has space instead of T, and weird .###T##:##:## duplicate time
    if ' ' in date_value and 'T' in date_value:
        # Replace space with T and remove duplicate time after milliseconds
        date_value = re.sub(r' (\d{2}:\d{2}:\d{2}\.\d+)T\d{2}:\d{2}:\d{2}', r'T\1', date_value)

    # Remove timezone info (e.g., +01:00, Z, +00:00)
    clean_str = re.sub(r'[+-]\d{2}:\d{2}$', '', date_value)
    clean_str = clean_str.replace('Z', '')

    # Try to parse common formats
    formats = [
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d',
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(clean_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue

    logger.warning(f"Could not parse date: {date_value}")
    return None


def clean_amount(amount_value: Any) -> float:
    """
    Clean and validate monetary amount.

    Args:
        amount_value: Amount value (float, int, or string)

    Returns:
        Float value, 0.0 if invalid
    """
    if amount_value is None:
        return 0.0

    try:
        return float(amount_value)
    except (ValueError, TypeError):
        logger.warning(f"Could not parse amount: {amount_value}")
        return 0.0


def clean_currency(currency_value: Any) -> str:
    """
    Clean and validate currency code.

    Args:
        currency_value: Currency code string

    Returns:
        Uppercase 3-letter currency code or empty string
    """
    if not currency_value:
        return ''

    if isinstance(currency_value, str):
        currency = currency_value.upper().strip()
        # Basic validation: 3 letters
        if len(currency) == 3 and currency.isalpha():
            return currency

    return ''


def clean_string(value: Any) -> str:
    """
    Clean string value.

    Args:
        value: Any value to convert to string

    Returns:
        Cleaned string or empty string
    """
    if value is None:
        return ''

    if isinstance(value, str):
        # Remove excessive whitespace
        return ' '.join(value.split())

    return str(value)


def clean_id(id_value: Any) -> str:
    """
    Clean and validate ID field.

    Args:
        id_value: ID value

    Returns:
        String ID or empty string
    """
    if not id_value:
        return ''

    return str(id_value).strip()


def validate_ocid(ocid: str) -> bool:
    """
    Validate OCID format.
    Should start with 'ocds-' prefix.

    Args:
        ocid: OCID string

    Returns:
        True if valid format
    """
    if not ocid:
        return False

    return isinstance(ocid, str) and ocid.startswith('ocds-')


def clean_array(arr: Any) -> list:
    """
    Clean array/list value.

    Args:
        arr: Array value

    Returns:
        List or empty list
    """
    if arr is None:
        return []

    if isinstance(arr, list):
        return arr

    # Single value -> make it a list
    return [arr]


def extract_year_month(date_str: Optional[str]) -> tuple:
    """
    Extract year and month from ISO date string.

    Args:
        date_str: ISO formatted date (YYYY-MM-DD)

    Returns:
        Tuple of (year, month) as strings, or ('unknown', 'unknown')
    """
    if not date_str or not isinstance(date_str, str):
        return ('unknown', 'unknown')

    try:
        parts = date_str.split('-')
        if len(parts) >= 2:
            return (parts[0], parts[1])
    except:
        pass

    return ('unknown', 'unknown')


def validate_record(record: dict) -> bool:
    """
    Validate if a record has minimum required fields.

    Args:
        record: Transformed record dictionary

    Returns:
        True if record is valid
    """
    required_fields = ['ocid', 'publication_date']

    for field in required_fields:
        if field not in record or not record[field]:
            logger.warning(f"Record missing required field: {field}")
            return False

    # Validate OCID format
    if not validate_ocid(record['ocid']):
        logger.warning(f"Invalid OCID format: {record['ocid']}")
        return False

    return True


def clean_record(record: dict) -> dict:
    """
    Apply all cleaning operations to a record.

    Args:
        record: Record dictionary with raw values

    Returns:
        Cleaned record dictionary
    """
    cleaned = {}

    # Clean date fields
    date_fields = ['publication_date', 'tender_start_date', 'tender_end_date', 'award_date']
    for field in date_fields:
        if field in record:
            cleaned[field] = clean_date(record[field])
        else:
            cleaned[field] = None

    # Clean amount fields
    amount_fields = ['tender_value_amount', 'award_amount']
    for field in amount_fields:
        if field in record:
            cleaned[field] = clean_amount(record[field])
        else:
            cleaned[field] = 0.0

    # Clean currency fields
    currency_fields = ['tender_value_currency', 'award_currency']
    for field in currency_fields:
        if field in record:
            cleaned[field] = clean_currency(record[field])
        else:
            cleaned[field] = ''

    # Clean string fields
    string_fields = [
        'ocid', 'source_country', 'source_publication_id', 'tender_id',
        'tender_title', 'tender_status', 'procurement_method',
        'procurement_category', 'buyer_id', 'buyer_name', 'record_hash',
        'source_file', 'processing_timestamp'
    ]
    for field in string_fields:
        if field in record:
            cleaned[field] = clean_string(record[field])
        else:
            cleaned[field] = ''

    # Clean array fields
    array_fields = ['supplier_ids', 'supplier_names', 'document_urls']
    for field in array_fields:
        if field in record:
            cleaned[field] = clean_array(record[field])
        else:
            cleaned[field] = []

    # Clean integer fields
    int_fields = ['num_lots', 'num_tenderers', 'num_awards']
    for field in int_fields:
        if field in record:
            try:
                cleaned[field] = int(record[field]) if record[field] else 0
            except (ValueError, TypeError):
                cleaned[field] = 0
        else:
            cleaned[field] = 0

    return cleaned
