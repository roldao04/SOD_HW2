# European Public Procurement Multi-Source Data Integration System
## A Medallion Architecture Data Pipeline with NLP Query Interface

**Academic Report**

---

## METADATA

**Course**: Data Oriented and Systems (SOD)
**Institution**: University of Aveiro
**Academic Year**: 2024/2025
**Assignment**: HW 2.2 - European Public Procurement Multi-Source Data Integration
**Date**: December 2025

**Team Members**:
- João Roldão (113920)
- Hugo Castro (113889)

---

## TABLE OF CONTENTS

1. Abstract
2. Introduction
3. System Architecture
4. Data Sources & Integration
5. Data Pipeline Implementation
6. Query Engine & SQL Analytics
7. NLP Chatbot Implementation
8. Automation & Orchestration
9. Results & Evaluation
10. Technical Challenges & Solutions
11. Conclusions
12. References
13. Appendices

---

# 1. ABSTRACT

European public procurement data remains fragmented across multiple national and international platforms, hindering transparency and market access for businesses. This project addresses this challenge by developing a comprehensive multi-source data integration system that aggregates, standardizes, and provides intelligent querying capabilities for European procurement tender data. The system implements a medallion architecture pattern, organizing data into three progressive layers: Bronze (raw data preservation), Silver (cleaned and standardized), and Gold (analytics-ready datasets). Four primary data sources were integrated: the Open Contracting Partnership (462,226 records from 7 countries), BASE Portugal via dados.gov.pt (58,418 records), TED Europe (16,895 records), and supplementary partner data (203 records), resulting in a unified dataset of 536,778 procurement records spanning 38 European countries from 2016 to 2025. Data standardization was achieved through alignment with the Open Contracting Data Standard (OCDS), establishing a unified 27-field schema across all sources. The infrastructure leverages MinIO for scalable S3-compatible object storage, Dremio as a distributed SQL query engine, and Docker Compose for containerized orchestration. A novel contribution is the integration of a dual Large Language Model (LLM) system using Google Gemini (2.0 Flash and 2.5 Pro) to provide natural language query capabilities, enabling non-technical users to generate SQL queries and analytical insights through conversational interfaces. The system achieves a 10:1 storage compression ratio through Apache Parquet columnar format, sub-second query response times for cached queries, and automated daily pipeline execution. This work demonstrates the feasibility of unified European procurement data access and establishes a foundation for enhanced transparency and market analysis in public spending.

---

# 2. INTRODUCTION

## 2.1 Context and Motivation

Public procurement represents a significant portion of government expenditure across the European Union, accounting for approximately 14% of GDP or roughly €2 trillion annually. Transparency in procurement processes is essential for preventing corruption, ensuring fair competition, and enabling efficient allocation of public resources. The Open Contracting Data Standard (OCDS) has emerged as the global standard for publishing structured, machine-readable procurement data, facilitating greater accountability and data-driven analysis of public spending patterns.

Despite the existence of data standards and various national procurement platforms, European procurement data remains highly fragmented. Each member state maintains its own procurement systems, often with multiple regional or municipal platforms operating independently. This fragmentation creates significant barriers for businesses seeking cross-border opportunities and for researchers attempting to analyze procurement patterns at the European level.

## 2.2 Problem Statement

