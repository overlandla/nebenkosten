#!/usr/bin/env python3
"""
Migration Script: YAML to PostgreSQL

This script migrates existing YAML configuration files to the PostgreSQL database.
Run this once to populate the database with initial data.

Usage:
    python database/migrate_yaml_to_postgres.py [--dry-run]
"""

import os
import sys
import yaml
import json
import psycopg2
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Any, Optional

# Database connection settings
DB_CONFIG = {
    'host': os.environ.get('CONFIG_DB_HOST', 'localhost'),
    'port': int(os.environ.get('CONFIG_DB_PORT', '5432')),
    'dbname': os.environ.get('CONFIG_DB_NAME', 'nebenkosten_config'),
    'user': os.environ.get('CONFIG_DB_USER', 'dagster'),
    'password': os.environ.get('CONFIG_DB_PASSWORD', 'dagster'),
}

# Paths to configuration files
PROJECT_ROOT = Path(__file__).parent.parent
METERS_YAML = PROJECT_ROOT / 'config' / 'meters.yaml'
CONFIG_YAML = PROJECT_ROOT / 'config' / 'config.yaml'


def connect_db():
    """Connect to PostgreSQL database"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        print(f"   Connection string: {DB_CONFIG['user']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}")
        sys.exit(1)


def parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parse date string to date object"""
    if not date_str:
        return None
    if date_str == '9999-12-31':
        return None  # Treat far future as NULL
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except:
        return None


def determine_meter_type(meter_data: Dict) -> str:
    """Determine meter type from meter configuration"""
    meter_id = meter_data.get('meter_id', '').lower()

    if 'strom' in meter_id or 'electricity' in meter_id:
        return 'electricity'
    elif 'gas' in meter_id:
        return 'gas'
    elif 'wasser' in meter_id or 'water' in meter_id:
        return 'water'
    elif 'heat' in meter_id or 'heiz' in meter_id or 'therme' in meter_id:
        return 'heat'
    elif 'solar' in meter_id:
        return 'solar'
    else:
        return 'electricity'  # default


def migrate_meters(conn, meters_yaml_path: Path, dry_run: bool = False) -> int:
    """Migrate meters from YAML to PostgreSQL"""
    print(f"📋 Reading meters from {meters_yaml_path}")

    with open(meters_yaml_path, 'r') as f:
        data = yaml.safe_load(f)

    meters = data.get('meters', [])
    print(f"   Found {len(meters)} meters")

    cursor = conn.cursor()
    inserted = 0

    for meter in meters:
        meter_id = meter['meter_id']
        meter_category = meter.get('type', 'physical')
        meter_type = determine_meter_type(meter)
        unit = meter.get('output_unit', 'kWh')
        description = meter.get('description', '')
        installation_date = parse_date(meter.get('installation_date'))
        deinstallation_date = parse_date(meter.get('deinstallation_date'))

        # Build source_meters and calculation_config for master/virtual meters
        source_meters = None
        calculation_config = None

        if meter_category == 'master':
            # Extract source meters from all periods
            all_sources = []
            periods_data = []

            for period in meter.get('periods', []):
                sources = period.get('source_meters', [])
                all_sources.extend(sources)
                periods_data.append({
                    'start_date': period.get('start_date'),
                    'end_date': period.get('end_date'),
                    'composition_type': period.get('composition_type'),
                    'source_meters': sources,
                    'source_unit': period.get('source_unit'),
                    'apply_offset': period.get('apply_offset_from_previous_period', False),
                })

            source_meters = json.dumps(list(set(all_sources)))
            calculation_config = json.dumps({
                'periods': periods_data
            })

        elif meter_category == 'virtual':
            calc_type = meter.get('calculation_type', 'subtraction')
            base_meter = meter.get('base_meter')
            subtract_meters = meter.get('subtract_meters', [])
            conversions = meter.get('subtract_meter_conversions', {})

            source_meters = json.dumps([base_meter] + subtract_meters)
            calculation_config = json.dumps({
                'calculation_type': calc_type,
                'base_meter': base_meter,
                'subtract_meters': subtract_meters,
                'conversions': conversions,
            })

        # Determine if meter is still active
        active = deinstallation_date is None

        if dry_run:
            print(f"   [DRY RUN] Would insert: {meter_id} ({meter_type}, {meter_category})")
        else:
            cursor.execute("""
                INSERT INTO meters (
                    id, name, meter_type, category, unit,
                    installation_date, deinstallation_date,
                    source_meters, calculation_config, active
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    meter_type = EXCLUDED.meter_type,
                    category = EXCLUDED.category,
                    unit = EXCLUDED.unit,
                    installation_date = EXCLUDED.installation_date,
                    deinstallation_date = EXCLUDED.deinstallation_date,
                    source_meters = EXCLUDED.source_meters,
                    calculation_config = EXCLUDED.calculation_config,
                    active = EXCLUDED.active,
                    updated_at = NOW()
            """, (
                meter_id,
                description or meter_id.replace('_', ' ').title(),
                meter_type,
                meter_category,
                unit,
                installation_date,
                deinstallation_date,
                source_meters,
                calculation_config,
                active
            ))
            inserted += 1

    if not dry_run:
        conn.commit()

    print(f"✅ Migrated {inserted} meters")
    return inserted


