# Nebenkosten/src/reporter.py
import logging
import os
from typing import Dict, List
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

class Reporter:
    def __init__(self, meter_replacements: List[Dict]):
        self.meter_replacements = meter_replacements

    def generate_summary_report(self, analysis_results: Dict):
        """Generate a nice summary report"""
        logging.info(f"\n{'='*60}")
        logging.info("📋 ANNUAL CONSUMPTION SUMMARY REPORT")
        logging.info(f"{'='*60}")
        
        if 'annual_consumption' not in analysis_results:
            logging.warning("❌ No consumption data available")
            return
        
        annual_data = analysis_results['annual_consumption']
        
        for year in sorted(annual_data.keys()):
            logging.info(f"\n{'='*20} YEAR {year} {'='*20}")
            
            year_data = annual_data[year]
            
            # Group by category
            water_data = {k: v for k, v in year_data.items() if 'wasser' in k.lower()}
            electricity_data = {k: v for k, v in year_data.items() if 'strom' in k.lower()}
            gas_data = {k: v for k, v in year_data.items() if any(x in k.lower() for x in ['gas', 'therme'])}
            heat_data = {k: v for k, v in year_data.items() if any(x in k.lower() for x in ['heat', 'warm']) and 'wasser' not in k.lower()}
            
            if electricity_data:
                logging.info(f"\n⚡ ELECTRICITY CONSUMPTION:")
                total_kwh = 0
                for meter, data in electricity_data.items():
                    kwh = data.get('consumption_kwh', 0)
                    total_kwh += kwh
                    logging.info(f"  📊 {meter}: {kwh:,.2f} kWh")
                logging.info(f"  🔸 TOTAL ELECTRICITY: {total_kwh:,.2f} kWh")
            
            if water_data:
                logging.info(f"\n💧 WATER CONSUMPTION:")
                total_m3 = 0
                for meter, data in water_data.items():
                    m3 = data.get('consumption_m3', 0)
                    total_m3 += m3
                    logging.info(f"  📊 {meter}: {m3:,.2f} m³")
                logging.info(f"  🔸 TOTAL WATER: {total_m3:,.2f} m³")
            
            if gas_data:
                logging.info(f"\n🔥 GAS CONSUMPTION:")
                total_m3 = 0
                total_kwh = 0
                for meter, data in gas_data.items():
                    m3 = data.get('consumption_m3', 0)
                    kwh = data.get('consumption_kwh', 0)
                    total_m3 += m3
                    total_kwh += kwh
                    logging.info(f"  📊 {meter}: {m3:,.2f} m³ ({kwh:,.2f} kWh)")
                logging.info(f"  🔸 TOTAL GAS: {total_m3:,.2f} m³ ({total_kwh:,.2f} kWh)")
            
            if heat_data:
                logging.info(f"\n🌡️ HEAT CONSUMPTION:")
                for meter, data in heat_data.items():
                    unit = data.get('unit', '')
                    if 'consumption_kwh' in data:
                        logging.info(f"  📊 {meter}: {data['consumption_kwh']:,.2f} kWh")
                    elif 'consumption_m3' in data:
                        logging.info(f"  📊 {meter}: {data['consumption_m3']:,.2f} m³")

    def generate_consumption_charts(self, analysis_results: Dict) -> Dict[str, go.Figure]:
        """Generate Plotly charts for daily consumption rates and return them."""
        logging.info(f"\n{'='*60}")
        logging.info("📊 GENERATING CONSUMPTION CHARTS")
        logging.info(f"{'='*60}")

        if 'monthly_consumption_data' not in analysis_results or not analysis_results['monthly_consumption_data']:
            logging.warning("❌ No monthly consumption data available for charting.")
            return {}

        monthly_data = analysis_results['monthly_consumption_data']
        
        charts = {}
        for meter_name, df in monthly_data.items():
            if df.empty:
                logging.warning(f"  ⚠️  No data for {meter_name} to chart.")
                continue

            fig = go.Figure()
            
            try:
                # Clean up timestamps and create proper monthly labels
                clean_timestamps = pd.to_datetime(df['timestamp']).dt.floor('S')
                
                # Create month labels for better display (YYYY-MM format)
                month_labels = clean_timestamps.dt.strftime('%Y-%m')
                
                fig.add_trace(go.Bar(
                    x=month_labels,
                    y=df['consumption'], 
                    name='Monthly Consumption',
                    text=[f"{val:.1f}" if val > 0 else "0" for val in df['consumption']],
                    textposition='outside'
                ))
                    
            except Exception as e:
                logging.error(f"Error adding trace for {meter_name}: {e}")

            fig.update_layout(
                title=f'Monthly Consumption for {meter_name}',
                xaxis_title='Date',
                yaxis_title='Monthly Consumption',
                hovermode='x unified'
            )
            charts[meter_name] = fig
            logging.info(f"  ✅ Generated chart for {meter_name}.")
        
        logging.info(f"  ✅ All monthly consumption charts generated.")
        return charts

    def generate_raw_and_interpolated_charts(self, analysis_results: Dict) -> Dict[str, go.Figure]:
        """Generate Plotly charts for raw meter readings and their interpolated series and return them."""
        logging.info(f"\n{'='*60}")
        logging.info("📊 GENERATING RAW AND INTERPOLATED CHARTS")
        logging.info(f"{'='*60}")

        if 'raw_data' not in analysis_results or not analysis_results['raw_data']:
            logging.warning("❌ No raw meter data available for charting.")
            return {}
        if 'interpolated_data' not in analysis_results or not analysis_results['interpolated_data']:
            logging.warning("❌ No interpolated data available for charting.")
            return {}

        raw_data_cache = analysis_results['raw_data']
        interpolated_data_cache = analysis_results['interpolated_data']
        meter_offsets = analysis_results.get('meter_offsets', {}) # Get offsets
        
        charts = {}
        
        # Create a mapping for meter replacements for easy lookup
        replacement_map = {r['new_meter']: r for r in self.meter_replacements}

        for meter_name, interpolated_df in interpolated_data_cache.items():
            if interpolated_df.empty:
                logging.warning(f"  ⚠️  No interpolated data for {meter_name} to chart.")
                continue

            # Determine which raw data to use and apply offset
            combined_raw_df = pd.DataFrame()
            current_offset = meter_offsets.get(meter_name, 0.0) # Get offset for this meter
            
            # Check if this meter is a 'new_meter' in a replacement
            if meter_name in replacement_map:
                replacement_info = replacement_map[meter_name]
                old_meter = replacement_info['old_meter']
                replacement_date = pd.Timestamp(replacement_info['replacement_date'], tz='UTC')

                # Get raw data for the old meter up to the replacement date
                if old_meter in raw_data_cache:
                    old_raw_df = raw_data_cache[old_meter].copy()
                    old_raw_df_filtered = old_raw_df[old_raw_df['timestamp'] <= replacement_date].copy()
                    combined_raw_df = pd.concat([combined_raw_df, old_raw_df_filtered], ignore_index=True)
                else:
                    logging.warning(f"     ⚠️  Old meter {old_meter} raw data not found in cache for combination with {meter_name}.")
                
                # Get raw data for the new meter from the replacement date onwards
                if meter_name in raw_data_cache:
                    new_raw_df = raw_data_cache[meter_name].copy()
                    new_raw_df_filtered = new_raw_df[new_raw_df['timestamp'] >= replacement_date].copy()
                    # Apply offset to the new meter's raw values
                    new_raw_df_filtered['value'] = new_raw_df_filtered['value'] + current_offset
                    combined_raw_df = pd.concat([combined_raw_df, new_raw_df_filtered], ignore_index=True)
                else:
                    logging.warning(f"     ⚠️  New meter {meter_name} raw data not found in cache for combination.")
            elif meter_name in raw_data_cache:
                # It's a regular meter, just use its raw data (no offset needed)
                combined_raw_df = raw_data_cache[meter_name].copy()
            else:
                logging.warning(f"  ⚠️  Raw data for {meter_name} not found in cache. Skipping raw data plot.")
                # combined_raw_df will be empty, so no raw data points will be added

            # Filter combined_raw_df to the same time range as interpolated_df
            if not combined_raw_df.empty:
                start_ts_interp = interpolated_df['timestamp'].min()
                end_ts_interp = interpolated_df['timestamp'].max()
                
                combined_raw_df = combined_raw_df[
                    (combined_raw_df['timestamp'] >= start_ts_interp) &
                    (combined_raw_df['timestamp'] <= end_ts_interp)
                ].copy()
                combined_raw_df = combined_raw_df.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)


            fig = go.Figure()
            if not combined_raw_df.empty:
                fig.add_trace(go.Scatter(x=combined_raw_df['timestamp'], y=combined_raw_df['value'], mode='markers', name='Raw Readings',
                                         marker=dict(size=8, opacity=0.8, color='red')))
            fig.add_trace(go.Scatter(x=interpolated_df['timestamp'], y=interpolated_df['value'], mode='lines', name='Interpolated Series',
                                     line=dict(width=2)))

            fig.update_layout(
                title=f'Raw Readings vs. Interpolated Series for {meter_name}',
                xaxis_title='Date',
                yaxis_title='Value',
                hovermode='x unified'
            )
            charts[meter_name] = fig
            logging.info(f"  ✅ Generated raw+interpolated chart for {meter_name}.")
        
        logging.info(f"  ✅ All raw+interpolated charts generated.")
        return charts