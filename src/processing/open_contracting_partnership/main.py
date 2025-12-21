#!/usr/bin/env python3
"""
Interactive menu for Open Contracting Partnership Silver layer processing.
Supports both interactive and CLI modes.
"""
import sys
import logging
import argparse
from pathlib import Path
from typing import Optional

from .transformer import process_bronze_directory
from .parquet_writer import write_to_parquet, get_parquet_stats
from .config import COUNTRY_MAPPINGS

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

# Default paths - use relative paths from project root
def get_default_paths():
    """Get default Bronze and Silver directory paths."""
    # Get project root (4 levels up from this file)
    project_root = Path(__file__).parent.parent.parent.parent
    data_dir = project_root / "data"
    
    bronze_dir = str(data_dir / "bronze" / "open_contracting_partnership")
    silver_dir = str(data_dir / "silver" / "open_contracting_partnership")
    
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


def display_menu():
    """Display the main menu."""
    print("\n" + "=" * 60)
    print(" Open Contracting Partnership - Silver Layer Processor")
    print("=" * 60)
    print("\nAvailable Countries:")

    countries = list(COUNTRY_MAPPINGS.keys())
    for idx, country in enumerate(countries, 1):
        print(f" {idx:2d}. {country.upper()}")

    print("\nOptions:")
    print("  1-7  - Process single country")
    print("  A    - Process all countries")
    print("  S    - Show Silver layer statistics")
    print("  V    - Validate Bronze layer")
    print("  0    - Exit")
    print("=" * 60)


