#!/usr/bin/env python3
"""
Fix for strom_total consumption calculation issue.

The problem: Monthly reading series only has end-of-month points, 
causing .diff() to calculate against the wrong baseline.

Solution: Ensure monthly reading series has both start and end points for each month.
"""

def fix_monthly_master_meter_series(series_df, freq='M'):
    """
    Fix monthly reading series to ensure proper consumption calculation.
    
    For monthly series, we need to ensure we have readings at both the start 
    and end of each month so that .diff() calculates the correct consumption.
    """
    if series_df.empty or freq != 'M':
        return series_df
    
    import pandas as pd
    
    # Ensure timestamp is datetime and sorted
    df = series_df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # Create a complete monthly range
    start_date = df['timestamp'].min()
    end_date = df['timestamp'].max()
    
    # Generate month start and end dates
    monthly_starts = pd.date_range(start=start_date.replace(day=1), end=end_date, freq='MS', tz=start_date.tz)
    monthly_ends = pd.date_range(start=start_date.replace(day=1), end=end_date, freq='M', tz=start_date.tz)
    
    # Combine start and end points
    all_monthly_points = pd.concat([
        pd.Series(monthly_starts),
        pd.Series(monthly_ends)
    ]).drop_duplicates().sort_values()
    
    # Interpolate to these points
    df_indexed = df.set_index('timestamp')
    interpolated = df_indexed.reindex(all_monthly_points, method='nearest', tolerance=pd.Timedelta(days=16))
    
    # Forward fill and backward fill to ensure no gaps
    interpolated = interpolated.fillna(method='ffill').fillna(method='bfill')
    
    result = interpolated.reset_index().rename(columns={'index': 'timestamp'})
    
    return result

# This function should be integrated into the master meter creation process