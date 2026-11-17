import pandas as pd
import chardet

FNAME = "df_main_redemption_OG.csv"
CHUNK_SIZE = 1_000_000  # soronkénti darabolás
OUT_TEMPLATE = "df_main_part_{i}.xlsx"

# --- kódolás detektálása ---
with open(FNAME, "rb") as f:
    enc_guess = chardet.detect(f.read(100000))
encoding_used = enc_guess["encoding"] or "latin1"
print(f"Kódolás felismerve: {encoding_used}")

# --- fájl darabolása és mentése Excel-be ---
chunks = pd.read_csv(
    FNAME,
    encoding=encoding_used,
    chunksize=CHUNK_SIZE,
    on_bad_lines="skip"
)

for i, chunk in enumerate(chunks, start=1):
    out_name = OUT_TEMPLATE.format(i=i)
    print(f"💾 {out_name} mentése ({len(chunk)} sor)")
    chunk.to_excel(out_name, index=False, engine="openpyxl")

print("✅ Kész! A fájl több Excel-részre lett darabolva.")
