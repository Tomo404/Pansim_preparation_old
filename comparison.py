# comparison.py
import pandas as pd
import numpy as np

PARETO_FILE = "teaor_becsult_dolgozok_pareto.xlsx"
KSH_FILE = "Havi_kereseti.xlsx"
OUTPUT = "teaor_normalizalt_letszam.xlsx"

# Pareto várható értékek (fixek)
EXPECTEDS = np.array([1.89, 6.64, 13.62, 30.58, 103.57, 348.62])
CATS = ["1-4 fő", "5-9 fő", "10-19 fő", "20-49 fő", "50-249 fő", "250-500 fő"]


print("📥 Pareto TEÁOR becslések betöltése...")
df = pd.read_excel(PARETO_FILE)

print("📥 KSH országos dolgozószám kinyerése...")
ksh_df = pd.read_excel(KSH_FILE)

# H95 cella → 0-index: row 94, col 7
KSH_total = 3761131
print("🔢 KSH országos összes dolgozó:", KSH_total)

# Pareto országos összes
estimated_total = df["Becsült_létszám"].sum()
print("🔢 Pareto országos összes becsült dolgozó:", estimated_total)

# Normalizáló arány
ratio = KSH_total / estimated_total
print("📉 Normalizációs arány:", ratio)


print("📊 Normalizált 6 kategóriás értékek számítása...")
counts = df[CATS].values  # shape (n,6)

# Minden cellára: darabszám * pareto-várható * ratio
normalized_matrix = counts * EXPECTEDS * ratio

# Új oszlopok
for i, cat in enumerate(CATS):
    df[f"Norm_{cat}"] = normalized_matrix[:, i]

# Összes dolgozó teáoronként
df["Norm_total"] = normalized_matrix.sum(axis=1).astype(int)

print("💾 Mentés Excelbe...")
df.to_excel(OUTPUT, index=False)

print("✅ Kész:", OUTPUT)
