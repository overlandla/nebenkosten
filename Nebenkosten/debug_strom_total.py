#!/usr/bin/env python3
"""
Debug script to investigate strom_total calculation issues in September 2024
"""
import logging
import sys
from src.main_app import UtilityAnalyzer

# Set up detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def main():
    print("🔍 DEBUGGING STROM_TOTAL CALCULATION")
    print("=" * 50)
    
    # Create analyzer
    analyzer = UtilityAnalyzer()
    
    # Run analysis for full period to focus on the issue
    print("\n🏃 Running analysis for full period...")
    results = analyzer.analyze_all_meters(start_year=2021)
    
    # Extract monthly consumption data
    monthly_data = results.get('monthly_consumption_data', {})
    
    print("\n📊 SEPTEMBER 2024 CONSUMPTION COMPARISON:")
    print("-" * 45)
    
    meters_to_check = ['strom_total', 'strom_1LOG0007013695_HT', 'strom_1LOG0007013695_NT', 'haupt_strom']
    
    for meter_name in meters_to_check:
        if meter_name in monthly_data:
            df = monthly_data[meter_name]
            sep_data = df[df['timestamp'].dt.strftime('%Y-%m') == '2024-09']
            if not sep_data.empty:
                consumption = sep_data['consumption'].iloc[0]
                print(f"{meter_name:25}: {consumption:8.2f} kWh")
            else:
                print(f"{meter_name:25}: No data")
        else:
            print(f"{meter_name:25}: Not found")
    
    # Check if individual meters sum correctly
    ht_sep = monthly_data.get('strom_1LOG0007013695_HT')
    nt_sep = monthly_data.get('strom_1LOG0007013695_NT')
    total_sep = monthly_data.get('strom_total')
    
    if ht_sep is not None and nt_sep is not None and total_sep is not None:
        ht_sep_data = ht_sep[ht_sep['timestamp'].dt.strftime('%Y-%m') == '2024-09']
        nt_sep_data = nt_sep[nt_sep['timestamp'].dt.strftime('%Y-%m') == '2024-09']
        total_sep_data = total_sep[total_sep['timestamp'].dt.strftime('%Y-%m') == '2024-09']
        
        if not ht_sep_data.empty and not nt_sep_data.empty and not total_sep_data.empty:
            ht_val = ht_sep_data['consumption'].iloc[0]
            nt_val = nt_sep_data['consumption'].iloc[0]
            total_val = total_sep_data['consumption'].iloc[0]
            calculated_sum = ht_val + nt_val
            
            print(f"\n🧮 CALCULATION CHECK:")
            print(f"HT + NT = {ht_val:.2f} + {nt_val:.2f} = {calculated_sum:.2f}")
            print(f"Actual total: {total_val:.2f}")
            print(f"Difference: {total_val - calculated_sum:.2f}")
            
            if abs(total_val - calculated_sum) > 1.0:  # Threshold for significant difference
                print("❌ SIGNIFICANT DISCREPANCY DETECTED!")
            else:
                print("✅ Values match within tolerance")

if __name__ == "__main__":
    main()