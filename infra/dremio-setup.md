# Dremio Setup Guide

Quick guide to configure Dremio with MinIO for SQL queries on procurement data.

## Overview

Dremio provides SQL query capabilities over the Parquet files stored in MinIO's silver bucket.

**Data Available:**
- 462,312+ tender records across 7 countries
- Stored in MinIO `silver/open_contracting_partnership/` bucket
- Format: Partitioned Parquet files

---

## Prerequisites

Ensure services are running:

```bash
make up
```

Wait ~30 seconds for Dremio to initialize. Check status:

```bash
make dremio-status
```

---

## Setup Steps

### 1) First-Time Setup (One-Time Only)

**a) Create Admin Account**

1. Open Dremio UI: **http://localhost:9047**
2. Click "Get Started"
3. Fill in admin credentials:
   - **First Name**: Admin
   - **Last Name**: User
   - **Username**: `admin`
   - **Email**: `admin@localhost`
   - **Password**: Choose a strong password (remember it!)
4. Click "Sign Up"

**b) Run Automated Configuration**

```bash
make dremio-setup
```

You'll be prompted for admin credentials:
- Username: `admin`
- Password: [password you just created]

The script will:
- Connect to Dremio API
- Create MinIO S3 source
- Configure connection properties
- Refresh metadata to discover folders

---

### 3) Format Dataset (2 Clicks - Required!)

After `make dremio-setup` completes, you need to format the Parquet folder:

**Steps:**

1. Open http://localhost:9047
2. Navigate: Sources → **minio** → **silver** → **open_contracting_partnership**
3. **RIGHT-CLICK** on `open_contracting_partnership` folder
4. Select **"Format Folder"**
5. Format: **Parquet** → Click **"Save"**

**Done!** Now you can query the data.

---

### 4) Verification

**Check Source Was Created:**

1. Open http://localhost:9047
2. In the left sidebar, you should see **"minio"** source
3. Expand it: `minio` → `silver` → `open_contracting_partnership`

**Run Test Query:**

```bash
make dremio-query
```

This runs a sample query to verify data access.

---

## Querying Data

### Via Dremio Web UI

1. Open http://localhost:9047
2. Click **"SQL Runner"** (top navigation)
3. Write SQL queries:

```sql
-- Count tenders by country
SELECT source_country, COUNT(*) as total_tenders
FROM minio.silver.open_contracting_partnership
GROUP BY source_country
ORDER BY total_tenders DESC;

-- Recent high-value tenders
SELECT
  tender_id,
  title,
  source_country,
  tender_value_amount,
  tender_value_currency,
  publication_date
FROM minio.silver.open_contracting_partnership
WHERE tender_value_amount > 1000000
  AND publication_date >= '2025-01-01'
ORDER BY publication_date DESC
LIMIT 20;

-- Tenders by month
SELECT
  DATE_TRUNC('month', publication_date) as month,
  COUNT(*) as tender_count,
  AVG(tender_value_amount) as avg_value
FROM minio.silver.open_contracting_partnership
WHERE publication_date >= '2025-01-01'
GROUP BY month
ORDER BY month;

-- Top 10 most expensive tenders
SELECT
  tender_id,
  title,
  source_country,
  tender_value_amount,
  tender_value_currency,
  buyer_name
FROM minio.silver.open_contracting_partnership
WHERE tender_value_amount IS NOT NULL
ORDER BY tender_value_amount DESC
LIMIT 10;
```

### Via Python (ODBC/JDBC)

Connect to Dremio from code:

```python
# Using PyArrow Flight (recommended)
from pyarrow import flight

# Connection details
location = "grpc://localhost:32010"
client = flight.FlightClient(location)

# Authenticate
token = client.authenticate_basic_token(b"admin", b"your_password")

# Run query
query = "SELECT COUNT(*) FROM minio.silver.open_contracting_partnership"
info = client.get_flight_info(flight.FlightDescriptor.for_command(query))
reader = client.do_get(info.endpoints[0].ticket)
data = reader.read_all()
```

## Quick Reference

```bash
# Start services
make up

# Configure Dremio (first time)
make dremio-setup

# Check status
make dremio-status

# Run test query
make dremio-query

# View logs
make logs-api

# Stop services
make down
```

**Dremio UI**: http://localhost:9047
**MinIO Console**: http://localhost:9001
**API Docs**: http://localhost:8000/docs
