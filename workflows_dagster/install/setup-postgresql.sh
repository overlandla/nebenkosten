#!/usr/bin/env bash

# Copyright (c) 2024
# Author: overlandla
# License: MIT
# https://github.com/overlandla/nebenkosten
#
# This script sets up PostgreSQL for Dagster

set -e

# Colors for output
BL="\033[36m"
GN="\033[1;92m"
CL="\033[m"
YW="\033[1;33m"
RD="\033[01;31m"

msg_info() { echo -e "${BL}[INFO]${CL} $1"; }
msg_ok() { echo -e "${GN}[OK]${CL} $1"; }
msg_error() { echo -e "${RD}[ERROR]${CL} $1"; }

# PostgreSQL database configuration
POSTGRES_USER="dagster"
POSTGRES_PASSWORD="dagster"
POSTGRES_DB="dagster"

msg_info "Installing PostgreSQL"
apt-get install -y postgresql postgresql-contrib >/dev/null 2>&1
msg_ok "Installed PostgreSQL"

msg_info "Starting PostgreSQL service"
systemctl enable postgresql
systemctl start postgresql
msg_ok "PostgreSQL service started"

msg_info "Creating Dagster database and user"
# Create user and database
sudo -u postgres psql <<EOF
-- Create dagster user if it doesn't exist
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_user WHERE usename = '$POSTGRES_USER') THEN
    CREATE USER $POSTGRES_USER WITH PASSWORD '$POSTGRES_PASSWORD';
  END IF;
END
\$\$;

-- Create dagster database if it doesn't exist
SELECT 'CREATE DATABASE $POSTGRES_DB OWNER $POSTGRES_USER'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$POSTGRES_DB')\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $POSTGRES_DB TO $POSTGRES_USER;
ALTER USER $POSTGRES_USER WITH SUPERUSER;
EOF

msg_ok "Created Dagster database and user"

msg_info "Configuring PostgreSQL for local connections"
# Allow local connections (already default in Debian, but ensure it's set)
PG_VERSION=$(ls /etc/postgresql/ | head -n1)
PG_HBA="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"

# Ensure local connections are allowed (should already be there)
if ! grep -q "local.*all.*all.*trust" "$PG_HBA"; then
    echo "local   all             all                                     trust" >> "$PG_HBA"
fi
if ! grep -q "host.*all.*all.*127.0.0.1/32.*md5" "$PG_HBA"; then
    echo "host    all             all             127.0.0.1/32            md5" >> "$PG_HBA"
fi

systemctl reload postgresql
msg_ok "PostgreSQL configured"

msg_info "Testing database connection"
if sudo -u postgres psql -d $POSTGRES_DB -c '\q' 2>/dev/null; then
    msg_ok "Database connection successful"
else
    msg_error "Failed to connect to database"
    exit 1
fi
