# Configuration Database - Makefile Integration

This document explains how the shared configuration database is automatically set up through the existing `make install-dagster` and `make update-dagster` procedures.

## Overview

The configuration database setup is now **fully integrated** into the standard Dagster installation and update procedures. You don't need to run any separate setup scripts - everything happens automatically.

## What Happens Automatically

### During `make install-dagster`

1. **PostgreSQL Installation**
   - Installs PostgreSQL if not present
   - Creates `dagster` user with superuser privileges

2. **Database Creation**
   - Creates `dagster` database (for Dagster metadata)
   - Creates `nebenkosten_config` database (for shared configuration) ✨ NEW

3. **Schema Initialization**
   - Runs `/database/schema.sql` to create tables ✨ NEW
   - Creates 6 tables: meters, households, household_meters, settings, users, audit_log

4. **Configuration Migration**
   - Runs `/database/migrate_yaml_to_postgres.py` ✨ NEW
   - Imports existing YAML configs to PostgreSQL
   - Migrates 39 meters, 5 households, system settings

5. **Environment Variables**
   - All systemd services get CONFIG_DB_* environment variables ✨ NEW
   - Dagster can immediately access the config database

### During `make update-dagster`

1. **Code Update**
   - Pulls latest code from git
   - Updates Python dependencies

2. **Systemd Services Update**
   - Copies latest systemd service files ✨ NEW
   - Ensures CONFIG_DB_* environment variables are present

3. **Database Check**
   - Checks if `nebenkosten_config` database exists ✨ NEW
   - Creates it if missing (for existing installations)

4. **Schema Check**
   - Checks if schema is initialized ✨ NEW
   - Runs schema initialization if needed

5. **Migration**
   - Migrates YAML configs to database if schema was just created ✨ NEW
   - Existing data is preserved

## Files Modified

### Installation Scripts

**`workflows_dagster/install/setup-postgresql.sh`**
```bash
# Now creates TWO databases instead of one:
- dagster              (Dagster metadata)
- nebenkosten_config   (shared configuration) ✨ NEW
```

**`workflows_dagster/install/dagster-workflows-install.sh`**

Added for **fresh installs**:
```bash
# Initialize configuration database schema
sudo -u postgres psql -d nebenkosten_config -f database/schema.sql

# Migrate YAML configs to database
python database/migrate_yaml_to_postgres.py
```

Added for **updates**:
```bash
# Update systemd service files
cp workflows_dagster/systemd/*.service /etc/systemd/system/

# Create config database if missing
CREATE DATABASE nebenkosten_config OWNER dagster

# Initialize schema if needed
psql -d nebenkosten_config -f database/schema.sql

# Migrate configs if schema was just created
python database/migrate_yaml_to_postgres.py
```

### Systemd Service Files

All three service files updated with environment variables:

**`workflows_dagster/systemd/dagster-daemon.service`**
**`workflows_dagster/systemd/dagster-webserver.service`**
**`workflows_dagster/systemd/dagster-user-code.service`**

Added:
```ini
Environment="CONFIG_DB_HOST=localhost"
Environment="CONFIG_DB_PORT=5432"
Environment="CONFIG_DB_NAME=nebenkosten_config"
Environment="CONFIG_DB_USER=dagster"
Environment="CONFIG_DB_PASSWORD=dagster"
```

## Usage

### Fresh Installation

On a new LXC container:

```bash
# Clone repository
cd /path/to/project
git clone https://github.com/overlandla/nebenkosten.git
cd nebenkosten

# Run Makefile installation (does EVERYTHING)
make install-dagster
```

**What happens:**
- ✅ PostgreSQL installed
- ✅ Both databases created
- ✅ Configuration database schema initialized
- ✅ YAML configs migrated to PostgreSQL
- ✅ Dagster services started with DB access
- ✅ Ready to use immediately!

### Updating Existing Installation

On an existing Dagster LXC:

```bash
# Pull latest code
cd /opt/dagster-workflows/nebenkosten
git pull origin main

# Run Makefile update (does EVERYTHING)
make update-dagster
```

**What happens:**
- ✅ Services stopped
- ✅ Code updated
- ✅ Dependencies updated
- ✅ Systemd services updated with new env vars
- ✅ Config database created (if missing)
- ✅ Schema initialized (if needed)
- ✅ Configs migrated (if needed)
- ✅ Services restarted
- ✅ Everything works!

## Verification

After installation or update, verify everything is set up correctly:

### 1. Check Databases Exist

```bash
sudo -u postgres psql -l | grep nebenkosten
```

Expected output:
```
 dagster             | dagster  | UTF8     | ...
 nebenkosten_config  | dagster  | UTF8     | ...
```

### 2. Check Tables Exist

```bash
sudo -u postgres psql -d nebenkosten_config -c "\dt"
```

Expected output:
```
 public | audit_log         | table | dagster
 public | household_meters  | table | dagster
 public | households        | table | dagster
 public | meters            | table | dagster
 public | settings          | table | dagster
 public | users             | table | dagster
```

### 3. Check Data Was Migrated

```bash
sudo -u postgres psql -d nebenkosten_config -c "SELECT COUNT(*) FROM meters;"
sudo -u postgres psql -d nebenkosten_config -c "SELECT COUNT(*) FROM households;"
sudo -u postgres psql -d nebenkosten_config -c "SELECT COUNT(*) FROM settings;"
```

