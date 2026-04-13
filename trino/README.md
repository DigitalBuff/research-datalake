# Trino Lightweight Configuration

This directory contains the configuration for a lightweight Trino deployment optimized for the data lake PoC.

## Configuration Files

- **Dockerfile**: Builds a lightweight Trino image by removing unnecessary connectors
- **etc/config.properties**: Main Trino server configuration with memory tuning
- **etc/jvm.config**: JVM memory settings (reduced heap for lightweight operation)
- **etc/node.properties**: Node identity and data directory configuration
- **etc/log.properties**: Logging configuration
- **etc/catalog/iceberg.properties**: Iceberg connector configuration for LakeKeeper REST catalog

## Lightweight Optimizations

Based on: https://dev.to/resurfacelabs/building-a-lightweight-trino-distribution-54h7

1. **Connector Stripping**: Only Iceberg connector is included (removes ~30 other connectors)
2. **Memory Tuning**:
   - JVM heap: 512MB-1GB (vs default 4-8GB)
   - Query max memory: 1GB
   - Reduced query history and cache sizes
3. **Single-node Mode**: Coordinator also acts as worker

## Expected Resource Usage

- Memory: ~500MB-1GB when running
- CPU: Minimal when idle
- Image size: ~400MB (vs ~1.3GB standard)

## Connecting to Trino

- **URL**: http://localhost:8080
- **Catalog**: `iceberg`
- **Schemas**: Managed by LakeKeeper (e.g., `demo`)

Example query:
```sql
SHOW SCHEMAS FROM iceberg;
SELECT * FROM iceberg.demo.sales LIMIT 10;
```

## Iceberg Catalog Integration

The Iceberg connector is configured to:
- Connect to LakeKeeper REST catalog at `http://lakekeeper:8181/catalog`
- Access RustFS S3 storage at `http://rustfs:9000`
- Use warehouse: `datalake-warehouse`
