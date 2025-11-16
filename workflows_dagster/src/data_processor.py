"""
Data Processor for Utility Meter Interpolation
Handles interpolation of sparse meter readings to create standardized time series
"""
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from scipy import stats
from sklearn.linear_model import LinearRegression

from .influx_client import InfluxClient


class DataProcessor:
    """
    Processes raw meter data to create standardized interpolated time series.

    Key responsibilities:
    - Interpolate sparse meter readings to daily values
    - Handle meter installation/deinstallation dates
    - Apply backward/forward extrapolation when needed
    - Aggregate daily data to monthly frequency
    - Cache results for performance

    Interpolation Methods:
    - Time-based linear interpolation for meters with frequent readings
    - Regression-based extrapolation for sparse data
    - Seasonal-aware interpolation for heating/cooling meters (optional)
    """

    def __init__(
        self,
        influx_client: InfluxClient,
        high_freq_threshold_medium: int = 100,
        high_freq_threshold_very: int = 1000,
        target_reduction_points: int = 50
    ):
        """
        Initialize DataProcessor

        Args:
            influx_client: InfluxDB client for fetching raw meter data
            high_freq_threshold_medium: Point count above which to apply medium reduction
            high_freq_threshold_very: Point count above which to apply aggressive reduction
            target_reduction_points: Target number of points after reduction
        """
        self.influx_client = influx_client
        self.interpolated_series_cache = {}

        # Data reduction thresholds
        self.high_freq_threshold_medium = high_freq_threshold_medium
        self.high_freq_threshold_very = high_freq_threshold_very
        self.target_reduction_points = target_reduction_points

    def estimate_consumption_rate(
        self,
        raw_data: pd.DataFrame
    ) -> Tuple[float, float, str]:
        """
        Estimate consumption rate using statistical regression

        Uses multiple methods and selects the most reliable:
        1. Scipy linear regression (preferred if R² > 0.7 and p < 0.05)
        2. Sklearn linear regression (if R² > 0.6)
        3. Median pairwise rate (robust method)
        4. Simple first-to-last rate (fallback)

        Args:
            raw_data: DataFrame with 'timestamp' and 'value' columns

        Returns:
            Tuple of (rate_per_day, r_squared, method_used)
            - rate_per_day: Estimated consumption per day
            - r_squared: Coefficient of determination (0-1, higher is better)
            - method_used: String describing which method was chosen

        Example:
            rate, r2, method = processor.estimate_consumption_rate(readings)
            # rate=2.5, r2=0.85, method="scipy_regression_r2_0.850"
        """
        if len(raw_data) < 2:
            return 0.0, 0.0, "insufficient_data"

        # Convert timestamps to days since first measurement for regression
        first_timestamp = raw_data['timestamp'].iloc[0]
        df = raw_data.copy()
        df['days_since_start'] = (
            df['timestamp'] - first_timestamp
        ).dt.total_seconds() / (24 * 3600)

        X = df['days_since_start'].values.reshape(-1, 1)
        y = df['value'].values

        # Method 1: Scipy linear regression (provides p-value)
        try:
            slope, intercept, r_value, p_value, std_err = stats.linregress(
                df['days_since_start'], df['value']
            )
            scipy_rate = slope
            scipy_r2 = r_value ** 2

            logging.debug(
                f"Scipy regression: {scipy_rate:.4f} units/day "
                f"(R²={scipy_r2:.3f}, p={p_value:.3f})"
            )
        except Exception as e:
            logging.warning(f"Scipy regression failed: {e}")
            scipy_rate, scipy_r2, p_value = 0.0, 0.0, 1.0

        # Method 2: Sklearn linear regression
        try:
            lr_model = LinearRegression()
            lr_model.fit(X, y)
            lr_rate = lr_model.coef_[0]
            lr_r2 = lr_model.score(X, y)

            logging.debug(
                f"Sklearn regression: {lr_rate:.4f} units/day (R²={lr_r2:.3f})"
            )
        except Exception as e:
            logging.warning(f"Sklearn regression failed: {e}")
            lr_rate, lr_r2 = 0.0, 0.0

        # Method 3: Robust median of pairwise rates
        try:
            pairwise_rates = []
            for i in range(len(df) - 1):
                for j in range(i + 1, len(df)):
                    time_diff = df['days_since_start'].iloc[j] - df['days_since_start'].iloc[i]
                    value_diff = df['value'].iloc[j] - df['value'].iloc[i]
                    if time_diff > 0:
                        rate = value_diff / time_diff
                        pairwise_rates.append(rate)

            if pairwise_rates:
                median_rate = np.median(pairwise_rates)
                logging.debug(f"Pairwise median rate: {median_rate:.4f} units/day")
            else:
                median_rate = 0.0
        except Exception as e:
            logging.warning(f"Pairwise rates calculation failed: {e}")
            median_rate = 0.0

        # Method 4: Simple first/last rate (fallback)
        if len(df) >= 2:
            total_time = df['days_since_start'].iloc[-1] - df['days_since_start'].iloc[0]
            total_value = df['value'].iloc[-1] - df['value'].iloc[0]
            simple_rate = total_value / total_time if total_time > 0 else 0.0
            logging.debug(f"Simple first-to-last rate: {simple_rate:.4f} units/day")
        else:
            simple_rate = 0.0

        # Choose best method based on data quality
        if len(df) >= 4 and scipy_r2 > 0.7 and p_value < 0.05:
            # High confidence: good R² and statistically significant
            chosen_rate = scipy_rate
            chosen_r2 = scipy_r2
            chosen_method = f"scipy_regression_r2_{scipy_r2:.3f}"
            logging.debug("Using scipy regression (high R², significant)")

        elif len(df) >= 4 and lr_r2 > 0.6:
            # Decent confidence: acceptable R²
            chosen_rate = lr_rate
            chosen_r2 = lr_r2
            chosen_method = f"sklearn_regression_r2_{lr_r2:.3f}"
            logging.debug("Using sklearn regression (decent R²)")

        elif len(df) >= 3 and median_rate > 0:
            # Medium confidence: robust to outliers
            chosen_rate = median_rate
            chosen_r2 = 0.0
            chosen_method = "median_pairwise"
            logging.debug("Using median pairwise rate (robust method)")

        else:
            # Low confidence: fallback method
            chosen_rate = simple_rate
            chosen_r2 = 0.0
            chosen_method = "simple_first_last"
            logging.debug("Using simple first-to-last rate (fallback)")

        # Ensure non-negative rate (cumulative meters should only increase)
        chosen_rate = max(0, chosen_rate)

        return chosen_rate, chosen_r2, chosen_method

    def reduce_high_frequency_data(
        self,
        raw_data: pd.DataFrame,
        entity_id: str
    ) -> pd.DataFrame:
        """
        Reduce high-frequency data to manageable number of points

        For meters with very frequent readings (e.g., every minute), interpolation
        becomes computationally expensive. This method intelligently reduces the
        number of points while preserving key characteristics.

        Strategies:
        - Very dense (>1000 points): Keep first, last, and evenly spaced middle points
        - Medium dense (>100 points): Resample to daily readings
        - Always preserve original first and last points

        Args:
            raw_data: DataFrame with 'timestamp' and 'value' columns
            entity_id: Meter identifier (for logging)

        Returns:
            Reduced DataFrame with same structure as input

        Example:
            Input: 5000 points
            Output: ~50 representative points preserving first/last/trend
        """
        if len(raw_data) <= self.target_reduction_points:
            return raw_data

        logging.info(
            f"Reducing {len(raw_data)} high-frequency points to "
            f"~{self.target_reduction_points} for {entity_id}"
        )

        # Strategy 1: Very dense data - keep first, last, evenly spaced points
        if len(raw_data) > self.high_freq_threshold_very:
            first_point = raw_data.iloc[0:1]
            last_point = raw_data.iloc[-1:]

            middle_data = raw_data.iloc[1:-1]
            if len(middle_data) > 0:
                step = max(1, len(middle_data) // (self.target_reduction_points - 2))
                middle_sampled = middle_data.iloc[::step]

                reduced_data = pd.concat(
                    [first_point, middle_sampled, last_point],
                    ignore_index=True
                )
            else:
                reduced_data = pd.concat(
                    [first_point, last_point],
                    ignore_index=True
                )

        # Strategy 2: Medium dense data - daily sampling
        elif len(raw_data) > self.high_freq_threshold_medium:
            raw_indexed = raw_data.set_index('timestamp')
            daily_data = raw_indexed.resample('D').last().dropna()
            reduced_data = daily_data.reset_index()

        else:
            reduced_data = raw_data

        # Ensure first and last points are preserved exactly
        if not reduced_data.empty:
            if reduced_data['timestamp'].min() > raw_data['timestamp'].min():
                first_row = raw_data.iloc[0:1]
                reduced_data = pd.concat([first_row, reduced_data], ignore_index=True)

            if reduced_data['timestamp'].max() < raw_data['timestamp'].max():
                last_row = raw_data.iloc[-1:]
                reduced_data = pd.concat([reduced_data, last_row], ignore_index=True)

            # Remove any duplicates and sort
            reduced_data = reduced_data.drop_duplicates(subset=['timestamp'])
            reduced_data = reduced_data.sort_values('timestamp').reset_index(drop=True)

        logging.info(
            f"Reduced to {len(reduced_data)} points "
            f"({len(raw_data)} → {len(reduced_data)})"
        )

        return reduced_data

    def create_standardized_daily_series(
        self,
        entity_id: str,
        start_date: str,
        end_date: str,
        installation_date: Optional[str] = None,
        deinstallation_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Create standardized daily series with one data point per day

        This is the core interpolation method. It:
        1. Fetches raw meter data from InfluxDB
        2. Reduces high-frequency data if needed
        3. Applies backward extrapolation to installation date
        4. Applies forward extrapolation to deinstallation/end date
        5. Interpolates to create daily values
        6. Returns DataFrame with exactly one value per day

        Args:
            entity_id: Meter identifier
            start_date: Start of analysis period (ISO format: 'YYYY-MM-DD')
            end_date: End of analysis period
            installation_date: Optional meter installation date (defaults to start_date)
            deinstallation_date: Optional meter removal date (defaults to end_date)

        Returns:
            DataFrame with DatetimeIndex and 'value' column containing daily readings

        Example:
            df = processor.create_standardized_daily_series(
                'gas_zahler',
                '2024-01-01',
                '2024-12-31',
                installation_date='2023-06-15'
            )
            # Returns daily readings from 2024-01-01 to 2024-12-31

        Notes:
            - Results are cached for performance
            - Missing data is interpolated linearly
            - Extrapolation uses regression-based rate estimation
        """
        cache_key = f"{entity_id}_daily_std_{start_date}_{end_date}"

        if cache_key in self.interpolated_series_cache:
            return self.interpolated_series_cache[cache_key]

        # Get raw data
        raw_data = self.influx_client.fetch_all_meter_data(entity_id)

        if raw_data.empty:
            logging.warning(
                f"Cannot create standardized daily series for {entity_id} - no data"
            )
            return pd.DataFrame()

        # Reduce high-frequency data if needed
        if len(raw_data) > self.high_freq_threshold_medium:
            raw_data = self.reduce_high_frequency_data(raw_data, entity_id)

        # Setup time range
        start_ts = pd.Timestamp(start_date, tz='UTC')
        end_ts = pd.Timestamp(end_date, tz='UTC')

        installation_ts = (
            pd.Timestamp(installation_date, tz='UTC')
            if installation_date
            else start_ts
        )

        effective_end = (
            pd.Timestamp(deinstallation_date, tz='UTC')
            if deinstallation_date
            else end_ts
        )
        effective_end = min(effective_end, end_ts)

        effective_start = max(start_ts, installation_ts)

        logging.info(
            f"Creating standardized daily series for {entity_id} "
            f"({start_date} to {end_date})"
        )
        logging.debug(
            f"Installation: {installation_date}, Deinstallation: {deinstallation_date}"
        )
        logging.debug(
            f"Effective range: {effective_start.date()} to {effective_end.date()}"
        )

        # Backward extrapolation if needed
        earliest_data = raw_data.iloc[0]
        earliest_timestamp = earliest_data['timestamp']
        earliest_value = earliest_data['value']

        if earliest_timestamp > effective_start:
            logging.debug(f"Need backward extrapolation from {earliest_timestamp} to {effective_start}")

            if len(raw_data) >= 2:
                rate_per_day, r_squared, method = self.estimate_consumption_rate(raw_data)
                logging.debug(
                    f"Backward extrapolation rate: {rate_per_day:.4f} units/day "
                    f"using {method}"
                )

                if rate_per_day > 0:
                    days_back = (
                        earliest_timestamp - effective_start
                    ).total_seconds() / (24 * 3600)
                    extrapolated_value = earliest_value - (rate_per_day * days_back)

                    if extrapolated_value < 0:
                        # Meter would hit zero before start date
                        days_to_zero = earliest_value / rate_per_day
                        zero_timestamp = earliest_timestamp - pd.Timedelta(days=days_to_zero)

                        if zero_timestamp < effective_start:
                            zero_timestamp = effective_start

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

                    logging.debug(f"Added backward extrapolation to {effective_start}")
                else:
                    # Zero consumption rate - assume meter started at 0
                    start_row = pd.DataFrame({
                        'timestamp': [effective_start],
                        'value': [0.0]
                    })
                    raw_data = pd.concat([start_row, raw_data], ignore_index=True)
                    logging.debug("Zero rate - assuming meter started at 0")
            else:
                # Single data point - assume started at 0
                start_row = pd.DataFrame({
                    'timestamp': [effective_start],
                    'value': [0.0]
                })
                raw_data = pd.concat([start_row, raw_data], ignore_index=True)
                logging.debug("Single data point - assuming meter started at 0")

        # Forward extrapolation if needed
        latest_data = raw_data.iloc[-1]
        latest_timestamp = latest_data['timestamp']
        latest_value = latest_data['value']

        if latest_timestamp < effective_end:
            logging.debug(f"Need forward extrapolation from {latest_timestamp} to {effective_end}")

            if len(raw_data) >= 2:
                rate_per_day, r_squared, method = self.estimate_consumption_rate(raw_data)

                logging.debug(
                    f"Forward extrapolation rate: {rate_per_day:.4f} units/day "
                    f"using {method}"
                )

                if rate_per_day > 0:
                    days_forward = (
                        effective_end - latest_timestamp
                    ).total_seconds() / (24 * 3600)
                    extrapolated_value = latest_value + (rate_per_day * days_forward)

                    end_row = pd.DataFrame({
                        'timestamp': [effective_end],
                        'value': [extrapolated_value]
                    })
                    raw_data = pd.concat([raw_data, end_row], ignore_index=True)

                    logging.debug(
                        f"Added forward extrapolation: {effective_end} = {extrapolated_value:.2f}"
                    )
                else:
                    # Constant value forward
                    end_row = pd.DataFrame({
                        'timestamp': [effective_end],
                        'value': [latest_value]
                    })
                    raw_data = pd.concat([raw_data, end_row], ignore_index=True)
                    logging.debug("Zero rate - extending with constant value")
            else:
                # Only one point - extend with constant value
                end_row = pd.DataFrame({
                    'timestamp': [effective_end],
                    'value': [latest_value]
                })
                raw_data = pd.concat([raw_data, end_row], ignore_index=True)
                logging.debug("Single point - extending with constant value")

        # Create daily timestamp range
        daily_range = pd.date_range(
            start=effective_start,
            end=effective_end,
            freq='D',
            tz='UTC'
        )
        logging.debug(f"Creating {len(daily_range)} daily data points")

        # Prepare for interpolation
        raw_data = raw_data.sort_values('timestamp')
        raw_data = raw_data.drop_duplicates(subset=['timestamp'])
        raw_data = raw_data.reset_index(drop=True)

        # Combine raw data timestamps with daily grid for better interpolation
        all_timestamps = sorted(set(list(raw_data['timestamp']) + list(daily_range)))

        interpolation_df = pd.DataFrame({'timestamp': all_timestamps})
        interpolation_df = interpolation_df.merge(raw_data, on='timestamp', how='left')
        interpolation_df = interpolation_df.set_index('timestamp').sort_index()

        # Perform time-based linear interpolation
        interpolation_df['value'] = interpolation_df['value'].interpolate(method='time')

        # Fill any remaining NaNs (edge cases)
        interpolation_df['value'] = interpolation_df['value'].fillna(method='ffill').fillna(method='bfill')

        # Extract only the daily end-of-day points
        result_df = interpolation_df.loc[daily_range].reset_index()
        result_df.columns = ['timestamp', 'value']

        # Cache and return
        self.interpolated_series_cache[cache_key] = result_df

        logging.info(
            f"Created standardized daily series with {len(result_df)} points "
            f"(values: {result_df['value'].iloc[0]:.2f} → {result_df['value'].iloc[-1]:.2f})"
        )

        return result_df

    def aggregate_daily_to_frequency(
        self,
        daily_df: pd.DataFrame,
        freq: str
    ) -> pd.DataFrame:
        """
        Aggregate standardized daily series to specified frequency

        Takes the last reading of each period.

        Args:
            daily_df: DataFrame with 'timestamp' and 'value' columns (daily readings)
            freq: Pandas frequency string ('D' for daily, 'M' for monthly, 'W' for weekly)

        Returns:
            DataFrame with same structure aggregated to specified frequency

        Example:
            daily_df:
                2024-01-01: 100.0
                2024-01-02: 102.0
                ...
                2024-01-31: 150.0
                2024-02-01: 152.0
                ...

            aggregate_daily_to_frequency(daily_df, 'M'):
                2024-01-31: 150.0  (last value of January)
                2024-02-29: 200.0  (last value of February)

        Notes:
            - 'D' returns the same DataFrame (already daily)
            - 'M' takes last value of each month
            - Other frequencies use pandas resample
        """
        if daily_df.empty:
            return pd.DataFrame()

        if freq == 'D':
            return daily_df.copy()  # Already daily

        # Ensure timestamp column exists
        if 'timestamp' not in daily_df.columns:
            if isinstance(daily_df.index, pd.DatetimeIndex):
                df = daily_df.reset_index()
                if 'timestamp' not in df.columns:
                    df = df.rename(columns={df.columns[0]: 'timestamp'})
            else:
                logging.error("Cannot find timestamp column in daily_df")
                return pd.DataFrame()
        else:
            df = daily_df.copy()

        # Set timestamp as index for resampling
        df = df.set_index('timestamp')

        # Resample to specified frequency (take last value of period)
        aggregated = df.resample(freq).last()

        # Remove NaNs and reset index
        result = aggregated.dropna().reset_index()

        return result
