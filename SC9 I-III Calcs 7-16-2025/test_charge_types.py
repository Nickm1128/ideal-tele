"""
Simple test script to verify the charge type functionality works with existing data.
"""

import pandas as pd
import json

def test_charge_types():
    """Test the charge type filtering functionality."""
    
    print("=== ANALYZING CHARGE CONFIGURATION DATA ===\n")
    
    # Load data
    try:
        charges_df = pd.read_csv('../charge_config.csv')
        print("✓ Charge configuration loaded successfully")
        print(f"Total charges in config: {len(charges_df)}\n")
    except Exception as e:
        print(f"✗ Error loading data: {e}")
        return
    
    # Show charge distribution by service type
    print("CHARGE DISTRIBUTION BY SERVICE TYPE:")
    print("=" * 50)
    
    for service_type in sorted(charges_df['ServiceTypeId'].unique()):
        type_charges = charges_df[charges_df['ServiceTypeId'] == service_type]
        count = len(type_charges)
        
        print(f"\nService Type {service_type}: {count} charges")
        print("-" * 30)
        
        # Group by unit type
        unit_counts = type_charges['Unit'].value_counts()
        for unit, unit_count in unit_counts.items():
            print(f"  {unit}: {unit_count} charges")
        
        # Show some examples
        print("  Examples:")
        examples = type_charges['Description'].head(5)
        for desc in examples:
            print(f"    - {desc}")
        if len(type_charges) > 5:
            print(f"    ... and {len(type_charges) - 5} more")
    
    # Test different charge type combinations
    print(f"\n\nCHARGE TYPE COMBINATION ANALYSIS:")
    print("=" * 50)
    
    test_cases = [
        ([0, 2], "Transmission + Delivery (Current Default)"),
        ([0, 1], "Transmission + Supply"),
        ([0], "Transmission Only"),
        ([1], "Supply Only"), 
        ([2], "Delivery Only")
    ]
    
    for charge_types, description in test_cases:
        print(f"\n{description} (Types {charge_types}):")
        print("-" * 40)
        
        # Filter charges for this combination
        filtered_charges = charges_df[charges_df['ServiceTypeId'].isin(charge_types)]
        
        print(f"Total charges: {len(filtered_charges)}")
        
        # Break down by unit type
        if not filtered_charges.empty:
            unit_breakdown = filtered_charges['Unit'].value_counts()
            for unit, count in unit_breakdown.items():
                print(f"  {unit} charges: {count}")
        else:
            print("  No charges found")
    
    # Show the key difference between combinations
    print(f"\n\nKEY DIFFERENCES:")
    print("=" * 50)
    
    # Compare 0+1 vs 0+2
    charges_01 = charges_df[charges_df['ServiceTypeId'].isin([0, 1])]
    charges_02 = charges_df[charges_df['ServiceTypeId'].isin([0, 2])]
    
    print("Charges in [0,1] but NOT in [0,2]:")
    only_in_01 = charges_01[~charges_01['Description'].isin(charges_02['Description'])]
    for desc in only_in_01['Description'].head(10):
        print(f"  - {desc}")
    
    print(f"\nCharges in [0,2] but NOT in [0,1]:")
    only_in_02 = charges_02[~charges_02['Description'].isin(charges_01['Description'])]
    for desc in only_in_02['Description'].head(10):
        print(f"  - {desc}")
    
    print(f"\nSummary:")
    print(f"  - Types [0,1]: {len(charges_01)} total charges")
    print(f"  - Types [0,2]: {len(charges_02)} total charges") 
    print(f"  - Unique to [0,1]: {len(only_in_01)} charges")
    print(f"  - Unique to [0,2]: {len(only_in_02)} charges")

if __name__ == "__main__":
    test_charge_types()