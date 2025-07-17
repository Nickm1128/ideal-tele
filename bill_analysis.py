"""
Analysis of the bill calculation results to identify discrepancies.
"""

import pandas as pd
import json

def analyze_bill_discrepancy():
    """Analyze the discrepancy between calculated and expected bill amounts."""
    
    print("=== BILL CALCULATION ANALYSIS ===")
    print()
    
    # Results from our calculation
    calculated_total = 18401.78
    expected_total = 17230.93
    difference = calculated_total - expected_total
    
    print(f"Calculated Total: ${calculated_total:,.2f}")
    print(f"Expected Total:   ${expected_total:,.2f}")
    print(f"Difference:       ${difference:,.2f} ({difference/expected_total*100:.1f}% higher)")
    print()
    
    # Breakdown of our calculation
    customer_charge = 68.63
    processing_charge = 0.00
    contract_demand_charge = 3389.87
    summer_demand_charge = 0.00
    nonsummer_demand_charge = 14092.80
    energy_surcharge = 850.48
    
    print("=== OUR CALCULATION BREAKDOWN ===")
    print(f"Customer Charge:        ${customer_charge:>8,.2f}")
    print(f"Processing Charge:      ${processing_charge:>8,.2f}")
    print(f"Contract Demand:        ${contract_demand_charge:>8,.2f}")
    print(f"Summer Demand:          ${summer_demand_charge:>8,.2f}")
    print(f"Non-Summer Demand:      ${nonsummer_demand_charge:>8,.2f}")
    print(f"Energy Surcharge:       ${energy_surcharge:>8,.2f}")
    print(f"                        --------")
    print(f"Total:                  ${calculated_total:>8,.2f}")
    print()
    
    # Potential issues to investigate
    print("=== POTENTIAL ISSUES ===")
    print()
    
    print("1. NON-SUMMER DEMAND CALCULATION:")
    print(f"   - Our calculation: ${nonsummer_demand_charge:,.2f}")
    print(f"   - This seems high compared to expected total")
    print(f"   - Rate used: $1.174400/kW")
    print(f"   - Total kW calculated: {nonsummer_demand_charge / 1.174400:.2f} kW")
    print(f"   - This suggests ~12,000 kW total, which seems excessive")
    print()
    
    print("2. CONTRACT DEMAND CALCULATION:")
    print(f"   - Our calculation: ${contract_demand_charge:,.2f}")
    print(f"   - 382 kW × $8.874/kW = ${382 * 8.874:.2f}")
    print(f"   - Rate may need prorating for partial month")
    print()
    
    print("3. CUSTOMER CHARGE:")
    print(f"   - Our calculation: ${customer_charge:.2f}")
    print(f"   - This may also need prorating")
    print()
    
    print("4. DEMAND DATA ISSUES:")
    print("   - We're using synthetic demand data")
    print("   - Real meter data would show actual daily peaks")
    print("   - Our synthetic data may be overestimating demand")
    print()
    
    print("=== RECOMMENDATIONS ===")
    print()
    print("1. Check demand calculation logic:")
    print("   - Verify how daily max demand is calculated")
    print("   - Ensure we're not double-counting days")
    print()
    print("2. Verify prorating logic:")
    print("   - Contract demand should be prorated for billing days")
    print("   - Customer charges may need prorating")
    print()
    print("3. Use actual meter data:")
    print("   - Replace synthetic demand data with real readings")
    print("   - This would give more accurate demand charges")
    print()
    print("4. Check rate effective dates:")
    print("   - Ensure we're using correct rates for April 2025")
    print("   - Some rates may have changed during billing period")

if __name__ == "__main__":
    analyze_bill_discrepancy()