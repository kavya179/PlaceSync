import re
from decimal import Decimal

def clean_roll_number_val(val):
    if val is None:
        return ''
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ['nan', 'none', 'null']:
        return ''
    
    # Remove any embedded newlines, carriage returns, tabs, or spaces
    val_str = re.sub(r'[\r\n\t\s]+', '', val_str)
    
    if val_str.endswith('.0'):
        val_str = val_str[:-2]
        
    # Handle scientific notation e.g. "2.4002170210009e+13" or "2.4002170210009E+13"
    if 'e+' in val_str.lower() or 'e-' in val_str.lower() or ('e' in val_str.lower() and any(ch.isdigit() for ch in val_str)):
        try:
            d_val = Decimal(val_str)
            # If it converts cleanly to integer format
            if d_val == d_val.to_integral_value():
                val_str = str(int(d_val))
            else:
                val_str = f"{d_val:f}"
        except Exception:
            pass
    elif '.' in val_str:
        try:
            d_val = Decimal(val_str)
            if d_val == d_val.to_integral_value():
                val_str = str(int(d_val))
        except Exception:
            pass
            
    return val_str

test_inputs = [
    "24002170210009",
    "24002170\n210009",
    "24002170\r\n210009",
    "24002170 210009",
    "24002170210009.0",
    "2.4002170210009e+13",
    "2.4002170210009E+13",
    "2.4e13",
]

for inp in test_inputs:
    res = clean_roll_number_val(inp)
    print(f"Input: {inp!r:25} -> Cleaned: {res!r}")
