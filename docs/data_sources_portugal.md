# Data Source Validation (Portugal E-Procurement)

## BASE - Portal Base
**https://www.base.gov.pt/base4/**

- Contracts search (https://www.base.gov.pt/Base4/pt/pesquisa/?type=contratos)
- Open data (OCDS format) (https://dados.gov.pt/pt/datasets/ocds-portal-base-www-base-gov-pt/)
- Open data API documentation (https://dados.gov.pt/en/docapi/)
- Portal managed by IMPIC (Instituto dos Mercados Públicos, do Imobiliário e da Construção)
- Contracts from 2012 to 2025 available

**Details**

API Available (Restricted)
- API exists but requires registration and prior authorization from IMPIC
- Request access through Help Topic "Contratos Públicos/Pedido de acesso à API Portal Base"
- Open data alternative available at dados.gov.pt in OCDS format (no authorization required)
- OCDS dataset updated regularly with BASE portal data

Data Access Options
- ✔ Public web interface for searching contracts
- ✔ Open Data Portal (dados.gov.pt) - OCDS format, no authorization needed
- ✔ Restricted API - requires IMPIC authorization for bulk data extraction
- ✔ Search by contract object, announcements, or entities

Technical Considerations
- Open Data Portal recommended for automated extraction (no authorization barriers)
- OCDS format provides standardized structure
- Web scraping possible but Open Data Portal is preferred method
- API authorization process required for direct BASE API access

## ComprasPT
**https://compraspt.com/**

- Main portal (https://compraspt.com/home/)
- English version (https://compraspt.com/home/en/home-en/)
- +Concursos Públicos service (https://compraspt.com/home/produto/mais-concursos-publicos-1-ano/)
- One of five licensed electronic public procurement platforms in Portugal

**Details**

Commercial Platform
- No public API available
- WordPress-based platform (v6.4.3) with WooCommerce
- Elementor page builder with jQuery/JavaScript frontend
- Service filters and identifies tenders from all Portuguese e-procurement platforms

Access Levels
- Public: Service descriptions, contact info, general information
- Login required: Tender listings, buyer/seller platforms, bid submissions
- Platform URLs follow pattern: `https://www.compraspt.com/cpt-[entity]/faces/`

Scraping Possibilities
- ✔ Public pages can be scraped (service info, contacts)
- ✘ Tender data requires login authentication
- ✘ WordPress/WooCommerce structure with AJAX endpoints
- ⚠ Most procurement data behind authentication

Technical Considerations
- WordPress REST API endpoints available (`/wp-json/`)
- Internal AJAX endpoints (`/wp-admin/admin-ajax.php`)
- Session-based authentication required for tender access
- Entity-specific subdomains (cpt-[entity])

## Vortal Gov
**https://www.vortal.biz/pt-pt/vortal-gov/**

- Portuguese version: https://www.vortal.biz/pt-pt/vortal-gov/
- English version: https://www.vortal.biz/vortalgov/
- Spanish version: https://www.vortal.biz/es/vortal-gov/
- One of five licensed electronic public procurement platforms in Portugal
- Electronic public procurement system for public entities

**Details**

Restricted Access Platform
- No public API documentation found
- Platform designed for institutional users (public entities)
- Multilingual support (Portuguese, English, Spanish)
- Manages purchase and sales processes for public organizations

Access
- Institutional access only (public entities)
- No open browse access to tenders
- Entity-restricted login system
- Not designed for public data extraction

Scraping Possibilities
- ✘ Tender content is NOT publicly accessible
- ✘ Institutional authentication required
- ✔ Only corporate/marketing pages publicly visible
- ✘ Not suitable for automated data extraction

Technical Considerations
- Site primarily technical markup (CSS, fonts, analytics)
- No visible API endpoints or documentation
- Platform designed for authorized entity use
- Not recommended for public data pipeline

## AcinGov
**https://www.acingov.pt/acingovprod/2/**

- Login/Registration: `/zonaPublica/zona_publica_c/adesao`
- Procedures: `/zonaPublica/zona_publica_c/indexProcedimentos`
- Characteristics: `/zonaPublica/zona_publica_c/carateristicas`
- Help: `/zonaPublica/zona_publica_c/ajuda`
- Contact: apoio@acingov.pt / Phone: 707 451 451
- One of five licensed electronic public procurement platforms in Portugal

**Details**

Municipal Platform Statistics
- 26,912 active procedures
- €2.9 trillion total awarded (cumulative)
- Platform used by Portuguese municipalities
- Two-zone architecture: Public Zone + Authenticated Zone

Technology Stack
- CodeIgniter framework (evident from URL patterns)
- jQuery, AJAX, Bootstrap
- Plupload file manager
- Session-based authentication (cookies + CSRF tokens)

API and Data Access
- No public API available
- AJAX calls to internal endpoints (`/login_c/`, `/plupload_c/`)
- POST requests for authentication
- Proprietary system without published REST/GraphQL APIs

Scraping Possibilities
- ✔ Public procurement listings searchable
- ✔ Procurement statistics publicly visible
- ✔ Participating entities information available
- ✘ Bid submissions and detailed documents require authentication
- ⚠ Data availability varies by municipality

Technical Considerations
- Each municipality may have separate instance
- Relatively standard HTML structure
- Session management with CSRF tokens
- Public zone allows browsing active procedures
- Authentication required for detailed procurement documents

## Summary Table

| Platform | API | Open Data | Public Data | Scraping Difficulty | Notes |
|----------|-----|-----------|-------------|-------------------|-------|
| BASE | ✔ Restricted* | ✔ OCDS | ✔ Full | 🟢 Easy** | Main state portal. OCDS open data available |
| ComprasPT | ❌ | ❌ | ✔ Minimal | 🟥 Hard | Service platform. Tender data requires login |
| Vortal Gov | ❌ | ❌ | ✘ | 🟥 Very Hard | Institutional only. Not suitable for extraction |
| AcinGov | ❌ | ❌ | ✔ Partial | 🟧 Medium | Municipal platform. Public listings available |

*Requires IMPIC authorization | **Use dados.gov.pt Open Data Portal instead of scraping

## Recommendations

### Priority 1: BASE Portal via Open Data
**Use dados.gov.pt OCDS dataset**
- ✅ No authorization required
- ✅ Standardized OCDS format
- ✅ Most comprehensive data (2012-2025)
- ✅ API available with documentation
- ✅ Official government source (IMPIC)
- ✅ Regular updates

### Priority 2: BASE Portal Direct API (Optional)
**If bulk extraction needed**
- Requires IMPIC authorization request
- Use only if Open Data Portal is insufficient
- Approval process via BASE help system

### Priority 3: AcinGov (Supplementary)
**Municipal level data**
- Useful for local government contracts
- Public listings available without login
- 26,912+ active procedures
- May require mapping municipal instances

### Not Recommended
- **ComprasPT**: Tender data requires authentication, limited value
- **Vortal Gov**: Institutional access only, not suitable for extraction

## Legal Considerations

**For dados.gov.pt (BASE Open Data):**
- ✓ Open data - designed for public consumption
- ✓ Check license terms on dataset page
- ✓ Attribution to IMPIC/BASE Portal required
- ✓ Complies with Portuguese open data policies

**For Web Scraping (if used):**
- ✓ Verify terms of service for each platform
- ✓ Implement rate limiting and respectful crawling
- ✓ Check robots.txt compliance
- ✓ Ensure data usage complies with Portuguese GDPR/data protection laws
- ✓ Prefer official data sources (dados.gov.pt) over scraping

**General:**
- ✓ Attribute all data sources properly
- ✓ Request official API access when available (BASE API requires IMPIC authorization)
- ✓ Respect platform usage policies

## References and Sources

### BASE Portal
- [Portal Base](https://www.base.gov.pt/base4)
- [Contracts Search](https://www.base.gov.pt/Base4/pt/pesquisa/?type=contratos)
- [API Announcement](https://www.base.gov.pt/Base4/pt/noticias/2025/api-para-consulta-de-dados-do-portal-base/)
- [OCDS Open Data](https://dados.gov.pt/pt/datasets/ocds-portal-base-www-base-gov-pt/)
- [dados.gov.pt API Documentation](https://dados.gov.pt/en/docapi/)

### ComprasPT
- [ComprasPT Home](https://compraspt.com/home/)
- [+Concursos Públicos Service](https://compraspt.com/home/produto/mais-concursos-publicos-1-ano/)

### Vortal Gov
- [Vortal Gov (PT)](https://www.vortal.biz/pt-pt/vortal-gov/)

### AcinGov
- [AcinGov Portal](https://www.acingov.pt/acingovprod/2/)
- Contact: apoio@acingov.pt / 707 451 451

### Additional Resources
- [Licensed E-Procurement Platforms in Portugal](https://alertaconcursospublicos.pt/plataformas-eletronicas-de-contratacao-publica/)
- IMPIC - Instituto dos Mercados Públicos, do Imobiliário e da Construção

## Technical Architecture Recommendations

### Recommended Approach: Use BASE Open Data (dados.gov.pt)

**Primary Data Source:**
```python
# Use dados.gov.pt API for OCDS data
# API Documentation: https://dados.gov.pt/en/docapi/
# Dataset: https://dados.gov.pt/pt/datasets/ocds-portal-base-www-base-gov-pt/

Strategy:
1. Use dados.gov.pt API to fetch OCDS data
2. OCDS format already standardized (no parsing needed)
3. Schedule daily/weekly updates
4. Store OCDS JSON directly (Bronze layer)
5. Transform to internal schema (Silver layer)
```

**Advantages:**
- No scraping required
- No authorization barriers
- Standardized format (OCDS)
- Official data source
- API documented and maintained

### Supplementary: AcinGov Extraction

```python
# For municipal-level supplement only
Strategy:
1. Identify target municipalities
2. HTTP requests to public procedure listings
3. Parse HTML with BeautifulSoup
4. Store as supplementary source
5. Deduplicate with BASE data
```

### Data Pipeline Architecture

```
┌─────────────────────────────────────────────────────────┐
│ BRONZE LAYER (Raw Data)                                 │
├─────────────────────────────────────────────────────────┤
│ • BASE OCDS JSON (from dados.gov.pt API)                │
│ • AcinGov HTML (optional supplement)                    │
│ • Store as-is with timestamp                            │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ SILVER LAYER (Processed)                                │
├─────────────────────────────────────────────────────────┤
│ • Parse OCDS to internal schema                         │
│ • Extract entities, dates, values                       │
│ • Normalize formats                                     │
│ • Deduplicate across sources                            │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ GOLD LAYER (Analytics)                                  │
├─────────────────────────────────────────────────────────┤
│ • Entity relationship graphs                            │
│ • Time series aggregations                              │
│ • Value metrics and statistics                          │
│ • Ready for BI/visualization                            │
└─────────────────────────────────────────────────────────┘
```
