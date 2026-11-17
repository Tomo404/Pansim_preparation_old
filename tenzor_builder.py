import pandas as pd
import numpy as np
import json
import unicodedata
import re

MAIN = "df_main_redemption_OG_cleaned_split_finale.xlsx"
SUMMARY = "df_summary_redemption_OG_cleaned_split_finale.xlsx"


# ====================================================
# 🧹 UNICODE NORMALIZÁLÓK
# ====================================================

def normalize_text(s: str) -> str:
    """Unicode hibák javítása (ő→ö, ű→ü stb.), whitespace tisztítás."""
    if pd.isna(s):
        return ""
    s = str(s)

    # Unicode normalizáció (NFKC eltünteti a hibás latin-1 karaktereket)
    s = unicodedata.normalize("NFKC", s)

    # általános tisztítás
    s = s.replace("  ", " ").strip()

    return s


# ====================================================
# 🧩 LÉTSZÁM NORMALIZÁLÓ
# ====================================================

CANONICAL_SIZE_CATS_MAIN = [
    "1-4 fő",
    "5-9 fő",
    "10-19 fő",
    "20-49 fő",
    "50-249 fő",
    "250 fő felett"
]

CANONICAL_SIZE_CATS_SUMMARY = CANONICAL_SIZE_CATS_MAIN + ["Mindösszesen Létszámkategória"]


def normalize_size_category(cat: str, is_summary=False) -> str:
    """Létszámkategóriák egységesítése (ő/õ → fő)."""
    if pd.isna(cat):
        return ""

    cat = normalize_text(cat)

    # az összes hibás "fõ" → "fő"
    cat = cat.replace("fõ", "fő").replace("fo", "fő")

    # whitespace fix
    cat = cat.strip()

    # standard formátum
    if not is_summary:
        # main 6 kategóriája
        for c in CANONICAL_SIZE_CATS_MAIN:
            if re.sub(r"[\s\-]", "", c) == re.sub(r"[\s\-]", "", cat):
                return c
    else:
        # summary 7 kategóriája
        for c in CANONICAL_SIZE_CATS_SUMMARY:
            if re.sub(r"[\s\-]", "", c) == re.sub(r"[\s\-]", "", cat):
                return c

    return cat  # ha új kategória lenne (nem valószínű)


# ====================================================
# 🧩 DF TISZTÍTÓ
# ====================================================

def clean_df(df, is_summary=False):
    text_cols = ["Terület", "Régió", "TEÁOR főág",
                 "TEÁOR alág kód", "TEÁOR alág név", "Létszámkategória"]

    for c in text_cols:
        if c in df.columns:
            df[c] = df[c].map(normalize_text)

    df["Létszámkategória"] = df["Létszámkategória"].map(
        lambda x: normalize_size_category(x, is_summary=is_summary)
    )

    # ----  Üres kategóriák törlése ----
    df = df[df["Létszámkategória"] != ""]

    # ----  Csak a canonical kategóriák maradhatnak ----
    if not is_summary:
        valid = set(CANONICAL_SIZE_CATS_MAIN)
    else:
        valid = set(CANONICAL_SIZE_CATS_SUMMARY)

    df = df[df["Létszámkategória"].isin(valid)]

    # Érték → integer
    df["Érték"] = pd.to_numeric(df["Érték"], errors="coerce").fillna(0).astype(int)

    return df

# ====================================================
# 🧩 TENZOR ÉPÍTŐ
# ====================================================

def build_tensor(df, name, is_summary=False):
    print(f"\n==============================")
    print(f"📌 TENZOR ÉPÍTÉS: {name}")
    print(f"==============================")

    df = clean_df(df, is_summary=is_summary)

    territories = sorted(df["Terület"].unique())
    size_cats = sorted(df["Létszámkategória"].unique())
    teaor_codes = sorted(df["TEÁOR alág kód"].unique())

    print(f"➡️ Területek száma:         {len(territories)}")
    print(f"➡️ Létszámkategóriák száma: {len(size_cats)}")
    print(f"➡️ TEÁOR alágak száma:      {len(teaor_codes)}")

    # Pivot
    pivot = df.pivot_table(
        index="Terület",
        columns=["Létszámkategória", "TEÁOR alág kód"],
        values="Érték",
        fill_value=0
    )

    pivot = pivot.reindex(
        pd.MultiIndex.from_product(
            [size_cats, teaor_codes],
            names=["Létszámkategória", "TEÁOR alág kód"]
        ),
        axis=1
    )

    pivot = pivot.reindex(territories, axis=0)

    tensor = pivot.to_numpy().reshape(
        len(territories),
        len(size_cats),
        len(teaor_codes)
    )

    print(f"✅ Tenzor elkészült, shape = {tensor.shape}")

    # Mentés
    np.save(f"tensor_{name}.npy", tensor)

    dims = {
        "teruletek": territories,
        "letszamkategoriak": size_cats,
        "teaor_alagak": teaor_codes
    }

    with open(f"tensor_{name}_dimensions.json", "w", encoding="utf-8") as f:
        json.dump(dims, f, ensure_ascii=False, indent=2)

    print(f"💾 Mentve: tensor_{name}.npy + tensor_{name}_dimensions.json")

    return tensor


# ====================================================
# 🚀 FUTTATÁS
# ====================================================

print("📥 Betöltés...")

df_main = pd.read_excel(MAIN)
df_summary = pd.read_excel(SUMMARY)

print(f"MAIN sorok: {len(df_main):,}")
print(f"SUMMARY sorok: {len(df_summary):,}")

tensor_main = build_tensor(df_main, "main", is_summary=False)
tensor_summary = build_tensor(df_summary, "summary", is_summary=True)

print("\n🎉 KÉSZ! Mindkét tenzor sikeresen generálva.")
