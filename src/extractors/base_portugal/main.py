#!/usr/bin/env python3
"""
Interactive menu for BASE Portugal data extraction.
"""
import sys
import json
import logging
from pathlib import Path

from .extractor import BasePortugalExtractor
from .config import PORTUGAL_PUBLICATIONS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def display_menu():
    """Display the main menu."""
    print("\n" + "=" * 50)
    print(" BASE Portugal Extractor (dados.gov.pt)")
    print("=" * 50)
    print("\nAvailable Publications:")

    # Create ordered list of publications
    pubs_list = list(PORTUGAL_PUBLICATIONS.items())
    for idx, (pub_key, pub_config) in enumerate(pubs_list, 1):
        print(f" {idx}. {pub_config['name']}")
        print(f"    Data range: {pub_config['data_range']}")
        print(f"    Format: {pub_config['format']}")

    print("\nOptions:")
    print("  1  - Extract BASE Portugal data")
    print("  0  - Exit")
    print("=" * 50)


def display_results_summary(result: dict):
    """Display extraction results summary."""
    print("\n" + "-" * 50)
    print("EXTRACTION RESULTS")
    print("-" * 50)

    if result.get('success'):
        print(f"✓ Success: {result['publication_name']}")
        print(f"  Records downloaded: {result['records_downloaded']}")
        print(f"  Records saved: {result['records_saved']}")

        if result.get('date_distribution'):
            dates = sorted(result['date_distribution'].keys())
            if dates:
                print(f"  Date range: {dates[0]} to {dates[-1]}")
                print(f"  Total dates with data: {len(dates)}")
    else:
        print(f"✗ Failed: {result.get('publication_name', 'Unknown')}")
        print(f"  Error: {result.get('error', 'Unknown error')}")

    print("-" * 50)


def display_all_results_summary(results: dict):
    """Display summary for all publications extraction."""
    print("\n" + "=" * 50)
    print("OVERALL EXTRACTION SUMMARY")
    print("=" * 50)
    print(f"Total publications: {results['total_publications']}")
    print(f"Successful: {results['successful_publications']}")
    print(f"Failed: {results['failed_publications']}")
    print(f"Total records saved: {results['total_records_saved']}")
    print(f"Duration: {results['duration_seconds']:.2f} seconds")

    # Show failed publications if any
    if results['failed_publications'] > 0:
        print("\nFailed publications:")
        for pub_result in results['publication_results']:
            if not pub_result['success']:
                print(f"  - {pub_result['publication_name']}: {pub_result['error']}")

    print("=" * 50)


def extract_portugal(extractor: BasePortugalExtractor, year: int = 2025):
    """Extract data from BASE Portugal."""
    print(f"\nExtracting: BASE Portugal (Year: {year})")
    print("Please wait...\n")

    results = extractor.extract_all(year)
    display_all_results_summary(results)

    # Save results summary
    results_path = Path(extractor.base_data_dir) / "bronze" / "base_portugal" / "extraction_results.json"
    results_path.parent.mkdir(parents=True, exist_ok=True)

    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nResults summary saved to: {results_path}")

    return results


def main():
    """Main application loop."""
    extractor = BasePortugalExtractor()

    while True:
        display_menu()

        try:
            choice = input("\nEnter choice: ").strip()

            # Exit
            if choice == '0':
                print("\nExiting. Goodbye!")
                sys.exit(0)

            # Extract BASE Portugal
            elif choice == '1':
                year = input("Enter year (default 2025): ").strip() or "2025"
                try:
                    year = int(year)
                    extract_portugal(extractor, year)
                except ValueError:
                    print("Invalid year. Using default: 2025")
                    extract_portugal(extractor, 2025)

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
