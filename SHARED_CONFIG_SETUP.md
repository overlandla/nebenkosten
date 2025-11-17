# Shared Configuration Setup Guide

This guide walks you through setting up the shared PostgreSQL configuration database that both Dagster and Next.js will use for managing meters, households, and system settings.

## Architecture Overview

```
┌─────────────────────────────────────┐
│  LXC 1: Dagster + PostgreSQL        │
│  - Dagster workflows                │
│  - PostgreSQL (dagster DB)          │
│  - PostgreSQL (nebenkosten_config)  │  ← Shared config
│  - Reads config from DB             │
│  - Falls back to YAML if unavailable│
└─────────────────────────────────────┘
           │
           ├──── PostgreSQL Connection ───┐
           │                               │
           ▼                               ▼
┌──────────────────────────┐    ┌────────────────────────────┐
│  InfluxDB Server         │    │  PostgreSQL Server        │
│  (192.168.1.75:8086)     │    │  (Same LXC as Dagster)    │
│  - Time-series data      │    │  - dagster (metadata)     │
└──────────────────────────┘    │  - nebenkosten_config ✓   │
           ▲                     └────────────────────────────┘
           │                               ▲
┌─────────────────────────────────────┐   │
│  LXC 2: Next.js Dashboard           │   │
│  - Web UI for viewing data          │───┘
│  - Admin UI for editing config      │
│  - Connects to config DB            │
│  - Reads time-series from InfluxDB  │
└─────────────────────────────────────┘
```

## What Gets Shared?

### PostgreSQL Database (`nebenkosten_config`)

Stores **mutable configuration** that can be edited via the Next.js admin UI:

- **Meters**: Physical, master, and virtual meter definitions
- **Households**: Building units and their properties
- **Meter Assignments**: Which meters belong to which households
- **System Settings**: Gas conversion factors, InfluxDB config, etc.

### InfluxDB (Unchanged)

Continues to store **time-series data**:

- Meter readings over time
- Processed consumption data
- Historical trends

### YAML Files (Backup/Fallback)

Remain in place as:

- Initial data source for migration
- Fallback if database is unavailable
- Documentation of configuration structure

## Installation Steps

### 1. Prerequisites

Ensure you have:

- PostgreSQL installed on the Dagster LXC (should already exist)
- Network connectivity between Dagster and Next.js LXCs
- SSH access to both LXCs

### 2. Create the Configuration Database

On the **Dagster LXC** (where PostgreSQL is running):

```bash
# Connect as postgres user
sudo -u postgres psql

# Create the database
CREATE DATABASE nebenkosten_config OWNER dagster;

# Verify
\l

# Exit
\q
```

### 3. Initialize the Database Schema

From your **development machine** or **Dagster LXC**:

```bash
# Navigate to project root
cd /home/user/nebenkosten

# Initialize schema
sudo -u postgres psql -d nebenkosten_config -f database/schema.sql
```

This creates:
- 6 tables: meters, households, household_meters, settings, users, audit_log
- Indexes for performance
- Default system settings
- Triggers for automatic timestamps

### 4. Migrate Existing YAML Data

```bash
# Set environment variables (if not using defaults)
export CONFIG_DB_HOST=localhost
export CONFIG_DB_PORT=5432
export CONFIG_DB_NAME=nebenkosten_config
export CONFIG_DB_USER=dagster
export CONFIG_DB_PASSWORD=dagster

# Test migration (dry run)
python database/migrate_yaml_to_postgres.py --dry-run

# Run actual migration
python database/migrate_yaml_to_postgres.py
```

Expected output:
```
✅ Migrated 39 meters
✅ Migrated 4 settings
✅ Migrated 5 households
```

### 5. Configure Next.js Dashboard

On the **Next.js LXC**:

```bash
cd /path/to/dashboard

# Copy environment file
cp .env.example .env.local

# Edit .env.local
nano .env.local
```

Add the config database URL (update host if on different LXC):

```bash
# If Next.js is on different LXC, use Dagster LXC IP
CONFIG_DATABASE_URL=postgresql://dagster:dagster@192.168.1.XXX:5432/nebenkosten_config

# Other existing vars...
INFLUX_URL=http://192.168.1.75:8086
INFLUX_TOKEN=your_token_here
# ...
```

Install dependencies and generate Prisma client:

```bash
# Install new dependencies
npm install

# Generate Prisma client
npm run prisma:generate

# Verify database connection
npm run prisma:studio  # Opens Prisma Studio on http://localhost:5555
```

### 6. Configure Dagster

On the **Dagster LXC**:

