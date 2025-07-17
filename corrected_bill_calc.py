"""
Corrected bill calculation that addresses the identified issues.
"""

import pandas as pd
import json

# Copy the corrected functions
def calculate_bill_corrected(
    billing_df: pd.DataFrame,
    usage_kwh: float,
    start_date,
    end_date,
    rate_data: dict,
    contract_demand_kW: float = 0.0,
    charge_types: list = [0, 2],
):
    """Calculate a corrected electric delivery bill."""
    
    # --- Date Handling ---
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    billing_days = (end_date - start_date).days

    # --- Seasonal Masks ---
    billing_df['Month'] = billing_df['Date'].dt.month
    summer_mask = billing_df['Month'].isin([6, 7, 8, 9])  # June through Sept

    # --- Contract Demand Charge (CORRECTED: Already prorated in rate extraction) ---
    contract_demand_rate = rate_data.get('contract_demand_rate', 0.0)
    contract_demand_charge = contract_demand_kW * contract_demand_rate

    # --- Summer As-Used Demand ---
    summer_df = billing_df[summer_mask]
    midpeak_kW_summer = summer_df['MidPeakDemand_kW'].fillna(0).sum()
    peak_kW_summer = summer_df['PeakDemand_kW'].fillna(0).sum()

    midpeak_rate = rate_data.get('midpeak_rate_summer', 0.0)
    peak_rate = rate_data.get('peak_rate_summer', 0.0)
    demand_charge_summer = (
        midpeak_kW_summer * midpeak_rate +
        peak_kW_summer * peak_rate
    )

    # --- Non-Summer As-Used Demand (CORRECTED: Use max per day, not sum) ---
    nonsummer_df = billing_df[~summer_mask][['MidPeakDemand_kW', 'PeakDemand_kW']].fillna(0)
    # Use highest daily kW of either midpeak or peak per day, then sum those daily maxes
    nonsummer_daily_max = nonsummer_df.max(axis=1).sum()

    as_used_rate_nonsummer = rate_data.get('as_used_rate_nonsummer', 0.0)
    demand_charge_nonsummer = nonsummer_daily_max * as_used_rate_nonsummer

    # --- Energy-Based Surcharge ---
    surcharge_rate = rate_data.get('surcharge_rate', 0.0)
    surcharge_charge = usage_kwh * surcharge_rate
    kwh_breakdown = rate_data.get('kwh_charge_breakdown', {})
    energy_breakdown = {
        k: {
            'rate_per_kWh': v,
            'charge': round(v * usage_kwh, 10)
        } for k, v in kwh_breakdown.items()
    }

    # --- Fixed Monthly Charges (CORRECTED: Customer charge already prorated) ---
    customer_charge = rate_data.get('customer_charge', 0.0)
    processing_charge = rate_data.get('processing_charge', 0.0)
    fixed_charges = customer_charge + processing_charge

    # --- Total Delivery Bill ---
    total = (
        fixed_charges +
        contract_demand_charge +
        demand_charge_summer +
        demand_charge_nonsummer +
        surcharge_charge
    )

    # --- Return Detailed Breakdown ---
    return {
        'customer_charge': {
            'amount': round(customer_charge, 2),
            'description': 'Fixed monthly customer service charge'
        },
        'processing_charge': {
            'amount': round(processing_charge, 2),
            'description': 'Billing & payment processing fee'
        },
        'energy_surcharge': {
                'amount': round(surcharge_charge, 2),
                'rate_per_kWh': round(surcharge_rate, 10),
                'usage_kWh': usage_kwh,
                'breakdown': energy_breakdown,
                'description': 'Total of all $/kWh delivery surcharges'
            },
        'demand_charge_summer': {
            'amount': round(demand_charge_summer, 2),
            'midpeak_kWh_sum': round(midpeak_kW_summer, 2),
            'midpeak_rate': midpeak_rate,
            'peak_kWh_sum': round(peak_kW_summer, 2),
            'peak_rate': peak_rate,
            'description': 'Sum of midpeak and peak weekday demand (Summer)'
        },
        'demand_charge_nonsummer': {
            'amount': round(demand_charge_nonsummer, 2),
            'sum_daily_max_kW': round(nonsummer_daily_max, 2),
            'rate': as_used_rate_nonsummer,
            'description': 'Sum of daily weekday max(kW) for Non-Summer',
            'billing_days': len(nonsummer_df),
            'avg_daily_max': round(nonsummer_daily_max / len(nonsummer_df) if len(nonsummer_df) > 0 else 0, 2)
        },
        'contract_demand_charge': {
            'amount': round(contract_demand_charge, 2),
            'kW': contract_demand_kW,
            'rate': contract_demand_rate,
            'description': 'Fixed monthly rate based on contracted demand',
            'billing_days': billing_days
        },
        'total': round(total, 2),
        'billing_days': billing_days
    }

