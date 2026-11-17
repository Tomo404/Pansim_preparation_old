# district_mover.py
import pandas as pd
import unicodedata
import re

MAIN_IN = "df_main_redemption_OG_cleaned_split.xlsx"
SUMMARY_IN = "df_summary_redemption_OG_cleaned_split.xlsx"

MAIN_OUT = "df_main_redemption_OG_cleaned_split_final.xlsx"
SUMMARY_OUT = "df_summary_redemption_OG_cleaned_split_final.xlsx"


def normalize(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", s.lower())


print("📥 Betöltés...")
df_main = pd.read_excel(MAIN_IN)
df_summary = pd.read_excel(SUMMARY_IN)

print("Sorok (main):", len(df_main))
print("Sorok (summary):", len(df_summary))

# --- 1) Kerület detektálása ---
summary_norm = df_summary["Terület"].map(normalize)
mask_kerulet = summary_norm.str.contains("kerulet")  # "kerület" → "kerulet"

# --- 2) De csak akkor mozgatjuk, ha NEM mindösszesen ---
mask_not_osszeg = ~df_summary["Létszámkategória"].str.contains("Mindösszesen", case=False, na=False)

# --- 3) A két feltétel együtt ---
mask_move = mask_kerulet & mask_not_osszeg

df_move = df_summary[mask_move].copy()
df_keep = df_summary[~mask_move].copy()

print("Mozgatandó kerületi sorok:", len(df_move))
print("Summary-ben maradó sorok:", len(df_keep))

# --- 4) Main-hez adjuk hozzá ---
df_main_new = pd.concat([df_main, df_move], ignore_index=True)

# --- 5) Mentés ---
df_main_new.to_excel(MAIN_OUT, index=False)
df_keep.to_excel(SUMMARY_OUT, index=False)

print("📁 Kész!")
print("Új MAIN:", len(df_main_new), "sor")
print("Új SUMMARY:", len(df_keep), "sor")
