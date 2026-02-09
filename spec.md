# Lightweight Data Lake Architecture Plan

## Document Purpose

This document serves as an architectural blueprint for implementing a lightweight, resource-efficient data lake proof-of-concept (PoC). It is designed to be self-contained and can be used as input for implementation sessions.

---

## 1. Problem Statement

### Requirements

| Requirement | Description |
|-------------|-------------|
| **Minimal Resources** | Query engine should use minimum CPU/memory when inactive |
| **Scale to Zero** | Query engine container should stop completely when not in use |
| **Iceberg Format** | Use Apache Iceberg as the data lake table format |
| **REST Catalog** | Use LakeKeeper as the Iceberg REST catalog |
| **S3 Storage** | Use S3-compatible object storage (RustFS) |
| **PowerBI Access** | Users connect via PowerBI Desktop using standard SQL |
| **Server-Side Execution** | Only query results sent to clients (no Parquet file downloads) |
| **Simple Auth** | Username/password authentication |

### Constraints

- Data volume: < 50GB per table
- Environment: Docker Compose for PoC, Kubernetes for production
- Users: SQL-proficient, comfortable with slightly advanced connection setup
- Usage pattern: Ad-hoc exploration with acceptable cold-start delay (~1 minute)

### Explicitly Rejected Alternatives

| Alternative | Reason for Rejection |
|-------------|---------------------|
| MinIO | Deprecated; originally replaced by SeaweedFS, now superseded by RustFS |
| SeaweedFS | Replaced by RustFS; SeaweedFS requires 4 separate containers (master, volume, filer, s3) vs RustFS's single container |
| Azurite | Does not support ADLS Gen2 required by LakeKeeper |
| Buena Vista | Not maintained (2+ years inactive) |
| pg_duckdb | Replaced by Trino; DuckDB's Iceberg extension has limited REST catalog support, requiring workarounds like `iceberg_scan()` instead of native catalog integration |
| MotherDuck connector | Only works with MotherDuck cloud or local files, not remote self-hosted DuckDB |
| Client-side DuckDB | Would require users to access object storage directly |

---

## 2. Technology Stack

### Selected Components

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Query Engine** | Trino (lightweight) | Latest | Distributed SQL query engine with native Iceberg support |
| **Table Format** | Apache Iceberg | Latest | Open table format with ACID guarantees |
| **Catalog** | LakeKeeper | Latest | Rust-native Iceberg REST catalog |
| **Object Storage** | RustFS | Latest | S3-compatible object storage (single container) |
| **Catalog Database** | PostgreSQL | 16 | Metadata storage for LakeKeeper |
| **TCP Gateway** | Custom (Rust) | N/A | Connection proxy with idle timeout (Phase 2) |

### Why Trino (Lightweight)?

