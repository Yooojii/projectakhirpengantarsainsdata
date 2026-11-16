"""Model, prediksi, dan distribusi skor.

Berkas model (`model/model.joblib`) dibuat rekan kelompok dan bisa saja belum
ada; tanpa model, `prediksi` memakai jalan mundur Poisson.
"""
import json
import os

import numpy as np
import pandas as pd
from scipy.stats import poisson

from inti.fitur import NAMA_FITUR

# Rata-rata data nyata (9.880 laga): kandang 1,53 gol, tandang 1,18 gol.
GOL_RATA_TIM = 1.355
FAKTOR_KANDANG = 1.13   # 1,53 / 1,355
FAKTOR_TANDANG = 0.87   # 1,18 / 1,355


def muat_model(path: str = "model/model.joblib"):
    """Kembalikan model terlatih, atau None kalau berkasnya belum ada."""
    if not os.path.exists(path):
        return None
    import joblib
    return joblib.load(path)


def muat_evaluasi(path: str = "model/metrik.json") -> dict | None:
    """Kembalikan metrik evaluasi model, atau None kalau belum ada."""
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _gol_harapan(serang: dict, lawan: dict) -> float:
    """Gabungan serangan satu tim dan kebobolan lawan, dikali faktor kandang.

    Hanya memakai fitur gol dan `penanda_kandang`; kunci yang hilang diisi
    rata-rata liga, jadi dict parsial cukup untuk jalan mundur ini.
    """
    serangan = serang.get("rata_gol_dicetak", GOL_RATA_TIM)
    kebobolan = lawan.get("rata_gol_kebobolan", GOL_RATA_TIM)
    kandang = serang.get("penanda_kandang", 0.5)
    faktor = FAKTOR_TANDANG + (FAKTOR_KANDANG - FAKTOR_TANDANG) * kandang
    return max(0.0, (serangan + kebobolan) / 2 * faktor)


def distribusi_skor(gol_k: float, gol_t: float, maks: int = 6) -> dict[tuple[int, int], float]:
    """Sebaran bersama skor (kandang, tandang), dua Poisson independen, dinormalkan.

    Gol harapan 0 sah: poisson.pmf(0, 0) == 1.
    """
    gol_k, gol_t = max(0.0, gol_k), max(0.0, gol_t)
    ks = np.arange(maks + 1)
    pk, pt = poisson.pmf(ks, gol_k), poisson.pmf(ks, gol_t)
    total = pk.sum() * pt.sum()  # massa di dalam kotak 0..maks
    return {(int(i), int(j)): float(pk[i] * pt[j] / total)
            for i in ks for j in ks}


def _hasil(k: int, t: int) -> str:
    return "H" if k > t else "A" if k < t else "D"


def skor_utama(dist: dict, hasil: str) -> tuple[int, int]:
    """Skor paling mungkin di antara yang konsisten dengan `hasil` (H/D/A)."""
    cocok = {s: p for s, p in dist.items() if _hasil(*s) == hasil}
    if not cocok:
        raise ValueError(f"Tidak ada skor untuk hasil {hasil!r}")
    return max(cocok, key=cocok.get)


def _peluang_dari_skor(dist: dict) -> tuple[float, float, float]:
    h = sum(p for s, p in dist.items() if _hasil(*s) == "H")
    d = sum(p for s, p in dist.items() if _hasil(*s) == "D")
    return h, d, 1.0 - h - d


def prediksi(fitur_k: dict, fitur_t: dict, model=None) -> dict:
    """Peluang hasil dan gol harapan untuk satu pertandingan.

    Dengan model, KESEPULUH fitur wajib ada (vektor harus lengkap dan
    berurutan `NAMA_FITUR`). Tanpa model, jalan mundur Poisson cukup dengan
    fitur gol dan `penanda_kandang` saja.
    """
    gol_k = _gol_harapan(fitur_k, fitur_t)
    gol_t = _gol_harapan(fitur_t, fitur_k)

    if model is None:
        h, d, a = _peluang_dari_skor(distribusi_skor(gol_k, gol_t))
    else:
        hilang = [n for n in NAMA_FITUR if n not in fitur_k]
        if hilang:
            raise ValueError(f"Fitur untuk model tidak lengkap, kurang: {hilang}")
        x = [[fitur_k[n] for n in NAMA_FITUR]]
        proba = dict(zip(model.classes_, model.predict_proba(x)[0]))
        h, d, a = float(proba["H"]), float(proba["D"]), float(proba["A"])

    return {"p_menang_kandang": h, "p_seri": d, "p_menang_tandang": a,
            "gol_harapan_kandang": gol_k, "gol_harapan_tandang": gol_t}


def pembanding(prediksi_uji: pd.DataFrame) -> dict[str, float]:
    """Akurasi model, selalu-kandang, dan ikut-odds pada baris yang sama."""
    df = prediksi_uji
    odds = df[["odds_kandang", "odds_seri", "odds_tandang"]].to_numpy()
    tebak_odds = np.array(["H", "D", "A"])[odds.argmin(axis=1)]
    return {
        "model": float((df["prediksi"] == df["hasil"]).mean()),
        "selalu_kandang": float((df["hasil"] == "H").mean()),
        "ikut_odds": float((tebak_odds == df["hasil"].to_numpy()).mean()),
    }
