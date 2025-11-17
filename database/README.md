# Nebenkosten Configuration Database

This directory contains the database schema and migration scripts for the configuration database used by both Dagster and Next.js.

## Architecture

- **Database Name**: `nebenkosten_config`
- **Location**: Same PostgreSQL instance as Dagster (typically same LXC)
- **User**: `dagster` (reuses existing Dagster database user)
- **Purpose**: Store mutable configuration (meters, households, settings) that can be edited via UI

## Database Structure

### Core Tables

1. **meters** - Meter definitions (physical, master, virtual)
2. **households** - Household/unit definitions
3. **household_meters** - Meter assignments to households
4. **settings** - Key-value store for system settings
5. **users** - User accounts (for future authentication)
6. **audit_log** - Audit trail of configuration changes

### Data Separation

- **PostgreSQL**: Configuration data (editable via UI)
- **InfluxDB**: Time-series data (meter readings, consumption)

## Setup Instructions

### 1. Create Database

On the PostgreSQL server (same LXC as Dagster):

```bash
# Connect as postgres user
sudo -u postgres psql

# Create the database
CREATE DATABASE nebenkosten_config OWNER dagster;

# Exit
\q
```

### 2. Initialize Schema

```bash
# From the nebenkosten project root
sudo -u postgres psql -d nebenkosten_config -f database/schema.sql
```

### 3. Migrate Existing Data

```bash
# Run the migration script to import YAML data
cd /home/user/nebenkosten
python database/migrate_yaml_to_postgres.py
```

### 4. Verify Setup

```bash
# Connect to the database
sudo -u postgres psql -d nebenkosten_config

# Check tables
\dt

# Check meters
SELECT id, name, meter_type, category FROM meters LIMIT 5;

# Check settings
SELECT key, description FROM settings;

# Exit
\q
```

## Connection Details

### Environment Variables

Both Dagster and Next.js need these environment variables:

```bash
# Configuration Database
CONFIG_DB_HOST=localhost              # Or IP of PostgreSQL LXC
CONFIG_DB_PORT=5432
CONFIG_DB_NAME=nebenkosten_config
CONFIG_DB_USER=dagster
CONFIG_DB_PASSWORD=dagster            # Use secure password in production
```

### Connection Strings

- **Dagster (Python)**: `postgresql://dagster:dagster@localhost:5432/nebenkosten_config`
- **Next.js (Prisma)**: `postgresql://dagster:dagster@localhost:5432/nebenkosten_config`

## Maintenance

### Backup Configuration Database

```bash
# Backup
sudo -u postgres pg_dump nebenkosten_config > nebenkosten_config_backup.sql

# Restore
sudo -u postgres psql -d nebenkosten_config < nebenkosten_config_backup.sql
```

### View Audit Log

```sql
-- Recent changes
SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 20;

-- Changes to specific meter
SELECT * FROM audit_log
WHERE table_name = 'meters' AND record_id = 'strom_haupt'
ORDER BY created_at DESC;
```

## Development

### Local Development

For local development, you can use the same PostgreSQL instance:

```bash
# Create local database
createdb nebenkosten_config

# Initialize schema
psql -d nebenkosten_config -f database/schema.sql

# Run migration
python database/migrate_yaml_to_postgres.py
```

### Testing

Test database is automatically created and seeded during CI/CD:

```bash
# See .github/workflows/dagster-ci.yml and .github/workflows/nextjs-ci.yml
```

## Security Considerations

1. **Production**: Use strong passwords, not the default `dagster:dagster`
2. **Network**: Restrict PostgreSQL access to only Dagster and Next.js LXCs
3. **SSL**: Enable SSL for PostgreSQL connections in production
4. **Audit**: Review audit_log regularly for unauthorized changes

## Future Enhancements

- [ ] User authentication and authorization
- [ ] Role-based access control (RBAC)
- [ ] Configuration versioning
- [ ] Rollback capability
- [ ] Change approval workflow