def process_country(country: str, bronze_dir: str, silver_dir: str):
    """Process a single country."""
    print(f"\n{'='*60}")
    print(f" Processing: {country.upper()}")
    print("="*60)

    print("Checking for Bronze data (MinIO + local)...")

    try:
        # Get storage client
        storage_client = get_storage_client()

        # Transform records (checks both MinIO and local storage)
        transformed_records = process_bronze_directory(
            bronze_dir,
            country,
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

        if stats.get('partitions'):
            print("\nPartitions:")
            for partition, count in stats['partitions'].items():
                print(f"  {partition}: {count} records")

        print("="*60)

    except Exception as e:
        logger.error(f"Error processing {country}: {e}", exc_info=True)
        print(f"\n✗ Error: {e}")


def process_all_countries(bronze_dir: str, silver_dir: str, skip_confirmation: bool = False):
    """
    Process all countries.

    Args:
        bronze_dir: Bronze layer directory
        silver_dir: Silver layer directory
        skip_confirmation: Skip confirmation prompt (for CLI/automated mode)
    """
    print(f"\n{'='*60}")
    print(" Processing ALL Countries")
    print("="*60)

    countries = list(COUNTRY_MAPPINGS.keys())
    print(f"\nCountries to process: {', '.join([c.upper() for c in countries])}")

    # Skip confirmation in CLI/automated mode
    if not skip_confirmation:
        confirm = input("\nThis may take a while. Continue? (y/N): ").strip().lower()
        if confirm != 'y':
            print("Cancelled.")
            return

    total_records = 0
    total_files = 0
    failed_countries = []

    # Initialize storage client once for all countries
    storage_client = get_storage_client()

    for country in countries:
        print(f"\n\n{'='*60}")
        print(f" Processing: {country.upper()}")
        print("="*60)

        try:
            # Try processing - process_bronze_directory will check both MinIO and local storage
            transformed_records = process_bronze_directory(
                bronze_dir,
                country,
                storage_client=storage_client,
                incremental=True
            )

            if transformed_records:
                stats = write_to_parquet(
                    transformed_records,
                    silver_dir,
                    partition_by_date=True,
                    storage_client=storage_client,
                    validate_quality=True,
                    enable_deduplication=True
                )
                total_records += stats['records_written']
                total_files += stats['files_written']
                print(f"✓ {country.upper()}: {stats['records_written']} records written")
            else:
                print(f"✗ {country.upper()}: No records transformed")
                failed_countries.append(country)

        except Exception as e:
            logger.error(f"Error processing {country}: {e}")
            print(f"✗ {country.upper()}: Error - {e}")
            failed_countries.append(country)

    # Summary
    print(f"\n{'='*60}")
    print(" OVERALL SUMMARY")
    print("="*60)
    print(f"Total files written: {total_files}")
    print(f"Total records written: {total_records}")

    if failed_countries:
        print(f"\nFailed countries: {', '.join([c.upper() for c in failed_countries])}")
    else:
        print("\n✓ All countries processed successfully!")

    print("="*60)


def show_statistics(silver_dir: str):
    """Show Silver layer statistics."""
    print(f"\n{'='*60}")
    print(" Silver Layer Statistics")
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
            print("\nBy Country:")
            for country, country_stats in sorted(stats['countries'].items()):
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
    print(" Bronze Layer Validation")
    print("="*60)

    bronze_path = Path(bronze_dir)
    if not bronze_path.exists():
        print(f"\n✗ Bronze directory not found: {bronze_dir}")
        return

    print("\nScanning Bronze layer...")

    countries = list(COUNTRY_MAPPINGS.keys())
    for country in countries:
        country_path = bronze_path / country
        if country_path.exists():
            json_files = list(country_path.glob("**/records_*.json"))
            print(f"  {country.upper()}: {len(json_files)} files")
        else:
            print(f"  {country.upper()}: No data")


def run_interactive_mode():
    """Run interactive menu mode."""
    bronze_dir = DEFAULT_BRONZE_DIR
    silver_dir = DEFAULT_SILVER_DIR

    countries = list(COUNTRY_MAPPINGS.keys())

    while True:
        display_menu()

        try:
            choice = input("\nEnter choice: ").strip().upper()

            # Exit
            if choice == '0':
                print("\nExiting. Goodbye!")
                sys.exit(0)

            # Process all
            elif choice == 'A':
                process_all_countries(bronze_dir, silver_dir)

            # Show statistics
            elif choice == 'S':
                show_statistics(silver_dir)

            # Validate Bronze
            elif choice == 'V':
                validate_bronze(bronze_dir)

            # Process specific country
            elif choice.isdigit():
                number = int(choice)
                if 1 <= number <= len(countries):
                    country = countries[number - 1]
                    process_country(country, bronze_dir, silver_dir)
                else:
                    print(f"\nInvalid country number: {number}")

            else:
                print(f"\nInvalid choice: {choice}")

        except KeyboardInterrupt:
            print("\n\nInterrupted by user. Exiting...")
            sys.exit(0)
        except EOFError:
            print("\n\nNo input available. Exiting...")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            print(f"\nError: {e}")

        # Wait for user to continue
        try:
            input("\nPress Enter to continue...")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            sys.exit(0)


def main():
    """Main application entry point. Supports both CLI and interactive modes."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Open Contracting Partnership Silver Layer Processor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive menu
  python -m src.processing.open_contracting_partnership.main

  # Process all countries
  python -m src.processing.open_contracting_partnership.main --all

  # Process specific country
  python -m src.processing.open_contracting_partnership.main --country spain

  # Show statistics
  python -m src.processing.open_contracting_partnership.main --stats

  # Validate bronze layer
  python -m src.processing.open_contracting_partnership.main --validate
        """
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='Process all countries'
    )

    parser.add_argument(
        '--country',
        type=str,
        metavar='NAME',
        help='Process specific country (e.g., spain, germany, uk)'
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

    # Determine mode: CLI or interactive
    if args.all or args.country or args.stats or args.validate:
        # CLI mode - non-interactive
        bronze_dir = args.bronze_dir
        silver_dir = args.silver_dir

        try:
            if args.all:
                # Process all countries (skip confirmation in CLI mode)
                print("Processing all countries...")
                process_all_countries(bronze_dir, silver_dir, skip_confirmation=True)

            elif args.country:
                # Process specific country
                country = args.country.lower()
                if country in COUNTRY_MAPPINGS:
                    print(f"Processing country: {country.upper()}")
                    process_country(country, bronze_dir, silver_dir)
                else:
                    print(f"Error: Invalid country: {country}")
                    print(f"Valid countries: {', '.join(COUNTRY_MAPPINGS.keys())}")
                    sys.exit(1)

            elif args.stats:
                # Show statistics
                show_statistics(silver_dir)

            elif args.validate:
                # Validate Bronze layer
                validate_bronze(bronze_dir)

            # Exit after CLI operation
            sys.exit(0)

        except Exception as e:
            logger.error(f"Processing failed: {e}", exc_info=True)
            print(f"\nError: {e}")
            sys.exit(1)

    else:
        # Interactive mode
        run_interactive_mode()


if __name__ == "__main__":
    main()
