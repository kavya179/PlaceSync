import re
from decimal import Decimal

def clean_roll_number_val(val):
    if val is None:
        return ''
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ['nan', 'none', 'null']:
        return ''
    
    # Remove any embedded newlines, carriage returns, tabs, or spaces inside enrollment numbers
    val_str = re.sub(r'[\r\n\t\s]+', '', val_str)
    
    if val_str.endswith('.0'):
        val_str = val_str[:-2]
        
    if 'e+' in val_str.lower() or 'e-' in val_str.lower() or ('e' in val_str.lower() and any(ch.isdigit() for ch in val_str)):
        try:
            d_val = Decimal(val_str)
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

print("Row 1 ('24002170210063'):", clean_roll_number_val('24002170210063'))
print("Row 2 ('2.4002170210063e+13'):", clean_roll_number_val('2.4002170210063e+13'))
print("Row 3 ('24002170210063.0'):", clean_roll_number_val('24002170210063.0'))
print("Row 4 ('24002170210063'):", clean_roll_number_val('24002170210063'))
