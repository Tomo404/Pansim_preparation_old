# add_telepules.py
import openpyxl
import numpy as np
import json
import unicodedata
import re
from typing import Optional, Tuple, List

# -------------------------
# Normalizáló segéd
# -------------------------
def norm(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.lower().strip()
    return re.sub(r"\s+", " ", s)


def norm_key(s: str) -> str:
    """küszöbszó-mentes kulcs (keresésekhez)"""
    return re.sub(r"[^a-z0-9]", "", norm(s))


# -------------------------
# Dimenziók/tenzor be/ki
# -------------------------
def load_tensor_and_dims(db: str):
    tensor_path = f"tensor_{db}.npy"
    dims_path = f"tensor_{db}_dimensions.json"
    try:
        tensor = np.load(tensor_path)
    except FileNotFoundError:
        raise FileNotFoundError(f"Nem található a tenzor fájl: {tensor_path}")

    with open(dims_path, "r", encoding="utf-8") as f:
        dims = json.load(f)

    return tensor, dims, tensor_path, dims_path


def save_tensor_and_dims(tensor: np.ndarray, dims: dict, tensor_path: str, dims_path: str):
    np.save(tensor_path, tensor)
    with open(dims_path, "w", encoding="utf-8") as f:
        json.dump(dims, f, ensure_ascii=False, indent=2)


# -------------------------
# Segéd: TEÁOR kód normalizálás (01 -> 1)
# -------------------------
def norm_teaor_code(raw: str) -> str:
    """
    Excelben a TEÁOR oszlopok így jönnek:
        "01==  Növénytermesztés..."
        "10==  Élelmiszergyártás"
    Ez kiszedi belőle az első részt (01, 10, stb.), levágja a vezető nullát.
    """
    if raw is None:
        return ""

    s = str(raw).strip()

    # Ha '==' szerepel, akkor az előtti rész a kód
    if "==" in s:
        s = s.split("==", 1)[0].strip()

    # Ha nagyon hosszú véletlenül, tartsuk csak az első szót
    s = s.split()[0]

    # Nullák eltávolítása elejéről (01 -> 1)
    s = re.sub(r"^0+", "", s)

    return s



# -------------------------
# Excel-ből blokkok keresése
# -------------------------
def find_teaor_header(ws, hint_keywords: List[str]=["TEÁOR","TEAOR","TEÁOR alag","TEÁOR alág","TEÁOR alág kód"]):
    """
    Megkeresi a munkalapban azt a cellát, ami a TEÁOR fejlécre utal.
    Visszaad (row, col) indexet (1-alapú openpyxl index).
    """
    for row in ws.iter_rows(min_row=1, max_row=40, min_col=1, max_col=30):  # általános keresési ablak
        for cell in row:
            if cell.value is None:
                continue
            v = norm(str(cell.value))
            for kw in hint_keywords:
                if norm(kw) in v:
                    return cell.row, cell.column
    return None


# -------------------------
# Fő függvény
# -------------------------
def add_telepules(excel_path: str, telepules_nev: str, start_cell: Optional[str]=None,
                  overwrite_existing: bool=True):
    """
    Beolvassa az Excelből a TEÁOR értékeket és hozzáadja / frissíti őket a tensor_main/summary tenzorokban.

    - excel_path: a lokal Excel fájl (pl "Visegrad.xlsx")
    - telepules_nev: a település neve, ahogy a dims-ben szerepel/ vagy szeretnénk, hogy szerepeljen
    - start_cell: pl "C11" — ha megadod, a keresés kihagyható
    - overwrite_existing: ha True, felülírja a meglévő értékeket; ha False, összeadja az új értéket a meglévőhöz
    """
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    ws = wb.active

    # 1) megkeressük a TEÁOR fejléc celláját (ha van)
    if start_cell:
        m = re.match(r"^([A-Za-z]+)(\d+)$", start_cell)
        if not m:
            raise ValueError("start_cell formátum hibás (pl. 'C11').")
        col_str, row_str = m.groups()
        col = openpyxl.utils.column_index_from_string(col_str)
        row = int(row_str)
        header_pos = (row, col)
    else:
        found = find_teaor_header(ws)
        if not found:
            raise ValueError("Nem található TEÁOR oszlop a fájlban. Adj meg start_cell-t (pl 'C11') vagy ellenőrizd a fájlt.")
        header_pos = found

    header_row, header_col = header_pos

    # 2) TEÁOR oszlopok jobbra haladva: gyűjtjük a kódokat (ameddig nem üres)
    teaor_cols = []
    teaor_codes = []
    c = header_col
    while True:
        val = ws.cell(row=header_row, column=c).value
        if val is None or str(val).strip() == "":
            break
        code = str(val).strip()
        code_norm = norm_teaor_code(code)
        if code_norm == "":
            break
        teaor_cols.append(c)
        teaor_codes.append(code_norm)
        c += 1

    if not teaor_cols:
        raise ValueError("A TEÁOR-fejlécet találtuk, de nem sikerült kinyerni belőle oszlopokat/azonosítókat.")

    # 3) feltételezve: a méret-kategória oszlop egy oszloppal balra van (pl. B ha TEÁOR C-ben van)
    size_col = header_col - 1
    if size_col < 1:
        raise ValueError("Nem található a létszámkategória oszlop (nincs baloldali oszlop).")

    # 4) az adatok a header sor alatti sorokban vannak (header_row+1, +2, ...) ameddig a size_col nem üres
    data_rows = []
    r = header_row + 1
    while True:
        size_val = ws.cell(row=r, column=size_col).value
        if size_val is None or str(size_val).strip() == "":
            break
        # beolvassuk az összes TEÁOR értéket ezen a soron
        row_vals = {}
        for idx, col_idx in enumerate(teaor_cols):
            cellv = ws.cell(row=r, column=col_idx).value
            try:
                v = 0 if cellv is None else float(cellv)
            except Exception:
                # ha nem numeric, próbáljuk számmá konvertálni, egyébként 0
                try:
                    v = float(str(cellv).strip().replace(",", "."))
                except Exception:
                    v = 0
            row_vals[teaor_codes[idx]] = int(v)
        data_rows.append((str(ws.cell(row=r, column=size_col).value).strip(), row_vals))
        r += 1

    if not data_rows:
        raise ValueError("Nincsenek adat-sorok a TEÁOR fejléc alatti blokkon.")

    # 5) Végigmegyünk a sorokon: a 'Mindösszesen' létszámok summary-be mennek, a többi main-be
    # Betöltjük mindkét tenzort/dimset
    tensor_main, dims_main, main_tensor_path, main_dims_path = load_tensor_and_dims("main")
    tensor_sum, dims_sum, sum_tensor_path, sum_dims_path = load_tensor_and_dims("summary")

    # norm maps
    terr_map_main = {norm_key(t): t for t in dims_main["teruletek"]}
    terr_map_sum = {norm_key(t): t for t in dims_sum["teruletek"]}

    # teaor dim (mindkét tenzor feltételezi ugyanazokat az alágakat; ha eltérés -> jelezzük)
    teaor_dim_main = [norm_teaor_code(s) for s in dims_main["teaor_alagak"]]
    teaor_dim_sum = [norm_teaor_code(s) for s in dims_sum["teaor_alagak"]]

    missing_in_main = [c for c in teaor_codes if c not in teaor_dim_main]
    missing_in_sum = [c for c in teaor_codes if c not in teaor_dim_sum]
    if missing_in_main or missing_in_sum:
        missing = sorted(set(missing_in_main + missing_in_sum))
        raise ValueError(f"A következő TEÁOR-kód(ok) hiányoznak a tenzor dimenziókból: {missing}. "
                         "Add hozzá őket a dims-hez vagy egységesítsd a kódokat (01 -> 1).")

    # helper: beszúrás / frissítés logika
    def ensure_territory(tensor, dims, terr_map, territory_name):
        """
        Ha a territory nincs a dims-ben: hozzáadjuk a dims listához és kibővítjük a tenzort (első dim növelése).
        Visszaadja: (tensor_new, dims_new, index_of_territory)
        """
        key = norm_key(territory_name)
        if key in terr_map:
            idx = dims["teruletek"].index(terr_map[key])
            return tensor, dims, idx
        # új territory: append
        new_name = territory_name
        dims["teruletek"].append(new_name)
        old_shape = tensor.shape  # (T, S, A)
        T_new = old_shape[0] + 1
        new_tensor = np.zeros((T_new, old_shape[1], old_shape[2]), dtype=tensor.dtype)
        new_tensor[: old_shape[0], :, :] = tensor
        # az új sor (last) marad 0-kal (később feltöltjük)
        idx = T_new - 1
        return new_tensor, dims, idx

    # feldolgozás
    # ha summary sor --> use tensor_sum/dims_sum, különben main
    main_changed = False
    sum_changed = False

    for size_cat, teaor_map_vals in data_rows:
        is_summary_row = ("mindosszesen" in norm(size_cat).replace(" ", "")) or ("mindösszesen" in norm(size_cat))
        target = "summary" if is_summary_row else "main"

        if target == "main":
            tensor_main, dims_main, idx = ensure_territory(tensor_main, dims_main, terr_map_main, telepules_nev)
            # frissítsük terr_map_main is (új név hozzáadva)
            terr_map_main = {norm_key(t): t for t in dims_main["teruletek"]}
            # indexek
            t_idx = idx
            s_idx_map = {v: i for i, v in enumerate(dims_main["letszamkategoriak"])}
            a_idx_map = {norm_teaor_code(v): i for i, v in enumerate(dims_main["teaor_alagak"])}
            # létszám index keresés
            s_key = next((k for k in dims_main["letszamkategoriak"] if norm_key(k) == norm_key(size_cat)), None)
            if s_key is None:
                raise ValueError(f"Létszámkategória nincs a main dims-ben: '{size_cat}'")
            s_idx = dims_main["letszamkategoriak"].index(s_key)
            for teaor_code, val in teaor_map_vals.items():
                a_key = norm_teaor_code(teaor_code)
                a_idx = dims_main["teaor_alagak"].index(next(x for x in dims_main["teaor_alagak"] if norm_teaor_code(x)==a_key))
                if overwrite_existing:
                    tensor_main[t_idx, s_idx, a_idx] = val
                else:
                    tensor_main[t_idx, s_idx, a_idx] += val
            main_changed = True

        else:
            tensor_sum, dims_sum, idx = ensure_territory(tensor_sum, dims_sum, terr_map_sum, telepules_nev)
            terr_map_sum = {norm_key(t): t for t in dims_sum["teruletek"]}
            s_key = next((k for k in dims_sum["letszamkategoriak"] if norm_key(k) == norm_key(size_cat)), None)
            if s_key is None:
                raise ValueError(f"Létszámkategória nincs a summary dims-ben: '{size_cat}'")
            s_idx = dims_sum["letszamkategoriak"].index(s_key)
            for teaor_code, val in teaor_map_vals.items():
                a_key = norm_teaor_code(teaor_code)
                a_idx = dims_sum["teaor_alagak"].index(next(x for x in dims_sum["teaor_alagak"] if norm_teaor_code(x)==a_key))
                if overwrite_existing:
                    tensor_sum[idx, s_idx, a_idx] = val
                else:
                    tensor_sum[idx, s_idx, a_idx] += val
            sum_changed = True

    # 6) mentés, ha változott
    if main_changed:
        save_tensor_and_dims(tensor_main, dims_main, main_tensor_path, main_dims_path)
        print(f"MAIN tenzor frissítve és mentve: {main_tensor_path}, {main_dims_path}")
    if sum_changed:
        save_tensor_and_dims(tensor_sum, dims_sum, sum_tensor_path, sum_dims_path)
        print(f"SUMMARY tenzor frissítve és mentve: {sum_tensor_path}, {sum_dims_path}")

    return {"main_changed": main_changed, "sum_changed": sum_changed}

res = add_telepules("Visegrad.xlsx", "Visegrád", start_cell="C11", overwrite_existing=True)
print(res)