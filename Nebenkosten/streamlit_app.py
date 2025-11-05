import streamlit as st
from src.main_app import UtilityAnalyzer
from src.config import CONSTANTS # Import CONSTANTS
import datetime
import io
from contextlib import redirect_stdout
import logging
import plotly.express as px # Import Plotly
import plotly.graph_objects as go # Import for advanced chart features
import pandas as pd # Import pandas for DataFrame operations

# Configure logging for Streamlit app
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

# Set specific loggers to higher levels to reduce noise
logging.getLogger('src.data_processor').setLevel(logging.WARNING)
logging.getLogger('src.influx_client').setLevel(logging.WARNING)
logging.getLogger('src.main_app').setLevel(logging.WARNING)
logging.getLogger('src.calculator').setLevel(logging.WARNING)
logging.getLogger('src.reporter').setLevel(logging.WARNING)

st.set_page_config(layout="wide")

st.title("🏠 Utility Consumption Analyzer")

# Initialize calculator
@st.cache_data
def get_calculator_instance():
    return UtilityAnalyzer()

analyzer = get_calculator_instance()

# Helper function to parse date and time from Excel columns
def parse_datetime_from_excel(ab_datum_raw, ab_zeit_raw, row_idx_for_logging=""):
    date_part = None
    time_part = datetime.time(0, 0)  # Default to midnight

    # Parse Date
    if pd.isna(ab_datum_raw):
        logging.warning(f"Row {row_idx_for_logging}: Ab-Datum is missing.")
        return None

    if isinstance(ab_datum_raw, datetime.datetime):
        date_part = ab_datum_raw.date()
    elif isinstance(ab_datum_raw, datetime.date):
        date_part = ab_datum_raw
    elif isinstance(ab_datum_raw, (int, float)): # Excel serial date
        try:
            # Origin '1899-12-30' for Excel for Windows (day 1 is 1900-01-01)
            date_part = pd.to_datetime(ab_datum_raw, unit='D', origin='1899-12-30').date()
        except (ValueError, TypeError) as e:
            logging.warning(f"Row {row_idx_for_logging}: Could not parse Excel serial date '{ab_datum_raw}': {e}")
            return None
    elif isinstance(ab_datum_raw, str):
        try:
            date_part = datetime.datetime.strptime(ab_datum_raw, '%d.%m.%Y').date()
        except ValueError:
            try: # Attempt generic parsing if specific format fails
                date_part = pd.to_datetime(ab_datum_raw).date()
            except (ValueError, TypeError) as e:
                logging.warning(f"Row {row_idx_for_logging}: Could not parse date string '{ab_datum_raw}': {e}")
                return None
    
    if date_part is None:
        logging.warning(f"Row {row_idx_for_logging}: Failed to determine date part from '{ab_datum_raw}'.")
        return None

    # Parse Time
    if not pd.isna(ab_zeit_raw):
        if isinstance(ab_zeit_raw, datetime.time):
            time_part = ab_zeit_raw
        elif isinstance(ab_zeit_raw, datetime.datetime): # if it's a datetime, extract time
             time_part = ab_zeit_raw.time()
        elif isinstance(ab_zeit_raw, str):
            try:
                time_part = datetime.datetime.strptime(ab_zeit_raw, '%H:%M').time()
            except ValueError:
                try:
                    time_part = datetime.datetime.strptime(ab_zeit_raw, '%H:%M:%S').time()
                except ValueError:
                    logging.warning(f"Row {row_idx_for_logging}: Could not parse time string '{ab_zeit_raw}', using default {time_part}.")
        elif isinstance(ab_zeit_raw, (int, float)): # Excel time as fraction of day
            if 0 <= ab_zeit_raw < 1: # Standard Excel time fraction
                total_seconds_in_day = 24 * 60 * 60
                current_seconds = int(ab_zeit_raw * total_seconds_in_day)
                hours = current_seconds // 3600
                minutes = (current_seconds % 3600) // 60
                seconds = current_seconds % 60
                time_part = datetime.time(hours, minutes, seconds)
            # Handle cases like time given as 'HH.MM' float, e.g. 10.30 for 10:30 - less common for Excel time
            # For now, sticking to Excel standard fraction. If ab_zeit_raw is e.g. 10.5 (meaning 10:30), this logic won't catch it.
            else:
                 logging.warning(f"Row {row_idx_for_logging}: Excel time number '{ab_zeit_raw}' out of expected range (0-1), using default {time_part}.")
        else:
            logging.warning(f"Row {row_idx_for_logging}: Unhandled type for Ab-Zeit '{ab_zeit_raw}' ({type(ab_zeit_raw)}), using default {time_part}.")
    else:
        logging.info(f"Row {row_idx_for_logging}: Ab-Zeit is missing, using default time {time_part}.")
        
    return datetime.datetime.combine(date_part, time_part)

