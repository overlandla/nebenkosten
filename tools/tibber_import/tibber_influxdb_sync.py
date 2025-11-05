#!/usr/bin/env python3
"""
Tibber InfluxDB Continuous Sync Script

This script runs as a cron job to continuously fetch the latest Tibber consumption data
and add it to the existing haupt_strom meter in InfluxDB. It only processes new data
since the last run to avoid duplicates.
"""

import requests
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import time
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/tibber_sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
TIBBER_CONFIG = {
    'token': 'BA2D594CDBC409A921FF75B0370A3855C8AEE38098B1058AF868196360D8357A-1',
    'url': 'https://api.tibber.com/v1-beta/gql'
}

INFLUXDB_CONFIG = {
    'url': 'http://192.168.1.75:8086',
    'token': 'OcXhfQCBA6rKpIN4f5JSrmtp2xxgjk4vBt1jAqpjb-g1sIh1nUDdB8Ljo-ZMYxjMQJEicDncrZ1QE2PzH9nzZg==',
    'org': '0d72e1f6b38972fa',
    'bucket': 'lampfi'
}

# Entity configuration for existing Home Assistant input_number
ENTITY_CONFIG = {
    'entity_id': 'haupt_strom',
    'domain': 'input_number',
    'field': 'value',
    'measurement': 'kWh',
    'unit_of_measurement': 'kWh',
    'device_class': 'energy',
    'state_class': 'total_increasing'
}

# State file to track last processed timestamp
STATE_FILE = '/var/lib/tibber_sync_state.json'

# Fallback last known meter reading (only used if state file doesn't exist)
FALLBACK_LAST_READING = {
    'timestamp': '2025-06-04T22:00:00.000Z',
    'value': 7933.53  # kWh
}

def load_state():
    """Load the last processed state from file"""
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                logger.info(f"Loaded state: last processed {state['timestamp']} with value {state['value']} kWh")
                return state
        else:
            logger.info("No state file found, using fallback last reading")
            return FALLBACK_LAST_READING
    except Exception as e:
        logger.error(f"Error loading state file: {e}")
        logger.info("Using fallback last reading")
        return FALLBACK_LAST_READING

def save_state(timestamp, value):
    """Save the last processed state to file"""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        
        state = {
            'timestamp': timestamp,
            'value': value,
            'updated': datetime.now(timezone.utc).isoformat()
        }
        
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        
        logger.info(f"Saved state: {timestamp} with value {value} kWh")
        
    except Exception as e:
        logger.error(f"Error saving state file: {e}")

def get_latest_meter_reading_from_influxdb():
    """Query InfluxDB to get the latest meter reading"""
    try:
        client = InfluxDBClient(
            url=INFLUXDB_CONFIG['url'],
            token=INFLUXDB_CONFIG['token'],
            org=INFLUXDB_CONFIG['org']
        )
        
        query_api = client.query_api()
        
        # Query to get the latest value for haupt_strom
        query = f'''
        from(bucket: "{INFLUXDB_CONFIG['bucket']}")
          |> range(start: -30d)
          |> filter(fn: (r) => r["_measurement"] == "{ENTITY_CONFIG['measurement']}")
          |> filter(fn: (r) => r["entity_id"] == "{ENTITY_CONFIG['entity_id']}")
          |> filter(fn: (r) => r["_field"] == "{ENTITY_CONFIG['field']}")
          |> last()
        '''
        
        result = query_api.query(query)
        
        for table in result:
            for record in table.records:
                timestamp = record.get_time().isoformat()
                value = float(record.get_value())
                client.close()
                logger.info(f"Found latest InfluxDB reading: {timestamp} = {value} kWh")
                return {'timestamp': timestamp, 'value': value}
        
        client.close()
        logger.warning("No existing data found in InfluxDB")
        return None
        
    except Exception as e:
        logger.error(f"Error querying InfluxDB for latest reading: {e}")
        return None

