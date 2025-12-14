"""Storage configuration management."""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class StorageConfig:
    """Configuration for storage backend."""

    # MinIO/S3 Configuration
    endpoint: str = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
    access_key: str = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
    secret_key: str = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
    secure: bool = os.getenv('MINIO_SECURE', 'false').lower() == 'true'

    # Bucket names
    bronze_bucket: str = 'bronze'
    silver_bucket: str = 'silver'
    gold_bucket: str = 'gold'

    # Local fallback (for development without Docker)
    use_local_storage: bool = os.getenv('USE_LOCAL_STORAGE', 'false').lower() == 'true'
    local_data_path: str = os.getenv('LOCAL_DATA_PATH', './data')

    @classmethod
    def from_env(cls) -> 'StorageConfig':
        """Create configuration from environment variables."""
        return cls()

    def get_layer_bucket(self, layer: str) -> str:
        """Get bucket name for a specific layer (bronze/silver/gold)."""
        layer = layer.lower()
        if layer == 'bronze':
            return self.bronze_bucket
        elif layer == 'silver':
            return self.silver_bucket
        elif layer == 'gold':
            return self.gold_bucket
        else:
            raise ValueError(f"Invalid layer: {layer}. Must be bronze, silver, or gold.")
