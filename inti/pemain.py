"""Pembangkit skuad terkalibrasi dari statistik tim.

Dataset tidak memuat satu pun pemain, jadi seluruh lapisan pemain dibangkitkan.
Kejujurannya bertumpu pada kalibrasi: atribut diturunkan dari statistik nyata
klub, bukan dikarang. Nama pemain sengaja rekaan (bukan pemain sungguhan) agar
atribut rekaan tidak dilekatkan pada orang nyata.

Pembatasan sepuluh fitur berlaku untuk MODEL, bukan untuk pembangkit ini:
di sini boleh dipakai statistik laga nyata apa pun (mis. tembakan yang
dibiarkan lawan), kecuali kolom odds, kelompok API, `xg_kandang`, `xg_tandang`
yang jarang atau tidak tersedia.

ARAH ATRIBUT (jangan dibalik; tiga di antaranya TERBALIK terhadap statistiknya):
    penyelesaian : rasio_konversi                     LANGSUNG
    kreativitas  : rata_tembakan + rata_sepak_pojok   LANGSUNG
    penguasaan   : tembakan yang dibiarkan lawan      TERBALIK (sedikit -> tinggi)
    rebutan      : rata_pelanggaran                   LANGSUNG
                   + tembakan dibiarkan lawan         TERBALIK
    antisipasi   : rata_gol_kebobolan                 TERBALIK (sedikit -> tinggi)
    ketenangan   : rata_kartu_kuning                  TERBALIK (sedikit -> tinggi)
    refleks (kiper saja) : rata_gol_kebobolan         TERBALIK
"""
import zlib
from dataclasses import dataclass

import numpy as np
import pandas as pd

from inti.fitur import UKURAN_JENDELA, MINIMUM_LAGA, LAGA_LIGA, fitur_tim

BENIH: int = 2627

ATRIBUT: list[str] = [
    "penyelesaian", "kreativitas", "penguasaan", "rebutan", "antisipasi", "ketenangan",
]

BATAS_BAWAH, BATAS_ATAS = 45.0, 85.0   # pusat sebaran untuk persentil 0 dan 1
SIMPANGAN = 2.0                        # sd derau per pemain; kecil agar urutan liga bertahan
GESER_CADANGAN = 6.0
GESER_POSISI = 6.0

# Simpangan posisi: penyerang naik di penyelesaian, bek di antisipasi dan
# rebutan, gelandang di kreativitas dan penguasaan.
_GESER = {
    "DEP": {"penyelesaian": GESER_POSISI},
    "BEL": {"antisipasi": GESER_POSISI, "rebutan": GESER_POSISI},
    "TEN": {"kreativitas": GESER_POSISI, "penguasaan": GESER_POSISI},
    "KIP": {},
}

_INTI = ["KIP"] + ["BEL"] * 4 + ["TEN"] * 3 + ["DEP"] * 3
_CADANGAN = ["KIP", "BEL", "BEL", "TEN", "TEN", "DEP", "DEP"]

_NAMA_DEPAN = [
    "James", "Oliver", "Harry", "Jack", "Callum", "Declan", "Marcus", "Luke", "Reece",
    "Tom", "Ben", "Connor", "Jordan", "Kieran", "Mason", "Liam", "Ryan", "Sam",
    "Lucas", "Mateo", "Rafael", "Julian", "Florian", "Andre", "Pieter", "Matthias",
    "Stefan", "Luka", "Diego", "Emil", "Hugo", "Nico", "Viktor", "Marco", "Pablo",
]
_NAMA_BELAKANG = [
    "Walker", "Hughes", "Palmer", "Bennett", "Fletcher", "Hartley", "Sutton", "Rowe",
    "Barnes", "Collins", "Dawson", "Ellis", "Griffin", "Holloway", "Marsh", "Nolan",
    "Pearce", "Whitaker", "Mueller", "Kovac", "Ferreira", "Lindqvist", "Dubois",
    "Rossi", "Hoffmann", "Vasquez", "Janssen", "Novak", "Bergman", "Moreau",
    "Santos", "Petrov", "Andersen", "Costa", "Wagner",
]


@dataclass
class Pemain:
    nama: str
    posisi: str            # "KIP", "BEL", "TEN", "DEP"
    atribut: dict[str, int]
    inti: bool


def _rng(klub: str) -> np.random.Generator:
    # crc32 (bukan hash()) agar sama antar sesi; urutan [BENIH, klub] beda antar klub
    return np.random.default_rng([BENIH, zlib.crc32(klub.encode("utf-8"))])


