"""
Parquet writer for TED Silver layer output.
"""
import logging
from pathlib import Path
from typing import List, Dict, Optional, TYPE_CHECKING
from datetime import datetime
from io import BytesIO

try:
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    PARQUET_AVAILABLE = True
except ImportError:
    PARQUET_AVAILABLE = False
    pd = None
    pa = None
    pq = None

from .config import PARQUET_CONFIG, SILVER_SCHEMA
from .validators import extract_year_month
from src.common import QualityValidator, DeduplicationManager, StateManager

if TYPE_CHECKING:
    from src.storage import MinIOClient

logger = logging.getLogger(__name__)


def get_parquet_schema() -> pa.Schema:
    """
    Get explicit PyArrow schema for Silver layer parquet files.

    This ensures consistent schema across all parquet files, regardless of
    data completeness in individual partitions. Without this, PyArrow infers
    schema from data, causing type inconsistencies (e.g., null vs string).

    Returns:
        PyArrow schema with all field types explicitly defined
    """
    return pa.schema([
        ('publication_date', pa.string()),
        ('tender_start_date', pa.string()),
        ('tender_end_date', pa.string()),
        ('award_date', pa.string()),
        ('tender_value_amount', pa.float64()),
        ('award_amount', pa.float64()),
        ('tender_value_currency', pa.string()),
        ('award_currency', pa.string()),
        ('ocid', pa.string()),
        ('source_country', pa.string()),
        ('source_publication_id', pa.string()),
        ('tender_id', pa.string()),
        ('tender_title', pa.string()),
        ('tender_status', pa.string()),
        ('procurement_method', pa.string()),
        ('procurement_category', pa.string()),
        ('buyer_id', pa.string()),
        ('buyer_name', pa.string()),
        ('record_hash', pa.string()),
        ('source_file', pa.string()),
        ('processing_timestamp', pa.string()),
        ('supplier_ids', pa.list_(pa.string())),
        ('supplier_names', pa.list_(pa.string())),
        ('document_urls', pa.list_(pa.string())),
        ('num_lots', pa.int64()),
        ('num_tenderers', pa.int64()),
        ('num_awards', pa.int64()),
    ])


def check_parquet_dependencies():
    """Check if parquet dependencies are available."""
    if not PARQUET_AVAILABLE:
        raise ImportError(
            "Parquet dependencies not installed. "
            "Install with: pip install pandas pyarrow"
        )


