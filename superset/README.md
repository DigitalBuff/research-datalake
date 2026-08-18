# Superset Configuration

Apache Superset - Modern data visualization and exploration platform with Trino support.

## Configuration

- **Dockerfile**: Custom Superset image with Trino database driver pre-installed
- **init-superset.sh**: Initialization script that sets up the database and admin user
- SQLite database for Superset metadata (persists in `superset-data` volume)
- Admin user automatically created on first startup
- Trino Python driver (`trino` package) included for native Trino connectivity

## Default Credentials

- Username: `admin`
- Password: `admin`

**Important**: Change the password after first login!

## Using Superset

1. Open http://localhost:8088 in your browser
2. Log in with default credentials
3. Add a Trino database connection:
   - Go to **Data** → **Databases** → **+ Database**
   - Select **Trino** (or use "Other" if not listed)
   - **SQLAlchemy URI**: `trino://trino:trino@trino.datalake.local:443/iceberg`
   - Advanced → Other → Engine Parameters:
     ``` 
     {"connect_args": {"http_scheme": "https", "verify": "/etc/ssl/datalake/root.pem"}}
     ```
   - Test connection and save

4. Explore your data:
   - Go to **SQL Lab** → **SQL Editor**
   - Select your Trino database
   - Schema: `demo`
   - Query your Iceberg tables:
     ```sql
     SELECT * FROM sales LIMIT 100;

     SELECT
         category,
         region,
         COUNT(*) as num_sales,
         SUM(total_amount) as revenue
     FROM sales
     GROUP BY category, region
     ORDER BY revenue DESC;
     ```

5. Create visualizations and dashboards from your queries

## Features

- Interactive SQL editor
- Rich data visualizations (charts, maps, dashboards)
- Query result caching
- Data exploration and drill-down
- Shareable dashboards
- Role-based access control