st.header("📊 Consumption Analysis")

# Analysis runs for full time period (2021 onwards)
st.info("Analysis includes all data from 2021 onwards. This provides the most accurate consumption calculations based on complete historical data.")

if st.button("Run Analysis"):
        st.subheader("Analysis Results:")
        
        # Capture logging output from the calculator
        log_capture_string = io.StringIO()
        
        ch = logging.StreamHandler(log_capture_string)
        ch.setLevel(logging.WARNING) # Only capture warnings and errors
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logging.getLogger().addHandler(ch)

        try:
            results = analyzer.analyze_all_meters(start_year=2021)
            analyzer.reporter.generate_raw_and_interpolated_charts(results)
            analyzer.reporter.generate_consumption_charts(results)
        finally:
            logging.getLogger().removeHandler(ch) # Clean up handler
        
        # Only show log output if there are warnings or errors
        log_output = log_capture_string.getvalue()
        if log_output.strip():
            st.text(log_output)

        st.success("Analysis completed!")

        # Generate and display Plotly charts
        st.header("📈 Consumption Trends")

        raw_interpolated_charts = results.get('raw_interpolated_charts', {})
        consumption_charts = results.get('consumption_charts', {})

        if raw_interpolated_charts:
            st.subheader("Raw Readings vs. Interpolated Series")
            for meter_name, fig in raw_interpolated_charts.items():
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No raw vs. interpolated charts available.")

        if consumption_charts:
            st.subheader("Monthly Consumption Charts")
            
            for meter_name, fig in consumption_charts.items():
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No monthly consumption charts available.")

        # New section for Gas Breakdown Chart (in m³)
        st.header("🔥 Gas Consumption Breakdown (Monthly, m³)")
        
        monthly_data_store = results.get('monthly_consumption_data', {})
        gas_therme_gesamt_monthly = monthly_data_store.get('gastherme_gesamt')
        eg_kalfire_monthly = monthly_data_store.get('eg_kalfire')
        # Use gas_total master meter for the total line (not the individual gas_zahler)
        gas_total_meter_id = "gas_total"
        total_gas_line_monthly = monthly_data_store.get(gas_total_meter_id)

        # Check for necessary data and columns for m³ chart
        can_generate_m3_chart = True
        if not (gas_therme_gesamt_monthly is not None and not gas_therme_gesamt_monthly.empty and 'consumption_m3_equivalent' in gas_therme_gesamt_monthly.columns):
            can_generate_m3_chart = False
            logging.warning("Gastherme Gesamt monthly data or 'consumption_m3_equivalent' column missing for m³ chart.")
        if not (eg_kalfire_monthly is not None and not eg_kalfire_monthly.empty and 'consumption' in eg_kalfire_monthly.columns): # eg_kalfire 'consumption' is now m³
            can_generate_m3_chart = False
            logging.warning("EG Kalfire monthly data or 'consumption' column missing for m³ chart.")
        if not (total_gas_line_monthly is not None and not total_gas_line_monthly.empty and 'consumption' in total_gas_line_monthly.columns): # This is m³ from gas_total master meter
            can_generate_m3_chart = False
            logging.warning(f"{gas_total_meter_id} monthly data or 'consumption' column missing for m³ chart's total line.")

        if can_generate_m3_chart:
                
            # Prepare data for stacked bar chart in m³
            df_therme_m3 = gas_therme_gesamt_monthly[['timestamp', 'consumption_m3_equivalent']].copy()
            df_therme_m3.rename(columns={'consumption_m3_equivalent': 'consumption_m3'}, inplace=True)
            df_therme_m3['meter'] = 'Gastherme Gesamt (m³ eq.)'
            
            df_kalfire_m3 = eg_kalfire_monthly[['timestamp', 'consumption']].copy() # 'consumption' is already m³
            df_kalfire_m3.rename(columns={'consumption': 'consumption_m3'}, inplace=True)
            df_kalfire_m3['meter'] = 'EG Kalfire (m³)'
            
            stacked_df_m3 = pd.concat([df_therme_m3, df_kalfire_m3])
            stacked_df_m3['timestamp'] = pd.to_datetime(stacked_df_m3['timestamp'])

            fig_gas_breakdown_m3 = px.bar(
                stacked_df_m3,
                x='timestamp',
                y='consumption_m3',
                color='meter',
                title='Monthly Gas Consumption: Gastherme vs. EG Kalfire (Stacked in m³)',
                labels={'timestamp': 'Month', 'consumption_m3': 'Consumption (m³)', 'meter': 'Component'},
                barmode='stack'
            )

            # Add Total Gas (as configured) consumption (m³) as a line
            df_total_gas_line_m3 = total_gas_line_monthly[['timestamp', 'consumption']].copy() # 'consumption' should be m³
            df_total_gas_line_m3.rename(columns={'consumption': 'consumption_m3'}, inplace=True)
            df_total_gas_line_m3['timestamp'] = pd.to_datetime(df_total_gas_line_m3['timestamp'])
            df_total_gas_line_m3 = df_total_gas_line_m3.sort_values(by='timestamp')

            fig_gas_breakdown_m3.add_trace(go.Scatter(
                x=df_total_gas_line_m3['timestamp'],
                y=df_total_gas_line_m3['consumption_m3'],
                mode='lines+markers',
                name=f'{gas_total_meter_id.replace("_", " ").title()} Total (m³)',
                line=dict(color='black', dash='dash')
            ))
            
            fig_gas_breakdown_m3.update_layout(
                xaxis_title='Month',
                yaxis_title='Monthly Consumption (m³)',
                legend_title_text='Meter / Component'
            )
            st.plotly_chart(fig_gas_breakdown_m3, use_container_width=True)
        else:
            st.info("Data for Gas Consumption Breakdown chart (m³) is not fully available. Check logs for details.")

        # New section for Electricity Breakdown Chart
        st.header("⚡ Electricity Consumption Breakdown (Monthly, kWh)")
        
        # monthly_data_store is already defined from the gas chart section
        
        # Define the ID for the master total electricity meter
        strom_total_master_id = "strom_total"
        total_strom_line_data = monthly_data_store.get(strom_total_master_id)

        # Data for stacked components
        eg_strom_monthly = monthly_data_store.get('eg_strom')
        og1_strom_monthly = monthly_data_store.get('og1_strom')
        og2_strom_monthly = monthly_data_store.get('og2_strom')
        strom_allgemein_monthly = monthly_data_store.get('strom_allgemein')

        can_generate_strom_chart = True
        # This dictionary will hold dataframes for the STACKED components
        stacked_components_data = {}
        # This dataframe will be for the TOTAL line
        df_for_total_line = None

        # Check and prepare data for the TOTAL line (strom_total)
        if total_strom_line_data is not None and \
           not total_strom_line_data.empty and \
           'consumption_kwh' in total_strom_line_data.columns:
            df_for_total_line = total_strom_line_data[['timestamp', 'consumption_kwh']].copy()
        else:
            can_generate_strom_chart = False # If strom_total is missing, we can't generate the intended chart
            logging.warning(f"Data for '{strom_total_master_id}' (consumption_kwh) missing. This is required for the electricity breakdown chart's total line.")

        # Check and prepare data for STACKED components
        component_meter_ids = {
            'eg_strom': eg_strom_monthly,
            'og1_strom': og1_strom_monthly,
            'og2_strom': og2_strom_monthly,
            'strom_allgemein': strom_allgemein_monthly
        }

        for meter_name, df_check in component_meter_ids.items():
            if df_check is not None and not df_check.empty and 'consumption_kwh' in df_check.columns:
                component_df = df_check[['timestamp', 'consumption_kwh']].copy()
                component_df['meter'] = f"{meter_name.replace('_', ' ').title()} (kWh)"
                stacked_components_data[meter_name] = component_df
            else:
                # If a component is missing, log it. The chart can still be generated
                # but the sum of bars might not match the total line.
                logging.warning(f"Data for component '{meter_name}' (consumption_kwh) missing for electricity breakdown chart stack.")
        
        if can_generate_strom_chart: # True if df_for_total_line (strom_total) is available
            
            stacked_strom_dfs_list = [df for df in stacked_components_data.values() if df is not None and not df.empty]
            
            if not stacked_strom_dfs_list:
                logging.warning("No component data available for the stacked part of the electricity breakdown chart.")
                # Create an empty DataFrame to avoid errors with pd.concat if list is empty
                stacked_strom_df_final = pd.DataFrame(columns=['timestamp', 'consumption_kwh', 'meter'])
            else:
                stacked_strom_df_final = pd.concat(stacked_strom_dfs_list)
                if not stacked_strom_df_final.empty: # Ensure concat didn't result in an empty df if list was all empty dfs
                    stacked_strom_df_final['timestamp'] = pd.to_datetime(stacked_strom_df_final['timestamp'])

            # Create the figure using plotly express for bars
            fig_strom_breakdown = px.bar(
                stacked_strom_df_final, # This might be empty if no components found
                x='timestamp',
                y='consumption_kwh',
                color='meter',
                title='Monthly Electricity Consumption Breakdown (kWh)',
                labels={'timestamp': 'Month', 'consumption_kwh': 'Consumption (kWh)', 'meter': 'Component'},
                barmode='stack'
            )

            # Add Total Strom (strom_total) consumption as a line
            # df_for_total_line is already prepared and checked
            df_for_total_line['timestamp'] = pd.to_datetime(df_for_total_line['timestamp'])
            df_for_total_line = df_for_total_line.sort_values(by='timestamp')

            fig_strom_breakdown.add_trace(go.Scatter(
                x=df_for_total_line['timestamp'],
                y=df_for_total_line['consumption_kwh'],
                mode='lines+markers',
                name=f'{strom_total_master_id.replace("_", " ").title()} Total (kWh)',
                line=dict(color='black', dash='dash')
            ))
            
            fig_strom_breakdown.update_layout(
                xaxis_title='Month',
                yaxis_title='Monthly Consumption (kWh)',
                legend_title_text='Meter / Component'
                # barmode='stack' is already set by px.bar for the bar traces
            )
            st.plotly_chart(fig_strom_breakdown, use_container_width=True)
        else:
            st.info(f"Data for '{strom_total_master_id}' (total electricity) is not available for the breakdown chart. Ensure it has monthly kWh consumption data and check logs for details.")

        # New section for Annual Gas Breakdown Chart (in m³)
        st.header("🔥 Gas Consumption Breakdown (Annual, m³)")
        
        # Calculate annual consumption directly from reading differences (not sum of monthly)
        annual_gas_data = {}
        
        if can_generate_m3_chart:
            # Get reading series for annual calculations
            final_readings_monthly = results.get('interpolated_data', {})
            
            # Calculate annual consumption from reading differences
            annual_consumption_gas = {}
            
            # Available years from the data
            available_years = set()
            for meter_id in ['gas_total', 'gastherme_gesamt']:
                if meter_id in final_readings_monthly and not final_readings_monthly[meter_id].empty:
                    meter_years = final_readings_monthly[meter_id]['timestamp'].dt.year.unique()
                    available_years.update(meter_years)
            
            for year in sorted(available_years):
                year_start = pd.Timestamp(f'{year}-01-01', tz='UTC')
                year_end = pd.Timestamp(f'{year}-12-31', tz='UTC')
                
                # Calculate gas_total annual consumption
                if 'gas_total' in final_readings_monthly and not final_readings_monthly[gas_total_meter_id].empty:
                    gas_series = final_readings_monthly[gas_total_meter_id].set_index('timestamp')
                    
                    start_idx = gas_series.index.get_indexer([year_start], method='nearest')[0]
                    end_idx = gas_series.index.get_indexer([year_end], method='nearest')[0]
                    
                    if start_idx >= 0 and end_idx >= 0:
                        start_value = gas_series.iloc[start_idx]['value']
                        end_value = gas_series.iloc[end_idx]['value'] 
                        annual_gas_total = max(0, end_value - start_value)
                        annual_consumption_gas[f'gas_total_{year}'] = annual_gas_total
                
                # Calculate gastherme_gesamt annual consumption (in kWh, will convert to m³)
                if 'gastherme_gesamt' in final_readings_monthly and not final_readings_monthly['gastherme_gesamt'].empty:
                    gastherme_series = final_readings_monthly['gastherme_gesamt'].set_index('timestamp')
                    
                    start_idx = gastherme_series.index.get_indexer([year_start], method='nearest')[0]
                    end_idx = gastherme_series.index.get_indexer([year_end], method='nearest')[0]
                    
                    if start_idx >= 0 and end_idx >= 0:
                        start_value = gastherme_series.iloc[start_idx]['value']
                        end_value = gastherme_series.iloc[end_idx]['value']
                        annual_gastherme_kwh = max(0, end_value - start_value)
                        # Convert kWh to m³ using gas conversion factor
                        gas_conversion_factor = analyzer.gas_conversion_factor
                        annual_gastherme_m3 = annual_gastherme_kwh / gas_conversion_factor if gas_conversion_factor > 0 else 0
                        annual_consumption_gas[f'gastherme_gesamt_{year}'] = annual_gastherme_m3
                
                # Calculate eg_kalfire as gas_total - gastherme_gesamt
                if f'gas_total_{year}' in annual_consumption_gas and f'gastherme_gesamt_{year}' in annual_consumption_gas:
                    annual_kalfire = annual_consumption_gas[f'gas_total_{year}'] - annual_consumption_gas[f'gastherme_gesamt_{year}']
                    annual_consumption_gas[f'eg_kalfire_{year}'] = max(0, annual_kalfire)
            
            # Prepare data for chart
            if annual_consumption_gas:
                # Extract years and create dataframes
                years = sorted(set(int(key.split('_')[-1]) for key in annual_consumption_gas.keys()))
                
                # Gastherme data
                gastherme_data = []
                for year in years:
                    if f'gastherme_gesamt_{year}' in annual_consumption_gas:
                        gastherme_data.append({'year': year, 'consumption_m3': annual_consumption_gas[f'gastherme_gesamt_{year}'], 'meter': 'Gastherme Gesamt (m³ eq.)'})
                
                # Kalfire data  
                kalfire_data = []
                for year in years:
                    if f'eg_kalfire_{year}' in annual_consumption_gas:
                        kalfire_data.append({'year': year, 'consumption_m3': annual_consumption_gas[f'eg_kalfire_{year}'], 'meter': 'EG Kalfire (m³)'})
                
                # Total data
                total_data = []
                for year in years:
                    if f'gas_total_{year}' in annual_consumption_gas:
                        total_data.append({'year': year, 'consumption_m3': annual_consumption_gas[f'gas_total_{year}']})
                
                if gastherme_data or kalfire_data:
                    annual_gas_data['gastherme'] = pd.DataFrame(gastherme_data) if gastherme_data else pd.DataFrame()
                    annual_gas_data['kalfire'] = pd.DataFrame(kalfire_data) if kalfire_data else pd.DataFrame()
                    annual_gas_data['total'] = pd.DataFrame(total_data) if total_data else pd.DataFrame()
            
            # Create annual gas breakdown chart if we have data
            if annual_gas_data:
                # Combine stacked components
                stacked_annual_gas = []
                if 'gastherme' in annual_gas_data:
                    stacked_annual_gas.append(annual_gas_data['gastherme'])
                if 'kalfire' in annual_gas_data:
                    stacked_annual_gas.append(annual_gas_data['kalfire'])
                
                if stacked_annual_gas:
                    stacked_annual_gas_df = pd.concat(stacked_annual_gas, ignore_index=True)
                    
                    fig_gas_breakdown_annual = px.bar(
                        stacked_annual_gas_df,
                        x='year',
                        y='consumption_m3',
                        color='meter',
                        title='Annual Gas Consumption: Gastherme vs. EG Kalfire (Stacked in m³)',
                        labels={'year': 'Year', 'consumption_m3': 'Consumption (m³)', 'meter': 'Component'},
                        barmode='stack'
                    )
                    
                    # Add total gas line if available
                    if 'total' in annual_gas_data:
                        fig_gas_breakdown_annual.add_trace(go.Scatter(
                            x=annual_gas_data['total']['year'],
                            y=annual_gas_data['total']['consumption_m3'],
                            mode='lines+markers',
                            name=f'{gas_total_meter_id.replace("_", " ").title()} Total (m³)',
                            line=dict(color='black', dash='dash')
                        ))
                    
                    fig_gas_breakdown_annual.update_layout(
                        xaxis_title='Year',
                        yaxis_title='Annual Consumption (m³)',
                        legend_title_text='Meter / Component'
                    )
                    st.plotly_chart(fig_gas_breakdown_annual, use_container_width=True)
                else:
                    st.info("No annual gas component data available for stacked chart.")
            else:
                st.info("No annual gas data available for breakdown chart.")
        else:
            st.info("Data for annual gas consumption breakdown chart is not fully available.")

        # New section for Annual Electricity Breakdown Chart
        st.header("⚡ Electricity Consumption Breakdown (Annual, kWh)")
        
        # Calculate annual consumption directly from reading differences (not sum of monthly)
        annual_electricity_data = {}
        
        if can_generate_strom_chart:
            # Get reading series for annual calculations
            final_readings_monthly = results.get('interpolated_data', {})
            
            # Calculate annual consumption from reading differences
            annual_consumption_electricity = {}
            
            # Available years from the data
            available_years = set()
            for meter_id in ['strom_total', 'eg_strom', 'og1_strom', 'og2_strom']:
                if meter_id in final_readings_monthly and not final_readings_monthly[meter_id].empty:
                    meter_years = final_readings_monthly[meter_id]['timestamp'].dt.year.unique()
                    available_years.update(meter_years)
            
            for year in sorted(available_years):
                year_start = pd.Timestamp(f'{year}-01-01', tz='UTC')
                year_end = pd.Timestamp(f'{year}-12-31', tz='UTC')
                
                # Calculate annual consumption for each meter
                meter_debug_info = {}
                for meter_id in ['strom_total', 'eg_strom', 'og1_strom', 'og2_strom']:
                    if meter_id in final_readings_monthly and not final_readings_monthly[meter_id].empty:
                        meter_series = final_readings_monthly[meter_id].set_index('timestamp')
                        
                        start_idx = meter_series.index.get_indexer([year_start], method='nearest')[0]
                        end_idx = meter_series.index.get_indexer([year_end], method='nearest')[0]
                        
                        if start_idx >= 0 and end_idx >= 0:
                            start_value = meter_series.iloc[start_idx]['value']
                            end_value = meter_series.iloc[end_idx]['value']
                            start_timestamp = meter_series.index[start_idx]
                            end_timestamp = meter_series.index[end_idx]
                            annual_consumption = max(0, end_value - start_value)
                            annual_consumption_electricity[f'{meter_id}_{year}'] = annual_consumption
                            
                            # Store debug info for 2024
                            if year == 2024:
                                meter_debug_info[meter_id] = {
                                    'start_ts': start_timestamp,
                                    'start_value': start_value,
                                    'end_ts': end_timestamp,
                                    'end_value': end_value,
                                    'annual_consumption': annual_consumption
                                }
                
                # Show debug info for 2024 if we have inconsistencies
                if year == 2024 and meter_debug_info:
                    with st.expander(f"🔍 Debug: {year} Electricity Meter Reading Details"):
                        for meter_id, info in meter_debug_info.items():
                            st.write(f"**{meter_id}**:")
                            st.write(f"  - Start: {info['start_value']:.1f} kWh at {info['start_ts']}")
                            st.write(f"  - End: {info['end_value']:.1f} kWh at {info['end_ts']}")
                            st.write(f"  - Annual consumption: {info['annual_consumption']:.1f} kWh")
                
                # Calculate strom_allgemein as strom_total - individual meters
                if f'strom_total_{year}' in annual_consumption_electricity:
                    strom_total_annual = annual_consumption_electricity[f'strom_total_{year}']
                    individual_sum = 0
                    individual_details = []
                    
                    for meter in ['eg_strom', 'og1_strom', 'og2_strom']:
                        if f'{meter}_{year}' in annual_consumption_electricity:
                            meter_value = annual_consumption_electricity[f'{meter}_{year}']
                            individual_sum += meter_value
                            individual_details.append(f"{meter}: {meter_value:.1f} kWh")
                    
                    # Debug output for problematic cases
                    if individual_sum > strom_total_annual:
                        st.warning(f"⚠️ **DATA INCONSISTENCY for {year}**: Individual meters sum ({individual_sum:.1f} kWh) exceeds strom_total ({strom_total_annual:.1f} kWh)")
                        st.info(f"Individual meters: {', '.join(individual_details)}")
                        st.info("This suggests an issue with meter data synchronization or overlapping coverage.")
                        # Set strom_allgemein to 0 in this case to avoid negative values
                        strom_allgemein_annual = 0
                    else:
                        strom_allgemein_annual = strom_total_annual - individual_sum
                    
                    annual_consumption_electricity[f'strom_allgemein_{year}'] = strom_allgemein_annual
            
            # Prepare data for chart
            if annual_consumption_electricity:
                # Extract years and create dataframes
                years = sorted(set(int(key.split('_')[-1]) for key in annual_consumption_electricity.keys()))
                
                # Component data
                component_data = {
                    'eg_strom': {'meter_name': 'Eg Strom (kWh)', 'data': []},
                    'og1_strom': {'meter_name': 'Og1 Strom (kWh)', 'data': []},
                    'og2_strom': {'meter_name': 'Og2 Strom (kWh)', 'data': []},
                    'strom_allgemein': {'meter_name': 'Strom Allgemein (kWh)', 'data': []}
                }
                
                for year in years:
                    for meter_key in component_data.keys():
                        if f'{meter_key}_{year}' in annual_consumption_electricity:
                            component_data[meter_key]['data'].append({
                                'year': year, 
                                'consumption_kwh': annual_consumption_electricity[f'{meter_key}_{year}'], 
                                'meter': component_data[meter_key]['meter_name']
                            })
                
                # Total data
                total_data = []
                for year in years:
                    if f'strom_total_{year}' in annual_consumption_electricity:
                        total_data.append({'year': year, 'consumption_kwh': annual_consumption_electricity[f'strom_total_{year}']})
                
                # Create dataframes for components that have data
                annual_strom_components = {}
                for meter_key, meter_info in component_data.items():
                    if meter_info['data']:
                        annual_strom_components[meter_key] = pd.DataFrame(meter_info['data'])
                
                annual_electricity_data['total'] = pd.DataFrame(total_data) if total_data else pd.DataFrame()
            
            # Create annual electricity breakdown chart if we have data
            if annual_electricity_data or annual_strom_components:
                # Combine stacked components
                stacked_annual_strom = []
                for comp_df in annual_strom_components.values():
                    stacked_annual_strom.append(comp_df)
                
                if stacked_annual_strom:
                    stacked_annual_strom_df = pd.concat(stacked_annual_strom, ignore_index=True)
                    
                    fig_strom_breakdown_annual = px.bar(
                        stacked_annual_strom_df,
                        x='year',
                        y='consumption_kwh',
                        color='meter',
                        title='Annual Electricity Consumption Breakdown (kWh)',
                        labels={'year': 'Year', 'consumption_kwh': 'Consumption (kWh)', 'meter': 'Component'},
                        barmode='stack'
                    )
                    
                    # Add total electricity line if available
                    if 'total' in annual_electricity_data and not annual_electricity_data['total'].empty:
                        fig_strom_breakdown_annual.add_trace(go.Scatter(
                            x=annual_electricity_data['total']['year'],
                            y=annual_electricity_data['total']['consumption_kwh'],
                            mode='lines+markers',
                            name=f'{strom_total_master_id.replace("_", " ").title()} Total (kWh)',
                            line=dict(color='black', dash='dash')
                        ))
                    
                    fig_strom_breakdown_annual.update_layout(
                        xaxis_title='Year',
                        yaxis_title='Annual Consumption (kWh)',
                        legend_title_text='Meter / Component'
                    )
                    st.plotly_chart(fig_strom_breakdown_annual, use_container_width=True)
                else:
                    st.info("No annual electricity component data available for stacked chart.")
            else:
                st.info("No annual electricity data available for breakdown chart.")
        else:
            st.info("Data for annual electricity consumption breakdown chart is not fully available.")

