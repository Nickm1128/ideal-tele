"""
Helper functions for working with different charge type combinations in the bill calculator.
"""

import pandas as pd
import json

def get_charge_types_info():
    """Return information about available charge type combinations."""
    return {
        'transmission_delivery': {
            'types': [0, 2],
            'description': 'Transmission + Delivery charges',
            'includes': ['System transmission charges', 'Delivery infrastructure charges', 'Regulatory adjustments']
        },
        'transmission_supply': {
            'types': [0, 1], 
            'description': 'Transmission + Supply charges',
            'includes': ['System transmission charges', 'Generation/supply charges', 'Environmental compliance']
        },
        'transmission_only': {
            'types': [0],
            'description': 'Transmission charges only',
            'includes': ['System transmission charges only']
        },
        'supply_only': {
            'types': [1],
            'description': 'Supply charges only', 
            'includes': ['Generation/supply charges', 'Environmental compliance']
        },
        'delivery_only': {
            'types': [2],
            'description': 'Delivery charges only',
            'includes': ['Delivery infrastructure charges', 'Regulatory adjustments']
        }
    }

def filter_charges_by_type(charges_df, charge_types):
    """Filter charge configuration DataFrame by service type IDs."""
    return charges_df[charges_df['ServiceTypeId'].isin(charge_types)]

def compare_charge_combinations(charges_df):
    """Compare the two main charge combinations: [0,1] vs [0,2]."""
    
    combinations = {
        'transmission_supply': [0, 1],
        'transmission_delivery': [0, 2]
    }
    
    comparison = {}
    
    for name, types in combinations.items():
        filtered = filter_charges_by_type(charges_df, types)
        
        comparison[name] = {
            'types': types,
            'total_charges': len(filtered),
            'kwh_charges': len(filtered[filtered['Unit'] == 'kWh']),
            'kw_charges': len(filtered[filtered['Unit'] == 'kW']),
            'monthly_charges': len(filtered[filtered['Unit'] == 'per month']),
            'charge_descriptions': filtered['Description'].tolist()
        }
    
    return comparison

def print_charge_comparison():
    """Print a detailed comparison of charge combinations."""
    
    try:
        charges_df = pd.read_csv('../charge_config.csv')
    except Exception as e:
        print(f"Error loading charge config: {e}")
        return
    
    comparison = compare_charge_combinations(charges_df)
    
    print("=== CHARGE COMBINATION COMPARISON ===\n")
    
    for name, data in comparison.items():
        print(f"{name.replace('_', ' ').title()} {data['types']}:")
        print(f"  Total charges: {data['total_charges']}")
        print(f"  kWh charges: {data['kwh_charges']}")
        print(f"  kW charges: {data['kw_charges']}")
        print(f"  Monthly charges: {data['monthly_charges']}")
        print()
    
    # Show unique charges in each combination
    ts_charges = set(comparison['transmission_supply']['charge_descriptions'])
    td_charges = set(comparison['transmission_delivery']['charge_descriptions'])
    
    print("Charges unique to Transmission + Supply [0,1]:")
    unique_to_ts = ts_charges - td_charges
    for charge in sorted(unique_to_ts):
        print(f"  - {charge}")
    
    print(f"\nCharges unique to Transmission + Delivery [0,2]:")
    unique_to_td = td_charges - ts_charges
    for charge in sorted(list(unique_to_td)[:10]):  # Show first 10
        print(f"  - {charge}")
    if len(unique_to_td) > 10:
        print(f"  ... and {len(unique_to_td) - 10} more")

def create_bill_calculator_wrapper():
    """Create a wrapper function that makes it easy to calculate bills with different charge types."""
    
    wrapper_code = '''
def calculate_bill_with_charge_types(
    billing_df, usage_kwh, start_date, end_date, 
    contract_demand_kW=0.0, charge_combination='transmission_delivery'
):
    """
    Calculate electric bill with specified charge type combination.
    
    Parameters:
    - billing_df: DataFrame with demand data
    - usage_kwh: Total energy usage
    - start_date, end_date: Billing period
    - contract_demand_kW: Contract demand
    - charge_combination: One of:
        - 'transmission_delivery' (types [0,2]) - Default
        - 'transmission_supply' (types [0,1])
        - 'transmission_only' (types [0])
        - 'supply_only' (types [1])
        - 'delivery_only' (types [2])
    
    Returns:
    - Dictionary with bill breakdown and total
    """
    
    # Load data
    charges_df = pd.read_csv('../charge_config.csv')
    with open('../charge_history.json', 'r') as f:
        rates = json.load(f)
    
    # Get charge types for the specified combination
    charge_info = get_charge_types_info()
    if charge_combination not in charge_info:
        raise ValueError(f"Invalid combination. Choose from: {list(charge_info.keys())}")
    
    charge_types = charge_info[charge_combination]['types']
    
    # Filter charges
    filtered_charges = filter_charges_by_type(charges_df, charge_types)
    
    # Extract rate data
    rate_data = extract_rate_data(
        rates, filtered_charges, start_date, end_date, 
        charge_types=charge_types
    )
    
    # Calculate bill
    bill = calculate_bill(
        billing_df, usage_kwh, start_date, end_date,
        rate_data, contract_demand_kW, charge_types
    )
    
    # Add metadata
    bill['charge_combination'] = charge_combination
    bill['charge_types'] = charge_types
    bill['rate_data'] = rate_data
    
    return bill
'''
    
    return wrapper_code

if __name__ == "__main__":
    print_charge_comparison()
    
    print("\n" + "="*60)
    print("CHARGE TYPE INFORMATION:")
    print("="*60)
    
    info = get_charge_types_info()
    for name, details in info.items():
        print(f"\n{name.replace('_', ' ').title()}:")
        print(f"  Types: {details['types']}")
        print(f"  Description: {details['description']}")
        print(f"  Includes: {', '.join(details['includes'])}")