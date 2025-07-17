# Electric Bill Calculator - Charge Type Configuration

## Overview

This electric bill calculator supports different charge type combinations to calculate bills based on various utility rate components. The system uses three main service types:

- **Type 0**: Transmission charges (4 charges)
- **Type 1**: Supply charges (9 charges) 
- **Type 2**: Delivery charges (38 charges)

## Charge Type Combinations

### Option 1: Transmission + Delivery [0, 2] - Current Default
- **Total charges**: 42
- **Includes**: System transmission + delivery infrastructure charges
- **Use case**: Standard delivery service billing
- **Key charges**: Monthly Adjustment Clause, Energy Delivery Charge, Revenue Decoupling, regulatory surcharges

### Option 2: Transmission + Supply [0, 1] - Alternative
- **Total charges**: 13  
- **Includes**: System transmission + generation/supply charges
- **Use case**: Supply service billing
- **Key charges**: Clean Energy Standard charges, Merchant Function charges, Market Supply Charge

## Usage Examples

### Basic Usage with Default Charge Types [0, 2]

```python
import pandas as pd
import json
from bill_calc import calculate_bill, extract_rate_data

# Load data
charges_df = pd.read_csv('charge_config.csv')
with open('charge_history.json', 'r') as f:
    rates = json.load(f)

# Create billing data (replace with actual meter data)
billing_df = pd.DataFrame({
    'Date': pd.date_range('2025-04-16', '2025-05-15', freq='D'),
    'MidPeakDemand_kW': [300] * 30,
    'PeakDemand_kW': [350] * 30
})

# Extract rate data with default charge types [0, 2]
rate_data = extract_rate_data(
    rates, charges_df, '2025-04-16', '2025-05-15',
    charge_types=[0, 2]
)

# Calculate bill
bill = calculate_bill(
    billing_df, 128627, '2025-04-16', '2025-05-15',
    rate_data, contract_demand_kW=382, charge_types=[0, 2]
)

print(f"Total Bill: ${bill['total']:,.2f}")
```

### Using Alternative Charge Types [0, 1]

```python
# Extract rate data with supply charges [0, 1]
rate_data_supply = extract_rate_data(
    rates, charges_df, '2025-04-16', '2025-05-15',
    charge_types=[0, 1]
)

# Calculate bill with supply charges
bill_supply = calculate_bill(
    billing_df, 128627, '2025-04-16', '2025-05-15',
    rate_data_supply, contract_demand_kW=382, charge_types=[0, 1]
)

print(f"Supply Bill Total: ${bill_supply['total']:,.2f}")
```

### Comparing Both Options

```python
# Compare delivery vs supply billing
print("=== BILL COMPARISON ===")
print(f"Transmission + Delivery [0,2]: ${bill['total']:,.2f}")
print(f"Transmission + Supply [0,1]:   ${bill_supply['total']:,.2f}")
print(f"Difference: ${bill['total'] - bill_supply['total']:,.2f}")
```

## Key Differences Between Charge Types

### Unique to Supply [0,1]:
- Clean Energy Standard Supply Charges
- Merchant Function Charges  
- Market Supply Charge - Capacity
- Environmental compliance charges

### Unique to Delivery [0,2]:
- Monthly Adjustment Clause (MAC)
- Energy Delivery Charge
- Revenue Decoupling Mechanism
- Various delivery surcharges and regulatory adjustments

## Modified Functions

The following functions have been updated to support charge type selection:

1. **`calculate_bill()`** - Added `charge_types` parameter (default: [0, 2])
2. **`extract_rate_data()`** - Added `charge_types` parameter (default: [0, 2])  
3. **`GetChargeConfig()`** - Added `charge_types` parameter (default: [0, 2])

## Files

- **`bill_calc.py`** - Main calculation functions (updated)
- **`test_charge_types.py`** - Analysis of charge type distributions
- **`charge_type_helper.py`** - Helper functions and utilities
- **`example_usage.py`** - Complete usage examples
- **`charge_config.csv`** - Charge configuration data
- **`charge_history.json`** - Rate history data

## Rate Calculation Formula

For each billing period, the system:

1. **Filters charges** by selected service types (0, 1, 2)
2. **Multiplies rate × quantity** for each applicable charge:
   - kWh charges: `rate_per_kWh × usage_kWh`
   - kW charges: `rate_per_kW × demand_kW` 
   - Fixed charges: `rate × billing_days/30` (if prorated)
3. **Sums all charges** to get the total bill

The key insight is that choosing [0,1] vs [0,2] determines whether you're billing for supply services or delivery services, which have very different rate structures and total costs.