import pandas as pd
import re
import csv

MAIN_PATH = "df_main_redemption_OG.csv"
SUMMARY_PATH = "df_summary_redemption_OG.csv"
NEW_MAIN = "df_main_redemption_OG_fixed.csv"
NEW_SUMMARY = "df_summary_redemption_OG_fixed.csv"

# --- 1) Saját oszlopnevek, első sor kihagyása
columns = ['terulet', 'region_file', 'teaor_főág', 'teaor_alág_kód', 'teaor_alág_név', 'létszám_kategória', 'érték']
df_main = pd.read_csv(MAIN_PATH, encoding='utf-8-sig', header=None, skiprows=1, names=columns)
df_summary = pd.read_csv(SUMMARY_PATH, encoding='utf-8-sig')

# --- 2) Sorvégi pontosvesszők eltávolítása minden cellából
for col in df_main.columns:
    df_main[col] = df_main[col].astype(str).str.rstrip(';').str.strip()

# --- 3) Hibás sorok szűrése ('mindösszesen' vagy 'járás')
mask = df_main['terulet'].str.contains(r'mindösszesen|járás', flags=re.IGNORECASE, na=False)
to_move = df_main[mask].copy()
df_main_cleaned = df_main[~mask].copy()

# --- 4) Áthelyezés a summary-be
df_summary_extended = pd.concat([df_summary, to_move], ignore_index=True)

# --- 5) Mentés CSV-be UTF-8-sig
df_main_cleaned.to_csv(NEW_MAIN, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_MINIMAL)
df_summary_extended.to_csv(NEW_SUMMARY, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_MINIMAL)

print("✅ Kész! Az első sort kihagytuk, sorvégi ';'-k eltávolítva, hibás sorok átmozgatva a summary-be.")