```bash
cd /opt/dagster-workflows/nebenkosten

# Add config database environment variables
sudo nano /etc/systemd/system/dagster-daemon.service
sudo nano /etc/systemd/system/dagster-webserver.service
```

Add these environment variables to both service files:

```ini
Environment="CONFIG_DB_HOST=localhost"
Environment="CONFIG_DB_PORT=5432"
Environment="CONFIG_DB_NAME=nebenkosten_config"
Environment="CONFIG_DB_USER=dagster"
Environment="CONFIG_DB_PASSWORD=dagster"
```

Reload and restart services:

```bash
sudo systemctl daemon-reload
sudo systemctl restart dagster-daemon
sudo systemctl restart dagster-webserver
```

### 7. Verify Setup

#### Test Database Connection

```bash
# From Dagster LXC
python -c "
from src.config_db import ConfigDatabaseClient
client = ConfigDatabaseClient()
print('Connection:', 'OK' if client.check_connection() else 'FAILED')
meters = client.get_meters()
print(f'Meters: {len(meters)}')
"
```

#### Test Next.js Admin UI

```bash
# Start Next.js dev server
cd /path/to/dashboard
npm run dev
```

Visit: `http://localhost:3000/admin/config`

You should see:
- List of all meters with activate/deactivate buttons
- List of all households with their assigned meters

#### Test Dagster Config Loading

```bash
# Check Dagster logs
sudo journalctl -u dagster-daemon -n 50 -f
```

Look for:
```
Loading configuration from PostgreSQL database
Loaded 39 meters from database
Loaded 5 households from database
```

### 8. Network Configuration for Multi-LXC Setup

If Dagster and Next.js are on different LXCs, ensure PostgreSQL accepts remote connections:

#### On Dagster LXC (PostgreSQL Server)

Edit PostgreSQL configuration:

```bash
sudo nano /etc/postgresql/*/main/postgresql.conf
```

Find and update:
```conf
listen_addresses = 'localhost,192.168.1.XXX'  # Add Dagster LXC IP
```

Edit pg_hba.conf:

```bash
sudo nano /etc/postgresql/*/main/pg_hba.conf
```

Add line (replace 192.168.1.YYY with Next.js LXC IP):
```conf
host    nebenkosten_config    dagster    192.168.1.YYY/32    md5
```

Restart PostgreSQL:

```bash
sudo systemctl restart postgresql
```

#### Test from Next.js LXC

```bash
# From Next.js LXC
psql -h 192.168.1.XXX -U dagster -d nebenkosten_config -c "SELECT COUNT(*) FROM meters;"
```

## Usage

### Managing Configuration via Admin UI

1. **Access Admin UI**:
   - Navigate to `http://your-dashboard:3000/admin/config`

2. **View Meters**:
   - See all meters with their types, categories, and status
   - Toggle active/inactive status
   - (Future: Add, edit, delete meters)

3. **View Households**:
   - See all households with assigned meters
   - Toggle active/inactive status
   - (Future: Add, edit, assign meters)

4. **Changes Take Effect Immediately**:
   - Dagster reads from database on each workflow run
   - Next.js API routes read latest data in real-time

### API Endpoints

All config API routes are under `/api/config/`:

- `GET /api/config/meters` - List all meters
- `POST /api/config/meters` - Create a meter
- `PATCH /api/config/meters?id=xxx` - Update a meter
- `DELETE /api/config/meters?id=xxx` - Delete a meter

- `GET /api/config/households` - List all households
- `POST /api/config/households` - Create a household
- `PATCH /api/config/households?id=xxx` - Update a household
- `DELETE /api/config/households?id=xxx` - Delete a household

- `GET /api/config/household-meters?household_id=xxx` - List meter assignments
- `POST /api/config/household-meters` - Assign meter to household
- `DELETE /api/config/household-meters?id=xxx` - Unassign meter

- `GET /api/config/settings` - List all settings
- `PATCH /api/config/settings?key=xxx` - Update a setting

### Python Client (Dagster)

```python
from src.config_db import ConfigDatabaseClient

# Create client
client = ConfigDatabaseClient()

# Get all active meters
meters = client.get_meters(active_only=True)

# Get specific meter
meter = client.get_meter('strom_haupt')

# Get meters by type
gas_meters = client.get_meters(meter_type='gas')

# Get households
households = client.get_households()

# Get meters for a household
hh_meters = client.get_household_meters('og1')

# Get settings
gas_conversion = client.get_setting('gas_conversion')
all_settings = client.get_all_settings()

# Update setting
client.update_setting('gas_conversion', {
    'energy_content': 11.504,
    'z_factor': 0.8885
})
```

