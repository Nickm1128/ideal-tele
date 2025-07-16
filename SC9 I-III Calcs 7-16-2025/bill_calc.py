import pandas as pd 
import numpy as np 
import pyodbc
import ast
from datetime import datetime
import json
import re

import sys
import os
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

def string_to_list(s):
    try:
        result = ast.literal_eval(s)
        if isinstance(result, list):
            return result
        else:
            raise ValueError("The string does not represent a list.")
    except Exception as e:
        print(f"Error: {e}")
        return None

def calculate_bill(
    billing_df: pd.DataFrame,
    usage_kwh: float,
    start_date,
    end_date,
    rate_data: dict,
    contract_demand_kW: float = 0.0,
):
    """
    Calculate a detailed electric delivery bill based on as-used demand and energy usage.

    Parameters:
    - billing_df (pd.DataFrame): DataFrame containing as-used demand data with
      ``Date`` and demand columns.
    - usage_kwh (float): Total energy usage during billing period
    - start_date (str or datetime): Billing period start date
    - end_date (str or datetime): Billing period end date
    - rate_data (dict): Rate structure extracted via ``extract_rate_data``
    - contract_demand_kW (float, optional): Contract demand in kW used for the
      contract demand charge calculation.

    Returns:
    - dict: Itemized breakdown of charges and total bill
    """

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

def extract_rate_data(rates, charges_df, start_date, end_date, city="New York City"):
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
                next_date = min(end_date, df.iloc[i + 1]['EffectiveDate'] )#- pd.Timedelta(days=1))
            else:
                next_date = end_date
            days = (next_date - eff_date).days #+ 1
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

        if row['Unit'] == 'kWh' and row['ServiceTypeId'] in [0, 2]:
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

def GetChargeHistory(conn1):
    sql1 = """SELECT TOP (1000) [Id]
        ,[RateAcuityRateId]
        ,[EffectiveDate]
        ,[RateHistory]
        ,[CreatedBy]
        ,[CreatedDate]
        ,[ModifiedBy]
        ,[ModifiedDate]
    FROM [ExternalData].[dbo].[RateAcuityRateHistory]
    WHERE RateAcuityRateId = 22
    """
    return string_to_list(pd.read_sql(sql1,conn1)['RateHistory'][0])[0]

def GetChargeConfig(conn1):
    sql1 = """
    SELECT TOP (1000) [Id]
        ,[RateAcuityRateId]
        ,[RateAcuityChargeId]
        ,[RateAcuityChargeDescription] AS 'Description'
        ,[RateAcuityChargeSeason]
        ,[RateAcuityChargeStartDate]
        ,[RateAcuityChargeEndDate]
        ,[RateAcuityChargeStartTime]
        ,[RateAcuityChargeEndTime]
        ,[RateAcuityChargeTimeOfDay]
        ,[RateAcuityChargeDeterminant] AS 'Unit'
        ,[ChargeTypeId]
        ,[ChargeParameterTypeId]
        ,[UsageType]
        ,[WeightedAverage] AS 'Weighted'
        ,[Prorated]
        ,[Block]
        ,[ServiceTypeId]
        ,[RatchetChargeDetailsId]
        ,[Complete]
        ,[CreatedBy]
        ,[CreatedDate]
        ,[ModifiedBy]
        ,[ModifiedDate]
    FROM [ExternalData].[dbo].[ChargeConfiguration]
    WHERE RateAcuityRateId = 22
    AND RateAcuityChargeDescription NOT LIKE '%Average Supply Charge%'
    AND [ChargeTypeId] IN (0, 2)

    """
    return pd.read_sql(sql1,conn1)