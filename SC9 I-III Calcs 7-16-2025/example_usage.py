"""
Example usage of the updated bill calculator with different charge type combinations.

This demonstrates how to calculate bills using:
- Charge types [0, 2]: Transmission + Delivery charges (current default)
- Charge types [0, 1]: Transmission + Supply charges
"""

import pandas as pd
import json
from bill_calc import calculate_bill, extract_rate_data

def load_sample_data():
    """Load the charge configuration and history data from CSV and JSON files."""
    # Load charge configuration
    charges_df = pd.read_csv('../charge_config.csv')
    
    # Load charge history
    with open('../charge_history.json', 'r') as f:
        rates = json.load(f)
    
    return charges_df, rates

def create_sample_billing_data():
    """Create sample billing data for demonstration."""
    # Sample demand data for a billing period
    dates = pd.date_range('2025-04-16', '2025-05-15', freq='D')
    
    # Create sample demand data (you would replace this with actual meter data)
    billing_df = pd.DataFrame({
        'Date': dates,
        'MidPeakDemand_kW': [300 + i*2 for i in range(len(dates))],  # Sample midpeak demand
        'PeakDemand_kW': [350 + i*2.5 for i in range(len(dates))]    # Sample peak demand
    })
    
    return billing_df

def calculate_bill_comparison():
    """Compare bills calculated with different charge type combinations."""
    
    # Load data
    charges_df, rates = load_sample_data()
    billing_df = create_sample_billing_data()
    
    # Sample parameters (matching the example in Sample calculation.txt)
    usage_kwh = 128627  # From sample calculation
    start_date = '2025-04-16'
    end_date = '2025-05-15'
    contract_demand_kW = 382  # From sample calculation
    
    print("=== ELECTRIC BILL CALCULATION COMPARISON ===\n")
    print(f"Billing Period: {start_date} to {end_date}")
    print(f"Usage: {usage_kwh:,} kWh")
    print(f"Contract Demand: {contract_demand_kW} kW")
    print("="*60)
    
    # Scenario 1: Transmission + Delivery charges (types 0 + 2)
    print("\n1. TRANSMISSION + DELIVERY CHARGES (Types 0 + 2)")
    print("-" * 50)
    
    rate_data_02 = extract_rate_data(
        rates, charges_df, start_date, end_date, 
        charge_types=[0, 2]
    )
    
    bill_02 = calculate_bill(
        billing_df, usage_kwh, start_date, end_date, 
        rate_data_02, contract_demand_kW, charge_types=[0, 2]
    )
    
    print_bill_summary(bill_02, rate_data_02)
    
    # Scenario 2: Transmission + Supply charges (types 0 + 1)
    print("\n2. TRANSMISSION + SUPPLY CHARGES (Types 0 + 1)")
    print("-" * 50)
    
    rate_data_01 = extract_rate_data(
        rates, charges_df, start_date, end_date, 
        charge_types=[0, 1]
    )
    
    bill_01 = calculate_bill(
        billing_df, usage_kwh, start_date, end_date, 
        rate_data_01, contract_demand_kW, charge_types=[0, 1]
    )
    
    print_bill_summary(bill_01, rate_data_01)
    
    # Comparison
    print("\n3. COMPARISON")
    print("-" * 50)
    print(f"Types 0+2 Total: ${bill_02['total']:,.2f}")
    print(f"Types 0+1 Total: ${bill_01['total']:,.2f}")
    print(f"Difference: ${bill_02['total'] - bill_01['total']:,.2f}")
    
    return bill_02, bill_01

def print_bill_summary(bill, rate_data):
    """Print a formatted bill summary."""
    print(f"Customer Charge: ${bill['customer_charge']['amount']:,.2f}")
    print(f"Processing Charge: ${bill['processing_charge']['amount']:,.2f}")
    print(f"Contract Demand Charge: ${bill['contract_demand_charge']['amount']:,.2f}")
    print(f"Summer Demand Charge: ${bill['demand_charge_summer']['amount']:,.2f}")
    print(f"Non-Summer Demand Charge: ${bill['demand_charge_nonsummer']['amount']:,.2f}")
    print(f"Energy Surcharge: ${bill['energy_surcharge']['amount']:,.2f}")
    print(f"  - Surcharge Rate: ${rate_data['surcharge_rate']:.6f}/kWh")
    print(f"TOTAL BILL: ${bill['total']:,.2f}")
    
    # Show breakdown of energy charges
    if rate_data['kwh_charge_breakdown']:
        print("\nEnergy Charge Breakdown:")
        for desc, rate in rate_data['kwh_charge_breakdown'].items():
            if rate != 0:
                print(f"  - {desc.replace('_', ' ').title()}: ${rate:.6f}/kWh")

def analyze_charge_types():
    """Analyze what charges are included in each type."""
    charges_df = pd.read_csv('../charge_config.csv')
    
    print("\n=== CHARGE TYPE ANALYSIS ===")
    
    for charge_type in [0, 1, 2]:
        print(f"\nCharge Type {charge_type}:")
        type_charges = charges_df[charges_df['ServiceTypeId'] == charge_type]
        
        if not type_charges.empty:
            for _, row in type_charges.iterrows():
                print(f"  - {row['Description']} ({row['Unit']})")
        else:
            print("  - No charges found")

if __name__ == "__main__":
    try:
        # Run the comparison
        bill_02, bill_01 = calculate_bill_comparison()
        
        # Show charge type analysis
        analyze_charge_types()
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure the charge_config.csv and charge_history.json files are in the parent directory.")