# Dremio Gold Layer Configuration Guide

**Status**: ✅ Gold layer uploaded to MinIO (7 files, 73.88 MB)
**Next**: Configure Dremio to query the data

---

## What Was Uploaded

```
gold/
├── unified/
│   └── all_tenders.parquet (73.84 MB, 536,778 records)
├── aggregates/
│   ├── country_summary.parquet
│   ├── monthly_trends.parquet
│   ├── category_analysis.parquet
│   ├── top_buyers.parquet
│   └── top_suppliers.parquet
└── quality/
    └── quality_report_20251220_224904.json
```

---

## Step-by-Step: Configure Dremio

### Step 1: Open Dremio UI

Navigate to: **http://localhost:9047**

Login with your admin credentials (the ones you created during first setup).

### Step 2: Refresh MinIO Source Metadata

**Why?** Dremio needs to discover the new `gold/` folder that we just uploaded.

1. In the left sidebar, find **"Sources"** section
2. Locate **"minio"** source (should have a green checkmark)
3. **Right-click** on "minio"
4. Select **"Refresh Metadata"**
5. Wait 5-10 seconds for the refresh to complete

### Step 3: Verify Gold Bucket is Visible

1. Click to expand **"minio"** source
2. You should now see three buckets:
   - `bronze` (2,445 objects)
   - `silver` (1,109 objects)
   - `gold` ✨ **(7 objects - newly appeared!)**
3. Expand `gold/` to see:
   - `unified/` folder
   - `aggregates/` folder
   - `quality/` folder

If you don't see `gold/`, repeat Step 2 (Refresh Metadata).

### Step 4: Format the Unified Dataset

**Why?** Dremio needs to know the folder contains Parquet files.

1. Navigate: **minio → gold → unified**
2. You should see `all_tenders.parquet` file inside
3. **Right-click** on the **"unified"** folder (NOT the file)
4. Select **"Format Folder"**
5. In the dialog:
   - Format: **Parquet** ✓
   - Click **"Save"**
6. Wait 2-3 seconds
7. The `unified` folder icon should change (looks like a table now)

### Step 5: Format the Aggregates Dataset

1. Navigate: **minio → gold → aggregates**
2. You should see 5 parquet files inside
3. **Right-click** on the **"aggregates"** folder
4. Select **"Format Folder"**
5. In the dialog:
   - Format: **Parquet** ✓
   - Click **"Save"**

### Step 6: Run Your First Query!

1. Click **"SQL Runner"** in the top navigation bar
2. Copy and paste this test query:

```sql
SELECT COUNT(*) as total_tenders
FROM minio.gold.unified;
```

3. Click **"Run"** (or press Ctrl+Enter)
4. **Expected result**: `total_tenders: 536778`

If you see this number, **SUCCESS!** 🎉 Your gold layer is fully queryable.

---

## Test Queries

Open the file: **`docs/dremio_test_queries.sql`**

This contains 10 categories of queries you can test:
1. Basic verification
2. Country analysis
3. Procurement category analysis
4. Time-series analysis
5. High-value tenders
6. Buyer & supplier analysis
7. Data quality dashboard
8. Silver vs Gold comparison
9. Advanced analytics
10. Sample business queries

### Quick Test Suite

Run these 5 queries to verify everything works:

```sql
-- 1. Total record count (should be 536,778)
SELECT COUNT(*) FROM minio.gold.unified;

-- 2. Top 5 countries
SELECT source_country, COUNT(*) as count
FROM minio.gold.unified
GROUP BY source_country
ORDER BY count DESC
LIMIT 5;

-- 3. Check titles are populated
SELECT tender_title, buyer_name, tender_value_amount
FROM minio.gold.unified
WHERE tender_title != ''
LIMIT 10;

-- 4. Procurement categories
SELECT procurement_category_standardized, COUNT(*) as count
FROM minio.gold.unified
WHERE procurement_category_standardized != ''
GROUP BY procurement_category_standardized;

-- 5. Data quality overview
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN tender_title != '' THEN 1 ELSE 0 END) as has_title,
    SUM(CASE WHEN tender_value_amount > 0 THEN 1 ELSE 0 END) as has_value,
    SUM(CASE WHEN date_quality_flag = 'valid' THEN 1 ELSE 0 END) as valid_dates
FROM minio.gold.unified;
```

---

## Troubleshooting

### Gold bucket not showing?
- **Solution**: Refresh metadata (right-click minio → Refresh Metadata)
- Wait 10 seconds and check again

### "Table not found" error?
- **Solution**: Format the folder (right-click folder → Format Folder → Parquet → Save)

### Query returns 0 records?
- Check you formatted the **folder** (not individual files)
- Verify upload: Check MinIO Console at http://localhost:9001
  - Login: minioadmin / minioadmin
  - Browse: gold bucket → Should show 7 objects

