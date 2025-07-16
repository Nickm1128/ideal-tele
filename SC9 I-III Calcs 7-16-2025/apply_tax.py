import pandas as pd

tax_df = pd.read_excel(r"Q:\AUDITORS\EGOS Shared Folder\Development\Nick's pythons\SC9 IV Calcs 5-20-2025\SalesGRTax.xlsx")

def apply_grt_salestax(bill, tax_df):
    sub_tax_df = tax_df[
        (tax_df['AccountID'] == bill['AccountID']) &
        (tax_df['DateFrom'] == bill['DateFrom']) & 
        (tax_df['DateTo'] == bill['DateTo'])
    ]
    if len(sub_tax_df) > 0:
        sub_tax_df = sub_tax_df.iloc[0]
        sales_tax_rate = sub_tax_df['SalesTaxRate'] / 100
        if not sales_tax_rate > 0:
            sales_tax_rate = 0
        grt_rate = sub_tax_df['GRTRate']
        if not grt_rate > 0:
            grt_rate = 0

        print(grt_rate)
        total = float(bill['total']) * (1 + grt_rate)
        total = total * (1 + sales_tax_rate)
        bill['total'] = str(total)
        
        return bill 
    else:
        return bill
 