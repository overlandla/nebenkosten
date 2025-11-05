# Nebenkosten/src/main_app.py
import logging
import traceback
from typing import List, Dict
import pandas as pd
from functools import reduce

from .config import CONSTANTS, setup_environment
from .influx_client import InfluxClient
from .data_processor import DataProcessor
from .calculator import ConsumptionCalculator
from .reporter import Reporter

class UtilityAnalyzer:
    def __init__(self):
        setup_environment() # Setup environment variables and logging
        self.influx_client = InfluxClient()
        self.data_processor = DataProcessor(self.influx_client)
        self.consumption_calculator = ConsumptionCalculator()
        # Note: Meter replacements are now handled by master meter periods, not legacy METER_REPLACEMENTS
        self.reporter = Reporter([]) 
        self.gas_conversion_factor = self.consumption_calculator.gas_energy_content * self.consumption_calculator.gas_z_factor

    def _convert_series_value_for_master(self, series_df: pd.DataFrame, from_unit: str, to_unit: str, meter_id_for_log: str) -> pd.DataFrame:
        # This is for converting 'value' columns of reading series
        if from_unit == to_unit or series_df is None or series_df.empty:
            return series_df.copy() if series_df is not None else pd.DataFrame(columns=['timestamp', 'value'])

        converted_series = series_df.copy()
        if 'value' not in converted_series.columns:
            logging.error(f"Value column missing in series for {meter_id_for_log} during unit conversion. Columns: {converted_series.columns}")
            return pd.DataFrame(columns=['timestamp', 'value'])

        logging.debug(f"Converting reading series for {meter_id_for_log}: {from_unit} -> {to_unit}")
        if from_unit.lower() == 'm³' and to_unit.lower() == 'kwh': # Assuming gas
            converted_series['value'] = converted_series['value'] * self.gas_conversion_factor
        elif from_unit.lower() == 'kwh' and to_unit.lower() == 'm³': # Assuming gas
            if self.gas_conversion_factor == 0:
                logging.error(f"Gas conversion factor is zero for {meter_id_for_log}. Cannot convert kWh to m³ reading series.")
                # Keep original values or set to 0? For readings, keeping original might be less destructive.
                # Or, this scenario should be an error in config. For now, keep original.
            else:
                converted_series['value'] = converted_series['value'] / self.gas_conversion_factor
        else:
            logging.warning(f"Unsupported reading series unit conversion: {from_unit} to {to_unit} for {meter_id_for_log}. Values unchanged.")
        return converted_series

    def _convert_consumption_value(self, value: float, from_unit: str, to_unit: str, meter_id_for_log: str) -> float:
        if from_unit == to_unit: return value
        if from_unit.lower() == 'm³' and to_unit.lower() == 'kwh': return value * self.gas_conversion_factor
        if from_unit.lower() == 'kwh' and to_unit.lower() == 'm³':
            return value / self.gas_conversion_factor if self.gas_conversion_factor > 0 else 0.0
        logging.warning(f"Unsupported consumption unit conversion: {from_unit} to {to_unit} for {meter_id_for_log}."); return value

    def _process_virtual_meters(self, virtual_meter_definitions, monthly_consumption_data, final_readings_daily, final_readings_monthly, meters, start_date_str, end_date_str):
        """Process virtual meters based on configuration definitions."""
        for vm_def in virtual_meter_definitions:
            vm_id = vm_def.get('meter_id')
            if not vm_id:
                logging.warning(f"⚠️ Virtual meter definition missing meter_id: {vm_def}")
                continue
            
            # Clear any existing data for this virtual meter
            if vm_id in final_readings_daily: del final_readings_daily[vm_id]
            if vm_id in final_readings_monthly: del final_readings_monthly[vm_id]
            if vm_id in meters: meters.remove(vm_id)
            
            calc_type = vm_def.get('calculation_type', 'subtraction')
            if calc_type == 'subtraction':
                success = self._calculate_subtraction_virtual_meter(vm_def, monthly_consumption_data, final_readings_daily, final_readings_monthly, start_date_str, end_date_str)
                if success and vm_id not in meters:
                    meters.append(vm_id)
            else:
                logging.warning(f"⚠️ Unsupported virtual meter calculation type '{calc_type}' for {vm_id}")

    def _calculate_subtraction_virtual_meter(self, vm_def, monthly_consumption_data, final_readings_daily, final_readings_monthly, start_date_str, end_date_str):
        """Calculate virtual meter using subtraction method."""
        vm_id = vm_def['meter_id']
        base_meter = vm_def.get('base_meter')
        subtract_meters = vm_def.get('subtract_meters', [])
        output_unit = vm_def.get('output_unit')
        conversions = vm_def.get('subtract_meter_conversions', {})
        
        if not base_meter or not subtract_meters or not output_unit:
            logging.warning(f"⚠️ Virtual meter {vm_id} missing required fields: base_meter, subtract_meters, or output_unit")
            return False
        
        # Get base meter consumption data
        base_consum_df = monthly_consumption_data.get(base_meter)
        if base_consum_df is None or base_consum_df.empty:
            logging.warning(f"⚠️ Base meter '{base_meter}' for virtual meter '{vm_id}' not found or empty")
            return False
        
        logging.info(f"  Calculating virtual meter '{vm_id}' ({output_unit}) using base '{base_meter}' minus {subtract_meters}")
        
        try:
            # Start with base consumption
            result_df = base_consum_df[['timestamp', 'consumption']].copy().rename(columns={'consumption': 'base_consum'})
            
            # Subtract each meter's consumption
            for sub_meter in subtract_meters:
                sub_consum_df = monthly_consumption_data.get(sub_meter)
                if sub_consum_df is None or sub_consum_df.empty:
                    logging.warning(f"⚠️ Subtract meter '{sub_meter}' for virtual meter '{vm_id}' not found, treating as zero")
                    continue
                
                # Apply unit conversion if needed
                sub_consumption = sub_consum_df['consumption'].copy()
                if sub_meter in conversions:
                    conv = conversions[sub_meter]
                    from_unit = conv.get('from_unit')
                    to_unit = conv.get('to_unit')
                    if from_unit and to_unit and from_unit != to_unit:
                        if from_unit.lower() == 'kwh' and to_unit.lower() == 'm³':
                            sub_consumption = sub_consumption / self.gas_conversion_factor if self.gas_conversion_factor > 0 else 0.0
                        elif from_unit.lower() == 'm³' and to_unit.lower() == 'kwh':
                            sub_consumption = sub_consumption * self.gas_conversion_factor
                        else:
                            logging.warning(f"⚠️ Unsupported conversion {from_unit} -> {to_unit} for {sub_meter}")
                
                # Merge and subtract
                sub_df = pd.DataFrame({'timestamp': sub_consum_df['timestamp'], f'sub_{sub_meter}': sub_consumption})
                result_df = pd.merge(result_df, sub_df, on='timestamp', how='left')
                result_df[f'sub_{sub_meter}'] = result_df[f'sub_{sub_meter}'].fillna(0)
                result_df['base_consum'] -= result_df[f'sub_{sub_meter}']
            
            # Clip to non-negative values and finalize
            result_df['consumption'] = result_df['base_consum'].clip(lower=0)
            
            # Additional validation: if base consumption is 0, virtual meter should also be 0
            zero_base_mask = result_df['base_consum'] <= 0
            if zero_base_mask.any():
                logging.info(f"  📊 Setting {zero_base_mask.sum()} periods to 0 for {vm_id} due to zero/negative base consumption")
                result_df.loc[zero_base_mask, 'consumption'] = 0
            
            vm_monthly_consum = result_df[['timestamp', 'consumption']]
            monthly_consumption_data[vm_id] = vm_monthly_consum
            
            # Generate reading series - ensure we start from a reasonable baseline
            vm_readings = vm_monthly_consum.copy()
            vm_readings['value'] = vm_readings['consumption'].cumsum()
            
            # For virtual meters, if all consumption is 0, readings should also be 0
            if vm_readings['consumption'].sum() == 0:
                vm_readings['value'] = 0
                logging.info(f"  📊 Virtual meter {vm_id} has zero total consumption - setting all readings to 0")
            
            final_readings_monthly[vm_id] = vm_readings[['timestamp', 'value']]
            
            # Interpolate daily readings
            daily_vm = vm_readings.set_index('timestamp')[['value']].reindex(
                pd.date_range(start=start_date_str, end=end_date_str, freq='D', tz='UTC')
            ).interpolate(method='linear').ffill().bfill().fillna(0)
            final_readings_daily[vm_id] = daily_vm.reset_index().rename(columns={'index': 'timestamp'})
            
            logging.info(f"  ✅ Successfully calculated virtual meter '{vm_id}'")
            return True
            
        except Exception as e:
            logging.error(f"❌ Error calculating virtual meter '{vm_id}': {e}\n{traceback.format_exc()}")
            return False

    def _process_legacy_virtual_meters(self, monthly_consumption_data, final_readings_daily, final_readings_monthly, meters, start_date_str, end_date_str):
        """Process legacy hardcoded virtual meters for backward compatibility."""
        # EG_KALFIRE (legacy)
        kalfire_base_gas_id = CONSTANTS.get("EG_KALFIRE_BASE_GAS_METER_ID", "gas_zahler")
        base_gas_consum_df = monthly_consumption_data.get(kalfire_base_gas_id)
        gtg_consum_df = monthly_consumption_data.get('gastherme_gesamt')
        eg_kalfire_created = False
        
        if base_gas_consum_df is not None and not base_gas_consum_df.empty and \
           gtg_consum_df is not None and not gtg_consum_df.empty and self.gas_conversion_factor > 0:
            logging.info(f"  Calculating legacy 'eg_kalfire' (m³) using base '{kalfire_base_gas_id}' and 'gastherme_gesamt'.")
            try:
                gz_m3_consum = base_gas_consum_df.set_index('timestamp')['consumption']
                gtg_kwh_consum = gtg_consum_df.set_index('timestamp')['consumption']
                
                aligned_df = pd.DataFrame({'base_gas_m3': gz_m3_consum, 'gtg_kwh': gtg_kwh_consum}).reindex(gz_m3_consum.index.union(gtg_kwh_consum.index)).fillna(0)
                aligned_df['gtg_m3_eq'] = aligned_df['gtg_kwh'] / self.gas_conversion_factor
                aligned_df['consumption'] = (aligned_df['base_gas_m3'] - aligned_df['gtg_m3_eq']).clip(lower=0)
                
                kalfire_monthly_consum = aligned_df[['consumption']].reset_index()
                monthly_consumption_data['eg_kalfire'] = kalfire_monthly_consum
                
                kalfire_readings = kalfire_monthly_consum.copy()
                kalfire_readings['value'] = kalfire_readings['consumption'].cumsum()
                final_readings_monthly['eg_kalfire'] = kalfire_readings[['timestamp', 'value']]
                daily_kalfire = kalfire_readings.set_index('timestamp')[['value']].reindex(pd.date_range(start=start_date_str, end=end_date_str, freq='D', tz='UTC')).interpolate(method='linear').ffill().bfill().fillna(0)
                final_readings_daily['eg_kalfire'] = daily_kalfire.reset_index().rename(columns={'index':'timestamp'})
                eg_kalfire_created = True
            except Exception as e:
                logging.error(f"Error legacy 'eg_kalfire': {e}\n{traceback.format_exc()}")
        if eg_kalfire_created and 'eg_kalfire' not in meters:
            meters.append('eg_kalfire')

        # STROM_ALLGEMEIN (legacy)
        allg_base_strom_id = CONSTANTS.get("STROM_ALLGEMEIN_BASE_STROM_METER_ID", "haupt_strom")
        sub_ids = ['eg_strom', 'og1_strom', 'og2_strom']
        allg_src_ids = [allg_base_strom_id] + sub_ids
        allg_src_consum_dfs = {m: monthly_consumption_data.get(m) for m in allg_src_ids}
        strom_allg_created = False
        
        if all(df is not None and not df.empty for df in allg_src_consum_dfs.values()):
            logging.info(f"  Calculating legacy 'strom_allgemein' (kWh) using base '{allg_base_strom_id}'.")
            try:
                base_consum_df = allg_src_consum_dfs[allg_base_strom_id][['timestamp', 'consumption']].copy().rename(columns={'consumption': 'base_consum'})
                merged_strom_consum_df = base_consum_df
                for sub_id in sub_ids:
                    sub_consum_df = allg_src_consum_dfs[sub_id][['timestamp', 'consumption']].rename(columns={'consumption': f'sub_{sub_id}'})
                    merged_strom_consum_df = pd.merge(merged_strom_consum_df, sub_consum_df, on='timestamp', how='left')
                merged_strom_consum_df = merged_strom_consum_df.fillna(0)

                current_sum_col = 'base_consum'
                for sub_id in sub_ids:
                    merged_strom_consum_df[current_sum_col] -= merged_strom_consum_df[f'sub_{sub_id}']
                
                merged_strom_consum_df['consumption'] = merged_strom_consum_df[current_sum_col].clip(lower=0)
                allg_monthly_consum = merged_strom_consum_df[['timestamp', 'consumption']]
                monthly_consumption_data['strom_allgemein'] = allg_monthly_consum

                allg_readings = allg_monthly_consum.copy()
                allg_readings['value'] = allg_readings['consumption'].cumsum()
                final_readings_monthly['strom_allgemein'] = allg_readings[['timestamp', 'value']]
                daily_allg = allg_readings.set_index('timestamp')[['value']].reindex(pd.date_range(start=start_date_str, end=end_date_str, freq='D', tz='UTC')).interpolate(method='linear').ffill().bfill().fillna(0)
                final_readings_daily['strom_allgemein'] = daily_allg.reset_index().rename(columns={'index':'timestamp'})
                strom_allg_created = True
            except Exception as e:
                logging.error(f"Error legacy 'strom_allgemein': {e}\n{traceback.format_exc()}")
        if strom_allg_created and 'strom_allgemein' not in meters:
            meters.append('strom_allgemein')

    def analyze_all_meters(self, start_year: int = 2021) -> Dict:
        logging.info("🔍 DISCOVERING AVAILABLE METERS...")
        discovered_meters = self.influx_client.discover_available_meters()
        if not discovered_meters: logging.warning("❌ No meters found!"); return {}
        logging.info(f"✅ Found {len(discovered_meters)} meters: {discovered_meters}")

        logging.info(f"\n🔄 FETCHING RAW METER DATA...")
        for meter in discovered_meters: self.influx_client.fetch_all_meter_data(meter)
        
        logging.info(f"\n📈 CREATING STANDARDIZED READING SERIES (PHYSICAL METERS)...")
        from datetime import datetime, timedelta
        start_date_str = f'{start_year}-01-01'
        # Include full current day by setting end date to tomorrow (allowing today's data to be included)
        end_date_str = (datetime.now().date() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Create standardized daily series for all meters (exactly one data point per day)
        logging.info(f"  🔄 Creating standardized daily series for {len(discovered_meters)} meters...")
        raw_standardized_daily = {}
        for meter in discovered_meters:
            standardized_daily = self.data_processor.create_standardized_daily_series(meter, start_date_str, end_date_str)
            if not standardized_daily.empty:
                raw_standardized_daily[meter] = standardized_daily
                logging.info(f"    ✅ {meter}: {len(standardized_daily)} daily points")
            else:
                logging.warning(f"    ❌ {meter}: No standardized data")
        
        # Aggregate daily to monthly using end-of-month values
        logging.info(f"  📅 Aggregating to monthly series...")
        raw_interpolated_readings_daily = raw_standardized_daily.copy()
        raw_interpolated_readings_monthly = {}
        for meter, daily_df in raw_standardized_daily.items():
            monthly_df = self.data_processor.aggregate_daily_to_frequency(daily_df, 'M')
            if not monthly_df.empty:
                raw_interpolated_readings_monthly[meter] = monthly_df
                logging.info(f"    ✅ {meter}: {len(monthly_df)} monthly points")
            else:
                logging.warning(f"    ❌ {meter}: No monthly data")

        # These will store the final set of *reading* series after master meter processing
        final_readings_daily = raw_interpolated_readings_daily.copy()
        final_readings_monthly = raw_interpolated_readings_monthly.copy()
        
        current_meter_ids = list(discovered_meters) # All meters available for processing

        # --- MASTER METER DEFINITIONS PROCESSING (Creates Continuous Reading Series) ---
        master_meter_definitions = CONSTANTS.get("MASTER_METER_DEFINITIONS", [])
        master_meter_offsets_applied = {} # Store offsets if needed by reporter

        if master_meter_definitions:
            logging.info(f"\n🛠️ PROCESSING MASTER METER DEFINITIONS ({len(master_meter_definitions)})...")
            for master_def in master_meter_definitions:
                master_id = master_def.get("master_meter_id")
                master_out_unit = master_def.get("output_unit")
                periods_def = master_def.get("periods", [])
                if not all([master_id, master_out_unit, periods_def]):
                    logging.warning(f"  ⚠️ Invalid master definition: {master_def}"); continue
                logging.info(f"  Master Meter: {master_id} (Target Unit: {master_out_unit})")

                # These will collect period segments for the current master meter
                master_period_segments_daily, master_period_segments_monthly = [], []
                
                last_processed_period_series_daily, last_processed_period_series_monthly = None, None

                for period_idx, period_def in enumerate(periods_def):
                    p_start, p_end = period_def.get("start_date"), period_def.get("end_date")
                    comp_type, src_ids, src_unit = period_def.get("composition_type"), period_def.get("source_meters", []), period_def.get("source_unit")
                    apply_offset = period_def.get("apply_offset_from_previous_period", False)

                    if not all([p_start, p_end, comp_type, src_ids, src_unit]):
                        logging.warning(f"    Invalid period in {master_id}: {period_def}"); continue
                    p_start_ts, p_end_ts = pd.Timestamp(p_start, tz='UTC'), pd.Timestamp(p_end, tz='UTC')
                    logging.info(f"    Period {period_idx+1}: {p_start}-{p_end}, Type: {comp_type}, Src: {src_ids}, SrcUnit: {src_unit}, Offset: {apply_offset}")

                    for freq_lbl, base_src_readings_dict, period_segments_list_ref, last_series_ref_name in [
                        ("daily", raw_interpolated_readings_daily, master_period_segments_daily, "last_processed_period_series_daily"),
                        ("monthly", raw_interpolated_readings_monthly, master_period_segments_monthly, "last_processed_period_series_monthly")
                    ]:
                        converted_src_series_for_period = []
                        valid_src_found = True
                        for src_id in src_ids:
                            raw_src_series = base_src_readings_dict.get(src_id)
                            if raw_src_series is None or raw_src_series.empty:
                                logging.warning(f"      Src '{src_id}' for {master_id} ({freq_lbl}) not found in raw readings for period.");
                                if comp_type == "single": valid_src_found = False; break
                                continue
                            converted = self._convert_series_value_for_master(raw_src_series, src_unit, master_out_unit, f"{master_id}/{src_id}")
                            if converted.empty and src_unit != master_out_unit: valid_src_found = False; break
                            if not converted.empty: converted_src_series_for_period.append(converted)
                        
                        if not valid_src_found or not converted_src_series_for_period:
                            logging.warning(f"      Skipping {freq_lbl} for period of {master_id} due to source issues."); continue

                        current_period_composed_data = pd.DataFrame()
                        # Debug source data before composition for strom_total
                        if master_id == "strom_total" and freq_lbl == "monthly":
                            logging.info(f"DEBUG STROM_TOTAL P{period_idx+1} ({freq_lbl}): Source meters: {src_ids}")
                            for i, src_series in enumerate(converted_src_series_for_period):
                                src_id = src_ids[i] if i < len(src_ids) else f"src_{i}"
                                logging.info(f"DEBUG STROM_TOTAL P{period_idx+1} ({freq_lbl}): Source {src_id} has {len(src_series)} points")
                                if len(src_series) > 0:
                                    logging.info(f"DEBUG STROM_TOTAL P{period_idx+1} ({freq_lbl}): Source {src_id} sample:\n{src_series.head()}")

                        if comp_type == "single":
                            if len(converted_src_series_for_period) == 1: current_period_composed_data = converted_src_series_for_period[0]
                            else: logging.warning(f"      'single' expects 1 source for {master_id}, got {len(converted_src_series_for_period)}."); continue
                        elif comp_type == "sum":
                            indexed_dfs = [s.set_index('timestamp')[['value']].rename(columns={'value': f'val_{i}'}) for i, s in enumerate(converted_src_series_for_period)]
                            if not indexed_dfs: continue
                            
                            # Debug sum composition for strom_total
                            if master_id == "strom_total" and freq_lbl == "monthly":
                                combined_for_debug = pd.concat(indexed_dfs, axis=1)
                                logging.info(f"DEBUG STROM_TOTAL P{period_idx+1} ({freq_lbl}): Combined indexed data before sum:\n{combined_for_debug.head()}")
                            
                            current_period_composed_data = pd.concat(indexed_dfs, axis=1).sum(axis=1).fillna(0).to_frame(name='value').reset_index()
                        
                        if current_period_composed_data.empty: continue
                        
                        # Apply offset if needed
                        if apply_offset and period_idx > 0:
                            last_series_val = locals()[last_series_ref_name] # Get daily/monthly last series
                            if last_series_val is not None and not last_series_val.empty and not current_period_composed_data.empty:
                                last_val_period1 = last_series_val['value'].iloc[-1]
                                
                                # Correctly find the first value of the new period's source series AT p_start_ts
                                temp_series_for_offset_calc = current_period_composed_data.set_index('timestamp')['value']
                                # Use reindex with 'nearest' to find the value at or closest to p_start_ts
                                # Increase tolerance to 30 days to account for potential monthly data points not exactly at period start
                                nearest_value_series = temp_series_for_offset_calc.reindex([p_start_ts], method='nearest', tolerance=pd.Timedelta(days=30))
                                
                                if not nearest_value_series.empty and not pd.isna(nearest_value_series.iloc[0]):
                                    first_val_period2_pre_offset = nearest_value_series.iloc[0]
                                    actual_ts_found_for_p2_start = nearest_value_series.index[0]
                                    logging.info(f"      Found P2 start value for {master_id} at {actual_ts_found_for_p2_start} with value {first_val_period2_pre_offset:.3f} (tolerance 30 days).")
                                else:
                                    first_val_period2_pre_offset = pd.NA # Indicates value not found or NaN
                                    actual_ts_found_for_p2_start = None # Timestamp not found
                                    logging.warning(f"      Could not find valid value for {master_id} source near period start {p_start_ts} (tolerance 30 days) for offset calc. Found: {nearest_value_series.iloc[0] if not nearest_value_series.empty else 'None'}.")

                                offset_val = pd.NA # Default to NA
                                if not pd.isna(first_val_period2_pre_offset):
                                    offset_val = last_val_period1 - first_val_period2_pre_offset
                                else:
                                    logging.warning(f"      First value for P2 of {master_id} is NA/NaN around {p_start_ts}. Offset cannot be calculated reliably.")

                                if not pd.isna(offset_val):
                                    current_period_composed_data['value'] += offset_val
                                    master_meter_offsets_applied[f"{master_id}_{freq_lbl}_P{period_idx+1}"] = offset_val
                                    logging.info(f"      Applied offset {offset_val:.2f} to {master_id} ({freq_lbl}) for period starting {p_start}")
                                else:
                                    logging.warning(f"      Offset not applied for {master_id} ({freq_lbl}) for period starting {p_start} due to issues finding P2 start value or NaN result.")
                            else: logging.warning(f"      Cannot apply offset for {master_id} ({freq_lbl}), prev/current data missing for P1 end or P2 start.")

                        current_period_composed_data['timestamp'] = pd.to_datetime(current_period_composed_data['timestamp'])
                        filtered_segment = current_period_composed_data[
                            (current_period_composed_data['timestamp'] >= p_start_ts) & 
                            (current_period_composed_data['timestamp'] <= p_end_ts)
                        ].copy()
                        
                        
                        if not filtered_segment.empty:
                            period_segments_list_ref.append(filtered_segment)
                            if freq_lbl == "daily": last_processed_period_series_daily = filtered_segment
                            else: last_processed_period_series_monthly = filtered_segment
                
                # Concatenate all period segments for the master meter
                # Always build the daily series first, then derive monthly from it
                if master_period_segments_daily:
                    final_master_daily_series = pd.concat(master_period_segments_daily, ignore_index=True).sort_values('timestamp').drop_duplicates(subset=['timestamp'], keep='first').reset_index(drop=True)
                    final_readings_daily[master_id] = final_master_daily_series
                    logging.info(f"    ✅ Generated DAILY master reading series for {master_id} ({len(final_master_daily_series)} pts).")
                    
                    # FOR MASTER METERS: ALWAYS derive monthly from daily series (not from period segments)
                    # This ensures proper continuity across meter transitions
                    monthly_from_daily = self.data_processor.aggregate_daily_to_frequency(final_master_daily_series, 'M')
                    final_readings_monthly[master_id] = monthly_from_daily
                    logging.info(f"    ✅ Generated MONTHLY master reading series for {master_id} ({len(monthly_from_daily)} pts) from continuous daily series.")
                    
                else:
                    logging.warning(f"    ⚠️ No DAILY data generated for master {master_id}. MONTHLY will be empty.")
                    final_readings_daily[master_id] = pd.DataFrame(columns=['timestamp', 'value'])
                    final_readings_monthly[master_id] = pd.DataFrame(columns=['timestamp', 'value'])
                
                if master_id not in current_meter_ids: current_meter_ids.append(master_id)
        
        meters = current_meter_ids # Final list of meters with reading series

        # --- CALCULATE MONTHLY CONSUMPTION (for all meters with reading series) ---
        logging.info(f"\n CALCULATING MONTHLY CONSUMPTION (for all available reading series)...")
        monthly_consumption_data = {}
        # Ensure tmp directory exists within the current workspace
        import os
        output_dir = "tmp"
        os.makedirs(output_dir, exist_ok=True)

        for meter_name, reading_series_monthly in final_readings_monthly.items(): # Use final reading series

            logging.info(f"  Calculating monthly consumption for {meter_name}. Series range: {reading_series_monthly['timestamp'].min()} to {reading_series_monthly['timestamp'].max()}")
            
            monthly_consum_series = self.consumption_calculator.calculate_period_consumption(reading_series_monthly, freq='M')
            if not monthly_consum_series.empty:
                monthly_consumption_data[meter_name] = monthly_consum_series
                
                # Debug specific meters
                if meter_name in ["strom_total", "gas_total", "strom_1LOG0007013695_HT", "strom_1LOG0007013695_NT", "haupt_strom"]:
                    # Check December 2024 consumption
                    dec_2024_data = monthly_consum_series[monthly_consum_series['timestamp'].dt.strftime('%Y-%m') == '2024-12']
                    if not dec_2024_data.empty:
                        logging.info(f"🔍 DEBUG {meter_name}: Dec 2024 monthly consumption: {dec_2024_data['consumption'].iloc[0]:.4f}")
                    else:
                        logging.info(f"🔍 DEBUG {meter_name}: No Dec 2024 consumption data")
                    
                    # Also check Sep 2024 for comparison
                    sep_2024_data = monthly_consum_series[monthly_consum_series['timestamp'].dt.strftime('%Y-%m') == '2024-09']
                    if not sep_2024_data.empty:
                        logging.info(f"DEBUG {meter_name}: Sep 2024 monthly consumption: {sep_2024_data['consumption'].iloc[0]:.2f}")
                    else:
                        logging.info(f"DEBUG {meter_name}: No Sep 2024 consumption data")
                    
                    # Check November 2024 specifically
                    nov_2024_data = monthly_consum_series[monthly_consum_series['timestamp'].dt.strftime('%Y-%m') == '2024-11']
                    if not nov_2024_data.empty:
                        logging.info(f"🔍 DEBUG {meter_name}: Nov 2024 monthly consumption: {nov_2024_data['consumption'].iloc[0]:.4f}")
                    else:
                        logging.info(f"🔍 DEBUG {meter_name}: No Nov 2024 consumption data")
                
                # Special validation for strom_total
                if meter_name == "strom_total":
                    # Check if September 2024 strom_total consumption matches sum of individual meters
                    strom_total_sep = monthly_consum_series[monthly_consum_series['timestamp'].dt.strftime('%Y-%m') == '2024-09']
                    if not strom_total_sep.empty:
                        strom_total_val = strom_total_sep['consumption'].iloc[0]
                        
                        # Get individual meter values
                        ht_consum = monthly_consumption_data.get('strom_1LOG0007013695_HT')
                        nt_consum = monthly_consumption_data.get('strom_1LOG0007013695_NT')
                        
                        if ht_consum is not None and nt_consum is not None:
                            ht_sep = ht_consum[ht_consum['timestamp'].dt.strftime('%Y-%m') == '2024-09']
                            nt_sep = nt_consum[nt_consum['timestamp'].dt.strftime('%Y-%m') == '2024-09']
                            
                            if not ht_sep.empty and not nt_sep.empty:
                                ht_val = ht_sep['consumption'].iloc[0]
                                nt_val = nt_sep['consumption'].iloc[0]
                                individual_sum = ht_val + nt_val
                                
                                logging.info(f"🔍 VALIDATION: Sep 2024 strom_total={strom_total_val:.2f}, HT+NT={individual_sum:.2f}, diff={strom_total_val-individual_sum:.2f}")
                                
                                if abs(strom_total_val - individual_sum) > 100:  # Threshold for significant difference
                                    logging.error(f"❌ MAJOR DISCREPANCY DETECTED in Sep 2024 strom_total calculation!")
                        
                if meter_name == "strom_total":
                    logging.debug(f"DEBUG STROM_TOTAL: Full monthly consumption data:\n{monthly_consum_series}")
            else:
                logging.warning(f"  ❌ No monthly consumption for {meter_name}.")

        # --- VIRTUAL METERS PROCESSING ---
        # Process virtual meters defined in configuration
        virtual_meter_definitions = CONSTANTS.get("VIRTUAL_METER_DEFINITIONS", [])
        
        # Also handle legacy virtual meters if no definitions exist
        if not virtual_meter_definitions:
            logging.info("  No virtual meter definitions found, processing legacy virtual meters")
            self._process_legacy_virtual_meters(monthly_consumption_data, final_readings_daily, final_readings_monthly, meters, start_date_str, end_date_str)
        else:
            logging.info(f"  Processing {len(virtual_meter_definitions)} virtual meters from configuration")
            self._process_virtual_meters(virtual_meter_definitions, monthly_consumption_data, final_readings_daily, final_readings_monthly, meters, start_date_str, end_date_str)

        # Final categorization and enrichment
        current_gas_meters = [m for m in meters if 'gas' in m.lower() or m == 'eg_kalfire' or (md:=next((d for d in master_meter_definitions if d.get("master_meter_id") == m),None)) and md.get("output_unit")=="m³"]
        current_electricity_meters = [m for m in meters if 'strom' in m.lower() or m == 'strom_allgemein' or (md:=next((d for d in master_meter_definitions if d.get("master_meter_id") == m),None)) and md.get("output_unit")=="kWh"]
        current_water_meters = [m for m in meters if 'wasser' in m.lower() and 'gastherme_warmwasser' not in m.lower()]
        current_heat_meters = [m for m in meters if any(x in m.lower() for x in ['heat', 'warm']) and 'wasser' not in m.lower()]

        logging.info("  ➕ Enriching monthly consumption data with units and all equivalent forms...")
        for meter_name, mc_df in monthly_consumption_data.items():
            # Debug December 2024 before enrichment
            if meter_name in ['strom_total', 'gas_total']:
                dec_2024_before = mc_df[mc_df['timestamp'].dt.strftime('%Y-%m') == '2024-12']
                if not dec_2024_before.empty:
                    logging.info(f"🔍 ENRICHMENT {meter_name}: Dec 2024 BEFORE enrichment: {dec_2024_before['consumption'].iloc[0]:.4f}")
            if mc_df is None or mc_df.empty or 'consumption' not in mc_df.columns: continue
            df = mc_df.copy()
            md_match = next((md for md in master_meter_definitions if md.get("master_meter_id") == meter_name), None)
            
            # Determine primary unit based on master def or inference for virtual/physical
            if md_match: primary_unit = md_match.get("output_unit")
            elif meter_name == 'eg_kalfire': primary_unit = 'm³'
            elif meter_name == 'strom_allgemein': primary_unit = 'kWh'
            elif 'strom' in meter_name.lower(): primary_unit = 'kWh'
            elif 'gastherme_gesamt' == meter_name : primary_unit = 'kWh' # Special case, gas but reports kWh
            elif 'gas' in meter_name.lower() or 'wasser' in meter_name.lower(): primary_unit = 'm³'
            else: primary_unit = 'unknown'
            df['unit'] = primary_unit
            
            is_gas_related = 'gas' in meter_name.lower() or meter_name == 'eg_kalfire' or (md_match and 'gas' in md_match.get("master_meter_id","").lower())

            if primary_unit == 'm³':
                df['consumption_m3'] = df['consumption']
                if is_gas_related: df['consumption_kwh'] = df['consumption_m3'] * self.gas_conversion_factor
            elif primary_unit == 'kWh':
                df['consumption_kwh'] = df['consumption']
                if is_gas_related: df['consumption_m3_equivalent'] = df['consumption_kwh'] / self.gas_conversion_factor if self.gas_conversion_factor > 0 else 0.0
            monthly_consumption_data[meter_name] = df
            
            # Debug December 2024 after enrichment
            if meter_name in ['strom_total', 'gas_total']:
                dec_2024_after = df[df['timestamp'].dt.strftime('%Y-%m') == '2024-12']
                if not dec_2024_after.empty:
                    consumption_col = 'consumption_kwh' if 'consumption_kwh' in df.columns else 'consumption_m3' if 'consumption_m3' in df.columns else 'consumption'
                    logging.info(f"🔍 ENRICHMENT {meter_name}: Dec 2024 AFTER enrichment ({consumption_col}): {dec_2024_after[consumption_col].iloc[0]:.4f}")
        
        logging.info(f"\n📊 CALCULATING ANNUAL CONSUMPTION...")
        results = {}
        # Calculate for all years from start_year to current year
        current_year = datetime.now().year
        years = list(range(start_year, current_year + 1))
        
        for year_val in years:
            results[year_val] = {}
            logging.info(f"\n📅 Year {year_val}:")
            for meter_name in meters: 
                res_entry = {}
                annual_consum_val = 0.0
                # Annual consumption is derived from the daily *reading* series if available
                if meter_name in final_readings_daily and not final_readings_daily[meter_name].empty:
                    annual_consum_val = self.consumption_calculator.calculate_annual_consumption_from_series(final_readings_daily[meter_name], year=year_val)
                    # Unit and conversions based on enriched monthly data
                    if meter_name in monthly_consumption_data and not monthly_consumption_data[meter_name].empty:
                        mc_info = monthly_consumption_data[meter_name]
                        res_entry['unit'] = mc_info['unit'].iloc[0]
                        if 'consumption_m3' in mc_info.columns and res_entry['unit'] == 'm³': res_entry['consumption_m3'] = annual_consum_val
                        if 'consumption_kwh' in mc_info.columns: 
                            res_entry['consumption_kwh'] = mc_info[mc_info['timestamp'].dt.year == year_val]['consumption_kwh'].sum() if res_entry['unit'] == 'm³' else annual_consum_val
                        if 'consumption_m3_equivalent' in mc_info.columns:
                             res_entry['consumption_m3_equivalent'] = mc_info[mc_info['timestamp'].dt.year == year_val]['consumption_m3_equivalent'].sum() if res_entry['unit'] == 'kWh' else annual_consum_val

                    else: # Fallback if no monthly consumption data (should not happen for meters with readings)
                        res_entry['unit'] = "unknown_unit_annual"
                        res_entry[f'consumption_{res_entry["unit"]}'] = annual_consum_val
                elif meter_name in monthly_consumption_data: # For meters only in monthly_consumption (e.g. masters if not generating readings)
                    mc_df_annual = monthly_consumption_data[meter_name]
                    annual_consum_val = mc_df_annual[mc_df_annual['timestamp'].dt.year == year_val]['consumption'].sum()
                    res_entry['unit'] = mc_df_annual['unit'].iloc[0] if not mc_df_annual.empty else "unknown"
                    if res_entry['unit'] == 'm³': res_entry['consumption_m3'] = annual_consum_val
                    if 'consumption_kwh' in mc_df_annual.columns: res_entry['consumption_kwh'] = mc_df_annual[mc_df_annual['timestamp'].dt.year == year_val]['consumption_kwh'].sum()
                    if res_entry['unit'] == 'kWh': res_entry['consumption_kwh'] = annual_consum_val
                    if 'consumption_m3_equivalent' in mc_df_annual.columns: res_entry['consumption_m3_equivalent'] = mc_df_annual[mc_df_annual['timestamp'].dt.year == year_val]['consumption_m3_equivalent'].sum()

                else:
                    logging.warning(f"No data for annual calculation of {meter_name}. Skipping."); continue
                
                is_master_annual = any(md.get("master_meter_id") == meter_name for md in master_meter_definitions)
                virtual_meter_definitions = CONSTANTS.get("VIRTUAL_METER_DEFINITIONS", [])
                is_virtual_annual = any(vd.get("meter_id") == meter_name for vd in virtual_meter_definitions) or meter_name in ['eg_kalfire', 'strom_allgemein']  # Include legacy virtual meters
                res_entry['unit'] += " (master)" if is_master_annual else (" (virtual)" if is_virtual_annual else "")
                
                logging.info(f"  Meter {meter_name}: {annual_consum_val:.2f} {res_entry['unit']}")
                results[year_val][meter_name] = res_entry
        
        results_dict = {
            'available_meters': {'all': meters, 'water': current_water_meters, 'electricity': current_electricity_meters, 'gas': current_gas_meters, 'heat': current_heat_meters},
            'raw_data': self.influx_client.meter_data_cache, 
            'interpolated_data': final_readings_daily, 
            'monthly_consumption_data': monthly_consumption_data, 
            'annual_consumption': results,
            'meter_offsets': master_meter_offsets_applied # Offsets applied during master meter creation
        }
        raw_interpolated_charts = self.reporter.generate_raw_and_interpolated_charts(results_dict)
        consumption_charts = self.reporter.generate_consumption_charts(results_dict)
        results_dict['raw_interpolated_charts'] = raw_interpolated_charts
        results_dict['consumption_charts'] = consumption_charts
        logging.info(f"📊 Generated {len(raw_interpolated_charts)} charts and {len(consumption_charts)} consumption charts.")
        return results_dict

    def run_analysis(self, start_year: int = 2021):
        logging.info("🏠 UTILITY CONSUMPTION ANALYZER")
        try:
            results = self.analyze_all_meters(start_year)
            self.reporter.generate_summary_report(results) 
            logging.info(f"\n✅ Analysis completed successfully!")
        except Exception as e:
            logging.error(f"❌ Error during analysis: {e}\n{traceback.format_exc()}")

def main():
    analyzer = UtilityAnalyzer()
    analyzer.run_analysis()

if __name__ == "__main__":
    main()