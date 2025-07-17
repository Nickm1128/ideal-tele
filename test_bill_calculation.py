"""
Test script to verify bill calculation with sample data using charges 0 and 2.
"""

import pandas as pd
import json
import sys
import os
import ast
from datetime import datetime

# Add the SC9 directory to path
sys.path.append('SC9 I-III Calcs 7-16-2025')

# Copy the necessary functions from bill_calc.py to avoid import issues
def calculate_bill(
    billing_df: pd.DataFrame,
    usage_kwh: float,
    start_date,
    end_date,
    rate_data: dict,
    contract_demand_kW: float = 0.0,
    charge_types: list = [0, 2],
):
    """Calculate a detailed electric delivery bill based on as-used demand and energy usage."""
    
    # --- Date Handling ---
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    # --- Seasonal Masks ---
    billing_df['Month'] = billing_df['Date'].dt.month
    summer_mask = billing_df['Month'].isin([6, 7, 8, 9])  # June through Sept

    # --- Contract Demand Charge ---
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

    # --- Non-Summer As-Used Demand ---
    nonsummer_df = billing_df[~summer_mask][['MidPeakDemand_kW', 'PeakDemand_kW']].fillna(0)
    # Use highest daily kW of either midpeak or peak per day
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

    # --- Fixed Monthly Charges ---
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
            'description': 'Sum of daily weekday max(kW) for Non-Summer'
        },
        'contract_demand_charge': {
            'amount': round(contract_demand_charge, 2),
            'kW': contract_demand_kW,
            'rate': contract_demand_rate,
            'description': 'Fixed monthly rate based on contracted demand'
        },
        'total': round(total, 2)
    }

def extract_rate_data(rates, charges_df, start_date, end_date, city="New York City", charge_types=[0, 2]):
    if isinstance(start_date, str): start_date = pd.to_datetime(start_date)
    if isinstance(end_date, str): end_date = pd.to_datetime(end_date)
    billing_days = (end_date - start_date).days

    def get_effective_rate(entries, field, date_col='EffectiveDate'):
        df = pd.DataFrame(entries)
        df[date_col] = pd.to_datetime(df[date_col])
        df = df[df[date_col] <= end_date]
        if df.empty:
            return 0.0
        return float(df.sort_values(date_col).iloc[-1][field])

    def extract_summer_demand_rate(entries, start_time, end_time):
        df = pd.DataFrame(entries)
        df['EffectiveDate'] = pd.to_datetime(df['EffectiveDate'])
        df = df[
            (df['StartTime'] == start_time) &
            (df['EndTime'] == end_time) &
            (df['Season'].str.strip().str.lower() == 'june-sept') &
            (df['EffectiveDate'] <= end_date)
        ]
        if df.empty:
            return 0.0
        return float(df.sort_values('EffectiveDate').iloc[-1]['RatekW'])

    def get_weighted_average(entries, field):
        df = pd.DataFrame(entries)
        df['EffectiveDate'] = pd.to_datetime(df['EffectiveDate'])
        df = df[df['EffectiveDate'] <= end_date]
        df = df.sort_values('EffectiveDate')
        if df.empty:
            return 0.0

        weights, rates = [], []
        for i, row in df.iterrows():
            eff_date = max(row['EffectiveDate'], start_date)
            if i + 1 < len(df):
                next_date = min(end_date, df.iloc[i + 1]['EffectiveDate'])
            else:
                next_date = end_date
            days = (next_date - eff_date).days
            if days < 0:
                continue
            weights.append(days)
            rates.append(float(row[field]))

        total_days = sum(weights)
        return sum(w * r for w, r in zip(weights, rates)) / total_days if total_days > 0 else 0.0

    def extract(table_key, field_name, desc_match, charge_meta):
        entries = [e for e in rates.get(table_key, []) if desc_match.lower() in e['Description'].lower()]

        if not entries:
            return 0.0

        if charge_meta.get('Weighted', False):
            rate = get_weighted_average(entries, field_name)
        else:
            rate = get_effective_rate(entries, field_name)

        if charge_meta.get('Prorated', False):
            rate *= billing_days / 30

        return rate

    rate_data = {}
    kwh_charges = {}

    for _, row in charges_df.iterrows():
        desc = row['Description']
        key = desc.lower().strip().replace(" ", "_").replace("-", "").replace("/", "").replace(":", "")

        if row['Unit'] == 'kWh' and row['ServiceTypeId'] in charge_types:
            rate = extract('Energy_Table', 'RatekWh', desc, row)
            kwh_charges[key] = round(rate, 10)

        elif row['Unit'] == 'kW':
            rate = extract('Demand_Table', 'RatekW', desc, row)

        elif 'Customer Charge' in desc:
            rate = extract('ServiceCharge_Table', 'Rate', desc, row)

        elif 'Processing' in desc:
            rate = extract('OtherCharges_Table', 'ChargeType', desc, row)

        else:
            continue

        rate_data[key] = round(rate, 10)

    rate_data_mapped = {
        'midpeak_rate_summer': extract_summer_demand_rate(rates["DemandTime_Table"], "800", "1759"),
        'peak_rate_summer': extract_summer_demand_rate(rates["DemandTime_Table"], "800", "2159"),
        'as_used_rate_nonsummer': extract(
            'DemandTime_Table', 'RatekW',
            'As-used Daily Demand Delivery Charge',
            {'Weighted': False, 'Prorated': False}
        ),
        'surcharge_rate': sum(v for v in kwh_charges.values()),
        'customer_charge': rate_data.get('customer_charge', 0.0),
        'processing_charge': rate_data.get('billing_and_payment_processing_ch', 0.0),
        'contract_demand_rate': extract(
            'Demand_Table', 'RatekW',
            'Contract Demand Delivery Charge',
            {'Weighted': False, 'Prorated': True}
        ),
        'delivery_tax_rate': 0.0,  # not implemented
        'kwh_charge_breakdown': kwh_charges
    }

    return rate_data_mapped

