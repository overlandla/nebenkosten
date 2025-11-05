# Nebenkosten/src/influx_client.py
import pandas as pd
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import os
import logging
from typing import List
from datetime import datetime
from .config import CONSTANTS # Import constants from config.py

class InfluxClient:
    def __init__(self, influx_url=None, token=None, org=None, bucket=None):
        """Initialize InfluxDB connection using environment variables or parameters"""
        
        # Use environment variables as defaults, allow override via parameters
        self.influx_url = influx_url or os.getenv('INFLUX_URL', 'http://localhost:8086')
        self.token = token or os.getenv('INFLUX_TOKEN', '')
        self.org = org or os.getenv('INFLUX_ORG', '')
        self.bucket = bucket or os.getenv('INFLUX_BUCKET', 'lampfi')
        
        logging.info(f"🔌 Connecting to InfluxDB:")
        logging.info(f"   URL: {self.influx_url}")
        logging.info(f"   Org: {self.org or '(default)'}")
        logging.info(f"   Bucket: {self.bucket}")
        logging.info(f"   Token: {'***' + self.token[-8:] if len(self.token) > 8 else '(not set)'}")
        
        # Initialize InfluxDB client
        self.client = InfluxDBClient(
            url=self.influx_url, 
            token=self.token, 
            org=self.org
        )
        self.query_api = self.client.query_api()
        
        # Store all meter data once fetched
        self.meter_data_cache = {}

    def discover_available_meters(self) -> List[str]:
        """Discover all available entity_ids in the database for input_number domain"""
        query = f'''
        from(bucket: "{self.bucket}")
        |> range(start: 1970-01-01T00:00:00Z)
        |> filter(fn: (r) => r["domain"] == "input_number")
        |> filter(fn: (r) => r["_field"] == "value")
        |> group(columns: ["entity_id"])
        |> distinct(column: "entity_id")
        |> yield()
        '''
        
        try:
            result = self.query_api.query_data_frame(query)
            
            # Handle case where result is a list
            if isinstance(result, list):
                if len(result) == 0:
                    return []
                result = pd.concat(result, ignore_index=True)
            
            if result.empty:
                return []
            
            # Filter out None values
            entity_ids = result['entity_id'].dropna().unique().tolist()
            
            # Remove any empty strings
            entity_ids = [eid for eid in entity_ids if eid and str(eid).strip()]
            
            return sorted(entity_ids)
        
        except Exception as e:
            logging.error(f"Error discovering meters: {e}")
            return []
    
    def fetch_all_meter_data(self, entity_id: str) -> pd.DataFrame:
        """Fetch ALL available data for a specific input_number meter"""
        logging.info(f"  📥 Fetching all data for {entity_id}...")
        
        if entity_id in self.meter_data_cache:
            logging.info(f"  ✅ Using cached data for {entity_id}")
            return self.meter_data_cache[entity_id]
        
        query = f'''
        from(bucket: "{self.bucket}")
        |> range(start: 1970-01-01T00:00:00Z)
        |> filter(fn: (r) => r["entity_id"] == "{entity_id}")
        |> filter(fn: (r) => r["domain"] == "input_number")
        |> filter(fn: (r) => r["_field"] == "value")
        |> sort(columns: ["_time"])
        |> yield()
        '''
        
        try:
            result = self.query_api.query_data_frame(query)
            
            # Handle case where result is a list
            if isinstance(result, list):
                if len(result) == 0:
                    logging.warning(f"  ❌ No data found for {entity_id}")
                    return pd.DataFrame()
                result = pd.concat(result, ignore_index=True)
            
            if result.empty:
                logging.warning(f"  ❌ No data found for {entity_id}")
                return pd.DataFrame()
            
            # Clean and prepare data
            df = result[['_time', '_value']].copy()
            df['_time'] = pd.to_datetime(df['_time'], utc=True)
            df = df.sort_values('_time').reset_index(drop=True)
            df.columns = ['timestamp', 'value']
            
            # Remove duplicates (keep last value for same timestamp)
            df = df.drop_duplicates(subset=['timestamp'], keep='last')
            
            # Cache the result
            self.meter_data_cache[entity_id] = df
            
            logging.info(f"  ✅ Found {len(df)} data points for {entity_id}")
            logging.info(f"     📅 From {df['timestamp'].min()} to {df['timestamp'].max()}")
            logging.info(f"     📊 Values: {df['value'].min():.2f} → {df['value'].max():.2f}")
            
            return df
            
        except Exception as e:
            logging.error(f"  ❌ Error fetching data for {entity_id}: {e}")
            return pd.DataFrame()

    def write_data_to_influx(self, entity_id: str, value: float, timestamp: datetime, measurement: str, domain: str = "input_number", source: str = "HA"):
        """
        Writes a single data point to InfluxDB.
        """
        try:
            point = (
                Point(measurement)
                .tag("entity_id", entity_id)
                .tag("domain", domain)
                .tag("source", source)
                .field("value", float(value))
                .time(timestamp)
            )
            write_api = self.client.write_api(write_options=SYNCHRONOUS)
            write_api.write(bucket=self.bucket, org=self.org, record=point)
            logging.info(f"Successfully wrote data to InfluxDB: {entity_id}={value} at {timestamp} ({measurement})")
            return True
        except Exception as e:
            logging.error(f"Failed to write data to InfluxDB for {entity_id}: {e}")
            return False