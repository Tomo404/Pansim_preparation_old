import pandas as pd
import numpy as np
from pathlib import Path

EXPECTEDS = np.array([1.89, 6.64, 13.62, 30.58, 103.63, 473.09])
SCALE = 0.5483922140641009

INPUT_FOLDER = Path("telepules_teaor_kategoriankent")
OUTPUT_SUFFIX = "_expected_mult"

TABLES = [
    "1-4_fő.xls",
    "5-9_fő.xls",
    "10-19_fő.xls",
    "20-49_fő.xls",
    "50-249_fő.xls",
    "250_fő_felett.xls"
]

for i, fname in enumerate(TABLES):
    path = INPUT_FOLDER / fname
    print("📥 Betöltés:", fname)

    df = pd.read_excel(path)

    # Ellenőrizzük, hogy benne van-e a “darab” oszlop
    if "darab" not in df.columns:
        raise ValueError(f"Nincs 'darab' oszlop a fájlban: {fname}")

    expected_value = EXPECTEDS[i]

    # Skálázott dolgozók (összdolgozó becslés kategóriánként)
    df["dolgozók"] = (df["darab"] * expected_value).round().astype(int)

    # Mentés CSV-be
    out_name = fname.replace(".xls", f"{OUTPUT_SUFFIX}.csv")
    df.to_csv(INPUT_FOLDER / out_name, index=False, encoding="utf-8-sig")

    print("💾 Mentve →", out_name)

print("\n✅ Minden scaled tábla kész!")
