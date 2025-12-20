#!/usr/bin/env python3
"""
CLI for TED (Tenders Electronic Daily) Silver layer processing.
"""
import sys
import logging
import argparse
from pathlib import Path
from typing import Optional

from .transformer import process_bronze_directory
from .parquet_writer import write_to_parquet, get_parquet_stats

# Import storage client for MinIO
try:
    from src.storage import MinIOClient, StorageConfig
    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False
    MinIOClient = None
    StorageConfig = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default paths - will be auto-detected from project structure
def get_default_paths():
    """Get default Bronze and Silver directory paths."""
    # Get project root (4 levels up from this file)
    project_root = Path(__file__).parent.parent.parent.parent
    data_dir = project_root / "data"

    bronze_dir = str(data_dir / "bronze")
    silver_dir = str(data_dir / "silver" / "ted")

    return bronze_dir, silver_dir

DEFAULT_BRONZE_DIR, DEFAULT_SILVER_DIR = get_default_paths()


def get_storage_client() -> Optional['MinIOClient']:
    """
    Initialize MinIO storage client if available.

    Returns:
        MinIOClient instance or None if unavailable/disabled
    """
    if not MINIO_AVAILABLE:
        logger.info("MinIO not available - using local storage only")
        return None

    try:
        client = MinIOClient(StorageConfig.from_env())
        logger.info("✓ MinIO client initialized - dual write enabled (local + MinIO)")
        return client
    except Exception as e:
        logger.warning(f"Failed to initialize MinIO: {e}. Using local storage only.")
        return None


def process_ted_data(bronze_dir: str, silver_dir: str):
    """Process TED partner data from Bronze to Silver layer."""
    print(f"\n{'='*60}")
    print(" TED (Tenders Electronic Daily) - Silver Layer Processing")
    print("="*60)

    print("\nChecking for TED Bronze data (MinIO + local)...")

    try:
        # Get storage client
        storage_client = get_storage_client()

        # Transform records (checks both MinIO and local storage)
        transformed_records = process_bronze_directory(
            bronze_dir,
            storage_client=storage_client,
            incremental=True
        )

        if not transformed_records:
            print("\n✗ No records were successfully transformed")
            return

        print(f"✓ Transformed {len(transformed_records)} records")

        # Write to Parquet (dual write: local + MinIO)
        print("\nWriting to Silver layer...")
        stats = write_to_parquet(
            transformed_records,
            silver_dir,
            partition_by_date=True,
            storage_client=storage_client,
            validate_quality=True,
            enable_deduplication=True
        )

        # Display results
        print(f"\n{'='*60}")
        print(" PROCESSING RESULTS")
        print("="*60)
        print(f"Files written: {stats['files_written']}")
        print(f"Records written: {stats['records_written']}")

        if stats.get('duplicates_skipped', 0) > 0:
            print(f"Duplicates skipped: {stats['duplicates_skipped']}")

        if stats.get('partitions'):
            print("\nPartitions:")
            for partition, count in sorted(stats['partitions'].items()):
                print(f"  {partition}: {count} records")

        # Quality report summary
        if stats.get('quality_report'):
            qr = stats['quality_report']
            print(f"\nQuality Report:")
            print(f"  Completeness: {qr.get('completeness_score', 0):.2%}")
            print(f"  Validation passed: {qr.get('validation_passed', 0)}")
            print(f"  Validation failed: {qr.get('validation_failed', 0)}")

        print("="*60)

    except Exception as e:
        logger.error(f"Error processing TED data: {e}", exc_info=True)
        print(f"\n✗ Error: {e}")


