# Nebenkosten/src/config.py
import os
import json
import logging
import warnings
from dotenv import load_dotenv
from typing import Dict, List, Optional

def setup_environment():
    """Loads environment variables and configures basic logging."""
    load_dotenv()
    warnings.filterwarnings('ignore')
    # Ensure logging is configured to output DEBUG messages
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Add a StreamHandler to ensure output to console, even if basicConfig is overridden later
    # This is a fallback to ensure debug messages are visible
    import sys
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # Prevent adding multiple handlers if setup_environment is called multiple times
    if not any(isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout for handler in logging.getLogger().handlers):
        logging.getLogger().addHandler(console_handler)

    # Constants loaded from environment variables
    GAS_ENERGY_CONTENT = float(os.getenv('GAS_ENERGY_CONTENT', '11.450'))  # kWh/m³
    GAS_Z_FACTOR = float(os.getenv('GAS_Z_FACTOR', '1.0'))

    # Water heating constants
    WATER_TEMP_DIFF = 40  # 50°C - 10°C
    WATER_SPECIFIC_HEAT = 4.18  # kJ/kg·K
    WATER_DENSITY = 1.0  # kg/L

    # Data reduction thresholds
    HIGH_FREQ_THRESHOLD_VERY_DENSE = 1000
    HIGH_FREQ_THRESHOLD_MEDIUM_DENSE = 100
    TARGET_REDUCTION_POINTS = 50
    INTERPOLATION_WEEKLY_SAMPLING_THRESHOLD = 500
    MAX_INTERPOLATION_POINTS = 1096 # Max ~3 years daily

    # Parse comprehensive meter configuration
    meter_config = _parse_meter_configuration()
    
    # Parse seasonal consumption patterns
    seasonal_patterns = _parse_seasonal_patterns()
    
    return {
        "GAS_ENERGY_CONTENT": GAS_ENERGY_CONTENT,
        "GAS_Z_FACTOR": GAS_Z_FACTOR,
        "WATER_TEMP_DIFF": WATER_TEMP_DIFF,
        "WATER_SPECIFIC_HEAT": WATER_SPECIFIC_HEAT,
        "WATER_DENSITY": WATER_DENSITY,
        "HIGH_FREQ_THRESHOLD_VERY_DENSE": HIGH_FREQ_THRESHOLD_VERY_DENSE,
        "HIGH_FREQ_THRESHOLD_MEDIUM_DENSE": HIGH_FREQ_THRESHOLD_MEDIUM_DENSE,
        "TARGET_REDUCTION_POINTS": TARGET_REDUCTION_POINTS,
        "INTERPOLATION_WEEKLY_SAMPLING_THRESHOLD": INTERPOLATION_WEEKLY_SAMPLING_THRESHOLD,
        "MAX_INTERPOLATION_POINTS": MAX_INTERPOLATION_POINTS,
        "SEASONAL_PATTERNS": seasonal_patterns,
        **meter_config
    }

def _parse_meter_configuration() -> Dict:
    """Parse the comprehensive meter configuration from environment variables."""
    
    # Try new comprehensive format first
    meter_config_str = os.getenv('METER_CONFIGURATION_JSON', '')
    if meter_config_str:
        return _parse_comprehensive_meter_config(meter_config_str)
    
    # Fallback to legacy format for backward compatibility
    logging.warning("🔄 METER_CONFIGURATION_JSON not found, falling back to legacy configuration format")
    return _parse_legacy_meter_config()

