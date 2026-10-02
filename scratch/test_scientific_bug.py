import re

def clean_roll_number_val(val):
    if val is None:
        return ''
    val_str = str(val).strip()
    print("Initial val_str:", repr(val_str))
    if not val_str or val_str.lower() in ['nan', 'none', 'null']:
        return ''
    
    # Remove any embedded newlines, carriage returns, tabs
    val_str = re.sub(r'[\r\n\t]+', '', val_str)
    
    if val_str.endswith('.0'):
        val_str = val_str[:-2]
        
    if 'e+' in val_str.lower() or 'e-' in val_str.lower() or ('e' in val_str.lower() and any(ch.isdigit() for ch in val_str)):
        try:
            f_val = float(val_str)
            if f_val.is_integer():
                val_str = str(int(f_val))
            else:
                val_str = f"{f_val:.0f}"
        except (ValueError, OverflowError):
            pass
    elif '.' in val_str:
        try:
            f_val = float(val_str)
            if f_val.is_integer():
                val_str = str(int(f_val))
        except (ValueError, OverflowError):
            pass
    return val_str

print("Test 2.4e13:", clean_roll_number_val("2.4e13"))
print("Test 2.4E+13:", clean_roll_number_val("2.4E+13"))
print("Test 24002170210009:", clean_roll_number_val("24002170210009"))
print("Test 24002170\\n210009:", clean_roll_number_val("24002170\n210009"))
print("Test 2.4002170210009e+13:", clean_roll_number_val("2.4002170210009e+13"))
print("Test 2.400217e+13:", clean_roll_number_val("2.400217e+13"))
