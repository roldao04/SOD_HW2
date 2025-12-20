"""
State management for extraction and processing pipelines.

Tracks what data has been extracted/processed to enable incremental updates.
"""

import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, TYPE_CHECKING
from dataclasses import dataclass, asdict

if TYPE_CHECKING:
    from src.storage import MinIOClient

logger = logging.getLogger(__name__)


@dataclass
class FileState:
    """State information for a single file."""
    timestamp: str
    record_count: int
    md5_hash: str
    size_bytes: int = 0


@dataclass
class ExtractionState:
    """State tracking for extraction (Bronze layer)."""
    last_run: str
    extracted_files: Dict[str, FileState]
    total_records: int = 0
    total_files: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'last_run': self.last_run,
            'total_records': self.total_records,
            'total_files': self.total_files,
            'extracted_files': {
                path: asdict(state) for path, state in self.extracted_files.items()
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ExtractionState':
        """Create from dictionary."""
        extracted_files = {
            path: FileState(**state_dict)
            for path, state_dict in data.get('extracted_files', {}).items()
        }
        return cls(
            last_run=data.get('last_run', ''),
            total_records=data.get('total_records', 0),
            total_files=data.get('total_files', 0),
            extracted_files=extracted_files
        )


@dataclass
class ProcessingState:
    """State tracking for processing (Silver layer)."""
    last_run: str
    processed_bronze_files: List[str]
    record_hashes_written: Set[str]
    total_records_processed: int = 0
    total_files_processed: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'last_run': self.last_run,
            'total_records_processed': self.total_records_processed,
            'total_files_processed': self.total_files_processed,
            'processed_bronze_files': self.processed_bronze_files,
            'record_hashes_written': list(self.record_hashes_written)
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ProcessingState':
        """Create from dictionary."""
        return cls(
            last_run=data.get('last_run', ''),
            total_records_processed=data.get('total_records_processed', 0),
            total_files_processed=data.get('total_files_processed', 0),
            processed_bronze_files=data.get('processed_bronze_files', []),
            record_hashes_written=set(data.get('record_hashes_written', []))
        )


class StateManager:
    """
    Manages extraction and processing state for incremental updates.

    Supports both local filesystem and MinIO storage.
    """

    def __init__(
        self,
        source_name: str,
        base_dir: str = "./data",
        storage_client: Optional['MinIOClient'] = None
    ):
        """
        Initialize state manager.

        Args:
            source_name: Name of the data source (e.g., 'open_contracting_partnership')
            base_dir: Base directory for local state files
            storage_client: Optional MinIO client for cloud storage
        """
        self.source_name = source_name
        self.base_dir = Path(base_dir)
        self.storage_client = storage_client

    def _get_state_path(self, layer: str, state_type: str) -> Path:
        """
        Get local path for state file.

        Args:
            layer: 'bronze' or 'silver'
            state_type: 'extraction_state' or 'processing_state'

        Returns:
            Path to state file
        """
        return self.base_dir / layer / self.source_name / f"{state_type}.json"

    def _get_state_object_path(self, layer: str, state_type: str) -> str:
        """
        Get MinIO object path for state file.

        Args:
            layer: 'bronze' or 'silver'
            state_type: 'extraction_state' or 'processing_state'

        Returns:
            Object path string
        """
        return f"{self.source_name}/{state_type}.json"

    def load_extraction_state(self) -> ExtractionState:
        """
        Load extraction state from storage.

        Returns:
            ExtractionState object
        """
        state_path = self._get_state_path('bronze', 'extraction_state')

        # Try local file first
        if state_path.exists():
            try:
                with open(state_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"Loaded extraction state from {state_path}")
                    return ExtractionState.from_dict(data)
            except Exception as e:
                logger.warning(f"Failed to load extraction state from {state_path}: {e}")

        # Try MinIO if available
        if self.storage_client:
            try:
                object_path = self._get_state_object_path('bronze', 'extraction_state')
                data = self.storage_client.read_json('bronze', object_path)
                logger.info(f"Loaded extraction state from MinIO: bronze/{object_path}")
                return ExtractionState.from_dict(data)
            except Exception as e:
                logger.debug(f"No extraction state in MinIO: {e}")

        # Return empty state if not found
        logger.info("No existing extraction state found, starting fresh")
        return ExtractionState(
            last_run='',
            extracted_files={},
            total_records=0,
            total_files=0
        )

    def save_extraction_state(self, state: ExtractionState) -> None:
        """
        Save extraction state to storage.

        Args:
            state: ExtractionState to save
        """
        # Update timestamps
        state.last_run = datetime.utcnow().isoformat() + 'Z'

        data = state.to_dict()

        # Save to local file
        state_path = self._get_state_path('bronze', 'extraction_state')
        state_path.parent.mkdir(parents=True, exist_ok=True)

        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved extraction state to {state_path}")

        # Save to MinIO if available
        if self.storage_client:
            try:
                object_path = self._get_state_object_path('bronze', 'extraction_state')
                self.storage_client.write_json('bronze', object_path, data)
                logger.info(f"Saved extraction state to MinIO: bronze/{object_path}")
            except Exception as e:
                logger.warning(f"Failed to save extraction state to MinIO: {e}")

    def load_processing_state(self) -> ProcessingState:
        """
        Load processing state from storage.

        Returns:
            ProcessingState object
        """
        state_path = self._get_state_path('silver', 'processing_state')

        # Try local file first
        if state_path.exists():
            try:
                with open(state_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"Loaded processing state from {state_path}")
                    return ProcessingState.from_dict(data)
            except Exception as e:
                logger.warning(f"Failed to load processing state from {state_path}: {e}")

        # Try MinIO if available
        if self.storage_client:
            try:
                object_path = self._get_state_object_path('silver', 'processing_state')
                data = self.storage_client.read_json('silver', object_path)
                logger.info(f"Loaded processing state from MinIO: silver/{object_path}")
                return ProcessingState.from_dict(data)
            except Exception as e:
                logger.debug(f"No processing state in MinIO: {e}")

        # Return empty state if not found
        logger.info("No existing processing state found, starting fresh")
        return ProcessingState(
            last_run='',
            processed_bronze_files=[],
            record_hashes_written=set(),
            total_records_processed=0,
            total_files_processed=0
        )

    def save_processing_state(self, state: ProcessingState) -> None:
        """
        Save processing state to storage.

        Args:
            state: ProcessingState to save
        """
        # Update timestamps
        state.last_run = datetime.utcnow().isoformat() + 'Z'

        data = state.to_dict()

        # Save to local file
        state_path = self._get_state_path('silver', 'processing_state')
        state_path.parent.mkdir(parents=True, exist_ok=True)

        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved processing state to {state_path}")

        # Save to MinIO if available
        if self.storage_client:
            try:
                object_path = self._get_state_object_path('silver', 'processing_state')
                self.storage_client.write_json('silver', object_path, data)
                logger.info(f"Saved processing state to MinIO: silver/{object_path}")
            except Exception as e:
                logger.warning(f"Failed to save processing state to MinIO: {e}")

    @staticmethod
    def compute_file_hash(file_path: Path) -> str:
        """
        Compute MD5 hash of a file.

        Args:
            file_path: Path to file

        Returns:
            MD5 hash string
        """
        md5 = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    md5.update(chunk)
            return md5.hexdigest()
        except Exception as e:
            logger.warning(f"Failed to compute hash for {file_path}: {e}")
            return ''

    @staticmethod
    def compute_content_hash(content: bytes) -> str:
        """
        Compute MD5 hash of content.

        Args:
            content: Bytes content

        Returns:
            MD5 hash string
        """
        return hashlib.md5(content).hexdigest()

    def should_extract_file(
        self,
        file_key: str,
        current_hash: str,
        extraction_state: ExtractionState
    ) -> bool:
        """
        Check if a file should be extracted (incremental logic).

        Args:
            file_key: Unique identifier for the file
            current_hash: Current hash of the file
            extraction_state: Current extraction state

        Returns:
            True if file should be extracted
        """
        if file_key not in extraction_state.extracted_files:
            logger.debug(f"File {file_key} is new, should extract")
            return True

        previous_hash = extraction_state.extracted_files[file_key].md5_hash
        if current_hash != previous_hash:
            logger.info(f"File {file_key} has changed (hash mismatch), should re-extract")
            return True

        logger.debug(f"File {file_key} already extracted and unchanged, skipping")
        return False

    def should_process_file(
        self,
        bronze_file_path: str,
        processing_state: ProcessingState
    ) -> bool:
        """
        Check if a Bronze file should be processed (incremental logic).

        Args:
            bronze_file_path: Path to Bronze file
            processing_state: Current processing state

        Returns:
            True if file should be processed
        """
        if bronze_file_path not in processing_state.processed_bronze_files:
            logger.debug(f"Bronze file {bronze_file_path} not yet processed")
            return True

        logger.debug(f"Bronze file {bronze_file_path} already processed, skipping")
        return False
