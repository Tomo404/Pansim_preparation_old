import numpy as np
import re
from scipy.optimize import curve_fit
from scipy.stats import lognorm, pareto

# =========================================================
# 1) TXT beolvasása
# =========================================================

def load_table(filename="teaor_szerinti_letszam.txt"):
    """
    Beolvassa a TEÁOR-alkódonkénti eloszlást.
    Formátum:
    1 | 61993 | 157 | 58 | 0 | 685 | 16
    """
    rows = []
    pattern = re.compile(r"\s*\|?\s*")

    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            parts = [p for p in line.replace("|", " ").split() if p]
            if len(parts) < 7:
                continue

            # első: TEÁOR alág
            teaor = parts[0]
            values = list(map(int, parts[1:7]))
            rows.append(values)

    return np.array(rows)  # shape: (n,6)


# =========================================================
# 2) Exponenciális modell
# =========================================================

def exp_model(x, lam, A):
    return A * np.exp(-lam * x)


# =========================================================
# 3) Pareto modell (power-law)
# =========================================================

def pareto_model(x, alpha, A):
    # x+1, hogy ne legyen 0^(-alpha)
    return A * (x + 1) ** (-alpha)


# =========================================================
# 4) Illesztés + legjobb modell kiválasztás
# =========================================================

def fit_distributions(vals):
    x = np.arange(len(vals))

    results = {}

    # ---- EXP ----
    try:
        popt_exp, _ = curve_fit(exp_model, x, vals, p0=[0.5, vals[0]])
        pred_exp = exp_model(x, *popt_exp)
        mse_exp = np.mean((vals - pred_exp) ** 2)
        results["exponential"] = (mse_exp, popt_exp, pred_exp)
    except:
        pass

    # ---- LOGNORMAL ----
    try:
        # lognorm fit expects raw sample → approximate using category midpoint
        midpoints = np.array([2.5, 7, 15, 35, 150, 300])
        sample = []
        for m, count in zip(midpoints, vals):
            sample += [m] * max(count, 1)  # avoid zero count

        shape, loc, scale = lognorm.fit(sample, floc=0)
        pred_lognorm = lognorm.pdf(midpoints, shape, loc=loc, scale=scale)
        pred_lognorm = pred_lognorm / pred_lognorm.sum() * vals.sum()

        mse_ln = np.mean((vals - pred_lognorm) ** 2)
        results["lognormal"] = (mse_ln, (shape, loc, scale), pred_lognorm)
    except:
        pass

    # ---- PARETO ----
    try:
        popt_par, _ = curve_fit(pareto_model, x, vals, p0=[1.5, vals[0]])
        pred_par = pareto_model(x, *popt_par)
        mse_par = np.mean((vals - pred_par) ** 2)
        results["pareto"] = (mse_par, popt_par, pred_par)
    except:
        pass

    # =========================================================
    # Legjobb modell
    # =========================================================
    best_name = min(results, key=lambda k: results[k][0])
    mse, params, pred = results[best_name]

    return best_name, params, pred, results


# =========================================================
# 5) MAIN
# =========================================================

if __name__ == "__main__":
    print("📥 Adatok beolvasása...")
    table = load_table("teaor_szerinti_letszam.txt")

    # országos összesítés 6 kategóriára
    national = table.sum(axis=0)

    print("\n=== Országos összesített 6 kategória ===")
    print(national)

    print("\n📈 Illesztés folyamatban...")

    best, params, pred, all_models = fit_distributions(national)

    print("\n==============================")
    print("   📊  LEGJOBB ILLESZTÉS")
    print("==============================")
    print("Modell:", best)
    print("Paraméterek:", params)

    print("\n🔮 Illesztett 6 várható érték:")
    for i, v in enumerate(pred):
        print(f"Kategória {i+1}: {v:.2f}")

    print("\n📉 Modellhiba (MSE):", np.mean((national - pred)**2))

    print("\n📂 Egyéb modellek hibái:")
    for k, (mse, p, pr) in all_models.items():
        print(f"{k}: MSE={mse:.2f}")
