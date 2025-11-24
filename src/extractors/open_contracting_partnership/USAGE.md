# Open Contracting Partnership Extractor - Usage Guide

## Quick Start

Run the interactive menu:

```bash
cd /home/roldao/Desktop/MEI/SOD/hw2
python3 -m src.extractors.open_contracting_partnership.main
```

## Menu Options

### Extract All Publications
- Press `A` and Enter
- Enter year (default: 2025)
- Wait for all 11 publications to be extracted
- Results will be saved to the Bronze layer

### Extract Single Publication
- Press a number `1-11` and Enter
- Enter year (default: 2025)
- Wait for extraction to complete

### Exit
- Press `0` and Enter

## Available Publications

1. United Kingdom - Wales
2. United Kingdom - Scotland
3. United Kingdom
4. United Kingdom 2
5. Spain
6. Spain - Zaragoza
7. Germany
8. Albania
9. Croatia
10. Italy
11. Kosovo

## Data Location

Extracted data is saved to:
```
data/bronze/open_contracting_partnership/{country}/{YYYY}/{MM}/{DD}/records_{timestamp}.json
```

## License

All data is licensed under **CC BY-NC-SA 4.0** with proper attribution included in each file.
