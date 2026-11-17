import os
import re
import pandas as pd
from openpyxl import load_workbook

# --- KONFIG ---
FOLDER = r"C:\Users\mshco\Desktop\KSH_adathalmaz\filled_corrected_merged"

REGIOK = [
    "Közép-Magyarország", "Közép-Dunántúl", "Nyugat-Dunántúl",
    "Dél-Dunántúl", "Észak-Magyarország", "Észak-Alföld", "Dél-Alföld"
]
REGION_RE = re.compile("|".join([re.escape(r) for r in REGIOK]), re.I)
MEGYE_RE = re.compile(r"\b(vármegye|megye|főváros)\b", re.I)
JARAS_RE = re.compile(r"\b(járás|kerület)\b", re.I)
OSSZESEN_RE = re.compile(r"(összesen|mindösszesen)", re.I)
# --- /KONFIG ---


def extract_by_7block_keep_empty(folder):
    main_rows, summary_rows = [], []

    for fname in sorted(os.listdir(folder)):
        if not fname.endswith(".xlsx"):
            continue

        wb = load_workbook(os.path.join(folder, fname), data_only=True)
        print(f"\n📄 Fájl feldolgozása: {fname}")

        for sheet in wb.sheetnames:
            ws = wb[sheet]
            teaor_cols = [
                c for c in range(3, ws.max_column + 1)
                if ws.cell(row=11, column=c).value not in (None, "")
            ]
            if not teaor_cols:
                continue

            prev_a, prev_b = "", ""
            file_summary_count = 0
            file_detail_count = 0
            row = 12

            while row <= ws.max_row:
                # 🟢 Első sor a blokkban
                a_val = ws.cell(row=row, column=1).value
                b_val = ws.cell(row=row, column=2).value

                # öröklés már itt megtörténik
                a_str = str(a_val).strip() if a_val else prev_a
                b_str = str(b_val).strip() if b_val else prev_b

                # teljesen üres blokk esetén kilép
                if not a_str and not b_str:
                    break

                # frissítjük az örökölt értékeket
                prev_a, prev_b = a_str, b_str

                # megye/régió/járás/mindösszesen felismerése
                is_territorial = bool(
                    REGION_RE.search(a_str)
                    or MEGYE_RE.search(a_str)
                    or JARAS_RE.search(a_str)
                    or OSSZESEN_RE.search(a_str)
                )

                # 🟨 blokk feldolgozása
                for i in range(7):
                    current_row = row + i
                    if current_row > ws.max_row:
                        break

                    a_cur = ws.cell(row=current_row, column=1).value
                    b_cur = ws.cell(row=current_row, column=2).value

                    # ha üres, örököljük a blokk elejétől
                    if not a_cur:
                        a_cur = a_str
                    if not b_cur:
                        b_cur = b_str

                    a_cur = str(a_cur).strip()
                    b_cur = str(b_cur).strip()

                    for c in teaor_cols:
                        val = ws.cell(row=current_row, column=c).value
                        if val is None:
                            continue

                        record = {
                            "file": fname,
                            "sheet": sheet,
                            "row": current_row,
                            "A_raw": a_cur,
                            "B_raw": b_cur,
                            "teaor_sub": ws.cell(row=11, column=c).value,
                            "value": val,
                        }

                        # az első sor és a területi szint summary
                        if i == 0 or is_territorial:
                            record["is_summary"] = True
                            summary_rows.append(record)
                            file_summary_count += 1
                        else:
                            record["is_summary"] = False
                            main_rows.append(record)
                            file_detail_count += 1

                row += 7

            print(f"  → Lap: {sheet:25s} | Részletes: {file_detail_count:6d} | Összesített: {file_summary_count:6d}")

    import re

    # --- Területi hierarchia detektor ---
    REGIOK = [
        "Közép-Magyarország", "Közép-Dunántúl", "Nyugat-Dunántúl",
        "Dél-Dunántúl", "Észak-Magyarország", "Észak-Alföld", "Dél-Alföld"
    ]

    def hierarchikus_teruleti_kitoltes(df):
        """Kitölti a region / county / district / city oszlopokat a A_raw alapján."""
        region, county, district = None, None, None

        region_re = re.compile("|".join(REGIOK), re.I)
        county_re = re.compile(r"\b(vármegye|megye|főváros)\b", re.I)
        district_re = re.compile(r"\b(járás|kerület)\b", re.I)

        regions, counties, districts, cities = [], [], [], []

        for val in df["A_raw"]:
            text = str(val).strip() if val else ""

            # Régió felismerése
            if region_re.search(text):
                region = next((r for r in REGIOK if r.lower() in text.lower()), region)
                county, district = None, None  # új hierarchia kezdődik

            # Megye / főváros
            elif county_re.search(text):
                county = text
                district = None

            # Járás / kerület
            elif district_re.search(text):
                district = text

            # Település
            elif text:
                city = text
            else:
                city = None

            regions.append(region)
            counties.append(county)
            districts.append(district)
            cities.append(city)

        df["region"] = regions
        df["county_or_capital"] = counties
        df["district_or_budapest_district"] = districts
        df["city"] = cities

        return df

    al_df_main = pd.DataFrame(main_rows)
    al_df_summary = pd.DataFrame(summary_rows)

    print("\n🧩 Területi hierarchia hozzáadása...")

    df_main = hierarchikus_teruleti_kitoltes(al_df_main)
    df_summary = hierarchikus_teruleti_kitoltes(al_df_summary)

    print("✅ Területi mezők kitöltve (region, county_or_capital, district_or_budapest_district, city)")

    print("\n📊 Összesítés (globális):")
    print(f"  → Részletes rekordok: {len(df_main):,}")
    print(f"  → Összesített rekordok: {len(df_summary):,}")
    print("\n🔎 Minta a részletesből:")
    print(df_main.head(15))
    print("\n🔎 Minta az összesítettből:")
    print(df_summary.head(15))

    return df_main, df_summary


if __name__ == "__main__":
    df_main, df_summary = extract_by_7block_keep_empty(FOLDER)

    # 💾 Mentés pickle-be, hogy ne kelljen újra beolvasni legközelebb
    df_main.to_pickle("df_main.pkl")
    df_summary.to_pickle("df_summary.pkl")

    print("\n✅ Mentés kész: df_main.pkl és df_summary.pkl létrehozva.")