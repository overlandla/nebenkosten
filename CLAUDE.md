# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Streamlit Application
```bash
# Run the main utility analysis application
cd Nebenkosten && streamlit run streamlit_app.py

# Run with custom port
cd Nebenkosten && streamlit run streamlit_app.py --server.port 8502
```

### Python Environment
```bash
# Activate virtual environment (if created)
cd Nebenkosten && source venv/bin/activate

# Install dependencies (infer from imports)
pip install streamlit pandas plotly influxdb-client python-dotenv scipy scikit-learn openpyxl
```

### Data Processing
```bash
# Run the analyzer directly
cd Nebenkosten && python -m src.main_app

# Process specific utility (if needed)
cd Nebenkosten && python relabel_entries.py
```

## Architecture

### Core System Structure
This is a utility consumption analysis system that processes electricity, gas, and water meter readings from InfluxDB. The system creates continuous reading series from potentially fragmented meter data and calculates consumption patterns.

**Main Components:**
- `streamlit_app.py`: Web interface for analysis and data import
- `src/main_app.py`: Core `UtilityAnalyzer` class that orchestrates the entire analysis
- `src/influx_client.py`: InfluxDB connectivity and data fetching
- `src/data_processor.py`: Data interpolation and series creation
- `src/calculator.py`: Consumption calculations from meter readings
- `src/reporter.py`: Chart generation and reporting
- `src/config.py`: Environment configuration and constants

### Master Meter System
The system supports "master meters" that combine multiple physical meters across different time periods to create continuous reading series. This handles scenarios where meters are replaced or upgraded.

**Configuration via `.env`:**
- `MASTER_METER_DEFINITIONS_JSON`: JSON array defining master meter compositions
- `METER_INSTALLATION_*` and `METER_DEINSTALLATION_*`: Meter lifecycle dates
- `GAS_ENERGY_CONTENT` and `GAS_Z_FACTOR`: Gas-to-energy conversion parameters

### Virtual Meters
The system calculates derived meters:
- `eg_kalfire`: Gas consumption for fireplace (total gas minus heating gas)
- `strom_allgemein`: General electricity consumption (total minus individual meters)

### Data Flow
1. **Discovery**: Find available meters in InfluxDB
2. **Fetching**: Retrieve raw meter data
3. **Interpolation**: Create daily/monthly reading series with gap filling
4. **Master Processing**: Combine meters per master definitions with offset handling
5. **Consumption Calculation**: Convert readings to consumption values
6. **Virtual Meter Generation**: Calculate derived consumption metrics
7. **Reporting**: Generate charts and annual summaries

## Configuration

### Environment Variables (.env file)
Required configuration:
- **InfluxDB**: `INFLUX_URL`, `INFLUX_TOKEN`, `INFLUX_ORG`, `INFLUX_BUCKET`
- **Gas conversion**: `GAS_ENERGY_CONTENT`, `GAS_Z_FACTOR`
- **Meter configuration**: `METER_CONFIGURATION_JSON` (comprehensive meter definitions)

**Note**: Legacy individual `METER_INSTALLATION_*`, `METER_DEINSTALLATION_*`, `METER_REPLACEMENTS`, and virtual meter base ID variables are no longer needed when using `METER_CONFIGURATION_JSON`.

### Comprehensive Meter Configuration
The system now uses a single `METER_CONFIGURATION_JSON` environment variable that defines all meters, their relationships, installation dates, and virtual meter calculations. This replaces the previous scattered configuration approach.

**Meter Types:**
- **Physical**: Real meters that exist in InfluxDB
- **Master**: Composite meters that combine multiple physical meters across time periods (for meter replacements)
- **Virtual**: Calculated meters derived from other meters (e.g., subtraction calculations)

**Example Configuration:**
```json
[
  {
    "meter_id": "strom_total",
    "type": "master",
    "output_unit": "kWh",
    "description": "Total electricity across meter replacements",
    "periods": [
      {"start_date": "2020-01-01", "end_date": "2024-11-26", "composition_type": "sum", "source_meters": ["old_meter_nt", "old_meter_ht"], "source_unit": "kWh"},
      {"start_date": "2024-11-27", "end_date": "9999-12-31", "composition_type": "single", "source_meters": ["new_meter"], "source_unit": "kWh", "apply_offset_from_previous_period": true}
    ]
  },
  {
    "meter_id": "eg_kalfire",
    "type": "virtual",
    "output_unit": "m³",
    "description": "Fireplace gas consumption",
    "calculation_type": "subtraction",
    "base_meter": "gas_total",
    "subtract_meters": ["gastherme_gesamt"],
    "subtract_meter_conversions": {
      "gastherme_gesamt": {"from_unit": "kWh", "to_unit": "m³"}
    }
  },
  {
    "meter_id": "haupt_strom",
    "type": "physical",
    "output_unit": "kWh",
    "installation_date": "2024-11-27",
    "description": "Main electricity meter"
  }
]
```

**Legacy Support:** The system maintains backward compatibility with the old format (`MASTER_METER_DEFINITIONS_JSON` and individual `METER_INSTALLATION_*` variables) if `METER_CONFIGURATION_JSON` is not present.

## Data Import

The Streamlit interface supports Excel import for meter readings with expected columns:
- `Ab-Datum`: Reading date
- `Ab-Zeit`: Reading time (optional)
- `Zählerstand`: Meter reading value

## Development Notes

- All timestamps are handled in UTC
- The system automatically handles unit conversions between m³ and kWh for gas meters
- Meter data is cached in `InfluxClient` to avoid repeated queries
- The system supports both physical meters and calculated master/virtual meters
- Offset calculations ensure continuity when transitioning between meter periods