def fetch_tibber_data():
    """Fetch recent consumption data from Tibber GraphQL API"""
    
    # For continuous sync, we only need recent data (last 48 hours should be enough)
    query = """
    {
      viewer {
        homes {
          consumption(resolution: HOURLY, last: 48) {
            nodes {
              from
              to
              cost
              unitPrice
              unitPriceVAT
              consumption
              consumptionUnit
            }
          }
        }
      }
    }
    """
    
    headers = {
        'Authorization': f'{TIBBER_CONFIG["token"]}',
        'Content-Type': 'application/json',
        'User-Agent': 'TibberInfluxDBSync/1.0'
    }
    
    payload = {'query': query}
    
    logger.info("Fetching recent data from Tibber GraphQL API...")
    
    try:
        response = requests.post(
            TIBBER_CONFIG['url'], 
            json=payload, 
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        
        if 'errors' in data:
            logger.error(f"GraphQL errors: {data['errors']}")
            return None
            
        nodes = data['data']['viewer']['homes'][0]['consumption']['nodes']
        logger.info(f"Successfully fetched {len(nodes)} consumption records")
        return nodes
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data from Tibber: {e}")
        return None
    except (KeyError, IndexError) as e:
        logger.error(f"Error parsing Tibber response: {e}")
        return None

def process_consumption_data(nodes, last_reading):
    """Process consumption data and create incremental meter readings starting from last known reading"""
    
    if not nodes:
        logger.warning("No data to process")
        return []
    
    # Parse the last known timestamp
    last_timestamp = datetime.fromisoformat(last_reading['timestamp'].replace('Z', '+00:00'))
    
    # Filter out null/zero consumption values and only include data AFTER the last reading
    valid_nodes = []
    for node in nodes:
        if (node.get('consumption') is not None and 
            node.get('from') is not None and
            float(node.get('consumption', 0)) > 0):  # Skip zero consumption
            
            node_timestamp = datetime.fromisoformat(node['from'].replace('Z', '+00:00'))
            
            # Only include readings after our last known reading
            if node_timestamp > last_timestamp:
                valid_nodes.append(node)
    
    # Sort by timestamp (oldest first)
    valid_nodes.sort(key=lambda x: x['from'])
    
    logger.info(f"Found {len(valid_nodes)} new consumption records after {last_reading['timestamp']}")
    
    if not valid_nodes:
        logger.info("No new data to process - all readings are before the last known meter reading")
        return []
    
    # Create incremental meter readings starting from last known value
    meter_readings = []
    cumulative_consumption = last_reading['value']  # Start from last known reading
    
    for node in valid_nodes:
        consumption = float(node['consumption'])
        cumulative_consumption += consumption  # Add this hour's consumption to running total
        
        # Parse timestamp
        timestamp_str = node['from']
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        
        meter_reading = {
            'timestamp': timestamp,
            'cumulative_value': cumulative_consumption,
            'hourly_consumption': consumption,
            'cost': float(node.get('cost', 0)) if node.get('cost') else None,
            'unit_price': float(node.get('unitPrice', 0)) if node.get('unitPrice') else None
        }
        
        meter_readings.append(meter_reading)
    
    if meter_readings:
        logger.info(f"Created {len(meter_readings)} new meter readings")
        logger.info(f"Date range: {meter_readings[0]['timestamp']} to {meter_readings[-1]['timestamp']}")
        logger.info(f"Starting value: {last_reading['value']:.3f} kWh")
        logger.info(f"Ending value: {cumulative_consumption:.3f} kWh")
        logger.info(f"Total consumption added: {cumulative_consumption - last_reading['value']:.3f} kWh")
    
    return meter_readings

def write_to_influxdb(meter_readings):
    """Write meter readings to InfluxDB"""
    
    if not meter_readings:
        logger.info("No meter readings to write")
        return True  # Not an error condition
    
    logger.info("Connecting to InfluxDB...")
    
    try:
        client = InfluxDBClient(
            url=INFLUXDB_CONFIG['url'],
            token=INFLUXDB_CONFIG['token'],
            org=INFLUXDB_CONFIG['org']
        )
        
        write_api = client.write_api(write_options=SYNCHRONOUS)
        
        logger.info(f"Writing {len(meter_readings)} points to InfluxDB...")
        
        points = []
        
        for reading in meter_readings:
            # Create main meter reading point for existing input_number entity
            point = Point(ENTITY_CONFIG['measurement']) \
                .tag("entity_id", ENTITY_CONFIG['entity_id']) \
                .tag("domain", ENTITY_CONFIG['domain']) \
                .tag("unit_of_measurement", ENTITY_CONFIG['unit_of_measurement']) \
                .tag("device_class", ENTITY_CONFIG['device_class']) \
                .tag("state_class", ENTITY_CONFIG['state_class']) \
                .field(ENTITY_CONFIG['field'], reading['cumulative_value']) \
                .field("hourly_consumption", reading['hourly_consumption']) \
                .time(reading['timestamp'])
            
            # Add optional fields if available
            if reading['cost'] is not None:
                point = point.field("cost", reading['cost'])
            if reading['unit_price'] is not None:
                point = point.field("unit_price", reading['unit_price'])
            
            points.append(point)
        
        # Write all points at once (small batches for cron job)
        write_api.write(
            bucket=INFLUXDB_CONFIG['bucket'],
            record=points
        )
        
        client.close()
        logger.info("✅ Successfully written all data to InfluxDB!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error writing to InfluxDB: {e}")
        return False

def main():
    """Main execution function for continuous sync"""
    
    logger.info("🚀 Starting Tibber InfluxDB Continuous Sync")
    logger.info("=" * 50)
    
    try:
        # Step 1: Determine starting point
        # First try to get the latest reading from InfluxDB
        last_reading = get_latest_meter_reading_from_influxdb()
        
        # If that fails, try to load from state file
        if not last_reading:
            last_reading = load_state()
        
        logger.info(f"Starting from: {last_reading['timestamp']} = {last_reading['value']} kWh")
        
        # Step 2: Fetch recent data from Tibber
        nodes = fetch_tibber_data()
        if not nodes:
            logger.error("❌ Failed to fetch data from Tibber")
            return False
        
        # Step 3: Process consumption data
        meter_readings = process_consumption_data(nodes, last_reading)
        
        # Step 4: Write to InfluxDB
        success = write_to_influxdb(meter_readings)
        
        # Step 5: Update state if we have new readings
        if success and meter_readings:
            latest_reading = meter_readings[-1]
            save_state(
                latest_reading['timestamp'].isoformat(),
                latest_reading['cumulative_value']
            )
        
        if success:
            if meter_readings:
                logger.info("\n🎉 Sync completed successfully!")
                logger.info(f"📊 Entity: input_number.{ENTITY_CONFIG['entity_id']}")
                logger.info(f"📈 New records added: {len(meter_readings)}")
                logger.info(f"⚡ Starting value: {last_reading['value']:.3f} kWh")
                logger.info(f"⚡ Ending value: {meter_readings[-1]['cumulative_value']:.3f} kWh")
                logger.info(f"➕ Consumption added: {meter_readings[-1]['cumulative_value'] - last_reading['value']:.3f} kWh")
                logger.info(f"📅 Latest timestamp: {meter_readings[-1]['timestamp'].strftime('%Y-%m-%d %H:%M')}")
            else:
                logger.info("✅ Sync completed - no new data to add")
        else:
            logger.error("❌ Sync failed!")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Unexpected error in main: {e}")
        return False

if __name__ == "__main__":
    # For cron job usage, exit with proper codes
    success = main()
    sys.exit(0 if success else 1)