The current landscape of European procurement data presents several critical challenges. First, procurement records are scattered across numerous platforms operated by different governmental entities, including national portals (such as Portugal's BASE), international initiatives (TED - Tenders Electronic Daily), and various municipal systems. Second, despite the adoption of OCDS by many jurisdictions, implementations vary significantly in completeness and quality, with inconsistent field mappings and missing data elements. Third, technical barriers prevent non-expert users from accessing and analyzing this data, as most platforms require knowledge of SQL or specialized query languages.

These challenges result in information asymmetry, where large organizations with dedicated procurement teams can effectively navigate multiple platforms, while small and medium-sized enterprises struggle to identify relevant opportunities. Additionally, researchers and policymakers lack tools for comprehensive cross-country analysis of procurement trends, hindering evidence-based policy development.

## 2.3 Project Objectives

This project addresses the fragmentation challenge through six primary objectives:

1. **Multi-Source Integration**: Aggregate data from at least three diverse European procurement sources, exceeding the minimum requirement to demonstrate generalizability of the integration approach.

2. **Data Standardization**: Establish a unified data schema based on OCDS, enabling consistent representation of procurement records regardless of source, while accommodating source-specific variations through flexible field mappings.

3. **Scalable Architecture**: Implement a medallion architecture data lake capable of processing millions of records, supporting future expansion to additional data sources and countries.

4. **SQL Analytics**: Deploy a distributed query engine (Dremio) to enable high-performance analytical queries across the unified dataset, leveraging modern columnar storage formats for optimization.

5. **Natural Language Interface**: Develop an LLM-powered chatbot system that translates natural language questions into validated SQL queries and generates analytical insights, democratizing access to procurement data for non-technical users.

6. **Pipeline Automation**: Create automated extraction, transformation, and loading (ETL) processes with incremental update capabilities, ensuring data freshness without manual intervention.

## 2.4 Scope and Limitations

The system's scope encompasses tender and contract award data from 38 European countries, spanning the period from 2016 to 2025. Four primary data sources were selected based on availability, data quality, and geographic coverage: the Open Contracting Partnership portal (providing access to 11 national datasets), Portugal's BASE platform via the dados.gov.pt open data API, TED Europe data obtained through partner collaboration, and supplementary Portuguese data from Henrique & Monteiro.

Several limitations constrain this work. The system focuses exclusively on tender announcements and contract awards, excluding other procurement lifecycle stages such as planning, execution, and performance evaluation. Data completeness varies across sources, with some records lacking critical fields such as tender values or buyer information. The natural language query interface is limited to read-only operations and English language inputs. As an academic prototype, the system has not undergone production hardening for enterprise-scale deployment, security auditing, or compliance certification.

## 2.5 Report Structure

The remainder of this report is organized as follows. Chapter 3 presents the system architecture, detailing the medallion pattern implementation and infrastructure components. Chapter 4 describes the data sources and integration methodology, including OCDS alignment strategies. Chapter 5 provides technical details of the data pipeline implementation across Bronze, Silver, and Gold layers. Chapter 6 explains the query engine configuration and SQL analytics capabilities. Chapter 7 presents the NLP chatbot implementation, including prompt engineering techniques and safety mechanisms. Chapter 8 describes automation and orchestration approaches. Chapter 9 evaluates results with quantitative metrics. Chapter 10 discusses technical challenges encountered and solutions adopted. Chapter 11 concludes with achievements and reflections on lessons learned.

---

# 3. SYSTEM ARCHITECTURE

## 3.1 Architecture Overview

The system architecture follows a layered design that separates concerns across extraction, storage, processing, querying, and presentation layers. This separation enables independent scaling, maintenance, and evolution of each component while maintaining clear interfaces between layers. The architecture adheres to three core design principles: scalability through distributed systems and columnar storage formats, maintainability through modular component design and containerization, and extensibility through abstraction of source-specific logic and standardized data schemas.

Figure 1 illustrates the high-level system architecture. Data flows from heterogeneous sources through dedicated extractors into a MinIO-based data lake organized into Bronze, Silver, and Gold layers. The Dremio query engine provides SQL access to processed data, while a FastAPI-based application layer offers both traditional REST endpoints and natural language query capabilities through LLM integration.

```
Figure 1: Overall System Architecture

┌─────────────────────────────────────────────────────────────┐
│  DATA SOURCES                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ OCP (11 pubs)│  │BASE Portugal │  │  TED Europe  │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
          ↓                  ↓                  ↓
┌─────────────────────────────────────────────────────────────┐
│  EXTRACTION LAYER (Python)                                  │
│  • HTTP/API clients  • Rate limiting  • State management    │
└──────────────────────────┬──────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  BRONZE LAYER (MinIO S3 Storage)                            │
│  • Raw JSON (OCDS format)  • 2,447 files  • Partitioned     │
└──────────────────────────┬──────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  PROCESSING LAYER (Python + Pandas + PyArrow)               │
│  • Schema mapping  • Validation  • Transformation           │
└──────────────────────────┬──────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  SILVER LAYER (MinIO S3 Storage)                            │
│  • Parquet format  • 1,097 files  • Unified 27-field schema │
└──────────────────────────┬──────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  GOLD PROCESSOR (Unification + Aggregation)                 │
│  • Multi-source merge  • Deduplication  • Derived fields    │
└──────────────────────────┬──────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  GOLD LAYER (MinIO S3 Storage)                              │
│  • Unified dataset (536K records)  • Pre-computed aggregates│
└──────────────────────────┬──────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  DREMIO QUERY ENGINE                                        │
│  • Arrow Flight protocol  • SQL interface  • Optimization   │
└──────────┬──────────────────────────┬───────────────────────┘
           ↓                          ↓
┌────────────────────┐    ┌─────────────────────────────────┐
│  REST API          │    │  NLP CHATBOT API                │
│  (Traditional SQL) │    │  • Query Creator (Gemini 2.0)   │
└────────────────────┘    │  • Analytics (Gemini 2.5 Pro)   │
                          └─────────────────────────────────┘
```

## 3.2 Medallion Architecture Pattern

The medallion architecture pattern, pioneered by Databricks for data lake implementations, organizes data into three progressive quality tiers. This pattern was selected for several strategic reasons. First, it preserves data lineage by maintaining immutable raw data in the Bronze layer, enabling reprocessing if transformation logic evolves. Second, it establishes clear quality gates between layers, ensuring that only validated data progresses to Silver and that only business-ready datasets reach Gold. Third, it supports incremental processing by allowing each layer to be updated independently based on new source data.

The Bronze layer stores data exactly as received from sources, in JSON format matching OCDS structure. No transformations are applied at this stage beyond basic serialization. Files are partitioned by source, country, and date (year/month/day) to enable efficient incremental extraction and provide clear data lineage. As of the most recent pipeline execution, the Bronze layer contained 2,447 JSON files representing the complete history of extracted records.

The Silver layer applies schema normalization, data cleaning, and validation. All source-specific OCDS implementations are mapped to a unified 27-field schema, with null handling, type coercion, and format standardization applied consistently. Apache Parquet columnar format with Snappy compression replaces JSON, reducing storage footprint by approximately 10:1 while enabling efficient column-pruning in downstream queries. Partitioning shifts to source/country/year/month granularity. The Silver layer currently comprises 1,097 Parquet files.

The Gold layer consolidates Silver sources into a single unified dataset, applies cross-source deduplication, and generates pre-computed aggregates for common analytical queries. Category standardization translates multi-language procurement categories (Portuguese, Albanian, etc.) into English equivalents. Derived fields such as year, month, quarter, and data quality flags are added to support temporal analysis and quality filtering. Five aggregate datasets (country summary, monthly trends, category analysis, top buyers, and top suppliers) enable sub-second query response for dashboard use cases.

Figure 2 illustrates the medallion pattern data flow, showing quality improvement and transformation at each tier.

```
Figure 2: Medallion Pattern Data Flow

BRONZE (Raw)           SILVER (Cleaned)         GOLD (Analytics)
═════════════          ═══════════════          ════════════════
┌───────────┐          ┌───────────┐           ┌──────────────┐
│Raw JSON   │──────>──→│Unified    │──────>──→│Deduplicated  │
│OCDS format│ Transform│Schema     │  Merge   │Unified       │
│2,447 files│          │Parquet    │          │536K records  │
│           │          │1,097 files│          │              │
│No changes │          │Validated  │          │Standardized  │
│to data    │          │Cleaned    │          │categories    │
│           │          │           │          │              │
│Partitioned│          │Partitioned│          │+ Aggregates: │
│by date    │          │by month   │          │  - Country   │
│(daily)    │          │           │          │  - Monthly   │
│           │          │27 fields  │          │  - Category  │
└───────────┘          └───────────┘          │  - Top N     │
                                              └──────────────┘

Quality Gates:
Bronze→Silver:        Silver→Gold:
• Schema mapping      • Deduplication
• Type validation     • Multi-language std.
• Required fields     • Derived fields
• Data cleaning       • Aggregation
```

## 3.3 Infrastructure Components

### 3.3.1 MinIO (Data Lake Storage)

MinIO provides S3-compatible object storage, selected for three primary reasons. First, its S3 API compatibility ensures portability to cloud providers (AWS S3, Google Cloud Storage) without code changes, while enabling local development and cost-effective self-hosted deployment. Second, MinIO scales horizontally through distributed deployment, supporting petabyte-scale data lakes when required. Third, unlike managed cloud storage, MinIO eliminates egress costs and provides full data sovereignty.

The system deploys MinIO with three buckets corresponding to medallion layers: `bronze/`, `silver/`, and `gold/`. Each bucket employs hierarchical partitioning schemes optimized for access patterns. Bronze uses `source/country/year/month/day` to support incremental extraction. Silver employs `source/country/year/month` for balanced partition size. Gold stores unified and aggregate datasets without further partitioning, as these are queried holistically. As of the latest pipeline execution, the three buckets collectively store approximately 1.3 GB of data, achieving significant compression through Parquet format in Silver and Gold layers.

### 3.3.2 Dremio (Query Engine)

Dremio serves as the distributed SQL query engine, providing lakehouse capabilities over MinIO object storage. Selection of Dremio was driven by four key capabilities. First, Apache Arrow Flight protocol enables high-performance data transfer between Dremio and client applications, with zero-copy operations and columnar data representation. Second, Dremio's query optimizer applies predicate pushdown and partition pruning automatically, reducing I/O by eliminating unnecessary data scans. Third, reflections (materialized views) can accelerate frequently-executed aggregation queries, though the current implementation relies on Gold layer pre-aggregation rather than Dremio reflections. Fourth, Dremio's web interface provides SQL development capabilities for data analysts unfamiliar with command-line tools.

The deployment configures Dremio with MinIO as a data source, using S3-compatible connection parameters. Path-style access and proper endpoint configuration (`http://minio:9000` within the Docker network) enable seamless integration. Dremio's metadata refresh mechanism synchronizes schema changes when new Parquet files are added to MinIO buckets.

### 3.3.3 Docker Compose Orchestration

Docker Compose orchestrates four containerized services: MinIO, Dremio, chatbot-api, and scheduler. This approach provides several advantages over manual deployment. Services are defined declaratively in `docker-compose.yml`, ensuring reproducible deployments across development and demonstration environments. Health checks monitor service availability, with automatic restart policies recovering from transient failures. A dedicated Docker network (`sod-network`) enables service discovery by name, allowing the chatbot API to connect to Dremio at `dremio:32010` without hardcoded IP addresses. Volume mounts persist data across container restarts: `minio_data` for object storage and `dremio_data` for metadata.

Figure 3 shows the container architecture and dependencies. The scheduler and chatbot-api both depend on Dremio, which in turn depends on MinIO, ensuring correct startup sequencing.

```
Figure 3: Container Architecture

Docker Host
├── Network: sod-network
│   ├── MinIO (port 9000:9000, 9001:9001)
│   │   └── Volume: minio_data → /data
│   │
│   ├── Dremio (port 9047:9047, 32010:32010)
│   │   ├── Depends on: MinIO
│   │   └── Volume: dremio_data → /opt/dremio/data
│   │
│   ├── Chatbot API (port 8000:8000)
│   │   ├── Depends on: Dremio
│   │   └── Environment: GEMINI_API_KEY, DREMIO_HOST=dremio
│   │
│   └── Scheduler (no exposed ports)
│       ├── Depends on: Dremio, MinIO
│       └── Volume: ./data → /app/data
│
└── Shared Volumes
    ├── minio_data (persistent object storage)
    └── dremio_data (persistent metadata catalog)
```

## 3.4 Technology Stack

Table 1 summarizes the technology stack with justifications for each selection. The stack prioritizes Python for its rich data processing ecosystem, open-source components for cost efficiency and transparency, and standards-based formats (Parquet, Arrow) for interoperability.

**Table 1: Technology Stack Summary**

| Category | Technology | Version | Justification |
|----------|-----------|---------|---------------|
| **Programming** | Python | 3.10+ | Rich data processing libraries, extensive LLM SDK support |
| **Data Processing** | Pandas | 2.x | Industry-standard DataFrame operations, wide adoption |
| | PyArrow | 14.x | Parquet I/O, Arrow Flight client, schema enforcement |
| **Storage** | MinIO | Latest | S3-compatible, self-hosted, horizontal scalability |
| | Apache Parquet | 2.0 | Columnar format, compression, schema evolution |
| **Query Engine** | Dremio | OSS | Lakehouse architecture, Arrow Flight, optimizer |
| **API Framework** | FastAPI | 0.109.0 | Async support, automatic OpenAPI docs, type validation |
| | Uvicorn | 0.27.0 | Production-grade ASGI server, performance |
| **LLM Integration** | Google Gemini | 2.0 Flash | Cost-effective SQL generation, low latency |
| | Google Gemini | 2.5 Pro | Advanced reasoning for analytics generation |
| **Orchestration** | Docker Compose | 2.x | Multi-container management, reproducible deployment |
| | Python schedule | 1.2.0 | Lightweight job scheduling, cron-like syntax |
| **Validation** | Pydantic | 2.6.0 | Runtime type validation, data model definitions |
| | sqlparse | 0.4.4 | SQL parsing, injection prevention |

## 3.5 Data Flow

The end-to-end data flow comprises four phases: extraction, transformation, aggregation, and querying. In the extraction phase, Python-based extractors make HTTP requests to source APIs or read static datasets, serialize responses as OCDS-compliant JSON, and write files to MinIO's Bronze bucket with appropriate partitioning. State management tracks extraction progress to enable incremental updates on subsequent runs.

The transformation phase reads Bronze JSON files, applies source-specific field mappings to extract values into the unified 27-field schema, validates required fields and data types, cleans values (trimming whitespace, normalizing nulls, standardizing formats), and writes validated records as Snappy-compressed Parquet files to the Silver bucket. Processing occurs incrementally, with state files tracking which Bronze files have been successfully transformed.

The aggregation phase merges all Silver source tables into a single DataFrame, adds a source column to preserve provenance, applies category standardization mappings to translate non-English categories, deduplicates records using composite keys (OCID + source_publication_id), adds derived fields (year, month, quarter, quality flags), generates five pre-computed aggregate datasets, and writes both the unified dataset and aggregates to the Gold bucket.

The querying phase begins when Dremio's metadata catalog is refreshed to discover new Gold layer files, after which datasets are formatted (Parquet schema inference), enabling SQL queries via Dremio's web UI or Arrow Flight API. The NLP chatbot invokes Dremio programmatically, translating natural language to SQL and executing queries to generate insights.

Figure 4 illustrates this end-to-end flow.

```
Figure 4: Detailed Data Flow

┌─────────────┐
│Source APIs  │
└──────┬──────┘
       │ HTTPS/JSON
       ↓
┌─────────────┐
│ Extractors  │  Incremental: Check state → Fetch new records only
└──────┬──────┘
       │ Write JSON
       ↓
┌─────────────┐
│Bronze Layer │  Partitioning: source/country/year/month/day
│ (MinIO)     │  Format: OCDS JSON
└──────┬──────┘
       │ Read JSON
       ↓
┌─────────────┐
│ Processors  │  Transform: Map to unified schema → Validate → Clean
└──────┬──────┘
       │ Write Parquet
       ↓
┌─────────────┐
│Silver Layer │  Partitioning: source/country/year/month
│ (MinIO)     │  Format: Parquet (Snappy), 27-field schema
└──────┬──────┘
       │ Read all sources
       ↓
┌─────────────┐
│Gold Processor│ Unify: Merge + Deduplicate + Standardize → Aggregate
└──────┬──────┘
       │ Write unified + aggregates
       ↓
┌─────────────┐
│ Gold Layer  │  Datasets: 1 unified + 5 aggregates
│ (MinIO)     │  Format: Parquet, optimized for queries
└──────┬──────┘
       │ Metadata refresh
       ↓
┌─────────────┐
│  Dremio     │  Query optimization: Predicate pushdown, pruning
└──────┬──────┘
       │ Arrow Flight / SQL
       ↓
┌─────────────┐
│ Applications│  REST API + NLP Chatbot
└─────────────┘
```

---

# 4. DATA SOURCES & INTEGRATION

## 4.1 Source Selection Criteria

Data source selection was conducted through a systematic evaluation methodology during an initial validation phase (Phase 0). Four primary selection criteria guided the decision-making process. First, API availability and documentation quality determined the feasibility of automated extraction, with preference given to sources offering RESTful APIs or downloadable bulk datasets over those requiring web scraping. Second, adherence to the Open Contracting Data Standard (OCDS) was prioritized, as standardized schemas significantly reduce transformation complexity and improve data quality. Third, geographic coverage and record volume were assessed to maximize the breadth of European procurement data captured. Fourth, data quality indicators such as field completeness, temporal coverage, and update frequency were evaluated through sample analysis.

The validation phase involved testing candidate sources to verify API functionality, assess data structure, and measure extraction feasibility. Sources requiring authentication without clear public access pathways were deprioritized due to access sustainability concerns. This methodical approach resulted in the selection of four complementary sources that collectively provide broad European coverage while maintaining data standardization through OCDS compliance.

## 4.2 Open Contracting Partnership

The Open Contracting Partnership (OCP) operates a global data portal providing access to procurement datasets published in OCDS format by governments and public institutions worldwide. The portal, accessible at https://data.open-contracting.org/, serves as the largest single source of standardized procurement data for this project, contributing 462,226 records across seven European countries.

Eleven individual publications were integrated from the OCP portal, spanning multiple jurisdictions: Germany (1 publication), United Kingdom (4 publications covering national, Wales, Scotland, and additional national datasets), Italy (1 publication), Spain (2 publications including national and Zaragoza municipal data), Croatia (1 publication), Kosovo (1 publication), and Albania (1 publication). Each publication represents a distinct procurement authority or aggregated national dataset, with temporal coverage varying by jurisdiction but generally spanning 2016 to 2025.

The primary advantage of OCP data lies in its strict OCDS compliance. All datasets conform to the OCDS Release Package schema, providing consistent field structures across jurisdictions despite varying implementations. Data access is provided through direct bulk download links for JSON files, eliminating API rate limit concerns and enabling efficient batch extraction. Each publication page provides metadata including update frequency, record counts, and licensing terms (typically CC BY-NC-SA 4.0, requiring attribution and restricting commercial use).

Data quality assessment during the validation phase revealed generally high completeness for core fields (tender title, buyer, dates) but variable completeness for optional fields such as award amounts and supplier information. The standardized format significantly reduced extraction complexity compared to non-OCDS sources, requiring only minor variations in field path mappings across different OCP publications.

## 4.3 BASE Portugal (dados.gov.pt)

BASE (Base de Aquisições e Serviços do Estado) serves as Portugal's national public procurement portal, operated by IMPIC (Instituto dos Mercados Públicos, do Imobiliário e da Construção). While the primary BASE portal (https://www.base.gov.pt/) requires registration and authorization for API access, procurement data is made publicly available through Portugal's open data portal at dados.gov.pt in OCDS format, providing 58,418 procurement records spanning 2012 to 2025.

The dados.gov.pt platform exposes BASE data through a RESTful API documented at https://dados.gov.pt/en/docapi/. The OCDS dataset (resource ID: "ocds-portal-base-www-base-gov-pt") supports pagination, filtering, and field selection through query parameters. API requests follow the pattern `https://dados.gov.pt/api/1/datasets/{dataset-id}/resources/{resource-id}/data?page=1&page_size=100`, with responses structured as JSON containing OCDS release packages.

An incremental extraction strategy was implemented to minimize redundant data transfers and respect API rate limits. Each extraction session queries records with publication dates newer than the last successful extraction timestamp, tracked in a state file (`extraction_state.json`). The API returns records in chronological order, enabling efficient pagination until no additional records are found. This approach reduced initial extraction time while supporting daily updates to capture new tenders.

Field completeness analysis revealed strong coverage for tender metadata (title, buyer, publication date) with over 95% population rates, but lower completeness for award-stage data (supplier names, contract values) at approximately 60-70%. The Portuguese language procurement categories required standardization mapping to English equivalents during Silver layer processing.

## 4.4 TED (Tenders Electronic Daily)

Tenders Electronic Daily (TED) is the official publication portal for European public procurement notices, operated by the Publications Office of the European Union. TED publishes procurement opportunities exceeding EU threshold values (generally €140,000 for supplies/services, €5.35 million for works), providing EU-wide visibility for cross-border tender opportunities.

Integration of TED data was achieved through collaboration with a partner team who had previously extracted TED procurement records and provided the dataset in Parquet format. This collaboration yielded 16,895 European procurement records covering multiple EU member states. The provided dataset included partial OCDS field mappings, though not fully compliant with the OCDS release package structure used by other sources.

Data format heterogeneity presented integration challenges. Unlike the standardized OCDS JSON from OCP and BASE Portugal sources, the TED dataset required custom transformation logic to map partner-specific column names to the unified 27-field schema. Field naming conventions differed significantly (e.g., `contract_title` vs. `tender.title`), necessitating a dedicated transformer module (`src/processing/ted/transformer.py`) with explicit column mappings.

Despite format differences, the TED dataset provided valuable EU-wide coverage complementing the national and regional sources. Geographic attribution was limited, with many records lacking explicit country identifiers, resulting in classification as "unknown" country during Silver layer partitioning. This limitation was accepted given the dataset's value for demonstrating multi-format integration capabilities and providing additional European procurement records.

## 4.5 Henrique & Monteiro (Partner Data)

A supplementary Portuguese procurement dataset containing 203 records was obtained through academic collaboration with Henrique & Monteiro. This dataset, provided in a static format, complemented the larger BASE Portugal collection by offering a smaller, high-quality sample useful for validation and testing purposes.

The limited record count made this source valuable primarily for pipeline testing and quality assurance rather than comprehensive coverage. During development, the dataset served to validate transformation logic, test deduplication mechanisms, and verify end-to-end data flow before processing larger source volumes. The static nature of the dataset (no ongoing updates) simplified integration, requiring only one-time processing without incremental extraction mechanisms.

Field coverage was comprehensive, with most procurement lifecycle fields populated, providing a useful reference for completeness expectations. The dataset demonstrated that even small supplementary sources contribute value in multi-source architectures, both for testing purposes and for filling gaps in larger datasets where specific tenders might be missing.

## 4.6 OCDS Standard

The Open Contracting Data Standard (OCDS) is an open data standard for publication of structured, machine-readable information about public procurement processes, developed by the Open Contracting Partnership. OCDS defines a JSON-based schema covering the complete procurement lifecycle from planning through implementation, enabling consistent representation of procurement data across jurisdictions and platforms.

The OCDS schema organizes data around the concept of a "contracting process," identified by a unique OCID (Open Contracting ID). Each contracting process may contain multiple releases representing procurement lifecycle stages: tender announcement, award notification, contract signature, and implementation updates. The core schema includes objects for planning, tender, awards, contracts, buyers, suppliers, and documents, with extensible classification schemes for procurement categories, procurement methods, and tender statuses.

Standardization through OCDS provides critical advantages for multi-source integration. First, semantic consistency ensures that "tender value" means the same concept across different jurisdictions, reducing ambiguity in field interpretation. Second, structural consistency enables reusable transformation logic, where a single field mapping template applies across multiple OCDS-compliant sources with minor adaptations. Third, validation schemas facilitate automated quality checking, as records can be programmatically verified against the OCDS JSON Schema specification.

Mapping diverse source implementations to a unified schema required accommodating variations in OCDS adoption. While the OCP and BASE Portugal sources provided fully compliant OCDS Release Packages, implementation differences existed in field population priorities, optional field usage, and extension schemas. The project's unified 27-field schema was designed as an intersection of commonly-populated OCDS fields across all sources, ensuring that essential procurement information (identifiers, tender details, dates, parties, awards) was captured consistently while acknowledging that not all OCDS optional fields would be universally available.

**Table 2: Data Source Comparison**

| Source | Countries | Records | Format | API/Access | OCDS Compliant |
|--------|-----------|---------|--------|------------|----------------|
| Open Contracting Partnership | 7 (DE, UK, IT, ES, HR, XK, AL) | 462,226 | JSON (OCDS) | Bulk download | Full |
| BASE Portugal (dados.gov.pt) | 1 (PT) | 58,418 | JSON (OCDS) | RESTful API | Full |
| TED (Partner Data) | EU-wide (country unspecified) | 16,895 | Parquet | Static file | Partial |
| Henrique & Monteiro | 1 (PT) | 203 | Static file | Static file | Partial |
| **TOTAL** | **38 unique** | **536,778** | **Multi-format** | **Varied** | **Mixed** |

**Table 3: Geographic Coverage by Country**

| Country | Primary Source(s) | Record Count (approx.) |
|---------|-------------------|------------------------|
| United Kingdom | OCP (4 publications) | 285,000+ |
| Germany | OCP | 95,000+ |
| Portugal | BASE Portugal, H&M | 58,600+ |
| Italy | OCP | 42,000+ |
| Spain | OCP (2 publications) | 28,000+ |
| Croatia | OCP | 6,500+ |
| Albania | OCP | 4,200+ |
| Kosovo | OCP | 2,900+ |
| EU-wide (multi-country) | TED | 16,895 |
| **Total (38 countries)** | **All sources** | **536,778** |

*Note: Exact country-level breakdowns for some OCP publications are aggregated. TED records span multiple EU countries without explicit country attribution in all cases.*

## 4.7 Integration Challenges

Multi-source integration presented several technical and data quality challenges that required systematic solutions. API rate limiting was encountered with the dados.gov.pt platform, where excessive request frequencies triggered HTTP 429 (Too Many Requests) responses. This was mitigated through implementation of exponential backoff retry logic and request throttling with minimum intervals between API calls. The incremental extraction strategy also reduced load by fetching only new records rather than complete dataset refreshes.

Data quality inconsistencies manifested across all sources despite OCDS standardization. Missing required fields occurred frequently, with award-stage information (supplier names, contract values) absent in 30-40% of records across sources. Date quality issues included future dates (procurement publication dates in 2026-2027, likely data entry errors), historical anomalies (dates set to 1900-01-01 as placeholder values), and format inconsistencies. A data validation framework with quality flagging was implemented to identify and mark problematic records rather than rejecting them, preserving data volume while enabling downstream quality-based filtering.

Schema variations existed despite OCDS compliance due to different interpretations of optional fields and extension usage. For example, some OCP publications nested supplier information in `awards[].suppliers[]` arrays, while others used `contracts[].suppliers[]`, requiring conditional field extraction logic. Currency representation varied between three-letter ISO codes (EUR, GBP) and symbol representations (€, £), necessitating standardization mappings.

Language diversity posed challenges for category standardization and search functionality. Portuguese procurement categories (e.g., "Aquisição de serviços", "Empreitadas de obras públicas") and Albanian categories required manual mapping to English equivalents ("Acquisition of services", "Public works"). A category standardization dictionary was developed covering the most frequent non-English category values, while less common categories were preserved in original language with a standardization_attempted flag.

Missing field handling required careful consideration of null semantics. Empty strings (`""`), null values (`null`), and absent fields each required different treatment. A normalization strategy was adopted where empty strings were converted to null for consistency, but records with missing critical identifiers (OCID, tender ID) were flagged for manual review rather than automatic rejection to enable potential recovery through alternative identifier fields.

---

# 5. DATA PIPELINE IMPLEMENTATION

## 5.1 Bronze Layer - Raw Data Ingestion

### 5.1.1 Extraction Process

**Topics**:
- [ ] Extractor architecture
- [ ] Source-specific extractors (base_portugal/, open_contracting_partnership/)
- [ ] HTTP client implementation
- [ ] Error handling and retries
- [ ] Rate limiting

### 5.1.2 State Management

**Topics**:
- [ ] Incremental extraction
- [ ] State file structure (extraction_state.json)
- [ ] Tracking: last_extraction, total_records, last_record_id
- [ ] Avoiding duplicate downloads

### 5.1.3 Storage Structure

**Topics**:
- [ ] Partitioning strategy: source/country/year/month/day
- [ ] File naming convention
- [ ] JSON format preservation
- [ ] Bronze layer statistics: 2,447 files

**Code Example 1**: Bronze Layer Extraction
```python
# Example extractor logic
```

**Diagram 5**: Bronze Layer Directory Structure
- Tree view of data/bronze/ organization

## 5.2 Silver Layer - Data Cleaning & Normalization

### 5.2.1 Unified Schema Design

**Topics**:
- [ ] 27-field unified schema
- [ ] Field categories: Identifiers, Tender Info, Dates, Procurement Details, Parties, Awards, Metadata
- [ ] Schema evolution considerations
- [ ] Field mapping from OCDS

**Table 4**: Unified Schema Definition
| Field Name | Type | Description | Required |
|------------|------|-------------|----------|

### 5.2.2 Transformation Pipeline

**Topics**:
- [ ] Processor architecture (src/processing/)
- [ ] Field extraction from nested JSON
- [ ] Data type conversions
- [ ] Array handling (suppliers, documents)
- [ ] Hash computation for deduplication

**Code Example 2**: Field Mapping Example
```python
# Show transformation from Bronze OCDS to Silver schema
```

### 5.2.3 Data Validation

**Topics**:
- [ ] Required field validation
- [ ] Data type validation
- [ ] Date format validation (ISO 8601)
- [ ] Value range validation (amounts > 0)
- [ ] Quality flagging

**Code Example 3**: Validation Rules
```python
# Validation function examples
```

### 5.2.4 Data Cleaning

**Topics**:
- [ ] Whitespace trimming
- [ ] Empty string normalization
- [ ] Invalid date handling
- [ ] Currency standardization
- [ ] Text encoding fixes

### 5.2.5 Parquet Optimization

**Topics**:
- [ ] Why Parquet? (columnar, compression, schema enforcement)
- [ ] Snappy compression
- [ ] Partitioning by source/country/year/month
- [ ] Compression ratio: 10:1 vs JSON
- [ ] Silver layer statistics: 1,097 files

**Diagram 6**: Bronze → Silver Transformation Flow
- Show transformation steps visually

## 5.3 Gold Layer - Analytics-Ready Datasets

### 5.3.1 Multi-Source Unification

**Topics**:
- [ ] Loading all Silver sources
- [ ] Source tagging
- [ ] Schema alignment
- [ ] Merging strategy

**Code Example 4**: Unification Logic
```python
# Combining multiple Silver sources
```

### 5.3.2 Category Standardization

**Topics**:
- [ ] Multi-language categories (Portuguese, Albanian, etc.)
- [ ] Standardization to English
- [ ] Category mapping dictionary
- [ ] Handling missing categories

**Table 5**: Category Standardization Map
| Original | Language | Standardized |
|----------|----------|--------------|

### 5.3.3 Derived Fields

**Topics**:
- [ ] year, month, quarter (from publication_date)
- [ ] is_future_date flag
- [ ] has_value, has_award boolean flags
- [ ] date_quality_flag (valid/future/past)
- [ ] data_completeness_score (0.0-1.0)

**Code Example 5**: Derived Field Calculation
```python
# Completeness score computation
```

### 5.3.4 Deduplication

**Topics**:
- [ ] Deduplication strategy
- [ ] Composite key: ocid + source_publication_id
- [ ] Keep first occurrence
- [ ] Future: fuzzy matching on title/buyer/date

### 5.3.5 Pre-Computed Aggregates

**Topics**:
- [ ] Country summary (tender_count, total_value, avg_value, etc.)
- [ ] Monthly trends (time-series)
- [ ] Category analysis (breakdown by procurement type)
- [ ] Top buyers (top 100)
- [ ] Top suppliers (top 100)
- [ ] Rationale: Fast dashboard queries

**Table 6**: Gold Layer Datasets
| Dataset | Records | Purpose |
|---------|---------|---------|

### 5.3.6 Quality Reports

**Topics**:
- [ ] Automated quality report generation
- [ ] Metrics: completeness, validation pass/fail, date ranges
- [ ] JSON format
- [ ] Example quality report structure

**Diagram 7**: Gold Layer Generation Process
- Unified dataset creation flow
- Aggregate generation flow

## 5.4 Data Quality Framework

**Topics**:
- [ ] Quality dimensions: completeness, validity, consistency
- [ ] Scoring methodology
- [ ] Quality thresholds
- [ ] Reporting mechanism

**Estimated length**: 7-8 pages

---

# 6. QUERY ENGINE & SQL ANALYTICS

## 6.1 Dremio Configuration

**Topics**:
- [ ] MinIO source setup
- [ ] S3 connection parameters
- [ ] Path-style access configuration
- [ ] Metadata refresh

## 6.2 Dataset Promotion

**Topics**:
- [ ] Promoting folders to datasets
- [ ] Parquet format detection
- [ ] Schema inference
- [ ] Physical dataset layout (PDS)

## 6.3 Query Optimization

**Topics**:
- [ ] Partitioning benefits (predicate pushdown)
- [ ] Columnar format advantages
- [ ] Compression (Snappy) impact on I/O
- [ ] Query result caching

## 6.4 Example Queries

### 6.4.1 Country Analysis

**SQL Example 1**: Top 10 Countries
```sql
SELECT source_country, COUNT(*) as tender_count
FROM minio.gold.unified
GROUP BY source_country
ORDER BY tender_count DESC
LIMIT 10;
```

### 6.4.2 Time-Series Analysis

**SQL Example 2**: Monthly Trends
```sql
SELECT year, month, COUNT(*) as tender_count
FROM minio.gold.unified
WHERE year IN (2024, 2025)
GROUP BY year, month
ORDER BY year, month;
```

### 6.4.3 Value-Based Queries

**SQL Example 3**: High-Value Tenders
```sql
SELECT tender_title, buyer_name, tender_value_amount
FROM minio.gold.unified
WHERE tender_value_amount > 1000000
  AND tender_value_currency = 'EUR'
ORDER BY tender_value_amount DESC
LIMIT 100;
```

### 6.4.4 Aggregate Queries

**SQL Example 4**: Using Pre-Computed Aggregates
```sql
SELECT * FROM minio.gold.aggregates
WHERE country = 'portugal';
```

## 6.5 Performance Metrics

**Topics**:
- [ ] Query execution times
- [ ] First run vs cached performance
- [ ] Bytes scanned
- [ ] Optimization impact

**Table 7**: Query Performance Benchmarks
| Query Type | Rows Scanned | Duration (first) | Duration (cached) |
|------------|--------------|------------------|-------------------|

**Estimated length**: 3-4 pages

---

# 7. NLP CHATBOT IMPLEMENTATION

## 7.1 Motivation and Design Goals

**Topics**:
- [ ] Why natural language interface?
- [ ] Target users: non-technical analysts, business users
- [ ] Design principles: safety, accuracy, transparency

## 7.2 Architecture Overview

**Topics**:
- [ ] FastAPI REST API framework
- [ ] Dual-bot architecture
- [ ] Service layer design
- [ ] Dremio integration via Arrow Flight

**Diagram 8**: Chatbot System Architecture
- Components: API endpoints, LLM Service, Dremio Client, Query Executor
- Data flow for NL query → SQL → Results → Insights

## 7.3 Query Creator Bot

### 7.3.1 Model Selection

**Topics**:
- [ ] Google Gemini 2.0 Flash
- [ ] Why Flash? (speed, cost-effectiveness, SQL generation quality)
- [ ] Model configuration: temperature=0.1, max_tokens=1024

### 7.3.2 Natural Language to SQL

**Topics**:
- [ ] Input: User question in natural language
- [ ] Output: Validated SQL query
- [ ] Confidence scoring
- [ ] Explanation generation

### 7.3.3 Prompt Engineering

**Topics**:
- [ ] Schema-aware prompts
- [ ] Dynamic schema injection
- [ ] Few-shot learning examples
- [ ] Domain-specific hints (procurement terminology)
- [ ] Constraint enforcement (valid columns, syntax)

**Code Example 6**: SQL Generation Prompt Template
```python
# Show prompt structure
```

### 7.3.4 Schema Introspection

**Topics**:
- [ ] Schema Inspector service
- [ ] Metadata caching (1-hour TTL)
- [ ] Keyword-based table relevance
- [ ] Sample value provision

### 7.3.5 SQL Validation

**Topics**:
- [ ] Security layer (SQL injection prevention)
- [ ] Forbidden keyword blocking (DROP, DELETE, INSERT, etc.)
- [ ] Required keyword enforcement (SELECT, FROM)
- [ ] Complexity limits: max 5 JOINs, max 3 subquery depth
- [ ] Syntax validation with sqlparse

**Code Example 7**: SQL Validator
```python
# Validation logic
```

### 7.3.6 Retry Mechanism

**Topics**:
- [ ] Max 3 attempts
- [ ] Error feedback incorporation
- [ ] Progressive refinement
- [ ] Fallback strategy

**Diagram 9**: Query Creator Flow
- User question → Schema retrieval → Prompt construction → LLM generation → Validation → Return or retry

## 7.4 Analytics Bot

### 7.4.1 Model Selection

**Topics**:
- [ ] Google Gemini 2.5 Pro
- [ ] Why Pro? (advanced reasoning, complex analysis)
- [ ] Model configuration: temperature=0.7, max_tokens=2048

### 7.4.2 SQL Execution

**Topics**:
- [ ] Query Executor service
- [ ] Dremio Arrow Flight connection
- [ ] Result formatting
- [ ] Row limits (10,000 max)

### 7.4.3 Insight Generation

**Topics**:
- [ ] Chain-of-thought reasoning
- [ ] Pattern identification
- [ ] Trend analysis
- [ ] Outlier detection
- [ ] Statistical summaries

**Code Example 8**: Analytics Prompt Template
```python
# Show analytics generation prompt
```

### 7.4.4 Visualization Recommendations

**Topics**:
- [ ] Automatic chart type suggestions
- [ ] Axis recommendations
- [ ] Library suggestions (Plotly, matplotlib)
- [ ] Context-aware visualizations

### 7.4.5 User Focus Integration

**Topics**:
- [ ] Optional user message for analysis guidance
- [ ] Focus-based insight filtering
- [ ] Customized analysis

**Diagram 10**: Analytics Bot Flow
- SQL + user message → Query execution → Result formatting → LLM analysis → Insights + visualizations

## 7.5 API Endpoints

### 7.5.1 Health Check

**Endpoint**: `GET /api/health`

**Topics**:
- [ ] Service status verification
- [ ] Model availability check
- [ ] Dremio connection check

### 7.5.2 Query Creator

**Endpoint**: `POST /api/chat/query-creator`

**Topics**:
- [ ] Request schema: message, include_explanation, max_attempts
- [ ] Response schema: success, sql, explanation, confidence, hints
- [ ] Error handling

**Example 9**: API Request/Response
```json
// Request and response examples
```

### 7.5.3 Analytics

**Endpoint**: `POST /api/chat/analytics`

**Topics**:
- [ ] Request schema: sql, message, include_visualizations
- [ ] Response schema: success, results, insights, visualizations, trends
- [ ] Execution metrics

### 7.5.4 Additional Endpoints

**Topics**:
- [ ] `/api/validate-sql`: Validation without execution
- [ ] `/api/schema`: Schema introspection
- [ ] `/api/chat/refine`: Query refinement

## 7.6 Security & Safety

**Topics**:
- [ ] Multi-layer SQL injection prevention
- [ ] Read-only enforcement (Dremio permissions)
- [ ] Query timeout limits (30 seconds)
- [ ] Result size limits
- [ ] API key security (environment variables)

**Table 8**: Security Measures
| Layer | Mechanism | Protection |
|-------|-----------|------------|

## 7.7 Deployment

**Topics**:
- [ ] Docker containerization
- [ ] Service dependencies (dremio)
- [ ] Environment configuration
- [ ] Health checks
- [ ] Logging

## 7.8 Usage Examples

**Example 10**: Complete Workflow
1. User asks: "Show me top 10 countries by tender count"
2. Query Creator generates SQL
3. User submits SQL to Analytics
4. Analytics executes and generates insights
5. User receives results + insights + visualization suggestions

**Estimated length**: 6-7 pages

---

# 8. AUTOMATION & ORCHESTRATION

## 8.1 Pipeline Orchestration

**Topics**:
- [ ] Scheduler architecture (src/scheduler/)
- [ ] Complete pipeline workflow: Extract → Process → Gold
- [ ] Error handling and recovery
- [ ] Execution logging

**Diagram 11**: Pipeline Orchestration Flow
- Show Extract → Process → Gold → Upload stages
- Error handling paths

## 8.2 Automated Scheduler

**Topics**:
- [ ] Daily execution mode (2 AM)
- [ ] Test mode (5-minute intervals)
- [ ] Manual/once mode
- [ ] Python schedule library

### 8.2.1 Scheduler Modes

**Topics**:
- [ ] `daily`: Production mode
- [ ] `test`: Development mode
- [ ] `once`: Manual execution

### 8.2.2 State Tracking

**Topics**:
- [ ] scheduler_state.json
- [ ] Last run timestamp
- [ ] Success/failure tracking
- [ ] Next run scheduling

## 8.3 Incremental Processing

**Topics**:
- [ ] Extraction state management
- [ ] Processing state tracking
- [ ] Avoiding redundant work
- [ ] State file structure

**Code Example 11**: State Management
```python
# State tracking logic
```

## 8.4 Docker Integration

**Topics**:
- [ ] Scheduler container
- [ ] Volume mounts for data persistence
- [ ] Service dependencies
- [ ] Automatic restart policies

## 8.5 Monitoring & Logging

**Topics**:
- [ ] Centralized logging (logs/scheduled_runs/)
- [ ] Execution reports (pipeline_execution_report.txt)
- [ ] Error tracking
- [ ] Performance metrics

**Example 12**: Pipeline Execution Report
```
# Sample report content
```

**Estimated length**: 3-4 pages

---

# 9. RESULTS & EVALUATION

## 9.1 Data Pipeline Metrics

**Topics**:
- [ ] Total records processed: 536,778
- [ ] Geographic coverage: 38 European countries
- [ ] Data sources integrated: 4
- [ ] Bronze layer: 2,447 JSON files
- [ ] Silver layer: 1,097 Parquet files
- [ ] Gold layer: 6 datasets (unified + 5 aggregates)
- [ ] Date range: 2016-02-20 to 2025-12-15
- [ ] Storage efficiency: 10:1 compression ratio

**Table 9**: Pipeline Statistics Summary
| Metric | Value |
|--------|-------|

**Chart 1**: Records by Country (Bar Chart)
- Top 15 countries by tender count

**Chart 2**: Records by Source (Pie Chart)
- Distribution: OCP, BASE Portugal, TED, H&M

## 9.2 Data Quality Analysis

**Topics**:
- [ ] Completeness scores by field
- [ ] Field population rates
- [ ] Validation pass/fail statistics
- [ ] Quality flag distribution (valid/future/past dates)
- [ ] Records with values vs without

**Table 10**: Data Completeness Analysis
| Field | Population Rate | Notes |
|-------|----------------|-------|

**Chart 3**: Field Completeness (Horizontal Bar Chart)
- Show percentage of records with each field populated

## 9.3 NLP Chatbot Performance

**Topics**:
- [ ] SQL generation success rate
- [ ] Validation pass rate
- [ ] Average query generation time (~500ms)
- [ ] Average analytics generation time (~1-2s)
- [ ] Example successful queries
- [ ] Example failed queries and causes

**Table 11**: Chatbot Performance Metrics
| Metric | Value | Notes |
|--------|-------|-------|

## 9.4 Query Performance

**Topics**:
- [ ] Simple count queries: 1-2s (first), <500ms (cached)
- [ ] Aggregation queries: 2-3s
- [ ] Complex filters: 5-10s
- [ ] Optimization impact

**Table 12**: Dremio Query Performance
| Query Type | Complexity | First Run | Cached | Rows Scanned |
|------------|-----------|-----------|---------|--------------|

## 9.5 System Performance

**Topics**:
- [ ] Extraction duration (by source)
- [ ] Processing duration (Bronze → Silver)
- [ ] Gold layer generation duration
- [ ] End-to-end pipeline duration
- [ ] Resource usage (CPU, memory, storage)

**Chart 4**: Monthly Tender Trends (Line Chart)
- Show tender volume over time (2016-2025)

## 9.6 Validation Against Objectives

**Topics**:
- [ ] ✅ Objective 1: Integrate ≥3 sources → Achieved (4 sources)
- [ ] ✅ Objective 2: Standardize with OCDS → Achieved (27-field unified schema)
- [ ] ✅ Objective 3: Scalable architecture → Achieved (medallion + MinIO + Dremio)
- [ ] ✅ Objective 4: SQL analytics → Achieved (Dremio queries)
- [ ] ✅ Objective 5: NLP interface → Achieved (dual-bot chatbot)
- [ ] ✅ Objective 6: Automation → Achieved (daily scheduler)

**Estimated length**: 4-5 pages

---

# 10. TECHNICAL CHALLENGES & SOLUTIONS

## 10.1 Multi-Source Integration

### Challenge
**Topics**:
- [ ] Diverse API structures
- [ ] Inconsistent OCDS implementations
- [ ] Rate limiting differences
- [ ] Authentication requirements

### Solution
**Topics**:
- [ ] Modular extractor architecture
- [ ] Flexible field mapping
- [ ] Configurable rate limiting
- [ ] State-based incremental extraction

## 10.2 Data Quality & Completeness

### Challenge
**Topics**:
- [ ] Missing required fields
- [ ] Invalid dates (future dates, year 1900)
- [ ] Empty strings vs null values
- [ ] Inconsistent data types

### Solution
**Topics**:
- [ ] Validation framework with clear rules
- [ ] Data cleaning pipeline
- [ ] Quality scoring system
- [ ] Quality flags for downstream users
- [ ] Acceptance of imperfect data with metadata

## 10.3 Schema Standardization

### Challenge
**Topics**:
- [ ] OCDS standard variations
- [ ] Multi-language categories (Portuguese, Albanian, etc.)
- [ ] Nested vs flat structures
- [ ] Array vs single value fields

### Solution
**Topics**:
- [ ] 27-field unified schema design
- [ ] Category standardization mappings
- [ ] Flexible extraction with nested path support
- [ ] Array handling for suppliers/documents

**Code Example 13**: Field Mapping Challenge
```python
# Show complex nested extraction
```

## 10.4 Deduplication Strategy

### Challenge
**Topics**:
- [ ] Same tender appearing in multiple sources
- [ ] Slight variations in field values
- [ ] No universal tender ID across sources
- [ ] Performance considerations for fuzzy matching

### Solution
**Topics**:
- [ ] Phase 1: Composite key (ocid + source_publication_id)
- [ ] Keep first occurrence strategy
- [ ] Record hash for exact matching
- [ ] Future: Fuzzy matching on title/buyer/date

## 10.5 NLP Query Generation

### Challenge
**Topics**:
- [ ] Schema awareness (LLM needs to know available tables/columns)
- [ ] SQL injection risks
- [ ] Query complexity limits
- [ ] Hallucination (invalid column names)

### Solution
**Topics**:
- [ ] Dynamic schema injection in prompts
- [ ] Multi-layer SQL validation
- [ ] Forbidden keyword filtering
- [ ] Retry mechanism with error feedback
- [ ] Example-driven prompts (few-shot learning)

**Code Example 14**: SQL Validation Multi-Layer
```python
# Show validation layers
```

## 10.6 Scalability & Performance

### Challenge
**Topics**:
- [ ] Large JSON files in Bronze layer
- [ ] Memory constraints for processing
- [ ] Query performance on 500K+ records
- [ ] Storage efficiency

### Solution
**Topics**:
- [ ] Parquet columnar format (10:1 compression)
- [ ] Partitioning strategy (source/country/year/month)
- [ ] Incremental processing (state tracking)
- [ ] Dremio query optimization (predicate pushdown, caching)
- [ ] Pre-computed aggregates in Gold layer

**Table 13**: Performance Optimization Impact
| Optimization | Impact | Measurement |
|--------------|--------|-------------|

## 10.7 Deployment & Configuration

### Challenge
**Topics**:
- [ ] Service orchestration (MinIO, Dremio, API dependencies)
- [ ] Environment configuration
- [ ] Secret management (API keys)
- [ ] Data persistence across restarts

### Solution
**Topics**:
- [ ] Docker Compose for orchestration
- [ ] Environment file (.env) for configuration
- [ ] Volume mounts for data persistence
- [ ] Health checks and restart policies

**Estimated length**: 3-4 pages

---

# 11. CONCLUSIONS

## 11.1 Summary of Achievements

**Topics**:
- [ ] Successfully integrated 4 European procurement data sources
- [ ] Processed 536,778 tender records across 38 countries
- [ ] Implemented complete medallion architecture (Bronze/Silver/Gold)
- [ ] Standardized data using OCDS-based unified schema
- [ ] Built NLP chatbot for natural language querying
- [ ] Automated daily pipeline execution
- [ ] Achieved 10:1 storage compression with Parquet

## 11.2 Technical Contributions

**Topics**:
- [ ] Medallion architecture implementation for public procurement data
- [ ] OCDS standardization across diverse European sources
- [ ] LLM-powered natural language SQL generation with safety mechanisms
- [ ] Multi-language category standardization (Portuguese, Albanian → English)
- [ ] Scalable data lake architecture with distributed query engine

## 11.3 Objectives Validation

**Topics**:
- [ ] All primary objectives achieved
- [ ] Exceeded minimum requirement (≥3 sources → 4 sources)
- [ ] Additional features: NLP chatbot, automated scheduling
- [ ] Quality metrics demonstrate data pipeline effectiveness

## 11.4 Lessons Learned

### Data Engineering
**Topics**:
- [ ] Importance of data standards (OCDS) for integration
- [ ] Value of layered architecture for data quality control
- [ ] Partitioning and format choices critical for performance
- [ ] State management essential for incremental processing

### NLP & LLM Integration
**Topics**:
- [ ] Prompt engineering crucial for domain-specific tasks
- [ ] Multi-layer validation necessary for SQL safety
- [ ] Schema awareness improves SQL generation quality
- [ ] Dual-model approach balances cost and quality

### System Design
**Topics**:
- [ ] Containerization simplifies deployment
- [ ] Modular architecture enables extensibility
- [ ] Separation of concerns (extractors, processors, aggregators)
- [ ] Automation reduces manual intervention

## 11.5 Project Limitations

**Topics**:
- [ ] Data completeness varies by source
- [ ] Limited to tender/contract data (not full procurement lifecycle)
- [ ] Deduplication currently simple (no fuzzy matching)
- [ ] NLP chatbot limited to read-only queries
- [ ] Academic project scope (not production-hardened)

## 11.6 Future Work (Out of Scope)

**Topics**:
- [ ] Additional data sources (more countries, platforms)
- [ ] Advanced deduplication (fuzzy matching, ML-based)
- [ ] Real-time data ingestion (streaming)
- [ ] Advanced analytics (predictive modeling, anomaly detection)
- [ ] Multi-language NLP support (queries in Portuguese, Spanish, etc.)
- [ ] Frontend visualization dashboard
- [ ] Production deployment (Kubernetes, monitoring, scaling)

## 11.7 Final Remarks

**Topics**:
- [ ] Project demonstrates feasibility of unified European procurement data access
- [ ] Combination of data engineering and NLP creates powerful tool
- [ ] Architecture supports future expansion and enhancement
- [ ] Academic objectives fully achieved

**Estimated length**: 2-3 pages

---

# 12. REFERENCES

## Academic & Technical Literature
- [ ] Databricks. "Medallion Architecture". https://www.databricks.com/glossary/medallion-architecture
- [ ] Data lake architecture best practices

## Standards & Specifications
- [ ] Open Contracting Data Standard (OCDS). https://standard.open-contracting.org/
- [ ] Apache Parquet Documentation. https://parquet.apache.org/docs/
- [ ] JSON Schema Specification

## Technologies & Tools
- [ ] MinIO Documentation. https://min.io/docs/
- [ ] Dremio Documentation. https://docs.dremio.com/
- [ ] FastAPI Documentation. https://fastapi.tiangolo.com/
- [ ] Google Gemini API. https://ai.google.dev/docs
- [ ] PyArrow Documentation
- [ ] Pandas Documentation
- [ ] Docker Documentation

## Data Sources
- [ ] Open Contracting Partnership. https://data.open-contracting.org/
- [ ] dados.gov.pt - BASE Portal OCDS Dataset. https://dados.gov.pt/pt/datasets/ocds-portal-base-www-base-gov-pt/
- [ ] BASE Portal. https://www.base.gov.pt/
- [ ] TED (Tenders Electronic Daily). https://ted.europa.eu/

## Research & Methodology
- [ ] Google AI Prompt Engineering Guide. https://ai.google.dev/docs/prompt_best_practices
- [ ] Few-Shot Prompting Techniques
- [ ] SQL Injection Prevention Best Practices

---

# 13. APPENDICES

## Appendix A: Unified Schema Definition

**Content**:
- [ ] Complete 27-field schema
- [ ] Field-by-field description
- [ ] Data types
- [ ] Validation rules
- [ ] Example values

**Table A1**: Complete Schema Specification
| Field | Type | Description | Required | Validation |
|-------|------|-------------|----------|------------|

## Appendix B: Data Source Details

**Content**:
- [ ] URLs for all data sources
- [ ] API documentation links
- [ ] Access methods
- [ ] Data licenses
- [ ] Contact information

## Appendix C: API Documentation

**Content**:
- [ ] Complete API endpoint listing
- [ ] Request/response schemas (JSON)
- [ ] Example cURL commands
- [ ] Error codes and messages

**Example C1**: Query Creator Request
```bash
curl -X POST http://localhost:8000/api/chat/query-creator \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me top 10 countries"}'
```

**Example C2**: Analytics Request
```bash
curl -X POST http://localhost:8000/api/chat/analytics \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT ...", "message": "Analyze trends"}'
```

## Appendix D: SQL Query Examples

**Content**:
- [ ] 10-15 example SQL queries
- [ ] Covering different query patterns
- [ ] With expected results
- [ ] Performance notes

## Appendix E: Docker Deployment

**Content**:
- [ ] docker-compose.yml configuration
- [ ] Environment variables (.env template)
- [ ] Volume mounts
- [ ] Network configuration
- [ ] Service health checks

## Appendix F: Quick Start Guide

**Content**:
- [ ] Prerequisites
- [ ] Installation steps
- [ ] First run instructions
- [ ] Verification commands
- [ ] Troubleshooting

---

# DIAGRAM SUMMARY

**Diagrams to Create**:

1. **Overall System Architecture** (Section 3.1)
   - Components: Sources, Extractors, MinIO, Processors, Dremio, Applications
   - Data flow arrows

2. **Medallion Pattern Data Flow** (Section 3.2)
   - Bronze → Silver → Gold progression
   - Transformations at each layer

3. **Container Architecture** (Section 3.3.3)
   - Docker services: minio, dremio, chatbot-api, scheduler
   - Networks and volumes

4. **Detailed Data Flow** (Section 3.5)
   - End-to-end: API → Bronze → Silver → Gold → Query

5. **Bronze Layer Directory Structure** (Section 5.1.3)
   - Tree view of partitioning

6. **Bronze → Silver Transformation** (Section 5.2)
   - Processing steps visualization

7. **Gold Layer Generation** (Section 5.3)
   - Unification + aggregation flow

8. **Chatbot System Architecture** (Section 7.2)
   - API, LLM Service, Dremio Client, Query Executor

9. **Query Creator Flow** (Section 7.3)
   - NL question → SQL generation → Validation

10. **Analytics Bot Flow** (Section 7.4)
    - SQL → Execution → Insights

11. **Pipeline Orchestration** (Section 8.1)
    - Extract → Process → Gold → Upload

**Charts to Create**:

1. **Records by Country** (Section 9.1)
   - Bar chart, top 15 countries

2. **Records by Source** (Section 9.1)
   - Pie chart

3. **Field Completeness** (Section 9.2)
   - Horizontal bar chart

4. **Monthly Tender Trends** (Section 9.5)
   - Line chart (2016-2025)

---

# WRITING NOTES

**Style Guidelines**:
- Academic tone: formal, objective, technical
- Use passive voice where appropriate
- Cite sources for external claims
- Include evidence (numbers, metrics) for all claims
- Technical accuracy is paramount
- Explain acronyms on first use

**Formatting**:
- Standard academic report format
- Section numbering (1, 1.1, 1.1.1)
- Consistent heading styles
- Code examples with syntax highlighting
- Tables with clear headers
- Figures/diagrams with captions and numbers
- Page numbers
- Table of contents with page references

**Length Targets**:
- Total: 25-35 pages
- Sections vary as noted in skeleton
- Appendices not counted in main page count

**Review Checklist**:
- [ ] All diagrams created and referenced
- [ ] All code examples tested and accurate
- [ ] All statistics verified
- [ ] All references complete
- [ ] No TODO markers remaining
- [ ] Consistent terminology throughout
- [ ] All sections meet length targets
- [ ] Abstract accurately summarizes content

---

**END OF SKELETON**

Next step: Fill in content section by section, starting with metadata, abstract, and introduction.
