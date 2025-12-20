-- ============================================================
-- DREMIO TEST QUERIES - Gold Layer
-- ============================================================
-- Copy these queries to Dremio SQL Runner after formatting datasets
-- http://localhost:9047
-- ============================================================

-- ============================================================
-- 1. BASIC VERIFICATION QUERIES
-- ============================================================

-- Test 1: Count total records in unified dataset
-- Expected: 536,778 records
SELECT COUNT(*) as total_tenders
FROM minio.gold.unified;

-- Test 2: Check data is actually there
-- Should return sample rows with titles, buyers, values
SELECT
    tender_title,
    buyer_name,
    tender_value_amount,
    source_country,
    publication_date
FROM minio.gold.unified
LIMIT 10;

-- ============================================================
-- 2. COUNTRY ANALYSIS
-- ============================================================

-- Top 10 Countries by Tender Count
SELECT
    source_country,
    COUNT(*) as tender_count,
    ROUND(AVG(tender_value_amount), 2) as avg_value_eur,
    ROUND(SUM(tender_value_amount), 2) as total_value_eur
FROM minio.gold.unified
GROUP BY source_country
ORDER BY tender_count DESC
LIMIT 10;

-- Expected Top 3:
-- 1. germany: 223,113
-- 2. uk: 116,323
-- 3. italy: 107,891

-- ============================================================
-- 3. PROCUREMENT CATEGORY ANALYSIS
-- ============================================================

-- Tenders by Standardized Category
SELECT
    procurement_category_standardized,
    COUNT(*) as count,
    ROUND(AVG(tender_value_amount), 2) as avg_value,
    ROUND(SUM(tender_value_amount), 2) as total_value
FROM minio.gold.unified
WHERE procurement_category_standardized != ''
GROUP BY procurement_category_standardized
ORDER BY count DESC;

-- Category Distribution by Country
SELECT
    source_country,
    procurement_category_standardized,
    COUNT(*) as tender_count
FROM minio.gold.unified
WHERE procurement_category_standardized IN ('services', 'works', 'goods')
GROUP BY source_country, procurement_category_standardized
ORDER BY source_country, tender_count DESC;

-- ============================================================
-- 4. TIME-SERIES ANALYSIS
-- ============================================================

-- Tenders by Month (2024-2025)
SELECT
    year,
    month,
    COUNT(*) as tender_count,
    ROUND(SUM(tender_value_amount), 2) as total_value
FROM minio.gold.unified
WHERE year >= 2024
  AND date_quality_flag = 'valid'  -- Exclude future dates
GROUP BY year, month
ORDER BY year DESC, month DESC
LIMIT 24;

-- Monthly Trend (using date functions)
SELECT
    DATE_TRUNC('month', CAST(publication_date AS DATE)) as month,
    COUNT(*) as tenders,
    ROUND(AVG(tender_value_amount), 2) as avg_value
FROM minio.gold.unified
WHERE publication_date IS NOT NULL
  AND year BETWEEN 2020 AND 2025
  AND date_quality_flag = 'valid'
GROUP BY DATE_TRUNC('month', CAST(publication_date AS DATE))
ORDER BY month DESC
LIMIT 12;

-- ============================================================
-- 5. HIGH-VALUE TENDERS
-- ============================================================

-- Top 20 Most Expensive Tenders
SELECT
    tender_title,
    buyer_name,
    tender_value_amount,
    tender_value_currency,
    source_country,
    publication_date,
    procurement_category_standardized
FROM minio.gold.unified
WHERE tender_value_amount > 0
ORDER BY tender_value_amount DESC
LIMIT 20;

-- High-Value Portuguese Tenders (Over €100k)
SELECT
    tender_title,
    buyer_name,
    tender_value_amount,
    publication_date,
    procurement_category_standardized
FROM minio.gold.unified
WHERE source_country = 'portugal'
  AND tender_value_amount > 100000
  AND date_quality_flag = 'valid'
ORDER BY tender_value_amount DESC
LIMIT 20;

-- ============================================================
-- 6. BUYER & SUPPLIER ANALYSIS
-- ============================================================

-- Top 50 Buyers Across All Countries
SELECT
    source_country,
    buyer_name,
    COUNT(*) as tender_count,
    ROUND(SUM(tender_value_amount), 2) as total_value
FROM minio.gold.unified
WHERE buyer_name != ''
GROUP BY source_country, buyer_name
ORDER BY total_value DESC
LIMIT 50;

-- Most Active Buyers (by number of tenders)
SELECT
    buyer_name,
    source_country,
    COUNT(*) as tender_count,
    ROUND(AVG(tender_value_amount), 2) as avg_value
