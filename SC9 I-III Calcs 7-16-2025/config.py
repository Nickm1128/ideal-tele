import pyodbc
import pandas as pd

conn1 = pyodbc.connect('Driver={SQL Server};'
                              'Server=UTIL-PROD-DB;'
                              'Database=NewClientInfo;')

def GetElecBills(Anumber, conn1):
    '''Takes account number, not account ID'''

    sql1 = """SELECT distinct Bill.[AccountID] as AccountID
                                ,Acc.[AccountNumber] as AccountNumber
                    ,Client.[CompanyName] as Client
                    ,CONVERT(datetime,Bill.[DateFrom], 1) As DateFrom
                    ,CONVERT(datetime,Bill.[DateTo], 1) As DateTo
                    ,Bill.[Usage] As Usage
                    ,Bill.[Demand] As Demand
                    ,Bill.[BillAmount]
                    ,Bill.ReadingType
                    ,Bill.ProcessedDate
                    ,Bill.StatementDate
                FROM [NewClientInfo].[dbo].[EGOS_BillingDetails] Bill
                JOIN [NewClientInfo].[dbo].[Accounts] Acc on Acc.[AccountID]=Bill.[AccountID]
                JOIN [NewClientInfo].[dbo].[Client] on [NewClientInfo].[dbo].[Client].[ClientID]=Acc.[AccountClientID]
                WHERE Bill.[Revised] = 0 and Acc.[AccountInvoicePrefix] = 'E' and Acc.[AccountID] = ?
                ORDER BY [DateTo] desc"""
    bills = pd.read_sql(sql1, conn1, params = [Anumber])
    
    bills['DateFrom'] = bills['DateFrom'].astype('datetime64[ns]')
    bills['DateTo'] = bills['DateTo'].astype('datetime64[ns]')
    

    bills['Days'] = (bills['DateTo']-bills['DateFrom'])
    
    for i in bills.index:
        bills['Days'][i]=bills['Days'][i].days
    bills['Load Factor'] = float(0)
    for i in bills.index:
        if bills['Demand'][i] != 0:
            bills['Load Factor'][i] = bills['Usage'][i] / (bills['Demand'][i]*bills['Days'][i]*24)
    bills['Load Factor'] = bills['Load Factor'].astype('float')
    bills['Load Factor'] = bills['Load Factor'].round(2)
        

    return bills

def print_bill_summary(bill):
    print("Itemized Bill Summary:\n")
    
    for key, details in bill.items():
        if isinstance(details, dict):
            print(f"{key.replace('_', ' ').title()}: ${details.get('amount', 0):,.2f}")
            
            # Special handling for energy surcharge breakdown
            if key == "energy_surcharge" and 'breakdown' in details:
                print(f"    - Rate per kWh: {details.get('rate_per_kWh', 0):.6f}")
                print(f"    - Usage: {details.get('usage_kWh', 0):,} kWh")
                print(f"    - Breakdown:")
                for charge, info in details['breakdown'].items():
                    charge_label = charge.replace('_', ' ').title()
                    charge_amt = info.get('charge', 0.0)
                    charge_rate = info.get('rate_per_kWh', 0.0)
                    print(f"        • {charge_label}: ${charge_amt:,.2f} @ {charge_rate:.10f}/kWh")
            else:
                for k, v in details.items():
                    if k != 'amount':
                        print(f"    - {k.replace('_', ' ').capitalize()}: {v}")
        else:
            print(f"{key.replace('_', ' ').title()}: ${details:,.2f}")