def _tembakan_dibiarkan(lampau: pd.DataFrame, klub: str) -> float:
    """Rata-rata tembakan lawan di `UKURAN_JENDELA` laga terakhir klub dalam `lampau`
    (laga yang sudah lewat); kurang dari `MINIMUM_LAGA` laga memakai rata-rata
    liga dari `LAGA_LIGA` laga terakhir di `lampau`."""
    kandang = lampau[lampau["tim_kandang"] == klub]
    tandang = lampau[lampau["tim_tandang"] == klub]
    laga = pd.concat([
        pd.DataFrame({"tanggal": kandang["tanggal"], "nilai": kandang["tembakan_tandang"]}),
        pd.DataFrame({"tanggal": tandang["tanggal"], "nilai": tandang["tembakan_kandang"]}),
    ]).sort_values("tanggal", kind="stable").tail(UKURAN_JENDELA)
    if len(laga) >= MINIMUM_LAGA:
        return float(laga["nilai"].mean())
    akhir = lampau.tail(LAGA_LIGA)
    return float(np.r_[akhir["tembakan_kandang"], akhir["tembakan_tandang"]].mean())


def _metrik(df: pd.DataFrame, lampau: pd.DataFrame, klub: str, sebelum: pd.Timestamp) -> dict[str, float]:
    f = fitur_tim(df, klub, sebelum, True)
    return {**f, "tembakan_dibiarkan": _tembakan_dibiarkan(lampau, klub)}


def _musim_acuan(df: pd.DataFrame, sebelum: pd.Timestamp) -> list[str]:
    lampau = df[df["tanggal"] < sebelum]
    sumber = lampau if len(lampau) else df
    musim = sumber["musim"].iloc[-1]
    sub = df[df["musim"] == musim]
    return sorted(set(sub["tim_kandang"]) | set(sub["tim_tandang"]))


def _persentil(nilai: float, acuan: np.ndarray) -> float:
    """Persentil tengah-peringkat (0-1) nilai di antara klub musim itu."""
    return float(((acuan < nilai).sum() + 0.5 * (acuan == nilai).sum()) / len(acuan))


def _pusat(persentil: float) -> float:
    return BATAS_BAWAH + (BATAS_ATAS - BATAS_BAWAH) * persentil


def _pusat_atribut(df: pd.DataFrame, klub: str, sebelum: pd.Timestamp) -> dict[str, float]:
    lampau = df[df["tanggal"] < sebelum]
    acuan = [_metrik(df, lampau, k, sebelum) for k in _musim_acuan(df, sebelum)]
    saya = _metrik(df, lampau, klub, sebelum)

    def pct(nama: str) -> float:
        return _persentil(saya[nama], np.array([a[nama] for a in acuan]))

    # LANGSUNG: nilai statistik tinggi -> atribut tinggi
    # TERBALIK: nilai statistik rendah -> atribut tinggi (1 - persentil)
    langsung = pct
    terbalik = lambda nama: 1.0 - pct(nama)

    p = {
        "penyelesaian": langsung("rasio_konversi"),
        "kreativitas": (langsung("rata_tembakan") + langsung("rata_sepak_pojok")) / 2,
        "penguasaan": terbalik("tembakan_dibiarkan"),
        "rebutan": (langsung("rata_pelanggaran") + terbalik("tembakan_dibiarkan")) / 2,
        "antisipasi": terbalik("rata_gol_kebobolan"),
        "ketenangan": terbalik("rata_kartu_kuning"),
        "refleks": terbalik("rata_gol_kebobolan"),
    }
    return {a: _pusat(v) for a, v in p.items()}


def bangkitkan_skuad(df: pd.DataFrame, klub: str, sebelum: pd.Timestamp) -> list[Pemain]:
    """Sebelas inti berformasi 4-3-3 ditambah tujuh cadangan, deterministik per klub."""
    pusat = _pusat_atribut(df, klub, sebelum)
    rng = _rng(klub)
    posisi_semua = [(p, True) for p in _INTI] + [(p, False) for p in _CADANGAN]
    nama_dipakai: set[str] = set()
    skuad = []
    for posisi, inti in posisi_semua:
        while True:
            nama = f"{rng.choice(_NAMA_DEPAN)} {rng.choice(_NAMA_BELAKANG)}"
            if nama not in nama_dipakai:
                nama_dipakai.add(nama)
                break
        nama_atribut = ATRIBUT + (["refleks"] if posisi == "KIP" else [])
        atribut = {}
        for a in nama_atribut:
            nilai = (pusat[a] + _GESER[posisi].get(a, 0.0)
                     - (0.0 if inti else GESER_CADANGAN) + rng.normal(0.0, SIMPANGAN))
            atribut[a] = int(np.clip(round(nilai), 1, 99))
        skuad.append(Pemain(nama, posisi, atribut, inti))
    return skuad
