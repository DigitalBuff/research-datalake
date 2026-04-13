#!/bin/bash
# Superset initialization script

set -e

echo "Initializing Superset..."

# Check if already initialized
if [ -f /app/superset_home/.initialized ]; then
    echo "Superset already initialized, skipping..."
    exit 0
fi

# Initialize the database
superset db upgrade

# Create admin user
superset fab create-admin \
    --username admin \
    --firstname Admin \
    --lastname User \
    --email admin@superset.com \
    --password admin

# Initialize Superset
superset init

# Mark as initialized
touch /app/superset_home/.initialized

echo "Superset initialization complete!"
