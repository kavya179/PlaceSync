import pandas as pd
import io

csv_content = """Enrollment Number,Student Name,Email
24002170210063,Krisha,krisha@gmail.com
2.4002170210063e+13,Student 2,s2@gmail.com
24002170210063.0,Student 3,s3@gmail.com
"24002170210063",Student 4,s4@gmail.com
"""

buf = io.StringIO(csv_content)
df = pd.read_csv(buf, dtype=str)
print("pd.read_csv dtype=str:")
for idx, r in df.iterrows():
    print(f"Row {idx+1}: {r['Enrollment Number']!r}")
