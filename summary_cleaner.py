import pandas as pd
import csv

INPUT = "df_summary_redemption_OG_cleaned.csv"
OUTPUT = "df_summary_redemption_OG_cleaned_final.csv"

# CSV beolvasása
df = pd.read_csv(INPUT, encoding='utf-8-sig', dtype=str, low_memory=False)

# Minden cella utolsó 4 karakterének levágása
def strip_last4(x):
    if pd.isna(x):
        return x
    return str(x)[:-4] if len(str(x)) > 4 else ''

df = df.applymap(strip_last4)

# Mentés
df.to_csv(OUTPUT, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_MINIMAL)

print("✅ Kész! Minden cella utolsó 4 karaktere levágva.")
