# Lightweight Data Lake Stack - Phase 1 (Minimal)

This is the minimal foundational setup for the lightweight data lake PoC, consisting of:
- **RustFS**: S3-compatible object storage
- **LakeKeeper**: Iceberg REST catalog
- **PostgreSQL**: Metadata storage for LakeKeeper
- **Trino**: Lightweight query engine with native Iceberg support
- **Superset**: Modern data visualization and exploration platform

See [spec.md](./spec.md) for the complete architecture plan.

## Prerequisites

- Docker and Docker Compose installed
- Ports available: 443, 5433, 8088, 8181, 9000, 9001
- AWS CLI (optional, for manual S3 operations)
- Trino CLI (optional, for connecting to Trino)

## Architecture Notes

- **Optimized Images**: Services use lightweight or stable images based on use case
  - PostgreSQL: Standard image (better stability for metadata storage)
  - RustFS: Rust-based S3-compatible object storage
  - LakeKeeper: Optimized Rust binary
  - Superset: Modern data visualization platform
  - Bootstrap utilities: Minimal Alpine images

- **Data Persistence**:
  - PostgreSQL: Fully persistent via Docker volume
  - LakeKeeper: Metadata persists in PostgreSQL
  - RustFS: Fully persistent via Docker volumes (2 data volumes)
  - Superset: Persistent via Docker volume (dashboards and queries saved)

## Quick Start

1. Start all services:
   ```bash
   docker compose up
   ```

## Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| **Superset** | http://localhost:8088 | Data visualization and exploration (login: admin/admin) |
| **Trino** | https://trino.datalake.local | Query engine endpoint — behind Caddy TLS, requires a `hosts` entry and trusting the local CA (run [scripts/setup-caddy-pki.sh](./scripts/setup-caddy-pki.sh)), and username/password auth (`TRINO_USER`/`TRINO_PASSWORD` env vars) |
| **LakeKeeper UI** | http://localhost:8181/ui/ | Manage warehouses, namespaces, and tables |
| **LakeKeeper API** | http://localhost:8181 | REST catalog API |
| **RustFS S3 API** | http://localhost:9000 | S3-compatible storage endpoint |
| **RustFS Console** | http://localhost:9001/rustfs/console | Web interface for RustFS management |
| **PostgreSQL** | localhost:5433 | LakeKeeper metadata (user: lakekeeper, pass: lakekeeper123) |

## S3 Credentials

RustFS S3 is configured with these credentials:

```
Access Key: admin
Secret Key: admin123
Bucket: datalake (auto-created on startup)
Endpoint: http://localhost:9000
Region: us-east-1
```

## Service Architecture

```
┌─────────────────────────────────────────────────┐
│  Superset (port 8088)                          │
│  • Data Visualization & Exploration            │
│  • Interactive Dashboards                      │
└────────┬───────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│  Caddy (port 443) → Trino                      │
│  • TLS termination + query engine              │
│  • Native Iceberg Connector                    │
└────────┬───────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│  LakeKeeper (port 8181)                        │
│  • REST Catalog API                            │
│  • Web UI at /ui/                              │
└────────┬─────────────────────────┬──────────────┘
         │                         │
         ▼                         ▼
┌──────────────────┐    ┌──────────────────────┐
│  PostgreSQL      │    │  RustFS              │
│  port 5433       │    │  S3: port 9000       │
│  (Metadata)      │    │  Console: port 9001  │
│                  │    │  (Object Storage)    │
└──────────────────┘    └──────────────────────┘
```

## Stopping and Cleaning Up

Stop services (preserves data):
```bash
docker compose down
```

Stop and remove all data:
```bash
docker compose down -v
```

## Next Steps

- Query data using Trino
- Set up PowerBI or other BI tool connections (requires Trino ODBC driver)
- Add additional data sources and transformations

## Project Structure

```
digitalbuff_datalake_stack/
├── docker-compose.yml           # Main stack configuration
├── README.md                    # This file
├── spec.md                      # Architecture specification
├── .gitignore
├── caddy/
│   └── Caddyfile                # TLS-terminating reverse proxy config
├── scripts/
│   └── setup-caddy-pki.sh       # Generates the static root CA + prints hosts entries
├── superset/
│   ├── Dockerfile              # Superset with Trino support
│   ├── README.md               # Superset documentation
│   └── init-superset.sh        # Superset initialization script
├── init-data/
│   ├── Dockerfile              # Data init container
│   ├── requirements.txt        # Python dependencies
│   └── populate.py             # Sample data generation script
└── trino/
    ├── Dockerfile              # Lightweight Trino build
    └── etc/                    # Trino configuration
        └── catalog/
            └── iceberg.properties  # Iceberg connector config
```

## Memory usage
- RustFS: 120-160MB
- LakeKeeper: 30-50MB
- Trino: 780MB
- Superset: 210MB

## References

- [Apache Superset Documentation](https://superset.apache.org/docs/intro)
- [Superset Trino Connection](https://superset.apache.org/docs/databases/trino)
- [Trino Documentation](https://trino.io/docs/current/)
- [Trino Iceberg Connector](https://trino.io/docs/current/connector/iceberg.html)
- [Lightweight Trino Distribution](https://dev.to/resurfacelabs/building-a-lightweight-trino-distribution-54h7)
- [LakeKeeper Documentation](https://docs.lakekeeper.io/)
- [LakeKeeper GitHub](https://github.com/lakekeeper/lakekeeper)
- [RustFS Documentation](https://docs.rustfs.com/)
- [RustFS GitHub](https://github.com/rustfs/rustfs)
- [PyIceberg Documentation](https://py.iceberg.apache.org/)