def write_to_parquet(
    records: List[Dict],
    output_dir: str,
    partition_by_date: bool = True,
    storage_client: Optional['MinIOClient'] = None,
    validate_quality: bool = True,
    enable_deduplication: bool = True
) -> Dict[str, int]:
    """
    Write records to Parquet files with partitioning, validation, and deduplication.

    Args:
        records: List of transformed records
        output_dir: Base output directory for Silver layer (used for local fallback)
        partition_by_date: Whether to partition by country/year/month
        storage_client: Optional MinIOClient for object storage
        validate_quality: Whether to run quality validation
        enable_deduplication: Whether to filter duplicate records

    Returns:
        Dictionary with write statistics
    """
    check_parquet_dependencies()

    if not records:
        logger.warning("No records to write")
        return {'files_written': 0, 'records_written': 0}

    # Initialize state manager
    state_manager = StateManager(
        source_name='ted',
        base_dir=output_dir,
        storage_client=storage_client
    )
    processing_state = state_manager.load_processing_state()

    # Quality validation
    quality_report = None
    if validate_quality:
        logger.info("Running quality validation...")
        required_fields = ['ocid', 'publication_date']
        validator = QualityValidator(
            schema=SILVER_SCHEMA,
            required_fields=required_fields
        )
        quality_report = validator.validate_records(records, 'ted')

        logger.info(f"Quality validation complete:")
        logger.info(f"  - Completeness score: {quality_report.completeness_score:.2%}")
        logger.info(f"  - Passed: {quality_report.validation_passed}, Failed: {quality_report.validation_failed}")

        # Save quality report
        QualityValidator.save_quality_report(quality_report, output_dir, storage_client)

        # Check if quality meets minimum standards
        if not quality_report.summary.get('quality_check_passed', True):
            logger.warning("Quality check failed! Review quality report for details.")
            for warning in quality_report.summary.get('warnings', []):
                logger.warning(f"  - {warning}")

    # Deduplication
    dedup_stats = {'duplicates_skipped': 0, 'new_records': len(records)}
    if enable_deduplication:
        logger.info("Running deduplication...")
        dedup_manager = DeduplicationManager()

        # Filter out records we've already written (based on record_hash)
        original_count = len(records)
        records, dedup_stats = dedup_manager.filter_new_records(
            records,
            processing_state.record_hashes_written
        )

        logger.info(f"Deduplication: {dedup_stats['new_records']} new records, {dedup_stats['duplicates_skipped']} duplicates skipped")

        if dedup_stats['new_records'] == 0:
            logger.info("No new records to write after deduplication")
            return {
                'files_written': 0,
                'records_written': 0,
                'duplicates_skipped': dedup_stats['duplicates_skipped'],
                'quality_report': quality_report.to_dict() if quality_report else None
            }

    stats = {'files_written': 0, 'records_written': 0, 'partitions': {}}

    try:
        # Convert to DataFrame
        df = pd.DataFrame(records)

        # Add year and month columns for partitioning
        if partition_by_date and 'publication_date' in df.columns:
            df[['year', 'month']] = df['publication_date'].apply(
                lambda x: pd.Series(extract_year_month(x))
            )
        else:
            df['year'] = 'unknown'
            df['month'] = 'unknown'

        # Group by country for partitioning
        if partition_by_date:
            # Partition by country, year, month
            for (country, year, month), group_df in df.groupby(['source_country', 'year', 'month']):
                # Generate filename with timestamp
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                object_path = f"ted/{country}/{year}/{month}/tenders_{timestamp}.parquet"

                # Drop partition columns before writing (they're in the path)
                write_df = group_df.drop(columns=['year', 'month'])

                # Convert to PyArrow Table with explicit schema
                # This ensures consistent schema across all parquet files
                table = pa.Table.from_pandas(write_df, schema=get_parquet_schema())

                # Convert to bytes
                buffer = BytesIO()
                pq.write_table(
                    table,
                    buffer,
                    compression=PARQUET_CONFIG['compression']
                )
                parquet_bytes = buffer.getvalue()

                # DUAL WRITE: Write to both local and MinIO
                # 1. Always write to local (backup + compatibility)
                _write_parquet_local(parquet_bytes, output_dir, country, year, month, timestamp)

                # 2. Also write to MinIO if client available
                if storage_client:
                    try:
                        storage_client.write_parquet('silver', object_path, parquet_bytes)
                        logger.info(f"Wrote {len(group_df)} records to MinIO: silver/{object_path}")
                    except Exception as e:
                        logger.error(f"Failed to write to MinIO: {e}. Local copy still available.")


                records_in_partition = len(group_df)
                stats['files_written'] += 1
                stats['records_written'] += records_in_partition
                stats['partitions'][f"{country}/{year}/{month}"] = records_in_partition
        else:
            # Write all to single file
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            object_path = f"ted/tenders_{timestamp}.parquet"

            # Drop partition columns
            write_df = df.drop(columns=['year', 'month'], errors='ignore')

            # Convert to PyArrow Table with explicit schema
            # This ensures consistent schema across all parquet files
            table = pa.Table.from_pandas(write_df, schema=get_parquet_schema())

            # Convert to bytes
            buffer = BytesIO()
            pq.write_table(
                table,
                buffer,
                compression=PARQUET_CONFIG['compression']
            )
            parquet_bytes = buffer.getvalue()

            # DUAL WRITE: Write to both local and MinIO
            # 1. Always write to local (backup + compatibility)
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            filename = output_path / f"tenders_{timestamp}.parquet"
            filename.write_bytes(parquet_bytes)
            logger.info(f"Wrote {len(df)} records to local storage: {filename}")

            # 2. Also write to MinIO if client available
            if storage_client:
                try:
                    storage_client.write_parquet('silver', object_path, parquet_bytes)
                    logger.info(f"Wrote {len(df)} records to MinIO: silver/{object_path}")
                except Exception as e:
                    logger.error(f"Failed to write to MinIO: {e}. Local copy still available.")

            stats['files_written'] = 1
            stats['records_written'] = len(df)

        # Update processing state with written record hashes
        if enable_deduplication:
            for record in records:
                record_hash = record.get('record_hash')
                if record_hash:
                    processing_state.record_hashes_written.add(record_hash)

        # Save processing state
        state_manager.save_processing_state(processing_state)

        # Add quality and dedup info to stats
        stats['duplicates_skipped'] = dedup_stats.get('duplicates_skipped', 0)
        if quality_report:
            stats['quality_report'] = quality_report.to_dict()

        return stats

    except Exception as e:
        logger.error(f"Error writing to Parquet: {e}", exc_info=True)
        return {'files_written': 0, 'records_written': 0, 'error': str(e)}