def _parse_comprehensive_meter_config(config_str: str) -> Dict:
    """Parse the new comprehensive meter configuration format."""
    try:
        meter_configs = json.loads(config_str)
        if not isinstance(meter_configs, list):
            raise ValueError("METER_CONFIGURATION_JSON must be a JSON array")
        
        # Categorize meters by type
        physical_meters = {}
        master_meter_definitions = []
        virtual_meter_definitions = []
        installation_dates = {}
        deinstallation_dates = {}
        
        for config in meter_configs:
            meter_id = config.get('meter_id')
            meter_type = config.get('type')
            
            if not meter_id or not meter_type:
                logging.warning(f"⚠️ Skipping meter config with missing meter_id or type: {config}")
                continue
            
            # Extract installation/deinstallation dates
            if 'installation_date' in config:
                installation_dates[meter_id] = config['installation_date']
            if 'deinstallation_date' in config:
                deinstallation_dates[meter_id] = config['deinstallation_date']
            
            # Categorize by type
            if meter_type == 'physical':
                physical_meters[meter_id] = config
            elif meter_type == 'master':
                # Convert to legacy master meter format for compatibility
                master_def = {
                    'master_meter_id': meter_id,
                    'output_unit': config.get('output_unit'),
                    'periods': config.get('periods', [])
                }
                master_meter_definitions.append(master_def)
            elif meter_type == 'virtual':
                virtual_meter_definitions.append(config)
        
        logging.info(f"✅ Parsed {len(physical_meters)} physical, {len(master_meter_definitions)} master, {len(virtual_meter_definitions)} virtual meters from comprehensive config")
        
        return {
            'PHYSICAL_METERS': physical_meters,
            'MASTER_METER_DEFINITIONS': master_meter_definitions,
            'VIRTUAL_METER_DEFINITIONS': virtual_meter_definitions,
            'METER_INSTALLATION_DATES': installation_dates,
            'METER_DEINSTALLATION_DATES': deinstallation_dates,
            'EG_KALFIRE_BASE_GAS_METER_ID': _get_virtual_meter_base_id('eg_kalfire', virtual_meter_definitions, 'gas_total'),
            'STROM_ALLGEMEIN_BASE_STROM_METER_ID': _get_virtual_meter_base_id('strom_allgemein', virtual_meter_definitions, 'strom_total'),
            'METER_REPLACEMENTS': []  # Deprecated in favor of master meter periods
        }
        
    except (json.JSONDecodeError, ValueError) as e:
        logging.error(f"❌ Error parsing METER_CONFIGURATION_JSON: {e}. Falling back to legacy format.")
        return _parse_legacy_meter_config()

def _get_virtual_meter_base_id(virtual_meter_name: str, virtual_defs: List[Dict], default: str) -> str:
    """Extract base meter ID for a virtual meter from its definition."""
    for vdef in virtual_defs:
        if vdef.get('meter_id') == virtual_meter_name:
            return vdef.get('base_meter', default)
    return default

def _parse_legacy_meter_config() -> Dict:
    """Parse legacy meter configuration format for backward compatibility."""
    
    # Legacy master meter definitions
    master_defs_str = os.getenv('MASTER_METER_DEFINITIONS_JSON', '[]')
    try:
        master_meter_definitions = json.loads(master_defs_str)
        if not isinstance(master_meter_definitions, list):
            logging.error(f"❌ MASTER_METER_DEFINITIONS_JSON is not a valid JSON list")
            master_meter_definitions = []
    except json.JSONDecodeError:
        logging.error(f"❌ Error decoding MASTER_METER_DEFINITIONS_JSON")
        master_meter_definitions = []
    
    # Legacy individual installation/deinstallation dates (only if no comprehensive config exists)
    installation_dates = {}
    deinstallation_dates = {}
    
    if not os.getenv('METER_CONFIGURATION_JSON'):
        logging.info("🔄 Parsing legacy individual METER_INSTALLATION_* and METER_DEINSTALLATION_* variables")
        meter_keys = [
            'haupt_strom', 'haupt_wasser', 'gas_zahler', 'gas_zahler_alt',
            'eg_strom', 'og1_strom', 'og2_strom',
            'og1_wasser_kalt', 'og1_wasser_warm', 'og2_wasser_kalt', 'og2_wasser_warm',
            'gastherme_gesamt', 'gastherme_heizen', 'gastherme_warmwasser',
            'solarspeicher'
        ]
        
        for key in meter_keys:
            install_var = f"METER_INSTALLATION_{key.upper()}"
            deinstall_var = f"METER_DEINSTALLATION_{key.upper()}"
            
            if install_date := os.getenv(install_var):
                installation_dates[key] = install_date
            if deinstall_date := os.getenv(deinstall_var):
                deinstallation_dates[key] = deinstall_date
    else:
        logging.info("ℹ️  Skipping legacy METER_INSTALLATION_*/METER_DEINSTALLATION_* parsing since METER_CONFIGURATION_JSON is present")
    
    # Legacy meter replacements (deprecated)
    meter_replacements = []
    replacements_str = os.getenv('METER_REPLACEMENTS', '[]')
    if replacements_str != '[]':
        logging.warning("⚠️  METER_REPLACEMENTS is deprecated. Use METER_CONFIGURATION_JSON with master meter periods instead.")
        try:
            meter_replacements = json.loads(replacements_str)
        except json.JSONDecodeError:
            logging.error(f"❌ Error decoding deprecated METER_REPLACEMENTS")
    
    # Legacy virtual meter base IDs (deprecated)
    eg_kalfire_base_id = os.getenv('EG_KALFIRE_BASE_GAS_METER_ID', 'gas_zahler')
    strom_allgemein_base_id = os.getenv('STROM_ALLGEMEIN_BASE_STROM_METER_ID', 'haupt_strom')
    
    if os.getenv('EG_KALFIRE_BASE_GAS_METER_ID') or os.getenv('STROM_ALLGEMEIN_BASE_STROM_METER_ID'):
        logging.warning("⚠️  EG_KALFIRE_BASE_GAS_METER_ID and STROM_ALLGEMEIN_BASE_STROM_METER_ID are deprecated. Define virtual meters in METER_CONFIGURATION_JSON instead.")
    
    return {
        'PHYSICAL_METERS': {},  # Not defined in legacy format
        'MASTER_METER_DEFINITIONS': master_meter_definitions,
        'VIRTUAL_METER_DEFINITIONS': [],  # Not defined in legacy format
        'METER_INSTALLATION_DATES': installation_dates,
        'METER_DEINSTALLATION_DATES': deinstallation_dates,
        'EG_KALFIRE_BASE_GAS_METER_ID': eg_kalfire_base_id,
        'STROM_ALLGEMEIN_BASE_STROM_METER_ID': strom_allgemein_base_id,
        'METER_REPLACEMENTS': meter_replacements
    }

