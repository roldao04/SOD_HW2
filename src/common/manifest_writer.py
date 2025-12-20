"""
Manifest file management for tracking data lineage and metadata.

Provides utilities for reading/writing manifest files that track:
- Data provenance
- Processing metadata
- File relationships
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.storage import MinIOClient

logger = logging.getLogger(__name__)


class ManifestWriter:
    """
    Manages manifest files for data lineage and metadata tracking.

    Manifest files provide audit trail and help track data provenance.
    """

    @staticmethod
    def create_extraction_manifest(
        source_name: str,
        extraction_date: str,
        file_count: int,
        record_count: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict:
        """
        Create extraction manifest.

        Args:
            source_name: Name of data source
            extraction_date: Date of extraction
            file_count: Number of files extracted
            record_count: Number of records extracted
            metadata: Optional additional metadata

        Returns:
            Manifest dictionary
        """
        manifest = {
            'manifest_version': '1.0',
            'manifest_type': 'extraction',
            'source': source_name,
            'extraction_date': extraction_date,
            'extraction_timestamp': datetime.utcnow().isoformat() + 'Z',
            'file_count': file_count,
            'record_count': record_count,
            'metadata': metadata or {}
        }

        return manifest

    @staticmethod
    def create_processing_manifest(
        source_name: str,
        input_files: List[str],
        output_files: List[str],
        records_processed: int,
        quality_score: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict:
        """
        Create processing manifest.

        Args:
            source_name: Name of data source
            input_files: List of input file paths (Bronze)
            output_files: List of output file paths (Silver)
            records_processed: Number of records processed
            quality_score: Data quality score
            metadata: Optional additional metadata

        Returns:
            Manifest dictionary
        """
        manifest = {
            'manifest_version': '1.0',
            'manifest_type': 'processing',
            'source': source_name,
            'processing_timestamp': datetime.utcnow().isoformat() + 'Z',
            'input_layer': 'bronze',
            'output_layer': 'silver',
            'input_files': input_files,
            'output_files': output_files,
            'records_processed': records_processed,
            'quality_score': quality_score,
            'metadata': metadata or {}
        }

        return manifest

    @staticmethod
    def save_manifest(
        manifest: Dict,
        output_dir: str,
        filename: str,
        storage_client: Optional['MinIOClient'] = None,
        bucket: str = 'bronze'
    ) -> None:
        """
        Save manifest to storage.

        Args:
            manifest: Manifest dictionary
            output_dir: Local output directory
            filename: Manifest filename
            storage_client: Optional MinIO client
            bucket: Bucket name for MinIO
        """
        # Save to local file
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        local_file = output_path / filename

        with open(local_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved manifest to {local_file}")

        # Save to MinIO if available
        if storage_client:
            try:
                source_name = manifest.get('source', 'unknown')
                object_path = f"{source_name}/manifests/{filename}"
                storage_client.write_json(bucket, object_path, manifest)
                logger.info(f"Saved manifest to MinIO: {bucket}/{object_path}")
            except Exception as e:
                logger.warning(f"Failed to save manifest to MinIO: {e}")

    @staticmethod
    def load_manifest(
        manifest_path: str,
        storage_client: Optional['MinIOClient'] = None,
        bucket: str = 'bronze',
        object_path: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Load manifest from storage.

        Args:
            manifest_path: Local path to manifest file
            storage_client: Optional MinIO client
            bucket: Bucket name for MinIO
            object_path: Object path in MinIO

        Returns:
            Manifest dictionary or None if not found
        """
        # Try local file first
        local_path = Path(manifest_path)
        if local_path.exists():
            try:
                with open(local_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                logger.info(f"Loaded manifest from {local_path}")
                return manifest
            except Exception as e:
                logger.warning(f"Failed to load manifest from {local_path}: {e}")

        # Try MinIO if available
        if storage_client and object_path:
            try:
                manifest = storage_client.read_json(bucket, object_path)
                logger.info(f"Loaded manifest from MinIO: {bucket}/{object_path}")
                return manifest
            except Exception as e:
                logger.debug(f"No manifest in MinIO: {e}")

        logger.warning(f"Manifest not found: {manifest_path}")
        return None

    @staticmethod
    def create_summary_manifest(
        source_name: str,
        layer: str,
        total_files: int,
        total_records: int,
        date_range: Optional[Dict[str, str]] = None,
        quality_metrics: Optional[Dict] = None
    ) -> Dict:
        """
        Create summary manifest for a data layer.

        Args:
            source_name: Name of data source
            layer: Data layer (bronze/silver/gold)
            total_files: Total number of files
            total_records: Total number of records
            date_range: Optional date range (min/max)
            quality_metrics: Optional quality metrics

        Returns:
            Summary manifest dictionary
        """
        manifest = {
            'manifest_version': '1.0',
            'manifest_type': 'summary',
            'source': source_name,
            'layer': layer,
            'generated_at': datetime.utcnow().isoformat() + 'Z',
            'total_files': total_files,
            'total_records': total_records,
            'date_range': date_range or {'min': None, 'max': None},
            'quality_metrics': quality_metrics or {}
        }

        return manifest
