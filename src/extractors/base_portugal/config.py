"""
Configuration for BASE Portugal data sources via dados.gov.pt.

License: Open Data License (dados.gov.pt)
- Attribution required
- Free for commercial and non-commercial use
"""

# Portugal publications from dados.gov.pt (Excel format from BASE Portal)
PORTUGAL_PUBLICATIONS = {
    "portugal_base": {
        "dataset_id": "contratos-publicos-portal-base-impic-contratos-de-2012-a-2025",
        "url": "https://dados.gov.pt/pt/datasets/contratos-publicos-portal-base-impic-contratos-de-2012-a-2025/",
        "api_url": "https://dados.gov.pt/api/1/datasets/contratos-publicos-portal-base-impic-contratos-de-2012-a-2025/",
        "country": "portugal",
        "region": "national",
        "name": "Portugal - BASE Portal (Contratos Públicos)",
        "description": "Public procurement contracts from BASE (IMPIC) 2012-2025",
        "data_range": "2012-2025",
        "format": "XLSX"
    }
}

# License information for dados.gov.pt
LICENSE_INFO = {
    "name": "Open Data License",
    "full_name": "dados.gov.pt Open Data License",
    "url": "https://dados.gov.pt/pt/datasets/ocds-portal-base-www-base-gov-pt/",
    "attribution": "IMPIC - Instituto dos Mercados Públicos, do Imobiliário e da Construção",
    "source_url": "https://www.base.gov.pt/base4",
    "portal": "dados.gov.pt",
    "restrictions": [
        "Attribution required",
        "Open data - free for commercial and non-commercial use"
    ]
}

# HTTP request configuration
REQUEST_CONFIG = {
    "user_agent": "SOD-HW2-EProcurement-System/1.0 (Educational Project)",
    "timeout": 60,  # Larger timeout for potentially large files
    "retry_attempts": 3,
    "retry_delay": 5,  # seconds
    "rate_limit_delay": 2  # seconds between requests
}

# dados.gov.pt API endpoints
DADOS_API_BASE = "https://dados.gov.pt/api/1"
DADOS_DATASETS_ENDPOINT = f"{DADOS_API_BASE}/datasets"

# OCDS data download patterns
# The actual download URLs will be discovered via the API
# Typical pattern: https://dados.gov.pt/s/resources/{resource_id}/...
OCDS_DOWNLOAD_PATTERN = "ocds-portal-base"
