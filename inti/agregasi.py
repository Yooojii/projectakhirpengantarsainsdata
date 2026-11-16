"""Agregasi atribut pemain kembali menjadi fitur tim.

Janji spec 7.1: dengan semua penggeser di posisi awal, fitur hasil agregasi
harus sama persis dengan fitur nyata. Itu dijamin menurut konstruksi:
`kalibrasi` memasang konstanta pada atribut yang DIHASILKAN pembangkit apa
adanya (pembulatan dan derau ikut), bukan dengan membalik pembangkit:

    konst[fitur] = fitur_nyata / bentuk(skuad_awal)

`bentuk` dihitung di satu tempat dan dipakai oleh `kalibrasi` maupun
`agregasi_fitur`, sehingga keduanya tidak mungkin berbeda.

Fitur berarah terbalik (kartu kuning, gol kebobolan) diagregasi atas
(100 - atribut). Fitur turunan (gol dicetak, tembakan tepat) tidak punya
konstanta langsung dari atribut agar satu geseran tidak terhitung dua kali.
Hanya pemain inti yang dihitung.
"""
import pandas as pd

from inti.fitur import NAMA_FITUR, fitur_tim
from inti.pemain import Pemain, bangkitkan_skuad

# Bobot posisi per atribut: lini depan berpengaruh pada serangan, lini belakang
# pada pertahanan. Dinormalkan saat dipakai, jadi hanya perbandingannya yang penting.
BOBOT_POSISI: dict[str, dict[str, float]] = {
    "penyelesaian": {"DEP": 0.60, "TEN": 0.30, "BEL": 0.10},
    "kreativitas": {"TEN": 0.50, "DEP": 0.35, "BEL": 0.15},
    "rebutan_pelanggaran": {"TEN": 0.40, "BEL": 0.40, "DEP": 0.20},
    "ketenangan": {"BEL": 0.35, "TEN": 0.35, "DEP": 0.20, "KIP": 0.10},
    "antisipasi": {"BEL": 0.50, "TEN": 0.30, "KIP": 0.20},
    "rebutan_bertahan": {"BEL": 0.50, "TEN": 0.40, "DEP": 0.10},
    "refleks": {"KIP": 1.0},
}

# Bobot campuran tiga atribut bertahan pada gol kebobolan.
BOBOT_KEBOBOLAN = {"antisipasi": 0.45, "rebutan_bertahan": 0.25, "refleks": 0.30}

# Fitur yang punya konstanta sendiri; sisanya turunan atau diteruskan.
FITUR_LANGSUNG = [
    "rata_tembakan", "rata_sepak_pojok", "rasio_konversi", "rata_pelanggaran",
    "rata_kartu_kuning", "rata_gol_kebobolan",
]


def _rata(skuad: list[Pemain], kunci: str, atribut: str, balik: bool = False) -> float:
    bobot = BOBOT_POSISI[kunci]
    total = bobot_total = 0.0
    for p in skuad:
        if p.inti and p.posisi in bobot and atribut in p.atribut:
            nilai = 100.0 - p.atribut[atribut] if balik else float(p.atribut[atribut])
            total += bobot[p.posisi] * nilai
            bobot_total += bobot[p.posisi]
    return total / bobot_total


def bentuk(skuad: list[Pemain]) -> dict[str, float]:
    """Rata-rata tertimbang atribut per fitur. SATU-SATUNYA definisi bentuk;
    dipakai `kalibrasi` dan `agregasi_fitur`."""
    kreativitas = _rata(skuad, "kreativitas", "kreativitas")
    kebobolan = sum(
        BOBOT_KEBOBOLAN[k] * _rata(skuad, k, k.split("_")[0], balik=True)
        for k in BOBOT_KEBOBOLAN
    )
    penyelesaian = _rata(skuad, "penyelesaian", "penyelesaian")
    return {
        "rata_tembakan": kreativitas,
        "rata_sepak_pojok": kreativitas,
        "rasio_konversi": penyelesaian,
        "rata_pelanggaran": _rata(skuad, "rebutan_pelanggaran", "rebutan"),
        "rata_kartu_kuning": _rata(skuad, "ketenangan", "ketenangan", balik=True),
        "rata_gol_kebobolan": kebobolan,
        "proporsi_tepat": penyelesaian,
    }


def kalibrasi(df: pd.DataFrame, klub: str, sebelum: pd.Timestamp) -> dict[str, float]:
    """Konstanta per klub (bukan per laga) yang membuat titik nol tepat."""
    nyata = fitur_tim(df, klub, sebelum, True)
    b = bentuk(bangkitkan_skuad(df, klub, sebelum))
    konst = {f: nyata[f] / b[f] for f in FITUR_LANGSUNG}
    konst["proporsi_tepat"] = (nyata["rata_tembakan_tepat"] / nyata["rata_tembakan"]) / b["proporsi_tepat"]
    return konst


def agregasi_fitur(skuad: list[Pemain], konst: dict[str, float],
                   poin_lima_laga: float, kandang: bool) -> dict[str, float]:
    b = bentuk(skuad)
    n = {f: konst[f] * b[f] for f in FITUR_LANGSUNG}
    proporsi = min(1.0, konst["proporsi_tepat"] * b["proporsi_tepat"])
    hasil = {
        **n,
        "rata_tembakan_tepat": n["rata_tembakan"] * proporsi,
        "rata_gol_dicetak": n["rasio_konversi"] * n["rata_tembakan"],
        "poin_lima_laga": poin_lima_laga,
        "penanda_kandang": 1.0 if kandang else 0.0,
    }
    return {nama: hasil[nama] for nama in NAMA_FITUR}
