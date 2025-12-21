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
