"""
Configuration for Open Contracting Partnership data sources.

License: CC BY-NC-SA 4.0
- Attribution required
- Non-commercial use only
- Share-alike
"""

# European publications from Open Contracting Partnership Data Registry
EUROPEAN_PUBLICATIONS = {
    "uk_wales": {
        "publication_id": "119",
        "url": "https://data.open-contracting.org/en/publication/119",
        "country": "uk",
        "region": "wales",
        "name": "United Kingdom - Wales"
    },
    "uk_scotland": {
        "publication_id": "39",
        "url": "https://data.open-contracting.org/en/publication/39",
        "country": "uk",
        "region": "scotland",
        "name": "United Kingdom - Scotland"
    },
    "uk_main_1": {
        "publication_id": "128",
        "url": "https://data.open-contracting.org/en/publication/128",
        "country": "uk",
        "region": "national",
        "name": "United Kingdom"
    },
    "uk_main_2": {
        "publication_id": "41",
        "url": "https://data.open-contracting.org/en/publication/41",
        "country": "uk",
        "region": "national",
        "name": "United Kingdom 2"
    },
    "spain_national": {
        "publication_id": "89",
        "url": "https://data.open-contracting.org/en/publication/89",
        "country": "spain",
        "region": "national",
        "name": "Spain"
    },
    "spain_zaragoza": {
        "publication_id": "1",
        "url": "https://data.open-contracting.org/en/publication/1",
        "country": "spain",
        "region": "zaragoza",
        "name": "Spain - Zaragoza"
    },
    "germany": {
        "publication_id": "136",
        "url": "https://data.open-contracting.org/en/publication/136",
        "country": "germany",
        "region": "national",
        "name": "Germany"
    },
    "albania": {
        "publication_id": "134",
        "url": "https://data.open-contracting.org/en/publication/134",
        "country": "albania",
        "region": "national",
        "name": "Albania"
    },
    "croatia": {
        "publication_id": "80",
        "url": "https://data.open-contracting.org/en/publication/80",
        "country": "croatia",
        "region": "national",
        "name": "Croatia"
    },
    "italy": {
        "publication_id": "117",
        "url": "https://data.open-contracting.org/en/publication/117",
        "country": "italy",
        "region": "national",
        "name": "Italy"
    },
    "kosovo": {
        "publication_id": "115",
        "url": "https://data.open-contracting.org/en/publication/115",
        "country": "kosovo",
        "region": "national",
        "name": "Kosovo"
    }
}

# License information
LICENSE_INFO = {
    "name": "CC BY-NC-SA 4.0",
    "full_name": "Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International",
    "url": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
    "attribution": "Open Contracting Partnership",
    "source_url": "https://data.open-contracting.org/",
    "restrictions": [
        "Non-commercial use only",
        "Attribution required",
        "Share-alike"
    ]
}

# HTTP request configuration
REQUEST_CONFIG = {
    "user_agent": "SOD-HW2-EProcurement-System/1.0 (Educational Project)",
    "timeout": 30,
    "retry_attempts": 3,
    "retry_delay": 5,  # seconds
    "rate_limit_delay": 2  # seconds between requests
}