### TypeScript Client (Next.js)

```typescript
import { prisma } from '@/lib/prisma';

// Get all meters
const meters = await prisma.meter.findMany({
  where: { active: true },
});

// Get meter with households
const meter = await prisma.meter.findUnique({
  where: { id: 'strom_haupt' },
  include: {
    householdMeters: {
      include: { household: true },
    },
  },
});

// Get household with meters
const household = await prisma.household.findUnique({
  where: { id: 'og1' },
  include: {
    householdMeters: {
      include: { meter: true },
    },
  },
});

// Update meter
await prisma.meter.update({
  where: { id: 'strom_haupt' },
  data: { active: false },
});
```

## Troubleshooting

### Database Connection Failed

**Symptom**: Dagster or Next.js can't connect to PostgreSQL

**Check**:
```bash
# Verify PostgreSQL is running
sudo systemctl status postgresql

# Check if database exists
sudo -u postgres psql -l | grep nebenkosten_config

# Test connection
psql -h localhost -U dagster -d nebenkosten_config -c "SELECT 1;"
```

**Fix**:
- Ensure PostgreSQL is running
- Verify environment variables are set correctly
- Check pg_hba.conf for access permissions

### No Meters in Database

**Symptom**: Admin UI shows empty list

**Check**:
```bash
sudo -u postgres psql -d nebenkosten_config -c "SELECT COUNT(*) FROM meters;"
```

**Fix**:
```bash
# Re-run migration
python database/migrate_yaml_to_postgres.py
```

### Dagster Still Using YAML

**Symptom**: Dagster logs show "Loading configuration from YAML files"

**Check**:
- Verify CONFIG_DB_* environment variables are set in systemd services
- Check database connection from Dagster

**Fix**:
```bash
# Verify env vars
sudo systemctl show dagster-daemon | grep CONFIG_DB

# If missing, add to service file and restart
sudo systemctl daemon-reload
sudo systemctl restart dagster-daemon
```

### Prisma Client Not Generated

**Symptom**: TypeScript errors about @prisma/client

**Fix**:
```bash
cd dashboard
npm run prisma:generate
```

## Backup and Restore

### Backup Configuration Database

```bash
# Full backup
sudo -u postgres pg_dump nebenkosten_config > nebenkosten_config_backup_$(date +%Y%m%d).sql

# Backup specific tables
sudo -u postgres pg_dump -t meters -t households nebenkosten_config > config_backup.sql
```

### Restore from Backup

```bash
# Restore full backup
sudo -u postgres psql -d nebenkosten_config < nebenkosten_config_backup_20241117.sql

# Restore specific backup
sudo -u postgres psql -d nebenkosten_config < config_backup.sql
```

### Export to YAML (Fallback)

To regenerate YAML files from database:

```python
from src.config_db import ConfigDatabaseClient
import yaml

client = ConfigDatabaseClient()
meters = client.get_meters(active_only=False)

# Convert to YAML format and save
with open('config/meters_from_db.yaml', 'w') as f:
    yaml.dump({'meters': meters}, f)
```

## Security Considerations

### Production Deployment

1. **Change Default Password**:
   ```sql
   ALTER USER dagster WITH PASSWORD 'strong_random_password';
   ```

2. **Restrict Network Access**:
   - Update pg_hba.conf to only allow specific IPs
   - Use SSL for PostgreSQL connections

3. **Environment Variables**:
   - Never commit passwords to git
   - Use secrets management (e.g., HashiCorp Vault)

4. **Database Permissions**:
   ```sql
   -- Create read-only user for dashboards
   CREATE USER dashboard_readonly WITH PASSWORD 'password';
   GRANT CONNECT ON DATABASE nebenkosten_config TO dashboard_readonly;
   GRANT SELECT ON ALL TABLES IN SCHEMA public TO dashboard_readonly;
   ```

## Next Steps

1. **Implement Full CRUD UI**: Add forms for creating/editing meters and households
2. **Add Authentication**: Implement user accounts and role-based access control
3. **Audit Trail**: Track who changed what and when
4. **Validation**: Add business logic validation (e.g., prevent deleting active meters)
5. **Approval Workflow**: Require approval for critical configuration changes
6. **API Documentation**: Generate OpenAPI/Swagger docs for the config API
7. **Monitoring**: Add alerts for configuration changes

## Support

For issues or questions:
- Check logs: `sudo journalctl -u dagster-daemon -n 100`
- Check database: `sudo -u postgres psql -d nebenkosten_config`
- Review code: `database/`, `dashboard/app/api/config/`, `workflows_dagster/src/config_db.py`
