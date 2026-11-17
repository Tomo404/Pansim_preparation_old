import os
from openpyxl import load_workbook

# --- KONFIG ---
SOURCE_FOLDER = r"C:\Users\mshco\Desktop\KSH_adathalmaz\corrected_merged"
TARGET_FOLDER = r"C:\Users\mshco\Desktop\KSH_adathalmaz\KSH_halmaz"

# ha a célmappa nem létezik, létrehozzuk
os.makedirs(TARGET_FOLDER, exist_ok=True)

def fill_missing_cells():
    files = [f for f in os.listdir(SOURCE_FOLDER) if f.endswith(".xlsx")]

    for fname in files:
        src_path = os.path.join(SOURCE_FOLDER, fname)
        tgt_path = os.path.join(TARGET_FOLDER, fname.replace(".xlsx", "_filled.xlsx"))

        wb = load_workbook(src_path)
        print(f"\n📄 Fájl feldolgozása: {fname}")

        for sheetname in wb.sheetnames:
            ws = wb[sheetname]
            print(f"  → Lap: {sheetname}")

            row = 12  # adatsorok kezdete
            col_start = 3  # C oszlop
            changes = 0
            filled_rows = 0

            while True:
                b_val = ws.cell(row=row, column=2).value
                if b_val is None or str(b_val).strip() == "":
                    # ha a B oszlopban nincs szöveg, leállunk
                    break

                # végigmegyünk az összes teáor oszlopon
                for col in range(col_start, ws.max_column + 1):
                    cell = ws.cell(row=row, column=col)
                    val = cell.value

                    # ha üres (None vagy ""), 0-t írunk bele
                    if val is None or val == "":
                        cell.value = 0
                        changes += 1

                filled_rows += 1
                row += 1

            print(f"    → Kitöltött sorok: {filled_rows:5d} | Pótolt cellák: {changes:6d}")

        wb.save(tgt_path)
        print(f"✅ Mentve ide: {tgt_path}")

if __name__ == "__main__":
    fill_missing_cells()