def _parse_seasonal_patterns() -> Dict:
    """Parse seasonal consumption patterns from environment variables."""
    seasonal_patterns = {}
    
    # Try to parse SEASONAL_PATTERNS_JSON
    seasonal_config_str = os.getenv('SEASONAL_PATTERNS_JSON', '')
    if seasonal_config_str:
        try:
            seasonal_configs = json.loads(seasonal_config_str)
            if isinstance(seasonal_configs, dict):
                for meter_id, pattern_config in seasonal_configs.items():
                    if isinstance(pattern_config, dict) and 'monthly_percentages' in pattern_config:
                        monthly_percentages = pattern_config['monthly_percentages']
                        
                        # Validate that percentages are provided for all 12 months and sum to 100%
                        if len(monthly_percentages) == 12:
                            total = sum(monthly_percentages)
                            if 95 <= total <= 105:  # Allow small rounding errors
                                # Normalize to exactly 100%
                                normalized = [p * 100.0 / total for p in monthly_percentages]
                                
                                # Convert percentages to multipliers (relative to average month = 8.33%)
                                average_percent = 100.0 / 12  # 8.33%
                                monthly_multipliers = {i + 1: p / average_percent for i, p in enumerate(normalized)}
                                
                                seasonal_patterns[meter_id] = monthly_multipliers
                                logging.info(f"🌱 Loaded seasonal pattern for {meter_id}")
                                
                                # Log the pattern
                                for month, multiplier in monthly_multipliers.items():
                                    month_name = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][month]
                                    logging.info(f"     {month_name}: {multiplier:.2f}x ({normalized[month-1]:.1f}%)")
                            else:
                                logging.warning(f"⚠️ Seasonal pattern for {meter_id} percentages sum to {total:.1f}%, expected ~100%")
                        else:
                            logging.warning(f"⚠️ Seasonal pattern for {meter_id} must have exactly 12 monthly values, got {len(monthly_percentages)}")
                    else:
                        logging.warning(f"⚠️ Invalid seasonal pattern format for {meter_id}")
                        
            logging.info(f"✅ Loaded {len(seasonal_patterns)} seasonal patterns from configuration")
        except json.JSONDecodeError as e:
            logging.error(f"❌ Error parsing SEASONAL_PATTERNS_JSON: {e}")
        except Exception as e:
            logging.error(f"❌ Error processing seasonal patterns: {e}")
    else:
        logging.info("ℹ️  No SEASONAL_PATTERNS_JSON configured, will use automatic pattern detection")
    
    return seasonal_patterns

# Call setup_environment once when the module is imported
CONSTANTS = setup_environment()