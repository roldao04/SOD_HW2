"""
Utility functions for BASE Portugal extractor.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple, TYPE_CHECKING
import logging

from .config import LICENSE_INFO

if TYPE_CHECKING:
    from src.storage import MinIOClient

logger = logging.getLogger(__name__)


def parse_ocds_date(date_string: str) -> Optional[datetime]:
    """
    Parse OCDS date string to datetime object.
    OCDS dates are typically in ISO 8601 format.

    Args:
        date_string: Date string from OCDS data

    Returns:
        datetime object or None if parsing fails
    """
    if not date_string:
        return None

    import re

    # Remove timezone info for simpler parsing
    # Handle patterns like +01:00, +00:00, -05:00, Z
    clean_date = re.sub(r'[+-]\d{2}:\d{2}$', '', date_string)
    clean_date = clean_date.replace('Z', '')

    # Common OCDS date formats
    formats = [
        "%Y-%m-%dT%H:%M:%S.%f",  # 2025-01-15T10:30:00.123
        "%Y-%m-%dT%H:%M:%S",     # 2025-01-15T10:30:00
        "%Y-%m-%d",              # 2025-01-15
    ]

    for fmt in formats:
        try:
            return datetime.strptime(clean_date, fmt)
        except ValueError:
            continue

    logger.warning(f"Could not parse date: {date_string}")
    return None


def extract_publication_date(ocds_record: Dict) -> Optional[datetime]:
    """
    Extract the publication date from an OCDS record.
    Checks multiple possible fields in order of preference.

    Args:
        ocds_record: OCDS record dictionary

    Returns:
        datetime object or None if no date found
    """
    # Priority order for date fields
    date_fields = [
        'date',  # Release date
        'publishedDate',
        'tender.tenderPeriod.startDate',
        'tender.datePublished',
    ]

    for field in date_fields:
        # Handle nested fields
        value = ocds_record
        for key in field.split('.'):
            if isinstance(value, dict):
                value = value.get(key)
            else:
                value = None
                break

        if value:
            date_obj = parse_ocds_date(value)
            if date_obj:
                return date_obj

    return None


def get_bronze_path(base_dir: str, country: str, date: datetime) -> Path:
    """
    Generate Bronze layer path following the structure:
    /data/bronze/base_portugal/{country}/{YYYY}/{MM}/{DD}/

    Args:
        base_dir: Base data directory
        country: Country code
        date: Publication date

    Returns:
        Path object for the Bronze layer directory
    """
    path = Path(base_dir) / "bronze" / "base_portugal" / country / \
           f"{date.year:04d}" / f"{date.month:02d}" / f"{date.day:02d}"

    return path


def ensure_directory(path: Path) -> None:
    """
    Create directory if it doesn't exist.

    Args:
        path: Directory path to create
    """
    path.mkdir(parents=True, exist_ok=True)


def add_license_metadata(data: Dict) -> Dict:
    """
    Add license and attribution metadata to the data.

    Args:
        data: Data dictionary to add metadata to

    Returns:
        Data dictionary with metadata added
    """
    data['_metadata'] = {
        'license': LICENSE_INFO['name'],
        'license_full_name': LICENSE_INFO['full_name'],
        'license_url': LICENSE_INFO['url'],
        'attribution': LICENSE_INFO['attribution'],
        'source_url': LICENSE_INFO['source_url'],
        'portal': LICENSE_INFO['portal'],
        'restrictions': LICENSE_INFO['restrictions'],
        'extraction_timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    return data


def save_records_to_bronze(
    records: list,
    country: str,
    base_dir: str,
    storage_client: Optional['MinIOClient'] = None
) -> Tuple[int, Dict[str, int]]:
    """
    Save OCDS records to Bronze layer, organized by publication date.

    Args:
        records: List of OCDS records
        country: Country code
        base_dir: Base data directory (used for local storage fallback)
        storage_client: Optional MinIOClient for object storage

    Returns:
        Tuple of (total_saved, date_counts_dict)
    """
    total_saved = 0
    date_counts = {}
    records_by_date = {}

    # Group records by publication date
    for record in records:
        pub_date = extract_publication_date(record)

        if not pub_date:
            logger.warning(f"Skipping record without valid date: {record.get('ocid', 'unknown')}")
            continue

        date_key = pub_date.strftime("%Y-%m-%d")
        if date_key not in records_by_date:
            records_by_date[date_key] = []

        records_by_date[date_key].append(record)

    # Save records grouped by date
    for date_key, date_records in records_by_date.items():
        pub_date = datetime.strptime(date_key, "%Y-%m-%d")
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        # Prepare data with metadata
        data = {
            'records': date_records,
            'count': len(date_records),
            'publication_date': date_key,
            'country': country
        }
        data = add_license_metadata(data)

        # Create object path: base_portugal/{country}/{YYYY}/{MM}/{DD}/records_{timestamp}.json
        object_path = f"base_portugal/{country}/{pub_date.year:04d}/{pub_date.month:02d}/{pub_date.day:02d}/records_{timestamp}.json"

        # DUAL WRITE: Always write to local storage (for backward compatibility and backup)
        _save_to_local(data, base_dir, country, pub_date, timestamp)

        # Also write to MinIO if available
        if storage_client:
            try:
                storage_client.write_json('bronze', object_path, data)
                logger.info(f"Saved {len(date_records)} records to MinIO: bronze/{object_path}")
            except Exception as e:
                logger.error(f"Failed to save to MinIO: {e}. Local copy still available.")

        total_saved += len(date_records)
        date_counts[date_key] = len(date_records)

    return total_saved, date_counts


def _save_to_local(data: Dict, base_dir: str, country: str, pub_date: datetime, timestamp: str) -> None:
    """
    Save data to local filesystem (fallback method).

    Args:
        data: Data to save
        base_dir: Base data directory
        country: Country code
        pub_date: Publication date
        timestamp: Timestamp string
    """
    bronze_path = get_bronze_path(base_dir, country, pub_date)
    ensure_directory(bronze_path)

    filename = bronze_path / f"records_{timestamp}.json"

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved {data['count']} records to local storage: {filename}")


def filter_records_by_year(records: list, year: int = 2025) -> list:
    """
    Filter OCDS records to only include those from a specific year.

    Args:
        records: List of OCDS records
        year: Year to filter for

    Returns:
        Filtered list of records
    """
    filtered = []

    for record in records:
        pub_date = extract_publication_date(record)
        if pub_date and pub_date.year == year:
            filtered.append(record)

    return filtered
