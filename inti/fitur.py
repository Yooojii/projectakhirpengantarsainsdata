"""Perhitungan fitur pertandingan: sumber kebenaran tunggal.

Modul ini diimpor oleh pipeline pelatihan model dan oleh pembalikan atribut
pemain, jadi definisi jendela hanya boleh ada di sini.

Aturan jendela (spec 8.2): sepuluh laga terakhir klub, kandang dan tandang
digabung, diurutkan menurut tanggal, melintasi batas musim, tanpa laga yang
tanggalnya sama dengan atau sesudah `sebelum`. Kurang dari sepuluh laga memakai
yang ada (minimum tiga); di bawah tiga memakai rata-rata liga pada musim itu.
"""
import numpy as np
import pandas as pd

NAMA_FITUR: list[str] = [
    "rata_tembakan", "rata_tembakan_tepat", "rasio_konversi",
    "rata_sepak_pojok", "rata_pelanggaran", "rata_kartu_kuning",
    "rata_gol_dicetak", "rata_gol_kebobolan", "poin_lima_laga",
    "penanda_kandang",
]

UKURAN_JENDELA = 10
MINIMUM_LAGA = 3
LAGA_POIN = 5

# Kolom statistik per laga dari sudut pandang satu klub, urutannya tetap.
_STAT = ["tembakan", "tepat", "pojok", "pelanggaran", "kuning", "gol", "kebobolan", "poin"]
_IDENTITAS = ["tanggal", "tim_kandang", "tim_tandang"]


def _poin(gol_sendiri: pd.Series, gol_lawan: pd.Series) -> pd.Series:
    return np.where(gol_sendiri > gol_lawan, 3.0, np.where(gol_sendiri == gol_lawan, 1.0, 0.0))


def _sisi(df: pd.DataFrame, sisi: str, lawan: str) -> pd.DataFrame:
    """Statistik tiap laga dari sudut pandang klub yang bermain di `sisi`."""
    return pd.DataFrame({
        "klub": df[f"tim_{sisi}"].to_numpy(),
        "tanggal": df["tanggal"].to_numpy(),
        "tembakan": df[f"tembakan_{sisi}"].to_numpy(float),
        "tepat": df[f"tembakan_tepat_{sisi}"].to_numpy(float),
        "pojok": df[f"sepak_pojok_{sisi}"].to_numpy(float),
        "pelanggaran": df[f"pelanggaran_{sisi}"].to_numpy(float),
        "kuning": df[f"kartu_kuning_{sisi}"].to_numpy(float),
        "gol": df[f"gol_{sisi}"].to_numpy(float),
        "kebobolan": df[f"gol_{lawan}"].to_numpy(float),
        "poin": _poin(df[f"gol_{sisi}"], df[f"gol_{lawan}"]),
    })


def _panjang(df: pd.DataFrame) -> pd.DataFrame:
    """Satu baris per (klub, laga). Kolom kandang/tandang dipilih menurut peran
    klub pada laga itu, bukan menurut laga yang sedang diprediksi."""
    p = pd.concat([_sisi(df, "kandang", "tandang"), _sisi(df, "tandang", "kandang")])
    return p.sort_values("tanggal", kind="stable").reset_index(drop=True)


def _vektor(jendela: np.ndarray, kandang: bool) -> dict[str, float]:
    """Fitur dari matriks jendela (baris = laga urut tanggal, kolom = _STAT)."""
    rata = jendela.mean(axis=0)
    tembakan, tepat, pojok, pelanggaran, kuning, gol, kebobolan, _ = rata
    return {
        "rata_tembakan": float(tembakan),
        "rata_tembakan_tepat": float(tepat),
        # jumlah gol dibagi jumlah tembakan, bukan rata-rata rasio per laga
        "rasio_konversi": float(jendela[:, 5].sum() / jendela[:, 0].sum()),
        "rata_sepak_pojok": float(pojok),
        "rata_pelanggaran": float(pelanggaran),
        "rata_kartu_kuning": float(kuning),
        "rata_gol_dicetak": float(gol),
        "rata_gol_kebobolan": float(kebobolan),
        "poin_lima_laga": float(jendela[-LAGA_POIN:, 7].sum()),
        "penanda_kandang": 1.0 if kandang else 0.0,
    }


def _jendela(laga_klub: np.ndarray, tanggal_klub: np.ndarray, sebelum) -> np.ndarray:
    """Hingga sepuluh laga terakhir yang tanggalnya sebelum `sebelum`."""
    akhir = int(np.searchsorted(tanggal_klub, np.datetime64(sebelum), side="left"))
    return laga_klub[max(0, akhir - UKURAN_JENDELA):akhir]


def _matriks(p: pd.DataFrame) -> np.ndarray:
    return p[_STAT].to_numpy(float)


def _rata_liga(df: pd.DataFrame, sebelum) -> np.ndarray:
    """Rata-rata liga (per klub per laga) pada musim yang memuat `sebelum`."""
    sesudah = df[df["tanggal"] >= sebelum]
    musim = sesudah.iloc[0]["musim"] if len(sesudah) else df.iloc[-1]["musim"]
    return _matriks(_panjang(df[df["musim"] == musim]))


def fitur_tim(df: pd.DataFrame, klub: str, sebelum: pd.Timestamp, kandang: bool) -> dict[str, float]:
    """Fitur satu klub dari laga-laga sebelum `sebelum`.

    `kandang` hanya mengisi `penanda_kandang` untuk laga yang diprediksi.
    """
    p = _panjang(df)
    p = p[p["klub"] == klub]
    jendela = _jendela(_matriks(p), p["tanggal"].to_numpy(), sebelum)
    if len(jendela) < MINIMUM_LAGA:
        jendela = _rata_liga(df, sebelum)
        # rata-rata liga sudah jadi satu baris rata-rata; poin 5 laga = 5x rata-rata
        vektor = _vektor(jendela, kandang)
        vektor["poin_lima_laga"] = float(jendela[:, 7].mean() * LAGA_POIN)
        return vektor
    return _vektor(jendela, kandang)


def tabel_pelatihan(df: pd.DataFrame) -> pd.DataFrame:
    """Satu baris per laga untuk pelatihan model.

    Kolom identitas (`tanggal`, `tim_kandang`, `tim_tandang`) ada di depan dan
    BUKAN fitur; dipakai untuk pemisahan temporal dan berkas evaluasi. Fitur
    didefinisikan oleh `NAMA_FITUR` dengan akhiran `_k` (kandang) dan `_t`
    (tandang), lalu kolom `hasil`. Laga yang salah satu klubnya punya kurang
    dari tiga laga sebelumnya dibuang.
    """
    p = _panjang(df)
    matriks = _matriks(p)
    tanggal = p["tanggal"].to_numpy()
    per_klub = {
        klub: (matriks[idx], tanggal[idx])
        for klub, idx in p.groupby("klub", sort=False).indices.items()
    }
    baris = []
    for laga in df.itertuples(index=False):
        jk = _jendela(*per_klub[laga.tim_kandang], laga.tanggal)
        jt = _jendela(*per_klub[laga.tim_tandang], laga.tanggal)
        if len(jk) < MINIMUM_LAGA or len(jt) < MINIMUM_LAGA:
            continue
        baris.append({
            "tanggal": laga.tanggal,
            "tim_kandang": laga.tim_kandang,
            "tim_tandang": laga.tim_tandang,
            **{f"{k}_k": v for k, v in _vektor(jk, True).items()},
            **{f"{k}_t": v for k, v in _vektor(jt, False).items()},
            "hasil": laga.hasil,
        })
    return pd.DataFrame(baris)
