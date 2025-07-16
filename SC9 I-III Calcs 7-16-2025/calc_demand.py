import pandas as pd 
import numpy as np 
import pyodbc
import ast
from datetime import timedelta


import sys
import os
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)
import AccConv as ac

def add_peak_columns(ami):
    on_peak_start = 8   
    on_peak_end = 18   
    mid_peak_start = 8  
    mid_peak_end = 22    
    ami['on_peak'] = 0
    ami['mid_peak'] = 0
    ami['off_peak'] = 1

    ami.loc[(ami['StartDate'].dt.hour >= on_peak_start) &
            (ami['EndDate'].dt.hour < on_peak_end) &
            (ami['EndDate'].dt.hour != 0) &
            (ami['EndDate'].dt.month.isin([6, 7, 8, 9])), 'on_peak'] = 1
    
    ami.loc[(ami['StartDate'].dt.hour >= mid_peak_start) &
            (ami['EndDate'].dt.hour < mid_peak_end) &
            (ami['EndDate'].dt.hour != 0), 'mid_peak'] = 1

    return ami

def CalcCoinDemand(bills, ami):
    bills['AMI Demand'] = np.nan
    bills['AMI Usage'] = np.nan

    ami['StartDate'] = pd.to_datetime(ami['StartDate'])
    ami['EndDate'] = pd.to_datetime(ami['EndDate'])
    ami = ami[(ami['EndDate'] - ami['StartDate']).dt.total_seconds() / 60 == 5]
    ami = ami[(ami['UsageUnit'] == 'KWH')]

    for i in bills.index:
        rel_ami = ami[(ami['StartDate'] >= bills['DateFrom'][i] + timedelta(days=1)) & 
                      (ami['EndDate'] <= bills['DateTo'][i])]
        
        if rel_ami.shape[0] > 0:
            rel_ami = pd.DataFrame(rel_ami.groupby(['StartDate', 'EndDate'])['Usage'].sum()).reset_index()

            bills['AMI Demand'][i] = rel_ami['Usage'].rolling(6).sum().max() * 2
            bills['AMI Usage'][i] = rel_ami['Usage'].sum()

    return bills
