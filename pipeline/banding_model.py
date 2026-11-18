"""Membandingkan beberapa algoritma ML pada fitur dan data uji yang sama persis
dengan model utama (model_prediksi.py).

Setiap musim uji diduga oleh model yang hanya dilatih dari musim-musim sebelumnya.
Hasil disimpan ke model/perbandingan_model.json untuk ditampilkan di dashboard.
"""

from __future__ import annotations

import json
import time
import warnings

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss, mean_absolute_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import model_prediksi as mp

warnings.filterwarnings("ignore")
KELAS = {"H": 0, "D": 1, "A": 2}


def latih_dan_duga(nama_model: str, latih: pd.DataFrame, uji: pd.DataFrame, fitur: list[str],
                   alpha: float, rho: float) -> tuple[np.ndarray, np.ndarray]:
    median = latih[fitur].median()
    X, Xu = latih[fitur].fillna(median).to_numpy(), uji[fitur].fillna(median).to_numpy()
    y_kelas = latih.hasil.map(KELAS).to_numpy()
    Y = latih[mp.TARGET].to_numpy()

    if nama_model == "Regresi Poisson":
        model = mp.latih_semua(X, latih[mp.TARGET], {}, alpha)
        angka = np.column_stack([model[k].predict(Xu) for k in mp.TARGET])
        peluang = np.array([mp.peluang_hasil(mp.matriks_skor(a, b, rho))
                            for a, b in angka[:, :2]])
    elif nama_model == "Random Forest":
        klas = RandomForestClassifier(n_estimators=500, min_samples_leaf=40, max_features=0.3,
                                      n_jobs=-1, random_state=42).fit(X, y_kelas)
        reg = RandomForestRegressor(n_estimators=300, min_samples_leaf=40, max_features=0.3,
                                    n_jobs=-1, random_state=42).fit(X, Y)
        peluang, angka = klas.predict_proba(Xu), reg.predict(Xu)
    elif nama_model == "LightGBM":
        umum = dict(learning_rate=0.02, num_leaves=15, min_child_samples=60, subsample=0.8,
                    subsample_freq=1, colsample_bytree=0.7, reg_lambda=2.0, verbose=-1)
        klas = lgb.LGBMClassifier(n_estimators=400, **umum).fit(X, y_kelas)
        angka = np.column_stack([
            lgb.LGBMRegressor(objective="poisson", n_estimators=300, **umum).fit(X, Y[:, j]).predict(Xu)
            for j in range(Y.shape[1])])
        peluang = klas.predict_proba(Xu)
    else:  # regresi logistik untuk hasil, angka memakai rata-rata latih sebagai pembanding
        klas = make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000, C=0.1)).fit(X, y_kelas)
        peluang = klas.predict_proba(Xu)
        angka = np.tile(Y.mean(0), (len(Xu), 1))
    return peluang, angka


def main() -> None:
    mulai = time.time()
    laga = mp.muat_laga()
    data, fitur, _ = mp.bangun_fitur(laga)
    metrik = json.load(open(mp.MODEL / "metrik_poisson.json", encoding="utf-8"))
    alpha, rho = metrik["alpha"], metrik["rho"]

    hasil = {}
    for nama_model in ["Regresi Poisson", "Random Forest", "LightGBM", "Regresi logistik"]:
        semua_peluang, semua_angka, semua_uji = [], [], []
        t0 = time.time()
        for musim in mp.MUSIM_UJI:
            latih = data[data.sudah_main & (data.musim < musim)
                         & (data.k_riwayat >= 5) & (data.t_riwayat >= 5)]
            uji = data[data.sudah_main & (data.musim == musim)]
            p, a = latih_dan_duga(nama_model, latih, uji, fitur, alpha, rho)
            semua_peluang.append(p); semua_angka.append(a); semua_uji.append(uji)
        p, a, u = np.vstack(semua_peluang), np.vstack(semua_angka), pd.concat(semua_uji)
        benar_kelas = u.hasil.map(KELAS).to_numpy()
        benar_angka = u[mp.TARGET].to_numpy()
        hasil[nama_model] = {
            "akurasi_hasil": round(float(accuracy_score(benar_kelas, p.argmax(1))), 4),
            "log_loss": round(float(log_loss(benar_kelas, p / p.sum(1, keepdims=True),
                                             labels=[0, 1, 2])), 4),
            "mae_gol": round(float(mean_absolute_error(benar_angka[:, :2], a[:, :2])), 4),
            "mae_statistik": round(float(mean_absolute_error(benar_angka[:, 2:], a[:, 2:])), 4),
            "waktu_latih_detik": round(time.time() - t0, 1),
            "laga_uji": int(len(u)),
        }
        print(f"  {nama_model} selesai")

    hasil["Peluang bandar (pembanding)"] = {
        "akurasi_hasil": metrik["uji"].get("akurasi_bandar"),
        "log_loss": metrik["uji"].get("log_loss_bandar"),
        "mae_gol": None, "mae_statistik": None, "waktu_latih_detik": None,
        "laga_uji": metrik["uji"]["laga"],
    }
    tabel = pd.DataFrame(hasil).T
    print(f"\nData uji: musim {' + '.join(mp.MUSIM_UJI)}, {metrik['uji']['laga']} laga\n")
    print(tabel.to_string())
    (mp.MODEL / "perbandingan_model.json").write_text(
        json.dumps(hasil, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSelesai dalam {time.time() - mulai:.0f} detik, tersimpan di model/perbandingan_model.json")


if __name__ == "__main__":
    main()
