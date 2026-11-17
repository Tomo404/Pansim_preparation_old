# normalize_and_enrich.py
import re
import os
import pandas as pd

# --- Konfiguráció (szükség szerint módosítható) ---
MAIN_PICKLE = "df_main.pkl"
SUMMARY_PICKLE = "df_summary.pkl"

OUT_MAIN_PICKLE = "df_main_enriched.pkl"
OUT_SUMMARY_PICKLE = "df_summary_enriched.pkl"

# Régiók (ugyanaz, mint amit használsz)
REGIOK = [
    "Közép-Magyarország", "Közép-Dunántúl", "Nyugat-Dunántúl",
    "Dél-Dunántúl", "Észak-Magyarország", "Észak-Alföld", "Dél-Alföld"
]
REGION_RE = re.compile("|".join([re.escape(r) for r in REGIOK]), re.I)
MEGYE_RE = re.compile(r"\b(vármegye|megye|főváros)\b", re.I)
JARAS_RE = re.compile(r"\b(járás|kerület)\b", re.I)
OSSZESEN_RE = re.compile(r"(összesen|mindösszesen)", re.I)

# próbáljuk importálni a teaor mappinget a builderből (ha elérhető)
teaor_rev = {}
try:
    from structure import teaor as teaor_map  # ha builder.py-ban van a dict
    for main_k, main_v in teaor_map.items():
        subs = main_v.get("sub", {})
        for sub_k in subs.keys():
            teaor_rev[sub_k.zfill(2)] = main_k  # '01' -> 'A'
    print("→ TEÁOR mapping betöltve a builderből (teaor_rev kész).")
except Exception:
    # ha nincs builder import, teaor_rev marad üres; nem végzünk main-kategória hozzárendelést
    print("→ Nem sikerült importálni a teaor mappinget a builderből; teaor_main nem lesz feltöltve.")

# regex a teaor mező feldarabolásához
TEAOR_RE = re.compile(r'^\s*([A-Za-z]?)(\d{2})(?:\s*==\s*)?(.*)$')