def show_statistics(silver_dir: str):
    """Show Silver layer statistics."""
    print(f"\n{'='*60}")
    print(" TED Silver Layer Statistics")
    print("="*60)

    silver_path = Path(silver_dir)
    if not silver_path.exists():
        print("\nSilver layer directory does not exist yet.")
        print("Process some data first to generate the Silver layer.")
        return

    print("\nAnalyzing...")

    try:
        stats = get_parquet_stats(silver_dir)

        if stats.get('error'):
            print(f"\n✗ Error: {stats['error']}")
            return

        print(f"\nTotal files: {stats['total_files']}")
        print(f"Total records: {stats['total_records']:,}")
        print(f"Total size: {stats['total_size_mb']:.2f} MB")

        if stats.get('countries'):
            print(f"\nCountries: {len(stats['countries'])}")
            print("\nTop 10 Countries by Records:")
            sorted_countries = sorted(
                stats['countries'].items(),
                key=lambda x: x[1]['records'],
                reverse=True
            )[:10]

            for country, country_stats in sorted_countries:
                print(f"  {country.upper()}:")
                print(f"    Files: {country_stats['files']}")
                print(f"    Records: {country_stats['records']:,}")
                print(f"    Size: {country_stats['size_mb']:.2f} MB")

    except Exception as e:
        logger.error(f"Error getting statistics: {e}", exc_info=True)
        print(f"\n✗ Error: {e}")


def validate_bronze(bronze_dir: str):
    """Validate Bronze layer structure and data."""
    print(f"\n{'='*60}")
    print(" TED Bronze Layer Validation")
    print("="*60)

    partner_path = Path(bronze_dir) / "partner_data" / "andré&abel"
    if not partner_path.exists():
        print(f"\n✗ TED partner data directory not found: {partner_path}")
        return

    print(f"\nScanning TED Bronze layer: {partner_path}")

    parquet_files = list(partner_path.glob("*.parquet"))
    print(f"\nFound {len(parquet_files)} parquet file(s):")

    for file in parquet_files:
        size_mb = file.stat().st_size / (1024 * 1024)
        print(f"  {file.name}: {size_mb:.2f} MB")

    # Try to read metadata
    metadata_file = partner_path / "metadata.json"
    if metadata_file.exists():
        print(f"\n✓ Metadata file found: {metadata_file}")
        import json
        try:
            with open(metadata_file) as f:
                metadata = json.load(f)
                print(f"\nMetadata:")
                print(f"  Partner: {metadata.get('partner', 'N/A')}")
                print(f"  Source: {metadata.get('source', 'N/A')}")
                print(f"  Records: {metadata.get('records', 'N/A'):,}")
                print(f"  Date range: {metadata.get('date_range', {}).get('start', 'N/A')} to {metadata.get('date_range', {}).get('end', 'N/A')}")
        except Exception as e:
            print(f"  ✗ Error reading metadata: {e}")
    else:
        print(f"\n⚠ No metadata file found")


def main():
    """Main application entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='TED (Tenders Electronic Daily) Silver Layer Processor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process TED partner data
  python -m src.processing.ted.main

  # Show statistics
  python -m src.processing.ted.main --stats

  # Validate bronze layer
  python -m src.processing.ted.main --validate
        """
    )

    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show Silver layer statistics'
    )

    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate Bronze layer structure'
    )

    parser.add_argument(
        '--bronze-dir',
        type=str,
        default=DEFAULT_BRONZE_DIR,
        metavar='PATH',
        help=f'Bronze layer directory (default: {DEFAULT_BRONZE_DIR})'
    )

    parser.add_argument(
        '--silver-dir',
        type=str,
        default=DEFAULT_SILVER_DIR,
        metavar='PATH',
        help=f'Silver layer directory (default: {DEFAULT_SILVER_DIR})'
    )

    args = parser.parse_args()

    # Execute based on arguments
    bronze_dir = args.bronze_dir
    silver_dir = args.silver_dir

    try:
        if args.stats:
            # Show statistics
            show_statistics(silver_dir)

        elif args.validate:
            # Validate Bronze layer
            validate_bronze(bronze_dir)

        else:
            # Default: process TED data
            print(f"\nUsing directories:")
            print(f"  Bronze: {bronze_dir}")
            print(f"  Silver: {silver_dir}")
            process_ted_data(bronze_dir, silver_dir)

        sys.exit(0)

    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
