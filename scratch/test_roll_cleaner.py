def clean_roll_number(val):
    if val is None:
        return ''
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ['nan', 'none', 'null']:
        return ''
    if val_str.endswith('.0'):
        val_str = val_str[:-2]
    if 'e+' in val_str.lower() or 'e-' in val_str.lower() or 'e' in val_str.lower() and ('+' in val_str or '-' in val_str):
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

test_cases = [
    ("24002170210063", "24002170210063"),
    ("24002170210063.0", "24002170210063"),
    ("2.4002170210063e+13", "24002170210063"),
    ("2.4002170210063E+13", "24002170210063"),
    ("2.4002170210063e13", "24002170210063"),
    ("CS2027901", "CS2027901"),
    ("MIT-101", "MIT-101"),
    (24002170210063, "24002170210063"),
    (24002170210063.0, "24002170210063"),
]

for item, expected in test_cases:
    result = clean_roll_number(item)
    status = "OK" if result == expected else f"FAIL (got {result})"
    print(f"Input: {item!r:25} -> Result: {result!r:20} [{status}]")