def create_realistic_demand_data():
    """Create more realistic demand data based on the 382 kW sample."""
    dates = pd.date_range('2025-04-16', '2025-05-15', freq='D')
    
    # Create more realistic demand data
    # April 2025 is non-summer, so we expect lower, more consistent demand
    # Base demand around 382 kW with some daily variation
    billing_df = pd.DataFrame({
        'Date': dates,
        # Midpeak demand: varies between 320-380 kW
        'MidPeakDemand_kW': [320 + (i % 10) * 6 + (i % 3) * 4 for i in range(len(dates))],
        # Peak demand: slightly higher, varies between 350-400 kW  
        'PeakDemand_kW': [350 + (i % 8) * 6 + (i % 4) * 3 for i in range(len(dates))]
    })
    
    return billing_df

def test_corrected_calculation():
    """Test the corrected bill calculation."""
    
    # Load data
    charges_df = pd.read_csv('charge_config.csv')
    with open('charge_history.json', 'r') as f:
        rates = json.load(f)
    
    # Create more realistic demand data
    billing_df = create_realistic_demand_data()
    
    print("=== CORRECTED BILL CALCULATION ===")
    print()
    print("Demand data summary:")
    print(f"Date range: {billing_df['Date'].min().date()} to {billing_df['Date'].max().date()}")
    print(f"Days: {len(billing_df)}")
    print(f"Midpeak demand range: {billing_df['MidPeakDemand_kW'].min():.1f} - {billing_df['MidPeakDemand_kW'].max():.1f} kW")
    print(f"Peak demand range: {billing_df['PeakDemand_kW'].min():.1f} - {billing_df['PeakDemand_kW'].max():.1f} kW")
    print(f"Average daily max: {billing_df[['MidPeakDemand_kW', 'PeakDemand_kW']].max(axis=1).mean():.1f} kW")
    print()
    
    # Sample parameters
    usage_kwh = 128627
    start_date = '2025-04-16'
    end_date = '2025-05-15'
    contract_demand_kW = 382
    charge_types = [0, 2]
    
    # Import the rate extraction function from our test file
    from test_bill_calculation import extract_rate_data
    
    # Extract rate data
    rate_data = extract_rate_data(
        rates, charges_df, start_date, end_date, 
        charge_types=charge_types
    )
    
    print("Rate data:")
    print(f"Contract demand rate: ${rate_data['contract_demand_rate']:.6f}/kW")
    print(f"Non-summer as-used rate: ${rate_data['as_used_rate_nonsummer']:.6f}/kW")
    print(f"Total surcharge rate: ${rate_data['surcharge_rate']:.6f}/kWh")
    print(f"Customer charge: ${rate_data['customer_charge']:.2f}")
    print()
    
    # Calculate bill with corrected function
    bill = calculate_bill_corrected(
        billing_df, usage_kwh, start_date, end_date, 
        rate_data, contract_demand_kW, charge_types
    )
    
    print("=== CORRECTED BILL BREAKDOWN ===")
    print(f"Customer Charge: ${bill['customer_charge']['amount']:,.2f}")
    print(f"Processing Charge: ${bill['processing_charge']['amount']:,.2f}")
    print(f"Contract Demand Charge: ${bill['contract_demand_charge']['amount']:,.2f}")
    print(f"  - {contract_demand_kW} kW × ${rate_data['contract_demand_rate']:.6f}/kW")
    print(f"  - Billing days: {bill['billing_days']}")
    print(f"Summer Demand Charge: ${bill['demand_charge_summer']['amount']:,.2f}")
    print(f"Non-Summer Demand Charge: ${bill['demand_charge_nonsummer']['amount']:,.2f}")
    print(f"  - Sum of daily max kW: {bill['demand_charge_nonsummer']['sum_daily_max_kW']:.2f}")
    print(f"  - Average daily max: {bill['demand_charge_nonsummer']['avg_daily_max']:.2f} kW")
    print(f"  - Billing days: {bill['demand_charge_nonsummer']['billing_days']}")
    print(f"Energy Surcharge: ${bill['energy_surcharge']['amount']:,.2f}")
    print()
    print(f"TOTAL CALCULATED: ${bill['total']:,.2f}")
    print(f"EXPECTED FROM SAMPLE: $17,230.93")
    print(f"DIFFERENCE: ${bill['total'] - 17230.93:,.2f}")
    print(f"Accuracy: {(1 - abs(bill['total'] - 17230.93) / 17230.93) * 100:.1f}%")
    
    return bill

if __name__ == "__main__":
    try:
        bill = test_corrected_calculation()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()