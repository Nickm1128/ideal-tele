from config import conn1 
import pyodbc 
import pandas as pd 

def GetTargetAccs(conn1):
    params = pd.read_csv(r"Q:\AUDITORS\EGOS Shared Folder\Development\Nick's Pythons' Food\BillCalcParameters.csv")

    params = params[(params['ServiceClass'] == 9) & (params['Subrate'] != 'II')].drop_duplicates(subset='AccountID')

    ami_head_sql = """
    SELECT DISTINCT AccountID
    FROM [IntervalData].[dbo].[AMIImportHeader]
    """

    ami_head = pd.read_sql(ami_head_sql, conn1)

    params = params[params['AccountID'].isin(ami_head['AccountID'].tolist())]
    params = params[['AccountID','Load Zone','Full Service']]

    return params

print(GetTargetAccs(conn1))