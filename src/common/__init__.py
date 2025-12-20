"""
Common utilities shared across extractors and processors.

This module provides reusable components for:
- State tracking (extraction and processing state)
- Data quality validation
- Deduplication logic
- Manifest file management
"""

from .state_manager import StateManager, ExtractionState, ProcessingState, FileState
from .quality_validator import QualityValidator, QualityReport
from .deduplication import DeduplicationManager
from .manifest_writer import ManifestWriter

__all__ = [
    'StateManager',
    'ExtractionState',
    'ProcessingState',
    'FileState',
    'QualityValidator',
    'QualityReport',
    'DeduplicationManager',
    'ManifestWriter',
]
