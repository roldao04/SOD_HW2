#!/usr/bin/env python3
"""
Upload Gold layer files to MinIO.

This script uploads the locally-generated Gold layer files (unified dataset,
aggregates, and quality reports) to the MinIO gold bucket, making them
accessible to Dremio for SQL queries.
"""

import json
import logging
from pathlib import Path
from src.storage import MinIOClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def upload_gold_layer():
    """Upload all Gold layer files to MinIO gold bucket."""

    print("\n" + "=" * 60)
    print(" UPLOADING GOLD LAYER TO MINIO")
    print("=" * 60 + "\n")

    # Initialize MinIO client
    client = MinIOClient()
    gold_base = Path('data/gold')

    if not gold_base.exists():
        print(f"❌ Gold layer directory not found: {gold_base}")
        print("   Run: make gold-layer")
        return 0, 0

    # Define files to upload (local_path, minio_path)
    files_to_upload = []

    # 1. Unified dataset
    unified_file = gold_base / 'unified' / 'all_tenders.parquet'
    if unified_file.exists():
        files_to_upload.append((
            unified_file,
            'unified/all_tenders.parquet',
            'parquet'
        ))

    # 2. Aggregates
    aggregates_dir = gold_base / 'aggregates'
    if aggregates_dir.exists():
        for parquet_file in aggregates_dir.glob('*.parquet'):
            files_to_upload.append((
                parquet_file,
                f'aggregates/{parquet_file.name}',
                'parquet'
            ))

    # 3. Quality reports
    quality_dir = gold_base / 'quality'
    if quality_dir.exists():
        for json_file in quality_dir.glob('*.json'):
            files_to_upload.append((
                json_file,
                f'quality/{json_file.name}',
                'json'
            ))

    if not files_to_upload:
        print("❌ No Gold layer files found to upload")
        print("   Run: make gold-layer")
        return 0, 0

    print(f"Found {len(files_to_upload)} files to upload\n")

    uploaded = 0
    failed = 0
    total_size_mb = 0

    for local_path, minio_path, file_type in files_to_upload:
        try:
            # Read file bytes
            file_bytes = local_path.read_bytes()
            file_size_mb = len(file_bytes) / (1024 * 1024)
            total_size_mb += file_size_mb

            print(f"📤 Uploading {minio_path} ({file_size_mb:.2f} MB)...")

            # Upload to MinIO based on file type
            if file_type == 'parquet':
                client.write_parquet('gold', minio_path, file_bytes)
            else:  # json
                json_data = json.loads(file_bytes.decode('utf-8'))
                client.write_json('gold', minio_path, json_data)

            uploaded += 1
            print(f"   ✅ Uploaded successfully")

        except Exception as e:
            failed += 1
            logger.error(f"Failed to upload {local_path}: {e}")
            print(f"   ❌ Failed: {e}")

    print(f"\n{'=' * 60}")
    print(f" UPLOAD SUMMARY")
    print(f"{'=' * 60}")
    print(f"✅ Uploaded: {uploaded} files ({total_size_mb:.2f} MB)")
    print(f"❌ Failed: {failed} files")
    print(f"{'=' * 60}\n")

    # Verify uploads
    print("Verifying uploads in MinIO gold bucket...")
    try:
        gold_objects = client.list_objects('gold', '')
        print(f"\n📦 Total objects in gold bucket: {len(gold_objects)}")

        if gold_objects:
            print("\nGold bucket contents:")

            # Group by directory
            unified_files = [o for o in gold_objects if o.startswith('unified/')]
            aggregate_files = [o for o in gold_objects if o.startswith('aggregates/')]
            quality_files = [o for o in gold_objects if o.startswith('quality/')]

            if unified_files:
                print("\n  📊 Unified:")
                for obj in sorted(unified_files):
                    print(f"     - {obj}")

            if aggregate_files:
                print("\n  📈 Aggregates:")
                for obj in sorted(aggregate_files):
                    print(f"     - {obj}")

            if quality_files:
                print("\n  📋 Quality Reports:")
                for obj in sorted(quality_files):
                    print(f"     - {obj}")

        print(f"\n{'=' * 60}")
        print(" NEXT STEPS")
        print(f"{'=' * 60}")
        print("\n1. Open Dremio UI: http://localhost:9047")
        print("2. Navigate to: Sources → minio")
        print("3. Right-click 'minio' → Refresh Metadata")
        print("4. Wait 5-10 seconds, then expand: minio → gold")
        print("\n5. Format the datasets:")
        print("   a) Right-click 'unified' folder → Format Folder → Parquet → Save")
        print("   b) Right-click 'aggregates' folder → Format Folder → Parquet → Save")
        print("\n6. Test with SQL:")
        print("   SELECT COUNT(*) FROM minio.gold.unified;")
        print("   -- Expected: 536,778 records")
        print(f"\n{'=' * 60}\n")

    except Exception as e:
        logger.error(f"Failed to verify uploads: {e}")
        print(f"❌ Verification failed: {e}")

    return uploaded, failed


if __name__ == "__main__":
    try:
        uploaded, failed = upload_gold_layer()
        exit_code = 0 if failed == 0 else 1
        exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nUpload interrupted by user")
        exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n❌ Unexpected error: {e}")
        exit(1)
