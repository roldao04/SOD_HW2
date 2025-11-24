"""
Open Contracting Partnership Data Extractor

Extracts OCDS (Open Contracting Data Standard) data from European publications
on the Open Contracting Partnership Data Registry.

License: Data is CC BY-NC-SA 4.0 (Non-commercial, Attribution, Share-alike)
"""

from .extractor import OCPExtractor
from .config import EUROPEAN_PUBLICATIONS, LICENSE_INFO

__version__ = "1.0.0"
__all__ = ["OCPExtractor", "EUROPEAN_PUBLICATIONS", "LICENSE_INFO"]
