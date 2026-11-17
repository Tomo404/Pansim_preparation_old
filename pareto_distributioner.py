# estimate_by_pareto.py
import numpy as np
import pandas as pd
import re
from pathlib import Path
import math

INPUT_FILE = "teaor_szerinti_letszam.txt"
OUT_TXT = "teaor_becsult_dolgozok_pareto.txt"
OUT_XLSX = "teaor_becsult_dolgozok_pareto.xlsx"

# kategória-intervallumok (zárt intervallumok)
INTERVALS = [
    (1.0, 4.0),
    (5.0, 9.0),
    (10.0, 19.0),
    (20.0, 49.0),
    (50.0, 249.0),
    (250.0, 500.0)   # a user kérése szerint 250-500
]

# kategória középpontok (fallback)
MIDPOINTS = np.array([2.5, 7.0, 15.0, 35.0, 150.0, 375.0])

def parse_line(line: str):
    if not line or not line.strip():
        return None
    parts = [p for p in re.split(r"[|]", line) if p.strip()]
    if len(parts) == 1:
        parts = [p for p in line.replace("|", " ").split() if p]
    parts = [p.strip() for p in parts]
    if len(parts) < 7:
        return None
    m = re.search(r"\d+", parts[0])
    if not m:
        return None
    code = int(m.group())
    nums = []
    for p in parts[1:7]:
        # tisztítás, ha üres vagy nem szám -> 0
        s = re.sub(r"[^\d\-]", "", p)
        nums.append(int(s) if s != "" else 0)
    return [code] + nums

def load_table(fn: str):
    rows = []
    p = Path(fn)
    if not p.exists():
        raise FileNotFoundError(f"Input file not found: {fn}")
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            parsed = parse_line(line)
            if parsed:
                rows.append(parsed)
    if not rows:
        raise ValueError("Nincs beolvasható sor az input fájlban.")
    df = pd.DataFrame(rows, columns=["TEÁOR", "1-4 fő", "5-9 fő", "10-19 fő",
                                     "20-49 fő", "50-249 fő", "250-500 fő"])
    return df

# Súlyozott MLE Pareto alpha estimate (xm rögzített)
# alpha_hat = (sum w_i) / sum( w_i * ln(x_i / xm) )
def pareto_weighted_alpha(midpoints, freqs, xm=1.0):
    midpoints = np.asarray(midpoints, dtype=float)
    freqs = np.asarray(freqs, dtype=float)
    mask = freqs > 0
    if not np.any(mask):
        return None
    x = midpoints[mask]
    w = freqs[mask]
    # mindnek x >= xm kell legyen
    if np.any(x <= xm):
        # ha van olyan x<=xm, akkor xm-t kisebbre állítjuk (soha ne legyen > min(x))
        xm = min(0.99 * np.min(x), xm)
    denom = np.sum(w * np.log(x / xm))
    if denom <= 0:
        return None
    alpha = np.sum(w) / denom
    return float(alpha), float(xm)

# Pareto density: f(x) = alpha * xm^alpha / x^{alpha+1}  (x >= xm)
# E[X | a <= X <= b] = ( ∫_a^b x f(x) dx ) / (S(a) - S(b))
# integral numerator: alpha * xm^alpha * ∫ x^{-alpha} dx = alpha*xm^alpha * ( b^{1-alpha} - a^{1-alpha} )/(1-alpha)
def pareto_conditional_mean(alpha, xm, a, b):
    # numerically stable handling
    if b <= a:
        return a
    if alpha <= 0:
        return None
    # if alpha == 1 special formula for integral
    Sa = (xm / a) ** alpha
    Sb = (xm / b) ** alpha
    prob = Sa - Sb
    if prob <= 0:
        return None
    if abs(alpha - 1.0) > 1e-8:
        num = (alpha * (xm ** alpha) / (1.0 - alpha)) * (b ** (1.0 - alpha) - a ** (1.0 - alpha))
    else:
        # alpha == 1: integral of x^{-1} -> ln
        num = alpha * (xm ** alpha) * (math.log(b) - math.log(a))
    mean = num / prob
    return float(mean)

def compute_expected_sizes_from_pareto(alpha, xm):
    expected = []
    for (a, b) in INTERVALS:
        m = pareto_conditional_mean(alpha, xm, a, b)
        if m is None or not np.isfinite(m):
            # fallback to midpoint
            m = (a + b) / 2.0
        # limit the last category maximum to 500 as requested
        if (a, b) == INTERVALS[-1]:
            if m > 500:
                m = 500.0
        expected.append(m)
    return np.array(expected)

def main():
    print("📥 Adatok beolvasása...")
    df = load_table(INPUT_FILE)
    print("\n=== BEOLVASOTT ADATOK (példa) ===")
    print(df.head(10).to_string(index=False))

    # orszagos összeg (a fithez)
    national = df[["1-4 fő", "5-9 fő", "10-19 fő", "20-49 fő", "50-249 fő", "250-500 fő"]].sum(axis=0).values
    print("\n🔢 Országos összesített 6 kategória:")
    print(national)

    # MIDPOINTS: a "megfigyelési" helyek a fithez
    midpoints = MIDPOINTS.copy()

    # pareto weighted MLE
    print("\n📈 Pareto illesztés (súlyozott MLE)...")
    res = pareto_weighted_alpha(midpoints, national, xm=1.0)
    if res is None:
        print("⚠️ Pareto illesztés nem stabil — fallback midpoint használat.")
        expected = MIDPOINTS.copy()
        alpha = None
        xm = None
    else:
        alpha, xm = res
        print(f"👉 becsült alpha={alpha:.4f}, xm={xm:.3f}")
        if alpha <= 0.0 or alpha < 0.1:
            print("⚠️ alpha nem megfelelő (<=0.1) — fallback midpoint használat.")
            expected = MIDPOINTS.copy()
        else:
            expected = compute_expected_sizes_from_pareto(alpha, xm)
    print("\n🔮 Várható (kategóriánként) értékek (dolgozók / település):")
    for i, v in enumerate(expected, 1):
        print(f"  Kategória {i}: {v:.2f}")

    # most TEÁOR-onként megszorozzuk
    cats = ["1-4 fő", "5-9 fő", "10-19 fő", "20-49 fő", "50-249 fő", "250-500 fő"]
    counts = df[cats].values.astype(float)   # shape (n,6)
    # estimated workers per TEÁOR = sum_i counts_i * expected_size_i
    estimated_workers = (counts * expected).sum(axis=1)
    df_out = df.copy()
    df_out["Becsült_létszám"] = np.round(estimated_workers).astype(np.int64)

    total_est = int(df_out["Becsült_létszám"].sum())
    print(f"\n📊 Országos becsült dolgozói létszám (összesen): {total_est:,}")

    # mentés
    print(f"\n📄 Mentés: {OUT_TXT}, {OUT_XLSX}")
    # TXT
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("TEÁOR | Becsült_létszám\n")
        for _, r in df_out.iterrows():
            f.write(f"{int(r['TEÁOR']):>3} | {int(r['Becsült_létszám']):>12}\n")
    # Excel
    df_out.to_excel(OUT_XLSX, index=False)
    print("✅ Kész.")

if __name__ == "__main__":
    main()
