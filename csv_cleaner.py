import pandas as pd
import csv
import re

MAIN_FIXED = "df_main_redemption_OG_fixed.csv"
SUMMARY_FIXED = "df_summary_redemption_OG_fixed.csv"
NEW_MAIN = "df_main_redemption_OG_cleaned.csv"
NEW_SUMMARY = "df_summary_redemption_OG_cleaned.csv"

# --- 1) Beolvasás stringként minden oszlopra
df_main = pd.read_csv(MAIN_FIXED, encoding='utf-8-sig', low_memory=False, dtype=str)
df_summary = pd.read_csv(SUMMARY_FIXED, encoding='utf-8-sig', low_memory=False, dtype=str)

# --- 2) Header-ek elmentése
header_main = df_main.columns.tolist()
header_summary = df_summary.columns.tolist()

# --- 3) Sorvégi felesleges mezők eltávolítása (nan, ;)
def strip_trailing_extra_safe(row):
    # sorvégi nan, üres cellák, ';' eltávolítása
    cleaned = [x for x in row if pd.notna(x) and str(x).strip() not in ('', ';', ',nan')]
    return pd.Series(cleaned)

# Header sorokat kihagyjuk a tisztításból
df_main_data = df_main.copy()
df_summary_data = df_summary.copy()

df_main_cleaned = df_main_data.apply(strip_trailing_extra_safe, axis=1)
df_summary_cleaned = df_summary_data.apply(strip_trailing_extra_safe, axis=1)

# Header visszaállítása (main fix 7 oszlop)
cols_main = ['terulet', 'region_file', 'teaor_főág', 'teaor_alág_kód', 'teaor_alág_név', 'létszám_kategória', 'érték']
df_main_cleaned.columns = cols_main[:df_main_cleaned.shape[1]]
df_summary_cleaned.columns = header_summary[:df_summary_cleaned.shape[1]]

# --- 4) Hibás sorok szűrése a mainből (mindösszesen / járás)
mask = df_main_cleaned['terulet'].str.contains(r'mindösszesen|járás', flags=re.IGNORECASE, na=False)
to_move = df_main_cleaned[mask].copy()
df_main_cleaned = df_main_cleaned[~mask].copy()

# --- 5) Áthelyezés a summary-be
df_summary_extended = pd.concat([df_summary_cleaned, to_move], ignore_index=True)

# --- 6) Vesszők cseréje nem idézőjelben
def replace_commas_not_in_quotes(s):
    if pd.isna(s):
        return s
    parts = re.split(r'(".*?")', str(s))
    for i in range(len(parts)):
        if i % 2 == 0:  # idézőjelek nélküli részek
            parts[i] = parts[i].replace(',', '|')
    return ''.join(parts)

for col in df_main_cleaned.columns:
    df_main_cleaned[col] = df_main_cleaned[col].apply(replace_commas_not_in_quotes)

for col in df_summary_extended.columns:
    df_summary_extended[col] = df_summary_extended[col].apply(replace_commas_not_in_quotes)

# --- 7) Mentés UTF-8-sig
df_main_cleaned.to_csv(NEW_MAIN, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_MINIMAL)
df_summary_extended.to_csv(NEW_SUMMARY, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_MINIMAL)

print("✅ Kész! Sorvégi felesleges mezők eltávolítva, vesszők cserélve, hibás sorok summary-be átmozgatva, header megőrizve.")
