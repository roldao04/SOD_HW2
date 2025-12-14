#!/usr/bin/env python3
"""
Interactive menu for BASE Portugal Silver layer processing.
"""
import sys
import logging
from pathlib import Path

from .transformer import process_bronze_directory
from .parquet_writer import write_to_parquet, get_parquet_stats
from .config import COUNTRY_MAPPINGS

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

    bronze_dir = str(data_dir / "bronze" / "base_portugal")
    silver_dir = str(data_dir / "silver" / "base_portugal")

    return bronze_dir, silver_dir

DEFAULT_BRONZE_DIR, DEFAULT_SILVER_DIR = get_default_paths()


def display_menu():
    """Display the main menu."""
    print("\n" + "=" * 60)
    print(" BASE Portugal - Silver Layer Processor")
    print("=" * 60)
    print("\nAvailable Countries:")

    countries = list(COUNTRY_MAPPINGS.keys())
    for idx, country in enumerate(countries, 1):
        print(f" {idx:2d}. {country.upper()}")

    print("\nOptions:")
    print("  1    - Process Portugal")
    print("  S    - Show Silver layer statistics")
    print("  V    - Validate Bronze layer")
    print("  0    - Exit")
    print("=" * 60)


def process_country(country: str, bronze_dir: str, silver_dir: str):
    """Process a single country."""
    print(f"\n{'='*60}")
    print(f" Processing: {country.upper()}")
    print("="*60)

    # Check if Bronze directory exists
    bronze_path = Path(bronze_dir) / country
    if not bronze_path.exists():
        print(f"\n✗ Bronze directory not found: {bronze_path}")
        print("  Make sure you have extracted data for this country first.")
        return

    # Count files
    json_files = list(bronze_path.glob("**/records_*.json"))
    print(f"\nFound {len(json_files)} Bronze files")

    if len(json_files) == 0:
        print("No data to process.")
        return

    print("Processing...")

    try:
        # Transform records
        transformed_records = process_bronze_directory(bronze_dir, country)

        if not transformed_records:
            print("\n✗ No records were successfully transformed")
            return

        print(f"✓ Transformed {len(transformed_records)} records")

        # Write to Parquet
        print("\nWriting to Silver layer...")
        stats = write_to_parquet(transformed_records, silver_dir, partition_by_date=True)

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


def main():
    """Main application loop."""
    bronze_dir = DEFAULT_BRONZE_DIR
    silver_dir = DEFAULT_SILVER_DIR

    print(f"\nUsing directories:")
    print(f"  Bronze: {bronze_dir}")
    print(f"  Silver: {silver_dir}")

    countries = list(COUNTRY_MAPPINGS.keys())

    while True:
        display_menu()

        try:
            choice = input("\nEnter choice: ").strip().upper()

            # Exit
            if choice == '0':
                print("\nExiting. Goodbye!")
                sys.exit(0)

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


if __name__ == "__main__":
    main()
