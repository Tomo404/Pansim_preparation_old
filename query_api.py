# query_api.py
import pandas as pd
from typing import Optional, Union, Dict

# --- Betöltés ---
df_main = pd.read_pickle("df_main_enriched.pkl")
df_summary = pd.read_pickle("df_summary_enriched.pkl")

def normalize(s: str) -> str:
    import unicodedata
    if pd.isna(s): return ""
    s = str(s).strip().lower()
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')

for df in (df_main, df_summary):
    for col in ["region", "county_or_capital", "district_or_budapest_district", "city",
                "size_cat", "teaor_sub_code", "teaor_main"]:
        df[col + "_norm"] = df[col].map(normalize)

def get_data(
    db: str = "main",
    teaor_main: Optional[str] = None,
    teaor_sub: Optional[str] = None,
    size_cat: Optional[str] = None,
    region: Optional[str] = None,
    county: Optional[str] = None,
    district: Optional[str] = None,
    city: Optional[str] = None,
    aggregate: bool = False
) -> Union[pd.DataFrame, Dict[str, int]]:
    """Lekérdezés API: paraméterek alapján visszaadja a szűrt adatokat vagy aggregált összesítést."""

    df = df_main if db == "main" else df_summary

    if teaor_main and teaor_main.lower() != "minden":
        df = df[df["teaor_main_norm"] == normalize(teaor_main)]

    if teaor_sub and teaor_sub.lower() != "minden":
        df = df[df["teaor_sub_code_norm"] == normalize(teaor_sub)]

    if size_cat and size_cat.lower() != "minden":
        df = df[df["size_cat_norm"] == normalize(size_cat)]

    if city and city.lower() != "minden":
        df = df[df["city_norm"] == normalize(city)]
    elif district and district.lower() != "minden":
        df = df[df["district_or_budapest_district_norm"] == normalize(district)]
    elif county and county.lower() != "minden":
        df = df[df["county_or_capital_norm"] == normalize(county)]
    elif region and region.lower() != "minden":
        df = df[df["region_norm"] == normalize(region)]

    if aggregate:
        return df.groupby("size_cat")["value"].sum().to_dict()

    return df

# 1️⃣ Egyszerű lekérdezés
df = get_data(db="main", city="Bácsalmás", teaor_main="A", teaor_sub="01")
print(df.head())

# 2️⃣ Összesített, létszám szerinti bontás
agg = get_data(db="main", city="Bácsalmás", teaor_main="A", aggregate=True)
print(agg)
# → {'1-4 fő': 15, '5-9 fő': 7, '10-19 fő': 2}

pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 0)
print(df[["region", "county_or_capital", "district_or_budapest_district", "city", "teaor_main", "teaor_sub_code", "size_cat", "value"]])