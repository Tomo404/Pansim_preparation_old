import pandas as pd
import os

BASE = r"C:\Users\mshco\Desktop\KSH_adathalmaz"
INPUT_FOLDER = os.path.join(BASE, "merged")
OUTPUT_FOLDER = os.path.join(BASE, "corrected_merged")

LETSZAM = ["1-4 fő", "5-9 fő", "10-19 fő", "20-49 fő", "50-249 fő", "250 fő felett"]

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

print("🚀 Településenkénti létszámkategória-kiegészítés indítása...")

for file in os.listdir(INPUT_FOLDER):
    if not file.endswith(".xlsx"):
        continue

    in_path = os.path.join(INPUT_FOLDER, file)
    out_path = os.path.join(OUTPUT_FOLDER, file)
    xls = pd.ExcelFile(in_path)

    print(f"\n📄 Feldolgozás: {file}")

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        for sheet in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet, header=None)

            # Ellenőrizzük, hogy tényleg adatlapon vagyunk-e
            if df.shape[1] < 3:
                continue

            # 11 fejlécsor, utána az adatok
            header = df.iloc[:11]
            data = df.iloc[11:].copy()
            data.columns = range(data.shape[1])

            # Az eredmény tárolására
            new_data_rows = []

            # Egyedi települések (az 1. oszlop = A)
            city_names = data.iloc[:, 0].ffill().unique()

            total_added = 0

            for city in city_names:
                city_rows = data[data.iloc[:, 0].ffill() == city]
                if city_rows.empty:
                    continue

                # Létező kategóriák
                existing = set(str(x).strip() for x in city_rows.iloc[:, 1].dropna())
                missing = [cat for cat in LETSZAM if cat not in existing]

                new_data_rows.append(city_rows)

                if missing:
                    base_row = city_rows.iloc[0].copy()
                    for m in missing:
                        new_row = base_row.copy()
                        new_row.iloc[1] = m  # létszámkategória
                        for c in range(2, len(new_row)):
                            new_row.iloc[c] = 0
                        new_data_rows.append(pd.DataFrame([new_row]))
                        total_added += 1

            # Összefűzés az eredeti sorrend megtartásával
            corrected = pd.concat(new_data_rows, ignore_index=True)
            final_df = pd.concat([header, corrected], ignore_index=True)

            final_df.to_excel(writer, sheet_name=sheet, index=False, header=False)
            print(f"  → Lap: {sheet} kész ✅  Új sorok beszúrva: {total_added}")

print("\n✅ Minden fájl kiegészítve és mentve a corrected_merged mappába!")
