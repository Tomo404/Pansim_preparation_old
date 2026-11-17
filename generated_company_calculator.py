import pandas as pd
from openpyxl import Workbook

# PATH-ek
paths = [
    r"C:\Users\mshco\PycharmProjects\KSH_database\generated_orgs_expected_mult_real\generated_orgs_1-4.csv",
    r"C:\Users\mshco\PycharmProjects\KSH_database\generated_orgs_expected_mult_real\generated_orgs_5-9.csv",
    r"C:\Users\mshco\PycharmProjects\KSH_database\generated_orgs_expected_mult_real\generated_orgs_10-19.csv",
    r"C:\Users\mshco\PycharmProjects\KSH_database\generated_orgs_expected_mult_real\generated_orgs_20-49.csv",
    r"C:\Users\mshco\PycharmProjects\KSH_database\generated_orgs_expected_mult_real\generated_orgs_50-249.csv",
    r"C:\Users\mshco\PycharmProjects\KSH_database\generated_orgs_expected_mult_real\generated_orgs_250-1000.csv",
]

# Betöltés
dfs = [pd.read_csv(p) for p in paths]

# Value countok (dolgozók)
#counts = [df["dolgozók"].value_counts().sort_index() for df in dfs]

# Value countok (teáor)
counts = [df["teáor"].value_counts().sort_index() for df in dfs]

# Excel létrehozása
wb = Workbook()

# Default sheet törlése
default_sheet = wb.active
wb.remove(default_sheet)

# Minden kategóriát külön sheetre írunk
for idx, cnt in enumerate(counts, start=1):
    ws = wb.create_sheet(f"cat{idx}")
    #ws.append(["dolgozók", "db"])
    ws.append(["teáor", "db"])
    for workers, db in cnt.items():
        ws.append([workers, db])

# Mentés
out = r"C:\Users\mshco\PycharmProjects\KSH_database\complete_teaor_counts.xlsx"
wb.save(out)

print("\n✔ Excel létrehozva:")
print(out)
