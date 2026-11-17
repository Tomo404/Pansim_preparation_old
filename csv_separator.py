import pandas as pd

INPUT = "df_main_redemption_OG_cleaned.csv"
OUTPUT = "df_main_redemption_OG_cleaned_split.xlsx"

# --- 1. Beolvasás ---
print(f"📥 Beolvasás: {INPUT}")
df = pd.read_csv(INPUT, header=None, encoding="utf-8-sig")

# --- 2. Csak az adatsorok (első sor kihagyva) ---
data = df[0].tolist()[1:]

# --- 3. Split '|' zárójeleken kívül ---
def smart_split(s):
    parts = []
    buf = ''
    depth = 0
    for char in s:
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
        elif char == '|' and depth == 0:
            parts.append(buf.strip())
            buf = ''
            continue
        buf += char
    parts.append(buf.strip())
    return parts

# --- 4. Feldarabolás minden sorra ---
split_data = [smart_split(row) for row in data]

# --- 5. Oszlopnevek ---
columns = [
    "Terület",
    "Régió",
    "TEÁOR főág",
    "TEÁOR alág kód",
    "TEÁOR alág név",
    "Létszámkategória",
    "Érték"
]

# --- 6. Egészítsük ki a hiányzó oszlopokat ---
max_len = len(columns)
split_data = [row + [""] * (max_len - len(row)) for row in split_data]

# --- 7. DataFrame ---
df_split = pd.DataFrame(split_data, columns=columns)

# --- 8. Mentés Excelbe ---
df_split.to_excel(OUTPUT, index=False, engine="openpyxl")

print(f"✅ Mentve: {OUTPUT}")
print(df_split.head())
