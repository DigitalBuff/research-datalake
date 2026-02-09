"""
Simple data population script for PoC.
Creates sample Iceberg tables with static data using LakeKeeper REST catalog.
"""

import os
import random
import time
import urllib.request
import urllib.error
from dataclasses import dataclass

import requests
import pyarrow as pa
from datetime import datetime, timedelta

from pyiceberg.catalog import load_catalog
from pyiceberg.schema import Schema
from pyiceberg.types import (
    NestedField,
    StringType,
    LongType,
    DoubleType,
    TimestampType
)
import pyiceberg.io.fsspec


@dataclass
class Config:
    """Configuration loaded from environment variables"""
    lakekeeper_uri: str
    lakekeeper_warehouse: str
    s3_endpoint: str
    s3_bucket: str
    s3_access_key_id: str
    s3_secret_access_key: str
    s3_region: str

    @classmethod
    def from_env(cls) -> 'Config':
        """Initialize configuration from environment variables"""
        return cls(
            lakekeeper_uri=os.getenv("LAKEKEEPER_URI", ""),
            lakekeeper_warehouse=os.getenv("LAKEKEEPER_WAREHOUSE", ""),
            s3_endpoint=os.getenv("S3_ENDPOINT", ""),
            s3_bucket=os.getenv("S3_BUCKET", ""),
            s3_access_key_id=os.getenv("S3_ACCESS_KEY_ID", ""),
            s3_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY", ""),
            s3_region=os.getenv("S3_REGION", "us-east-1")
        )

def wait_for_lakekeeper(config: Config) -> None:
    """Wait for LakeKeeper to be ready"""
    print("Waiting for LakeKeeper to be ready...")
    max_retries = 30
    for i in range(max_retries):
        try:
            urllib.request.urlopen(config.lakekeeper_uri + "/health", timeout=5)
            print("LakeKeeper is ready!")
            return
        except (urllib.error.URLError, TimeoutError):
            print(f"Attempt {i+1}/{max_retries}: LakeKeeper not ready yet...")
            time.sleep(2)
    raise Exception("LakeKeeper did not become ready in time")