def enrich_df(df, assumed_file_region=True):
    """
    Visszatér egy új DataFrame-el, amelyben:
      - region, county_or_capital, district_or_budapest_district, city, size_cat
        mezők vannak kinyerve / örökítve file+sheet csoporton belül
      - teaor_sub_code, teaor_desc, teaor_main mezők készülnek a teaor_sub alapján
    assumed_file_region: ha True, megpróbáljuk a file név alapján is kitalálni a régiót
    """
    enriched_rows = []
    # rendezés biztonságosan, ha nincs row oszlop, rendezd index alapján
    if "row" not in df.columns:
        df = df.reset_index().rename(columns={"index": "row"})

    groups = df.groupby(["file", "sheet"], sort=False)
    total_groups = len(groups)
    print(f"→ Feldolgozás: {total_groups} file+sheet csoport...")

    for (fname, sheet), g in groups:
        g_sorted = g.sort_values("row", kind="stable", ascending=True)
        # kezdeti örökölt értékek: próbáljuk kitalálni a régiót a fájlnévből, ha lehet
        prev_region = None
        if assumed_file_region and isinstance(fname, str):
            lowfn = fname.lower()
            for r in REGIOK:
                if r.replace("-", "_").lower() in lowfn or r.lower() in lowfn:
                    prev_region = r
                    break

        prev_county = None
        prev_district = None
        prev_city = None
        prev_size = None

        # iteráljunk tuple-okon (gyorsabb, mint .loc soronként)
        for t in g_sorted.itertuples(index=False):
            # t._asdict() nem mindig van, úgyhogy használjuk attribútumokat
            a_raw = getattr(t, "A_raw", "") or ""
            b_raw = getattr(t, "B_raw", "") or ""
            teaor_sub = getattr(t, "teaor_sub", "") or ""
            value = getattr(t, "value", None)
            rownum = getattr(t, "row", None)

            a_str = str(a_raw).strip()
            b_str = str(b_raw).strip()

            a_low = a_str.lower()
            b_low = b_str.lower()

            # 1) ha a sor tartalmaz régiót, frissítjük
            region_found = None
            if a_str:
                # közvetlen régió felismerés
                for r in REGIOK:
                    if r.lower() in a_low:
                        region_found = r
                        break

            if region_found:
                prev_region = region_found
                prev_county = prev_district = prev_city = None
            else:
                # 2) ha megye vagy főváros szó van benne → county
                if a_str and MEGYE_RE.search(a_str):
                    prev_county = a_str
                    prev_district = prev_city = None
                # 3) ha járás/kerület
                elif a_str and JARAS_RE.search(a_str):
                    prev_district = a_str
                    prev_city = None
                # 4) ha "összesen" (pl település összegezve) — ne cseréljük a települést, hagyjuk prev értéket
                elif a_str and OSSZESEN_RE.search(a_low):
                    # nem változtatunk hierarchiát; csak fontos lehet is_summary szempontból
                    pass
                # 5) egyéb: feltételezzük, hogy település neve (ha nem üres)
                elif a_str:
                    prev_city = a_str

            # size_cat
            if b_str:
                prev_size = b_str

            # TEÁOR parse
            teaor_code = None
            teaor_desc = None
            teaor_main = None
            ts = str(teaor_sub).strip()
            if ts:
                m = TEAOR_RE.match(ts)
                if m:
                    letter = m.group(1) or ""
                    code = m.group(2) or ""
                    desc = m.group(3) or ""
                    teaor_code = code.zfill(2)
                    teaor_desc = desc.strip()
                    if letter:
                        teaor_main = letter.upper()
                    else:
                        if teaor_code in teaor_rev:
                            teaor_main = teaor_rev.get(teaor_code)
                else:
                    # ha nem illeszkedik, próbáljuk kiválasztani az első 2 számjegyet
                    m2 = re.search(r'(\d{2})', ts)
                    if m2:
                        teaor_code = m2.group(1)
                        # leírás: minden, ami a code után jön
                        rest = ts.split(m2.group(1), 1)[-1]
                        teaor_desc = rest.strip().lstrip("=-: ")
                        if teaor_code in teaor_rev:
                            teaor_main = teaor_rev.get(teaor_code)
                    else:
                        teaor_desc = ts

            # ha nincs teaor_code, hagyjuk None — lehet, hogy vannak summary sorok, ahol nincs TEÁOR
            rec = {
                "file": fname,
                "sheet": sheet,
                "row": rownum,
                "A_raw": a_raw,
                "B_raw": b_raw,
                "region": prev_region,
                "county_or_capital": prev_county,
                "district_or_budapest_district": prev_district,
                "city": prev_city,
                "size_cat": prev_size,
                "teaor_sub_raw": teaor_sub,
                "teaor_sub_code": teaor_code,
                "teaor_desc": teaor_desc,
                "teaor_main": teaor_main,
                "value": value,
                # ha van eredeti is_summary mező, használjuk; különben False (de ezt a pickleből tudod)
                "is_summary": getattr(t, "is_summary", False),
            }
            enriched_rows.append(rec)

    df_enriched = pd.DataFrame(enriched_rows)
    # kis típusigazítás:
    # a value-t számként próbáljuk értelmezni
    df_enriched["value"] = pd.to_numeric(df_enriched["value"], errors="coerce").fillna(0).astype(int)

    return df_enriched

def main():
    # beolvassuk a picklekeket (ha nem léteznek, jelezzük)
    if not os.path.exists(MAIN_PICKLE) or not os.path.exists(SUMMARY_PICKLE):
        print("Hiba: nem találom a pickle fájlokat a beállított elérési útvonalon.")
        print("Győződj meg róla, hogy a df_main.pkl és df_summary.pkl a script mappájában van (vagy módosítsd a MAIN_PICKLE, SUMMARY_PICKLE útvonalat).")
        return

    print("Picklek betöltése...")
    df_main = pd.read_pickle(MAIN_PICKLE)
    df_summary = pd.read_pickle(SUMMARY_PICKLE)
    print(f"Betöltve: {len(df_main):,} részletes sor, {len(df_summary):,} összesített sor.")

    print("\n→ Enrich main...")
    df_main_enr = enrich_df(df_main, assumed_file_region=True)
    print("→ Enrich summary...")
    df_sum_enr = enrich_df(df_summary, assumed_file_region=True)

    # mentsük el új pickle-ként
    print(f"Mentés: {OUT_MAIN_PICKLE}, {OUT_SUMMARY_PICKLE} ...")
    df_main_enr.to_pickle(OUT_MAIN_PICKLE)
    df_sum_enr.to_pickle(OUT_SUMMARY_PICKLE)

    # rövid ellenőrzés
    print("\n🔎 Példa (main):")
    print(df_main_enr.head(12).to_string(index=False))
    print("\n🔎 Unique teaor_main (példa):")
    print(df_main_enr["teaor_main"].dropna().unique()[:30])

    # opcionálisan CSV (nagy fájloknál lassú és sok helyet foglal!)
    # df_main_enr.to_csv("df_main_enriched.csv", index=False)
    # df_sum_enr.to_csv("df_summary_enriched.csv", index=False)

    print("\nKész. A feldolgozott fájlok mentve.")

if __name__ == "__main__":
    main()