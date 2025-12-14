"""
Parquet writer for Silver layer output.
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

from .config import PARQUET_CONFIG
from .validators import extract_year_month

if TYPE_CHECKING:
    from src.storage import MinIOClient

logger = logging.getLogger(__name__)


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
    storage_client: Optional['MinIOClient'] = None
) -> Dict[str, int]:
    """
    Write records to Parquet files with partitioning.

    Args:
        records: List of transformed records
        output_dir: Base output directory for Silver layer (used for local fallback)
        partition_by_date: Whether to partition by country/year/month
        storage_client: Optional MinIOClient for object storage

    Returns:
        Dictionary with write statistics
    """
    check_parquet_dependencies()

    if not records:
        logger.warning("No records to write")
        return {'files_written': 0, 'records_written': 0}

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
                object_path = f"open_contracting_partnership/{country}/{year}/{month}/tenders_{timestamp}.parquet"

                # Drop partition columns before writing (they're in the path)
                write_df = group_df.drop(columns=['year', 'month'])

                # Convert to bytes
                buffer = BytesIO()
                write_df.to_parquet(
                    buffer,
                    engine='pyarrow',
                    compression=PARQUET_CONFIG['compression'],
                    index=False
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
            object_path = f"open_contracting_partnership/tenders_{timestamp}.parquet"

            # Drop partition columns
            write_df = df.drop(columns=['year', 'month'], errors='ignore')

            # Convert to bytes
            buffer = BytesIO()
            write_df.to_parquet(
                buffer,
                engine='pyarrow',
                compression=PARQUET_CONFIG['compression'],
                index=False
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
                # Assuming path: .../silver/open_contracting_partnership/{country}/...
                country_idx = parts.index('open_contracting_partnership') + 1
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
