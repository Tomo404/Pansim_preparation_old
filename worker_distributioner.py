import numpy as np
import pandas as pd
from pathlib import Path
from final_redemption_api import load_tensor   # innen jön a tensor betöltése

OUTPUT_DIR = Path("telepules_teaor_kategoriankent")
OUTPUT_DIR.mkdir(exist_ok=True)

print("📥 Tenzor betöltése (main)...")
tensor, dims, _, _, _ = load_tensor("main")

territories = dims["teruletek"]          # 3177 település
size_cats   = dims["letszamkategoriak"]  # 6 kategória
teaor_codes = dims["teaor_alagak"]       # 86 TEÁOR

tensor = tensor.astype(int)

print("📊 Település × TEÁOR × Létszámkategória mátrix alakja:", tensor.shape)
# shape = (3177, 6, 86)

# =====================================================
#  KATEGÓRIÁNKÉNT 6 DATAFRAME LÉTREHOZÁSA
# =====================================================

for size_idx, size_name in enumerate(size_cats):

    print(f"➡️  Feldolgozás: {size_name}")

    # tensor[:, size_idx, :]  -> shape = (3177, 86)
    data = tensor[:, size_idx, :]

    df = pd.DataFrame(
        data,
        index=territories,
        columns=teaor_codes
    )

    # Lapított táblázat → település, TEÁOR, érték
    df_melt = (
        df.reset_index()
          .melt(id_vars="index", var_name="TEÁOR", value_name="darab")
          .rename(columns={"index": "település"})
    )

    # Kihagyjuk ahol 0 darab van (opcionális)
    df_melt = df_melt[df_melt["darab"] > 0]

    out_file = OUTPUT_DIR / f"{size_name.replace(' ', '_')}.csv"
    df_melt.to_csv(out_file, index=False, encoding="utf-8")

    print(f"   ✔️ Mentve: {out_file}")

print("\n🎉 KÉSZ! Mind a 6 létszámkategória exportálva.")
