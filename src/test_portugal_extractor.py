#!/usr/bin/env python3
"""
Test script for BASE Portugal extractor.
Tests the extraction pipeline without downloading all data.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.extractors.base_portugal.extractor import BasePortugalExtractor

def test_api_connection():
    """Test connection to dados.gov.pt API."""
    print("=" * 60)
    print("Testing BASE Portugal Extractor")
    print("=" * 60)

    extractor = BasePortugalExtractor()

    print("\n1. Testing API connection...")
    print(f"   Base data directory: {extractor.base_data_dir}")

    # Test getting dataset resources
    print("\n2. Fetching dataset info from dados.gov.pt API...")
    resources = extractor._get_dataset_resources("contratos-publicos-portal-base-impic-contratos-de-2012-a-2025")

    if resources:
        print(f"   ✓ Successfully fetched {len(resources)} resources")
        print("\n   Available resources:")
        for i, resource in enumerate(resources[:5], 1):  # Show first 5
            title = resource.get('title', 'No title')
            url = resource.get('url', 'No URL')
            print(f"   {i}. {title}")
            print(f"      URL: {url[:80]}...")

        if len(resources) > 5:
            print(f"   ... and {len(resources) - 5} more resources")

        # Try to find 2025 resource
        print("\n3. Looking for 2025 data...")
        year_resource = extractor._find_year_resource(resources, 2025)

        if year_resource:
            print(f"   ✓ Found 2025 resource: {year_resource.get('title')}")
            print(f"   URL: {year_resource.get('url')}")
            print("\n   ✓ Extractor is ready to download data!")
            print("\n   To extract 2025 data, run:")
            print("   $ source venv/bin/activate")
            print("   $ python3 -m src.extractors.base_portugal.main")
        else:
            print("   ✗ No 2025 data found")
            print("   Available years in dataset:")
            for resource in resources[:10]:
                title = resource.get('title', '')
                if any(str(year) in title for year in range(2020, 2026)):
                    print(f"      - {title}")
    else:
        print("   ✗ Failed to fetch dataset info")
        return False

    print("\n" + "=" * 60)
    print("Test completed successfully!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        success = test_api_connection()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
