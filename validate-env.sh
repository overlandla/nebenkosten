#!/bin/bash
# Validate environment files exist before starting Dagster

set -e

SECRETS_DIR="./secrets"
REQUIRED_FILES=("influxdb.env" "tibber.env")
MISSING_FILES=()

echo "Validating environment files..."

for file in "${REQUIRED_FILES[@]}"; do
    filepath="${SECRETS_DIR}/${file}"
    if [ ! -f "$filepath" ]; then
        MISSING_FILES+=("$file")
        echo "❌ Missing: $filepath"

        # Check if example exists
        if [ -f "${filepath}.example" ]; then
            echo "   → Template available: ${filepath}.example"
        fi
    else
        echo "✓ Found: $filepath"
    fi
done

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    echo ""
    echo "ERROR: Missing required environment files:"
    for file in "${MISSING_FILES[@]}"; do
        echo "  - ${SECRETS_DIR}/${file}"
    done
    echo ""
    echo "Please create these files from the .example templates:"
    echo "  cp ${SECRETS_DIR}/influxdb.env.example ${SECRETS_DIR}/influxdb.env"
    echo "  cp ${SECRETS_DIR}/tibber.env.example ${SECRETS_DIR}/tibber.env"
    echo ""
    echo "Then edit the files and fill in your actual credentials."
    exit 1
fi

echo ""
echo "✓ All environment files present"
echo ""
