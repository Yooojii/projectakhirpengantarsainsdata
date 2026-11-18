"""Membandingkan LightGBM dengan model Poisson/linear untuk gol dan semua statistik laga.

Aturannya sama untuk kedua model: model untuk musim S hanya belajar dari musim sebelum S.
Setelan LightGBM dipilih di musim validasi 2024/25, lalu dinilai di musim uji.
Hasil: model/uji_lightgbm.json
"""

from __future__ import annotations

import json
import warnings

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, log_loss

import model_prediksi as mp

warnings.filterwarnings("ignore")
VALIDASI = "2024/25"
SETELAN = [
    {"n_estimators": 300, "learning_rate": 0.03, "num_leaves": 7, "min_child_samples": 50},
    {"n_estimators": 600, "learning_rate": 0.02, "num_leaves": 15, "min_child_samples": 80},
    {"n_estimators": 400, "learning_rate": 0.03, "num_leaves": 4, "min_child_samples": 100},
]
DASAR_LGB = {"subsample": 0.8, "subsample_freq": 1, "colsample_bytree": 0.7,
             "reg_lambda": 5.0, "verbose": -1, "n_jobs": -1}


def lgb_model(jenis, setelan):
    tujuan = "poisson" if jenis == "poisson" else "regression_l2"
    return lgb.LGBMRegressor(objective=tujuan, **setelan, **DASAR_LGB)


def dugaan(fitur, nama, target, jenis, musim, setelan, alpha, pakai_lgb, sumber=None):
    sumber = fitur if sumber is None else sumber
    latih = sumber[sumber.sudah_main & (sumber.musim < musim)]
    sasaran = fitur[(fitur.musim == musim) & fitur.sudah_main]
    median = latih[nama].median().fillna(0)
    Xs = sasaran[nama].fillna(median).to_numpy()
    keluar = {}
    for k in target:
        b = latih[latih[k].notna()]
        X, y = b[nama].fillna(median).to_numpy(), b[k].to_numpy()
        m = lgb_model(jenis.get(k, "poisson"), setelan) if pakai_lgb else mp.buat_model(jenis.get(k, "poisson"), alpha)
        keluar[k] = m.fit(X, y).predict(Xs)
    return sasaran, keluar


def hasil_laga(sasaran, duga, rho):
    p = np.array([mp.peluang_hasil(mp.matriks_skor(a, b, rho))
                  for a, b in zip(duga["gol_kandang"], duga["gol_tandang"])])
    p = p / p.sum(1, keepdims=True)
    kelas = sasaran.hasil.map({"H": 0, "D": 1, "A": 2}).to_numpy()
    return kelas, p


def main():
    laga = mp.muat_laga()
    laga["pekan"] = mp.isi_pekan(laga)
    fitur, nama, _ = mp.bangun_fitur(laga)
    fitur = fitur[(fitur.k_riwayat >= 5) & (fitur.t_riwayat >= 5) | ~fitur.sudah_main].copy()
    alpha, rho = 0.1, -0.035
    nama_x = nama + [c for c in fitur.columns if c.startswith(("k_bentuk_x_", "t_bentuk_x_"))]
    lengkap = fitur[fitur.statistik_lengkap.astype(str).str.lower().eq("true")]
    tambahan = dict(mp.TARGET_TAMBAHAN)
    tambahan.update({"penyelamatan_kiper_kandang": "poisson", "penyelamatan_kiper_tandang": "poisson"})

    # 1) pilih setelan di musim validasi (log loss hasil laga + MAE statistik)
    skor_setelan = []
    for s in SETELAN:
        sas, d = dugaan(fitur, nama, mp.TARGET, {}, VALIDASI, s, alpha, True)
        kelas, p = hasil_laga(sas, d, rho)
        ll = log_loss(kelas, p, labels=[0, 1, 2])
        sas2, d2 = dugaan(fitur, nama_x, list(tambahan), tambahan, VALIDASI, s, alpha, True, lengkap)
        mae_t = np.mean([np.nanmean(np.abs(sas2[k] - d2[k]) / sas2[k].std()) for k in tambahan])
        skor_setelan.append(ll + mae_t * 0.1)
        print(f"setelan {s}: log loss {ll:.4f}, MAE tambahan terbakukan {mae_t:.4f}")
    terbaik = SETELAN[int(np.argmin(skor_setelan))]
    print("terpilih:", terbaik)

    # 2) nilai di musim uji
    hasil = {"setelan": terbaik, "laga": {}, "statistik": {}}
    kumpul = {"poisson": [], "lightgbm": []}
    tambah = {"poisson": [], "lightgbm": []}
    for musim in mp.MUSIM_UJI:
        for nm, pakai in (("poisson", False), ("lightgbm", True)):
            sas, d = dugaan(fitur, nama, mp.TARGET, {}, musim, terbaik, alpha, pakai)
            kumpul[nm].append((sas, d))
            sas2, d2 = dugaan(fitur, nama_x, list(tambahan), tambahan, musim, terbaik, alpha, pakai, lengkap)
            tambah[nm].append((sas2, d2))

    for wadah in (kumpul, tambah):
        wadah["ensemble"] = [(s, {k: (dp[k] + dl[k]) / 2 for k in dp})
                             for (s, dp), (_, dl) in zip(wadah["poisson"], wadah["lightgbm"])]
    for nm in kumpul:
        kelas = np.concatenate([hasil_laga(s, d, rho)[0] for s, d in kumpul[nm]])
        p = np.concatenate([hasil_laga(s, d, rho)[1] for s, d in kumpul[nm]])
        hasil["laga"][nm] = {"laga": int(len(kelas)), "akurasi": round(float(accuracy_score(kelas, p.argmax(1))), 4),
                             "log_loss": round(float(log_loss(kelas, p, labels=[0, 1, 2])), 4)}
        for k in mp.TARGET:
            benar = np.concatenate([s[k].to_numpy() for s, _ in kumpul[nm]])
            duga = np.concatenate([d[k] for _, d in kumpul[nm]])
            hasil["statistik"].setdefault(k, {})[nm] = round(float(np.mean(np.abs(benar - duga))), 3)
        for k in tambahan:
            benar = np.concatenate([s[k].to_numpy() for s, _ in tambah[nm]])
            duga = np.concatenate([d[k] for _, d in tambah[nm]])
            ok = ~np.isnan(benar)
            hasil["statistik"].setdefault(k, {})[nm] = round(float(np.mean(np.abs(benar[ok] - duga[ok]))), 3)
            if nm == "poisson":
                rata = np.concatenate([np.full(len(s), lengkap[lengkap.musim < s.musim.iloc[0]][k].mean())
                                       for s, _ in tambah[nm]])
                hasil["statistik"][k]["rata_rata"] = round(float(np.mean(np.abs(benar[ok] - rata[ok]))), 3)

    print("\nHasil laga (uji", " + ".join(mp.MUSIM_UJI), "):")
    for nm, v in hasil["laga"].items():
        print(f"  {nm:9s} akurasi {v['akurasi']:.3f} | log loss {v['log_loss']:.4f} | {v['laga']} laga")
    print(f"\n{'statistik':28s} {'Poisson':>9s} {'LightGBM':>9s} {'Ensemble':>9s}  pemenang")
    for k, v in hasil["statistik"].items():
        menang = min(("poisson", "lightgbm", "ensemble"), key=v.get)
        print(f"  {k:26s} {v['poisson']:9.3f} {v['lightgbm']:9.3f} {v['ensemble']:9.3f}  {menang}")
    (mp.AKAR / "model" / "uji_lightgbm.json").write_text(json.dumps(hasil, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
