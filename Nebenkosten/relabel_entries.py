#!/usr/bin/env python3
"""
Switch entity_id from gas_zahler to gas_zahler_alt for specific entries
Uses simplified deletion predicate for InfluxDB OSS compatibility
"""

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime
import os
from dotenv import load_dotenv
import pandas as pd

# Load environment variables
load_dotenv()

# InfluxDB connection details
INFLUX_URL = os.getenv('INFLUX_URL', 'http://192.168.1.75:8086')
INFLUX_TOKEN = os.getenv('INFLUX_TOKEN')
INFLUX_ORG = os.getenv('INFLUX_ORG')
INFLUX_BUCKET = os.getenv('INFLUX_BUCKET', 'lampfi')

def switch_entity_ids():
    """Switch the entity_id for the two specific gas_zahler entries"""
    
    # Initialize client
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    query_api = client.query_api()
    write_api = client.write_api(write_options=SYNCHRONOUS)
    delete_api = client.delete_api()
    
    try:
        # Step 1: Query the specific entries we want to modify
        print("🔍 Querying the gas_zahler entries to modify...")
        
        query = f'''
        from(bucket: "{INFLUX_BUCKET}")
        |> range(start: 2023-09-01T00:00:00Z, stop: 2024-10-01T00:00:00Z)
        |> filter(fn: (r) => r["entity_id"] == "gas_zahler")
        |> filter(fn: (r) => r["_field"] == "value")
        |> filter(fn: (r) => r["_measurement"] == "m³")
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        '''
        
        result = query_api.query_data_frame(query)
        
        if isinstance(result, list):
            if len(result) == 0:
                print("❌ No data found")
                return
            result = pd.concat(result, ignore_index=True)
        
        if result.empty:
            print("❌ No matching entries found")
            return
        
        print(f"✅ Found {len(result)} entries to modify")
        
        # Display the entries for confirmation
        print("\n📋 Entries to be switched:")
        for _, row in result.iterrows():
            print(f"   🕐 {row['_time']}: {row['value']} m³")
        
        # Ask for confirmation
        response = input(f"\n⚠️  Switch these {len(result)} entries from gas_zahler to gas_zahler_alt? (yes/no): ")
        
        if response.lower() not in ['yes', 'y']:
            print("❌ Operation cancelled")
            return
        
        # Step 2: Create new points with gas_zahler_alt entity_id
        print("\n📝 Creating new entries with gas_zahler_alt...")
        
        new_points = []
        timestamps_to_delete = []
        
        for _, row in result.iterrows():
            # Create new point with gas_zahler_alt
            point = Point("m³") \
                .tag("domain", "input_number") \
                .tag("entity_id", "gas_zahler_alt") \
                .field("value", float(row['value'])) \
                .time(row['_time'])
            new_points.append(point)
            
            # Store timestamp for deletion
            timestamps_to_delete.append(row['_time'])
        
        # Step 3: Write new points
        print(f"💾 Writing {len(new_points)} new points...")
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=new_points)
        print("✅ New points written successfully")
        
        # Step 4: Delete old points using simpler predicate (tags only)
        print("🗑️  Deleting old gas_zahler entries...")
        
        for timestamp in timestamps_to_delete:
            # Create a small time window around each point
            timestamp_dt = pd.to_datetime(timestamp)
            start_time = (timestamp_dt - pd.Timedelta(seconds=30)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            stop_time = (timestamp_dt + pd.Timedelta(seconds=30)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            
            # Use only tag-based predicate (InfluxDB OSS limitation)
            try:
                delete_api.delete(
                    start=start_time,
                    stop=stop_time,
                    predicate='entity_id="gas_zahler"',  # Simplified predicate
                    bucket=INFLUX_BUCKET,
                    org=INFLUX_ORG
                )
                print(f"   ✅ Deleted entry around {timestamp}")
            except Exception as e:
                print(f"   ⚠️  Could not delete entry around {timestamp}: {e}")
        
        print("✅ Deletion process completed")
        
        print("\n🎉 Successfully switched entity_id from gas_zahler to gas_zahler_alt!")
        
    except Exception as e:
        print(f"❌ Error during operation: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        client.close()

def manual_cli_commands():
    """Print manual CLI commands as alternative"""
    
    print("\n" + "="*60)
    print("🛠️  ALTERNATIVE: Manual CLI Commands")
    print("="*60)
    print("""
If the Python approach has issues, use these CLI commands:

1️⃣ Write new entries:
influx write --bucket lampfi 'm³,domain=input_number,entity_id=gas_zahler_alt value=47757 1693598630000000000'
influx write --bucket lampfi 'm³,domain=input_number,entity_id=gas_zahler_alt value=51293 1726619130000000000'

2️⃣ Delete old entries:
influx delete --bucket lampfi --start 2023-09-01T19:43:00Z --stop 2023-09-01T19:44:00Z --predicate 'entity_id="gas_zahler"'
influx delete --bucket lampfi --start 2024-09-18T01:25:00Z --stop 2024-09-18T01:26:00Z --predicate 'entity_id="gas_zahler"'

3️⃣ Verify:
influx query 'from(bucket: "lampfi") |> range(start: 2023-01-01T00:00:00Z) |> filter(fn: (r) => r["entity_id"] == "gas_zahler_alt")'
    """)

def verify_switch():
    """Verify that the switch was successful"""
    
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    query_api = client.query_api()
    
    try:
        # Check for remaining gas_zahler entries in that time range
        query1 = f'''
        from(bucket: "{INFLUX_BUCKET}")
        |> range(start: 2023-09-01T00:00:00Z, stop: 2024-10-01T00:00:00Z)
        |> filter(fn: (r) => r["entity_id"] == "gas_zahler")
        |> filter(fn: (r) => r["_field"] == "value")
        |> filter(fn: (r) => r["_measurement"] == "m³")
        |> count()
        '''
        
        # Check for new gas_zahler_alt entries
        query2 = f'''
        from(bucket: "{INFLUX_BUCKET}")
        |> range(start: 2023-09-01T00:00:00Z, stop: 2024-10-01T00:00:00Z)
        |> filter(fn: (r) => r["entity_id"] == "gas_zahler_alt")
        |> filter(fn: (r) => r["_field"] == "value")
        |> filter(fn: (r) => r["_measurement"] == "m³")
        '''
        
        result1 = query_api.query_data_frame(query1)
        result2 = query_api.query_data_frame(query2)
        
        print("\n📋 Verification Results:")
        
        # Handle gas_zahler remaining count
        if isinstance(result1, list):
            remaining_count = 0 if len(result1) == 0 else "Unknown"
        else:
            remaining_count = len(result1) if not result1.empty else 0
            
        # Handle gas_zahler_alt created count  
        if isinstance(result2, list):
            created_count = 0 if len(result2) == 0 else "Unknown"
        else:
            created_count = len(result2) if not result2.empty else 0
        
        print(f"   gas_zahler entries remaining: {remaining_count}")
        print(f"   gas_zahler_alt entries found: {created_count}")
        
        # Show the actual gas_zahler_alt entries
        if not isinstance(result2, list) and not result2.empty:
            print("\n📊 gas_zahler_alt entries:")
            for _, row in result2.iterrows():
                print(f"   🕐 {row['_time']}: {row['_value']} m³")
        
    except Exception as e:
        print(f"❌ Error verifying switch: {e}")
    
    finally:
        client.close()

if __name__ == "__main__":
    print("🔄 InfluxDB Entity ID Switch Tool (OSS Compatible)")
    print("=" * 50)
    
    print(f"🔌 Connecting to: {INFLUX_URL}")
    print(f"📊 Bucket: {INFLUX_BUCKET}")
    print(f"🏢 Org: {INFLUX_ORG}")
    
    switch_entity_ids()
    
    # Show manual CLI alternative
    manual_cli_commands()
    
    # Wait a moment for operations to complete
    import time
    time.sleep(3)
    
    # Verify the switch
    verify_switch()