def _write_parquet_local(parquet_bytes: bytes, output_dir: str, country: str, year: str, month: str, timestamp: str) -> None:
    """
    Write Parquet bytes to local filesystem (fallback method).

    Args:
        parquet_bytes: Parquet file bytes
        output_dir: Base output directory
        country: Country code
        year: Year string
        month: Month string
        timestamp: Timestamp string
    """
    partition_path = Path(output_dir) / country / year / month
    partition_path.mkdir(parents=True, exist_ok=True)
    filename = partition_path / f"tenders_{timestamp}.parquet"
    filename.write_bytes(parquet_bytes)
    logger.info(f"Wrote to local storage: {filename}")


def read_parquet(parquet_path: str, limit: int = None) -> List[Dict]:
    """
    Read records from Parquet file.

    Args:
        parquet_path: Path to Parquet file or directory
        limit: Maximum number of records to read

    Returns:
        List of record dictionaries
    """
    check_parquet_dependencies()

    try:
        # Read Parquet file(s)
        df = pd.read_parquet(parquet_path, engine='pyarrow')

        if limit:
            df = df.head(limit)

        # Convert to list of dicts
        records = df.to_dict(orient='records')
        return records

    except Exception as e:
        logger.error(f"Error reading Parquet: {e}", exc_info=True)
        return []


def get_parquet_stats(silver_dir: str) -> Dict:
    """
    Get statistics about Parquet files in Silver layer.

    Args:
        silver_dir: Path to Silver layer directory

    Returns:
        Dictionary with statistics
    """
    check_parquet_dependencies()

    silver_path = Path(silver_dir)
    if not silver_path.exists():
        return {'error': 'Directory does not exist'}

    stats = {
        'total_files': 0,
        'total_records': 0,
        'total_size_mb': 0,
        'countries': {},
    }

    # Find all Parquet files
    parquet_files = list(silver_path.glob('**/*.parquet'))
    stats['total_files'] = len(parquet_files)

    for pq_file in parquet_files:
        try:
            # Read metadata only
            parquet_file = pq.ParquetFile(pq_file)
            num_rows = parquet_file.metadata.num_rows
            stats['total_records'] += num_rows

            # Get file size
            file_size_mb = pq_file.stat().st_size / (1024 * 1024)
            stats['total_size_mb'] += file_size_mb

            # Extract country from path
            parts = pq_file.parts
            try:
                # Assuming path: .../silver/ted/{country}/...
                country_idx = list(parts).index('ted') + 1
                country = parts[country_idx]

                if country not in stats['countries']:
                    stats['countries'][country] = {
                        'files': 0,
                        'records': 0,
                        'size_mb': 0
                    }

                stats['countries'][country]['files'] += 1
                stats['countries'][country]['records'] += num_rows
                stats['countries'][country]['size_mb'] += file_size_mb

            except (ValueError, IndexError):
                pass

        except Exception as e:
            logger.warning(f"Error reading {pq_file}: {e}")
            continue

    stats['total_size_mb'] = round(stats['total_size_mb'], 2)
    for country in stats['countries']:
        stats['countries'][country]['size_mb'] = round(
            stats['countries'][country]['size_mb'], 2
        )

    return stats
