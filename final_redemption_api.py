import numpy as np
import json
import unicodedata
from typing import List, Tuple, Union, Optional
from structure import teaor as TEAOR_STRUCT


# ==========================================================
# 🎯 0. Normalizáló segédfüggvény
# ==========================================================
def norm(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.lower().strip()


# ==========================================================
# 🎯 1. Tenzor + dimenziók betöltése
# ==========================================================
def load_tensor(db="main"):
    tensor = np.load(f"tensor_{db}.npy")

    with open(f"tensor_{db}_dimensions.json", "r", encoding="utf-8") as f:
        dims = json.load(f)

    territories = dims["teruletek"]
    size_cats = dims["letszamkategoriak"]
    teaor_codes = dims["teaor_alagak"]

    # normalizált lookup
    terr_norm = {norm(t): t for t in territories}
    size_norm = {norm(s): s for s in size_cats}
    alag_norm = {norm(a): a for a in teaor_codes}

    return tensor, dims, terr_norm, size_norm, alag_norm


# ==========================================================
# 🎯 2. TEÁOR főág → alágak listája
# ==========================================================
def expand_teaor_main(main_code: str) -> List[str]:
    main_code = main_code.upper().strip()
    if main_code not in TEAOR_STRUCT:
        return []

    subs = list(TEAOR_STRUCT[main_code]["sub"].keys())
    return [s.lstrip("0") for s in subs]    # 01 → 1


# ==========================================================
# 🎯 3. Területi típus felismerése (summary db-hez)
# ==========================================================
REGIOK = [
    "Közép-Magyarország", "Közép-Dunántúl", "Nyugat-Dunántúl",
    "Dél-Dunántúl", "Észak-Magyarország", "Észak-Alföld", "Dél-Alföld"
]
REGIO_NORM = [norm(r) for r in REGIOK]


def classify_summary_territory(t: str) -> str:
    s = norm(t)

    if "mindosszesen" in s:
        return "mindosszesen"
    if "jaras" in s:
        return "jaras"
    if "megye" in s:
        return "megye"
    if "kerulet" in s or "ker." in s:
        return "kerulet"
    if any(r in s for r in REGIO_NORM):
        return "regio"

    return "egyeb"


# ==========================================================
# 🎯 4. ÚJ, BŐVÍTETT LEKÉRDEZŐ (többdimenziós aggregációval)
# ==========================================================
def query(
    territory: Optional[str] = None,
    teaor_main: Optional[str] = None,
    teaor_sub: Optional[str] = None,
    size: Optional[str] = None,
    db="main"
):
    tensor, dims, terr_map, size_map, alag_map = load_tensor(db)

    # ======================================================
    # 🔹 4/A Területi indexek
    # ======================================================
    if territory is None:
        terr_idxs = list(range(len(dims["teruletek"])))

    else:
        terr_key = norm(territory)

        if db == "summary":
            # summary-n belül teljes területtípus
            t_list = dims["teruletek"]
            classified = [classify_summary_territory(t) for t in t_list]

            if terr_key in ["regio", "megye", "jaras", "kerulet", "mindosszesen"]:
                terr_idxs = [i for i, c in enumerate(classified) if c == terr_key]
            else:
                # konkrét település/járás/megye neve
                if terr_key not in terr_map:
                    return f"❌ Terület nem található: {territory}"
                terr_idxs = [dims["teruletek"].index(terr_map[terr_key])]

        else:
            # MAIN databázis → csak települések / kerületek
            if terr_key not in terr_map:
                return f"❌ Terület nem található: {territory}"
            terr_idxs = [dims["teruletek"].index(terr_map[terr_key])]

    # ======================================================
    # 🔹 4/B TEÁOR indexek
    # ======================================================
    teaor_idxs = []

    if teaor_main:
        for code in expand_teaor_main(teaor_main):
            if code in dims["teaor_alagak"]:
                teaor_idxs.append(dims["teaor_alagak"].index(code))

    if teaor_sub:
        key = norm(teaor_sub)
        if key not in alag_map:
            return f"❌ TEÁOR alág nem található: {teaor_sub}"
        teaor_idxs.append(dims["teaor_alagak"].index(alag_map[key]))

    if not teaor_idxs:
        teaor_idxs = list(range(len(dims["teaor_alagak"])))

    # ======================================================
    # 🔹 4/C Létszám kategória indexek
    # ======================================================
    if size:
        s_key = norm(size)
        if s_key not in size_map:
            return f"❌ Létszámkategória nem található: {size}"
        size_idxs = [dims["letszamkategoriak"].index(size_map[s_key])]
    else:
        size_idxs = list(range(len(dims["letszamkategoriak"])))

    # ======================================================
    # 🔹 4/D Tenzorból kivágás és összegzés
    # ======================================================
    sub = tensor[np.ix_(terr_idxs, size_idxs, teaor_idxs)]
    return int(sub.sum())


# ==========================================================
# 🎯 5. A régi egyszerű query_tensor változatlanul megmarad
# ==========================================================
def query_tensor(terulet: str, teaor_alag: str, letszam: str, db="main"):
    return query(territory=terulet, teaor_sub=teaor_alag, size=letszam, db=db)



# ==========================================================
# 🧪 TESZT
# ==========================================================
if __name__ == "__main__":

    print("\n--- Visegrád, TEÁOR 43, 1-4 fő (main) ---")
    print(query("Visegrád", teaor_sub="43", size="1-4 fő", db="main"))

    print("\n--- Összes megye, TEÁOR főág P, mindösszesen (summary) ---")
    print(query("megye", teaor_main="P", size="Mindösszesen Létszámkategória", db="summary"))

    print("\n--- Budapest 12. kerület, TEÁOR 56 (summary) ---")
    print(query("Budapest 12. kerület", teaor_sub="56", size="Mindösszesen Létszámkategória", db="summary"))

    print("\n==============================")
    print("🧪 ORSZÁGOS TEÁOR × LÉTSZÁM LEKÉRDEZÉS (MAIN)")
    print("==============================\n")

    # 1) Betöltjük a dimenziókat
    _, dims, _, _, _ = load_tensor("main")

    teaor_list = dims["teaor_alagak"]             # pl. ["1","2","3",...,"98"]
    size_list  = dims["letszamkategoriak"]        # 6 kategória

    results = []  # ide gyűjtjük

    # 2) Végigmegyünk a TEÁOR alágakon
    for teaor in teaor_list:
        row = {"TEÁOR": teaor}

        # 3) Végigmegyünk a 6 létszámkategórián
        for size in size_list:
            val = query(
                territory=None,     # teljes ország
                teaor_sub=teaor,
                size=size,
                db="main"
            )
            row[size] = val

        results.append(row)

    # 4) Kiírás táblázatos formában
    print("TEÁOR".ljust(8), " | " , " | ".join(size_list))
    print("-" * 80)
    for r in results:
        print(
            r["TEÁOR"].ljust(8),
            " | ",
            " | ".join(str(r[size]) for size in size_list)
        )