def load_data():
    """Load charge configuration and history data."""
    charges_df = pd.read_csv('charge_config.csv')
    
    with open('charge_history.json', 'r') as f:
        rates = json.load(f)
    
    return charges_df, rates

def create_sample_demand_data():
    """Create sample demand data for the billing period."""
    # Sample calculation period: 2025-04-16 to 2025-05-15
    dates = pd.date_range('2025-04-16', '2025-05-15', freq='D')
    
    # Create realistic demand data (non-summer period)
    # Assuming some variation around the 382 kW demand mentioned in sample
    billing_df = pd.DataFrame({
        'Date': dates,
        'MidPeakDemand_kW': [350 + (i % 7) * 10 for i in range(len(dates))],
        'PeakDemand_kW': [380 + (i % 5) * 8 for i in range(len(dates))]
    })
    
    return billing_df

def test_bill_calculation():
    """Test the bill calculation with sample data."""
    print("=== TESTING BILL CALCULATION ===")
    print("Sample from calculation.txt:")
    print("DateFrom: 2025-04-16, DateTo: 2025-05-15")
    print("Demand: 382 kW, Usage: 128627 kWh")
    print("Expected Bill Amount: $17,230.93")
    print("=" * 50)
    
    # Load data
    charges_df, rates = load_data()
    billing_df = create_sample_demand_data()
    
    # Sample parameters from the calculation file
    usage_kwh = 128627
    start_date = '2025-04-16'
    end_date = '2025-05-15'
    contract_demand_kW = 382
    charge_types = [0, 2]  # Transmission + Delivery
    
    print(f"\nUsing charge types: {charge_types}")
    print(f"Billing period: {start_date} to {end_date}")
    print(f"Usage: {usage_kwh:,} kWh")
    print(f"Contract demand: {contract_demand_kW} kW")
    
    # Extract rate data
    rate_data = extract_rate_data(
        rates, charges_df, start_date, end_date, 
        charge_types=charge_types
    )
    
    print(f"\nExtracted rates:")
    print(f"Contract demand rate: ${rate_data['contract_demand_rate']:.6f}/kW")
    print(f"Non-summer as-used rate: ${rate_data['as_used_rate_nonsummer']:.6f}/kW")
    print(f"Total surcharge rate: ${rate_data['surcharge_rate']:.6f}/kWh")
    print(f"Customer charge: ${rate_data['customer_charge']:.2f}")
    print(f"Processing charge: ${rate_data['processing_charge']:.2f}")
    
    # Calculate bill
    bill = calculate_bill(
        billing_df, usage_kwh, start_date, end_date, 
        rate_data, contract_demand_kW, charge_types
    )
    
    print(f"\n=== CALCULATED BILL BREAKDOWN ===")
    print(f"Customer Charge: ${bill['customer_charge']['amount']:,.2f}")
    print(f"Processing Charge: ${bill['processing_charge']['amount']:,.2f}")
    print(f"Contract Demand Charge: ${bill['contract_demand_charge']['amount']:,.2f}")
    print(f"  - {contract_demand_kW} kW × ${rate_data['contract_demand_rate']:.6f}/kW")
    print(f"Summer Demand Charge: ${bill['demand_charge_summer']['amount']:,.2f}")
    print(f"Non-Summer Demand Charge: ${bill['demand_charge_nonsummer']['amount']:,.2f}")
    print(f"Energy Surcharge: ${bill['energy_surcharge']['amount']:,.2f}")
    print(f"  - {usage_kwh:,} kWh × ${rate_data['surcharge_rate']:.6f}/kWh")
    
    print(f"\nTOTAL CALCULATED: ${bill['total']:,.2f}")
    print(f"EXPECTED FROM SAMPLE: $17,230.93")
    print(f"DIFFERENCE: ${bill['total'] - 17230.93:,.2f}")
    
    # Show energy charge breakdown
    if rate_data['kwh_charge_breakdown']:
        print(f"\n=== ENERGY CHARGE BREAKDOWN ===")
        for desc, rate in rate_data['kwh_charge_breakdown'].items():
            if rate != 0:
                charge = rate * usage_kwh
                print(f"{desc.replace('_', ' ').title()}: ${rate:.6f}/kWh = ${charge:.2f}")
    
    return bill, rate_data

if __name__ == "__main__":
    try:
        bill, rate_data = test_bill_calculation()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()