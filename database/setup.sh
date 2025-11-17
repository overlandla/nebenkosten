#!/bin/bash

# Nebenkosten Shared Configuration Database Setup Script
# This script automates the setup of the shared PostgreSQL configuration database

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DB_NAME="${CONFIG_DB_NAME:-nebenkosten_config}"
DB_USER="${CONFIG_DB_USER:-dagster}"
DB_HOST="${CONFIG_DB_HOST:-localhost}"
DB_PORT="${CONFIG_DB_PORT:-5432}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Nebenkosten Configuration Database Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Check if running as correct user
if [ "$EUID" -eq 0 ]; then
    print_error "Do not run this script as root. Run as your normal user with sudo access."
    exit 1
fi

# Check if PostgreSQL is installed
print_info "Checking PostgreSQL installation..."
if ! command -v psql &> /dev/null; then
    print_error "PostgreSQL is not installed. Please install it first:"
    echo "  sudo apt-get install postgresql postgresql-contrib"
    exit 1
fi
print_success "PostgreSQL is installed"

# Check if PostgreSQL is running
print_info "Checking if PostgreSQL is running..."
if ! sudo systemctl is-active --quiet postgresql; then
    print_error "PostgreSQL is not running. Starting it..."
    sudo systemctl start postgresql
    sleep 2
fi
print_success "PostgreSQL is running"

# Check if database already exists
print_info "Checking if database '$DB_NAME' exists..."
if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    print_warning "Database '$DB_NAME' already exists"
    read -p "Do you want to drop and recreate it? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Dropping database '$DB_NAME'..."
        sudo -u postgres psql -c "DROP DATABASE $DB_NAME;"
        print_success "Database dropped"
    else
        print_info "Skipping database creation"
        DB_EXISTS=true
    fi
fi

# Create database if it doesn't exist
if [ "$DB_EXISTS" != "true" ]; then
    print_info "Creating database '$DB_NAME'..."
    sudo -u postgres psql <<EOF
CREATE DATABASE $DB_NAME OWNER $DB_USER;
\c $DB_NAME
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
EOF
    print_success "Database created"
fi

# Initialize schema
print_info "Initializing database schema..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -f "$SCRIPT_DIR/schema.sql" ]; then
    print_error "schema.sql not found in $SCRIPT_DIR"
    exit 1
fi

sudo -u postgres psql -d "$DB_NAME" -f "$SCRIPT_DIR/schema.sql" > /dev/null 2>&1
print_success "Schema initialized"

# Verify tables were created
print_info "Verifying tables..."
TABLE_COUNT=$(sudo -u postgres psql -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
if [ "$TABLE_COUNT" -lt 5 ]; then
    print_error "Expected at least 5 tables, found $TABLE_COUNT"
    exit 1
fi
print_success "Found $TABLE_COUNT tables"

# Run migration
print_info "Migrating YAML configuration to database..."
if [ ! -f "$SCRIPT_DIR/migrate_yaml_to_postgres.py" ]; then
    print_error "migrate_yaml_to_postgres.py not found in $SCRIPT_DIR"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    exit 1
fi

# Check if required Python packages are installed
if ! python3 -c "import psycopg2" 2>/dev/null; then
    print_warning "psycopg2 is not installed. Installing..."
    pip3 install psycopg2-binary || sudo pip3 install psycopg2-binary
fi

if ! python3 -c "import yaml" 2>/dev/null; then
    print_warning "PyYAML is not installed. Installing..."
    pip3 install pyyaml || sudo pip3 install pyyaml
fi

# Run migration
cd "$SCRIPT_DIR/.." || exit 1
python3 "$SCRIPT_DIR/migrate_yaml_to_postgres.py"

if [ $? -eq 0 ]; then
    print_success "Migration completed successfully"
else
    print_error "Migration failed"
    exit 1
fi

# Display summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Database Configuration:"
echo "  Host:     $DB_HOST"
echo "  Port:     $DB_PORT"
echo "  Database: $DB_NAME"
echo "  User:     $DB_USER"
echo ""
echo "Connection String:"
echo "  postgresql://$DB_USER:PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
echo ""
echo "Next Steps:"
echo "  1. Configure Next.js .env.local with CONFIG_DATABASE_URL"
echo "  2. Run 'npm run prisma:generate' in the dashboard directory"
echo "  3. Add CONFIG_DB_* environment variables to Dagster systemd services"
echo "  4. Restart Dagster services"
echo ""
echo "Admin UI will be available at:"
echo "  http://your-dashboard:3000/admin/config"
echo ""
print_success "All done!"
