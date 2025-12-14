"""MinIO client wrapper for storage operations."""

import json
import logging
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Union, BinaryIO

from minio import Minio
from minio.error import S3Error

from .storage_config import StorageConfig

logger = logging.getLogger(__name__)


class MinIOClient:
    """
    Unified client for MinIO/S3 operations with local fallback.

    Provides consistent interface for:
    - Writing JSON/Parquet files
    - Reading files
    - Listing objects
    - Path management
    """

    def __init__(self, config: Optional[StorageConfig] = None):
        """
        Initialize MinIO client.

        Args:
            config: Storage configuration. If None, loads from environment.
        """
        self.config = config or StorageConfig.from_env()
        self.client: Optional[Minio] = None

        if not self.config.use_local_storage:
            try:
                self.client = Minio(
                    self.config.endpoint,
                    access_key=self.config.access_key,
                    secret_key=self.config.secret_key,
                    secure=self.config.secure
                )
                logger.info(f"Connected to MinIO at {self.config.endpoint}")
                self._ensure_buckets()
            except Exception as e:
                logger.warning(f"Failed to connect to MinIO: {e}. Falling back to local storage.")
                self.config.use_local_storage = True

    def _ensure_buckets(self):
        """Ensure all required buckets exist."""
        if not self.client:
            return

        for bucket in [self.config.bronze_bucket, self.config.silver_bucket, self.config.gold_bucket]:
            try:
                if not self.client.bucket_exists(bucket):
                    self.client.make_bucket(bucket)
                    logger.info(f"Created bucket: {bucket}")
            except S3Error as e:
                logger.error(f"Error creating bucket {bucket}: {e}")

    def write_json(self, layer: str, path: str, data: dict) -> str:
        """
        Write JSON data to storage.

        Args:
            layer: Storage layer (bronze/silver/gold)
            path: Object path within bucket (e.g., 'source/country/2025/01/01/file.json')
            data: Dictionary to write as JSON

        Returns:
            Full path to written object
        """
        bucket = self.config.get_layer_bucket(layer)
        json_bytes = json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8')

        if self.config.use_local_storage:
            return self._write_local(layer, path, json_bytes)

        try:
            self.client.put_object(
                bucket,
                path,
                BytesIO(json_bytes),
                len(json_bytes),
                content_type='application/json'
            )
            full_path = f"{bucket}/{path}"
            logger.info(f"Wrote JSON to MinIO: {full_path}")
            return full_path
        except S3Error as e:
            logger.error(f"Error writing to MinIO: {e}")
            raise

    def write_parquet(self, layer: str, path: str, data: bytes) -> str:
        """
        Write Parquet data to storage.

        Args:
            layer: Storage layer (bronze/silver/gold)
            path: Object path within bucket
            data: Parquet file bytes

        Returns:
            Full path to written object
        """
        bucket = self.config.get_layer_bucket(layer)

        if self.config.use_local_storage:
            return self._write_local(layer, path, data)

        try:
            self.client.put_object(
                bucket,
                path,
                BytesIO(data),
                len(data),
                content_type='application/parquet'
            )
            full_path = f"{bucket}/{path}"
            logger.info(f"Wrote Parquet to MinIO: {full_path}")
            return full_path
        except S3Error as e:
            logger.error(f"Error writing to MinIO: {e}")
            raise

    def read_json(self, layer: str, path: str) -> dict:
        """
        Read JSON data from storage.

        Args:
            layer: Storage layer (bronze/silver/gold)
            path: Object path within bucket

        Returns:
            Parsed JSON as dictionary
        """
        bucket = self.config.get_layer_bucket(layer)

        if self.config.use_local_storage:
            return self._read_local_json(layer, path)

        try:
            response = self.client.get_object(bucket, path)
            data = json.loads(response.read().decode('utf-8'))
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            logger.error(f"Error reading from MinIO: {e}")
            raise

    def read_bytes(self, layer: str, path: str) -> bytes:
        """
        Read raw bytes from storage.

        Args:
            layer: Storage layer (bronze/silver/gold)
            path: Object path within bucket

        Returns:
            Raw file bytes
        """
        bucket = self.config.get_layer_bucket(layer)

        if self.config.use_local_storage:
            return self._read_local_bytes(layer, path)

        try:
            response = self.client.get_object(bucket, path)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            logger.error(f"Error reading from MinIO: {e}")
            raise

    def list_objects(self, layer: str, prefix: str = '') -> List[str]:
        """
        List objects in storage with given prefix.

        Args:
            layer: Storage layer (bronze/silver/gold)
            prefix: Object path prefix to filter by

        Returns:
            List of object paths
        """
        bucket = self.config.get_layer_bucket(layer)

        if self.config.use_local_storage:
            return self._list_local(layer, prefix)

        try:
            objects = self.client.list_objects(bucket, prefix=prefix, recursive=True)
            return [obj.object_name for obj in objects]
        except S3Error as e:
            logger.error(f"Error listing objects from MinIO: {e}")
            raise

    def _write_local(self, layer: str, path: str, data: bytes) -> str:
        """Write data to local filesystem."""
        local_path = Path(self.config.local_data_path) / layer / path
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(data)
        logger.info(f"Wrote to local storage: {local_path}")
        return str(local_path)

    def _read_local_json(self, layer: str, path: str) -> dict:
        """Read JSON from local filesystem."""
        local_path = Path(self.config.local_data_path) / layer / path
        return json.loads(local_path.read_text())

    def _read_local_bytes(self, layer: str, path: str) -> bytes:
        """Read bytes from local filesystem."""
        local_path = Path(self.config.local_data_path) / layer / path
        return local_path.read_bytes()

    def _list_local(self, layer: str, prefix: str = '') -> List[str]:
        """List files from local filesystem."""
        base_path = Path(self.config.local_data_path) / layer
        if not base_path.exists():
            return []

        search_path = base_path / prefix if prefix else base_path
        if search_path.is_file():
            return [str(search_path.relative_to(base_path))]

        files = []
        if search_path.exists():
            for file_path in search_path.rglob('*'):
                if file_path.is_file():
                    files.append(str(file_path.relative_to(base_path)))
        return files
