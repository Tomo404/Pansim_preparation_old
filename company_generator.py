import pandas as pd
import numpy as np
from pathlib import Path

# ---- PARAMÉTEREK ----

CATEGORIES = [
    ("1-4_fő.xls",          "1-4_fő_expected_mult.csv",          1,   4),
    ("5-9_fő.xls",          "5-9_fő_expected_mult.csv",          5,   9),
    ("10-19_fő.xls",        "10-19_fő_expected_mult.csv",       10,  19),
    ("20-49_fő.xls",        "20-49_fő_expected_mult.csv",       20,  49),
    ("50-249_fő.xls",       "50-249_fő_expected_mult.csv",      50, 249),
    ("250_fő_felett.xls",   "250_fő_felett_expected_mult.csv", 250, 1000),
]

INPUT_FOLDER = Path("telepules_teaor_kategoriankent")
OUT_FOLDER   = Path("generated_orgs_expected_mult_real")
OUT_FOLDER.mkdir(exist_ok=True)

ALPHA = 2   # Pareto alakparaméter


# ----------------------------------------------------------
#  TÖKÉLETESEN STABIL, HATÁRRA ILLŐ, PARETO+VARIÁNCIA GENERÁTOR
# ----------------------------------------------------------
def generate_pareto_counts(n_orgs, total_workers, amin, amax, alpha=1.4):
    """
    Tökéletesen lejtős, Pareto-súlyozott, határon belüli generátor.
    1) Pareto minták
    2) Inverz súlyok (kicsi érték kap nagy súlyt)
    3) Minimumból induló skálázás
    4) Összeg pontos finomhangolása (határbetartással)
    """

    # ---- Triviális esetek ----
    if n_orgs == 0:
        return []
    if total_workers <= amin * n_orgs:
        return [amin] * n_orgs
    if total_workers >= amax * n_orgs:
        return [amax] * n_orgs

    # ---- 1) Pareto minták ----
    raw = (np.random.pareto(alpha, n_orgs) + 1)

    # Kis zaj, de NEM túl nagy:
    raw *= np.random.uniform(0.9, 1.1, n_orgs)

    # ---- 2) Inverz Pareto súlyok (!!!) ----
    # kicsi raw → nagy súly, nagy raw → kicsi súly
    weights = 1.0 / (raw ** 3)
    weights /= weights.sum()

    # ---- 3) Minimumból induló skálázás ----
    base = np.full(n_orgs, amin, dtype=float)
    free = total_workers - amin * n_orgs
    base += weights * free

    # ---- 4) Clamp ----
    base = np.clip(base, amin, amax)

    # ---- 5) Kerekítés ----
    final = np.round(base).astype(int)

    # ---- 6) Összeg finomhangolás ----
    diff = total_workers - final.sum()

    attempts = 0
    while diff != 0 and attempts < 10000:
        for i in np.random.permutation(n_orgs):

            if diff == 0:
                break

            if diff > 0 and final[i] < amax:
                final[i] += 1
                diff -= 1
            elif diff < 0 and final[i] > amin:
                final[i] -= 1
                diff += 1

        attempts += 1

    # utolsó clamp
    final = np.clip(final, amin, amax)
    return final.tolist()

# ----------------------------------------------------------
#  FŐ CIKLUS
# ----------------------------------------------------------
for org_file, scaled_file, a, b in CATEGORIES:

    print(f"\n📥 Feldolgozás: {org_file}")

    org_path = INPUT_FOLDER / org_file
    scaled_path = INPUT_FOLDER / scaled_file

    org_df = pd.read_excel(org_path)
    scaled_df = pd.read_csv(scaled_path)

    # Normalize column names
    org_df.columns = org_df.columns.str.strip().str.lower()
    scaled_df.columns = scaled_df.columns.str.strip().str.lower()

    # rename dolgozók → dolgozók_scaled
    if "dolgozók" in scaled_df.columns:
        scaled_df.rename(columns={"dolgozók": "dolgozók_scaled"}, inplace=True)
    if "dolgozok" in scaled_df.columns:
        scaled_df.rename(columns={"dolgozok": "dolgozók_scaled"}, inplace=True)

    # remove darab if accidentally in scaled file
    if "darab" in scaled_df.columns:
        scaled_df = scaled_df.drop(columns=["darab"])

    # merge
    merged = org_df.merge(
        scaled_df,
        on=["település", "teáor"],
        how="inner"
    )

    print(merged.head())
    print(merged.columns)

    out_rows = []

    for _, row in merged.iterrows():
        telep = row["település"]
        teaor = row["teáor"]
        n_orgs = int(row["darab"])
        total_workers = int(row["dolgozók_scaled"])

        generated = generate_pareto_counts(
            n_orgs=n_orgs,
            total_workers=total_workers,
            amin=a,
            amax=b
        )

        for w in generated:
            out_rows.append([telep, teaor, w])

    out_df = pd.DataFrame(out_rows, columns=["település", "teáor", "dolgozók"])

    out_name = f"generated_orgs_{a}-{b}.csv"
    out_df.to_csv(OUT_FOLDER / out_name, index=False, encoding="utf-8-sig")

    print(f"💾 Generált szervezetek mentve: {out_name}")

print("\n✅ MINDEN KATEGÓRIA KÉSZ – stabil, határon belüli, Pareto-random elosztás létrehozva!")
