# Nebenkosten/src/data_processor.py
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from scipy import stats
from sklearn.linear_model import LinearRegression

from .config import CONSTANTS
from .influx_client import InfluxClient # To fetch raw data

class DataProcessor:
    def __init__(self, influx_client: InfluxClient):
        self.influx_client = influx_client
        self.interpolated_series_cache = {}

        # Data reduction thresholds from config
        self.high_freq_threshold_very_dense = CONSTANTS["HIGH_FREQ_THRESHOLD_VERY_DENSE"]
        self.high_freq_threshold_medium_dense = CONSTANTS["HIGH_FREQ_THRESHOLD_MEDIUM_DENSE"]
        self.target_reduction_points = CONSTANTS["TARGET_REDUCTION_POINTS"]
        self.interpolation_weekly_sampling_threshold = CONSTANTS["INTERPOLATION_WEEKLY_SAMPLING_THRESHOLD"]
        self.max_interpolation_points = CONSTANTS["MAX_INTERPOLATION_POINTS"]
        
        # Use centralized meter configuration for installation/deinstallation dates
        self.meter_installation_dates = CONSTANTS["METER_INSTALLATION_DATES"]
        self.meter_deinstallation_dates = CONSTANTS["METER_DEINSTALLATION_DATES"]
        
        # Also store the complete meter configuration for future enhancements
        self.physical_meters = CONSTANTS.get("PHYSICAL_METERS", {})

    def get_meter_installation_date(self, entity_id: str) -> Optional[str]:
        """Get installation date from either legacy or new configuration format."""
        # First check legacy format
        if installation_date := self.meter_installation_dates.get(entity_id):
            return installation_date
        
        # Then check new comprehensive format
        if meter_config := self.physical_meters.get(entity_id):
            return meter_config.get('installation_date')
        
        return None

    def get_meter_deinstallation_date(self, entity_id: str) -> Optional[str]:
        """Get deinstallation date from either legacy or new configuration format."""
        # First check legacy format
        if deinstallation_date := self.meter_deinstallation_dates.get(entity_id):
            return deinstallation_date
        
        # Then check new comprehensive format
        if meter_config := self.physical_meters.get(entity_id):
            return meter_config.get('deinstallation_date')
        
        return None

    def estimate_consumption_rate(self, raw_data: pd.DataFrame) -> Tuple[float, float, str]:
        """
        Estimate consumption rate using multiple statistical methods
        Returns: (rate_per_day, r_squared, method_used)
        """
        if len(raw_data) < 2:
            return 0.0, 0.0, "insufficient_data"
        
        # Convert timestamps to days since first measurement for regression
        first_timestamp = raw_data['timestamp'].iloc[0]
        raw_data = raw_data.copy()
        raw_data['days_since_start'] = (raw_data['timestamp'] - first_timestamp).dt.total_seconds() / (24 * 3600)
        
        X = raw_data['days_since_start'].values.reshape(-1, 1)
        y = raw_data['value'].values
        
        # Method 1: Linear Regression (sklearn)
        try:
            lr_model = LinearRegression()
            lr_model.fit(X, y)
            lr_rate = lr_model.coef_[0]
            lr_r2 = lr_model.score(X, y)
            
            logging.info(f"     📈 Linear Regression: {lr_rate:.4f} units/day (R² = {lr_r2:.3f})")
        except Exception as e:
            logging.warning(f"     ⚠️  Linear Regression failed: {e}")
            lr_rate, lr_r2 = 0.0, 0.0
        
        # Method 2: Scipy linear regression (more statistical info)
        try:
            slope, intercept, r_value, p_value, std_err = stats.linregress(
                raw_data['days_since_start'], raw_data['value']
            )
            scipy_rate = slope
            scipy_r2 = r_value ** 2
            
            logging.info(f"     📊 Scipy Regression: {scipy_rate:.4f} units/day (R² = {scipy_r2:.3f}, p = {p_value:.3f})")
        except Exception as e:
            logging.warning(f"     ⚠️  Scipy Regression failed: {e}")
            scipy_rate, scipy_r2, p_value = 0.0, 0.0, 1.0
        
        # Method 3: Robust method using median of pairwise rates
        try:
            pairwise_rates = []
            for i in range(len(raw_data) - 1):
                for j in range(i + 1, len(raw_data)):
                    time_diff = raw_data['days_since_start'].iloc[j] - raw_data['days_since_start'].iloc[i]
                    value_diff = raw_data['value'].iloc[j] - raw_data['value'].iloc[i]
                    if time_diff > 0:
                        rate = value_diff / time_diff
                        pairwise_rates.append(rate)
            
            if pairwise_rates:
                median_rate = np.median(pairwise_rates)
                mean_rate = np.mean(pairwise_rates)
                std_rate = np.std(pairwise_rates)
                
                logging.info(f"     🎯 Pairwise Rates: median={median_rate:.4f}, mean={mean_rate:.4f}, std={std_rate:.4f}")
            else:
                median_rate = 0.0
        except Exception as e:
            logging.warning(f"     ⚠️  Pairwise Rates calculation failed: {e}")
            median_rate = 0.0
        
        # Method 4: Simple first/last rate (fallback)
        if len(raw_data) >= 2:
            total_time = raw_data['days_since_start'].iloc[-1] - raw_data['days_since_start'].iloc[0]
            total_value = raw_data['value'].iloc[-1] - raw_data['value'].iloc[0]
            simple_rate = total_value / total_time if total_time > 0 else 0.0
            
            logging.info(f"     📏 Simple Rate (first→last): {simple_rate:.4f} units/day")
        else:
            simple_rate = 0.0
        
        # Choose the best method based on data quality and statistical significance
        if len(raw_data) >= 4 and scipy_r2 > 0.7 and p_value < 0.05:
            chosen_rate = scipy_rate
            chosen_r2 = scipy_r2
            chosen_method = f"scipy_regression_r2_{scipy_r2:.3f}"
            logging.info(f"     ✅ Using Scipy regression (high R², significant)")
            
        elif len(raw_data) >= 4 and lr_r2 > 0.6:
            chosen_rate = lr_rate
            chosen_r2 = lr_r2
            chosen_method = f"linear_regression_r2_{lr_r2:.3f}"
            logging.info(f"     ✅ Using Linear regression (decent R²)")
            
        elif len(raw_data) >= 3 and median_rate > 0:
            chosen_rate = median_rate
            chosen_r2 = 0.0
            chosen_method = "median_pairwise"
            logging.info(f"     ✅ Using Median pairwise rate (robust method)")
            
        else:
            chosen_rate = simple_rate
            chosen_r2 = 0.0
            chosen_method = "simple_first_last"
            logging.info(f"     ✅ Using Simple first→last rate (fallback)")
        
        # Ensure non-negative rate (meters should only increase)
        chosen_rate = max(0, chosen_rate)
        
        return chosen_rate, chosen_r2, chosen_method
    
    def _estimate_seasonal_pattern(self, raw_data: pd.DataFrame, entity_id: str) -> dict:
        """
        Estimate seasonal consumption patterns from historical data.
        Returns monthly multipliers relative to annual average.
        """
        if len(raw_data) < 24:  # Need at least 2 years of monthly data for good seasonal estimates
            return {}
        
        try:
            # Calculate monthly consumption rates
            raw_data = raw_data.copy()
            raw_data['month'] = raw_data['timestamp'].dt.month
            raw_data['year'] = raw_data['timestamp'].dt.year
            
            # Calculate consumption rates between consecutive readings
            raw_data = raw_data.sort_values('timestamp')
            monthly_rates = []
            
            for i in range(1, len(raw_data)):
                time_diff_days = (raw_data.iloc[i]['timestamp'] - raw_data.iloc[i-1]['timestamp']).total_seconds() / (24 * 3600)
                if time_diff_days > 0:
                    value_diff = raw_data.iloc[i]['value'] - raw_data.iloc[i-1]['value']
                    daily_rate = value_diff / time_diff_days
                    
                    # Assign rate to the month where consumption primarily occurred
                    mid_timestamp = raw_data.iloc[i-1]['timestamp'] + (raw_data.iloc[i]['timestamp'] - raw_data.iloc[i-1]['timestamp']) / 2
                    monthly_rates.append({
                        'month': mid_timestamp.month,
                        'daily_rate': max(0, daily_rate)
                    })
            
            if not monthly_rates:
                return {}
            
            # Group by month and calculate median rates
            import pandas as pd
            rates_df = pd.DataFrame(monthly_rates)
            monthly_medians = rates_df.groupby('month')['daily_rate'].median()
            
            # Calculate seasonal multipliers
            overall_median = monthly_medians.median()
            if overall_median > 0:
                seasonal_multipliers = (monthly_medians / overall_median).to_dict()
                
                logging.info(f"     🌱 Seasonal pattern for {entity_id}:")
                for month, multiplier in sorted(seasonal_multipliers.items()):
                    month_name = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][month]
                    logging.info(f"       {month_name}: {multiplier:.2f}x")
                
                return seasonal_multipliers
            
        except Exception as e:
            logging.warning(f"     ⚠️ Could not estimate seasonal pattern for {entity_id}: {e}")
        
        return {}
    
    def _enhanced_seasonal_interpolation(self, interpolation_df: pd.DataFrame, entity_id: str, raw_data: pd.DataFrame) -> pd.Series:
        """
        Enhanced interpolation that preserves raw readings and applies seasonal patterns.
        """
        # First, ensure raw readings are preserved exactly
        result_series = interpolation_df['value'].copy()
        
        # Check for configured seasonal patterns first
        configured_patterns = CONSTANTS.get('SEASONAL_PATTERNS', {})
        seasonal_pattern = configured_patterns.get(entity_id, {})
        
        if seasonal_pattern:
            logging.info(f"     🌱 Using configured seasonal pattern for {entity_id}")
        else:
            # Fall back to automatic pattern detection for seasonal meters
            seasonal_meters = ['eg_strom', 'gas_total', 'gastherme_gesamt', 'gastherme_heizen', 
                              'og1_nord_heat', 'og2_nord_heat', 'eg_nord_heat']
            
            use_seasonal = any(seasonal_meter in entity_id for seasonal_meter in seasonal_meters)
            
            if use_seasonal and len(raw_data) >= 12:
                logging.info(f"     🔍 Auto-detecting seasonal pattern for {entity_id}")
                seasonal_pattern = self._estimate_seasonal_pattern(raw_data, entity_id)
            else:
                logging.debug(f"     ➡️  No seasonal pattern for {entity_id} (use_seasonal={use_seasonal}, data_points={len(raw_data)})")
        
        # Fill NaN values using seasonal-aware interpolation
        if result_series.isna().any():
            if seasonal_pattern:
                # Use seasonal interpolation
                result_series = self._seasonal_interpolate(result_series, seasonal_pattern, interpolation_df.index)
                logging.info(f"     ✅ Applied seasonal interpolation for {entity_id}")
            else:
                # Fall back to time-based interpolation
                result_series = result_series.interpolate(method='time')
                logging.debug(f"     📏 Used linear time interpolation for {entity_id}")
        
        return result_series
    
    def _seasonal_interpolate(self, values: pd.Series, seasonal_pattern: dict, timestamps: pd.Index) -> pd.Series:
        """
        Interpolate using seasonal consumption patterns.
        """
        result = values.copy()
        
        # Find gaps that need interpolation
        nan_mask = result.isna()
        if not nan_mask.any():
            return result
        
        # Get non-NaN boundary points
        known_indices = np.where(~nan_mask)[0]
        
        if len(known_indices) < 2:
            # Fall back to simple interpolation if insufficient data
            return result.interpolate(method='time')
        
        # Interpolate each gap using seasonal weighting
        for gap_start_idx in range(len(known_indices) - 1):
            left_idx = known_indices[gap_start_idx]
            right_idx = known_indices[gap_start_idx + 1]
            
            if right_idx - left_idx <= 1:
                continue  # No gap
            
            # Get gap range
            gap_indices = range(left_idx + 1, right_idx)
            
            if not gap_indices:
                continue
            
            left_time = timestamps[left_idx]
            right_time = timestamps[right_idx]
            left_value = result.iloc[left_idx]
            right_value = result.iloc[right_idx]
            
            # Calculate total consumption in gap period
            total_consumption = right_value - left_value
            
            # Distribute consumption based on seasonal pattern
            seasonal_weights = []
            for idx in gap_indices:
                gap_time = timestamps[idx]
                month = gap_time.month
                seasonal_multiplier = seasonal_pattern.get(month, 1.0)
                seasonal_weights.append(seasonal_multiplier)
            
            # Normalize weights
            total_weight = sum(seasonal_weights)
            if total_weight > 0:
                seasonal_weights = [w / total_weight for w in seasonal_weights]
            else:
                # Equal distribution if no seasonal data
                seasonal_weights = [1.0 / len(gap_indices)] * len(gap_indices)
            
            # Apply seasonal distribution
            cumulative_consumption = 0
            for i, idx in enumerate(gap_indices):
                # Calculate consumption up to this point
                consumption_fraction = sum(seasonal_weights[:i+1])
                target_consumption = total_consumption * consumption_fraction
                result.iloc[idx] = left_value + target_consumption
        
        return result

    def reduce_high_frequency_data(self, raw_data: pd.DataFrame, entity_id: str) -> pd.DataFrame:
        """
        Reduce high-frequency data to a manageable number of points for interpolation
        """
        if len(raw_data) <= self.target_reduction_points:
            return raw_data
        
        logging.info(f"     ⚡ Reducing {len(raw_data)} high-frequency data points to ~{self.target_reduction_points} for {entity_id}")
        
        # Strategy 1: Keep first, last, and evenly spaced points
        if len(raw_data) > self.high_freq_threshold_very_dense:
            first_point = raw_data.iloc[0:1]
            last_point = raw_data.iloc[-1:]
            
            middle_data = raw_data.iloc[1:-1]
            if len(middle_data) > 0:
                step = max(1, len(middle_data) // (self.target_reduction_points - 2))
                middle_sampled = middle_data.iloc[::step]
                
                reduced_data = pd.concat([first_point, middle_sampled, last_point], ignore_index=True)
            else:
                reduced_data = pd.concat([first_point, last_point], ignore_index=True)
        
        # Strategy 2: Daily/weekly sampling for medium frequency data
        elif len(raw_data) > self.high_freq_threshold_medium_dense:
            raw_data_indexed = raw_data.set_index('timestamp')
            
            daily_data = raw_data_indexed.resample('D').last().dropna()
            reduced_data = daily_data.reset_index()
        
        else:
            reduced_data = raw_data
        
        # Ensure we have the original first and last points
        if not reduced_data.empty:
            if reduced_data['timestamp'].min() > raw_data['timestamp'].min():
                first_row = raw_data.iloc[0:1]
                reduced_data = pd.concat([first_row, reduced_data], ignore_index=True)
            
            if reduced_data['timestamp'].max() < raw_data['timestamp'].max():
                last_row = raw_data.iloc[-1:]
                reduced_data = pd.concat([reduced_data, last_row], ignore_index=True)
            
            reduced_data = reduced_data.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
        
        logging.info(f"     ✅ Reduced to {len(reduced_data)} points ({len(raw_data)} → {len(reduced_data)})")
        
        return reduced_data

    def create_standardized_daily_series(self, entity_id: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Create a standardized daily series with exactly one data point per day at end of day.
        This provides a consistent foundation for all master meter and virtual meter calculations.
        """
        cache_key = f"{entity_id}_daily_std_{start_date}_{end_date}"
        
        if cache_key in self.interpolated_series_cache:
            return self.interpolated_series_cache[cache_key]
        
        # Get raw data
        raw_data = self.influx_client.fetch_all_meter_data(entity_id)
        
        if raw_data.empty:
            logging.warning(f"  ❌ Cannot create standardized daily series for {entity_id} - no data")
            return pd.DataFrame()
        
        # Reduce high-frequency data if needed
        if len(raw_data) > self.high_freq_threshold_medium_dense:
            raw_data = self.reduce_high_frequency_data(raw_data, entity_id)
        
        # Setup time range and installation/deinstallation logic
        start_ts = pd.Timestamp(start_date, tz='UTC')
        end_ts = pd.Timestamp(end_date, tz='UTC')
        
        installation_date = self.get_meter_installation_date(entity_id)
        installation_ts = pd.Timestamp(installation_date, tz='UTC') if installation_date else start_ts
        
        deinstallation_date = self.get_meter_deinstallation_date(entity_id)
        effective_end = pd.Timestamp(deinstallation_date, tz='UTC') if deinstallation_date else end_ts
        effective_end = min(effective_end, end_ts)
        
        # Calculate effective start (respecting installation date)
        effective_start = max(start_ts, installation_ts)
        
        logging.info(f"   🔄 Creating standardized daily series for {entity_id} ({start_date} to {end_date})")
        logging.info(f"      🏗️  Installation: {installation_date}, Deinstallation: {deinstallation_date}")
        logging.info(f"      📅 Effective processing range: {effective_start.strftime('%Y-%m-%d')} to {effective_end.strftime('%Y-%m-%d')}")
        
        # Apply backward extrapolation if needed
        earliest_data = raw_data.iloc[0]
        earliest_timestamp = earliest_data['timestamp']
        earliest_value = earliest_data['value']
        
        if earliest_timestamp > effective_start:
            if len(raw_data) >= 2:
                rate_per_day, r_squared, method = self.estimate_consumption_rate(raw_data)
                logging.info(f"      🧠 Backward extrapolation rate: {rate_per_day:.4f} units/day using {method}")
                
                if rate_per_day > 0:
                    days_back = (earliest_timestamp - effective_start).total_seconds() / (24 * 3600)
                    extrapolated_value = earliest_value - (rate_per_day * days_back)
                    
                    if extrapolated_value < 0:
                        # Meter would hit zero before start date
                        days_to_zero = earliest_value / rate_per_day
                        zero_timestamp = earliest_timestamp - pd.Timedelta(days=days_to_zero)
                        
                        if zero_timestamp < effective_start:
                            zero_timestamp = effective_start
                        
                        zero_row = pd.DataFrame({'timestamp': [zero_timestamp], 'value': [0.0]})
                        raw_data = pd.concat([zero_row, raw_data], ignore_index=True)
                        
                        if zero_timestamp > effective_start:
                            start_row = pd.DataFrame({'timestamp': [effective_start], 'value': [0.0]})
                            raw_data = pd.concat([start_row, raw_data], ignore_index=True)
                    else:
                        start_row = pd.DataFrame({'timestamp': [effective_start], 'value': [extrapolated_value]})
                        raw_data = pd.concat([start_row, raw_data], ignore_index=True)
                    
                    logging.info(f"      ✅ Added backward extrapolation to {effective_start}")
                else:
                    # For meters with zero or near-zero consumption rate, assume meter started at 0 on installation
                    logging.info(f"      🔄 Zero consumption rate detected - assuming meter started at 0 on installation date")
                    start_row = pd.DataFrame({'timestamp': [effective_start], 'value': [0.0]})
                    raw_data = pd.concat([start_row, raw_data], ignore_index=True)
                    logging.info(f"      ✅ Added installation date point: {effective_start} = 0.0")
            else:
                # Only one data point - assume meter started at 0 on installation
                logging.info(f"      🔄 Single data point - assuming meter started at 0 on installation date")
                start_row = pd.DataFrame({'timestamp': [effective_start], 'value': [0.0]})
                raw_data = pd.concat([start_row, raw_data], ignore_index=True)
                logging.info(f"      ✅ Added installation date point: {effective_start} = 0.0")
        
        # Check if we need forward extrapolation to deinstallation date
        latest_data = raw_data.iloc[-1]
        latest_timestamp = latest_data['timestamp']
        latest_value = latest_data['value']
        
        if latest_timestamp < effective_end:
            logging.info(f"      🔜 Need to extrapolate forward from {latest_timestamp} to {effective_end}")
            
            if len(raw_data) >= 2:
                rate_per_day, r_squared, method = self.estimate_consumption_rate(raw_data)
                
                logging.info(f"      🧠 Forward extrapolation rate: {rate_per_day:.4f} units/day using {method}")
                
                if rate_per_day > 0:
                    days_forward = (effective_end - latest_timestamp).total_seconds() / (24 * 3600)
                    extrapolated_value = latest_value + (rate_per_day * days_forward)
                    
                    end_row = pd.DataFrame({
                        'timestamp': [effective_end],
                        'value': [extrapolated_value]
                    })
                    raw_data = pd.concat([raw_data, end_row], ignore_index=True)
                    
                    logging.info(f"      ✅ Added forward extrapolation: {effective_end} = {extrapolated_value:.2f}")
                else:
                    logging.warning(f"      ⚠️  Rate is {rate_per_day:.4f}, assuming constant value forward")
                    
                    end_row = pd.DataFrame({
                        'timestamp': [effective_end],
                        'value': [latest_value]
                    })
                    raw_data = pd.concat([raw_data, end_row], ignore_index=True)
            else:
                logging.warning(f"      ⚠️  Only one data point, extending with constant value")
                
                end_row = pd.DataFrame({
                    'timestamp': [effective_end],
                    'value': [latest_value]
                })
                raw_data = pd.concat([raw_data, end_row], ignore_index=True)
        
        # Create daily timestamp range (exactly one point per day at end of day)
        daily_range = pd.date_range(start=effective_start, end=effective_end, freq='D', tz='UTC')
        logging.info(f"      📅 Creating {len(daily_range)} daily data points")
        
        # Interpolate to daily timestamps
        raw_data = raw_data.sort_values('timestamp').drop_duplicates(subset=['timestamp']).reset_index(drop=True)
        
        # Combine raw data timestamps with daily grid for better interpolation
        all_timestamps = sorted(set(list(raw_data['timestamp']) + list(daily_range)))
        
        interpolation_df = pd.DataFrame({'timestamp': all_timestamps})
        interpolation_df = interpolation_df.merge(raw_data, on='timestamp', how='left')
        interpolation_df = interpolation_df.set_index('timestamp').sort_index()
        
        # Enhanced interpolation with seasonal awareness
        interpolation_df['value'] = self._enhanced_seasonal_interpolation(
            interpolation_df, entity_id, raw_data=raw_data
        )
        
        # Extract only the daily end-of-day points
        result_df = interpolation_df.loc[daily_range].reset_index()
        
        # Ensure the timestamp column has the correct name
        if 'timestamp' not in result_df.columns:
            # The index was named something else, rename the first column to timestamp
            if len(result_df.columns) > 1 and result_df.columns[0] != 'value':
                result_df = result_df.rename(columns={result_df.columns[0]: 'timestamp'})
            else:
                # Fallback: create timestamp column from daily_range
                result_df['timestamp'] = daily_range[:len(result_df)]
        
        # Cache and return
        self.interpolated_series_cache[cache_key] = result_df
        
        logging.info(f"      ✅ Created standardized daily series with {len(result_df)} points")
        logging.info(f"      📊 Values: {result_df['value'].iloc[0]:.2f} → {result_df['value'].iloc[-1]:.2f}")
        
        return result_df

    def aggregate_daily_to_frequency(self, daily_df: pd.DataFrame, freq: str) -> pd.DataFrame:
        """
        Aggregate standardized daily series to monthly frequency.
        Takes only the reading at the end of each period.
        """
        if daily_df.empty:
            return pd.DataFrame()
        
        if freq == 'D':
            return daily_df.copy()  # Already daily
        
        # Debug the columns to understand the issue
        logging.debug(f"Daily DF columns for aggregation: {daily_df.columns.tolist()}")
        logging.debug(f"Daily DF shape: {daily_df.shape}")
        
        # Ensure we have the right column name
        if 'timestamp' not in daily_df.columns:
            # Try to find the timestamp column
            time_cols = [col for col in daily_df.columns if 'time' in col.lower()]
            if time_cols:
                daily_df = daily_df.rename(columns={time_cols[0]: 'timestamp'})
            else:
                # If index is timestamp, reset it
                if daily_df.index.name is not None and 'time' in str(daily_df.index.name).lower():
                    daily_df = daily_df.reset_index()
                else:
                    logging.error(f"Cannot find timestamp column in daily_df: {daily_df.columns}")
                    return pd.DataFrame()
        
        df = daily_df.copy().set_index('timestamp')
        
        if freq == 'M':
            # Take last reading of each month (end of month value) 
            aggregated = df.resample('M').last()
        else:
            # For other frequencies, use resampling
            aggregated = df.resample(freq).last()
        
        result = aggregated.dropna().reset_index()
        return result

    def create_interpolated_series(self, entity_id: str, start_date: str, end_date: str, freq: str = 'D') -> pd.DataFrame:
        """
        Create an interpolated time series from sparse meter readings with smart backward extrapolation
        """
        cache_key = f"{entity_id}_{start_date}_{end_date}_{freq}"
        
        if cache_key in self.interpolated_series_cache:
            return self.interpolated_series_cache[cache_key]
        
        # Get raw data using the injected InfluxClient
        raw_data = self.influx_client.fetch_all_meter_data(entity_id)
        
        if raw_data.empty:
            logging.warning(f"  ❌ Cannot create interpolated series for {entity_id} - no data")
            return pd.DataFrame()

        earliest_actual_data_timestamp = raw_data['timestamp'].min()
        if earliest_actual_data_timestamp > pd.Timestamp(end_date, tz='UTC'):
            logging.info(f"  ℹ️  Earliest data point ({earliest_actual_data_timestamp}) for {entity_id} is after analysis period end ({end_date}). Assuming 0 consumption for this period.")
            return pd.DataFrame()
        
        logging.info(f"  🔄 Creating interpolated series for {entity_id} ({start_date} to {end_date})")
        
        if len(raw_data) > self.high_freq_threshold_medium_dense:
            raw_data = self.reduce_high_frequency_data(raw_data, entity_id)
        
        start_ts = pd.Timestamp(start_date, tz='UTC')
        end_ts = pd.Timestamp(end_date, tz='UTC')
        
        installation_date = self.meter_installation_dates.get(entity_id, start_date)
        installation_ts = pd.Timestamp(installation_date, tz='UTC')
        
        # Specific debug for problematic meters
        if entity_id in ["strom_1LOG0007013695_NT", "strom_1LOG0007013695_HT"]:
            logging.debug(f"DEBUG_DEINSTALL: Processing {entity_id}")
            logging.debug(f"DEBUG_DEINSTALL: Analysis start_date: {start_date}, end_date: {end_date}")
            logging.debug(f"DEBUG_DEINSTALL: Installation date from CONSTANTS for {entity_id}: {installation_date}")

        logging.info(f"     🏗️  Meter installation date: {installation_date}")

        deinstallation_date = self.meter_deinstallation_dates.get(entity_id)
        deinstallation_ts = None
        if deinstallation_date:
            deinstallation_ts = pd.Timestamp(deinstallation_date, tz='UTC')
            logging.info(f"     🗑️  Meter deinstallation date: {deinstallation_date}")
            if entity_id in ["strom_1LOG0007013695_NT", "strom_1LOG0007013695_HT"]:
                 logging.debug(f"DEBUG_DEINSTALL: Found deinstallation_date for {entity_id}: {deinstallation_date} -> {deinstallation_ts}")
        elif entity_id in ["strom_1LOG0007013695_NT", "strom_1LOG0007013695_HT"]:
            logging.debug(f"DEBUG_DEINSTALL: NO deinstallation_date found for {entity_id} in self.meter_deinstallation_dates. Available keys: {list(self.meter_deinstallation_dates.keys())}")
        
        effective_end = end_ts
        if deinstallation_ts and deinstallation_ts < effective_end:
            effective_end = deinstallation_ts
            logging.info(f"     ✂️  Adjusting analysis end to deinstallation date: {effective_end}")
        
        # Cap at end of today instead of current moment to include today's data
        now_date = datetime.now().date()
        end_of_today = pd.Timestamp(now_date, tz='UTC') + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        if end_of_today < effective_end: # Further cap by end of today if deinstallation is in future or not set
            effective_end = end_of_today
            logging.info(f"     ⏱️  Capping analysis end at end of today: {effective_end}")

        if entity_id in ["strom_1LOG0007013695_NT", "strom_1LOG0007013695_HT"]:
            logging.debug(f"DEBUG_DEINSTALL: For {entity_id}, final effective_end for interpolation range: {effective_end}")
        
        earliest_data = raw_data.iloc[0]
        earliest_timestamp = earliest_data['timestamp']
        earliest_value = earliest_data['value']
        
        logging.info(f"     📅 Earliest data: {earliest_timestamp} = {earliest_value:.2f}")
        
        effective_start = max(start_ts, installation_ts)
        
        if earliest_timestamp > effective_start:
            logging.info(f"     🔙 Need to extrapolate backwards from {earliest_timestamp} to {effective_start}")
            
            if len(raw_data) >= 2:
                rate_per_day, r_squared, method = self.estimate_consumption_rate(raw_data)
                
                logging.info(f"     🧠 Smart rate estimation: {rate_per_day:.4f} units/day using {method}")
                
                if rate_per_day > 0:
                    days_back = (earliest_timestamp - effective_start).total_seconds() / (24 * 3600)
                    extrapolated_value = earliest_value - (rate_per_day * days_back)
                    
                    if extrapolated_value < 0:
                        days_to_zero = earliest_value / rate_per_day
                        zero_timestamp = earliest_timestamp - timedelta(days=days_to_zero)
                        
                        if zero_timestamp < effective_start:
                            zero_timestamp = effective_start
                        
                        logging.info(f"     🎯 Meter would hit zero at: {zero_timestamp}")
                        extrapolated_value = 0.0
                        
                        zero_row = pd.DataFrame({
                            'timestamp': [zero_timestamp],
                            'value': [0.0]
                        })
                        raw_data = pd.concat([zero_row, raw_data], ignore_index=True)
                        
                        if zero_timestamp > effective_start:
                            start_row = pd.DataFrame({
                                'timestamp': [effective_start],
                                'value': [0.0]
                            })
                            raw_data = pd.concat([start_row, raw_data], ignore_index=True)
                    else:
                        start_row = pd.DataFrame({
                            'timestamp': [effective_start],
                            'value': [extrapolated_value]
                        })
                        raw_data = pd.concat([start_row, raw_data], ignore_index=True)
                    
                    logging.info(f"     ✅ Added backward extrapolation: {effective_start} = {extrapolated_value:.2f}")
                
                else:
                    logging.warning(f"     ⚠️  Rate is {rate_per_day:.4f}, assuming constant value backwards")
                    
                    start_row = pd.DataFrame({
                        'timestamp': [effective_start],
                        'value': [earliest_value]
                    })
                    raw_data = pd.concat([start_row, raw_data], ignore_index=True)
            else:
                logging.warning(f"     ⚠️  Only one data point, assuming meter started at zero at installation")
                
                start_row = pd.DataFrame({
                    'timestamp': [installation_ts],
                    'value': [0.0]
                })
                raw_data = pd.concat([start_row, raw_data], ignore_index=True)
        
        raw_data = raw_data.sort_values('timestamp').reset_index(drop=True)
        
        # Check if we need forward extrapolation to deinstallation date
        latest_data = raw_data.iloc[-1]
        latest_timestamp = latest_data['timestamp']
        latest_value = latest_data['value']
        
        if latest_timestamp < effective_end:
            logging.info(f"     🔜 Need to extrapolate forward from {latest_timestamp} to {effective_end}")
            
            if len(raw_data) >= 2:
                rate_per_day, r_squared, method = self.estimate_consumption_rate(raw_data)
                
                logging.info(f"     🧠 Forward extrapolation rate: {rate_per_day:.4f} units/day using {method}")
                
                if rate_per_day > 0:
                    days_forward = (effective_end - latest_timestamp).total_seconds() / (24 * 3600)
                    extrapolated_value = latest_value + (rate_per_day * days_forward)
                    
                    end_row = pd.DataFrame({
                        'timestamp': [effective_end],
                        'value': [extrapolated_value]
                    })
                    raw_data = pd.concat([raw_data, end_row], ignore_index=True)
                    
                    logging.info(f"     ✅ Added forward extrapolation: {effective_end} = {extrapolated_value:.2f}")
                else:
                    logging.warning(f"     ⚠️  Rate is {rate_per_day:.4f}, assuming constant value forward")
                    
                    end_row = pd.DataFrame({
                        'timestamp': [effective_end],
                        'value': [latest_value]
                    })
                    raw_data = pd.concat([raw_data, end_row], ignore_index=True)
            else:
                logging.warning(f"     ⚠️  Only one data point, extending with constant value")
                
                end_row = pd.DataFrame({
                    'timestamp': [effective_end],
                    'value': [latest_value]
                })
                raw_data = pd.concat([raw_data, end_row], ignore_index=True)
        
        # Use ALL available historical data for interpolation, not just data within analysis period
        # This prevents the "started at 0" assumption when we have older data points
        interpolation_data = raw_data.copy()
        interpolation_data = interpolation_data.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)

        if entity_id in ["strom_1LOG0007013695_NT", "strom_1LOG0007013695_HT"]:
            logging.debug(f"DEBUG_DEINSTALL: For {entity_id}, shape of interpolation_data (using all historical data): {interpolation_data.shape}")
            if not interpolation_data.empty:
                logging.debug(f"DEBUG_DEINSTALL: For {entity_id}, interpolation_data time range: {interpolation_data['timestamp'].min()} to {interpolation_data['timestamp'].max()}")
            else:
                logging.debug(f"DEBUG_DEINSTALL: For {entity_id}, interpolation_data is EMPTY.")
        
        if interpolation_data.empty:
            logging.warning(f"  ❌ No data available for {entity_id} after extrapolation")
            return pd.DataFrame()
        
        if len(interpolation_data) < 2:
            logging.warning(f"  ⚠️  Only {len(interpolation_data)} data point(s) for {entity_id} available - cannot interpolate")
            
            if installation_ts > effective_end:
                logging.info(f"  ℹ️  Meter {entity_id} not installed until {installation_date}, after analysis period")
                return pd.DataFrame()
            
            if len(interpolation_data) == 1 and installation_ts <= start_ts:
                single_point = interpolation_data.iloc[0]
                
                simple_series = pd.DataFrame({
                    'timestamp': [start_ts, single_point['timestamp']],
                    'value': [0.0, single_point['value']]
                })
                
                full_range = pd.date_range(start=start_ts, end=effective_end, freq=freq, tz='UTC')
                
                all_timestamps = sorted(set(list(simple_series['timestamp']) + list(full_range)))
                interpolation_df = pd.DataFrame({'timestamp': all_timestamps})
                interpolation_df = interpolation_df.merge(simple_series, on='timestamp', how='left')
                interpolation_df = interpolation_df.drop_duplicates(subset=['timestamp']).set_index('timestamp').sort_index()
                # Use simple time interpolation for single-point cases (seasonal doesn't help here)
                interpolation_df['value'] = interpolation_df['value'].interpolate(method='time')
                
                result_df = interpolation_df.loc[start_ts:end_ts].reset_index()
                self.interpolated_series_cache[cache_key] = result_df
                
                logging.info(f"  ✅ Created simple interpolated series with {len(result_df)} points (0 → {single_point['value']:.2f})")
                return result_df
            
            return pd.DataFrame()
        
        if len(interpolation_data) > self.interpolation_weekly_sampling_threshold:
            temp_range = pd.date_range(start=start_ts, end=effective_end, freq='W', tz='UTC')
            logging.info(f"     ⚡ Using weekly sampling for dense data interpolation")
        else:
            temp_range = pd.date_range(start=start_ts, end=effective_end, freq=freq, tz='UTC')
        
        # For monthly frequency, only use the target frequency timestamps to avoid mixing raw data points
        # This prevents master meter composition from including individual raw readings in monthly series
        if freq == 'M':
            # Only use monthly end-of-month timestamps, not raw data timestamps
            all_timestamps = list(temp_range)
            logging.debug(f"     📅 Using only monthly timestamps for {entity_id} to avoid raw data mixing")
        else:
            # For daily and other frequencies, combine source data timestamps with target range
            all_timestamps = sorted(set(list(interpolation_data['timestamp']) + list(temp_range)))
        
        interpolation_df = pd.DataFrame({'timestamp': all_timestamps})
        interpolation_df = interpolation_df.merge(interpolation_data, on='timestamp', how='left')
        interpolation_df = interpolation_df.drop_duplicates(subset=['timestamp']).set_index('timestamp').sort_index()
        
        # Enhanced interpolation with seasonal awareness
        interpolation_df['value'] = self._enhanced_seasonal_interpolation(
            interpolation_df, entity_id, raw_data=interpolation_data
        )
        
        if len(interpolation_data) > 500:
            daily_range = pd.date_range(start=start_ts, end=effective_end, freq='D', tz='UTC')
            daily_df = pd.DataFrame({'timestamp': daily_range})
            daily_df = daily_df.set_index('timestamp')
            
            combined_index = interpolation_df.index.union(daily_df.index)
            interpolation_df = interpolation_df.reindex(combined_index)
            interpolation_df = interpolation_df.drop_duplicates(subset=['timestamp']).sort_index()
            # Re-apply enhanced interpolation after reindexing
            interpolation_df['value'] = self._enhanced_seasonal_interpolation(
                interpolation_df, entity_id, raw_data=interpolation_data
            )
        
        result_df = interpolation_df.loc[start_ts:effective_end].reset_index()

        if entity_id in ["strom_1LOG0007013695_NT", "strom_1LOG0007013695_HT"]:
            logging.debug(f"DEBUG_DEINSTALL: For {entity_id}, shape of final result_df (after .loc slice to effective_end): {result_df.shape}")
            if not result_df.empty:
                logging.debug(f"DEBUG_DEINSTALL: For {entity_id}, final result_df time range: {result_df['timestamp'].min()} to {result_df['timestamp'].max()}")
            else:
                logging.debug(f"DEBUG_DEINSTALL: For {entity_id}, final result_df is EMPTY after .loc slice to effective_end.")
        
        self.interpolated_series_cache[cache_key] = result_df
        
        logging.info(f"  ✅ Created interpolated series with {len(result_df)} points")
        if not result_df.empty:
            logging.info(f"     📊 Interpolated values: {result_df['value'].min():.2f} → {result_df['value'].max():.2f}")
        
        return result_df