Trino was initially rejected due to its heavy default footprint (~4-8GB memory, 1.3GB image). However, a [lightweight distribution approach](https://dev.to/resurfacelabs/building-a-lightweight-trino-distribution-54h7) makes it viable:

1. **Native Iceberg REST catalog connector** - First-class integration with LakeKeeper; tables are queried via standard SQL (`SELECT * FROM iceberg.demo.sales`) without workarounds like `iceberg_scan()`
2. **Lightweight distribution** - Strip unnecessary connectors (keep only Iceberg), use Alpine-based image, tune memory settings; reduces image from ~1.3GB to ~400MB and memory to ~1GB
3. **Standard SQL** - Full ANSI SQL support; PowerBI and other BI tools work naturally
4. **Active ecosystem** - Large community, extensive connector library, well-documented
5. **Full scale-to-zero** - Entire container can stop when idle (via Phase 2 gateway)
6. **Reasonable footprint when optimized** - ~1GB memory with lightweight distribution, acceptable for PoC

**Key trade-off**: Trino's cold start is slower than pg_duckdb (~30-60s vs ~5s), and its idle footprint is higher (~1GB vs ~200-500MB). These are acceptable given the native Iceberg catalog integration and standard SQL benefits.

### Why RustFS over SeaweedFS?

1. **Single container** - RustFS runs as one container vs SeaweedFS's 4 (master, volume, filer, s3)
2. **Built-in web console** - Management UI included on port 9001
3. **S3 compatible** - Drop-in replacement with standard S3 API on port 9000
4. **Simpler operations** - Fewer moving parts, easier to configure and debug

---

## 3. Architecture

### Phase 1: Without Gateway (Initial PoC)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Phase 1 Architecture (No Gateway)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│    PowerBI Desktop                                                          │
│    └── Trino ODBC Driver                                                    │
│              │                                                              │
│              ▼ port 8080                                                    │
│    ┌────────────────────────────────────────────────────────────────┐       │
│    │        Trino (Lightweight, Manual Start/Stop)                  │       │
│    │        • Native Iceberg connector                              │       │
│    │        • REST catalog integration with LakeKeeper              │       │
│    │        • Stripped to Iceberg connector only                     │       │
│    │        • Auth: username/password                                │       │
│    └────────────────────────────────────────────────────────────────┘       │
│              │                         │                                    │
│              ▼                         ▼                                    │
│    ┌──────────────────┐      ┌─────────────────────┐                       │
│    │   LakeKeeper     │      │      RustFS         │                       │
│    │   port 8181      │      │   S3: port 9000     │                       │
│    │   (REST Catalog) │      │   Console: 9001     │                       │
│    │   Always Running │      │   Always Running    │                       │
│    └────────┬─────────┘      └─────────────────────┘                       │
│             │                                                               │
│             ▼                                                               │
│    ┌──────────────────┐                                                    │
│    │    PostgreSQL    │                                                     │
│    │    port 5433     │                                                     │
│    │ (LakeKeeper DB)  │                                                    │
│    │  Always Running  │                                                    │
│    └──────────────────┘                                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Phase 2: With Rust Gateway (Future)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Phase 2 Architecture (With Gateway)                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│    PowerBI Desktop                                                          │
│    └── Trino ODBC Driver                                                    │
│              │                                                              │
│              ▼ port 8080                                                    │
│    ┌────────────────────────────────────────────────────────────────┐       │
│    │           Rust TCP Gateway (Always Running, ~10-20MB)          │       │
│    │           • Listens for Trino connections                      │       │
│    │           • Starts Trino container on first connection          │       │
│    │           • Proxies TCP traffic transparently                  │       │
│    │           • Tracks idle time per connection                    │       │
│    │           • Stops Trino after 1 hour of no connections         │       │
│    └────────────────────────────────────────────────────────────────┘       │
│              │                                                              │
│              ▼ port 8080 (internal)                                         │
│    ┌────────────────────────────────────────────────────────────────┐       │
│    │        Trino Lightweight (On-Demand)                           │       │
│    │        [Same as Phase 1]                                       │       │
│    └────────────────────────────────────────────────────────────────┘       │
│              │                         │                                    │
│              ▼                         ▼                                    │
│         [LakeKeeper]              [RustFS]                                  │
│              │                                                              │
│              ▼                                                              │
│         [PostgreSQL]                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Component Specifications

### 4.1 RustFS (Object Storage)

**Purpose**: S3-compatible object storage for Iceberg data files (Parquet)

**Image**: `rustfs/rustfs:latest`

**Architecture**: Single container with embedded S3 API and web console. Uses erasure-coded volumes for data integrity.

**Initialization**: Requires a permissions init container to set ownership on data volumes before first start. An S3 bucket (`datalake`) must be created after RustFS is healthy, via an init container using the AWS CLI.

**S3 Credentials**:
- Access Key: `admin`
- Secret Key: `admin123`
- Bucket: `datalake`
- Endpoint: `http://rustfs:9000`

**Ports**:
- `9000` - S3 API
- `9001` - Web console

### 4.2 PostgreSQL (LakeKeeper Metadata)

**Purpose**: Store LakeKeeper catalog metadata

**Image**: `postgres:16`

**Port**: `5433` (host) → `5432` (container)

### 4.3 LakeKeeper (Iceberg REST Catalog)

**Purpose**: Manage Iceberg table metadata via REST API

**Image**: `quay.io/lakekeeper/catalog:latest`

**Architecture**: LakeKeeper requires three steps to initialize:
1. **Migration** - A one-time `migrate` command to set up the database schema
2. **Serve** - The main catalog server process
3. **Bootstrap** - A one-time API call to `POST /management/v1/bootstrap` to accept terms and initialize

Warehouses are created programmatically via the management API (`POST /management/v1/warehouse`) with S3 storage profile configuration pointing to RustFS.

**Configuration**: Uses `LAKEKEEPER__PG_DATABASE_URL_READ` and `LAKEKEEPER__PG_DATABASE_URL_WRITE` connection strings (not individual host/port/user env vars).

**API Endpoints**:
- REST Catalog: `http://lakekeeper:8181/catalog`
- Management API: `http://lakekeeper:8181/management/v1/`
- Web UI: `http://lakekeeper:8181/ui/`
- Health: via built-in `lakekeeper healthcheck` command

### 4.4 Trino (Query Engine)

**Purpose**: Execute SQL queries against Iceberg tables via native Iceberg connector

**Approach**: Build a lightweight Trino distribution following the [lightweight Trino approach](https://dev.to/resurfacelabs/building-a-lightweight-trino-distribution-54h7):

**Lightweight distribution strategy**:
1. **Strip connectors** - Remove all connectors except Iceberg (standard Trino ships ~30+ connectors)
2. **Alpine-based image** - Use a minimal JDK base image instead of the default
3. **Memory tuning** - Configure for single-user PoC workloads (`query.max-memory=1GB`, reduced history/expiry settings)

**Iceberg connector configuration**:
- `connector.name=iceberg`
- `iceberg.catalog.type=rest`
- `iceberg.rest-catalog.uri=http://lakekeeper:8181/catalog`
- `iceberg.rest-catalog.warehouse=datalake-warehouse`

**Connection Details** (for PowerBI and other clients):
- Host: `localhost` (or server IP)
- Port: `8080`
- Protocol: Trino native protocol
- Auth: Username/password

**PowerBI Connectivity**: Requires a Trino ODBC driver (Starburst or Simba) instead of the PostgreSQL ODBC driver previously used with pg_duckdb.

---

## 5. Data Population Strategy

### Approach: Static Sample Data via PyIceberg

A Python init container (`init-data`) uses PyIceberg to create and populate sample Iceberg tables. It connects to LakeKeeper's REST catalog and writes Parquet data to RustFS.

The script:
1. Waits for LakeKeeper to be healthy
2. Creates a warehouse via the management API (with RustFS S3 storage profile)
3. Creates a `demo` namespace
4. Populates `demo.sales` (10,000 records) and `demo.customers` (1,000 records)

The init container runs on-demand via Docker Compose profiles (`docker compose --profile init up data-init`).

**Dependencies**: `pyiceberg[s3fs,pyarrow]`, `pyarrow`, `s3fs`, `requests`

---

## 6. Network Configuration

### Docker Network

All services communicate on an internal Docker network (`datalake-network`, bridge driver).

### Port Mappings (Host → Container)

| Service | Host Port | Container Port | Purpose |
|---------|-----------|----------------|---------|
| Trino | 8080 | 8080 | Trino native protocol |
| LakeKeeper | 8181 | 8181 | REST Catalog API + Web UI |
| RustFS S3 | 9000 | 9000 | S3 API |
| RustFS Console | 9001 | 9001 | Web management console |
| PostgreSQL (catalog) | 5433 | 5432 | LakeKeeper metadata |

---

## 7. Implementation Phases

### Phase 1: Basic PoC (No Gateway)

**Scope**:
- All infrastructure services running
- Trino runs continuously (manual start/stop)
- Sample data populated
- PowerBI can connect and query

**Services**:
1. RustFS (single container + permissions init)
2. S3 bucket creation (init container, runs once)
3. PostgreSQL (for LakeKeeper)
4. LakeKeeper (migration + serve + bootstrap)
5. Trino (lightweight distribution)
6. Data initialization container (runs once, via profile)

**Deliverables**:
- `docker-compose.yml`
- `trino/` - Trino configuration and lightweight Dockerfile
- `init-data/` - PyIceberg data population
- `README.md`

**Estimated Resource Usage (Idle)**:
| Service | Memory | CPU |
|---------|--------|-----|
| RustFS | ~100-200MB | Minimal |
| PostgreSQL (catalog) | ~50-100MB | Minimal |
| LakeKeeper | ~100-200MB | Minimal |
| Trino (lightweight) | ~500MB-1GB | Minimal |
| **Total** | ~750MB-1.5GB | Low |

### Phase 2: Add Rust Gateway (Future)

**Scope**:
- Implement Rust TCP gateway
- Gateway starts/stops Trino container on demand
- 1-hour idle timeout
- Trino truly scales to zero

**Gateway Requirements**:
- Listen on port 8080
- On first connection:
    - Start Trino container via Docker API
    - Wait for health check
    - Proxy connection
- Track active connections
- After last connection closes + 1 hour idle:
    - Stop Trino container
- Minimal footprint (~10-20MB)

**Gateway Technology**:
- Language: Rust
- Libraries: tokio (async), bollard (Docker API)

**Estimated Resource Usage (Idle, Phase 2)**:
| Service | Memory | CPU |
|---------|--------|-----|
| RustFS | ~100-200MB | Minimal |
| PostgreSQL (catalog) | ~50-100MB | Minimal |
| LakeKeeper | ~100-200MB | Minimal |
| Rust Gateway | ~10-20MB | Minimal |
| Trino | **0MB** (stopped) | **None** |
| **Total** | ~260-470MB | Very Low |

### Phase 3: Kubernetes Migration (Future)

**Scope**:
- Convert docker-compose to Kubernetes manifests
- Use KEDA or custom controller for scale-to-zero
- Persistent volumes for RustFS and PostgreSQL
- Ingress configuration for external access

---

## 8. File Structure

```
digitalbuff-datalake-stack/
├── docker-compose.yml
├── README.md
├── spec.md                        # This document
├── .env                           # Environment variables
├── trino/
│   ├── Dockerfile                 # Lightweight Trino build
│   └── etc/                       # Trino configuration
│       ├── config.properties
│       ├── catalog/
│       │   └── iceberg.properties # Iceberg connector config
│       └── jvm.config
├── init-data/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── populate.py
└── gateway/                       # Phase 2
    ├── Cargo.toml
    ├── src/
    │   └── main.rs
    └── Dockerfile
```

---

## 9. Known Limitations and Considerations

### Trino (Lightweight)

1. **Cold start time** - Trino takes ~30-60s to start vs ~5s for simpler engines; acceptable for Phase 2 gateway scenario
2. **Memory floor** - Even with lightweight tuning, Trino needs ~500MB-1GB minimum; JVM overhead is unavoidable
3. **Connector stripping** - Must maintain a custom Dockerfile to keep only the Iceberg connector
4. **JVM tuning** - Requires careful JVM configuration to avoid excessive heap allocation in constrained environments

### RustFS

1. **Persistence** - Requires properly configured volumes and a permissions init container
2. **S3 Compatibility** - Some advanced S3 features may not be supported

### PowerBI

1. **ODBC driver** - Requires Trino-specific ODBC driver (Starburst or Simba) instead of the more common PostgreSQL ODBC driver
2. **DirectQuery** - Trino SQL dialect differences may affect some DirectQuery operations

### LakeKeeper

1. **Initialization** - Requires explicit bootstrap, migration, and warehouse creation via API
2. **Configuration** - Uses PostgreSQL connection URL format, not individual host/port env vars

---

## 10. References

### Documentation

- Trino: https://trino.io/docs/current/
- Trino Iceberg Connector: https://trino.io/docs/current/connector/iceberg.html
- Lightweight Trino Distribution: https://dev.to/resurfacelabs/building-a-lightweight-trino-distribution-54h7
- LakeKeeper: https://github.com/lakekeeper/lakekeeper
- RustFS: https://github.com/rustfs/rustfs
- PyIceberg: https://py.iceberg.apache.org/

### Docker Images

- Trino: custom lightweight build (based on `trinodb/trino:latest`)
- RustFS: `rustfs/rustfs:latest`
- PostgreSQL: `postgres:16`
- LakeKeeper: `quay.io/lakekeeper/catalog:latest`

---

## 11. Summary

This architecture provides a lightweight, cost-effective data lake solution that:

1. **Minimizes idle resource usage** - Only essential services run continuously (~750MB-1.5GB)
2. **Supports true scale-to-zero** - Query engine can fully stop in Phase 2 (~260-470MB idle)
3. **Uses open standards** - Apache Iceberg, S3-compatible storage, standard SQL
4. **Native catalog integration** - Trino's Iceberg connector talks directly to LakeKeeper REST catalog
5. **Enables familiar tooling** - PowerBI connects via Trino ODBC; tables appear as standard database objects
6. **Keeps data server-side** - Only query results sent to clients

The phased approach allows for immediate PoC validation while providing a clear path to production-ready scale-to-zero architecture.