Expected output:
```
 count
-------
    39    <- meters
(1 row)

 count
-------
     5    <- households
(1 row)

 count
-------
     4    <- settings (gas_conversion, influxdb, tibber, workflows)
(1 row)
```

### 4. Check Dagster Has Access

```bash
# Check logs for database loading messages
sudo journalctl -u dagster-daemon -n 100 | grep -i "config\|database"
```

Expected to see:
```
Loading configuration from PostgreSQL database
Loaded 39 meters from database
Loaded 5 households from database
```

If you see this instead (should only happen if database fails):
```
Loading configuration from YAML files
```

Then check database connection and permissions.

## Environment Variables

All Dagster services now have these environment variables:

```bash
# Dagster Metadata Database (existing)
DAGSTER_POSTGRES_USER=dagster
DAGSTER_POSTGRES_PASSWORD=dagster
DAGSTER_POSTGRES_DB=dagster
DAGSTER_POSTGRES_HOST=localhost
DAGSTER_POSTGRES_PORT=5432

# Configuration Database (NEW)
CONFIG_DB_HOST=localhost
CONFIG_DB_PORT=5432
CONFIG_DB_NAME=nebenkosten_config
CONFIG_DB_USER=dagster
CONFIG_DB_PASSWORD=dagster
```

## Python Code Usage

In Dagster workflows, the ConfigResource now automatically uses the database:

```python
from dagster import asset
from dagster_project.resources import ConfigResource

@asset
def my_asset(config: ConfigResource):
    # Automatically loads from PostgreSQL database
    # Falls back to YAML if database unavailable
    cfg = config.load_config()

    # Use meters, households, settings
    meters = cfg['meters']
    households = cfg['households']
```

## Troubleshooting

### Database Not Created

**Symptom**: `nebenkosten_config` database doesn't exist after installation

**Check**:
```bash
sudo -u postgres psql -l | grep nebenkosten
```

**Fix**:
```bash
# Create manually
sudo -u postgres psql -c "CREATE DATABASE nebenkosten_config OWNER dagster;"

# Initialize schema
sudo -u postgres psql -d nebenkosten_config -f /opt/dagster-workflows/nebenkosten/database/schema.sql

# Migrate configs
cd /opt/dagster-workflows/nebenkosten
/opt/dagster-workflows/venv/bin/python database/migrate_yaml_to_postgres.py
```

### Schema Not Initialized

**Symptom**: Database exists but no tables

**Check**:
```bash
sudo -u postgres psql -d nebenkosten_config -c "\dt"
```

**Fix**:
```bash
sudo -u postgres psql -d nebenkosten_config -f /opt/dagster-workflows/nebenkosten/database/schema.sql
```

### Environment Variables Missing

**Symptom**: Dagster can't connect to config database

**Check**:
```bash
sudo systemctl show dagster-daemon | grep CONFIG_DB
```

**Fix**:
```bash
# Update service files
cd /opt/dagster-workflows/nebenkosten
sudo cp workflows_dagster/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart dagster-*
```

### Dagster Still Using YAML

**Symptom**: Logs show "Loading configuration from YAML files"

**Possible Causes**:
1. Database doesn't exist
2. Schema not initialized
3. Environment variables not set
4. Connection error

**Check**:
```bash
# Verify database exists
sudo -u postgres psql -l | grep nebenkosten_config

# Verify tables exist
sudo -u postgres psql -d nebenkosten_config -c "\dt"

# Verify env vars
sudo systemctl show dagster-daemon | grep CONFIG_DB

# Test connection
sudo -u postgres psql -d nebenkosten_config -c "SELECT COUNT(*) FROM meters;"
```

## Production Considerations

### Security

For production deployments, change default passwords:

```bash
# Change PostgreSQL password
sudo -u postgres psql -c "ALTER USER dagster WITH PASSWORD 'strong_random_password';"

# Update systemd service files
sudo nano /etc/systemd/system/dagster-daemon.service
# Change: Environment="CONFIG_DB_PASSWORD=strong_random_password"

# Update for all three services:
# - dagster-daemon.service
# - dagster-webserver.service
# - dagster-user-code.service

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart dagster-*
```

### Multi-LXC Setup

If Next.js dashboard is on a different LXC, allow remote connections:

```bash
# On Dagster LXC (PostgreSQL server)
PG_VERSION=$(ls /etc/postgresql/ | head -n1)

# Edit postgresql.conf
sudo nano /etc/postgresql/$PG_VERSION/main/postgresql.conf
# Add: listen_addresses = 'localhost,192.168.1.XXX'

# Edit pg_hba.conf
sudo nano /etc/postgresql/$PG_VERSION/main/pg_hba.conf
# Add: host  nebenkosten_config  dagster  192.168.1.YYY/32  md5

# Restart PostgreSQL
sudo systemctl restart postgresql
```

Then on Next.js LXC, set:
```bash
CONFIG_DATABASE_URL=postgresql://dagster:password@192.168.1.XXX:5432/nebenkosten_config
```

## Summary

✅ **No manual setup required** - Everything automated
✅ **Works for fresh installs** - Database created and migrated
✅ **Works for updates** - Existing installations get database
✅ **Safe and idempotent** - Can run multiple times
✅ **YAML fallback** - Still works if database unavailable
✅ **Environment variables** - All services have access
✅ **Zero downtime updates** - Services restart cleanly

The configuration database is now a first-class citizen in the Dagster installation process!