FROM minio.gold.unified
WHERE buyer_name != ''
GROUP BY buyer_name, source_country
ORDER BY tender_count DESC
LIMIT 30;

-- ============================================================
-- 7. DATA QUALITY DASHBOARD
-- ============================================================

-- Completeness Report by Source and Country
SELECT
    source,
    source_country,
    COUNT(*) as total_records,
    SUM(CASE WHEN tender_title != '' THEN 1 ELSE 0 END) as has_title,
    SUM(CASE WHEN buyer_name != '' THEN 1 ELSE 0 END) as has_buyer,
    SUM(CASE WHEN tender_value_amount > 0 THEN 1 ELSE 0 END) as has_value,
    SUM(CASE WHEN date_quality_flag = 'valid' THEN 1 ELSE 0 END) as valid_dates,
    SUM(CASE WHEN is_future_date = true THEN 1 ELSE 0 END) as future_dates,
    ROUND(AVG(data_completeness_score), 2) as avg_completeness
FROM minio.gold.unified
GROUP BY source, source_country
ORDER BY source, source_country;

-- Records with Data Quality Issues
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN is_future_date = true THEN 1 ELSE 0 END) as future_dates,
    SUM(CASE WHEN tender_title = '' THEN 1 ELSE 0 END) as missing_title,
    SUM(CASE WHEN buyer_name = '' THEN 1 ELSE 0 END) as missing_buyer,
    SUM(CASE WHEN tender_value_amount = 0 THEN 1 ELSE 0 END) as missing_value
FROM minio.gold.unified;

-- ============================================================
-- 8. COMPARE SILVER vs GOLD LAYERS
-- ============================================================

-- Verify OCP data consistency
SELECT
    'silver' as layer,
    COUNT(*) as record_count
FROM minio.silver.open_contracting_partnership

UNION ALL

SELECT
    'gold' as layer,
    COUNT(*) as record_count
FROM minio.gold.unified
WHERE source = 'ocp';

-- Both should be ~462K records

-- ============================================================
-- 9. ADVANCED ANALYTICS
-- ============================================================

-- Average Tender Value by Country and Category
SELECT
    source_country,
    procurement_category_standardized,
    COUNT(*) as tender_count,
    ROUND(AVG(tender_value_amount), 2) as avg_value,
    ROUND(MIN(tender_value_amount), 2) as min_value,
    ROUND(MAX(tender_value_amount), 2) as max_value
FROM minio.gold.unified
WHERE procurement_category_standardized != ''
  AND tender_value_amount > 0
GROUP BY source_country, procurement_category_standardized
ORDER BY source_country, avg_value DESC;

-- Tender Volume Trends (Quarterly)
SELECT
    year,
    quarter,
    COUNT(*) as tender_count,
    ROUND(SUM(tender_value_amount), 2) as total_value,
    ROUND(AVG(tender_value_amount), 2) as avg_value
FROM minio.gold.unified
WHERE date_quality_flag = 'valid'
  AND year >= 2023
GROUP BY year, quarter
ORDER BY year DESC, quarter DESC;

-- ============================================================
-- 10. SAMPLE BUSINESS QUERIES
-- ============================================================

-- Q: "Find all IT services tenders from Germany over €500k in 2025"
SELECT
    tender_title,
    buyer_name,
    tender_value_amount,
    publication_date
FROM minio.gold.unified
WHERE source_country = 'germany'
  AND procurement_category_standardized = 'services'
  AND tender_value_amount > 500000
  AND year = 2025
  AND (LOWER(tender_title) LIKE '%software%'
       OR LOWER(tender_title) LIKE '%it %'
       OR LOWER(tender_title) LIKE '%system%')
ORDER BY publication_date DESC;

-- Q: "What are the most common procurement methods?"
SELECT
    procurement_method,
    COUNT(*) as count,
    ROUND(AVG(tender_value_amount), 2) as avg_value
FROM minio.gold.unified
WHERE procurement_method != ''
GROUP BY procurement_method
ORDER BY count DESC
LIMIT 20;

-- Q: "Show me tenders published this month"
SELECT
    tender_title,
    source_country,
    buyer_name,
    tender_value_amount,
    publication_date
FROM minio.gold.unified
WHERE year = 2025
  AND month = 12  -- Change to current month
  AND date_quality_flag = 'valid'
ORDER BY publication_date DESC
LIMIT 50;

-- ============================================================
-- END OF TEST QUERIES
-- ============================================================
--
-- Next: Use these queries to build:
-- 1. Streamlit chatbot (LLM generates SQL from natural language)
-- 2. FastAPI endpoints (wrap these queries as REST API)
-- 3. Grafana dashboards (visualize trends)
-- ============================================================
