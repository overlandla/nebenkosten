# Nebenkosten/src/calculator.py
import pandas as pd
import logging
from typing import Dict, Optional, Tuple
from .config import CONSTANTS # Import constants from config.py

class ConsumptionCalculator:
    def __init__(self):
        self.gas_energy_content = CONSTANTS["GAS_ENERGY_CONTENT"]
        self.gas_z_factor = CONSTANTS["GAS_Z_FACTOR"]

    def calculate_annual_consumption_from_series(self, interpolated_series: pd.DataFrame, year: int) -> float:
        """Calculate annual consumption from an interpolated time series"""
        if interpolated_series.empty:
            return 0.0
        
        # Get values at year boundaries
        year_start = pd.Timestamp(f'{year}-01-01', tz='UTC')
        year_end = pd.Timestamp(f'{year}-12-31 23:59:59', tz='UTC')
        
        # Find closest values to year boundaries
        series_copy = interpolated_series.set_index('timestamp')
        
        try:
            # Get value at start of year (or closest)
            start_idx = series_copy.index.get_indexer([year_start], method='nearest')[0]
            start_value = series_copy.iloc[start_idx]['value']
            
            # Get value at end of year (or closest)
            end_idx = series_copy.index.get_indexer([year_end], method='nearest')[0]
            end_value = series_copy.iloc[end_idx]['value']
            
            consumption = end_value - start_value
            return max(0, consumption)  # Ensure non-negative
            
        except Exception as e:
            logging.error(f"    ❌ Error calculating consumption for {year}: {e}")
            return 0.0

    def calculate_period_consumption(self, interpolated_series: pd.DataFrame, freq: str = 'D') -> pd.DataFrame:
        """Calculate consumption for a given frequency from an interpolated time series."""
        if interpolated_series.empty:
            return pd.DataFrame()

        # Ensure the series is sorted by timestamp
        series = interpolated_series.sort_values('timestamp').set_index('timestamp')

        if freq == 'M':
            # Special handling for monthly consumption to avoid diff() issues with sparse data
            return self._calculate_monthly_consumption_robust(series)
        else:
            # Calculate difference (consumption) for daily/other frequencies
            # Use .diff() to get the difference between consecutive readings
            consumption = series['value'].diff().fillna(0).to_frame()
            consumption.columns = ['consumption']

            # Ensure consumption is non-negative
            consumption[consumption < 0] = 0

            # Resample to specified frequency to ensure consistent entries
            consumption = consumption.resample(freq).sum()

            return consumption.reset_index()

    def _calculate_monthly_consumption_robust(self, series: pd.DataFrame) -> pd.DataFrame:
        """Calculate monthly consumption by using interpolated values at exact month boundaries."""
        import pandas as pd
        
        # Get the data range
        start_date = series.index.min()
        end_date = series.index.max()
        
        # Generate monthly periods
        monthly_periods = pd.period_range(start=start_date, end=end_date, freq='M')
        
        consumption_results = []
        prev_month_end_value = None
        
        for i, period in enumerate(monthly_periods):
            month_start = period.start_time.tz_localize(start_date.tz) if start_date.tz else period.start_time
            month_end = period.end_time.tz_localize(start_date.tz) if start_date.tz else period.end_time
            
            # Use interpolated values at exact month boundaries
            try:
                month_start_idx = series.index.get_indexer([month_start], method='nearest')[0]
                month_start_value = series.iloc[month_start_idx]['value']
                
                month_end_idx = series.index.get_indexer([month_end], method='nearest')[0]
                month_end_value = series.iloc[month_end_idx]['value']
                
            except (IndexError, KeyError) as e:
                logging.warning(f"Could not find month-start or month-end value for {period}: {e}")
                month_start_value = None
                month_end_value = None
            
            month_consumption = 0
            if month_start_value is not None and month_end_value is not None:
                if prev_month_end_value is not None and month_end_value >= prev_month_end_value:
                    # Normal case: value increased from previous month
                    month_consumption = month_end_value - prev_month_end_value
                elif month_end_value < (prev_month_end_value if prev_month_end_value is not None else float('inf')):
                    # Meter reset or new period start: calculate consumption within the current month
                    month_consumption = month_end_value - month_start_value
                else:
                    # First month of the entire series or other edge case where prev_month_end_value is None
                    month_consumption = 0
                
                month_consumption = max(0, month_consumption) # Ensure non-negative
                prev_month_end_value = month_end_value
            else:
                logging.warning(f"Month {period}: No valid month-start/end values found, consumption = 0")
            
            consumption_results.append({
                'timestamp': month_end,
                'consumption': month_consumption
            })
        
        return pd.DataFrame(consumption_results)

    def get_combined_meter_series(self, old_meter_id: str, new_meter_id: str, replacement_date_str: str, all_interpolated_data: Dict[str, pd.DataFrame]) -> Tuple[Optional[pd.DataFrame], float]:
        """
        Combines the interpolated series of an old meter and a new meter at a specified replacement date.
        The new meter's series is adjusted to continue from the old meter's last value.
        """
        logging.info(f"🔄 Combining meter series: {old_meter_id} (old) and {new_meter_id} (new) at {replacement_date_str}")

        old_series = all_interpolated_data.get(old_meter_id)
        new_series = all_interpolated_data.get(new_meter_id)

        if old_series is None or old_series.empty:
            logging.warning(f"  ⚠️  Old meter series for {old_meter_id} not found or empty. Cannot combine.")
            return None, 0.0 # Return 0.0 offset
        if new_series is None or new_series.empty:
            logging.warning(f"  ⚠️  New meter series for {new_meter_id} not found or empty. Cannot combine.")
            return None, 0.0 # Return 0.0 offset

        replacement_ts = pd.Timestamp(replacement_date_str, tz='UTC')

        # Filter old series up to the replacement date
        old_series_filtered = old_series[old_series['timestamp'] <= replacement_ts].copy()
        
        # Get the last value of the old meter at or before the replacement date
        last_old_value = 0.0
        if not old_series_filtered.empty:
            last_old_value = old_series_filtered['value'].iloc[-1]
        
        # Filter new series from the replacement date onwards
        new_series_filtered = new_series[new_series['timestamp'] >= replacement_ts].copy()

        if new_series_filtered.empty:
            logging.warning(f"  ⚠️  New meter series for {new_meter_id} has no data after replacement date. Cannot combine effectively.")
            return old_series_filtered, 0.0 # Return old series as is, with 0.0 offset

        # Calculate the offset needed for the new meter's values
        # The new meter's first value at or after replacement_ts should align with the old meter's last value
        first_new_value = new_series_filtered['value'].iloc[0]
        offset = last_old_value - first_new_value

        # Apply the offset to the new meter's values
        new_series_filtered['value'] = new_series_filtered['value'] + offset
        
        # Combine the series
        combined_series = pd.concat([old_series_filtered, new_series_filtered]).drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
        
        logging.info(f"  ✅ Combined series for {old_meter_id}/{new_meter_id} created with {len(combined_series)} points. Offset applied: {offset:.2f}")
        return combined_series, offset