def migrate_settings(conn, config_yaml_path: Path, dry_run: bool = False) -> int:
    """Migrate settings from YAML to PostgreSQL"""
    print(f"📋 Reading settings from {config_yaml_path}")

    with open(config_yaml_path, 'r') as f:
        data = yaml.safe_load(f)

    cursor = conn.cursor()
    inserted = 0

    # Gas conversion settings
    if 'gas_conversion' in data:
        gas_settings = json.dumps(data['gas_conversion'])
        if dry_run:
            print(f"   [DRY RUN] Would update: gas_conversion")
        else:
            cursor.execute("""
                INSERT INTO settings (key, value, description)
                VALUES ('gas_conversion', %s, 'Gas to energy conversion factors (kWh per m³)')
                ON CONFLICT (key) DO UPDATE SET
                    value = EXCLUDED.value,
                    updated_at = NOW()
            """, (gas_settings,))
            inserted += 1

    # InfluxDB settings
    if 'influxdb' in data:
        influx_settings = json.dumps({
            'url': data['influxdb'].get('url'),
            'bucket_raw': data['influxdb'].get('bucket_raw'),
            'bucket_processed': data['influxdb'].get('bucket_processed'),
            'timeout': data['influxdb'].get('timeout'),
            'retry_attempts': data['influxdb'].get('retry_attempts'),
        })
        if dry_run:
            print(f"   [DRY RUN] Would update: influxdb")
        else:
            cursor.execute("""
                INSERT INTO settings (key, value, description)
                VALUES ('influxdb', %s, 'InfluxDB connection settings')
                ON CONFLICT (key) DO UPDATE SET
                    value = EXCLUDED.value,
                    updated_at = NOW()
            """, (influx_settings,))
            inserted += 1

    # Tibber settings
    if 'tibber' in data:
        tibber_settings = json.dumps(data['tibber'])
        if dry_run:
            print(f"   [DRY RUN] Would update: tibber")
        else:
            cursor.execute("""
                INSERT INTO settings (key, value, description)
                VALUES ('tibber', %s, 'Tibber API polling settings')
                ON CONFLICT (key) DO UPDATE SET
                    value = EXCLUDED.value,
                    updated_at = NOW()
            """, (tibber_settings,))
            inserted += 1

    # Workflow settings
    if 'workflows' in data:
        workflow_settings = json.dumps(data['workflows'])
        if dry_run:
            print(f"   [DRY RUN] Would update: workflows")
        else:
            cursor.execute("""
                INSERT INTO settings (key, value, description)
                VALUES ('workflows', %s, 'Dagster workflow schedules and configuration')
                ON CONFLICT (key) DO UPDATE SET
                    value = EXCLUDED.value,
                    updated_at = NOW()
            """, (workflow_settings,))
            inserted += 1

    if not dry_run:
        conn.commit()

    print(f"✅ Migrated {inserted} settings")
    return inserted