### Slow queries?
- First query is always slower (Dremio caches metadata)
- Subsequent queries are much faster

---

## What Data is Available?

### Unified Dataset (536,778 records)

**Countries** (Top 10):
- 🇩🇪 Germany: 223,113 tenders
- 🇬🇧 UK: 116,323 tenders
- 🇮🇹 Italy: 107,891 tenders
- 🇵🇹 Portugal: 59,718 tenders
- 🇭🇷 Croatia: 11,961 tenders
- 🇽🇰 Kosovo: 7,396 tenders
- 🇫🇷 France: 1,442 tenders
- 🇨🇿 Czech Republic: 1,141 tenders
- 🇸🇪 Sweden: 1,138 tenders
- 🇨🇭 Switzerland: 1,089 tenders

**Date Range**: 2016-02-20 to 2025-12-15 (32 future dates flagged)

**Procurement Categories**:
- Services
- Works
- Goods
- (Plus Portuguese/Albanian translations - standardized to English)

**Fields** (38 total):
- Core: `tender_title`, `buyer_name`, `tender_value_amount`, `publication_date`
- Derived: `year`, `month`, `quarter`, `data_completeness_score`
- Quality: `date_quality_flag`, `is_future_date`
- Classification: `procurement_category_standardized`, `procurement_category_original`
- Source: `source`, `source_country`, `source_publication_id`

---

## Next Steps: Build Frontend

Now that Dremio can query the gold layer, you can build:

### Option 1: Streamlit Chatbot (Recommended - Fastest)

**Natural Language → SQL Generation → Execute → Display Results**

```python
# Example: User asks "Show me tenders from Portugal"
# LLM generates: SELECT * FROM minio.gold.unified WHERE source_country = 'portugal'
# Execute via Dremio API
# Display results in table/chart
```

**Time to build**: 2-3 hours
**Technologies**: Streamlit + OpenAI/Claude API + Dremio REST API

### Option 2: FastAPI + React Frontend

**REST API wrapping Dremio queries + Modern web UI**

**Time to build**: 6-8 hours
**Technologies**: FastAPI (backend) + React (frontend) + Dremio REST API

### Option 3: Jupyter Notebooks

**Interactive data analysis environment**

**Time to build**: 1 hour
**Technologies**: JupyterLab + pandas + pyarrow.flight (Dremio connector)

---

## Integration Example: Query Dremio from Python

```python
import requests
import pandas as pd

class DremioClient:
    def __init__(self, host="localhost", port=9047, username="admin", password="your_password"):
        self.base_url = f"http://{host}:{port}"
        self.token = self._login(username, password)
        self.headers = {
            "Authorization": f"_dremio{self.token}",
            "Content-Type": "application/json"
        }

    def _login(self, username, password):
        response = requests.post(
            f"{self.base_url}/apiv2/login",
            json={"userName": username, "password": password}
        )
        return response.json()["token"]

    def query(self, sql: str) -> pd.DataFrame:
        # Submit job
        response = requests.post(
            f"{self.base_url}/apiv2/job/submit/sql",
            headers=self.headers,
            json={"sql": sql}
        )
        job_id = response.json()["id"]

        # Wait for completion
        import time
        while True:
            status = requests.get(
                f"{self.base_url}/apiv2/job/{job_id}",
                headers=self.headers
            ).json()

            if status["jobState"] == "COMPLETED":
                break
            elif status["jobState"] in ["FAILED", "CANCELED"]:
                raise Exception(f"Query failed: {status.get('errorMessage')}")
            time.sleep(0.5)

        # Get results
        results = requests.get(
            f"{self.base_url}/apiv2/job/{job_id}/results",
            headers=self.headers
        ).json()

        return pd.DataFrame(results["rows"])

# Usage
client = DremioClient(password="your_admin_password")
df = client.query("""
    SELECT source_country, COUNT(*) as count
    FROM minio.gold.unified
    GROUP BY source_country
    ORDER BY count DESC
    LIMIT 10
""")
print(df)
```

---

## Success Checklist

- [ ] Gold bucket visible in Dremio UI
- [ ] `unified` folder formatted as Parquet dataset
- [ ] `aggregates` folder formatted as Parquet dataset
- [ ] Test query returns 536,778 records
- [ ] Top countries query returns Germany as #1 (223K)
- [ ] Sample records show actual tender titles and buyer names
- [ ] Python client can execute queries successfully

Once all checked ✅, you're ready to build the frontend!

---

**Need help?** Check:
- MinIO Console: http://localhost:9001 (verify files uploaded)
- Dremio UI: http://localhost:9047 (run queries manually)
- Logs: `docker logs sod-dremio` (debug connection issues)