st.sidebar.header("Configuration")
st.sidebar.info("InfluxDB connection details are loaded from the `.env` file.")

st.sidebar.header("➕ Add Data Entry")

with st.sidebar.form("data_entry_form"):
    # Dropdown for entity selection
    # Get available meters from the calculator
    all_meters = analyzer.influx_client.discover_available_meters()
    
    # Text input for new or existing entity_id
    typed_entity = st.text_input("Enter new or existing Entity ID:", value="")
    
    # Selectbox for existing entity_ids
    existing_entity_selected = st.selectbox("Or select from existing Entity IDs:", options=[""] + all_meters, index=0) # Add empty option

    # Determine the final selected entity_id
    if typed_entity:
        selected_entity = typed_entity
    elif existing_entity_selected:
        selected_entity = existing_entity_selected
    else:
        selected_entity = "" # No entity selected or typed

    # Date and Time picker
    selected_date = st.date_input("Select Date:", datetime.date.today())
    selected_time = st.time_input("Select Time:", datetime.datetime.now().time())

    # Value input
    value_input = st.number_input("Enter Value:", value=0.0, format="%.2f")

    # Dropdown for _measurement
    measurement_options = ["kWh", "MWh", "m³"] # Changed m3 to m³
    selected_measurement = st.selectbox("Select Measurement Type:", options=measurement_options)

    submitted = st.form_submit_button("Add Entry to InfluxDB")

    if submitted:
        if selected_entity and value_input is not None and selected_date and selected_time and selected_measurement:
            # Combine date and time
            timestamp = datetime.datetime.combine(selected_date, selected_time)
            
            # Write data to InfluxDB
            success = analyzer.influx_client.write_data_to_influx(
                entity_id=selected_entity,
                value=value_input,
                timestamp=timestamp,
                measurement=selected_measurement
            )
            if success:
                st.sidebar.success("Data successfully added to InfluxDB!")
            else:
                st.sidebar.error("Failed to add data to InfluxDB. Check logs for details.")
        else:
            st.sidebar.warning("Please fill in all fields to add data.")

