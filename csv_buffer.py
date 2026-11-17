# merge_ab_excel_multiple.py
import pandas as pd
import csv
import glob

# --------- beállítások ----------
excel_pattern = "df_main_part_*.xlsx"  # feldolgozandó Excel részek
merged_csv = "df_main_merged.csv"  # végső kimeneti CSV
# ---------------------------------

all_csvs = []

# 1) mindegyik Excel fájl feldolgozása
for excel_file in sorted(glob.glob(excel_pattern)):
    print(f"⏳ Feldolgozás: {excel_file}")
    df = pd.read_excel(excel_file, header=0, engine="openpyxl")

    # A és B oszlopok
    colA = df.columns[0]
    colB = df.columns[1] if len(df.columns) > 1 else None


    # merge fgv: A + B, ha B üres, csak A
    def merge_ab(row):
        a = row[colA]
        b = row[colB] if colB is not None else None
        a = "" if pd.isna(a) else str(a)
        b = "" if colB is None or pd.isna(b) or str(b).strip() == "" else str(b)
        return a + b if b else a


    df["merged"] = df.apply(merge_ab, axis=1)

    # ideiglenes CSV minden részhez (utf-8-sig, ékezetek megőrzéséhez)
    temp_csv = excel_file.replace(".xlsx", ".csv")
    df[["merged"]].to_csv(temp_csv, index=False, quoting=csv.QUOTE_MINIMAL, encoding="utf-8-sig")
    all_csvs.append(temp_csv)
    print(f"✅ Mentve ideiglenes CSV-be: {temp_csv}")

# 2) összes rész CSV összevonása
merged_dfs = [pd.read_csv(f, encoding="utf-8-sig") for f in all_csvs]
final_df = pd.concat(merged_dfs, ignore_index=True)
final_df.to_csv(merged_csv, index=False, quoting=csv.QUOTE_MINIMAL, encoding="utf-8-sig")

print("🎉 Kész — végső CSV mentve:", merged_csv)
