"""
Deduplication logic for append-only data lake.

Provides hash-based deduplication while maintaining audit trail.
"""

import logging
from typing import List, Dict, Set, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class DeduplicationManager:
    """
    Manages record deduplication using hash-based approach.

    For append-only architecture: tracks duplicates but doesn't remove them.
    Provides metrics and filtering capabilities.
    """

    def __init__(self):
        """Initialize deduplication manager."""
        self.seen_hashes: Set[str] = set()
        self.duplicate_count = 0
        self.unique_count = 0

    def filter_new_records(
        self,
        records: List[Dict],
        existing_hashes: Set[str]
    ) -> Tuple[List[Dict], Dict[str, int]]:
        """
        Filter records to only include new ones not in existing_hashes.

        For incremental processing: only write records we haven't seen before.

        Args:
            records: List of records with 'record_hash' field
            existing_hashes: Set of hashes already written to storage

        Returns:
            Tuple of (new_records, stats_dict)
        """
        new_records = []
        stats = {
            'total_input': len(records),
            'duplicates_skipped': 0,
            'new_records': 0
        }

        for record in records:
            record_hash = record.get('record_hash')
            if not record_hash:
                logger.warning(f"Record missing 'record_hash' field: {record.get('ocid', 'unknown')}")
                # Include records without hash (shouldn't happen, but be safe)
                new_records.append(record)
                stats['new_records'] += 1
                continue

            if record_hash in existing_hashes:
                stats['duplicates_skipped'] += 1
                logger.debug(f"Skipping duplicate record: {record.get('ocid')} (hash: {record_hash[:8]}...)")
            else:
                new_records.append(record)
                existing_hashes.add(record_hash)
                stats['new_records'] += 1

        logger.info(
            f"Deduplication: {stats['new_records']} new, "
            f"{stats['duplicates_skipped']} duplicates (from {stats['total_input']} total)"
        )

        return new_records, stats

    def analyze_duplicates(self, records: List[Dict]) -> Dict:
        """
        Analyze duplicate records in a dataset.

        Useful for reporting and data quality checks.

        Args:
            records: List of records with 'record_hash' field

        Returns:
            Dictionary with duplicate analysis
        """
        hash_to_records = defaultdict(list)

        for idx, record in enumerate(records):
            record_hash = record.get('record_hash', f'missing_{idx}')
            hash_to_records[record_hash].append({
                'index': idx,
                'ocid': record.get('ocid', 'unknown'),
                'publication_date': record.get('publication_date'),
                'processing_timestamp': record.get('processing_timestamp')
            })

        # Find duplicates
        duplicates = {
            hash_val: occurrences
            for hash_val, occurrences in hash_to_records.items()
            if len(occurrences) > 1
        }

        total_records = len(records)
        unique_hashes = len(hash_to_records)
        duplicate_records = sum(len(occs) - 1 for occs in duplicates.values())

        return {
            'total_records': total_records,
            'unique_hashes': unique_hashes,
            'duplicate_groups': len(duplicates),
            'duplicate_records': duplicate_records,
            'deduplication_rate': 1 - (unique_hashes / total_records) if total_records > 0 else 0,
            'duplicate_details': duplicates
        }

    def mark_latest_records(self, records: List[Dict]) -> List[Dict]:
        """
        Add 'is_latest' flag to records based on processing_timestamp.

        For each unique record_hash, marks the most recent one as latest.

        Args:
            records: List of records with 'record_hash' and 'processing_timestamp'

        Returns:
            Records with 'is_latest' field added
        """
        # Group by hash
        hash_to_records = defaultdict(list)
        for record in records:
            record_hash = record.get('record_hash', '')
            hash_to_records[record_hash].append(record)

        # Mark latest for each hash
        for record_group in hash_to_records.values():
            if len(record_group) == 1:
                record_group[0]['is_latest'] = True
            else:
                # Sort by processing_timestamp (most recent last)
                sorted_group = sorted(
                    record_group,
                    key=lambda r: r.get('processing_timestamp', '')
                )
                # Mark only the most recent as latest
                for record in sorted_group[:-1]:
                    record['is_latest'] = False
                sorted_group[-1]['is_latest'] = True

        return records

    @staticmethod
    def get_unique_records(records: List[Dict]) -> List[Dict]:
        """
        Get only unique records (first occurrence of each hash).

        Useful for creating deduplicated views.

        Args:
            records: List of records with 'record_hash' field

        Returns:
            List of unique records
        """
        seen_hashes = set()
        unique_records = []

        for record in records:
            record_hash = record.get('record_hash')
            if record_hash and record_hash not in seen_hashes:
                unique_records.append(record)
                seen_hashes.add(record_hash)

        return unique_records

    @staticmethod
    def create_dedup_report(records: List[Dict]) -> str:
        """
        Create a human-readable deduplication report.

        Args:
            records: List of records

        Returns:
            Formatted report string
        """
        manager = DeduplicationManager()
        analysis = manager.analyze_duplicates(records)

        report_lines = [
            "=" * 60,
            "DEDUPLICATION ANALYSIS",
            "=" * 60,
            f"Total records: {analysis['total_records']:,}",
            f"Unique records: {analysis['unique_hashes']:,}",
            f"Duplicate groups: {analysis['duplicate_groups']:,}",
            f"Duplicate records: {analysis['duplicate_records']:,}",
            f"Deduplication rate: {analysis['deduplication_rate']:.2%}",
            "=" * 60
        ]

        if analysis['duplicate_groups'] > 0:
            report_lines.append("\nTop duplicate groups:")
            # Show top 5 most duplicated
            sorted_dupes = sorted(
                analysis['duplicate_details'].items(),
                key=lambda x: len(x[1]),
                reverse=True
            )[:5]

            for hash_val, occurrences in sorted_dupes:
                report_lines.append(f"  Hash {hash_val[:8]}...: {len(occurrences)} occurrences")
                for occ in occurrences[:3]:  # Show first 3
                    report_lines.append(f"    - OCID: {occ['ocid']}, Date: {occ['publication_date']}")

        return '\n'.join(report_lines)