st.sidebar.header("📥 Import from Excel")
uploaded_file = st.sidebar.file_uploader("Choose an XLSX file for 'haupt_strom'", type="xlsx", key="excel_uploader")

# Inputs for entity_id and measurement for the import
# For now, let's keep entity_id fixed as "haupt_strom" as per the JS example context
# and measurement as "kWh". These can be made configurable later if needed.
# import_entity_id = st.sidebar.text_input("Entity ID for import:", value="haupt_strom", key="import_entity_id")
# import_measurement = st.sidebar.selectbox(
#     "Measurement type for import:",
#     options=["kWh", "MWh", "m³"],
#     index=0,
#     key="import_measurement"
# )
fixed_entity_id_for_import = "haupt_strom"
fixed_measurement_for_import = "kWh"


if st.sidebar.button("Import Data from Excel", key="import_excel_button"):
    if uploaded_file is not None:
        try:
            st.sidebar.info(f"Processing '{uploaded_file.name}'...")
            # Use openpyxl engine for .xlsx files
            df_full_sheet = pd.read_excel(uploaded_file, header=None, engine='openpyxl')

            header_row_index = -1
            # Try to find the header row containing "Ab-Datum" within the first 20 rows
            for i, row_series in df_full_sheet.head(20).iterrows():
                # Convert row to list of strings, handling potential NaNs
                row_values = [str(cell) if pd.notna(cell) else "" for cell in row_series.tolist()]
                if any('Ab-Datum' in cell for cell in row_values):
                    header_row_index = i
                    logging.info(f"Found header row at index {i}: {row_values}")
                    break
            
            if header_row_index == -1:
                st.sidebar.error('Header row containing "Ab-Datum" not found in the first 20 rows of the Excel file.')
            else:
                # Extract headers and actual data
                headers = [str(h).strip() if pd.notna(h) else f'unnamed_{idx}' for idx, h in enumerate(df_full_sheet.iloc[header_row_index].tolist())]
                df_data = df_full_sheet.iloc[header_row_index + 1:].copy()
                df_data.columns = headers
                
                # Filter out rows where all values are NaN (often empty rows at the end of data)
                df_data.dropna(how='all', inplace=True)

                logging.info(f"Processed headers: {df_data.columns.tolist()}")
                logging.info(f"Number of data rows found: {len(df_data)}")

                valid_rows_imported = 0
                skipped_rows = 0
                error_messages = []

                for idx, row in df_data.iterrows():
                    row_log_idx = f"Excel Row {header_row_index + 2 + idx}" # User-friendly row number

                    ab_datum_raw = row.get('Ab-Datum')
                    ab_zeit_raw = row.get('Ab-Zeit') # This might be missing
                    zaehlerstand_raw = row.get('Zählerstand')

                    if pd.isna(ab_datum_raw) or pd.isna(zaehlerstand_raw):
                        logging.warning(f"{row_log_idx}: Missing 'Ab-Datum' or 'Zählerstand'. Skipping.")
                        error_messages.append(f"{row_log_idx}: Missing 'Ab-Datum' or 'Zählerstand'.")
                        skipped_rows += 1
                        continue

                    try:
                        meter_value_str = str(zaehlerstand_raw).replace(',', '.').strip()
                        meter_value = float(meter_value_str)
                        if meter_value <= 0 and fixed_measurement_for_import == "kWh": # As per JS logic for positive values
                             logging.warning(f"{row_log_idx}: Zählerstand '{meter_value}' is not positive. Skipping.")
                             error_messages.append(f"{row_log_idx}: Zählerstand '{meter_value}' not positive.")
                             skipped_rows += 1
                             continue
                    except ValueError:
                        logging.warning(f"{row_log_idx}: Could not parse Zählerstand '{zaehlerstand_raw}'. Skipping.")
                        error_messages.append(f"{row_log_idx}: Invalid Zählerstand '{zaehlerstand_raw}'.")
                        skipped_rows += 1
                        continue
                    
                    timestamp_obj = parse_datetime_from_excel(ab_datum_raw, ab_zeit_raw, row_log_idx)

                    if timestamp_obj is None:
                        logging.warning(f"{row_log_idx}: Could not parse date/time. Skipping.")
                        error_messages.append(f"{row_log_idx}: Invalid date/time from '{ab_datum_raw}', '{ab_zeit_raw}'.")
                        skipped_rows += 1
                        continue
                    
                    # Write to InfluxDB
                    success = analyzer.influx_client.write_data_to_influx(
                        entity_id=fixed_entity_id_for_import, # Using fixed entity_id
                        value=meter_value,
                        timestamp=timestamp_obj,
                        measurement=fixed_measurement_for_import # Using fixed measurement
                    )

                    if success:
                        valid_rows_imported += 1
                    else:
                        logging.error(f"{row_log_idx}: Failed to write to InfluxDB.")
                        error_messages.append(f"{row_log_idx}: Failed to write to InfluxDB.")
                        skipped_rows += 1
                
                st.sidebar.success(f"Import finished: {valid_rows_imported} rows imported.")
                if skipped_rows > 0:
                    st.sidebar.warning(f"{skipped_rows} rows skipped.")
                if error_messages:
                    st.sidebar.expander("Show Skipped Row Details").json(error_messages[:20]) # Show first 20 errors
                
        except Exception as e:
            st.sidebar.error(f"Error processing Excel file: {e}")
            logging.error(f"Excel import error: {e}", exc_info=True)

    elif uploaded_file is None:
        st.sidebar.warning("Please upload an XLSX file first.")