def migrate_households(conn, dry_run: bool = False) -> int:
    """Migrate default household configuration to PostgreSQL"""
    print(f"📋 Creating default households")

    # Default household configuration
    households = [
        {
            'id': 'eg_nord',
            'name': 'Ground Floor North',
            'floors': ['EG'],
            'meters': {
                'electricity': ['eg_strom'],
                'heat': ['eg_nord_heat'],
            },
            'allocation': {'sharedGas': 25, 'sharedWater': 20},
        },
        {
            'id': 'eg_sud',
            'name': 'Ground Floor South',
            'floors': ['EG'],
            'meters': {
                'heat': ['eg_sud_heat'],
            },
            'allocation': {'sharedElectricity': 20, 'sharedGas': 25, 'sharedWater': 20},
        },
        {
            'id': 'og1',
            'name': 'First Floor',
            'floors': ['OG1'],
            'meters': {
                'electricity': ['og1_strom'],
                'water': ['og1_wasser_kalt', 'og1_wasser_warm'],
                'heat': ['og1_heat'],
            },
            'allocation': {'sharedElectricity': 30, 'sharedGas': 25, 'sharedWater': 30},
        },
        {
            'id': 'og2',
            'name': 'Second Floor',
            'floors': ['OG2'],
            'meters': {
                'electricity': ['og2_strom'],
                'water': ['og2_wasser_kalt', 'og2_wasser_warm'],
                'heat': ['og2_heat'],
            },
            'allocation': {'sharedElectricity': 30, 'sharedGas': 25, 'sharedWater': 30},
        },
        {
            'id': 'buro',
            'name': 'Office',
            'floors': ['EG'],
            'meters': {
                'heat': ['buro_heat'],
            },
            'allocation': {'sharedElectricity': 20},
        },
    ]

    cursor = conn.cursor()
    inserted = 0

    for household in households:
        household_id = household['id']
        name = household['name']
        floors = household['floors']
        allocation = household.get('allocation', {})

        # Calculate average allocation percentage
        alloc_percentage = sum(allocation.values()) / len(allocation) if allocation else 0

        if dry_run:
            print(f"   [DRY RUN] Would insert household: {household_id}")
        else:
            cursor.execute("""
                INSERT INTO households (id, name, floors, allocation_percentage, active)
                VALUES (%s, %s, %s, %s, true)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    floors = EXCLUDED.floors,
                    allocation_percentage = EXCLUDED.allocation_percentage,
                    updated_at = NOW()
            """, (household_id, name, floors, alloc_percentage))
            inserted += 1

            # Insert meter assignments
            for meter_type, meter_ids in household.get('meters', {}).items():
                for meter_id in meter_ids:
                    alloc_value = allocation.get(f'shared{meter_type.capitalize()}', 100)

                    cursor.execute("""
                        INSERT INTO household_meters (household_id, meter_id, allocation_type, allocation_value)
                        VALUES (%s, %s, 'direct', %s)
                        ON CONFLICT (household_id, meter_id) DO UPDATE SET
                            allocation_type = EXCLUDED.allocation_type,
                            allocation_value = EXCLUDED.allocation_value
                    """, (household_id, meter_id, alloc_value))

    if not dry_run:
        conn.commit()

    print(f"✅ Migrated {inserted} households")
    return inserted


def verify_migration(conn):
    """Verify the migration was successful"""
    print("\n🔍 Verifying migration...")

    cursor = conn.cursor()

    # Check meters
    cursor.execute("SELECT COUNT(*), COUNT(DISTINCT meter_type), COUNT(DISTINCT category) FROM meters")
    meter_count, types, categories = cursor.fetchone()
    print(f"   Meters: {meter_count} total, {types} types, {categories} categories")

    # Check households
    cursor.execute("SELECT COUNT(*) FROM households")
    household_count = cursor.fetchone()[0]
    print(f"   Households: {household_count}")

    # Check household-meter assignments
    cursor.execute("SELECT COUNT(*) FROM household_meters")
    assignment_count = cursor.fetchone()[0]
    print(f"   Meter assignments: {assignment_count}")

    # Check settings
    cursor.execute("SELECT COUNT(*), string_agg(key, ', ') FROM settings")
    setting_count, setting_keys = cursor.fetchone()
    print(f"   Settings: {setting_count} ({setting_keys})")

    print("✅ Migration verification complete")


def main():
    """Main migration function"""
    import argparse

    parser = argparse.ArgumentParser(description='Migrate YAML configuration to PostgreSQL')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be migrated without actually doing it')
    args = parser.parse_args()

    print("=" * 60)
    print("Nebenkosten Configuration Migration")
    print("YAML → PostgreSQL")
    print("=" * 60)

    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be made\n")

    # Check if files exist
    if not METERS_YAML.exists():
        print(f"❌ Meters file not found: {METERS_YAML}")
        sys.exit(1)

    if not CONFIG_YAML.exists():
        print(f"❌ Config file not found: {CONFIG_YAML}")
        sys.exit(1)

    # Connect to database
    print(f"\n🔌 Connecting to database: {DB_CONFIG['dbname']}@{DB_CONFIG['host']}")
    conn = connect_db()
    print("✅ Connected successfully\n")

    try:
        # Run migrations
        total_meters = migrate_meters(conn, METERS_YAML, args.dry_run)
        total_settings = migrate_settings(conn, CONFIG_YAML, args.dry_run)
        total_households = migrate_households(conn, args.dry_run)

        if not args.dry_run:
            verify_migration(conn)

        print("\n" + "=" * 60)
        print("Migration Summary")
        print("=" * 60)
        print(f"Meters:     {total_meters}")
        print(f"Settings:   {total_settings}")
        print(f"Households: {total_households}")
        print("=" * 60)

        if args.dry_run:
            print("\n✅ Dry run complete - no changes were made")
        else:
            print("\n✅ Migration complete!")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        if not args.dry_run:
            conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
