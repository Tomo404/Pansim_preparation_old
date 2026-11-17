# district_mover_megye.py
import pandas as pd
import unicodedata
import re

MAIN_IN = "df_main_redemption_OG_cleaned_split_final.xlsx"
SUMMARY_IN = "df_summary_redemption_OG_cleaned_split_final.xlsx"

MAIN_OUT = "df_main_redemption_OG_cleaned_split_finale.xlsx"
SUMMARY_OUT = "df_summary_redemption_OG_cleaned_split_finale.xlsx"


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

# ============================
# 1️⃣ Normalizált területnév
# ============================
summary_norm = df_summary["Terület"].map(normalize)

# ============================
# 2️⃣ Megye települések detektálása
# Feltétel: tartalmazza "megye" → de NEM tartalmazza "varmegye"
# ============================
mask_megye = summary_norm.str.contains("megye")
mask_varmegye = summary_norm.str.contains("varmegye")

mask_fake_megye = mask_megye & ~mask_varmegye  # <-- Bábonymegyer, Megyer, Megyehíd stb.

# ============================
# 3️⃣ Mindösszesen létszám maradjon SUMMARY-ben!
# ============================
mask_not_osszeg = ~df_summary["Létszámkategória"].str.contains(
    "Mindösszesen", case=False, na=False
)

# ============================
# 4️⃣ Mozgatandó sorok: fake megye ÉS nem mindösszesen
# ============================
mask_move = mask_fake_megye & mask_not_osszeg

df_move = df_summary[mask_move].copy()
df_keep = df_summary[~mask_move].copy()

print("Mozgatandó településsorok:", len(df_move))
print("Summary-ben maradó sorok:", len(df_keep))

# ============================
# 5️⃣ Hozzáadjuk a MAIN-hez
# ============================
df_main_new = pd.concat([df_main, df_move], ignore_index=True)

# ============================
# 6️⃣ Mentés
# ============================
df_main_new.to_excel(MAIN_OUT, index=False)
df_keep.to_excel(SUMMARY_OUT, index=False)

print("📁 Kész!")
print("Új MAIN:", len(df_main_new), "sor")
print("Új SUMMARY:", len(df_keep), "sor")
