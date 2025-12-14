# Infrastructure Setup Guide

This directory contains the Docker infrastructure for the E-Procurement System.

## Services

The infrastructure includes:

1. **MinIO** - S3-compatible object storage for data lake (Bronze/Silver/Gold layers)
2. **Dremio** - Distributed SQL query engine for data analytics

## Quick Start

### 1. Start Infrastructure

```bash
make up
```

### 2. Verify Services

Check that all services are running:

```bash
cd infra && docker-compose ps
```

You should see:
- `sod-minio` - Running on ports 9000 (API) and 9001 (Console)
- `sod-dremio` - Running on ports 9047 (Web UI) and 32010 (Arrow Flight)

### 3. Access Services

**MinIO Console:**
- URL: http://localhost:9001
- Username: `minioadmin`
- Password: `minioadmin`

**Dremio Web UI:**
- URL: http://localhost:9047
- First-time setup required (create admin account)

## MinIO Setup

MinIO buckets are automatically created on startup:
- `bronze` - Raw JSON data from sources
- `silver` - Cleaned Parquet data
- `gold` - Aggregated analytics data

### Manual Bucket Creation

If needed, you can manually create buckets:

```bash
docker exec -it sod-minio mc alias set myminio http://localhost:9000 minioadmin minioadmin
docker exec -it sod-minio mc mb myminio/bronze
docker exec -it sod-minio mc mb myminio/silver
docker exec -it sod-minio mc mb myminio/gold
```

## Dremio Setup

### 1. Initial Configuration

1. Open http://localhost:9047
2. Create admin account on first login
3. Click "Add Source" → "Amazon S3"

### 2. Connect to MinIO

Configure S3 source with these settings:

- **Name:** `minio-bronze` (or any name)
- **Authentication:** AWS Access Key
  - AWS Access Key: `minioadmin`
  - AWS Secret Key: `minioadmin`
- **Connection Properties:**
  - Check "Enable compatibility mode"
  - Check "Encrypt connection" = **OFF**
  - Root Path: `/`
  - Connection Properties:
    - `fs.s3a.path.style.access` = `true`
    - `fs.s3a.endpoint` = `minio:9000`
    - `dremio.s3.compat` = `true`

### 3. Create Datasets

After adding the source:

1. Navigate to the MinIO source
2. Browse to `silver` bucket
3. Right-click on `open_contracting_partnership` folder
4. Select "Format Folder"
5. Choose "Parquet" format
6. Save as physical dataset

Now you can query the data with SQL:

```sql
-- Count tenders by country
SELECT source_country, COUNT(*) as total
FROM minio_bronze.silver.open_contracting_partnership
GROUP BY source_country
ORDER BY total DESC;

-- Recent tenders
SELECT tender_id, title, publication_date, tender_value_amount
FROM minio_bronze.silver.open_contracting_partnership
WHERE publication_date >= '2025-01-01'
ORDER BY publication_date DESC
LIMIT 10;
```

## Troubleshooting

### Services Not Starting

```bash
# Check logs
docker-compose logs -f [service-name]

# Restart services
docker-compose restart

# Full reset
docker-compose down -v
docker-compose up -d
```

### MinIO Connection Issues

Ensure `MINIO_ENDPOINT` in `.env` is set correctly:
```bash
# For local development
MINIO_ENDPOINT=localhost:9000

# For Docker-to-Docker communication
MINIO_ENDPOINT=minio:9000
```

### Dremio Cannot Connect to MinIO

1. Verify MinIO is running: `docker ps | grep minio`
2. Check Dremio can reach MinIO: `docker exec -it sod-dremio ping minio`
3. Ensure "Enable compatibility mode" is checked in Dremio source settings
4. Use endpoint `minio:9000` (not `localhost:9000`) in Dremio

## Data Management

### Backup MinIO Data

```bash
# Backup all buckets
docker exec sod-minio tar -czf /tmp/minio-backup.tar.gz /data
docker cp sod-minio:/tmp/minio-backup.tar.gz ./minio-backup.tar.gz
```

### Restore MinIO Data

```bash
docker cp ./minio-backup.tar.gz sod-minio:/tmp/
docker exec sod-minio tar -xzf /tmp/minio-backup.tar.gz -C /
docker-compose restart minio
```

### Clear All Data

```bash
# WARNING: This deletes all data!
docker-compose down -v
docker-compose up -d
```

## Ports Reference

| Service | Port | Description |
|---------|------|-------------|
| MinIO API | 9000 | S3-compatible API |
| MinIO Console | 9001 | Web UI for MinIO |
| Dremio Web UI | 9047 | Dremio interface |
| Dremio ODBC/JDBC | 31010 | Database connections |
| Dremio Arrow Flight | 32010 | High-performance queries |

## Environment Variables

See `../.env` for configuration. Key variables:

```bash
# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_ENDPOINT=localhost:9000

# Dremio
DREMIO_HOST=localhost
DREMIO_PORT=9047
```

## Production Considerations

For production deployment:

1. **Security:**
   - Change default passwords
   - Use secrets management
   - Enable SSL/TLS
   - Configure firewalls

2. **Performance:**
   - Increase Dremio memory (`DREMIO_JAVA_SERVER_EXTRA_OPTS`)
   - Use persistent volumes
   - Configure backups

3. **Monitoring:**
   - Add Prometheus/Grafana
   - Set up alerts
   - Monitor disk usage