def create_warehouse_if_not_exists(config: Config) -> None:
    """Create the warehouse if it doesn't exist"""
    management_url = config.lakekeeper_uri + "/management/v1/warehouse"

    print(f"Checking if warehouse '{config.lakekeeper_warehouse}' exists...")

    warehouse_config = {
        "warehouse-name": config.lakekeeper_warehouse,
        "storage-profile": {
            "type": "s3",
            "bucket": config.s3_bucket,
            "endpoint": config.s3_endpoint,
            "path-style-access": True,
            "region": config.s3_region,
            "key-prefix": "",
            "flavor": "s3-compat",
            "sts-enabled": False
        },
        "storage-credential": {
            "type": "s3",
            "credential-type": "access-key",
            "aws-access-key-id": config.s3_access_key_id,
            "aws-secret-access-key": config.s3_secret_access_key
        }
    }

    try:
        response = requests.post(
            management_url,
            json=warehouse_config,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 201 or response.status_code == 200:
            print(f"✓ Warehouse '{config.lakekeeper_warehouse}' created successfully")
        elif response.status_code >= 400 or response.status_code < 500:
            print(f"✓ Warehouse '{config.lakekeeper_warehouse}' already exists")
        else:
            print(f"Warning: Unexpected response when creating warehouse: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Warning: Could not create warehouse: {e}")
        print("Proceeding anyway - warehouse might already exist")

def main() -> None:
    # Initialize configuration from environment variables
    config = Config.from_env()

    # Wait for LakeKeeper to be ready
    wait_for_lakekeeper(config)

    # Create warehouse if it doesn't exist
    create_warehouse_if_not_exists(config)

    # Configure s3fs to use environment credentials and disable REST catalog signing
    # This is necessary because LakeKeeper vends static credentials without session tokens
    os.environ['AWS_S3_ALLOW_UNSAFE_RENAME'] = 'true'

    # Patch to disable REST signer - replace with a no-op function that doesn't sign
    pyiceberg.io.fsspec.s3v4_rest_signer = lambda request, **kwargs: None

    # Connect to LakeKeeper REST catalog
    print("Connecting to LakeKeeper catalog...")
    catalog = load_catalog(
        "lakekeeper",
        **{
            "type": "rest",
            "uri": config.lakekeeper_uri + "/catalog",
            "warehouse": config.lakekeeper_warehouse,
            "s3.endpoint": config.s3_endpoint,
            "s3.access-key-id": config.s3_access_key_id,
            "s3.secret-access-key": config.s3_secret_access_key,
            "s3.region": config.s3_region
        }
    )

    # Create namespace
    print("Creating namespace 'demo'...")
    try:
        catalog.create_namespace("demo")
        print("Namespace 'demo' created")
    except Exception as e:
        print(f"Namespace might already exist: {e}")

    # Define schema for sales table
    print("Creating sales table schema...")
    sales_schema = Schema(
        NestedField(1, "sale_id", LongType(), required=True),
        NestedField(2, "product_name", StringType(), required=True),
        NestedField(3, "category", StringType(), required=True),
        NestedField(4, "quantity", LongType(), required=True),
        NestedField(5, "unit_price", DoubleType(), required=True),
        NestedField(6, "total_amount", DoubleType(), required=True),
        NestedField(7, "sale_date", TimestampType(), required=True),
        NestedField(8, "region", StringType(), required=True),
    )

    # Create table
    print("Creating sales table...")
    try:
        sales_table = catalog.create_table(
            "demo.sales",
            schema=sales_schema
        )
        print("Sales table created")
    except Exception as e:
        print(f"Table might already exist, loading it: {e}")
        sales_table = catalog.load_table("demo.sales")

    # Generate sample data
    print("Generating sample sales data...")
    products = [
        ("Laptop", "Electronics", 999.99),
        ("Headphones", "Electronics", 149.99),
        ("Desk Chair", "Furniture", 299.99),
        ("Monitor", "Electronics", 399.99),
        ("Keyboard", "Electronics", 79.99),
        ("Mouse", "Electronics", 49.99),
        ("Desk", "Furniture", 449.99),
        ("Webcam", "Electronics", 89.99),
    ]

    regions = ["North", "South", "East", "West"]

    # Create 10,000 sample records
    records = []
    base_date = datetime(2024, 1, 1)

    for i in range(10000):
        product_name, category, unit_price = random.choice(products)
        quantity = random.randint(1, 10)
        records.append({
            "sale_id": i + 1,
            "product_name": product_name,
            "category": category,
            "quantity": quantity,
            "unit_price": unit_price,
            "total_amount": quantity * unit_price,
            "sale_date": base_date + timedelta(days=random.randint(0, 365)),
            "region": random.choice(regions),
        })

    # Convert to PyArrow table with explicit schema (non-nullable fields)
    print("Writing sales data to Iceberg table...")
    arrow_schema = pa.schema([
        pa.field("sale_id", pa.int64(), nullable=False),
        pa.field("product_name", pa.string(), nullable=False),
        pa.field("category", pa.string(), nullable=False),
        pa.field("quantity", pa.int64(), nullable=False),
        pa.field("unit_price", pa.float64(), nullable=False),
        pa.field("total_amount", pa.float64(), nullable=False),
        pa.field("sale_date", pa.timestamp('us'), nullable=False),
        pa.field("region", pa.string(), nullable=False),
    ])
    arrow_table = pa.Table.from_pylist(records, schema=arrow_schema)
    sales_table.append(arrow_table)

    print(f"✓ Created demo.sales table with {len(records)} records")

    # Create a second table for demonstration
    print("\nCreating customers table schema...")
    customers_schema = Schema(
        NestedField(1, "customer_id", LongType(), required=True),
        NestedField(2, "name", StringType(), required=True),
        NestedField(3, "email", StringType(), required=True),
        NestedField(4, "region", StringType(), required=True),
        NestedField(5, "created_at", TimestampType(), required=True),
    )

    print("Creating customers table...")
    try:
        customers_table = catalog.create_table(
            "demo.customers",
            schema=customers_schema
        )
        print("Customers table created")
    except Exception as e:
        print(f"Table might already exist, loading it: {e}")
        customers_table = catalog.load_table("demo.customers")

    # Generate customer data
    print("Generating sample customer data...")
    customer_records = []
    for i in range(1000):
        customer_records.append({
            "customer_id": i + 1,
            "name": f"Customer {i + 1}",
            "email": f"customer{i + 1}@example.com",
            "region": random.choice(regions),
            "created_at": base_date + timedelta(days=random.randint(-365, 0)),
        })

    print("Writing customer data to Iceberg table...")
    customers_schema = pa.schema([
        pa.field("customer_id", pa.int64(), nullable=False),
        pa.field("name", pa.string(), nullable=False),
        pa.field("email", pa.string(), nullable=False),
        pa.field("region", pa.string(), nullable=False),
        pa.field("created_at", pa.timestamp('us'), nullable=False),
    ])
    customers_arrow = pa.Table.from_pylist(customer_records, schema=customers_schema)
    customers_table.append(customers_arrow)

    print(f"✓ Created demo.customers table with {len(customer_records)} records")
    print("\n" + "="*50)
    print("Data population complete!")
    print("="*50)
    print(f"\nTables created:")
    print(f"  - demo.sales: {len(records)} records")
    print(f"  - demo.customers: {len(customer_records)} records")
    print(f"\nView in LakeKeeper UI: http://localhost:8181/ui/")

if __name__ == "__main__":
    main()
