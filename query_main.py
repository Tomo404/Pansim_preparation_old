import pandas as pd
import unicodedata

# --- Betöltés ---
df_main = pd.read_pickle("df_main_enriched.pkl")
df_summary = pd.read_pickle("df_summary_enriched.pkl")

print(f"✅ Betöltve: {len(df_main):,} részletes sor, {len(df_summary):,} összesített sor")

def normalize(s):
    """Egyszerű szövegtisztítás: kisbetű, space levágás, ékezetek eltávolítása."""
    if pd.isna(s):
        return ""
    s = str(s).strip().lower()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return s

for df in (df_main, df_summary):
    df["city_norm"] = df["city"].map(normalize)

# Normalizált oszlopok létrehozása
for df in (df_main, df_summary):
    for col in ["region", "county_or_capital", "district_or_budapest_district", "city", "size_cat", "teaor_main", "teaor_sub_code"]:
        if col in df.columns:
            df[col + "_norm"] = df[col].map(normalize)

def interaktiv_lekerdezes():
    print("\n💡 Tipp: A 'main' adatbázis településszintű, a 'summary' járás / megye / régió szintű adatokat tartalmaz.\n")
    db_choice = input("Melyik adatbázisból szeretnél lekérdezni? (main/summary): ").strip().lower()
    df = df_main if db_choice == "main" else df_summary

    # 1️⃣ TEÁOR fő kategória
    teakor = input("Add meg a TEÁOR fő kategóriát (A–T vagy minden): ").strip().upper()
    if teakor != "MINDEN":
        df = df[df["teaor_main_norm"] == teakor.lower()]
        print(f"➡️ Szűrés TEÁOR fő kategóriára: {teakor} → {len(df)} sor maradt")

    # 2️⃣ TEÁOR alkategória
    alk = input("Add meg a TEÁOR alkategóriát (pl. 01, 02... vagy minden): ").strip()
    if alk.lower() != "minden":
        df = df[df["teaor_sub_code_norm"].str.startswith(alk.lower(), na=False)]
        print(f"➡️ Szűrés TEÁOR alkategóriára: {alk} → {len(df)} sor maradt")

    # 3️⃣ Létszámkategória
    letszam = input("Add meg a létszámkategóriát (pl. 1-4 fő, 5-9 fő, minden): ").strip().lower()
    if letszam != "minden":
        df = df[df["size_cat_norm"].str.contains(letszam.replace(" ", ""), na=False)]
        print(f"➡️ Szűrés létszámra: {letszam} → {len(df)} sor maradt")

    # 4️⃣ Területi szűrés (csak ha az oszlop létezik)
    if "region_norm" in df.columns and db_choice == "summary":
        regio = input("Add meg a régiót (pl. Dél-Alföld, minden): ").strip().lower()
        if regio != "minden":
            df = df[df["region_norm"].str.contains(regio, na=False)]
            print(f"➡️ Szűrés régióra: {regio} → {len(df)} sor maradt")

    if "county_or_capital_norm" in df.columns and db_choice == "summary":
        megye = input("Add meg a megyét/fővárost (pl. Bács-Kiskun, minden): ").strip().lower()
        if megye != "minden":
            df = df[df["county_or_capital_norm"].str.contains(megye, na=False)]
            print(f"➡️ Szűrés megyére: {megye} → {len(df)} sor maradt")

    if "district_or_budapest_district_norm" in df.columns and db_choice == "summary":
        jaras = input("Add meg a járást/kerületet (pl. Bajai, minden): ").strip().lower()
        if jaras != "minden":
            df = df[df["district_or_budapest_district_norm"].str.contains(jaras, na=False)]
            print(f"➡️ Szűrés járásra: {jaras} → {len(df)} sor maradt")

    if "city_norm" in df.columns and db_choice == "main":
        telepules = input("Add meg a települést (pl. Baja, minden): ").strip().lower()
        if telepules != "minden":
            telepules_norm = normalize(telepules)
            df = df[df["city_norm"] == telepules_norm]
            print(f"➡️ Szűrés településre: {telepules_norm} → {len(df)} sor maradt")

    # --- Eredmény ---
    if df.empty:
        print("\n❌ Nincs találat a megadott szűrésre.")
        return

    osszeg = df["value"].sum()
    pd.set_option("display.max_rows", None)
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 0)
    print(f"\n📊 Találatok száma: {len(df):,}")
    print(f"Σ Összesített érték: {osszeg:,}")
    print(df[["region", "county_or_capital", "district_or_budapest_district", "city", "teaor_main", "teaor_sub_code", "size_cat", "value"]])

if __name__ == "__main__":
    interaktiv_lekerdezes()