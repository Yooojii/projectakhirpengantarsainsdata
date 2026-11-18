"""Model utama dashboard: regresi Poisson dengan koreksi Dixon-Coles.

Alur kerja:
1. Bangun fitur sebelum laga untuk setiap pertandingan, termasuk yang belum dimainkan:
   bentuk tim (rata-rata tertimbang laga-laga sebelumnya), Elo, poin dan selisih gol
   musim berjalan, serta jeda istirahat.
2. Latih satu regresi Poisson untuk tiap statistik yang diduga (gol, tembakan, tembakan
   tepat sasaran, sepak pojok, pelanggaran, kartu kuning, untuk kedua tim).
3. Dugaan untuk laga lama dibuat secara maju bertahap: model untuk musim S hanya dilatih
   dengan musim-musim sebelum S, jadi tidak pernah melihat hasil yang diduganya.
4. Gol kandang dan tandang diubah jadi matriks peluang skor dengan koreksi Dixon-Coles
   untuk skor rendah, lalu diturunkan menjadi peluang menang, seri, dan kalah.
5. Sisa musim berjalan disimulasikan ribuan kali untuk peluang juara, empat besar,
   dan degradasi.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import poisson
from sklearn.linear_model import PoissonRegressor, Ridge
from sklearn.metrics import accuracy_score, log_loss, mean_absolute_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

AKAR = Path(__file__).parent
DATA, MODEL = AKAR / "data", AKAR / "model"
MUSIM_BERJALAN = "2026/27"
MUSIM_UJI = ["2025/26", "2026/27"]
MUSIM_AWAL_DUGA = "2003/04"
MAKS_GOL = 10
SIMULASI = 20000

STAT = {"gol": "gol", "tembakan": "tembakan", "tembakan_tepat": "tepat",
        "sepak_pojok": "pojok", "pelanggaran": "langgar", "kartu_kuning": "kuning"}
TARGET = [f"{asal}_{sisi}" for asal in STAT for sisi in ("kandang", "tandang")]
TARGET_TAMBAHAN = {  # dari API-Football dan BBC Sport, nama kolomnya sudah diseragamkan
    "penguasaan_bola_kandang": "linear",
    "umpan_kandang": "poisson", "umpan_tandang": "poisson",
    "akurasi_umpan_kandang": "linear", "akurasi_umpan_tandang": "linear",
}
# penyelamatan kiper tidak dimodelkan langsung karena kalah dari tebakan rata-rata;
# nilainya diturunkan dari dugaan tembakan tepat sasaran lawan dikurangi dugaan gol lawan.
# offside dibuang karena tidak ada model yang mengalahkan tebakan rata-rata.
MINIMAL_TAMBAHAN = 150
# riwayat statistik tambahan tiap tim, dipakai sebagai fitur khusus model statistik tambahan
DASAR_TAMBAHAN = ["penguasaan_bola", "umpan", "akurasi_umpan"]


# ------------------------------------------------------------------ data
def muat_laga() -> pd.DataFrame:
    berkas = DATA / "liga_inggris_gabungan.csv"
    if not berkas.exists():
        berkas = DATA / "liga_inggris_lengkap.csv"
    hasil = pd.read_csv(berkas, parse_dates=["tanggal"], low_memory=False)
    hasil["sudah_main"] = True

    jadwal = pd.read_csv(DATA / "jadwal_musim.csv", parse_dates=["tanggal"])
    mendatang = jadwal[~jadwal.sudah_main][["tanggal", "waktu", "tim_kandang", "tim_tandang",
                                            "musim", "putaran"]].copy()
    mendatang["sudah_main"] = False

    pekan = jadwal[["musim", "tim_kandang", "tim_tandang", "putaran"]]
    hasil = hasil.merge(pekan, on=["musim", "tim_kandang", "tim_tandang"], how="left")
    laga = pd.concat([hasil, mendatang], ignore_index=True)
    laga = laga.sort_values(["tanggal", "tim_kandang"]).reset_index(drop=True)
    laga["pekan"] = laga.putaran.str.extract(r"(\d+)").astype(float)
    return laga


def isi_pekan(laga: pd.DataFrame) -> pd.Series:
    """Nomor pekan: dari jadwal resmi bila ada, selain itu diperkirakan dari urutan laga."""
    urut = {}
    ke = []
    musim_lalu = None
    for _, r in laga.iterrows():
        if r.musim != musim_lalu:
            urut, musim_lalu = {}, r.musim
        a = urut.get(r.tim_kandang, 0) + 1
        b = urut.get(r.tim_tandang, 0) + 1
        urut[r.tim_kandang], urut[r.tim_tandang] = a, b
        ke.append(max(a, b))
    return laga.pekan.fillna(pd.Series(ke, index=laga.index)).astype(int)


# ------------------------------------------------------------------ fitur
def tabel_tim(laga: pd.DataFrame) -> pd.DataFrame:
    sisi = []
    for kandang, (s, l) in ((1, ("kandang", "tandang")), (0, ("tandang", "kandang"))):
        d = pd.DataFrame({"id_laga": laga.index, "tanggal": laga.tanggal, "musim": laga.musim,
                          "tim": laga[f"tim_{s}"], "kandang": kandang})
        for asal, pendek in STAT.items():
            d[f"{pendek}_s"] = laga[f"{asal}_{s}"].values
            d[f"{pendek}_l"] = laga[f"{asal}_{l}"].values
        for asal in DASAR_TAMBAHAN:
            if f"{asal}_{s}" in laga:
                d[f"x_{asal}_s"] = pd.to_numeric(laga[f"{asal}_{s}"], errors="coerce").values
                d[f"x_{asal}_l"] = pd.to_numeric(laga[f"{asal}_{l}"], errors="coerce").values
        sisi.append(d)
    t = pd.concat(sisi, ignore_index=True).sort_values(["tanggal", "id_laga"]).reset_index(drop=True)
    main = t.gol_s.notna()
    t["poin"] = np.where(main, np.select([t.gol_s > t.gol_l, t.gol_s == t.gol_l], [3.0, 1.0], 0.0),
                         np.nan)
    t["selisih"] = t.gol_s - t.gol_l
    return t


def hitung_elo(laga: pd.DataFrame, k: float = 20.0, kandang: float = 60.0,
               tarik: float = 0.25) -> tuple[np.ndarray, np.ndarray, dict]:
    nilai: dict[str, float] = {}
    musim_lalu = None
    ek_semua, et_semua = np.zeros(len(laga)), np.zeros(len(laga))
    for i, r in enumerate(laga.itertuples()):
        if r.musim != musim_lalu and musim_lalu is not None:
            nilai = {t: 1500 + (v - 1500) * (1 - tarik) for t, v in nilai.items()}
        musim_lalu = r.musim
        ek = nilai.setdefault(r.tim_kandang, 1450.0)
        et = nilai.setdefault(r.tim_tandang, 1450.0)
        ek_semua[i], et_semua[i] = ek, et
        if not r.sudah_main:
            continue
        harap = 1 / (1 + 10 ** (-((ek + kandang) - et) / 400))
        nyata = 1.0 if r.gol_kandang > r.gol_tandang else (0.5 if r.gol_kandang == r.gol_tandang else 0.0)
        pengali = 1.0 + np.log1p(max(abs(r.gol_kandang - r.gol_tandang) - 1, 0))
        geser = k * pengali * (nyata - harap)
        nilai[r.tim_kandang], nilai[r.tim_tandang] = ek + geser, et - geser
    return ek_semua, et_semua, nilai


def bangun_fitur(laga: pd.DataFrame) -> tuple[pd.DataFrame, list[str], dict]:
    t = tabel_tim(laga)
    dasar = [c for c in t.columns if c.endswith(("_s", "_l"))] + ["poin"]
    per_tim = t.groupby("tim", sort=False)
    for c in dasar:
        geser = per_tim[c].shift(1)
        t[f"bentuk_{c}"] = geser.groupby(t.tim).transform(
            lambda s: s.ewm(halflife=6, ignore_na=True).mean())
    t["riwayat"] = per_tim["gol_s"].transform(lambda s: s.notna().cumsum().shift(1).fillna(0))
    t["jeda"] = per_tim["tanggal"].diff().dt.days.clip(2, 30).fillna(7)

    per_musim = [t.musim, t.tim]
    t["main_musim"] = t.gol_s.notna().groupby(per_musim).transform(lambda s: s.cumsum().shift(1).fillna(0))
    t["poin_musim"] = t.poin.fillna(0).groupby(per_musim).transform(
        lambda s: s.cumsum().shift(1).fillna(0)) / t.main_musim.clip(lower=1)
    t["selisih_musim"] = t.selisih.fillna(0).groupby(per_musim).transform(
        lambda s: s.cumsum().shift(1).fillna(0)) / t.main_musim.clip(lower=1)
    t.loc[t.main_musim == 0, ["poin_musim", "selisih_musim"]] = [1.35, 0.0]

    kolom = [f"bentuk_{c}" for c in dasar] + ["riwayat", "jeda", "poin_musim", "selisih_musim"]
    sisi_k = t[t.kandang == 1].set_index("id_laga")[kolom].add_prefix("k_")
    sisi_t = t[t.kandang == 0].set_index("id_laga")[kolom].add_prefix("t_")
    fitur = laga.join(sisi_k).join(sisi_t)

    ek, et, elo_akhir = hitung_elo(laga)
    fitur["elo_k"], fitur["elo_t"] = ek, et
    fitur["selisih_elo"] = ek - et

    nama = [c for c in fitur.columns if c.startswith(("k_", "t_"))
            and not c.endswith("riwayat") and "bentuk_x_" not in c] + ["elo_k", "elo_t", "selisih_elo"]
    return fitur, nama, elo_akhir


# ------------------------------------------------------------------ model
def buat_model(jenis: str, alpha: float):
    if jenis == "linear":
        return make_pipeline(StandardScaler(), Ridge(alpha=alpha * 100))
    return make_pipeline(StandardScaler(), PoissonRegressor(alpha=alpha, max_iter=800))


SETELAN_LGB = {"n_estimators": 400, "learning_rate": 0.03, "num_leaves": 4, "min_child_samples": 100,
               "subsample": 0.8, "subsample_freq": 1, "colsample_bytree": 0.7, "reg_lambda": 5.0,
               "verbose": -1}  # dipilih di musim validasi 2024/25 lewat uji_lightgbm.py


class Ensemble:
    """Rata-rata dugaan model GLM (Poisson atau Ridge) dan LightGBM."""

    def __init__(self, jenis: str, alpha: float):
        import lightgbm as lgb
        self.glm = buat_model(jenis, alpha)
        self.lgb = lgb.LGBMRegressor(objective="poisson" if jenis == "poisson" else "regression_l2",
                                     **SETELAN_LGB)

    def fit(self, X, y):
        self.glm.fit(X, y)
        self.lgb.fit(X, y)
        return self

    def predict(self, X):
        return (self.glm.predict(X) + self.lgb.predict(X)) / 2


def latih_semua(X: np.ndarray, Y: pd.DataFrame, jenis: dict, alpha: float, ensemble: bool = False) -> dict:
    pembuat = Ensemble if ensemble else buat_model
    return {k: pembuat(jenis.get(k, "poisson"), alpha).fit(X, Y[k].to_numpy()) for k in Y.columns}


def tau(x, y, lk, lt, rho):
    if x == 0 and y == 0:
        return 1 - lk * lt * rho
    if x == 0 and y == 1:
        return 1 + lk * rho
    if x == 1 and y == 0:
        return 1 + lt * rho
    if x == 1 and y == 1:
        return 1 - rho
    return 1.0


def matriks_skor(lk: float, lt: float, rho: float) -> np.ndarray:
    angka = np.arange(MAKS_GOL + 1)
    m = np.outer(poisson.pmf(angka, max(lk, 1e-3)), poisson.pmf(angka, max(lt, 1e-3)))
    for x in (0, 1):
        for y in (0, 1):
            m[x, y] *= tau(x, y, lk, lt, rho)
    return m / m.sum()


def peluang_hasil(m: np.ndarray) -> tuple[float, float, float]:
    return float(np.tril(m, -1).sum()), float(np.trace(m)), float(np.triu(m, 1).sum())


def setel_rho(lk, lt, gk, gt) -> float:
    terbaik, nilai_terbaik = 0.0, -np.inf
    for rho in np.linspace(-0.2, 0.2, 81):
        ll = 0.0
        for a, b, x, y in zip(lk, lt, gk, gt):
            t = tau(int(x), int(y), a, b, rho)
            ll += np.log(max(t, 1e-9))
        if ll > nilai_terbaik:
            terbaik, nilai_terbaik = rho, ll
    return float(terbaik)


def setel_alpha(fitur, nama, musim_urut) -> float:
    latih = fitur[fitur.sudah_main & fitur.musim.isin(musim_urut[:-3])
                  & (fitur.k_riwayat >= 5) & (fitur.t_riwayat >= 5)]
    sahih = fitur[fitur.sudah_main & (fitur.musim == musim_urut[-3])]
    median = latih[nama].median()
    hasil = {}
    for alpha in (0.01, 0.1, 0.3, 1.0):
        galat = 0.0
        for k in ("gol_kandang", "gol_tandang"):
            m = buat_model("poisson", alpha).fit(latih[nama].fillna(median), latih[k])
            duga = m.predict(sahih[nama].fillna(median))
            galat += float(np.mean(duga - sahih[k] * np.log(np.clip(duga, 1e-9, None))))
        hasil[alpha] = round(galat, 5)
    print("  penyetelan alpha (rugi Poisson, makin kecil makin baik):", hasil)
    return min(hasil, key=hasil.get)


# ------------------------------------------------------------------ simulasi
def simulasi_klasemen(fitur: pd.DataFrame, rho: float) -> pd.DataFrame:
    musim = fitur[fitur.musim == MUSIM_BERJALAN]
    main, sisa = musim[musim.sudah_main], musim[~musim.sudah_main]
    tim = sorted(set(musim.tim_kandang) | set(musim.tim_tandang))
    idx = {t: i for i, t in enumerate(tim)}

    poin0, sg0, gm0 = np.zeros(len(tim)), np.zeros(len(tim)), np.zeros(len(tim))
    for r in main.itertuples():
        k, t = idx[r.tim_kandang], idx[r.tim_tandang]
        gm0[k] += r.gol_kandang; gm0[t] += r.gol_tandang
        sg0[k] += r.gol_kandang - r.gol_tandang; sg0[t] += r.gol_tandang - r.gol_kandang
        poin0[k] += 3 if r.gol_kandang > r.gol_tandang else (1 if r.gol_kandang == r.gol_tandang else 0)
        poin0[t] += 3 if r.gol_tandang > r.gol_kandang else (1 if r.gol_kandang == r.gol_tandang else 0)

    acak = np.random.default_rng(42)
    poin = np.tile(poin0, (SIMULASI, 1))
    sg = np.tile(sg0, (SIMULASI, 1))
    gm = np.tile(gm0, (SIMULASI, 1))
    lebar = MAKS_GOL + 1
    for r in sisa.itertuples():
        m = matriks_skor(r.duga_gol_kandang, r.duga_gol_tandang, rho).ravel()
        pilih = np.searchsorted(np.cumsum(m), acak.random(SIMULASI) * m.sum())
        pilih = np.clip(pilih, 0, lebar * lebar - 1)
        x, y = pilih // lebar, pilih % lebar
        k, t = idx[r.tim_kandang], idx[r.tim_tandang]
        poin[:, k] += np.where(x > y, 3, np.where(x == y, 1, 0))
        poin[:, t] += np.where(y > x, 3, np.where(x == y, 1, 0))
        sg[:, k] += x - y; sg[:, t] += y - x
        gm[:, k] += x; gm[:, t] += y

    skor_urut = poin * 1e6 + (sg + 500) * 1e3 + gm + acak.random(poin.shape) * 1e-3
    posisi = (-skor_urut).argsort(axis=1).argsort(axis=1) + 1
    n = len(tim)
    return pd.DataFrame({
        "tim": tim,
        "poin_sekarang": poin0.astype(int),
        "laga_sisa": [int(((sisa.tim_kandang == t) | (sisa.tim_tandang == t)).sum()) for t in tim],
        "poin_harapan": poin.mean(0).round(1),
        "posisi_rata_rata": posisi.mean(0).round(2),
        "peluang_juara": (posisi == 1).mean(0).round(4),
        "peluang_empat_besar": (posisi <= 4).mean(0).round(4),
        "peluang_degradasi": (posisi > n - 3).mean(0).round(4),
    }).sort_values(["peluang_juara", "poin_harapan"], ascending=False).reset_index(drop=True)


# ------------------------------------------------------------------ alur utama
def nilai_musim(bagian: pd.DataFrame) -> dict:
    kelas = bagian.hasil.map({"H": 0, "D": 1, "A": 2}).to_numpy()
    peluang = bagian[["peluang_menang_kandang", "peluang_seri", "peluang_menang_tandang"]].to_numpy()
    peluang = peluang / peluang.sum(1, keepdims=True)  # pembulatan membuat jumlahnya meleset tipis
    benar = bagian[TARGET].to_numpy()
    duga = bagian[[f"duga_{k}" for k in TARGET]].to_numpy()
    keluar = {
        "laga": int(len(bagian)),
        "akurasi_hasil": round(float(accuracy_score(kelas, peluang.argmax(1))), 4),
        "log_loss": round(float(log_loss(kelas, peluang, labels=[0, 1, 2])), 4),
        "mae_gol": round(float(mean_absolute_error(benar[:, :2], duga[:, :2])), 4),
        "mae_statistik": round(float(mean_absolute_error(benar[:, 2:], duga[:, 2:])), 4),
        "skor_tepat": round(float(np.mean(bagian.skor_dugaan == (
            bagian.gol_kandang.astype(int).astype(str) + "-" + bagian.gol_tandang.astype(int).astype(str)))), 4),
    }
    odds = bagian[["odds_kandang", "odds_seri", "odds_tandang"]] if "odds_kandang" in bagian else None
    if odds is not None and odds.notna().all(axis=1).mean() > 0.9:
        sah = odds.notna().all(axis=1).to_numpy()
        balik = 1 / odds[sah].to_numpy(dtype=float)
        p_bandar = balik / balik.sum(1, keepdims=True)
        keluar["akurasi_bandar"] = round(float(accuracy_score(kelas[sah], p_bandar.argmax(1))), 4)
        keluar["log_loss_bandar"] = round(float(log_loss(kelas[sah], p_bandar, labels=[0, 1, 2])), 4)
    return keluar


def main() -> None:
    mulai = time.time()
    laga = muat_laga()
    laga["pekan"] = isi_pekan(laga)
    fitur, nama, elo_akhir = bangun_fitur(laga)
    musim_urut = sorted(fitur.musim.unique())
    print(f"Laga: {len(fitur)} ({int(fitur.sudah_main.sum())} selesai, "
          f"{int((~fitur.sudah_main).sum())} belum) | fitur: {len(nama)}")

    alpha = setel_alpha(fitur, nama, [m for m in musim_urut if m not in MUSIM_UJI] + MUSIM_UJI[:1])
    print(f"  alpha terpilih: {alpha}")

    duga_kolom = [f"duga_{k}" for k in TARGET]
    for k in duga_kolom:
        fitur[k] = np.nan

    # dugaan maju bertahap, satu model per musim
    for musim in musim_urut[musim_urut.index(MUSIM_AWAL_DUGA):]:
        latih = fitur[fitur.sudah_main & (fitur.musim < musim)
                      & (fitur.k_riwayat >= 5) & (fitur.t_riwayat >= 5)]
        median = latih[nama].median()
        model = latih_semua(latih[nama].fillna(median).to_numpy(), latih[TARGET], {}, alpha,
                            ensemble=True)
        sasaran = fitur.musim == musim
        Xs = fitur.loc[sasaran, nama].fillna(median).to_numpy()
        for k in TARGET:
            fitur.loc[sasaran, f"duga_{k}"] = model[k].predict(Xs)
    fitur = fitur.copy()  # rapatkan kembali susunan kolom setelah banyak penambahan
    print(f"  dugaan maju bertahap selesai ({time.time() - mulai:.0f} detik)")

    # koreksi Dixon-Coles disetel hanya dari musim sebelum musim uji
    acuan = fitur[fitur.sudah_main & fitur.duga_gol_kandang.notna() & ~fitur.musim.isin(MUSIM_UJI)]
    rho = setel_rho(acuan.duga_gol_kandang, acuan.duga_gol_tandang, acuan.gol_kandang, acuan.gol_tandang)
    print(f"  rho Dixon-Coles: {rho:+.3f}")

    ada = fitur.duga_gol_kandang.notna()
    peluang, skor_utama, peluang_skor, alternatif = [], [], [], []
    for r in fitur[ada].itertuples():
        m = matriks_skor(r.duga_gol_kandang, r.duga_gol_tandang, rho)
        peluang.append(peluang_hasil(m))
        urut = np.dstack(np.unravel_index(np.argsort(-m.ravel()), m.shape))[0][:5]
        skor_utama.append(f"{urut[0][0]}-{urut[0][1]}")
        peluang_skor.append(round(float(m[urut[0][0], urut[0][1]]), 4))
        alternatif.append(json.dumps({f"{a}-{b}": round(float(m[a, b]), 4) for a, b in urut}))
    peluang = np.array(peluang)
    for k in ("peluang_menang_kandang", "peluang_seri", "peluang_menang_tandang", "peluang_skor_dugaan"):
        fitur[k] = np.nan
    for k in ("skor_dugaan", "lima_skor_teratas"):
        fitur[k] = pd.Series(dtype="object")
    fitur.loc[ada, "peluang_menang_kandang"] = peluang[:, 0].round(4)
    fitur.loc[ada, "peluang_seri"] = peluang[:, 1].round(4)
    fitur.loc[ada, "peluang_menang_tandang"] = peluang[:, 2].round(4)
    fitur.loc[ada, "skor_dugaan"] = skor_utama
    fitur.loc[ada, "peluang_skor_dugaan"] = peluang_skor
    fitur.loc[ada, "lima_skor_teratas"] = alternatif

    # statistik tambahan: model untuk musim S hanya belajar dari laga lengkap sebelum musim S,
    # sedangkan laga yang belum dimainkan memakai seluruh laga lengkap
    tambahan_aktif, nilai_tambahan = [], {}
    if "statistik_lengkap" in fitur:
        lengkap = fitur[fitur.statistik_lengkap.astype(str).str.lower().eq("true") & fitur.sudah_main]
        kolom_t = [k for k in TARGET_TAMBAHAN if k in fitur]
        for k in kolom_t:
            fitur[f"duga_{k}"] = np.nan

        nama_x = nama + [c for c in fitur.columns if c.startswith(("k_bentuk_x_", "t_bentuk_x_"))]

        def isi(latih, sasaran):
            median = latih[nama_x].median().fillna(0)
            Xs = fitur.loc[sasaran, nama_x].fillna(median).to_numpy()
            for k in kolom_t:
                baris = latih[latih[k].notna()]
                if len(baris) < MINIMAL_TAMBAHAN:
                    continue
                model = Ensemble(TARGET_TAMBAHAN[k], alpha).fit(
                    baris[nama_x].fillna(median).to_numpy(), baris[k].to_numpy())
                fitur.loc[sasaran, f"duga_{k}"] = model.predict(Xs).round(2)

        for musim in sorted(fitur.musim.unique()):
            isi(lengkap[lengkap.musim < musim], (fitur.musim == musim) & fitur.sudah_main)
        isi(lengkap, ~fitur.sudah_main)

        if "duga_penguasaan_bola_kandang" in fitur:
            fitur["duga_penguasaan_bola_kandang"] = fitur.duga_penguasaan_bola_kandang.clip(25, 75)
            fitur["duga_penguasaan_bola_tandang"] = (100 - fitur.duga_penguasaan_bola_kandang).round(2)
        for sisi, lawan in (("kandang", "tandang"), ("tandang", "kandang")):
            fitur[f"duga_penyelamatan_kiper_{sisi}"] = (
                fitur[f"duga_tembakan_tepat_{lawan}"] - fitur[f"duga_gol_{lawan}"]).clip(lower=0).round(2)
        tambahan_aktif = [k for k in kolom_t if fitur[f"duga_{k}"].notna().any()]
        tambahan_aktif += ["penyelamatan_kiper_kandang", "penyelamatan_kiper_tandang"]

        # penilaian jujur: laga musim berjalan yang punya statistik asli
        nilai = fitur[(fitur.musim == MUSIM_BERJALAN) & fitur.sudah_main]
        for k in tambahan_aktif + (["penguasaan_bola_tandang"] if "penguasaan_bola_kandang" in tambahan_aktif else []):
            pasangan = nilai[[k, f"duga_{k}"]].dropna()
            if len(pasangan):
                rata_latih = lengkap[lengkap.musim < MUSIM_BERJALAN][k].mean()
                mae = float((pasangan[k] - pasangan[f"duga_{k}"]).abs().mean())
                mae_dasar = float((pasangan[k] - rata_latih).abs().mean())
                nilai_tambahan[k] = {"laga": int(len(pasangan)), "mae": round(mae, 3),
                                     "mae_tebakan_rata_rata": round(mae_dasar, 3),
                                     "perbaikan": round(1 - mae / mae_dasar, 4),
                                     "rata_rata_asli": round(float(pasangan[k].mean()), 2)}
        print(f"  statistik tambahan: {len(lengkap)} laga lengkap untuk belajar, "
              f"{len(tambahan_aktif)} statistik diduga")
        for k, v in nilai_tambahan.items():
            print(f"    {k:28s} MAE {v['mae']:8.2f} | tebakan rata-rata {v['mae_tebakan_rata_rata']:8.2f}"
                  f" | perbaikan {v['perbaikan']:6.1%}")

    # penilaian
    dinilai = fitur[fitur.sudah_main & ada]
    per_musim = {m: nilai_musim(dinilai[dinilai.musim == m]) for m in sorted(dinilai.musim.unique())}
    uji = nilai_musim(dinilai[dinilai.musim.isin(MUSIM_UJI)])
    print("\nPenilaian pada musim uji", " + ".join(MUSIM_UJI))
    print(" ", uji)

    # model akhir untuk koefisien yang dibaca di dashboard
    latih = fitur[fitur.sudah_main & (fitur.musim < MUSIM_BERJALAN)
                  & (fitur.k_riwayat >= 5) & (fitur.t_riwayat >= 5)]
    akhir = latih_semua(latih[nama].fillna(latih[nama].median()).to_numpy(),
                        latih[["gol_kandang", "gol_tandang"]], {}, alpha)
    koef = pd.DataFrame({k: akhir[k][-1].coef_ for k in ("gol_kandang", "gol_tandang")}, index=nama)
    koef.index.name = "fitur"

    simulasi = simulasi_klasemen(fitur, rho)
    print("\nSimulasi juara (5 teratas):")
    print(simulasi.head(5)[["tim", "poin_sekarang", "poin_harapan",
                            "peluang_juara", "peluang_empat_besar"]].to_string(index=False))

    # simpan
    MODEL.mkdir(exist_ok=True)
    simpan_kolom = (["musim", "pekan", "putaran", "tanggal", "waktu", "tim_kandang", "tim_tandang",
                     "sudah_main", "hasil", "wasit", "gol_kandang_babak1", "gol_tandang_babak1",
                     "elo_k", "elo_t"]
                    + [c for c in fitur.columns if c.startswith(tuple(f"{a}_" for a in STAT))
                       and not c.startswith("duga_")]
                    + [c for c in fitur.columns if c in (
                        "kartu_merah_kandang", "kartu_merah_tandang", "xg_kandang", "xg_tandang",
                        "odds_kandang", "odds_seri", "odds_tandang", "statistik_lengkap", "stadion")]
                    + [c for c in fitur.columns if c.endswith(("_kandang", "_tandang"))
                       and c.startswith(("penguasaan", "umpan", "penyelamatan", "offside",
                                         "tembakan_melenceng", "tembakan_terblok",
                                         "tembakan_dalam", "tembakan_luar", "akurasi_umpan",
                                         "xg_api", "xg_bbc", "gol_dicegah", "sentuhan_kotak",
                                         "duel_udara", "kena_tiang", "bola_panjang", "tekel",
                                         "persen_tekel", "sapuan"))]
                    + [c for c in ("sumber_statistik_lengkap", "kartu_kuning_dikoreksi", "url_bbc")
                       if c in fitur.columns]
                    + [c for c in fitur.columns if c.startswith("duga_")]
                    + ["peluang_menang_kandang", "peluang_seri", "peluang_menang_tandang",
                       "skor_dugaan", "peluang_skor_dugaan", "lima_skor_teratas"])
    simpan_kolom = list(dict.fromkeys(c for c in simpan_kolom if c in fitur.columns))
    fitur[simpan_kolom].to_csv(DATA / "prediksi_laga.csv", index=False)
    simulasi.to_csv(DATA / "simulasi_juara.csv", index=False)
    koef.round(4).to_csv(MODEL / "koefisien_gol.csv")
    (MODEL / "elo.json").write_text(json.dumps({k: round(v, 1) for k, v in elo_akhir.items()},
                                               indent=2), encoding="utf-8")
    (MODEL / "metrik_poisson.json").write_text(json.dumps({
        "model": "Regresi Poisson dengan koreksi Dixon-Coles",
        "alpha": alpha, "rho": rho, "jumlah_fitur": len(nama), "musim_uji": MUSIM_UJI,
        "uji": uji, "per_musim": per_musim, "statistik_tambahan": tambahan_aktif,
        "evaluasi_tambahan": nilai_tambahan,
        "simulasi": SIMULASI,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nTersimpan dalam {time.time() - mulai:.0f} detik: data/prediksi_laga.csv, "
          "data/simulasi_juara.csv, model/metrik_poisson.json, model/koefisien_gol.csv")


if __name__ == "__main__":
    main()
