import pandas as pd 
import numpy as np 
import pyodbc
import ast
from datetime import datetime
import json
import re
import random

import sys
import os
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)
import AccConv as ac

from bill_calc import *
from config import * 
from as_used_daily_demand import *
from target_accounts import GetTargetAccs
from apply_tax import apply_grt_salestax

tax_df = pd.read_excel(r"Q:\AUDITORS\EGOS Shared Folder\Development\Nick's pythons\SC9 IV Calcs 5-20-2025\SalesGRTax.xlsx")
bill_list = []

params = GetTargetAccs(conn1)
#print(params.loc[0])
print(f'Length of params: {len(params)}')
#params = random.sample(params, 1)

for i in params.index:
    Anumber = int(params['AccountID'][i])
    load_zone = params['Load Zone'][i]
    try:
        bills = GetElecBills(Anumber, conn1).sort_values(by='DateTo')

        bills['Contract Demand'] = bills['Demand'].rolling(24, min_periods=1).max()
        bills = bills.dropna(subset='Contract Demand')

        if len(bills) == 0:
            print('No Bills')
            continue

        else:
            ami = ac.AMIData(Anumber, 'KWH')

            # ami = ami[(ami['StartDate'] >= bills['DateFrom'].iloc[0]) & 
            #         (ami['EndDate'] <= bills['DateTo'].iloc[-1])]
            
            if len(ami) == 0:
                print('No AMI Data')
                continue
            else:
                daily_demand_df = CalcStandByDemand(bills, ami)

                history = GetChargeHistory(conn1)
                charges = GetChargeConfig(conn1)

                for idx in bills.index:
                    account_id = bills['AccountID'][idx]
                    start_date = bills['DateFrom'][idx].strftime('%m-%d-%Y')
                    end_date = bills['DateTo'][idx].strftime('%m-%d-%Y')

                    bill_amount = bills['BillAmount'][idx]

                    usage = bills['Usage'][idx]
                    contract_demand = bills['Contract Demand'][idx]
                    rates = extract_rate_data(history, charges, start_date, end_date, city="New York City")
                    bill = calculate_bill(
                        daily_demand_df,
                        usage,
                        start_date, end_date,
                        rates,
                        contract_demand_kW=contract_demand
                    )
                    bill['AccountID'] = account_id
                    bill['DateFrom'] = start_date 
                    bill['DateTo'] = end_date
                    bill['AsBilled'] = bill_amount

                    bill = apply_grt_salestax(bill, tax_df)
                    print(bill)

                    bill_list.append(bill)
                    #print_bill_summary(bill)

        progress = params['AccountID'].tolist().index(Anumber) + 1

        print(f'{progress}/{len(params)}')

        final_df = pd.DataFrame(bill_list)
        final_df.to_excel(rf"Q:\AUDITORS\EGOS Shared Folder\Development\Nick's pythons\SC9 IV Calcs 5-20-2025\Output\Standard\Standard Calcs{progress}.xlsx", index=False)
    except Exception as e:
        print(e)