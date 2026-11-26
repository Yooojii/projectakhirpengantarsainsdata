"""Clustering gaya bermain klub per musim dengan K-Means (bagian unsupervised).

Setiap baris adalah satu klub di satu musim. Fitur serangan dan pertahanan dihitung per laga
dari data football-data (tersedia sejak 2000/01), dibakukan, lalu dikelompokkan K-Means.
Nama kategori diberikan dari pusat klaster: indeks serangan dan indeks pertahanan.
Hasil: data/klaster_gaya.csv dan model/klaster_gaya.json
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

AKAR = Path(__file__).parent
SERANG = ["gol", "tembakan", "tembakan_tepat", "sepak_pojok"]
FITUR = SERANG + [f"{k}_kebobolan" for k in SERANG[:3]]
K = 5


def per_klub(laga: pd.DataFrame) -> pd.DataFrame:
    potong = []
    for sisi, lawan in (("kandang", "tandang"), ("tandang", "kandang")):
        d = pd.DataFrame({"musim": laga.musim, "klub": laga[f"tim_{sisi}"], "di_kandang": sisi == "kandang"})
        for k in SERANG:
            d[k] = laga[f"{k}_{sisi}"]
            d[f"{k}_kebobolan"] = laga[f"{k}_{lawan}"]
        selisih = laga[f"gol_{sisi}"] - laga[f"gol_{lawan}"]
        jeda = laga[f"gol_{sisi}_babak1"] - laga[f"gol_{lawan}_babak1"]
        d["poin"] = np.sign(selisih).map({1: 3, 0: 1, -1: 0})
        d["tertinggal_jeda"] = jeda < 0
        d["unggul_jeda"] = jeda > 0
        d["selisih_babak2"] = selisih - jeda
        d["selisih_babak1"] = jeda
        d["clean_sheet"] = laga[f"gol_{lawan}"] == 0
        d["pelanggaran"] = laga[f"pelanggaran_{sisi}"]
        d["kartu"] = laga[f"kartu_kuning_{sisi}"] + laga[f"kartu_merah_{sisi}"]
        for k in ("penguasaan_bola", "akurasi_umpan"):
            d[k] = laga.get(f"{k}_{sisi}")
        potong.append(d)
    d = pd.concat(potong)
    d["poin_comeback"] = d.poin.where(d.tertinggal_jeda, 0)
    d["hilang_unggul"] = d.unggul_jeda & (d.poin < 3)
    d["poin_kandang"] = d.poin.where(d.di_kandang)
    d["poin_tandang"] = d.poin.where(~d.di_kandang)
    g = d.groupby(["musim", "klub"])
    t = g.agg(main=("gol", "size"), **{k: (k, "mean") for k in FITUR}, poin=("poin", "sum"),
              poin_comeback=("poin_comeback", "sum"), hilang_unggul=("hilang_unggul", "sum"),
              selisih_babak1=("selisih_babak1", "sum"), selisih_babak2=("selisih_babak2", "sum"),
              clean_sheet=("clean_sheet", "sum"), poin_kandang=("poin_kandang", "mean"),
              poin_tandang=("poin_tandang", "mean"), pelanggaran=("pelanggaran", "mean"),
              kartu=("kartu", "mean"), penguasaan_bola=("penguasaan_bola", "mean"),
              akurasi_umpan=("akurasi_umpan", "mean")).reset_index()
    t["gol_per_tepat"] = t.gol / t.tembakan_tepat
    t["tembakan_per_gol"] = t.tembakan / t.gol
    return t[t.main >= 10].dropna(subset=FITUR)


def main() -> None:
    laga = pd.read_csv(AKAR / "data" / "liga_inggris_gabungan.csv", low_memory=False)
    laga = laga[laga.gol_kandang.notna()]
    t = per_klub(laga)
    # dibakukan per musim supaya perbedaan era (cara mencatat tembakan berubah) tidak ikut terbaca
    z = t.groupby("musim")[FITUR].transform(lambda s: (s - s.mean()) / s.std())
    t["indeks_serangan"] = z[FITUR[:4]].mean(axis=1).round(3)
    t["indeks_pertahanan"] = (-z[FITUR[4:]].mean(axis=1)).round(3)  # makin tinggi makin jarang kebobolan
    X = t[["indeks_serangan", "indeks_pertahanan"]].to_numpy()

    siluet = {k: round(float(silhouette_score(X, KMeans(k, n_init=20, random_state=8).fit_predict(X))), 3)
              for k in range(2, 8)}
    km = KMeans(K, n_init=20, random_state=8).fit(X)
    t["klaster"] = km.labels_
    pusat = pd.DataFrame(km.cluster_centers_, columns=["a", "d"])
    urut = (pusat.a + pusat.d).sort_values(ascending=False).index
    nama = {urut[0]: "Title Contenders", urut[1]: "Well-Balanced", urut[-1]: "Struggling"}
    for c in urut[2:-1]:
        nama[c] = "Attack-Minded" if pusat.a[c] > pusat.d[c] else "Defence-First"
    t["kategori"] = t.klaster.map(nama)
    t["serangan_terbaik"] = t.indeks_serangan == t.groupby("musim").indeks_serangan.transform("max")
    t["pertahanan_terbaik"] = t.indeks_pertahanan == t.groupby("musim").indeks_pertahanan.transform("max")
    t.drop(columns="klaster").sort_values(["musim", "poin"], ascending=[True, False]).to_csv(
        AKAR / "data" / "klaster_gaya.csv", index=False)

    ringkas = {"k": K, "siluet_per_k": siluet, "baris": int(len(t)), "fitur": FITUR, "kategori": {}}
    for c, n in nama.items():
        b = t[t.klaster == c]
        ringkas["kategori"][n] = {"jumlah": int(len(b)), "poin_per_38": round(float((b.poin / b.main * 38).mean()), 1),
                                  "indeks_serangan": round(float(pusat.a[c]), 2),
                                  "indeks_pertahanan": round(float(pusat.d[c]), 2),
                                  **{f: round(float(b[f].mean()), 2) for f in FITUR}}
    (AKAR / "model" / "klaster_gaya.json").write_text(json.dumps(ringkas, indent=1, ensure_ascii=False), encoding="utf-8")
    print({n: (v["jumlah"], v["poin_per_38"], v["indeks_serangan"], v["indeks_pertahanan"]) for n, v in ringkas["kategori"].items()})
    kini = t[t.musim == t.musim.max()].sort_values("poin", ascending=False)
    print(kini[["klub", "kategori", "indeks_serangan", "indeks_pertahanan", "serangan_terbaik", "pertahanan_terbaik"]].to_string())


if __name__ == "__main__":
    main()
